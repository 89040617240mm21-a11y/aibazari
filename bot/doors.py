"""Three doors at start: sell by photo, give away / ask for help, "is this a scam?".

State lives in ctx.user_data["state"]: sell | give | scam | msg:<listing> | reply:<user>:<listing>.
"""
import hashlib
import hmac
import os

from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as KB, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

import ai
import scam
import store
from texts import lang, t

LIMIT = int(os.environ.get("AI_LIMIT_DAY", "50"))
LIMIT_TRUSTED = int(os.environ.get("AI_LIMIT_TRUSTED", "100"))
DOORS = ("sell", "give", "scam")
SECRET = (os.environ.get("TELEGRAM_BOT_TOKEN") or "dev").encode()


def sign(to: int, lid, viewer: int) -> str:
    """Reply buttons are signed so a modified client cannot message arbitrary users."""
    return hmac.new(SECRET, f"{to}:{lid}:{viewer}".encode(), hashlib.sha256).hexdigest()[:10]


def reply_btn(lg: str, to: int, lid, viewer: int) -> KB:
    return KB([[B(t(lg, "reply"), callback_data=f"reply:{to}:{lid}:{sign(to, lid, viewer)}")]])


def _lg(update: Update) -> str:
    return lang(update.effective_user.language_code if update.effective_user else None)


def doors_kb(lg: str, skip: str | None = None) -> KB:
    return KB([[B(t(lg, f"door_{d}"), callback_data=f"door:{d}")] for d in DOORS if d != skip])


def card_text(card: dict, lg: str) -> str:
    lines = [f"<b>{_esc(card['title'])}</b>", _esc(card["body"])]
    if card.get("price"):
        lines.append(f"💰 {_esc(card['price'])}")
    if card.get("city"):
        lines.append(f"📍 {_esc(card['city'])}")
    return "\n".join(x for x in lines if x)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def can_ai(user_id: int) -> tuple[bool, int]:
    n = LIMIT_TRUSTED if store.is_trusted(user_id) else LIMIT
    return store.used(user_id) < n, n


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    ctx.user_data.clear()
    lg = _lg(update)
    await update.message.reply_text(t(lg, "hello"), reply_markup=doors_kb(lg))


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    lg, uid = _lg(update), update.effective_user.id
    kind, _, arg = q.data.partition(":")
    if kind == "door":
        ctx.user_data["state"] = arg
        await q.message.reply_text(t(lg, {"sell": "ask_photo", "give": "ask_give", "scam": "ask_scam"}[arg]))
    elif kind == "pub":
        p = ctx.user_data.pop("pending", None)
        if p:
            store.add_listing(uid, p["card"], p["kind"], p.get("photo"), lg)
            await q.message.reply_text(t(lg, "published") + "\n" + t(lg, "safety"))
            await _next(q.message, lg, p["kind"])
        ctx.user_data.pop("state", None)
    elif kind == "redo":
        ctx.user_data.pop("pending", None)
        await q.message.reply_text(t(lg, "cancelled"), reply_markup=doors_kb(lg))
    elif kind == "del":
        if store.delete(int(arg), uid):
            await q.message.reply_text(t(lg, "deleted"))
    elif kind == "msg":
        ctx.user_data["state"] = f"msg:{arg}"
        await q.message.reply_text(t(lg, "ask_msg"))
    elif kind == "reply":
        to, lid, sig = arg.split(":")
        if not hmac.compare_digest(sig, sign(int(to), lid, uid)):
            return
        ctx.user_data["state"] = f"reply:{to}:{lid}"
        await q.message.reply_text(t(lg, "ask_msg"))


async def _next(msg, lg: str, done: str) -> None:
    door = "sell" if done == "give" else "give" if done == "sell" else "sell"
    await msg.reply_text(t(lg, "next_door", doors=t(lg, f"door_{door}")), reply_markup=doors_kb(lg, skip=done))


async def _limit(update: Update, lg: str) -> bool:
    ok, n = can_ai(update.effective_user.id)
    if not ok:
        await update.message.reply_text(t(lg, "limit", n=n))
    return not ok


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lg, uid = _lg(update), update.effective_user.id
    if await _limit(update, lg):
        return
    ph = update.message.photo[-1]
    data = bytes(await (await ph.get_file()).download_as_bytearray())
    caption = update.message.caption or ""
    card = ai.make_card(caption, lg, data)
    store.count_use(uid)
    note = ""
    if not card:
        card, note = {"title": caption[:60] or "📦", "body": caption, "price": "", "city": ""}, t(lg, "no_ai")
    if not card["title"]:
        await update.message.reply_text(t(lg, "cancelled"), reply_markup=doors_kb(lg))
        return
    ctx.user_data["pending"] = {"card": card, "kind": "sell", "photo": ph.file_id}
    await update.message.reply_photo(ph.file_id, caption=f"{card_text(card, lg)}\n\n{note}{t(lg, 'card_ready')}",
                                     parse_mode="HTML", reply_markup=_pub_kb(lg))


def _pub_kb(lg: str) -> KB:
    return KB([[B(t(lg, "publish"), callback_data="pub:"), B(t(lg, "redo"), callback_data="redo:")]])


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lg, uid, text = _lg(update), update.effective_user.id, update.message.text or ""
    state = ctx.user_data.get("state", "")
    if update.message.forward_origin and not state.startswith(("msg", "reply")):
        state = "scam"
    if state == "scam":
        await _scam(update, lg, text)
    elif state == "give":
        if await _limit(update, lg):
            return
        card = ai.make_card(text, lg)
        store.count_use(uid)
        note = ""
        if not card:
            card, note = {"title": text[:60], "body": text, "price": "", "city": ""}, t(lg, "no_ai") + "\n"
        if not card["title"]:
            await update.message.reply_text(t(lg, "cancelled"), reply_markup=doors_kb(lg))
            return
        ctx.user_data["pending"] = {"card": card, "kind": "give"}
        await update.message.reply_text(f"{card_text(card, lg)}\n\n{note}{t(lg, 'card_ready')}",
                                        parse_mode="HTML", reply_markup=_pub_kb(lg))
    elif state.startswith("msg:"):
        row = store.get_listing(int(state[4:]))
        ctx.user_data.pop("state", None)
        if row and row["user_id"] != uid:
            await ctx.bot.send_message(
                row["user_id"], t(row["lang"], "msg_in", title=row["title"], text=text) + "\n\n" + t(row["lang"], "safety"),
                reply_markup=reply_btn(row["lang"], uid, row["id"], row["user_id"]))
            await update.message.reply_text(t(lg, "msg_sent"))
    elif state.startswith("reply:"):
        to, lid = state[6:].split(":")
        row = store.get_listing(int(lid))
        ctx.user_data.pop("state", None)
        title = row["title"] if row else "AIbazari"
        await ctx.bot.send_message(int(to), t(lg, "msg_in", title=title, text=text),
                                   reply_markup=reply_btn(lg, uid, lid, int(to)))
        await update.message.reply_text(t(lg, "msg_sent"))
    else:
        await update.message.reply_text(t(lg, "hello"), reply_markup=doors_kb(lg))


async def _scam(update: Update, lg: str, text: str) -> None:
    signs = scam.check(text, lg)
    out = (t(lg, "scam_rules") + "\n• " + "\n• ".join(signs)) if signs else t(lg, "scam_none")
    ok, _ = can_ai(update.effective_user.id)
    if ok and text.strip():
        verdict = ai.scam_check(text, lg)
        store.count_use(update.effective_user.id)
        if verdict:
            out = verdict + ("\n\n" + t(lg, "scam_rules") + "\n• " + "\n• ".join(signs) if signs else "")
    await update.message.reply_text(out + "\n\n" + t(lg, "safety"), reply_markup=doors_kb(lg, skip="scam"))


async def find(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lg = _lg(update)
    if not ctx.args:
        await update.message.reply_text(t(lg, "find_usage"))
        return
    rows = store.find(" ".join(ctx.args))
    if not rows:
        await update.message.reply_text(t(lg, "nothing"))
    for r in rows:
        kb = KB([[B(t(lg, "write_author"), callback_data=f"msg:{r['id']}")]])
        if r["photo"]:
            await update.message.reply_photo(r["photo"], caption=card_text(dict(r), lg), parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(card_text(dict(r), lg), parse_mode="HTML", reply_markup=kb)


async def my(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lg = _lg(update)
    rows = store.my(update.effective_user.id)
    if not rows:
        await update.message.reply_text(t(lg, "my_empty"), reply_markup=doors_kb(lg))
    for r in rows:
        await update.message.reply_text(card_text(dict(r), lg), parse_mode="HTML",
                                        reply_markup=KB([[B(t(lg, "delete"), callback_data=f"del:{r['id']}")]]))


def register(app) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("my", my))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(door|pub|redo|del|msg|reply):"))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
