"""AIbazari Telegram bot entry point. Token comes from env TELEGRAM_BOT_TOKEN (.env on the server)."""
import os

from telegram.ext import Application

import donate
import doors


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    doors.register(app)
    donate.register(app)
    app.run_polling()


if __name__ == "__main__":
    main()
