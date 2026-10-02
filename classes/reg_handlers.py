import logging
from telegram import Update
from telegram.ext import ContextTypes

from .keyboards import hr_menu_keyboard
from .database  import is_registered, register_user
from .states    import REG_NAME, REG_EMPLOYEE_ID, REG_DEPARTMENT, CHOOSING


# ─── Entry point ──────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /start.
    - If the user is already registered → show the HR menu.
    - If not → begin the registration onboarding flow.
    """
    user = update.effective_user
    logging.info("User %s (%s) used /start.", user.id, user.full_name)

    if is_registered(user.id):
        await update.message.reply_text(
            f"👋 Welcome back, *{user.first_name}*!\n\nWhat would you like to do today?",
            parse_mode="Markdown",
            reply_markup=hr_menu_keyboard(),
        )
        return CHOOSING

    # First time — start onboarding
    await update.message.reply_text(
        f"👋 Welcome to the *HR Management Bot*, *{user.first_name}*!\n\n"
        "Before we start, let's set up your profile.\n\n"
        "👤 Please enter your *full name*:",
        parse_mode="Markdown",
    )
    return REG_NAME


# ─── Registration flow ────────────────────────────────────────────────────────

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the user's name and ask for their employee ID."""
    name = update.message.text.strip()
    context.user_data["reg_name"] = name

    await update.message.reply_text(
        f"✅ Name saved: *{name}*\n\n"
        "🪪 Now please enter your *Employee ID*:\n"
        "_Example: EMP-001_",
        parse_mode="Markdown",
    )
    return REG_EMPLOYEE_ID


async def receive_employee_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the employee ID and ask for department."""
    emp_id = update.message.text.strip()
    context.user_data["reg_emp_id"] = emp_id

    await update.message.reply_text(
        f"✅ Employee ID saved: *{emp_id}*\n\n"
        "🏢 Finally, which *department* are you in?\n"
        "_Example: Engineering, HR, Finance, Sales_",
        parse_mode="Markdown",
    )
    return REG_DEPARTMENT


async def receive_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Complete registration, save the profile, and show the HR menu."""
    user       = update.effective_user
    department = update.message.text.strip()
    full_name  = context.user_data.pop("reg_name",   user.full_name)
    emp_id     = context.user_data.pop("reg_emp_id", "N/A")

    register_user(user.id, full_name, emp_id, department)
    logging.info("Registration complete for user %s.", user.id)

    await update.message.reply_text(
        "🎉 *Registration complete!*\n\n"
        f"👤 Name: *{full_name}*\n"
        f"🪪 Employee ID: *{emp_id}*\n"
        f"🏢 Department: *{department}*\n\n"
        "Your leave balance has been set up. Here's what you can do:",
        parse_mode="Markdown",
        reply_markup=hr_menu_keyboard(),
    )
    return CHOOSING


# ─── Wrong-input guards (registration) ───────────────────────────────────────

async def wrong_input_for_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚠️ Please send your *full name* as a text message.", parse_mode="Markdown"
    )
    return REG_NAME


async def wrong_input_for_emp_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚠️ Please send your *Employee ID* as a text message.", parse_mode="Markdown"
    )
    return REG_EMPLOYEE_ID


async def wrong_input_for_dept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚠️ Please send your *department name* as a text message.", parse_mode="Markdown"
    )
    return REG_DEPARTMENT
