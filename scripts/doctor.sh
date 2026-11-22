#!/usr/bin/env bash
# Diagnose Linux Qt platform-plugin errors without starting a QApplication.
set -u
printf 'Folio-Linux Qt environment check\n'
printf 'Desktop session: %s\n' "${XDG_SESSION_TYPE:-unknown}"
printf 'DISPLAY: %s\n' "${DISPLAY:-unset}"
printf 'WAYLAND_DISPLAY: %s\n' "${WAYLAND_DISPLAY:-unset}"
printf 'QT_QPA_PLATFORM: %s\n' "${QT_QPA_PLATFORM:-auto}"
if command -v ldconfig >/dev/null 2>&1; then
  for entry in libxcb-cursor.so.0 libxkbcommon-x11.so.0 libEGL.so.1; do
    if ldconfig -p 2>/dev/null | grep -Fq "$entry"; then
      printf '[OK] %s\n' "$entry"
    else
      printf '[MISSING] %s\n' "$entry"
    fi
  done
fi
PYTHON="${FOLIO_PYTHON:-$HOME/.local/share/folio-linux/venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi
printf '\nPython: %s\n' "$PYTHON"
PLUGIN_DIR="$($PYTHON - <<'PY'
try:
    from PySide6.QtCore import QLibraryInfo
    from pathlib import Path
    print(Path(QLibraryInfo.path(QLibraryInfo.PluginsPath)) / 'platforms')
except ImportError:
    pass
PY
)"
if [[ -n "$PLUGIN_DIR" && -d "$PLUGIN_DIR" ]]; then
  printf 'Qt platform plugins: %s\n' "$PLUGIN_DIR"
  if [[ -f "$PLUGIN_DIR/libqxcb.so" ]]; then
    printf '\nMissing shared objects for Qt XCB plugin (if any):\n'
    if command -v ldd >/dev/null 2>&1; then
      ldd "$PLUGIN_DIR/libqxcb.so" | grep 'not found' || printf '(none reported by ldd)\n'
    else
      printf 'Install ldd to inspect shared libraries.\n'
    fi
  fi
else
  printf 'Could not find PySide6 Qt platform plugins.\n'
fi
printf '\nCommon Ubuntu repair:\n'
printf '  sudo apt update && sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1\n'
printf 'Wayland test:\n'
printf '  QT_QPA_PLATFORM=wayland folio\n'
printf 'Further Qt diagnostics:\n'
printf '  QT_DEBUG_PLUGINS=1 folio\n'
