"""AIbazari Telegram bot entry point. Token comes from env TELEGRAM_BOT_TOKEN (.env on the server)."""
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import donate


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "AIbazari — free listings for everyone, run by AI.\n"
        "⭐ Support the project: /donate (amount in Stars, e.g. /donate 250)")


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    donate.register(app)
    app.run_polling()


if __name__ == "__main__":
    main()
