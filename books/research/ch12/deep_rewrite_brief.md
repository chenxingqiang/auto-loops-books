# Deep rewrite brief — ch12

**Title:** Three Kernel Execution Modes
**Gold standard:** `ch01` + `books/WRITING_STYLE.md`

## Machine pass (done by `book-loop deep-rewrite`)

1. Strip template / batch filler
2. Section-aligned prose scaffold (`book_prose_upgrade.py`)
3. Proper nouns, facts, citations, visuals, compile

## Agent pass — rewrite each section to ch01 density

Per section: problem-first hook → HW constraint → compile/kernel fix → multi-HW delta → cited metric or worked example.

### 1. `eager_mode` — eager mode

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `eager, pytorch`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:eager_mode}` or `sec:ch12_eager_mode`

### 2. `graph_mode` — graph mode

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `cuda graph`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:graph_mode}` or `sec:ch12_graph_mode`

### 3. `megakernel_mode` — MegaKernel mode

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `megakernel`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:megakernel_mode}` or `sec:ch12_megakernel_mode`

### 4. `mode_selection` — mode selection

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `hardware, trade`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:mode_selection}` or `sec:ch12_mode_selection`

