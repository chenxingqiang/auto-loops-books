# Loops a Book — `book-loop` orchestrator

Autonomous full-book iteration for *AI Compiler Performance Engineering*. Implements the machine phases from [`program_books.md`](../program_books.md); the coding agent completes `agent_tasks` between steps.

```
pick chapter → research → visuals → compile → evaluate → agent_tasks → (repeat)
```

## Install & entry points

```bash
uv sync
uv run book-loop status          # after sync: console script
uv run python book_loop.py step  # equivalent thin wrapper
```

Package: `loops.iterate:main` (see `pyproject.toml` → `[project.scripts]`).

## Commands

### `status`

Show book progress and per-chapter backlog.

```bash
uv run book-loop status
uv run book-loop status --pick weakest
```

Output includes `Book progress: N/M chapters ready`, per-chapter `open`/`ready`, priority, coverage, words, citations, figures, and **Next focus**.

### `step`

Run one full machine pipeline on the focus chapter.

```bash
uv run book-loop step
uv run book-loop step --chapter ch01
uv run book-loop step --skip-research
uv run book-loop step --research-dry-run
uv run book-loop step --skip-compile
uv run book-loop step --pick weakest
```

**Phases executed:**

1. **Stub** — create `books/chapters/<file>.tex` + `main.tex` `\input` if missing
2. **Research** — `research_tools` (or keywords/queries only without `SERPAPI_KEY`)
3. **Visuals** — `book_visuals` plan → render → auto-insert at `\label{sec:...}`
4. **Compile** — `books/make.sh`
5. **Evaluate** — `book_prepare.evaluate_chapter`
6. **Log** — append `book_results.tsv`, write `loops/loop_state.json`

Exit code `1` if any phase errors (e.g. compile failure).

### `run`

Multiple steps in one invocation.

```bash
uv run book-loop run --max-steps 10
uv run book-loop run --max-steps 5 --bootstrap-only --skip-research
uv run book-loop run --chapter ch01 --max-steps 3
```

| Flag | Behavior |
|------|----------|
| `--bootstrap-only` | Without `--chapter`, touches each OUTLINE entry once (ch01 → ch02 → ch03) then stops |
| (default) | Re-runs focus chapter each step until `--max-steps` or all OUTLINE ready |

Stops early when `phase == complete` (all OUTLINE chapters pass gates).

### `deep-rewrite`

Single-chapter depth loop: machine scaffold + agent brief for ch01-level prose.

```bash
uv run book-loop deep-rewrite --chapter ch14
uv run book-loop deep-rewrite --chapter ch05 --skip-research --skip-compile
uv run book-loop deep-rewrite --chapter ch01 --skip-prose   # agent-only brief + gates
```

**Requires `--chapter`** (one OUTLINE id).

**Machine phases (in order):**

1. **Brief** — `books/research/<id>/deep_rewrite_brief.md` (per-section spec bullets + rewrite targets)
2. **Prose scaffold** — strip batch filler + `book_prose_upgrade.py` section rewrite
3. **Proper nouns** — fix chapter `.tex`
4. **Research** — optional (`--skip-research`)
5. **Facts / refs / citations** — verify + redistribute + merge bib
6. **Visuals** — plan → render → insert
7. **Compile + evaluate** — optional (`--skip-compile`)

**Agent pass:** edit tasks from `loop_state.json`; rewrite each section using the brief and ch01 rhythm. Re-run until `quality_score` ≥ 85.

### `insert-visuals`

Plan, render, and insert snippets for one chapter (no full step).

```bash
uv run book-loop insert-visuals --chapter ch01
```

## Chapter selection

| Mode | Flag | Behavior |
|------|------|----------|
| **sequential** (default) | `--pick sequential` | First `OUTLINE` chapter that fails `chapter_ready` |
| **weakest** | `--pick weakest` | Highest `priority` score among incomplete chapters |

Explicit `--chapter` overrides both.

### `chapter_ready` gates

All must pass before the sequential pointer advances:

- `coverage_pct` == 100
- `word_count` >= `min_words` (from `book_prepare.OUTLINE`)
- `citation_count` >= `min_citations`
- `visual_missing` empty
- `compile_ok` true

## Outputs

| File | Purpose |
|------|---------|
| [`loop_state.json`](loop_state.json) | Last step: `actions`, `evaluation`, **`agent_tasks`**, `errors` |
| [`../book_results.tsv`](../book_results.tsv) | Tab-separated experiment log (`keep` / `discard` / `crash`) |
| [`../books/research/<id>/`](../books/research/) | Keywords, queries, papers, `search_data.json` |
| [`../books/visuals/<id>/`](../books/visuals/) | `plan.json`, `generated/*.tex` |

`loop_state.json` is gitignored under `loops/` (local run state).

## `agent_tasks` (LLM work)

Every `step` emits a task list. Typical items:

1. **Voice** — follow [`books/WRITING_STYLE.md`](../books/WRITING_STYLE.md); gold standard ch01
2. **Facts** — web-verify every number/example (≥2 searches); log URLs in `books/research/<id>/verified_facts.jsonl` per [`FACT_VERIFICATION.md`](../books/FACT_VERIFICATION.md)
3. **Style fix** — forbidden lecture phrases detected in chapter `.tex`
4. **Fact check** — uncited numeric paragraphs flagged by soft lint
5. **Sections** — expand missing `OUTLINE` sections with cited prose
6. **Words / citations** — meet per-chapter minimums
7. **Bib** — ingest `books/research/<id>/search_data.json`; bib `url` must match verification log
8. **Visuals** — refine or context-wrap auto-inserted figures/tables

When all OUTLINE chapters are ready, tasks include extending `book_prepare.OUTLINE` from the Chinese spec (ch04+).

## Full-book workflow

```bash
# 1. Progress
uv run book-loop status

# 2. Machine step
uv run book-loop step

# 3. Agent: edit loops/loop_state.json tasks → chapters/*.tex, book.bib

# 4. Verify
cd books && bash make.sh
uv run book_prepare.py --chapter ch01

# 5. Git keep/revert per program_books.md

# 6. Repeat until ch01 ready → ch02 → ch03 → extend OUTLINE
```

### One-shot bootstrap (new clone)

```bash
export SERPAPI_KEY=...   # optional
uv run book-loop run --max-steps 5 --bootstrap-only --skip-research
```

Creates stubs, visual plans, and generated TikZ for ch01–ch03 without expecting prose between runs.

## Related tools (called by orchestrator)

| Script | CLI examples |
|--------|----------------|
| [`book_prepare.py`](../book_prepare.py) | `--list`, `--chapter ch01` |
| [`research_tools.py`](../research_tools.py) | `--chapter ch01`, `--all`, `--dry-run` |
| [`book_visuals.py`](../book_visuals.py) | `--plan`, `--render`, `--audit` |

## Implementation

- [`iterate.py`](iterate.py) — `pick_focus_chapter`, `run_step`, `build_agent_tasks`, `fact_verification_tasks`, `insert_missing_visuals`
- [`book_loop.py`](../book_loop.py) — CLI shim

Do **not** change `book_prepare.py` scoring weights during loops; only extend `OUTLINE` when 目录 changes.
