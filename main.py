import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from classes import (
    # Registration flow
    start,
    receive_name,
    receive_employee_id,
    receive_department,
    wrong_input_for_name,
    wrong_input_for_emp_id,
    wrong_input_for_dept,
    # HR flow
    menu_button_handler,
    go_back_to_menu,
    go_back_to_leave_types,
    receive_leave_type,
    receive_leave_dates,
    wrong_input_dates,
    receive_mc_photo,
    wrong_input_photo,
    show_balance,
    show_history,
    cancel,
    # Bootstrap helpers
    ensure_dirs,
    init_db,
)
from classes.states import (
    REG_NAME, REG_EMPLOYEE_ID, REG_DEPARTMENT,
    CHOOSING, CHOOSING_LEAVE_TYPE, WAITING_FOR_DATES, WAITING_FOR_MC_PHOTO,
)

# ─── Bootstrap ────────────────────────────────────────────────────────────────

load_dotenv()
ensure_dirs()
init_db()

logging.basicConfig(
    filename=os.path.join("storage", "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logging.info("Starting HR Bot Application...")


# ─── App entry point ──────────────────────────────────────────────────────────

def main() -> None:
    token = os.getenv("token")
    if not token:
        raise ValueError("No Telegram bot token found. Check your .env file.")

    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={

            # ── Registration ─────────────────────────────────────────────────
            REG_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
                MessageHandler(~filters.TEXT,                   wrong_input_for_name),
            ],
            REG_EMPLOYEE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_employee_id),
                MessageHandler(~filters.TEXT,                   wrong_input_for_emp_id),
            ],
            REG_DEPARTMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_department),
                MessageHandler(~filters.TEXT,                   wrong_input_for_dept),
            ],

            # ── Main menu ────────────────────────────────────────────────────
            CHOOSING: [
                CallbackQueryHandler(menu_button_handler, pattern="^(mc|leave)$"),
                CallbackQueryHandler(show_balance,        pattern="^balance$"),
                CallbackQueryHandler(show_history,        pattern="^history$"),
                CallbackQueryHandler(go_back_to_menu,     pattern="^menu$"),  # from info screens
            ],

            # ── Leave type selection ──────────────────────────────────────────
            CHOOSING_LEAVE_TYPE: [
                CallbackQueryHandler(receive_leave_type, pattern="^lt_"),
                CallbackQueryHandler(go_back_to_menu,    pattern="^back$"),
            ],

            # ── Date input ────────────────────────────────────────────────────
            WAITING_FOR_DATES: [
                CallbackQueryHandler(go_back_to_leave_types,                  pattern="^back$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_leave_dates),
                MessageHandler(~filters.TEXT,                   wrong_input_dates),
            ],

            # ── MC photo upload ────────────────────────────────────────────────
            WAITING_FOR_MC_PHOTO: [
                CallbackQueryHandler(go_back_to_menu,          pattern="^back$"),
                MessageHandler(filters.PHOTO,    receive_mc_photo),
                MessageHandler(~filters.PHOTO,   wrong_input_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)

    logging.info("Bot is running and polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()