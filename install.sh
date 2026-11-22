#!/usr/bin/env bash
# Per-user installation. Developer checkout stays live so git pull updates Folio.
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET="$DATA_HOME/folio-linux"
BIN="$HOME/.local/bin"
APPS="$DATA_HOME/applications"
ICONS="$DATA_HOME/icons/hicolor/scalable/apps"
mkdir -p "$TARGET" "$BIN" "$APPS" "$ICONS"

if command -v ldconfig >/dev/null 2>&1 && \
   ! ldconfig -p 2>/dev/null | grep -q 'libxcb-cursor\.so\.0'; then
  printf '\nWarning: Qt X11 needs libxcb-cursor0, which appears to be missing.\n' >&2
  printf 'On Ubuntu/Debian run: sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1\n' >&2
  printf 'On a Wayland session you can also try QT_QPA_PLATFORM=wayland folio.\n\n' >&2
fi

python3 -m venv "$TARGET/venv"
"$TARGET/venv/bin/python" -m pip install --upgrade pip
# Editable install makes subsequent `git pull` update the installed application
# without reinstalling each time (as long as this checkout stays in place).
"$TARGET/venv/bin/python" -m pip install -e "$SOURCE_DIR"

cat > "$BIN/folio" <<EOF_WRAPPER
#!/usr/bin/env bash
# Try native Wayland first on Wayland desktops; Qt may fall back to XCB.
if [[ -z "\${QT_QPA_PLATFORM:-}" && "\${XDG_SESSION_TYPE:-}" == "wayland" ]]; then
  export QT_QPA_PLATFORM='wayland;xcb'
fi
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
printf '\nInstalled Folio-Linux (editable source checkout: %s)\n' "$SOURCE_DIR"
printf 'Run: %s/folio\n' "$BIN"
printf 'Future source updates: git pull (no reinstall needed).\n'
printf 'IMPORTANT: keep your source checkout at the same path.\n'
