import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from .keyboards import (
    hr_menu_keyboard,
    leave_type_keyboard,
    back_keyboard,
    back_to_menu_keyboard,
)
from .database import (
    get_all_balances,
    get_balance_for_type,
    get_leave_history,
    deduct_balance,
    save_leave_request,
)
from .storage import save_mc_photo
from .states  import (
    CHOOSING,
    CHOOSING_LEAVE_TYPE,
    WAITING_FOR_DATES,
    WAITING_FOR_MC_PHOTO,
    LEAVE_TYPES,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date_range(dates_str: str) -> int:
    """
    Parse a user-supplied date string and return the number of days it spans.

    Accepts:
        ``'2026-10-01'``                  → 1
        ``'2026-10-01 to 2026-10-03'``    → 3

    Returns 0 if the string cannot be parsed.
    """
    try:
        if " to " in dates_str:
            parts = [p.strip() for p in dates_str.split(" to ")]
            start = datetime.strptime(parts[0], "%Y-%m-%d")
            end   = datetime.strptime(parts[1], "%Y-%m-%d")
            delta = (end - start).days + 1
            return delta if delta > 0 else 0
        else:
            datetime.strptime(dates_str.strip(), "%Y-%m-%d")
            return 1
    except (ValueError, IndexError):
        return 0


def _balance_display(leave_type: str, remaining: int, total: int) -> str:
    """Return a human-readable balance string for a given leave type."""
    if leave_type == "unpaid":
        return "Unlimited"
    return f"{remaining}/{total} day(s) remaining"


async def _thank_and_restart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Send a thank-you message and re-display the HR menu."""
    message = update.message or (
        update.callback_query and update.callback_query.message
    )
    await message.reply_text(
        "✅ *Thank you!* Your request has been submitted successfully.\n\n"
        "Is there anything else I can help you with?",
        parse_mode="Markdown",
        reply_markup=hr_menu_keyboard(),
    )
    return CHOOSING


# ─── Main menu routing ────────────────────────────────────────────────────────

async def menu_button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Route 'mc' and 'leave' button presses from the main HR menu."""
    query  = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "mc":
        user    = update.effective_user
        balance = get_balance_for_type(user.id, "mc")
        remaining_text = (
            _balance_display("mc", balance["remaining"], balance["total_days"])
            if balance else "N/A"
        )
        await query.edit_message_text(
            "🤒 *MC Application*\n\n"
            f"💳 Balance: *{remaining_text}*\n\n"
            "Please upload a *photo* of your MC certificate as proof.\n"
            "_Send the image now, or go back:_",
            parse_mode="Markdown",
            reply_markup=back_keyboard(),
        )
        return WAITING_FOR_MC_PHOTO

    if choice == "leave":
        await query.edit_message_text(
            "🌴 *Apply Leave*\n\nPlease select the type of leave:",
            parse_mode="Markdown",
            reply_markup=leave_type_keyboard(),
        )
        return CHOOSING_LEAVE_TYPE

    return CHOOSING


# ─── Navigation — back buttons ────────────────────────────────────────────────

async def go_back_to_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    ⬅️ Back handler used from:
      - Leave-type selection (CHOOSING_LEAVE_TYPE)
      - MC photo input (WAITING_FOR_MC_PHOTO)
      - Balance / History info screens (CHOOSING — 'menu' pattern)
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Please choose an option below:",
        reply_markup=hr_menu_keyboard(),
    )
    return CHOOSING


async def go_back_to_leave_types(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """⬅️ Back from date-input step → return to leave type selection."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌴 *Apply Leave*\n\nPlease select the type of leave:",
        parse_mode="Markdown",
        reply_markup=leave_type_keyboard(),
    )
    return CHOOSING_LEAVE_TYPE


# ─── Leave type selection ─────────────────────────────────────────────────────

async def receive_leave_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Store the chosen leave type and ask for date(s)."""
    query     = update.callback_query
    await query.answer()
    leave_key = query.data[3:]   # strip "lt_" prefix

    context.user_data["selected_leave_type"] = leave_key

    cfg     = LEAVE_TYPES[leave_key]
    label   = cfg["label"]
    user    = update.effective_user
    balance = get_balance_for_type(user.id, leave_key)
    bal_txt = (
        _balance_display(leave_key, balance["remaining"], balance["total_days"])
        if balance else "N/A"
    )

    await query.edit_message_text(
        f"{label}\n\n"
        f"💳 Balance: *{bal_txt}*\n\n"
        "Please enter the *date(s)* for your leave:\n"
        "_Format: `YYYY-MM-DD` or `YYYY-MM-DD to YYYY-MM-DD`_\n\n"
        "Or go back to select a different type:",
        parse_mode="Markdown",
        reply_markup=back_keyboard(),
    )
    return WAITING_FOR_DATES


# ─── Leave date input ─────────────────────────────────────────────────────────

async def receive_leave_dates(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Validate dates, check balance, deduct, save request."""
    user      = update.effective_user
    dates     = update.message.text.strip()
    leave_key = context.user_data.get("selected_leave_type", "annual")
    cfg       = LEAVE_TYPES[leave_key]
    days      = _parse_date_range(dates)

    # ── Validate format ───────────────────────────────────────────────────────
    if days == 0:
        await update.message.reply_text(
            "⚠️ Invalid date format.\n"
            "Please use `YYYY-MM-DD` or `YYYY-MM-DD to YYYY-MM-DD`.\n"
            "_Example: `2026-10-01` or `2026-10-01 to 2026-10-03`_",
            parse_mode="Markdown",
        )
        return WAITING_FOR_DATES

    # ── Check balance (unpaid is always allowed) ───────────────────────────────
    if leave_key != "unpaid":
        balance = get_balance_for_type(user.id, leave_key)
        if balance and balance["remaining"] < days:
            await update.message.reply_text(
                f"❌ *Insufficient balance!*\n\n"
                f"You requested *{days} day(s)* of {cfg['label']} but only have "
                f"*{balance['remaining']} day(s)* remaining.\n\n"
                "Please enter different dates or go back to choose another leave type.",
                parse_mode="Markdown",
            )
            return WAITING_FOR_DATES

    # ── Deduct and save ───────────────────────────────────────────────────────
    deduct_balance(user.id, leave_key, days)
    save_leave_request(user.id, leave_key, dates, days_taken=days)

    balance   = get_balance_for_type(user.id, leave_key)
    remaining = _balance_display(leave_key, balance["remaining"], balance["total_days"]) if balance else "N/A"

    await update.message.reply_text(
        f"✅ *{cfg['label']}* request submitted!\n\n"
        f"📅 Date(s): *{dates}*\n"
        f"📊 Days taken: *{days}*\n"
        f"💳 Remaining balance: *{remaining}*",
        parse_mode="Markdown",
    )
    return await _thank_and_restart(update, context)


async def wrong_input_dates(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Remind user to send text when date input is expected."""
    await update.message.reply_text(
        "⚠️ Please send your leave *date(s)* as a text message.\n"
        "_Format: `YYYY-MM-DD` or `YYYY-MM-DD to YYYY-MM-DD`_",
        parse_mode="Markdown",
    )
    return WAITING_FOR_DATES


# ─── MC photo upload ──────────────────────────────────────────────────────────

async def receive_mc_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Download the MC photo, save to storage/mc/, deduct MC balance, save request."""
    user     = update.effective_user
    photo    = update.message.photo[-1]   # highest resolution
    today    = datetime.now().strftime("%Y-%m-%d")

    filename = await save_mc_photo(photo, user.id)
    deduct_balance(user.id, "mc", 1)
    save_leave_request(user.id, "mc", today, days_taken=1, mc_filename=filename)

    balance   = get_balance_for_type(user.id, "mc")
    remaining = balance["remaining"] if balance else "N/A"

    await update.message.reply_text(
        f"📎 MC proof saved as `{filename}`\n\n"
        f"✅ MC application submitted for *{today}*\n"
        f"💳 Remaining MC balance: *{remaining} day(s)*",
        parse_mode="Markdown",
    )
    return await _thank_and_restart(update, context)


async def wrong_input_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Remind user to send a photo when MC proof is expected."""
    await update.message.reply_text(
        "⚠️ Please send a *photo* (image file) as your MC proof.",
        parse_mode="Markdown",
    )
    return WAITING_FOR_MC_PHOTO


# ─── Info screens (balance & history) ────────────────────────────────────────

async def show_balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Display all leave balances for the user."""
    query = update.callback_query
    await query.answer()

    user     = update.effective_user
    balances = get_all_balances(user.id)

    # Build label map: leave_type → display label
    label_map = {k: v["label"] for k, v in LEAVE_TYPES.items()}
    label_map["mc"] = "🤒 Medical Leave (MC)"

    lines = ["📊 *Your Leave Balance*\n"]
    for b in balances:
        lt    = b["leave_type"]
        label = label_map.get(lt, lt.title())
        bal   = _balance_display(lt, b["remaining"], b["total_days"])
        lines.append(f"{label}\n   ➜ *{bal}*")

    await query.edit_message_text(
        "\n\n".join(lines),
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard(),
    )
    return CHOOSING


async def show_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Display the user's 5 most recent leave requests."""
    query = update.callback_query
    await query.answer()

    user    = update.effective_user
    history = get_leave_history(user.id, limit=5)

    label_map = {k: v["label"] for k, v in LEAVE_TYPES.items()}
    label_map["mc"] = "🤒 MC"

    STATUS_EMOJI = {"pending": "⏳", "approved": "✅", "rejected": "❌"}

    if not history:
        text = "📋 *My Recent Requests*\n\n_No requests found._"
    else:
        lines = ["📋 *My Recent Requests* _(last 5)_\n"]
        for i, h in enumerate(history, 1):
            lt      = h["leave_type"]
            label   = label_map.get(lt, lt.title())
            emoji   = STATUS_EMOJI.get(h["status"], "❓")
            mc_note = f" | 📎 `{h['mc_filename']}`" if h.get("mc_filename") else ""
            lines.append(
                f"*{i}. {label}*\n"
                f"   📅 {h['dates']} ({h['days_taken']} day(s))\n"
                f"   {emoji} {h['status'].title()} | {h['submitted_at'][:10]}{mc_note}"
            )
        text = "\n\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard(),
    )
    return CHOOSING


# ─── Cancel ───────────────────────────────────────────────────────────────────

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle /cancel — exit the current conversation."""
    await update.message.reply_text(
        "❌ Operation cancelled. Type /start to begin again."
    )
    return ConversationHandler.END
