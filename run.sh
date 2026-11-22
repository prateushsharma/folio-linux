#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
if ! "$PYTHON" -c 'import PySide6, fitz' 2>/dev/null; then
  cat <<'HELP'
Folio needs its Python dependencies installed first.

  python3 -m venv .venv
  .venv/bin/pip install -e .
  ./run.sh

Or run ./install.sh to set up the desktop integration automatically.
HELP
  exit 1
fi
exec "$PYTHON" -m folio "$@"
