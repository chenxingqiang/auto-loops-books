# Deep rewrite brief — ch14

**Title:** MLIR: Modern Compiler Infrastructure
**Gold standard:** `ch01` + `books/WRITING_STYLE.md`

## Machine pass (done by `book-loop deep-rewrite`)

1. Strip template / batch filler
2. Section-aligned prose scaffold (`book_prose_upgrade.py`)
3. Proper nouns, facts, citations, visuals, compile

## Agent pass — rewrite each section to ch01 density

Per section: problem-first hook → HW constraint → compile/kernel fix → multi-HW delta → cited metric or worked example.

### 1. `mlir_hw_matrix` — MLIR HW matrix

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `hardware, target, matrix, gpu|cpu|npu`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:mlir_hw_matrix}` or `sec:ch14_mlir_hw_matrix`

### 2. `mlir_arch_passes` — MLIR arch passes

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `pass, lower, optim, dialect`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:mlir_arch_passes}` or `sec:ch14_mlir_arch_passes`

### 3. `mlir_codegen` — MLIR codegen

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `codegen, backend, platform, emit`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:mlir_codegen}` or `sec:ch14_mlir_codegen`

### 4. `mlir_tuning` — MLIR tuning

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `tun, profile, hardware, pitfall`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:mlir_tuning}` or `sec:ch14_mlir_tuning`

### 5. `mlir_case_study` — MLIR case study

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `case, benchmark, cross-hardware, yirage`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:mlir_case_study}` or `sec:ch14_mlir_case_study`

