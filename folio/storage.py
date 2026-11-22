"""Local-first SQLite library, preferences and independent PDF annotations."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from .models import Book, normalize_pdf_path


def data_directory() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local" / "share") / "folio-linux"


class Library:
    """Only stores book metadata/annotations; original PDFs are never modified."""

    def __init__(self, database: str | Path | None = None):
        self.database = Path(database) if database else data_directory() / "library.sqlite3"
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.database), timeout=10)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self):
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                path TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL DEFAULT '',
                pages INTEGER NOT NULL DEFAULT 0, current_page INTEGER NOT NULL DEFAULT 0,
                last_opened TEXT NOT NULL DEFAULT '', is_favorite INTEGER NOT NULL DEFAULT 0,
                layout TEXT NOT NULL DEFAULT 'single', zoom REAL NOT NULL DEFAULT 1.0,
                theme TEXT NOT NULL DEFAULT 'paper', brightness INTEGER NOT NULL DEFAULT 100
            );
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT NOT NULL,
                page INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_annotations_page ON annotations(path, page);
            CREATE TABLE IF NOT EXISTS bookmarks (
                path TEXT NOT NULL, page INTEGER NOT NULL, title TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (path, page)
            );
        """)
        columns = {r[1] for r in self.con.execute("PRAGMA table_info(books)")}
        if "brightness" not in columns:
            self.con.execute("ALTER TABLE books ADD COLUMN brightness INTEGER NOT NULL DEFAULT 100")
        self.con.commit()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def upsert_book(self, path: str | Path, title: str, author: str, pages: int) -> None:
        path = normalize_pdf_path(path)
        with self.con:
            self.con.execute("""
                INSERT INTO books(path,title,author,pages,current_page,last_opened)
                VALUES(?,?,?,?,0,?)
                ON CONFLICT(path) DO UPDATE SET title=excluded.title,
                    author=excluded.author, pages=excluded.pages, last_opened=excluded.last_opened
            """, (path, title, author, pages, self.now()))

    def books(self, search: str = "", favorite: bool = False) -> list[Book]:
        query = "SELECT * FROM books WHERE (title LIKE ? OR author LIKE ? OR path LIKE ?)"
        if favorite:
            query += " AND is_favorite=1"
        query += " ORDER BY last_opened DESC"
        term = f"%{search}%"
        return [Book(r["path"], r["title"], r["author"], r["pages"],
                     r["current_page"], r["last_opened"], bool(r["is_favorite"]))
                for r in self.con.execute(query, (term, term, term)).fetchall()]

    def get_book(self, path: str | Path) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM books WHERE path=?", (normalize_pdf_path(path),)).fetchone()

    def reading_state(self, path: str | Path) -> dict:
        row = self.get_book(path)
        return dict(row) if row else {"current_page": 0, "layout": "single", "zoom": 1.0, "theme": "paper", "brightness": 100}

    def set_state(self, path: str | Path, **updates):
        allowed = {"current_page", "layout", "zoom", "theme", "brightness", "last_opened", "is_favorite"}
        clean = {k: v for k, v in updates.items() if k in allowed}
        if not clean:
            return
        fields = ", ".join(f"{k}=?" for k in clean)
        with self.con:
            self.con.execute(f"UPDATE books SET {fields} WHERE path=?",
                             (*clean.values(), normalize_pdf_path(path)))

    def annotation_add(self, path: str | Path, page: int, kind: str, payload: dict) -> int:
        with self.con:
            c = self.con.execute("INSERT INTO annotations(path,page,kind,payload) VALUES(?,?,?,?)",
                                 (normalize_pdf_path(path), page, kind, json.dumps(payload)))
            return c.lastrowid

    def annotations(self, path: str | Path, page: int | None = None) -> list[dict]:
        args: tuple = (normalize_pdf_path(path),)
        query = "SELECT * FROM annotations WHERE path=?"
        if page is not None:
            query += " AND page=?"
            args += (page,)
        query += " ORDER BY id ASC"
        rows = self.con.execute(query, args)
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def annotation_delete(self, identifier: int) -> None:
        with self.con:
            self.con.execute("DELETE FROM annotations WHERE id=?", (identifier,))

    def bookmark_toggle(self, path: str | Path, page: int, title: str = "") -> bool:
        path = normalize_pdf_path(path)
        old = self.con.execute("SELECT 1 FROM bookmarks WHERE path=? AND page=?", (path, page)).fetchone()
        with self.con:
            if old:
                self.con.execute("DELETE FROM bookmarks WHERE path=? AND page=?", (path, page))
            else:
                self.con.execute("INSERT INTO bookmarks(path,page,title) VALUES(?,?,?)", (path, page, title))
        return not bool(old)

    def bookmarks(self, path: str | Path) -> list[dict]:
        return [dict(r) for r in self.con.execute(
            "SELECT * FROM bookmarks WHERE path=? ORDER BY page", (normalize_pdf_path(path),))]

    def close(self):
        self.con.close()
