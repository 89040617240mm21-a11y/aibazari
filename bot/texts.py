"""User-facing texts. Language comes from Telegram language_code; anything not Russian gets English."""

T = {
    "ru": {
        "hello": ("Привет! Я помощник ИИ площадки AIbazari — бесплатные объявления для всех.\n"
                  "С чего начнём?"),
        "door_sell": "📸 Продать по фото",
        "door_give": "🤝 Отдам даром / нужна помощь",
        "door_scam": "🛡 Это мошенники?",
        "ask_photo": "Пришлите фото вещи. В подписи можно указать цену и город — остальное я допишу сам.",
        "ask_give": "Напишите одним сообщением, что отдаёте или с чем нужна помощь, и город.",
        "ask_scam": "Перешлите мне подозрительное сообщение (или вставьте текст) — объясню, на что обратить внимание.",
        "card_ready": "Вот карточка. Публикуем?",
        "publish": "✅ Опубликовать",
        "redo": "✏️ Заново",
        "published": "Опубликовано! Найти объявления: /find слово. Мои объявления: /my",
        "cancelled": "Хорошо, начнём заново.",
        "nothing": "Ничего не нашлось. Попробуйте другое слово.",
        "find_usage": "Напишите так: /find велосипед",
        "my_empty": "У вас пока нет объявлений.",
        "deleted": "Удалено.",
        "write_author": "✉️ Написать автору",
        "delete": "🗑 Удалить",
        "ask_msg": "Напишите сообщение автору — я перешлю его. Помните: никогда не платите заранее.",
        "msg_sent": "Отправил автору. Ответ придёт сюда.",
        "msg_in": "Сообщение по вашему объявлению «{title}»:\n\n{text}",
        "reply": "↩️ Ответить",
        "limit": "На сегодня лимит ИИ-действий исчерпан ({n}). Поиск и просмотр работают без ограничений. До завтра!",
        "no_ai": "(ИИ сейчас недоступен — карточка собрана из вашего текста как есть.)",
        "safety": "⚠️ Никогда не платите заранее и не называйте коды из СМС.",
        "scam_rules": "Признаки, которые я нашёл:",
        "scam_none": "Явных признаков обмана не нашёл, но будьте осторожны: встречайтесь лично и не платите заранее.",
        "next_door": "Получилось! Ещё можно: {doors}",
    },
    "en": {
        "hello": ("Hi! I'm the AI assistant of AIbazari — free listings for everyone.\n"
                  "Where shall we start?"),
        "door_sell": "📸 Sell by photo",
        "door_give": "🤝 Give away / ask for help",
        "door_scam": "🛡 Is this a scam?",
        "ask_photo": "Send a photo of the item. Put price and city in the caption — I'll write the rest.",
        "ask_give": "In one message: what you give away or what help you need, and your city.",
        "ask_scam": "Forward me the suspicious message (or paste the text) — I'll explain the warning signs.",
        "card_ready": "Here is the card. Publish it?",
        "publish": "✅ Publish",
        "redo": "✏️ Start over",
        "published": "Published! Search: /find word. My listings: /my",
        "cancelled": "OK, let's start over.",
        "nothing": "Nothing found. Try another word.",
        "find_usage": "Type: /find bicycle",
        "my_empty": "You have no listings yet.",
        "deleted": "Deleted.",
        "write_author": "✉️ Write to the author",
        "delete": "🗑 Delete",
        "ask_msg": "Write your message to the author — I'll forward it. Remember: never pay in advance.",
        "msg_sent": "Sent to the author. The reply will come here.",
        "msg_in": "Message about your listing \"{title}\":\n\n{text}",
        "reply": "↩️ Reply",
        "limit": "Today's AI limit is used up ({n}). Search and browsing stay unlimited. See you tomorrow!",
        "no_ai": "(AI is unavailable right now — the card is made from your text as is.)",
        "safety": "⚠️ Never pay in advance and never share SMS codes.",
        "scam_rules": "Warning signs I found:",
        "scam_none": "No obvious scam signs, but stay careful: meet in person and never pay in advance.",
        "next_door": "Done! You can also: {doors}",
    },
}


def lang(code: str | None) -> str:
    return "ru" if (code or "").lower().startswith(("ru", "uk", "be", "kk")) else "en"


def t(lg: str, key: str, **kw) -> str:
    s = T.get(lg, T["en"]).get(key) or T["en"][key]
    return s.format(**kw) if kw else s
