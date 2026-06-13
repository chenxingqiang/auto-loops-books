# Deep rewrite brief — ch13

**Title:** Core Theory: AI Compiler Optimization Principles
**Gold standard:** `ch01` + `books/WRITING_STYLE.md`

## Machine pass (done by `book-loop deep-rewrite`)

1. Strip template / batch filler
2. Section-aligned prose scaffold (`book_prose_upgrade.py`)
3. Proper nouns, facts, citations, visuals, compile

## Agent pass — rewrite each section to ch01 density

Per section: problem-first hook → HW constraint → compile/kernel fix → multi-HW delta → cited metric or worked example.

### 1. `tiling_theory` — tiling theory

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `tiling`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:tiling_theory}` or `sec:ch13_tiling_theory`

### 2. `fusion_theory` — fusion theory

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `fusion`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:fusion_theory}` or `sec:ch13_fusion_theory`

### 3. `layout_theory` — layout theory

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `layout`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:layout_theory}` or `sec:ch13_layout_theory`

### 4. `parallel_scheduling` — parallel scheduling

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `parallel`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:parallel_scheduling}` or `sec:ch13_parallel_scheduling`

### 5. `gpu_cpu_npu_split` — GPU CPU NPU split

- **Spec bullet:** (see Chinese spec)
- **Coverage patterns:** `gpu, cpu, npu`
- **Target:** ≥3 paragraphs + optional table/example; no template rotation
- **Anchor:** `\label{sec:gpu_cpu_npu_split}` or `sec:ch13_gpu_cpu_npu_split`

