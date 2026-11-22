# Architecture of Folio-Linux 0.1.0

## Why Qt Widgets + PyMuPDF?

Folio needs low-latency pen input, native Linux file associations, and readable text selection. Qt Widgets gives us mature input handling and menus without requiring a browser process. PyMuPDF is used only for PDF decoding, extraction and export. PySide6-Essentials avoids the larger Qt WebEngine dependency unless a user opts in.

```
Application / Qt Widgets
├── Home library dashboard + native file dialogs
├── Reader tabs / menus / research sidebar
└── PDFCanvas (QAbstractScrollArea)
    ├── Visible geometry for one, two, or continuous pages
    ├── Page raster LRU cache (default target 64 MiB)
    ├── Lazy PDF decoding through PDFDocument / PyMuPDF
    ├── Painted annotation layer from SQLite
    └── Text hit detection from PDF word rectangles

Local SQLite WAL storage
├── books (progress, layouts, zoom, page themes)
├── annotations (ink, marker, highlights, notes)
└── bookmarks
```

## Memory approach

- The canvas does **not** create a QWidget for each PDF page.
- Rasterization is lazy: only visible pages are rendered.
- Cached raster images are bounded by the chosen cache setting; default is 64 MiB.
- Individual raster images are limited to 8 million pixels and 3200 px on their longest side.
- Continuous scrolling stores page rectangles, not raster images, for off-screen pages.
- Per-page extracted word lists are cached for only eight pages.
- Qt WebEngine is **not** loaded at application startup and is an optional dependency.
- SQLite holds annotations outside PDFs; it does not load the full collection into memory.

The raster cache cap is **not** a limit on the whole application's RAM, because Qt, Python, PDF structures and the OS have their own allocations.

## Storage, privacy and recovery

- Default SQLite path: `~/.local/share/folio-linux/library.sqlite3`
- Honors `XDG_DATA_HOME`.
- Uses SQLite WAL and transactions so saved notes are resilient to crashes.
- Read position is saved when changing pages, books or closing the application.
- Original PDFs are never modified unless a user separately chooses Export; exports use a different filename.
- Google/Wikipedia links are explicit, and embedded web browsing is opt-in.
- No telemetry, account, sync service or API key is needed.

## Known technical limitations

- PDF text selection works from word positions, not a full typographic selection engine.
- Drawing eraser currently removes a nearby whole stroke rather than clipping segments.
- Embedded Google can be blocked by Google's restrictions; external browser remains available.
- PDF password entry, PDF forms, page reflow and OCR are not implemented.
- Continuous mode measures page metadata; initial layout for very long PDFs can take noticeable time.
- Current Windows/macOS support is untested; Ubuntu/Debian Linux are primary targets.
