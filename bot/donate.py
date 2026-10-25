"""Donations via Telegram Stars (currency XTR, no provider token needed).

Rule 12101: donations go to development only, the project is never sold;
every donation is logged and the public total is shown by /donations.
"""
import json
import os
import time

from telegram import LabeledPrice, Update
from telegram.ext import (CommandHandler, ContextTypes, MessageHandler,
                          PreCheckoutQueryHandler, filters)

LEDGER = os.environ.get("DONATIONS_LEDGER", "/opt/aibazari/data/donations.jsonl")
AMOUNTS = (50, 100, 250, 500, 1000)  # Stars


def _append(rec: dict) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def total_stars() -> int:
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return sum(json.loads(line).get("stars", 0) for line in f if line.strip())
    except FileNotFoundError:
        return 0


async def donate(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    stars = AMOUNTS[1]
    if ctx.args and ctx.args[0].isdigit():
        stars = max(1, min(int(ctx.args[0]), 10000))
    await ctx.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="Support AIbazari",
        description="Goes to development only. The project is never sold.",
        payload=f"donate:{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("Donation", stars)],
    )


async def precheckout(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.pre_checkout_query
    await q.answer(ok=q.invoice_payload.startswith("donate:"))


async def paid(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    p = update.message.successful_payment
    _append({
        "ts": int(time.time()),
        "user_id": update.effective_user.id,
        "stars": p.total_amount,
        "charge_id": p.telegram_payment_charge_id,
    })
    await update.message.reply_text("Thank you! Every Star goes to AIbazari development. /donations shows the total.")


async def donations(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Collected: {total_stars()} ⭐. Spending report: docs/spending.md")


def register(app) -> None:
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("donations", donations))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, paid))
