"""Free, AI-less first pass of the "is this a scam?" door: classic warning signs by regex."""
import re

SIGNS = [
    (r"предоплат|аванс|переведите|перевод на карту|prepay|advance payment|pay (first|upfront)|wire",
     {"ru": "просят заплатить заранее", "en": "asks you to pay in advance"}),
    (r"код из смс|код из sms|скажите код|sms code|verification code|one[- ]time code",
     {"ru": "просят код из СМС — это ключ к вашему банку", "en": "asks for an SMS code — it is the key to your bank"}),
    (r"https?://|bit\.ly|t\.me/\S+|wa\.me",
     {"ru": "есть ссылка — не вводите на ней карту и пароли", "en": "contains a link — never enter card or passwords there"}),
    (r"доставк\w* (через|по) (сайт|ссылк)|безопасн\w* сделк|courier link|safe deal",
     {"ru": "«безопасная сделка» или доставка по ссылке — частая схема", "en": "\"safe deal\" or delivery by link — a common scheme"}),
    (r"срочно|только сегодня|последний шанс|urgent|today only|last chance",
     {"ru": "торопят — мошенники не дают подумать", "en": "pressure to hurry — scammers don't let you think"}),
    (r"служба безопасности|сотрудник банка|ваша карта заблокирован|bank security|your card (is )?blocked",
     {"ru": "называют себя банком — банк так не пишет", "en": "pretends to be your bank — banks don't write like this"}),
    (r"выигр|приз|подарок за|you won|prize|giveaway",
     {"ru": "обещают выигрыш или подарок", "en": "promises a prize or a gift"}),
    (r"номер карты|cvv|cvc|card number|срок действия карты",
     {"ru": "просят данные карты", "en": "asks for card details"}),
]


def check(text: str, lg: str) -> list[str]:
    low = (text or "").lower()
    return [d.get(lg, d["en"]) for pat, d in SIGNS if re.search(pat, low)]
