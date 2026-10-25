"""SQLite storage: listings, per-user daily AI usage, daily AI spend. Path from env AIBAZARI_DB."""
import os
import sqlite3
import time
from contextlib import contextmanager

DB = os.environ.get("AIBAZARI_DB", "/opt/aibazari/data/aibazari.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings(
  id INTEGER PRIMARY KEY, user_id INTEGER, kind TEXT, title TEXT, body TEXT,
  price TEXT, city TEXT, photo TEXT, lang TEXT, created INTEGER, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS usage(user_id INTEGER, day TEXT, n INTEGER, PRIMARY KEY(user_id, day));
CREATE TABLE IF NOT EXISTS spend(day TEXT PRIMARY KEY, usd REAL);
CREATE TABLE IF NOT EXISTS trusted(user_id INTEGER PRIMARY KEY);
"""


@contextmanager
def conn():
    """Commit on success and always close: sqlite3's own context manager leaves the file open."""
    if os.path.dirname(DB):
        os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.create_function("ulower", 1, lambda s: s.lower() if isinstance(s, str) else s)  # SQLite lower() is ASCII-only
    c.executescript(SCHEMA)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def add_listing(user_id: int, card: dict, kind: str, photo: str | None, lg: str) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO listings(user_id,kind,title,body,price,city,photo,lang,created) VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, kind, card.get("title", ""), card.get("body", ""), card.get("price", ""),
             card.get("city", ""), photo, lg, int(time.time())))
        return cur.lastrowid


def get_listing(lid: int):
    with conn() as c:
        return c.execute("SELECT * FROM listings WHERE id=? AND active=1", (lid,)).fetchone()


def find(word: str, limit: int = 10) -> list:
    q = f"%{word.strip().lower()}%"
    with conn() as c:
        return c.execute(
            "SELECT * FROM listings WHERE active=1 AND (ulower(title) LIKE ? OR ulower(body) LIKE ? OR ulower(city) LIKE ?)"
            " ORDER BY id DESC LIMIT ?", (q, q, q, limit)).fetchall()


def my(user_id: int) -> list:
    with conn() as c:
        return c.execute("SELECT * FROM listings WHERE active=1 AND user_id=? ORDER BY id DESC", (user_id,)).fetchall()


def delete(lid: int, user_id: int) -> bool:
    with conn() as c:
        return c.execute("UPDATE listings SET active=0 WHERE id=? AND user_id=?", (lid, user_id)).rowcount > 0


def used(user_id: int) -> int:
    with conn() as c:
        r = c.execute("SELECT n FROM usage WHERE user_id=? AND day=?", (user_id, today())).fetchone()
        return r["n"] if r else 0


def count_use(user_id: int) -> None:
    with conn() as c:
        c.execute("INSERT INTO usage VALUES(?,?,1) ON CONFLICT(user_id,day) DO UPDATE SET n=n+1", (user_id, today()))


def is_trusted(user_id: int) -> bool:
    with conn() as c:
        return c.execute("SELECT 1 FROM trusted WHERE user_id=?", (user_id,)).fetchone() is not None


def spent_today() -> float:
    with conn() as c:
        r = c.execute("SELECT usd FROM spend WHERE day=?", (today(),)).fetchone()
        return r["usd"] if r else 0.0


def add_spend(usd: float) -> None:
    with conn() as c:
        c.execute("INSERT INTO spend VALUES(?,?) ON CONFLICT(day) DO UPDATE SET usd=usd+?", (today(), usd, usd))
