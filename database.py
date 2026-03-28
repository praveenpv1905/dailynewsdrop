"""
database.py — DailyNewsDrop SQLite layer
"""
import sqlite3, json
from datetime import datetime
from config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS seen_urls (
            url      TEXT PRIMARY KEY,
            title    TEXT,
            source   TEXT,
            seen_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS posts (
            id              TEXT PRIMARY KEY,
            article_url     TEXT,
            headline        TEXT,
            subline         TEXT,
            caption         TEXT,
            keywords        TEXT,
            category        TEXT,
            image_path      TEXT,
            post_image_path TEXT,
            status          TEXT DEFAULT 'pending',
            created_at      TEXT DEFAULT (datetime('now')),
            decided_at      TEXT,
            error_msg       TEXT
        );

        CREATE TABLE IF NOT EXISTS digest (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at       TEXT DEFAULT (datetime('now')),
            articles      TEXT,
            articles_full TEXT,
            thread_id     TEXT
        );
        """)
        # Migration: add articles_full column if it doesn't exist yet
        try:
            c.execute("ALTER TABLE digest ADD COLUMN articles_full TEXT")
        except Exception:
            pass  # column already exists


def url_seen(url: str) -> bool:
    with _conn() as c:
        return c.execute("SELECT 1 FROM seen_urls WHERE url=?", (url,)).fetchone() is not None


def mark_url(url: str, title: str, source: str):
    with _conn() as c:
        try:
            c.execute("INSERT INTO seen_urls(url,title,source) VALUES(?,?,?)",
                      (url, title, source))
        except sqlite3.IntegrityError:
            pass


def save_post(p: dict):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO posts
              (id, article_url, headline, subline, caption, keywords, category,
               image_path, post_image_path, status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            p["id"], p.get("article_url"), p.get("headline"), p.get("subline"),
            p.get("caption"), json.dumps(p.get("keywords", [])), p.get("category"),
            p.get("image_path"), p.get("post_image_path"), p.get("status", "pending")
        ))


def get_post(pid: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
        if row:
            d = dict(row)
            d["keywords"] = json.loads(d.get("keywords") or "[]")
            return d
    return None


def update_status(pid: str, status: str, **kw):
    fields = {"status": status, "decided_at": datetime.now().isoformat()}
    fields.update(kw)
    sets = ", ".join(f"{k}=?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE posts SET {sets} WHERE id=?",
                  list(fields.values()) + [pid])


def save_digest(articles: list, thread_id: str = "", articles_full: list = None):
    """Save digest. articles_full stores complete article data for restart recovery."""
    with _conn() as c:
        c.execute(
            "INSERT INTO digest(articles, articles_full, thread_id) VALUES(?,?,?)",
            (json.dumps(articles),
             json.dumps(articles_full or []),
             thread_id)
        )


def get_last_digest() -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM digest ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            d = dict(row)
            d["articles"]      = json.loads(d.get("articles")      or "[]")
            d["articles_full"] = json.loads(d.get("articles_full") or "[]")
            return d
    return None


# Initialise on import
init_db()
