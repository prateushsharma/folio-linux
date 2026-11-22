#!/usr/bin/env bash
# Installs to the current user's home directory. No sudo required.
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET="$DATA_HOME/folio-linux"
APP="$TARGET/app"
BIN="$HOME/.local/bin"
APPS="$DATA_HOME/applications"
ICONS="$DATA_HOME/icons/hicolor/scalable/apps"
mkdir -p "$APP" "$BIN" "$APPS" "$ICONS"
# Source checkout and Git history remain untouched; install a clean working copy.
cp -r "$SOURCE_DIR/folio" "$SOURCE_DIR/assets" "$SOURCE_DIR/pyproject.toml" "$SOURCE_DIR/README.md" "$SOURCE_DIR/LICENSE" "$APP/"
python3 -m venv "$TARGET/venv"
"$TARGET/venv/bin/python" -m pip install --upgrade pip
"$TARGET/venv/bin/python" -m pip install "$APP"
cat > "$BIN/folio" <<EOF_WRAPPER
#!/usr/bin/env bash
exec "$TARGET/venv/bin/python" -m folio "\$@"
EOF_WRAPPER
chmod +x "$BIN/folio"
cp "$SOURCE_DIR/assets/folio.svg" "$ICONS/folio.svg"
cat > "$APPS/folio-linux.desktop" <<EOF_DESKTOP
[Desktop Entry]
Type=Application
Name=Folio
GenericName=PDF Reader and Study Workspace
Comment=Read, annotate and explore your books
Exec=$BIN/folio %f
Icon=folio
Terminal=false
Categories=Office;Viewer;Education;
MimeType=application/pdf;
StartupNotify=true
Keywords=PDF;Books;Study;Annotations;Reader;
EOF_DESKTOP
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi
printf '\nInstalled Folio-Linux!\n'
printf 'Open Folio from your app menu, or run: %s/folio\n' "$BIN"
printf 'You can set Folio as the default PDF app in your file manager.\n'
printf 'Note: the embedded webview is optional; install PySide6-Addons if you need it.\n'
