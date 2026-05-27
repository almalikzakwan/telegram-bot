import os 
import logging
from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


# log activity
logging.basicConfig(
    filename='storage/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv()
logging.info("Starting Application...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Send a message when the command / start is issued """
    logging.info(f"\nUpdate content: {update}")
    logging.info(f"\nContext content: {context}")
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Send help reply """
    logging.info(f"\nUpdate content: {update}")
    logging.info(f"\nContext content: {context}")
    await update.message.reply_text("Help Command")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Echo the user message. """
    logging.info(f"\nUpdate content: {update}")
    logging.info(f"\nContext content: {context}")
    await update.message.reply_text(update.message.text)

def main() -> None:
    token = os.getenv("token")

    #start application
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__== "__main__":
    main()