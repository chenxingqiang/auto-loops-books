# AGENTS.md

## Cursor Cloud specific instructions

This repo currently contains only the **"Loops a Book" (autobooks)** loop — an autonomous
technical-book pipeline for *AI Compiler Performance Engineering*. The `autoresearch-mlx`
loop described in `README.md` is NOT present (`train.py`, `prepare.py`, `program.md` are
absent) and would require Apple Silicon, so ignore it on Linux cloud VMs.

### Toolchain (installed by the update script)
- Python deps are managed with **uv** (`uv sync`). Always invoke tools via `uv run ...`.
- `mlx` is a declared dependency but is only used by the (absent) MLX loop; it installs a
  Linux CPU wheel and is never imported by the book pipeline, so it is harmless.
- A LaTeX toolchain is required for compilation and for `book_prepare.py` scoring. The needed
  system packages are NOT in the update script (they are large, apt-level, and pre-baked into
  the VM snapshot): `texlive-latex-{base,recommended,extra}`, `texlive-fonts-recommended`,
  `texlive-pictures`, `texlive-science`, `texlive-binaries`, `texlive-bibtex-extra`
  (provides `breakcites.sty`), plus `cm-super` and `lmodern` (scalable Type1 fonts — without
  these, `microtype` font expansion aborts the build with "auto expansion is only possible
  with scalable fonts"). `poppler-utils` is handy for rasterizing PDFs to images.

### Running things (this is a CLI/batch tool, not a long-running service)
- Status / backlog: `uv run book-loop status`
- One machine step (research → visuals → compile → evaluate → log): `uv run book-loop step --chapter ch01`
  - Without a `SERPAPI_KEY`, add `--skip-research` (otherwise research falls back to
    keywords/queries only). Set `SERPAPI_KEY` as a secret to enable live Scholar search.
- Per-chapter quality score: `uv run book_prepare.py --chapter ch01` (recompiles the chapter
  internally, so it takes ~20–30s).
- Build PDFs from `books/`: `bash make.sh` (full `main.pdf`, ~20s, 495 pages) and
  `bash make-chapter.sh ch01` / `--all` (standalone chapter PDFs → `books/pdf/`).

### Gotchas
- Running `book-loop step` and `book_prepare.py` regenerates many tracked artifacts
  (`books/main.pdf`, `books/citations_merged.bib`, `books/build/chapters/*.tex`,
  `books/research/<id>/*.json`, `book_results.tsv`) and writes `loops/loop_state.json`
  (gitignored). These are normal pipeline outputs — do not commit them unless a content
  change is intended; `git restore` them after smoke-testing.
- `make.sh`/`pdflatex` use `-interaction=nonstopmode ... || true`, so a step can report
  `compile: ok` only because `book_prepare` checks for the output PDF afterwards. If a build
  silently produces no PDF, inspect `books/main.log` / `books/ch01.log` for the real error.
- There are no git hooks, lint, or automated test suites configured; the `quality_score`
  harness (`book_prepare.py`) is the effective acceptance gate. Do not change its scoring
  weights during loops (see `program_books.md`).
