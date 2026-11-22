# Troubleshooting Folio-Linux

## Clicking Folio does nothing

Run `~/.local/bin/folio` from a terminal to see the error. Common missing system libraries: `libxcb-cursor0`, `libxkbcommon-x11-0`, `libegl1`. On Ubuntu/Debian, run `sudo apt update && sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1` and retry. Run `./scripts/doctor.sh` to inspect your exact Qt dependencies. On Wayland (`echo $XDG_SESSION_TYPE` reports `wayland`), try `QT_QPA_PLATFORM=wayland folio`. Use `QT_DEBUG_PLUGINS=1 folio` for the full loader diagnostics.

## Embedded Google results do not display

Websites may block embedding, and the lightweight installation does not include Qt WebEngine. Use **Open Google in browser**, or optionally install `PySide6-Addons` in Folio's venv. This may increase RAM use.

## Unusually high memory use

Use the appearance menu → image cache → 32 MiB. Avoid embedded web browsing when memory is constrained. This bounds cached PDF rasters only; it does not cap the entire Python/Qt process. Large scanned PDFs may be heavy to decode.

## Double-clicking a PDF opens the old viewer

Set Folio as the default application for PDFs in your file manager's Properties / Open With dialog. Installing Folio registers the MIME type but does not change your preference automatically.

## Lost your reading position?

Check that `~/.local/share/folio-linux/library.sqlite3` is writable. The database stores the current page separately from the PDF. Avoid moving the source PDFs after importing because paths are keys in the database.

## Exported annotations look different

Qt draws Folio strokes using custom appearance rules, while the exported PDF uses standard PDF annotations. Shape and transparency may vary in other viewers. Keep a local backup of Folio's SQLite database if fidelity matters.
