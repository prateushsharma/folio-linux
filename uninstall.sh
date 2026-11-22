#!/usr/bin/env bash
# Remove installed app without touching personal reading history/annotations.
set -euo pipefail
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -f "$HOME/.local/bin/folio"
rm -f "$DATA_HOME/applications/folio-linux.desktop"
rm -f "$DATA_HOME/icons/hicolor/scalable/apps/folio.svg"
rm -rf "$DATA_HOME/folio-linux/app" "$DATA_HOME/folio-linux/venv"
printf 'Folio uninstalled. Library/annotations remain in %s/folio-linux/library.sqlite3\n' "$DATA_HOME"
