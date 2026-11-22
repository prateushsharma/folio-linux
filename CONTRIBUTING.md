# Contributing to Folio-Linux

Thank you for helping make reading on Linux more enjoyable.

1. Create a branch: `git switch -c feature/your-feature`.
2. Keep original PDFs immutable. Write annotations via `Library` and export explicitly.
3. Protect RAM usage: never allocate raster images for offscreen pages or start a browser engine at launch.
4. Write tests for persistent data and PDF behavior in `tests/`.
5. Run `python -m pytest -q` in an environment with dependencies installed.
6. Test keyboard and mouse interactions on both X11 and Wayland if possible.
7. Use descriptive commits and open a pull request.

If you are adding third-party libraries, review their licenses and packaging requirements first. Folio is AGPL-3.0.
