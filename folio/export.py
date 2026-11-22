"""Export non-destructive Folio annotations to an ordinary portable PDF."""
from __future__ import annotations
from pathlib import Path
import fitz
from .storage import Library


def export_annotated_pdf(source: str | Path, target: str | Path, library: Library) -> int:
    source = Path(source).expanduser().resolve()
    target = Path(target).expanduser().resolve()
    if source == target:
        raise ValueError("Export must use a different filename to protect the original PDF.")
    pdf = fitz.open(str(source))
    count = 0
    try:
        for record in library.annotations(str(source)):
            if not (0 <= record["page"] < pdf.page_count):
                continue
            page = pdf[record["page"]]
            data = record["payload"]
            kind = record["kind"]
            annot = None
            if kind in ("ink", "marker"):
                points = [[float(x), float(y)] for x, y in data.get("points", [])]
                if len(points) == 1:
                    points.append([points[0][0]+.1, points[0][1]+.1])
                if len(points) > 1:
                    annot = page.add_ink_annot([points])
                    color = fitz.utils.getColor("yellow") if kind == "marker" else fitz.sRGB_to_pdf(0xC6784C)
                    annot.set_colors(stroke=color)
                    annot.set_border(width=float(data.get("width", 2)))
                    annot.set_opacity(0.4 if kind == "marker" else 0.96)
            elif kind == "highlight":
                rects = [fitz.Rect(*r) for r in data.get("rects", [])]
                if rects:
                    # Standard highlight annotations are selectable by other PDF readers.
                    annot = page.add_highlight_annot(rects)
                    annot.set_colors(stroke=(1.0, .72, .14))
                    annot.set_opacity(.40)
            elif kind == "note":
                x, y = data.get("position", [12, 12])
                annot = page.add_text_annot(fitz.Point(x, y), data.get("text", ""))
            if annot:
                annot.update()
                count += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(str(target), garbage=3, deflate=True)
        return count
    finally:
        pdf.close()
