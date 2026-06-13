# AI Compiler Performance Engineering — LaTeX book

English manuscript for the autobooks loop ([`program_books.md`](../program_books.md)). Typesetting uses book-specific notation in `notation.tex` and shared macros in `math_commands.tex`.

[![Build book PDF](https://github.com/chenxingqiang/auto-loops-books/actions/workflows/book.yml/badge.svg)](https://github.com/chenxingqiang/auto-loops-books/actions/workflows/book.yml)

## Build

**Local:** requires `pdflatex` and `bibtex`.

**CI:** push to `master` runs [`.github/workflows/book.yml`](../.github/workflows/book.yml) → `books/main.pdf` artifact (no local TeX needed).

```bash
bash make.sh                    # full book → main.pdf (OUTLINE order via main.tex)
bash make-chapter.sh ch01       # standalone chapter → pdf/ch01.pdf
bash make-chapter.sh --all      # pdf/ch01.pdf, pdf/ch02.pdf, pdf/ch03.pdf
uv run python build_chapter.py --sync-main --main
```

`sync_main_tex_inputs()` in `book_prepare.py` keeps `main.tex` `\input{build/chapters/...}` order aligned with `OUTLINE`.

| Output | Contents |
|--------|----------|
| `main.pdf` | Cover + notation + all chapters in OUTLINE order + bibliography |
| `pdf/chXX.pdf` | Single-chapter PDF (`make-chapter.sh`) |

The loop runs compile via `book-loop step` → `book_prepare.compile_book()` (900s timeout; auto-syncs `main.tex`).

## Layout

| Path | Role |
|------|------|
| `cover.pdf` | Front cover (7in×9in / 504×648pt; run `bash resize_cover.sh` after replacing art) |
| `main.tex` | Document class, front matter, `\input{build/chapters/...}` order |
| `build/chapters/*.tex` | **Mutable** chapter prose (agent-edited) |
| `book.bib` | Core curated bibliography (seed entries) |
| `citations_merged.bib` | Auto-merged `book.bib` + all `research/chXX/chapter.bib` |
| `settings.tex` | Page geometry, fonts, chapter style |
| `math_commands.tex` | Shared math macros |
| `notation.tex` | Book-specific notation reference (LLM serving, metrics, compiler/GPU) |
| `visuals_style.tex` | TikZ palette (grayscale default; `\Colortrue` for color) |
| `visuals_macros.tex` | `\input` from `main.tex`; figure/table style helpers |

> **Path note:** Canonical manuscript lives under **`build/chapters/`**. Legacy `books/chapters/` is not used when `build/chapters/` exists (`book_prepare.CHAPTERS`).

## Autobooks outputs (do not hand-edit blindly)

| Path | Produced by |
|------|-------------|
| `research/<chapter_id>/` | `research_tools.py` / `book-loop step` |
| `research/<chapter_id>/verified_facts.jsonl` | Fact gate — web-verified claims + URLs |
| `research/<chapter_id>/chapter.bib` | `citation-loop plan` (≥25 papers per chapter) |
| `research/<chapter_id>/citation_bindings.jsonl` | Sentence ↔ `bib_key` bindings |
| `research/<chapter_id>/citation_strict_report.json` | Strict gate (papers, bindings, unbound ratio) |
| `visuals/<chapter_id>/plan.json` | `book_visuals.py --plan` |
| `visuals/<chapter_id>/generated/*.tex` | `book_visuals.py --render` |

### Per-chapter citation loop

```bash
# Plan + strict verify (Crossref; add SERPAPI_KEY for Scholar)
uv run citation-loop loop --all --crossref-only --min-papers 25

# Quality filter + apply \citep{}
uv run citation-loop enrich-tiers --all
uv run citation-loop apply --all --tier-a-only --prune-non-tier-a
uv run citation-loop merge-bib --tier-a-only
```

`main.tex` uses `\bibliography{book,citations_merged}`. Bindings are keyword-scored against full chapter text; figure/table blocks are skipped on apply.

Auto-inserted snippets are marked in chapter files:

```latex
\label{sec:prefill_decode}
% AUTO_VISUAL:fig_prefill_decode_pipeline
\begin{figure}...
```

Re-run `uv run book-loop insert-visuals --chapter ch01` to sync after plan changes.

## Chapters (OUTLINE)

**Status:** `uv run book-loop status` — currently **30/30** chapters pass gates (Parts I–VIII).

| Part | IDs | Theme |
|------|-----|-------|
| I | ch01–02 | Mindset / dataflow |
| II | ch03 | Hardware constraints |
| III | ch04–05 | CUDA Hopper + XDNA/AIE |
| IV | ch06–09 | MegaKernel core |
| V | ch10–12 | MegaKernel implementation |
| VI | ch13–21 | AI compilers + benchmarks |
| VII | ch22–27 | Production + future trends |
| VIII | ch28–30 | Frameworks, YiRage runtime, co-design |

Gold voice references: **ch01** (book rhythm), **ch12–13** (Fregly depth), [`reference-chapter-1.pdf`](../reference-chapter-1.pdf) (O'Reilly skeleton). List rubric: `uv run book_prepare.py --list`. Full 目录: [`book_content.md`](../book_content.md).

Example paths:

| ID | File |
|----|------|
| ch01 | `build/chapters/ch01_llm_decode_bottlenecks.tex` |
| ch28 | `build/chapters/ch28_inference_frameworks.tex` |
| ch30 | `build/chapters/ch30_framework_compiler_runtime.tex` |

## Fact verification

Numeric claims and worked examples require **web verification** (≥2 searches, cross-check) before publication. Log URLs in `research/<chapter_id>/verified_facts.jsonl`. Protocol: [`WRITING_STYLE.md`](WRITING_STYLE.md) §八（事实核验门禁）.

## Writing rules

All prose must follow [`WRITING_STYLE.md`](WRITING_STYLE.md):

- Problem-first openings (no textbook definitions)
- Hardware constraint → bottleneck → compile/kernel fix → multi-hardware delta
- Citations tied to benchmarks and architecture docs
- Key Takeaways + Conclusion (no legacy `Chapter Summary`)

## Evaluation

```bash
uv run book_prepare.py --chapter ch01
python3 book_pad_dedup.py --audit --range 14-27
uv run book-loop status
```

Metrics feed `quality_score` and `book-loop` completion gates. See root [`README.md`](../README.md#loops-a-book--autonomous-technical-book-writing).

## Template credit

Base notation files from the Deep Learning book open template (`dlbook_notation`). Book-specific extensions: `visuals_style.tex`, `visuals_macros.tex`, chapter content.
