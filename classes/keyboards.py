from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .states import LEAVE_TYPES


def hr_menu_keyboard() -> InlineKeyboardMarkup:
    """Main HR menu — Apply MC, Apply Leave, My Balance, My History."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤒 Apply MC",    callback_data="mc"),
            InlineKeyboardButton("🌴 Apply Leave", callback_data="leave"),
        ],
        [
            InlineKeyboardButton("📊 My Balance",  callback_data="balance"),
            InlineKeyboardButton("📋 My History",  callback_data="history"),
        ],
    ])


def leave_type_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard listing all leave types, paired 2-per-row, with a Back button."""
    items = list(LEAVE_TYPES.items())
    rows  = []
    for i in range(0, len(items), 2):
        row = [
            InlineKeyboardButton(cfg["label"], callback_data=f"lt_{key}")
            for key, cfg in items[i : i + 2]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
    return InlineKeyboardMarkup(rows)


def back_keyboard() -> InlineKeyboardMarkup:
    """Single ⬅️ Back button — used on MC and date-input prompts."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """⬅️ Back to Menu — used on the balance and history info screens."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu")]
    ])
