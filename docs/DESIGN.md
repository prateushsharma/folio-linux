# Design principles

**Reading first.** Keep the page centered and remove distractions. Only activate study tools when the user chooses them.

**Warm and calm.** Folio's palette uses paper white `#f7f5f1`, slate `#202c38`, and terracotta `#b96e49`. Book covers use distinct subdued colors rather than loud gradients.

**A native app, not an embedded web frontend.** Qt Widgets enables fluid scrollbars, context menus, windowing and keyboard shortcuts without a required browser runtime.

**Predictable opening flows.** `folio` shows library; `folio /path/book.pdf` opens that book immediately; `folio --page 30 book.pdf` starts at page 30. Reopening returns to the saved page by default.

**Refuse hidden data loss.** Reader progress and annotations are committed independently from PDFs, exports create another file, and personal data remains on the user's computer.
