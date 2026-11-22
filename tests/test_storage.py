from pathlib import Path
from folio.storage import Library
from folio.models import book_key, clamp, page_label


def test_book_progress_and_preferences(tmp_path):
    db = Library(tmp_path / "data.sqlite3")
    book = tmp_path / "book.pdf"
    book.write_bytes(b"%PDF-placeholder")
    db.upsert_book(book, "Foundations", "Reader", 120)
    db.set_state(book, current_page=64, theme="sepia", layout="spread", zoom=1.25)
    row = db.reading_state(book)
    assert row["current_page"] == 64
    assert row["layout"] == "spread"
    assert db.books(search="Foundations")[0].title == "Foundations"
    assert len(db.books(search="something else")) == 0
    db.close()


def test_annotation_and_bookmark(tmp_path):
    db = Library(tmp_path / "data.sqlite3")
    path = tmp_path / "a.pdf"
    db.upsert_book(path, "Book", "", 10)
    ident = db.annotation_add(path, 2, "ink", {"points": [[2,3],[4,5]], "color": "#123456"})
    assert db.annotations(path, 2)[0]["payload"]["points"][1] == [4, 5]
    assert len(db.annotations(path, 1)) == 0
    db.annotation_delete(ident)
    assert db.annotations(path) == []
    assert db.bookmark_toggle(path, 2)
    assert db.bookmarks(path)[0]["page"] == 2
    assert not db.bookmark_toggle(path, 2)
    db.close()


def test_helpers(tmp_path):
    assert book_key(tmp_path / "a.pdf") == book_key(tmp_path / "a.pdf")
    assert clamp(-2, 0, 100) == 0
    assert page_label(0, 0) == "0 / 0"
    assert page_label(5, 10) == "6 / 10"
