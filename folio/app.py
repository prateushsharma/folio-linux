"""Folio-Linux desktop shell: beautiful home, direct-open, tabs, reader and research."""
from __future__ import annotations
import argparse
import json
import os
import hashlib
from pathlib import Path
import sys
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, Signal, QSettings, QUrl
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import (QColor, QFont, QKeySequence, QPainter, QLinearGradient,
                           QBrush, QDesktopServices, QShortcut)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QLineEdit, QFileDialog, QMessageBox, QStackedWidget,
    QTabBar, QProgressBar, QComboBox, QSlider, QListWidget, QTreeWidget,
    QTreeWidgetItem, QMenu, QWidgetAction, QInputDialog, QColorDialog,
    QSizePolicy, QGridLayout, QSpacerItem
)

from .document import PDFDocument
from .export import export_annotated_pdf
from .models import page_label
from .reader import PDFCanvas
from .storage import Library
from .style import STYLE


PALETTE = [("#2d6571", "#1a3d50"), ("#a16d5f", "#734449"),
           ("#72779c", "#42466c"), ("#6b8c79", "#345b4d"),
           ("#c18b56", "#855a43"), ("#497998", "#2a4e73")]


def colored_cover(title: str):
    index = hashlib.sha1(title.encode("utf-8")).digest()[0] % len(PALETTE)
    return PALETTE[index]


def set_active(button: QPushButton, selected: bool):
    button.setProperty("active", "true" if selected else "false")
    button.style().unpolish(button)
    button.style().polish(button)
    button.update()


def create_button(text, css_id="IconButton", tip=None, action=None):
    btn = QPushButton(text)
    btn.setObjectName(css_id)
    btn.setCursor(Qt.PointingHandCursor)
    if tip:
        btn.setToolTip(tip)
    if action:
        btn.clicked.connect(action)
    return btn


class BookCover(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.colors = colored_cover(title)
        self.setMinimumHeight(158)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3, 1, -3, -1)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0, QColor(self.colors[0]))
        grad.setColorAt(1, QColor(self.colors[1]))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(r, 10, 10)
        p.setPen(QColor(255, 255, 255, 37))
        p.drawLine(r.right()-30, r.top()+15, r.right()-30, r.bottom()-15)
        p.drawLine(r.left()+14, r.bottom()-30, r.right()-15, r.bottom()-30)
        p.setPen(QColor("#ffffff"))
        f = QFont("Noto Sans", 12)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        text = self.title if len(self.title) < 50 else self.title[:47] + "…"
        text_rect = r.adjusted(16, 40, -40, -38)
        p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)
        p.setPen(QColor(245, 245, 245, 145))
        f.setPointSize(8)
        f.setWeight(QFont.Normal)
        p.setFont(f)
        p.drawText(r.adjusted(16, 13, -15, -12), Qt.AlignTop, "F O L I O    /    L I B R A R Y")
        p.end()


class BookCard(QFrame):
    clicked = Signal(str)

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book
        self.setObjectName("BookCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(210, 268)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(13, 12, 13, 13)
        lay.setSpacing(8)
        lay.addWidget(BookCover(book.title))
        name = QLabel(book.title)
        name.setObjectName("CardTitle")
        name.setFixedHeight(22)
        name.setToolTip(book.title)
        name.setText(book.title[:27] + ("…" if len(book.title) > 27 else ""))
        lay.addWidget(name)
        sub = QLabel(f"{book.pages} pages  ·  {round(book.current_page / max(1, book.pages) * 100)}% read")
        sub.setObjectName("CardSub")
        lay.addWidget(sub)
        progress = QProgressBar()
        progress.setObjectName("CardProgress")
        progress.setTextVisible(False)
        progress.setRange(0, max(1, book.pages))
        progress.setValue(book.current_page)
        lay.addWidget(progress)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.book.path)
        super().mouseReleaseEvent(event)


class FolioWindow(QMainWindow):
    def __init__(self, open_path=None, initial_page=None):
        super().__init__()
        self.setWindowTitle("Folio-Linux  ·  Read. Annotate. Explore.")
        self.resize(1360, 880)
        self.setMinimumSize(930, 630)
        self.storage = Library()
        self.settings = QSettings("FolioLinux", "Folio")
        self.documents: dict[str, PDFDocument] = {}
        self.current_path: str | None = None
        self._loading_doc = False
        self._closing = False
        self._ui_tool = "select"
        self._build_ui()
        self._shortcuts()
        self._refresh_home()
        self._switch_home()
        if open_path:
            self.open_pdf(open_path, initial_page)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)
        self._build_home()
        self._build_reader()

    def _build_home(self):
        screen = QWidget()
        screen.setObjectName("HomeSurface")
        self.stack.addWidget(screen)
        row = QHBoxLayout(screen)
        row.setSpacing(0)
        row.setContentsMargins(0, 0, 0, 0)
        nav = QFrame()
        nav.setObjectName("Sidebar")
        nav.setFixedWidth(238)
        row.addWidget(nav)
        navbox = QVBoxLayout(nav)
        navbox.setContentsMargins(22, 32, 22, 22)
        navbox.setSpacing(11)
        brand = QLabel("◈  Folio")
        brand.setObjectName("Logo")
        navbox.addWidget(brand)
        tagline = QLabel("READ · ANNOTATE · EXPLORE")
        tagline.setObjectName("LogoSubtitle")
        navbox.addWidget(tagline)
        navbox.addSpacing(35)
        navbox.addWidget(self._sidebar_label("WORKSPACE"))
        self.home_nav_btn = create_button("⌂    Your Library", "SidebarButton", action=self._show_library)
        self.home_nav_btn.setProperty("active", "true")
        navbox.addWidget(self.home_nav_btn)
        fav = create_button("★    Favorites", "SidebarButton", action=lambda: self._refresh_home(favorites=True))
        navbox.addWidget(fav)
        navbox.addSpacing(24)
        navbox.addWidget(self._sidebar_label("QUICK ACTIONS"))
        navbox.addWidget(create_button("＋    Open a PDF", "SidebarButton", action=self.open_file_dialog))
        navbox.addWidget(create_button("▤    Import folder", "SidebarButton", action=self.import_folder))
        navbox.addWidget(create_button("↻    Restore session", "SidebarButton", action=self.restore_session))
        navbox.addStretch()
        label = QLabel("PRIVATE & OFFLINE BY DEFAULT\nYour books stay on your computer.")
        label.setObjectName("LogoSubtitle")
        label.setWordWrap(True)
        navbox.addWidget(label)
        navbox.addSpacing(8)
        navbox.addWidget(create_button("⚙    Preferences", "SidebarButton", action=self.show_preferences))
        self.home_scroll = QScrollArea()
        self.home_scroll.setWidgetResizable(True)
        row.addWidget(self.home_scroll, 1)
        self.home_content = QWidget()
        self.home_scroll.setWidget(self.home_content)
        self.home_v = QVBoxLayout(self.home_content)
        self.home_v.setContentsMargins(50, 37, 50, 42)
        self.home_v.setSpacing(22)

    def _sidebar_label(self, text):
        label = QLabel(text)
        label.setObjectName("SidebarSection")
        return label

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _refresh_home(self, favorites=False):
        self._clear_layout(self.home_v)
        top = QHBoxLayout()
        title_column = QVBoxLayout()
        overline = QLabel("YOUR PERSONAL READING SPACE")
        overline.setObjectName("Eyebrow")
        title_column.addWidget(overline)
        title = QLabel("Good to have you back.")
        title.setObjectName("HugeTitle")
        title_column.addWidget(title)
        subtitle = QLabel("Pick up where you left off, or discover something new.")
        subtitle.setObjectName("Subtitle")
        title_column.addWidget(subtitle)
        top.addLayout(title_column)
        top.addStretch()
        self.library_search = QLineEdit()
        self.library_search.setObjectName("SearchBox")
        self.library_search.setPlaceholderText("⌕  Find a book...")
        self.library_search.setFixedWidth(235)
        top.addWidget(self.library_search)
        self.home_v.addLayout(top)
        self.home_v.addSpacing(4)
        books = self.storage.books(favorite=favorites)
        if books and not favorites:
            book = books[0]
            hero = QFrame()
            hero.setObjectName("Hero")
            h = QHBoxLayout(hero)
            h.setContentsMargins(27, 20, 25, 20)
            text_column = QVBoxLayout()
            eyebrow = QLabel("✦  CONTINUE READING")
            eyebrow.setObjectName("Eyebrow")
            text_column.addWidget(eyebrow)
            text_column.addSpacing(3)
            name = QLabel(book.title if len(book.title) < 60 else book.title[:57] + "…")
            name.setObjectName("HeroTitle")
            name.setWordWrap(True)
            text_column.addWidget(name)
            info = QLabel(f"Page {book.current_page+1} of {book.pages}  ·  Resume from your last visit")
            info.setObjectName("HeroText")
            text_column.addWidget(info)
            text_column.addSpacing(11)
            cta = create_button("Continue reading  →", "PrimaryButton", action=lambda p=book.path: self.open_pdf(p))
            cta.setFixedWidth(200)
            text_column.addWidget(cta)
            h.addLayout(text_column, 1)
            icon = QLabel("◈")
            icon.setStyleSheet("font-size: 88px; color: #c48c73; background: transparent;")
            h.addWidget(icon)
            self.home_v.addWidget(hero)
        section = QHBoxLayout()
        header = QLabel("Favorites" if favorites else "Your library")
        header.setObjectName("SectionTitle")
        section.addWidget(header)
        section.addStretch()
        section.addWidget(create_button("＋  Add book", "SecondaryButton", action=self.open_file_dialog))
        self.home_v.addLayout(section)
        self.home_grid_widget = QWidget()
        self.home_grid = QGridLayout(self.home_grid_widget)
        self.home_grid.setContentsMargins(0, 0, 0, 0)
        self.home_grid.setSpacing(18)
        self.home_v.addWidget(self.home_grid_widget)
        self.home_v.addStretch()
        self.library_search.textChanged.connect(lambda text: self._fill_books(text, favorites))
        self._fill_books("", favorites)

    def _fill_books(self, search="", favorites=False):
        self._clear_layout(self.home_grid)
        books = self.storage.books(search=search, favorite=favorites)
        # Responsive cards: fit up to four at common window widths.
        width = max(500, self.home_scroll.viewport().width()-130)
        cols = max(1, min(5, width // 228))
        if not books:
            empty = QLabel("No books found. Open a PDF to start your library.")
            empty.setObjectName("Subtitle")
            self.home_grid.addWidget(empty, 0, 0)
            return
        for index, book in enumerate(books):
            card = BookCard(book)
            card.clicked.connect(self.open_pdf)
            self.home_grid.addWidget(card, index // cols, index % cols, Qt.AlignLeft | Qt.AlignTop)
        self.home_grid.setColumnStretch(cols, 1)

    def _show_library(self):
        self._refresh_home()
        self._switch_home()

    def _switch_home(self):
        if self.current_path:
            self._save_current_state()
        self.stack.setCurrentIndex(0)
        self._refresh_home()

    def _build_reader(self):
        screen = QWidget()
        self.stack.addWidget(screen)
        outer = QHBoxLayout(screen)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        rail = QFrame()
        rail.setObjectName("ReaderRail")
        rail.setFixedWidth(62)
        outer.addWidget(rail)
        railbox = QVBoxLayout(rail)
        railbox.setContentsMargins(8, 14, 8, 12)
        railbox.setSpacing(9)
        railbox.addWidget(create_button("⌂", "RailButton", "Back to library", self._switch_home))
        railbox.addSpacing(22)
        self.tool_buttons = {}
        for key, label, tip in (
            ("select", "↖", "Select text"), ("hand", "✋", "Pan page"),
            ("pen", "✎", "Pen — draw notes"), ("highlighter", "▰", "Freehand highlighter"),
            ("eraser", "⌫", "Erase a drawing stroke")
        ):
            btn = create_button(label, "RailButton", tip, lambda checked=False, k=key: self.set_tool(k))
            self.tool_buttons[key] = btn
            railbox.addWidget(btn)
        set_active(self.tool_buttons["select"], True)
        railbox.addSpacing(10)
        railbox.addWidget(create_button("●", "RailButton", "Ink color", self.choose_ink))
        railbox.addWidget(create_button("⋯", "RailButton", "Pen thickness", self.choose_pen_width))
        railbox.addStretch()
        railbox.addWidget(create_button("⚙", "RailButton", "Preferences", self.show_preferences))

        content = QWidget()
        outer.addWidget(content, 1)
        vert = QVBoxLayout(content)
        vert.setSpacing(0)
        vert.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setObjectName("ReaderBar")
        header_v = QVBoxLayout(header)
        header_v.setContentsMargins(14, 7, 15, 4)
        header_v.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(7)
        self.doc_title = QLabel("No document")
        self.doc_title.setObjectName("ReaderTitle")
        self.doc_title.setMaximumWidth(250)
        top.addWidget(self.doc_title)
        top.addStretch()
        for text, mode in [("Single", "single"), ("Facing", "spread"), ("Scroll", "continuous")]:
            btn = create_button(text, "SegmentButton", action=lambda checked=False, m=mode: self.change_layout(m))
            btn.setToolTip(f"{text} page layout")
            top.addWidget(btn)
            if not hasattr(self, "layout_buttons"):
                self.layout_buttons = {}
            self.layout_buttons[mode] = btn
        top.addSpacing(5)
        top.addWidget(create_button("◐", "IconButton", "Page appearance and brightness", self.show_appearance_menu))
        top.addWidget(create_button("★", "IconButton", "Add/remove library favorite", self.toggle_favorite))
        top.addWidget(create_button("▤", "IconButton", "Contents sidebar", lambda: self.show_panel(0)))
        top.addWidget(create_button("▧", "IconButton", "Highlights and notes", lambda: self.show_panel(1)))
        top.addWidget(create_button("⌕", "IconButton", "Research sidebar", lambda: self.show_panel(2)))
        top.addWidget(create_button("⤴", "IconButton", "Export annotated PDF", self.export_pdf))
        header_v.addLayout(top)
        tabs_row = QHBoxLayout()
        tabs_row.setContentsMargins(0, 3, 0, 0)
        self.tabs = QTabBar()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setExpanding(False)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.setStyleSheet("""
            QTabBar::tab { background:#f2efe9; border:1px solid #e5e1d9; border-bottom:0;
                            border-radius:8px 8px 0 0; padding:7px 13px; color:#6f7e89; min-width:110px; max-width:180px; }
            QTabBar::tab:selected { background:#fffefa; color:#ae6241; font-weight:700; }
            QTabBar::tab:hover { color:#a75f3e; }
        """)
        self.tabs.currentChanged.connect(self._tab_activated)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        tabs_row.addWidget(self.tabs)
        tabs_row.addWidget(create_button("＋", "IconButton", "Open another PDF", self.open_file_dialog))
        tabs_row.addStretch()
        header_v.addLayout(tabs_row)
        vert.addWidget(header)

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(0)
        self.canvas = PDFCanvas(self.storage)
        center.addWidget(self.canvas, 1)
        self.canvas.page_changed.connect(self._page_changed)
        self.canvas.request_lookup.connect(self.lookup_text)
        self.canvas.annotations_changed.connect(self._refresh_annotations)
        self.side_panel = self._create_side_panel()
        self.side_panel.hide()
        center.addWidget(self.side_panel)
        vert.addLayout(center, 1)

        foot = QFrame()
        foot.setObjectName("BottomBar")
        footer = QHBoxLayout(foot)
        footer.setContentsMargins(18, 9, 18, 9)
        footer.setSpacing(11)
        footer.addWidget(create_button("‹", "IconButton", "Previous page (←)", self.previous_page))
        self.page_entry = QLineEdit("1")
        self.page_entry.setFixedWidth(45)
        self.page_entry.setAlignment(Qt.AlignCenter)
        self.page_entry.setObjectName("SearchBox")
        self.page_entry.returnPressed.connect(self._page_entry_go)
        footer.addWidget(self.page_entry)
        self.page_count = QLabel("/ 1")
        self.page_count.setObjectName("Muted")
        footer.addWidget(self.page_count)
        footer.addWidget(create_button("›", "IconButton", "Next page (→)", self.next_page))
        footer.addSpacing(14)
        self.progress = QProgressBar()
        self.progress.setObjectName("CardProgress")
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(145)
        footer.addWidget(self.progress)
        footer.addStretch()
        self.search_pdf = QLineEdit()
        self.search_pdf.setObjectName("SearchBox")
        self.search_pdf.setPlaceholderText("⌕  Find in book...")
        self.search_pdf.setFixedWidth(165)
        self.search_pdf.returnPressed.connect(self._find_in_pdf)
        footer.addWidget(self.search_pdf)
        footer.addWidget(create_button("☆", "IconButton", "Bookmark this page", self.toggle_bookmark))
        footer.addWidget(create_button("−", "IconButton", "Zoom out", lambda: self.change_zoom(-.1)))
        self.zoom_text = QLabel("100%")
        self.zoom_text.setObjectName("Muted")
        self.zoom_text.setMinimumWidth(44)
        footer.addWidget(self.zoom_text)
        footer.addWidget(create_button("＋", "IconButton", "Zoom in", lambda: self.change_zoom(.1)))
        vert.addWidget(foot)

    def _create_side_panel(self):
        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setFixedWidth(335)
        v = QVBoxLayout(panel)
        v.setContentsMargins(16, 17, 16, 16)
        v.setSpacing(12)
        h = QHBoxLayout()
        title = QLabel("Reading tools")
        title.setObjectName("PanelTitle")
        h.addWidget(title)
        h.addStretch()
        h.addWidget(create_button("×", "IconButton", "Close sidebar", lambda: self.side_panel.hide()))
        v.addLayout(h)
        nav = QHBoxLayout()
        nav.setSpacing(2)
        self.panel_buttons = []
        for index, text in enumerate(("Contents", "Notes", "Research")):
            b = create_button(text, "PanelTab", action=lambda checked=False, i=index: self.show_panel(i))
            nav.addWidget(b)
            self.panel_buttons.append(b)
        v.addLayout(nav)
        self.panel_stack = QStackedWidget()
        v.addWidget(self.panel_stack, 1)

        # Table of contents view.
        contents = QWidget()
        cl = QVBoxLayout(contents)
        cl.setContentsMargins(0, 0, 0, 0)
        self.toc = QTreeWidget()
        self.toc.setHeaderHidden(True)
        self.toc.itemClicked.connect(lambda item, col: self.canvas.go_to(item.data(0, Qt.UserRole)))
        cl.addWidget(self.toc)
        self.panel_stack.addWidget(contents)

        # Notes and bookmarks, pulled only for currently opened PDF.
        notes = QWidget()
        nl = QVBoxLayout(notes)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        self.annotation_list = QListWidget()
        self.annotation_list.itemClicked.connect(self._annotation_clicked)
        nl.addWidget(QLabel("HIGHLIGHTS, INK & NOTES"))
        nl.addWidget(self.annotation_list, 1)
        nl.addWidget(QLabel("BOOKMARKS"))
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemClicked.connect(self._bookmark_clicked)
        nl.addWidget(self.bookmark_list, 1)
        self.panel_stack.addWidget(notes)

        # No browser engine or web process exists until user explicitly opens it.
        research = QWidget()
        rl = QVBoxLayout(research)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        self.lookup_input = QLineEdit()
        self.lookup_input.setObjectName("SearchBox")
        self.lookup_input.setPlaceholderText("Search a term...")
        self.lookup_input.returnPressed.connect(self._search_lookup)
        rl.addWidget(self.lookup_input)
        self.lookup_intro = QLabel("Select a term in your book, then choose “Search & explain in sidebar.”")
        self.lookup_intro.setObjectName("Subtitle")
        self.lookup_intro.setWordWrap(True)
        rl.addWidget(self.lookup_intro)
        rl.addWidget(create_button("Search Google in sidebar", "PrimaryButton", action=self._embedded_google))
        rl.addWidget(create_button("↗  Open Google in browser", "SecondaryButton", action=self._external_google))
        rl.addWidget(create_button("↗  Look up on Wikipedia", "SecondaryButton", action=self._external_wikipedia))
        self.web_holder = QVBoxLayout()
        rl.addLayout(self.web_holder, 1)
        self.panel_stack.addWidget(research)
        return panel

    def show_panel(self, index):
        if self.side_panel.isVisible() and self.panel_stack.currentIndex() == index:
            self.side_panel.hide()
            return
        self.side_panel.show()
        self.panel_stack.setCurrentIndex(index)
        for i, b in enumerate(self.panel_buttons):
            set_active(b, i == index)
        if index == 0:
            self._refresh_toc()
        elif index == 1:
            self._refresh_annotations()

    def _refresh_toc(self):
        self.toc.clear()
        doc = self.documents.get(self.current_path)
        if not doc:
            return
        parent_by_level = {}
        for level, title, page in doc.outline():
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.UserRole, page)
            parent = parent_by_level.get(level - 1)
            if parent is not None:
                parent.addChild(item)
            else:
                self.toc.addTopLevelItem(item)
            parent_by_level[level] = item
        if not doc.outline():
            self.toc.addTopLevelItem(QTreeWidgetItem(["This PDF has no chapter outline."]))

    def _refresh_annotations(self):
        self.annotation_list.clear()
        self.bookmark_list.clear()
        if not self.current_path:
            return
        for row in self.storage.annotations(self.current_path):
            kind = row["kind"]
            payload = row["payload"]
            label = {"highlight": "◆ Highlight", "ink": "✎ Ink", "marker": "▰ Marker", "note": "✦ Note"}.get(kind, kind)
            summary = (payload.get("text") or "")[:65].replace("\n", " ")
            if summary:
                label += f" · {summary}"
            self.annotation_list.addItem(f"p. {row['page']+1}   {label}")
            self.annotation_list.item(self.annotation_list.count()-1).setData(Qt.UserRole, row["page"])
            self.annotation_list.item(self.annotation_list.count()-1).setToolTip(payload.get("text") or payload.get("quote") or label)
        for entry in self.storage.bookmarks(self.current_path):
            self.bookmark_list.addItem(f"★  Page {entry['page']+1}")
            self.bookmark_list.item(self.bookmark_list.count()-1).setData(Qt.UserRole, entry["page"])

    def _annotation_clicked(self, item):
        self.canvas.go_to(item.data(Qt.UserRole))

    def _bookmark_clicked(self, item):
        self.canvas.go_to(item.data(Qt.UserRole))

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open a PDF", str(Path.home()), "PDF files (*.pdf)")
        if path:
            self.open_pdf(path)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Import a folder of PDFs", str(Path.home()))
        if not folder:
            return
        found = list(Path(folder).rglob("*.pdf"))
        imported = 0
        for path in found:
            try:
                pdf = PDFDocument(str(path))
                self.storage.upsert_book(pdf.path, pdf.title, pdf.author, pdf.pages)
                pdf.close()
                imported += 1
            except Exception:
                continue
        self._refresh_home()
        QMessageBox.information(self, "Import complete", f"Imported {imported} PDF files into your library.")

    def open_pdf(self, path: str, at_page: int | None = None):
        path = str(Path(path).expanduser().resolve())
        if not Path(path).is_file():
            QMessageBox.warning(self, "PDF unavailable", f"File not found:\n{path}")
            return
        if path not in self.documents:
            try:
                doc = PDFDocument(path)
            except Exception as error:
                QMessageBox.warning(self, "Couldn't open PDF", str(error))
                return
            self.documents[path] = doc
            self.storage.upsert_book(path, doc.title, doc.author, doc.pages)
            self.tabs.blockSignals(True)
            index = self.tabs.addTab(doc.title[:25])
            self.tabs.setTabData(index, path)
            self.tabs.setTabToolTip(index, path)
            self.tabs.blockSignals(False)
        index = next(i for i in range(self.tabs.count()) if self.tabs.tabData(i) == path)
        self.tabs.blockSignals(True)
        self.tabs.setCurrentIndex(index)
        self.tabs.blockSignals(False)
        self._activate_book(path, at_page)

    def _tab_activated(self, index):
        if self._closing or index < 0:
            return
        path = self.tabs.tabData(index)
        if path and path in self.documents:
            self._activate_book(path)

    def _activate_book(self, path, at_page=None):
        if self.current_path and self.current_path != path:
            self._save_current_state()
        doc = self.documents.get(path)
        if not doc:
            return
        self._loading_doc = True
        self.current_path = path
        self.doc_title.setText(doc.title[:35])
        self.doc_title.setToolTip(doc.title)
        state = self.storage.reading_state(path)
        index = int(at_page) if at_page is not None else state.get("current_page", 0)
        self.canvas.set_document(doc, index, state.get("layout", "single"),
                                 state.get("zoom", 1.0), state.get("theme", "paper"))
        self.canvas.set_brightness(state.get("brightness", 100))
        self._loading_doc = False
        self._update_layout_buttons()
        self._page_changed(self.canvas.page)
        self._refresh_toc()
        self._refresh_annotations()
        self.stack.setCurrentIndex(1)
        self._save_session()
        self.canvas.setFocus()

    def _close_tab(self, index):
        if index < 0:
            return
        path = self.tabs.tabData(index)
        if path == self.current_path:
            self._save_current_state()
        self._closing = True
        self.tabs.removeTab(index)
        self._closing = False
        doc = self.documents.pop(path, None)
        if doc:
            if path == self.current_path:
                self.canvas.close_document()
                self.current_path = None
            doc.close()
        if self.tabs.count():
            self._tab_activated(self.tabs.currentIndex())
        else:
            self.current_path = None
            self._switch_home()
        self._save_session()

    def _save_session(self):
        paths = [self.tabs.tabData(i) for i in range(self.tabs.count())]
        self.settings.setValue("session", paths)

    def restore_session(self):
        files = self.settings.value("session", [], type=list)
        for path in files[:12]:
            if Path(path).is_file():
                self.open_pdf(path)
        if not files:
            QMessageBox.information(self, "Restore session", "No previous reading session found.")

    def _save_current_state(self):
        if self.current_path:
            self.storage.set_state(self.current_path,
                                   current_page=self.canvas.page,
                                   layout=self.canvas.layout,
                                   zoom=self.canvas.zoom,
                                   theme=self.canvas.theme,
                                   brightness=self.canvas.brightness)

    def _page_changed(self, page):
        doc = self.documents.get(self.current_path)
        if not doc:
            return
        self.page_entry.setText(str(page + 1))
        self.page_count.setText(f"/ {doc.pages}")
        self.progress.setRange(0, doc.pages)
        self.progress.setValue(page+1)
        self.zoom_text.setText(f"{round(self.canvas.zoom * 100)}%")
        if not self._loading_doc:
            self.storage.set_state(self.current_path, current_page=page)

    def _page_entry_go(self):
        try:
            index = int(self.page_entry.text()) - 1
            self.canvas.go_to(index)
        except ValueError:
            self._page_changed(self.canvas.page)

    def next_page(self):
        self.canvas.next_page()

    def previous_page(self):
        self.canvas.previous_page()

    def change_layout(self, mode):
        self.canvas.set_layout(mode)
        self._update_layout_buttons()
        self._save_current_state()

    def _update_layout_buttons(self):
        for mode, button in self.layout_buttons.items():
            set_active(button, mode == self.canvas.layout)

    def change_zoom(self, delta):
        self.canvas.set_zoom(self.canvas.zoom + delta)
        self.zoom_text.setText(f"{round(self.canvas.zoom * 100)}%")
        self._save_current_state()

    def _find_in_pdf(self):
        if self.search_pdf.text().strip() and not self.canvas.find_text(self.search_pdf.text()):
            self.statusBar().showMessage("No matches found", 3000)

    def toggle_bookmark(self):
        if not self.current_path:
            return
        added = self.storage.bookmark_toggle(self.current_path, self.canvas.page)
        self.statusBar().showMessage("Bookmark saved" if added else "Bookmark removed", 2200)
        self._refresh_annotations()

    def toggle_favorite(self):
        if not self.current_path:
            return
        row = self.storage.get_book(self.current_path)
        new_value = not bool(row["is_favorite"]) if row else True
        self.storage.set_state(self.current_path, is_favorite=int(new_value))
        self.statusBar().showMessage("Added to favorites" if new_value else "Removed from favorites", 2400)

    def set_tool(self, tool):
        self._ui_tool = tool
        self.canvas.set_tool(tool)
        for name, button in self.tool_buttons.items():
            set_active(button, name == tool)

    def choose_ink(self):
        color = QColorDialog.getColor(QColor(self.canvas.ink_color), self, "Choose pen color")
        if color.isValid():
            self.canvas.ink_color = color.name()
            self.set_tool("pen")

    def choose_pen_width(self):
        value, ok = QInputDialog.getDouble(self, "Pen thickness", "Stroke width (PDF points)",
                                           self.canvas.ink_width, 0.5, 20.0, 1)
        if ok:
            self.canvas.ink_width = value
            self.set_tool("pen")

    def show_appearance_menu(self):
        menu = QMenu(self)
        menu.addSection("Page appearance")
        for title, key in [("Warm paper", "paper"), ("Clean white", "white"),
                           ("Sepia", "sepia"), ("Night / inverted", "dark")]:
            action = menu.addAction(("✓  " if self.canvas.theme == key else "      ") + title)
            action.triggered.connect(lambda checked=False, k=key: self.change_theme(k))
        menu.addSeparator()
        menu.addSection("Page fitting")
        fit_page = menu.addAction("Fit entire page")
        fit_width = menu.addAction("Fit page width")
        fit_page.triggered.connect(lambda: self.canvas.set_fit_mode("page"))
        fit_width.triggered.connect(lambda: self.canvas.set_fit_mode("width"))
        menu.addSeparator()
        menu.addSection("Page brightness")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(30, 100)
        slider.setValue(self.canvas.brightness)
        slider.setMinimumWidth(195)
        slider.valueChanged.connect(lambda value: (self.canvas.set_brightness(value), self._save_current_state()))
        slider_frame = QWidget()
        box = QHBoxLayout(slider_frame)
        box.setContentsMargins(14, 4, 14, 6)
        box.addWidget(slider)
        action = QWidgetAction(menu)
        action.setDefaultWidget(slider_frame)
        menu.addAction(action)
        menu.addSeparator()
        menu.addSection("Image cache (maximum)")
        for size in (32, 64, 128):
            action = menu.addAction(f"{size} MiB")
            action.triggered.connect(lambda checked=False, s=size: self._set_cache_limit(s))
        menu.exec(self.cursor().pos())

    def _set_cache_limit(self, size):
        self.canvas.set_memory_budget(size)
        self.settings.setValue("image-cache-mib", size)
        self.statusBar().showMessage(f"Page cache limited to {size} MiB", 3000)

    def change_theme(self, key):
        self.canvas.set_theme(key)
        self._save_current_state()

    def lookup_text(self, text):
        self.lookup_input.setText(text[:300])
        self.lookup_intro.setText("Search the selected text using Google or Wikipedia. The embedded web browser loads only when requested to save memory.")
        self.show_panel(2) if not (self.side_panel.isVisible() and self.panel_stack.currentIndex() == 2) else None

    def _search_lookup(self):
        self._embedded_google()

    def _query(self):
        return self.lookup_input.text().strip()

    def _external_google(self):
        if self._query():
            QDesktopServices.openUrl(QUrl("https://www.google.com/search?q="+quote_plus(self._query())))

    def _external_wikipedia(self):
        if self._query():
            QDesktopServices.openUrl(QUrl("https://en.wikipedia.org/w/index.php?search="+quote_plus(self._query())))

    def _embedded_google(self):
        if not self._query():
            return
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QMessageBox.information(self, "Embedded web unavailable", "Qt WebEngine isn't installed. Google can still be opened in your default browser.")
            return
        if not hasattr(self, "web_view"):
            self.web_view = QWebEngineView()
            self.web_view.setMinimumHeight(230)
            self.web_holder.addWidget(self.web_view)
        self.web_view.setUrl(QUrl("https://www.google.com/search?q="+quote_plus(self._query())))
        self.lookup_intro.setText("Some sites may refuse to display inside an embedded webview. Use 'Open Google in browser' if necessary.")

    def export_pdf(self):
        if not self.current_path:
            return
        path = Path(self.current_path)
        default = str(path.with_name(path.stem + "-annotated.pdf"))
        filename, _ = QFileDialog.getSaveFileName(self, "Export annotated PDF", default, "PDF files (*.pdf)")
        if not filename:
            return
        try:
            n = export_annotated_pdf(path, filename, self.storage)
            QMessageBox.information(self, "Export complete", f"Saved PDF with {n} annotations:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Export failed", str(e))

    def show_preferences(self):
        QMessageBox.information(self, "Folio-Linux preferences",
            "Folio runs locally and never uploads your PDFs.\n\n"
            "Open PDFs directly by double-click once Folio is installed as your default reader.\n\n"
            "Use the appearance menu (◐) to change themes, brightness and memory cache.\n"
            "Hold Ctrl and scroll to zoom; use ← / → to turn pages.\n\n"
            "Annotations are saved separately and can be exported to a regular PDF.")

    def _shortcuts(self):
        bindings = [
            ("Ctrl+O", self.open_file_dialog),
            ("Ctrl+F", lambda: self.search_pdf.setFocus() if self.stack.currentIndex() == 1 else self.library_search.setFocus()),
            ("Ctrl+B", self.toggle_bookmark),
            ("Ctrl+1", lambda: self.change_layout("single")),
            ("Ctrl+2", lambda: self.change_layout("spread")),
            ("Ctrl+3", lambda: self.change_layout("continuous")),
            ("Ctrl+L", self._switch_home),
            ("Ctrl+Plus", lambda: self.change_zoom(.1)),
            ("Ctrl+Minus", lambda: self.change_zoom(-.1)),
            ("Right", self.next_page), ("Left", self.previous_page),
            ("F11", self._toggle_fullscreen),
            ("Escape", lambda: self.side_panel.hide()),
        ]
        self._shortcut_refs = []
        for key, function in bindings:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(function)
            self._shortcut_refs.append(shortcut)

    def _toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def closeEvent(self, event):
        self._save_current_state()
        self._save_session()
        for doc in self.documents.values():
            doc.close()
        self.storage.close()
        super().closeEvent(event)


def _receive_launch(server: QLocalServer, window: FolioWindow, clients: list):
    """Send file-open requests to existing instance instead of spawning windows."""
    while server.hasPendingConnections():
        client = server.nextPendingConnection()
        clients.append(client)

        def on_data(socket=client):
            try:
                message = json.loads(bytes(socket.readAll()).decode("utf-8"))
                path = message.get("pdf")
                if path:
                    window.open_pdf(path, message.get("page"))
                else:
                    window._switch_home()
                window.showNormal()
                window.raise_()
                window.activateWindow()
            except (ValueError, TypeError, UnicodeDecodeError):
                pass
            finally:
                if socket in clients:
                    clients.remove(socket)
                socket.disconnectFromServer()
                socket.deleteLater()

        client.readyRead.connect(on_data)
        # Bytes may be ready before the signal connection in local IPC.
        if client.bytesAvailable():
            on_data()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Folio-Linux: a comfortable, low-memory PDF reader")
    parser.add_argument("pdf", nargs="?", help="PDF file to open directly (without dashboard)")
    parser.add_argument("--page", type=int, help="1-based PDF page to open")
    parser.add_argument("--version", action="version", version="Folio-Linux 0.1.0")
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Folio")
    app.setOrganizationName("FolioLinux")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    # Local socket gives us Word-like desktop behavior: one process, new file tab.
    socket_name = f"folio-linux-{os.getuid()}"
    client = QLocalSocket()
    client.connectToServer(socket_name)
    if client.waitForConnected(200):
        data = {"pdf": str(Path(args.pdf).expanduser().resolve()) if args.pdf else None,
                "page": args.page - 1 if args.page else None}
        client.write((json.dumps(data) + "\n").encode("utf-8"))
        client.waitForBytesWritten(1000)
        client.disconnectFromServer()
        return 0
    client.close()
    server = QLocalServer()
    # An old crashed instance may have left a stale Unix socket.
    QLocalServer.removeServer(socket_name)
    server.listen(socket_name)
    window = FolioWindow(args.pdf, args.page - 1 if args.page else None)
    window.canvas.set_memory_budget(int(window.settings.value("image-cache-mib", 64)))
    client_connections = []
    server.newConnection.connect(lambda: _receive_launch(server, window, client_connections))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
