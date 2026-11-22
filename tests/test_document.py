import fitz
from folio.document import PDFDocument
from folio.export import export_annotated_pdf
from folio.storage import Library


def sample_pdf(path):
    doc = fitz.open()
    for number in range(1, 4):
        page = doc.new_page(width=300, height=400)
        page.insert_text((40, 60), f"Page {number} quantum computing foundations", fontsize=12)
    doc.set_metadata({"title": "Tiny Test Book", "author": "Folio"})
    doc.save(str(path))
    doc.close()


def test_pdf_open_search_render(tmp_path):
    path = tmp_path / "hello.pdf"
    sample_pdf(path)
    doc = PDFDocument(str(path))
    assert doc.title == "Tiny Test Book"
    assert doc.author == "Folio"
    assert doc.pages == 3
    assert doc.size(0) == (300, 400)
    assert doc.words(0)
    assert doc.find("quantum", 2)[0] == 2
    assert doc.find("notfound") is None
    pix = doc.render(1, .9)
    assert pix.width == 270
    doc.close()


def test_round_trip_annotated_pdf(tmp_path):
    path = tmp_path / "hello.pdf"
    sample_pdf(path)
    store = Library(tmp_path / "lib.sqlite3")
    store.upsert_book(path, "Tiny Test Book", "Folio", 3)
    store.annotation_add(path, 0, "ink", {"points": [[20, 25], [35, 40], [70, 65]], "width": 2.0})
    store.annotation_add(path, 0, "highlight", {"rects": [[40, 45, 155, 65]], "text": "Page 1"})
    store.annotation_add(path, 1, "note", {"position": [44, 51], "text": "Remember this"})
    result = tmp_path / "export.pdf"
    assert export_annotated_pdf(path, result, store) == 3
    original = fitz.open(path)
    target = fitz.open(result)
    assert list(original[0].annots() or []) == []
    assert len(list(target[0].annots() or [])) == 2
    assert len(list(target[1].annots() or [])) == 1
    target.close()
    original.close()
    store.close()
