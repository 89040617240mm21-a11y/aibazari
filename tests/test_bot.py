import os
import sys

os.environ["AIBAZARI_DB"] = os.path.join(os.path.dirname(__file__), "test.db")
os.environ.pop("ANTHROPIC_API_KEYS", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))

import pytest  # noqa: E402

import ai  # noqa: E402
import doors  # noqa: E402
import scam  # noqa: E402
import store  # noqa: E402
from texts import lang, t  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(store.DB):
        os.remove(store.DB)
    yield
    if os.path.exists(store.DB):
        os.remove(store.DB)


def test_listing_roundtrip():
    lid = store.add_listing(1, {"title": "Велосипед", "body": "Синий", "price": "5000", "city": "Тбилиси"},
                            "sell", None, "ru")
    assert store.find("велос")[0]["id"] == lid
    assert store.find("тбилиси")
    assert not store.delete(lid, 2)
    assert store.delete(lid, 1)
    assert not store.find("велос")


def test_daily_limit():
    for _ in range(doors.LIMIT):
        store.count_use(7)
    assert doors.can_ai(7) == (False, doors.LIMIT)
    with store.conn() as c:
        c.execute("INSERT INTO trusted VALUES(7)")
    assert doors.can_ai(7) == (True, doors.LIMIT_TRUSTED)


def test_budget_brake():
    assert ai.pick(ai.SMART) == ai.SMART
    store.add_spend(ai.DAILY + 0.01)
    assert ai.pick(ai.SMART) == ai.CHEAP
    store.add_spend(ai.DAILY)
    assert ai.pick(ai.SMART) is None


def test_no_keys_means_no_ai():
    assert ai.make_card("Отдам кота", "ru") is None


def test_parse_card():
    assert ai.parse_card('ok {"title": "Стол", "body": "Дуб", "price": 100}')["price"] == "100"
    assert ai.parse_card("not json") is None


def test_scam_signs():
    s = scam.check("Срочно! Внесите предоплату по ссылке https://x.ru и скажите код из СМС", "ru")
    assert len(s) >= 4
    assert scam.check("Привет, вещь ещё продаётся?", "ru") == []


def test_reply_signature():
    assert doors.sign(5, 9, 6) == doors.sign(5, 9, 6)
    assert doors.sign(5, 9, 6) != doors.sign(5, 9, 7)


def test_texts():
    assert lang("ru-RU") == "ru" and lang("de") == "en" and lang(None) == "en"
    assert "50" in t("en", "limit", n=50)
    assert set(t.__globals__["T"]["ru"]) == set(t.__globals__["T"]["en"])
