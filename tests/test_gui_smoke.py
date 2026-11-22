"""Run by GitHub Actions after installing PySide6-Essentials, not in core-only environments."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_window_very_basic(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from PySide6.QtWidgets import QApplication
    from folio.app import FolioWindow
    app = QApplication.instance() or QApplication([])
    window = FolioWindow()
    assert window.stack.currentIndex() == 0
    assert window.tabs.count() == 0
    window.close()
