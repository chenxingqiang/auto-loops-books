# autobooks — autonomous book iteration loop

**Docs:** [README.md](README.md) (overview) · [loops/README.md](loops/README.md) (CLI) · [books/README.md](books/README.md) (LaTeX layout)

An adaptation of [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) for technical book writing. The agent iterates **book outline (目录), chapter structure, and manuscript content** against a quality harness, keeping improvements and reverting regressions via git.

**Monorepo note:** Stage only files touched this session: `book_content.md`, `book_prepare.py` (when OUTLINE changed), `books/build/chapters/*.tex`, `books/book.bib`, `books/main.tex`, `books/research/<id>/`, and `book_results.tsv`. Never use blind `git add -A`.

## Setup

Work with the user to:

1. **Agree on a run tag**: e.g. `jun9`. Branch `autobooks/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autobooks/<tag>` from current master.
3. **Read in-scope files**:
   - `books/WRITING_STYLE.md` — **mandatory** unified voice (工程师叙事型硬核干货); gold standard = ch01; §八 fact gate (web-verify numbers; log `verified_facts.jsonl`).
   - `book_content.md` — full outline and style requirements (Chinese spec; output is English).
   - `book_prepare.py` — evaluation harness + `OUTLINE` rubric. **Extend `OUTLINE` when 目录 changes; do not change scoring weights or harness logic.**
   - `research_tools.py` — per-chapter literature search (auto-locks keywords; saves to `books/research/<id>/`). **Do not modify during loops** unless the user asks to fix the research harness itself.
   - `book_visuals.py` — per-chapter figure/table plan, audit, and LaTeX snippet render (`books/visuals/<id>/`).
   - `books/` — LaTeX template (Deep Learning book style). Mutable content lives in `books/build/chapters/*.tex`.
   - `program_books.md` — this protocol.
   - `loops/iterate.py` — **`uv run book-loop`** orchestrator (research + visuals + compile + evaluate).
4. **Configure research API** (required before live searches):
   ```bash
   export SERPAPI_KEY='your-serpapi-key'
   ```
   Dry-run keyword extraction works without a key: `uv run research_tools.py --chapter ch01 --dry-run`
5. **Verify build**: `cd books && bash make.sh` must succeed with current chapters.
6. **Initialize `book_results.tsv`**: header row + baseline entry after first successful compile + evaluation.
7. **Confirm and go**.

## What you CAN do

**目录 (outline / TOC) — iteratively refine:**

- Edit `book_content.md` — 全书目录、模块划分、章节 bullet、写作意图（中文 spec，可增删改章节与小节）。
- Edit `book_prepare.py` → `OUTLINE` only — add/rename/reorder chapters; add/adjust `SectionSpec` patterns when 目录或小节变化。**Keep evaluation formula unchanged.**
- Edit `books/main.tex` — `\input{}` order, `\part{}` / frontmatter title, new chapter stubs; TOC is auto-generated from `\chapter`/`\section` in chapter files.

**内容 (manuscript) — iteratively refine:**

- Edit `books/build/chapters/*.tex` — chapter prose, `\section`/`\subsection` structure, citations, tables.
- **Writing voice:** Every prose edit must follow `books/WRITING_STYLE.md` (problem-first, HW↔SW chain, multi-hardware deltas, no textbook lecturing). Match `ch01_llm_decode_bottlenecks.tex` rhythm.
- Create new `books/build/chapters/chXX_*.tex` when OUTLINE gains a chapter (stub → research → expand).
- Edit `books/book.bib` — citations from research.
- Run `research_tools.py` — `books/research/<chapter_id>/` (see **Literature research** below).
- Run `book_visuals.py` — plan/render figures and tables (see **Figures and tables** below).
- Edit `books/visuals/<chapter_id>/plan.json` — adjust visual specs before `--render`.

## What you CANNOT do

- Change `book_prepare.py` **scoring logic** (weights, `word_score`, `compile_book`, etc.) — only mutate the `OUTLINE` tuple and chapter/section specs.
- Modify template infrastructure: `math_commands.tex`, `notation.tex`, `settings.tex`, `natbib.bst`.
- Fabricate benchmark numbers. Use published measurements or clearly label projections/placeholders.
- Publish numeric facts or vendor examples **without** completing the fact-verification gate (see **Fact verification** below).
- Install new packages beyond what the LaTeX template already uses.

## Quality metric

Run: `uv run book_prepare.py --chapter <id>`

The harness prints a summary:

```
---
chapter:          ch01
coverage_pct:     87.5
word_count:       4200
citation_count:   12
compile_ok:       true
quality_score:    82.3
```

**`quality_score`** (0–100) combines:

| Component | Weight | Rule |
|-----------|--------|------|
| Section coverage | 40% | Required subsections from outline present |
| Word count | 20% | Target band per chapter type (see `book_prepare.py`) |
| Citations | 20% | Min unique `\citep`/`\citet` keys in `book.bib` |
| Compile | 20% | `make.sh` exits 0 |

Higher is better. A crash or failed compile → `quality_score: 0.000`.

## Logging results

Append to `book_results.tsv` (tab-separated):

```
commit	coverage_pct	word_count	citations	quality_score	status	description
```

- `status`: `keep`, `discard`, or `crash`
- On improvement: amend commit to include updated `book_results.tsv`
- On regression: `git reset --hard <previous kept commit>`

## Literature research (`research_tools.py`)

Research is **mandatory before writing or expanding** a chapter. Keywords are **auto-locked** from three sources — no manual keyword lists:

| Source | What it contributes |
|--------|---------------------|
| `book_prepare.OUTLINE` | Chapter title, section labels, coverage regex → English terms |
| `book_content.md` | `#### 第N章` bullets + Chinese→English term mapping |
| `books/build/chapters/<file>.tex` | `\section`, `\index`, `\newterm`, high-frequency body terms |

### Commands

```bash
# Preview locked keywords + queries (no API calls)
uv run research_tools.py --chapter ch01 --dry-run

# Full search for one chapter (no paper-count cap)
uv run research_tools.py --chapter ch01

# All chapters currently in OUTLINE (ch01–ch03)
uv run research_tools.py --all
```

Optional flags: `--min-relevance N` (default 1), `--max-pages-per-query N` (default: paginate until empty), `--query-delay SEC` (default 2).

### Output layout (per chapter)

```
books/research/<chapter_id>/
  keywords.json           # locked terms + weights
  queries.json            # Scholar queries used
  search_results.md       # full report (abstracts, scores)
  references.md           # sorted reference list
  section_references.md   # papers grouped by OUTLINE section label
  search_data.json        # structured payload for bib/cite workflow
  runs/<timestamp>/       # snapshot of each run (same files)
```

### Agent workflow: research → bib → write

1. **Run search** for the target chapter id.
2. **Read** `section_references.md` for the weakest/missing section; use `search_results.md` for abstracts and benchmark claims.
3. **Add bib entries** to `books/book.bib` from `search_data.json` fields: `title`, `reference`, `link`, `abstract`. Prefer arXiv/official docs; never fabricate numbers — copy only from paper abstract or linked source.
4. **Cite** in `.tex` with `\citep{key}`; map each new subsection to at least one external source.
5. **Re-run research** when a chapter draft changes substantially (new sections, major rewrites) so keywords track the updated `.tex`.

**Research rule:** Every new subsection needs at least one external citation unless it is pure methodology from this book's framework.

**No result cap:** Retrieval continues across all queries and Scholar pages until empty; relevance filtering only drops score-0 noise.

## Fact verification (mandatory before manuscript)

Any **factual description, measurement, vendor spec, or worked example** in `books/build/chapters/*.tex` must be **web-verified** before it ships. Training-data recall is not evidence.

### Gate (no exceptions)

1. **Identify the claim** — exact number, unit, product name, date, or configuration (model, batch, SL, hardware).
2. **Web search** — at least **two independent queries** (e.g. paper title + metric; vendor doc + third-party benchmark). Use `research_tools.py`, SerpAPI, or agent web search.
3. **Cross-check** — primary source (paper PDF, arXiv, official NVIDIA/AMD doc, peer-reviewed proceedings) **and** one corroborating source when possible. Resolve conflicts; do not average guesses.
4. **Record** — append one JSON line per claim to `books/research/<chapter_id>/verified_facts.jsonl`:

```json
{"claim":"847.5 kernels/token Llama-3.2-1B H100 BS4 SL2048","source_url":"https://arxiv.org/abs/2603.12465","corroboration_url":"https://arxiv.org/abs/2603.12465","bib_key":"taxbreak2026","verified_at":"2026-06-09","queries":["TaxBreak Llama kernels per token","TaxBreak arXiv 2603.12465"]}
```

5. **Cite in prose** — `\citep{bib_key}` adjacent to the claim; `book.bib` entry must include `url` or `howpublished` with the **same** link used in verification.
6. **Placeholders** — unverified numbers use `\vispending{…}` / table `TBD` / figure pending captions only; never present as facts.

Full protocol: [`books/WRITING_STYLE.md`](books/WRITING_STYLE.md) §八（事实核验门禁）. `book-loop step` adds `agent_tasks` for missing logs and uncited numeric paragraphs.

**Trusted source tiers (prefer top tiers):**

| Tier | Examples |
|------|----------|
| A | arXiv/OpenReview papers, ACM/IEEE proceedings, official vendor architecture whitepapers |
| B | Peer blogs with reproducible artifacts (GitHub harness, pinned configs) |
| C | Forum posts — **never** sole source for a number; use only to find Tier A/B |

**Loop enforcement:** `loops/iterate.py` → `fact_verification_tasks()`; soft-lint uncited numeric paragraphs; require `verified_facts.jsonl` per chapter with active prose.

## Figures and tables (`book_visuals.py`)

核心章节遵循中文 spec 的 **理论+源码+实测+跨硬件对比**：每章需配套 **表**（对比/实测/文献快照）与 **图**（数据流、roofline、架构示意）。图表与正文一样可迭代。

### Visual kinds

| Kind | Use for |
|------|---------|
| `comparison_table` | Qualitative contrasts (prefill vs decode, GPU vs NPU) |
| `benchmark_table` | Numeric measurements — **must** include `cite` and units |
| `reference_snapshot` | Literature metric rows (like verified-numbers tables) |
| `checklist_table` | Priority / constraint matrices |
| `pipeline_figure` | Phase or compiler pipelines (TikZ) |
| `roofline_figure` | Arithmetic intensity / bandwidth limits |
| `architecture_figure` | Memory hierarchy or operator graphs |
| `bar_figure` | Simple bar comparisons (kernels/token, latency) |
| `placeholder_figure` | Explicit pending slot — **never** invent benchmark bars |

### Commands

```bash
uv run book_visuals.py --list-kinds
uv run book_visuals.py --chapter ch01 --plan      # sync plan.json from OUTLINE section recipes + .tex labels
uv run book_visuals.py --chapter ch01 --audit       # tables/figures vs targets + missing ids
uv run book_visuals.py --chapter ch01 --render      # emit books/visuals/ch01/generated/*.tex
uv run book_visuals.py --chapter ch01 --render fig_roofline_decode
```

### Output layout

```
books/visuals/<chapter_id>/
  plan.json                 # visual specs (id, kind, section, label, caption, rows/stages…)
  generated/
    fig_roofline_decode.tex # paste into matching \section in chapters/*.tex
    tab_hw_priorities.tex
```

### Agent workflow: plan → render → insert → verify

1. After research, run `--plan` for the chapter (maps each `SectionSpec` to recommended tables/figures).
2. Run `--audit` — `book_prepare.py` also prints `table_count`, `figure_count`, `visual_missing`.
3. Fill `benchmark_table` / `bar_figure` cells only from `search_data.json` or cited papers; use `placeholder_figure` when Appendix B data is not ready.
4. `--render` missing ids; paste snippets under the matching `\section{}` in `books/build/chapters/*.tex`.
5. `cd books && bash make.sh` — TikZ figures require `tikz` in `main.tex` (already wired).
6. Re-run `--plan` to flip `status` to `done` when `\label{fig:...}` / `\label{tab:...}` appear in `.tex`.

**Table rule:** Every `benchmark_table` row must trace to a `\citep{}` or internal benchmark harness id.

**Figure rule:** Prefer TikZ (`pipeline_figure`, `roofline_figure`) for concepts; use `placeholder_figure` until measured data exists.

**Iteration:** When 目录 adds a section, extend `SECTION_VISUAL_RECIPES` in `book_visuals.py` (or edit `plan.json` directly), then `--plan --render`.

### Visual style (matching book template)

All generated figures/tables use **`books/visuals_style.tex`** — same palette across pipeline, roofline, bar, and placeholder figures:

| Token | Role |
|-------|------|
| `visPrimary` / `visFillPrimary` | Main series, compute roof, odd pipeline nodes |
| `visSecondary` / `visFillSecondary` | Bandwidth roof (dashed), even nodes/bars |
| `visAccent` | Placeholder borders |
| `visTableHead` | Table header row (`\visTableHeader`) |

- **Grayscale default** (no `\Colortrue` in `settings.tex`): print-safe `black!N` fills — matches DL book B&W mode.
- **Color mode:** set `\Colortrue` in `settings.tex` for steel-blue / teal / amber scheme.
- Do not hardcode `blue!20` or raw TikZ colors in chapters — use `--render` snippets or `visuals_style` tokens.

## Outline iteration (目录与结构同步)

全书 **目录** 与 **正文** 均可多轮迭代，但必须保持三层一致：

| Layer | File | Role |
|-------|------|------|
| 1 — Spec | `book_content.md` | 人类可读的全书目录与章节意图（source of intent） |
| 2 — Rubric | `book_prepare.py` → `OUTLINE` | 评测用章节 id、文件名、section 覆盖 regex |
| 3 — Book | `books/main.tex` + `books/build/chapters/*.tex` | 可编译 PDF；`\tableofcontents` 由 LaTeX 自动生成 |

### When to iterate 目录

- 调研发现新主题应独立成章（如新增编译器后端章节）
- 某章过长 → 拆成两章；两章过短 → 合并
- 大纲 bullet 与已写 `\section` 不对齐 → 优先统一 spec，再改 `.tex`
- 新增附录或调整篇章顺序（第一篇/第二篇…）

### Sync checklist (目录变更后必做)

1. **Spec** — update `book_content.md`（`#### 第N章`、bullets、模块表）
2. **Rubric** — add/update `ChapterSpec` + `SectionSpec` in `book_prepare.py` `OUTLINE`
3. **LaTeX** — create/rename chapter file; update `books/main.tex` `\input{}` order
4. **Research** — `uv run research_tools.py --chapter <new_or_changed_id>`
5. **Verify** — `cd books && bash make.sh` then `uv run book_prepare.py --list` and per-chapter eval

### Add a new chapter (template)

```
# book_prepare.py OUTLINE — new ChapterSpec(chapter_id, filename, title, min_words, max_words, min_citations, sections=...)
# books/build/chapters/ch04_xxx.tex — \chapter{English Title} + \section stubs matching SectionSpec labels
# books/main.tex — \input{chapters/ch04_xxx.tex} in correct order
```

Log outline changes in `book_results.tsv` `description` field, e.g. `outline: add ch04 mlir passes`.

## Experiment loop (`loops/iterate.py`)

**Entry point:** `uv run python book_loop.py` (or `uv run book-loop` after `uv sync`) — orchestrates research, visuals, compile, and evaluate; writes `loops/loop_state.json` with `agent_tasks` for LLM prose/bib work.

```bash
uv run python book_loop.py status
uv run python book_loop.py step
uv run python book_loop.py step --chapter ch01 --skip-research
uv run python book_loop.py run --max-steps 10
```

LOOP until the human stops you:

1. Read git state, `book_results.tsv`, and `loops/loop_state.json`.
2. **Run deterministic step:** `uv run python book_loop.py step` (or `--chapter <id>`).
   - Default `--pick sequential`: first OUTLINE chapter not yet `chapter_ready` (full-book order).
   - Optional `--pick weakest`: highest backlog among incomplete chapters.
   - Creates chapter stub + `main.tex` `\input` if missing.
   - **Research** → `research_tools` (or keywords-only if no `SERPAPI_KEY`).
   - **Visuals** → `book_visuals` plan + auto-insert `generated/*.tex` at `\label{sec:...}` + render.
   - **Compile** → `books/make.sh`
   - **Evaluate** → `book_prepare` metrics; append `book_results.tsv`.
3. **Complete `agent_tasks`** from `loop_state.json` (LLM-only):
   - Re-read `books/WRITING_STYLE.md`; align tone with ch01 before editing
   - Expand missing sections / word count / citations
   - Add `books/book.bib` from `books/research/<id>/search_data.json`
   - Edit `books/build/chapters/*.tex` (and 目录/OUTLINE/main.tex if needed)
4. **Outline iteration** when 目录 out of sync — manual checklist (see above), then re-run `book-loop step`.
5. Git **keep** if `quality_score` improved **or** structural sync succeeded; else **revert**.
6. Repeat — advance through all `OUTLINE` chapters (ch01–ch27 registered via `outline_extended.json`).

**Simplicity criterion:** Prefer one strong paragraph over three weak ones. Remove filler.

**NEVER STOP** once the loop begins. Alternate `book-loop step` (machine) with `agent_tasks` (writing) until the full book is covered.

## Chapter queue (living document)

`book_prepare.py --list` and `book_content.md` are the live sources — the table below is a **snapshot**, not a freeze:

| ID | File | Title |
|----|------|-------|
| ch01 | `ch01_llm_decode_bottlenecks.tex` | LLM Inference Bottlenecks |
| ch02 | `ch02_dataflow_mindset.tex` | Operator-Driven vs Dataflow-Driven |
| ch03 | `ch03_hardware_constraints.tex` | AI Hardware Architecture & Compiler Constraints |
| ch04–ch27 | `ch04_*.tex` … | Per spec — add to OUTLINE as writing progresses |
| app_a | `app_megakernel_source.tex` | Appendix A (stub until Ch.10–11 done) |

Write in order unless a later chapter unblocks an earlier one, or unless 目录迭代 explicitly reorders priorities.

## Output language

- **Primary manuscript:** English (`books/build/chapters/*.tex`).
- **Outline spec:** `book_content.md` is the source of truth for 目录与写作意图; keep it in sync with `OUTLINE` and LaTeX structure.
