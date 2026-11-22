"""Pure-python model and geometry helpers (also testable without Qt)."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import hashlib


@dataclass(frozen=True)
class Book:
    path: str
    title: str
    author: str = ""
    pages: int = 0
    current_page: int = 0
    last_opened: str = ""
    is_favorite: bool = False


@dataclass(frozen=True)
class InkPoint:
    x: float
    y: float


def normalize_pdf_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def book_key(path: str | Path) -> str:
    return hashlib.sha256(normalize_pdf_path(path).encode("utf-8")).hexdigest()[:20]


def safe_json(value, fallback):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return fallback


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def page_label(page_index: int, pages: int) -> str:
    if pages <= 0:
        return "0 / 0"
    return f"{max(1, min(pages, page_index + 1))} / {pages}"
