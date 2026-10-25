"""Claude layer with a daily budget brake.

Budget: MONTHLY_BUDGET_USD / 30 per day. Over the daily budget -> only the cheap model;
over twice the daily budget -> no AI at all (the bot keeps working without it).
Keys: ANTHROPIC_API_KEYS (comma-separated pool, each key has its own monthly credits) or ANTHROPIC_API_KEY.
A key that returns 401 or "credit balance too low" is skipped until the next day.
Without keys every call returns None and callers use the plain-text fallback.
"""
import base64
import json
import os

import store

CHEAP = os.environ.get("AI_MODEL_CHEAP", "claude-haiku-5-5")
SMART = os.environ.get("AI_MODEL_SMART", "claude-sonnet-5-5")
PRICE = {  # USD per 1M tokens: input, output
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}
DAILY = float(os.environ.get("MONTHLY_BUDGET_USD", "200")) / 30

KEYS = [k.strip() for k in (os.environ.get("ANTHROPIC_API_KEYS") or os.environ.get("ANTHROPIC_API_KEY", "")).split(",")
        if k.strip()]
_clients: dict[int, object] = {}
_dead: dict[int, str] = {}  # key index -> day it ran dry


def _live() -> list[int]:
    return [i for i in range(len(KEYS)) if _dead.get(i) != store.today()]


def _client(i: int):
    if i not in _clients:
        import anthropic
        _clients[i] = anthropic.Anthropic(api_key=KEYS[i], max_retries=1)
    return _clients[i]


def _dry(e: Exception) -> bool:
    code = getattr(e, "status_code", 0)
    return code in (401, 402, 403) or (code == 400 and "credit balance" in str(e).lower())


def client():
    live = _live()
    return _client(live[0]) if live else None


def pick(model: str) -> str | None:
    spent = store.spent_today()
    if spent >= DAILY * 2:
        return None
    return CHEAP if spent >= DAILY else model


def _call(model: str, system: str, content, max_tokens: int = 600) -> str | None:
    m = pick(model)
    if not m:
        return None
    kw = {"output_config": {"effort": "low"}}
    if m == "claude-haiku-5-5":
        kw["thinking"] = {"type": "disabled"}
    r = None
    for i in _live():
        try:
            r = _client(i).messages.create(model=m, max_tokens=max_tokens, system=system,
                                           messages=[{"role": "user", "content": content}], **kw)
            break
        except Exception as e:
            if not _dry(e):
                return None
            _dead[i] = store.today()
    if r is None:
        return None
    pin, pout = PRICE.get(m, PRICE["claude-opus-5-5"])
    store.add_spend((r.usage.input_tokens * pin + r.usage.output_tokens * pout) / 1e6)
    if r.stop_reason == "refusal":
        return None
    return "".join(b.text for b in r.content if b.type == "text").strip() or None


CARD_SYS = (
    "You turn a person's raw text (and photo) into a clean classified-ad card. "
    "Reply with JSON only: {\"title\": short, \"body\": 1-3 sentences, \"price\": string or \"\", "
    "\"city\": string or \"\"}. Write in language '{lang}'. Never invent a price or city that is not given. "
    "If the item is illegal, weapons, drugs, adult or a scam, reply {\"title\": \"\"}."
)


def parse_card(raw: str | None) -> dict | None:
    if not raw:
        return None
    a, b = raw.find("{"), raw.rfind("}")
    try:
        d = json.loads(raw[a:b + 1])
    except (ValueError, TypeError):
        return None
    return {k: str(d.get(k, "") or "")[:500] for k in ("title", "body", "price", "city")}


def make_card(text: str, lang: str, photo: bytes | None = None) -> dict | None:
    content = []
    if photo:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.standard_b64encode(photo).decode()}})
    content.append({"type": "text", "text": text or "(no text, describe the item from the photo)"})
    return parse_card(_call(CHEAP, CARD_SYS.replace("{lang}", lang), content))


SCAM_SYS = (
    "You help ordinary people check if a message is a scam. Language: '{lang}'. "
    "In at most 6 short lines: verdict (likely scam / suspicious / looks ok), the concrete warning signs "
    "in this message, and what to do. Plain words, no jargon. Never ask for personal data."
)


def scam_check(text: str, lang: str) -> str | None:
    return _call(SMART, SCAM_SYS.replace("{lang}", lang), text[:4000], max_tokens=1500)
