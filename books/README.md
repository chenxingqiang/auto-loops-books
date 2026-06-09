# AI Compiler Performance Engineering — LaTeX book

English manuscript for the autobooks loop ([`program_books.md`](../program_books.md)). Typesetting follows the [Deep Learning book](https://www.deeplearningbook.org) notation template (see `notation.tex`, `settings.tex`).

## Build

```bash
bash make.sh                    # full book → main.pdf (ch01 → ch02 → ch03 order)
bash make-chapter.sh ch01       # standalone chapter → pdf/ch01.pdf
bash make-chapter.sh --all      # pdf/ch01.pdf, pdf/ch02.pdf, pdf/ch03.pdf
uv run python build_chapter.py --sync-main --main
```

Requires `pdflatex` and `bibtex`. `sync_main_tex_inputs()` in `book_prepare.py` keeps `main.tex` `\input` order aligned with `OUTLINE` (fixes wrong chapter numbering).

| Output | Contents |
|--------|----------|
| `main.pdf` | Notation + all chapters in OUTLINE order + bibliography |
| `pdf/ch01.pdf` | Chapter 1 only (full prose + figures + bib) |
| `pdf/ch02.pdf` | Chapter 2 only |
| `pdf/ch03.pdf` | Chapter 3 only |

The loop runs compile via `book-loop step` → `book_prepare.compile_book()` (auto-syncs `main.tex`).

## Layout

| Path | Role |
|------|------|
| `main.tex` | Document class, front matter, `\input{chapters/...}` order |
| `chapters/*.tex` | **Mutable** chapter prose (agent-edited) |
| `book.bib` | Bibliography (agent + research ingest) |
| `settings.tex` | Page geometry, fonts, chapter style |
| `math_commands.tex` | Shared math macros |
| `notation.tex` / `notation.bib` | DL-book notation page |
| `visuals_style.tex` | TikZ palette (grayscale default; `\Colortrue` for color) |
| `visuals_macros.tex` | `\input` from `main.tex`; figure/table style helpers |

## Autobooks outputs (do not hand-edit blindly)

| Path | Produced by |
|------|-------------|
| `research/<chapter_id>/` | `research_tools.py` / `book-loop step` |
| `visuals/<chapter_id>/plan.json` | `book_visuals.py --plan` |
| `visuals/<chapter_id>/generated/*.tex` | `book_visuals.py --render` |

Auto-inserted snippets are marked in chapter files:

```latex
\label{sec:prefill_decode}
% AUTO_VISUAL:fig_prefill_decode_pipeline
\begin{figure}...
```

Re-run `uv run book-loop insert-visuals --chapter ch01` to sync after plan changes.

## Chapters (current OUTLINE)

| ID | File | Status |
|----|------|--------|
| ch01 | `chapters/ch01_llm_decode_bottlenecks.tex` | Gold-standard voice reference |
| ch02 | `chapters/ch02_dataflow_mindset.tex` | In progress |
| ch03 | `chapters/ch03_hardware_constraints.tex` | In progress |

List rubric: `uv run book_prepare.py --list`. Full 目录: [`AI Compiler Performance Engineering.md`](../AI%20Compiler%20Performance%20Engineering.md).

## Fact verification

Numeric claims and worked examples require **web verification** (≥2 searches, cross-check) before publication. Log URLs in `research/<chapter_id>/verified_facts.jsonl`. See [`FACT_VERIFICATION.md`](FACT_VERIFICATION.md).

## Writing rules

All prose must follow [`WRITING_STYLE.md`](WRITING_STYLE.md):

- Problem-first openings (no textbook definitions)
- Hardware constraint → bottleneck → compile/kernel fix → multi-hardware delta
- Citations tied to benchmarks and architecture docs
- Tone aligned with ch01

## Evaluation

```bash
uv run book_prepare.py --chapter ch01
```

Metrics feed `quality_score` and `book-loop` completion gates. See root [`README.md`](../README.md#loops-a-book--autonomous-technical-book-writing).

## Template credit

Base notation files from the Deep Learning book open template (`dlbook_notation`). Book-specific extensions: `visuals_style.tex`, `visuals_macros.tex`, chapter content.
