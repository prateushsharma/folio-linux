"""Thin PyMuPDF document adapter; the reader renders on demand only."""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
import fitz


class PDFDocument:
    def __init__(self, filename: str):
        self.path = str(Path(filename).expanduser().resolve())
        self.pdf = fitz.open(self.path)
        if self.pdf.needs_pass:
            self.pdf.close()
            raise ValueError("Password-protected PDFs are not supported in this release.")
        if not self.pdf.is_pdf:
            self.pdf.close()
            raise ValueError("This is not a PDF document.")
        self.pages = self.pdf.page_count
        if not self.pages:
            self.pdf.close()
            raise ValueError("The PDF contains no pages.")
        metadata = self.pdf.metadata or {}
        self.title = (metadata.get("title") or "").strip() or Path(self.path).stem.replace("_", " ")
        self.author = (metadata.get("author") or "").strip()
        self._word_cache: OrderedDict[int, list] = OrderedDict()
        self._size_cache: dict[int, tuple[float, float]] = {}

    def size(self, index: int) -> tuple[float, float]:
        if index not in self._size_cache:
            rect = self.pdf.load_page(index).rect
            self._size_cache[index] = (rect.width, rect.height)
        return self._size_cache[index]

    def render(self, index: int, scale: float):
        return self.pdf.load_page(index).get_pixmap(
            matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)

    def words(self, index: int) -> list:
        if index not in self._word_cache:
            self._word_cache[index] = self.pdf.load_page(index).get_text("words", sort=True)
            if len(self._word_cache) > 8:
                self._word_cache.popitem(last=False)
        else:
            self._word_cache.move_to_end(index)
        return self._word_cache[index]

    def outline(self) -> list[tuple[int, str, int]]:
        return [(level, title, page - 1) for level, title, page in self.pdf.get_toc() if 1 <= page <= self.pages]

    def find(self, text: str, from_page: int = 0) -> tuple[int, list[tuple]] | None:
        if not text.strip():
            return None
        # Search forward, wrapping once. Query comes from the local user.
        for offset in range(self.pages):
            i = (from_page + offset) % self.pages
            found = self.pdf.load_page(i).search_for(text.strip())[:30]
            if found:
                return i, [(r.x0, r.y0, r.x1, r.y1) for r in found]
        return None

    def close(self):
        self._word_cache.clear()
        self.pdf.close()
