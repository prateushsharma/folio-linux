# ◈ Folio-Linux

**Read. Annotate. Explore.**

Folio-Linux is an offline-first PDF reader for Linux that treats PDFs like books, with a welcoming personal library, facing pages, smooth navigation, local bookmarks, handwriting and an optional research sidebar.

> **Version:** 0.1.0-alpha — a working source-code prototype, not yet a polished production app. GUI dependencies could not be launched in the build environment; the unit/integration tests for core PDF functionality pass. Please report runtime issues when testing on Ubuntu.

## Screens and behavior

| Launch method | What opens |
|---|---|
| Open **Folio** from the Linux app menu | Home Dashboard with books and Continue Reading |
| Double-click a `.pdf` after choosing Folio as default | That PDF directly, with saved progress |
| `folio book.pdf` | That PDF directly |
| `folio --page 153 book.pdf` | PDF at page 153 (1-based) |
| Open a second PDF while Folio is running | In a tab, with saved state |

## Implemented in this alpha

- **Reading:** single-page, facing pages, continuous scroll, fit-page and fit-width scaling internally, zoom, next/previous page, page number navigation, full screen, warm paper/white/sepia/dark themes, adjustable page dimming.
- **Library:** import PDF, folder import, recent book cards, favorites in database (favorite toggle UI is planned), title search, reading progress and per-book state, manual restore session.
- **Annotation:** pen drawing, freehand marker, stroke eraser, PDF text selection, copy, selected-text highlight, sticky note, autosave to SQLite, export to standard annotated PDF.
- **Research:** select text → Google/Wikipedia actions in a sidebar; optionally load an embedded Google view, or open your regular browser. Embedded web requires the optional addon and may be blocked by websites.
- **Linux:** `.desktop` launcher, app-menu icon, MIME registration for `application/pdf`, launch from file manager using Open With, CLI support.
- **Memory:** lazy rendering of visible pages, 64 MiB default raster-cache target (configurable 32/64/128 MiB), maximum 8-megapixel page raster, no always-running embedded browser process.

## Install on Ubuntu/Linux Mint/Debian

**Requirements:** Python 3.10+, `python3-venv`, a graphical desktop, access to PyPI for the first dependency installation.

```bash
sudo apt update
sudo apt install python3-venv python3-pip libxcb-cursor0 libxkbcommon-x11-0 libegl1
unzip folio-linux-source-with-history.zip
cd folio-linux
./install.sh
```

Then launch **Folio** from your application menu, or run:

```bash
~/.local/bin/folio
~/.local/bin/folio ~/Documents/book.pdf
~/.local/bin/folio --page 42 ~/Documents/book.pdf
```

For developer mode (no desktop install):

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
./run.sh
```

### Optional embedded web sidebar

By default the lightweight installation has no web browser engine. To enable an embedded Google view inside Folio:

```bash
~/.local/share/folio-linux/venv/bin/pip install 'PySide6-Addons>=6.6,<7'
```

Embedded Google pages can refuse to render in a WebView. **Open Google in browser** is always offered as a fallback. Enabling WebEngine increases RAM consumption while browsing.

### Make it the default PDF reader

Once installed, right-click a PDF in Files → **Properties** / **Open With** → choose **Folio** → **Set as Default** (the exact UI varies by Linux desktop).

The installation script does *not* silently change your default app.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open PDF |
| `Ctrl+F` | Find in PDF / search library |
| `←` / `→` | Previous / next page |
| `Ctrl+1` / `Ctrl+2` / `Ctrl+3` | Single / facing / continuous mode |
| `Ctrl+Plus` / `Ctrl+Minus` | Zoom in/out |
| `Ctrl` + mouse wheel | Zoom under reader |
| `Ctrl+B` | Bookmark current page |
| `Ctrl+L` | Home dashboard |
| `F11` | Fullscreen |
| `Esc` | Close sidebar |

## Where are reading progress and notes stored?

`~/.local/share/folio-linux/library.sqlite3` (or `$XDG_DATA_HOME/folio-linux/library.sqlite3`). Your original PDFs are **never** overwritten by normal reading, highlighting or ink. Export from the reader to create a separately annotated PDF. Back up the SQLite file *and any WAL files while the app is open*, or close Folio before backing it up.

## Run tests

```bash
python3 -m pytest -q tests/test_storage.py tests/test_document.py
# after installing all GUI dependencies:
QT_QPA_PLATFORM=offscreen python3 -m pytest -q tests/test_gui_smoke.py
```

GitHub Actions runs the tests on pushes and pull requests.

## Push this exact project, including commits, to GitHub

**The ZIP includes a real `.git` directory and multiple actual commits.** After unzipping, keep the `.git` directory. Create a new *empty* repository on GitHub (without a README or license), then:

```bash
cd folio-linux
git log --oneline --all
./publish-to-github.sh https://github.com/YOUR_USERNAME/folio-linux.git
# Or run the equivalent git remote/branch/push commands yourself.
```

For HTTPS push, GitHub requires an authenticated Git credential manager/token (not your account password). Alternatively use a configured SSH URL: `git@github.com:YOUR_USERNAME/folio-linux.git`.

The GitHub repository will contain the complete project, commit history, test workflow, and all design documents. Future commits can be pushed with `git push`.

**Do not upload the ZIP as one repository file** if you want the history preserved; use Git to push the unzipped folder.

## Project map

```
folio-linux/
├── folio/
│   ├── app.py          # home, tabs, toolbars and sidebar
│   ├── reader.py       # memory-bounded canvas and input handling
│   ├── document.py     # PyMuPDF decoding and text search
│   ├── storage.py      # SQLite library + annotations
│   ├── export.py       # standard PDF annotation export
│   ├── models.py       # data/utility helpers
│   └── style.py        # visual design system
├── assets/folio.svg   # app icon
├── tests/             # PDF, storage and GUI smoke tests
├── docs/              # architecture, design and roadmap
├── .github/workflows/ # CI
├── publish-to-github.sh # preserve commits and push to your GitHub repo
├── install.sh         # per-user Linux installer
├── uninstall.sh       # uninstaller; keeps personal notes
├── run.sh             # development runner
└── .git/              # historical commits (included in ZIP)
```

## License and dependencies

Source code licensed under **GNU AGPL-3.0**. PyMuPDF is licensed under AGPL/commercial terms and PySide6 under LGPL/GPL/commercial terms. Respect these licenses if you redistribute or commercialize Folio. Full GNU AGPL-3.0 license text is in `LICENSE`.

See [architecture](docs/ARCHITECTURE.md), [design notes](docs/DESIGN.md), and [roadmap](docs/ROADMAP.md). Issues and PRs welcome.
