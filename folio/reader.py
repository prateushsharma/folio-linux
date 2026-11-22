"""Virtualized PDF canvas: single-page, facing pages and continuous scrolling.

Never creates one Qt widget per PDF page, and keeps only a bounded image cache.
Annotations are kept in separate SQLite storage and painted non-destructively.
"""
from __future__ import annotations
from collections import OrderedDict
import math
from typing import Optional
from PySide6.QtCore import Qt, QRectF, QPoint, QPointF, Signal, QTimer
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QImage, QPixmap,
                           QPainterPath, QFont, QCursor)
from PySide6.QtWidgets import QAbstractScrollArea, QMenu, QInputDialog
from .document import PDFDocument
from .storage import Library
from .models import clamp


class PDFCanvas(QAbstractScrollArea):
    page_changed = Signal(int)
    selection_changed = Signal(str)
    request_lookup = Signal(str)
    annotations_changed = Signal()

    def __init__(self, storage: Library, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.document: Optional[PDFDocument] = None
        self.page = 0
        self.layout = "single"
        self.fit_mode = "page"
        self.zoom = 1.0
        self.theme = "paper"
        self.brightness = 100
        self.tool = "select"
        self.ink_color = "#c6784c"
        self.ink_width = 2.2
        self._cache: OrderedDict[tuple, tuple[QImage, int]] = OrderedDict()
        self._cache_bytes = 0
        self._cache_max = 64 * 1024 * 1024
        self._rects: dict[int, QRectF] = {}
        self._total_height = 0.0
        self._total_width = 0.0
        self._scale = 1.0
        self._selection_start = None
        self._selection_end = None
        self._selected_words: list[tuple[int, tuple]] = []
        self._search_hits: dict[int, list[tuple]] = {}
        self._drawing_page = None
        self._stroke: list[list[float]] = []
        self._panning = None
        self._annotation_cache: dict[int, list[dict]] = {}
        self._relayout_pending = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFrameShape(self.Shape.NoFrame)
        self.viewport().setAutoFillBackground(False)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.horizontalScrollBar().valueChanged.connect(lambda _: self.viewport().update())

    def set_document(self, doc: PDFDocument, initial_page=0, layout="single", zoom=1.0, theme="paper"):
        self.document = doc
        self.page = max(0, min(doc.pages - 1, int(initial_page)))
        self.layout = layout if layout in ("single", "spread", "continuous") else "single"
        self.zoom = float(clamp(zoom, 0.5, 3.0))
        self.theme = theme if theme in ("paper", "white", "sepia", "dark") else "paper"
        self._cache_clear()
        self._annotation_cache.clear()
        self._search_hits.clear()
        self._selected_words = []
        self._relayout()
        if self.layout == "continuous":
            self._scroll_to_page(self.page)
        self.viewport().update()
        self.page_changed.emit(self.page)

    def close_document(self):
        self.document = None
        self._cache_clear()
        self._annotation_cache.clear()
        self._rects.clear()
        self.viewport().update()

    def _cache_clear(self):
        self._cache.clear()
        self._cache_bytes = 0

    def set_memory_budget(self, mebibytes: int):
        self._cache_max = max(16, min(256, mebibytes)) * 1024 * 1024
        self._trim_cache()

    def _trim_cache(self):
        while self._cache_bytes > self._cache_max and len(self._cache) > 1:
            _, (_, size) = self._cache.popitem(last=False)
            self._cache_bytes -= size

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def set_layout(self, mode: str):
        if mode not in ("single", "spread", "continuous"):
            return
        self.layout = mode
        self._relayout()
        if mode == "continuous":
            self._scroll_to_page(self.page)
        self.viewport().update()

    def set_zoom(self, zoom: float):
        self.zoom = float(clamp(zoom, 0.5, 3.0))
        self._relayout()
        if self.layout == "continuous":
            self._scroll_to_page(self.page)
        self.viewport().update()

    def set_fit_mode(self, mode: str):
        self.fit_mode = mode
        self._relayout()
        self.viewport().update()

    def set_theme(self, theme: str):
        if theme not in ("white", "paper", "sepia", "dark"):
            return
        self.theme = theme
        self._cache_clear()
        self.viewport().update()

    def set_brightness(self, brightness: int):
        self.brightness = int(clamp(brightness, 30, 100))
        self.viewport().update()

    def set_tool(self, name: str):
        self.tool = name
        self._selected_words = []
        self._selection_start = self._selection_end = None
        self.viewport().setCursor({
            "hand": Qt.OpenHandCursor,
            "pen": Qt.CrossCursor,
            "highlighter": Qt.CrossCursor,
            "eraser": Qt.CrossCursor,
            "select": Qt.IBeamCursor,
        }.get(name, Qt.ArrowCursor))
        self.viewport().update()

    def go_to(self, page: int):
        if not self.document:
            return
        page = max(0, min(self.document.pages - 1, int(page)))
        if page == self.page and self.layout != "continuous":
            return
        changed = self.page != page
        self.page = page
        if self.layout == "continuous":
            self._scroll_to_page(page)
        else:
            self._relayout()
            self.viewport().update()
        if changed:
            self.page_changed.emit(self.page)

    def next_page(self):
        self.go_to(self.page + (2 if self.layout == "spread" else 1))

    def previous_page(self):
        self.go_to(self.page - (2 if self.layout == "spread" else 1))

    def _visible_pages(self):
        if not self.document:
            return []
        if self.layout == "spread":
            # Even-numbered index is the left page in a typical two-page spread.
            first = (self.page // 2) * 2
            return [i for i in (first, first + 1) if i < self.document.pages]
        if self.layout == "single":
            return [self.page]
        return range(self.document.pages)

    def _relayout(self):
        self._rects = {}
        if not self.document:
            return
        vw = max(self.viewport().width(), 300)
        vh = max(self.viewport().height(), 240)
        gap = 26
        pad = 54
        pages = list(self._visible_pages())
        if not pages:
            return
        reference_w, reference_h = self.document.size(pages[0])
        page_columns = 2 if self.layout == "spread" and len(pages) > 1 else 1
        width_per_column = max(100, (vw - 2 * pad - (gap if page_columns == 2 else 0)) / page_columns)
        width_fit = width_per_column / reference_w
        page_fit = min(width_fit, (vh - pad * 1.5) / reference_h)
        self._scale = max(0.1, (page_fit if self.fit_mode == "page" and self.layout != "continuous" else width_fit) * self.zoom)
        if self.layout == "continuous":
            # Cache only layout geometry, not any rendered page pixels.
            y = float(pad)
            max_w = 0.0
            for i in pages:
                w, h = self.document.size(i)
                scaled_w, scaled_h = w * self._scale, h * self._scale
                self._rects[i] = QRectF(0, y, scaled_w, scaled_h)
                max_w = max(max_w, scaled_w)
                y += scaled_h + gap
            content_w = max(vw, max_w + 2 * pad)
            for i, rect in list(self._rects.items()):
                rect.moveLeft((content_w - rect.width()) / 2)
            content_h = y + pad
        else:
            sizes = [self.document.size(i) for i in pages]
            total_w = sum(w * self._scale for w, _ in sizes) + gap * (len(sizes) - 1)
            max_h = max(h * self._scale for _, h in sizes)
            content_w = max(vw, total_w + 2 * pad)
            content_h = max(vh, max_h + 2 * pad)
            x = (content_w - total_w) / 2
            y = (content_h - max_h) / 2
            for i, (w, h) in zip(pages, sizes):
                self._rects[i] = QRectF(x, y, w * self._scale, h * self._scale)
                x += w * self._scale + gap
        self._total_width = content_w
        self._total_height = content_h
        self.horizontalScrollBar().setRange(0, max(0, math.ceil(content_w - vw)))
        self.horizontalScrollBar().setPageStep(vw)
        self.verticalScrollBar().setRange(0, max(0, math.ceil(content_h - vh)))
        self.verticalScrollBar().setPageStep(vh)
        if self.layout != "continuous":
            self.horizontalScrollBar().setValue(0)
            self.verticalScrollBar().setValue(0)

    def _scroll_to_page(self, index):
        if index in self._rects:
            rect = self._rects[index]
            self.verticalScrollBar().setValue(max(0, int(rect.top() - 30)))
            self.viewport().update()

    def _on_scroll(self, _):
        if not self.document:
            return
        if self.layout == "continuous":
            y = self.verticalScrollBar().value() + self.viewport().height() * .35
            # Binary search on monotonically increasing page top positions.
            low, high = 0, self.document.pages - 1
            while low < high:
                mid = (low + high + 1) // 2
                if self._rects[mid].top() <= y:
                    low = mid
                else:
                    high = mid - 1
            if low != self.page:
                self.page = low
                self.page_changed.emit(low)
        self.viewport().update()

    def _viewport_rect(self, rect: QRectF) -> QRectF:
        return rect.translated(-self.horizontalScrollBar().value(), -self.verticalScrollBar().value())

    def _render_page(self, i: int) -> QImage | None:
        if not self.document:
            return None
        scale = self._scale
        key = (i, round(scale, 4), self.theme)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key][0]
        try:
            pix = self.document.render(i, scale)
            # Copy samples before native Pixmap goes out of scope.
            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride,
                            QImage.Format.Format_RGB888).copy()
            if self.theme == "dark":
                qimage.invertPixels(QImage.InvertMode.InvertRgb)
            size = qimage.sizeInBytes()
        except (RuntimeError, ValueError, MemoryError):
            return None
        self._cache[key] = (qimage, size)
        self._cache_bytes += size
        self._trim_cache()
        return qimage

    def _load_annotations(self, page: int):
        if page not in self._annotation_cache and self.document:
            self._annotation_cache[page] = self.storage.annotations(self.document.path, page)
            if len(self._annotation_cache) > 12:
                oldest = next(iter(self._annotation_cache))
                del self._annotation_cache[oldest]
        return self._annotation_cache.get(page, [])

    def _paint_annotations(self, painter: QPainter, index: int, dest: QRectF):
        for item in self._load_annotations(index):
            payload = item["payload"]
            kind = item["kind"]
            if kind in ("ink", "marker"):
                pts = payload.get("points", [])
                if not pts:
                    continue
                col = QColor(payload.get("color", "#cc7347"))
                if kind == "marker":
                    col.setAlpha(88)
                pen = QPen(col, payload.get("width", 2.0) * self._scale,
                           Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                path = QPainterPath()
                path.moveTo(dest.left() + pts[0][0] * self._scale,
                            dest.top() + pts[0][1] * self._scale)
                for x, y in pts[1:]:
                    path.lineTo(dest.left() + x * self._scale,
                                dest.top() + y * self._scale)
                if len(pts) == 1:
                    path.lineTo(path.currentPosition() + QPointF(.1, .1))
                painter.drawPath(path)
            elif kind == "highlight":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(245, 193, 69, 95))
                for x0, y0, x1, y1 in payload.get("rects", []):
                    painter.drawRect(QRectF(dest.left() + x0 * self._scale,
                                            dest.top() + y0 * self._scale,
                                            (x1-x0) * self._scale, (y1-y0) * self._scale))
            elif kind == "note":
                x, y = payload.get("position", [16, 16])
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#d5a45a"))
                painter.drawRoundedRect(QRectF(dest.left()+x*self._scale, dest.top()+y*self._scale, 15, 15), 4, 4)

    def paintEvent(self, event):
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing, True)
        viewport = self.viewport().rect()
        p.fillRect(viewport, QColor("#191f2a") if self.theme == "dark" else QColor("#e8e5df"))
        if not self.document:
            p.setPen(QColor("#9299a6"))
            p.drawText(viewport, Qt.AlignCenter, "Open a PDF to begin reading")
            return
        for index, rect in self._rects.items():
            dest = self._viewport_rect(rect)
            if not dest.intersects(QRectF(viewport).adjusted(-60, -60, 60, 60)):
                continue
            p.fillRect(dest.translated(0, 6), QColor(0, 0, 0, 20))
            p.fillRect(dest, QColor("#20242a") if self.theme == "dark" else QColor("#ffffff"))
            img = self._render_page(index)
            if img:
                p.drawImage(dest, img)
                if self.theme in ("paper", "sepia"):
                    p.save()
                    p.setCompositionMode(QPainter.CompositionMode_Multiply)
                    p.fillRect(dest, QColor("#f4ebd9") if self.theme == "paper" else QColor("#ead1a6"))
                    p.restore()
            if self.brightness < 100:
                p.fillRect(dest, QColor(0, 0, 0, int((100 - self.brightness) * 1.55)))
            self._paint_annotations(p, index, dest)
            if index in self._search_hits:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(97, 176, 238, 95))
                for x0, y0, x1, y1 in self._search_hits[index]:
                    p.drawRect(QRectF(dest.left()+x0*self._scale, dest.top()+y0*self._scale,
                                      (x1-x0)*self._scale, (y1-y0)*self._scale))
            if self._selected_words:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(82, 146, 232, 92))
                for k, w in self._selected_words:
                    if k == index:
                        x0, y0, x1, y1 = w[:4]
                        p.drawRect(QRectF(dest.left()+x0*self._scale,
                                          dest.top()+y0*self._scale,
                                          (x1-x0)*self._scale, (y1-y0)*self._scale))
            if self._drawing_page == index and self._stroke:
                painter_path = QPainterPath()
                painter_path.moveTo(dest.left()+self._stroke[0][0]*self._scale,
                                    dest.top()+self._stroke[0][1]*self._scale)
                for x, y in self._stroke[1:]:
                    painter_path.lineTo(dest.left()+x*self._scale, dest.top()+y*self._scale)
                color = QColor(self.ink_color)
                if self.tool == "highlighter":
                    color.setAlpha(95)
                p.setPen(QPen(color, self.ink_width*self._scale if self.tool == "pen" else 11*self._scale,
                              Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPath(painter_path)
        p.end()

    def _hit(self, pos: QPoint):
        canvas_pos = QPointF(pos) + QPointF(self.horizontalScrollBar().value(), self.verticalScrollBar().value())
        for i, rect in self._rects.items():
            if rect.contains(canvas_pos):
                return i, [(canvas_pos.x()-rect.left())/self._scale,
                           (canvas_pos.y()-rect.top())/self._scale]
        return None

    def mousePressEvent(self, event):
        if not self.document or event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        hit = self._hit(event.position().toPoint())
        if self.tool == "hand":
            self._panning = (event.position().toPoint(), self.horizontalScrollBar().value(),
                             self.verticalScrollBar().value())
            self.viewport().setCursor(Qt.ClosedHandCursor)
        elif hit and self.tool in ("pen", "highlighter"):
            self._drawing_page, point = hit
            self._stroke = [point]
        elif hit and self.tool == "eraser":
            self._erase_near(*hit)
        elif hit and self.tool == "select":
            self._selection_start = hit
            self._selection_end = hit
            self._selected_words = []
            self.viewport().update()

    def mouseMoveEvent(self, event):
        if self._panning:
            start, sx, sy = self._panning
            delta = event.position().toPoint() - start
            self.horizontalScrollBar().setValue(sx - delta.x())
            self.verticalScrollBar().setValue(sy - delta.y())
        elif self._drawing_page is not None:
            hit = self._hit(event.position().toPoint())
            if hit and hit[0] == self._drawing_page:
                self._stroke.append(hit[1])
                self.viewport().update()
        elif self._selection_start:
            self._selection_end = self._hit(event.position().toPoint())
            self._update_text_selection()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = None
            self.viewport().setCursor(Qt.OpenHandCursor)
        elif self._drawing_page is not None and self._stroke and self.document:
            kind = "marker" if self.tool == "highlighter" else "ink"
            self.storage.annotation_add(self.document.path, self._drawing_page, kind,
                                        {"points": self._stroke, "color": self.ink_color if kind == "ink" else "#ffcb52",
                                         "width": self.ink_width if kind == "ink" else 11.0})
            self._annotation_cache.pop(self._drawing_page, None)
            self._drawing_page = None
            self._stroke = []
            self.annotations_changed.emit()
            self.viewport().update()
        elif self._selection_start:
            self._update_text_selection()
            self._selection_start = self._selection_end = None
            selected = self.selected_text()
            if selected:
                self.selection_changed.emit(selected)
                self._selection_menu(event.globalPosition().toPoint())
        super().mouseReleaseEvent(event)

    def _update_text_selection(self):
        if not self._selection_start or not self._selection_end or not self.document:
            return
        (start_page, p1), (end_page, p2) = self._selection_start, self._selection_end
        if start_page != end_page:
            return
        x0, x1 = sorted((p1[0], p2[0]))
        y0, y1 = sorted((p1[1], p2[1]))
        if abs(x1-x0) < 3 and abs(y1-y0) < 3:
            self._selected_words = []
            return
        # Multi-line selection uses reading-order endpoints, rather than a huge rectangle.
        words = self.document.words(start_page)
        start_index = end_index = None
        for index, w in enumerate(words):
            if start_index is None and w[2] >= min(p1[0], p2[0]) and w[3] >= min(p1[1], p2[1]):
                start_index = index
            if w[0] <= max(p1[0], p2[0]) and w[1] <= max(p1[1], p2[1]):
                end_index = index
        if start_index is None or end_index is None:
            self._selected_words = []
        else:
            lo, hi = sorted((start_index, end_index))
            self._selected_words = [(start_page, w) for w in words[lo:hi+1]]
        self.viewport().update()

    def selected_text(self) -> str:
        # Join selected tokens with spaces; preserves useful copy/search behavior.
        return " ".join(str(w[4]) for _, w in self._selected_words)

    def _selection_menu(self, screen_pos):
        menu = QMenu(self)
        copy = menu.addAction("Copy text")
        highlight = menu.addAction("Highlight selection")
        lookup = menu.addAction("Search & explain in sidebar")
        note = menu.addAction("Attach note")
        result = menu.exec(screen_pos)
        if result == copy:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(self.selected_text())
        elif result == highlight:
            self.highlight_selection()
        elif result == lookup:
            self.request_lookup.emit(self.selected_text())
        elif result == note:
            self.note_on_selection()

    def highlight_selection(self):
        if not self.document or not self._selected_words:
            return
        page = self._selected_words[0][0]
        rectangles = [list(map(float, w[:4])) for _, w in self._selected_words]
        self.storage.annotation_add(self.document.path, page, "highlight",
                                    {"rects": rectangles, "text": self.selected_text()})
        self._annotation_cache.pop(page, None)
        self.annotations_changed.emit()
        self.viewport().update()

    def note_on_selection(self):
        if not self.document or not self._selected_words:
            return
        text, ok = QInputDialog.getMultiLineText(self, "Add note", "Your note:")
        if ok and text.strip():
            page, word = self._selected_words[0]
            self.storage.annotation_add(self.document.path, page, "note",
                                        {"position": list(word[:2]), "text": text.strip(),
                                         "quote": self.selected_text()[:500]})
            self._annotation_cache.pop(page, None)
            self.annotations_changed.emit()
            self.viewport().update()

    def _erase_near(self, page: int, point: list[float]):
        if not self.document:
            return
        x, y = point
        for item in reversed(self._load_annotations(page)):
            if item["kind"] not in ("ink", "marker"):
                continue
            pts = item["payload"].get("points", [])
            if any((a-x)**2+(b-y)**2 < 100 for a,b in pts):
                self.storage.annotation_delete(item["id"])
                self._annotation_cache.pop(page, None)
                self.annotations_changed.emit()
                self.viewport().update()
                return

    def find_text(self, text: str) -> bool:
        if not self.document or not text.strip():
            return False
        result = self.document.find(text, self.page)
        self._search_hits = {}
        if not result:
            self.viewport().update()
            return False
        page, hits = result
        self._search_hits[page] = hits
        self.go_to(page)
        self.viewport().update()
        return True

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.set_zoom(self.zoom + (0.1 if event.angleDelta().y() > 0 else -0.1))
            event.accept()
            return
        if self.layout != "continuous" and not (event.modifiers() & Qt.ShiftModifier):
            if event.angleDelta().y() < 0:
                self.next_page()
            elif event.angleDelta().y() > 0:
                self.previous_page()
            event.accept()
            return
        super().wheelEvent(event)
