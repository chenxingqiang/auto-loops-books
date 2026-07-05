## Gate (2026-07-05)
`python3 book_prepare.py --chapter ch08` → cov=100% words=**5000** q=**94.0** compile_ok figures=6 tables=6 visual_missing=∅

## Gap summary (from user content audit)
- Chapter 1 numbering / placeholder refs → `\label{chap:ch08}` + Ch3/4/5/6/7/9/20 bridges
- GPU/NPU/CPU hardware repetition → **deleted**; forward refs to Ch4–6
- Citation stuffing → ≤2 cites/paragraph, 19 total
- Prefill bias → decode-first depth worksheet + prologue accounting + anti-pattern 5
- Flat hardware essay → **pipeline landing path**: hook → 3-step depth → tri-hardware → YiRage pass → joint budget → pitfalls → patterns → review → benchmarking

## Section map
| Section | Label |
|---------|-------|
| Industrial hook (8.0) | `sec:industrial_hook` |
| Depth decision method (8.1) | `sec:ch08_pipeline_theory` |
| GPU TMA decode (8.2) | `sec:ch08_gpu_tma` |
| CPU async pipeline (8.3) | `sec:ch08_cpu_dma` |
| NPU spatial pipeline (8.4) | `sec:ch08_npu_pipeline` |
| Joint budget Ch6–7 | `sec:ch08_joint_budget` |
| YiRage pipeline pass (8.5) | `sec:ch08_yirage_pipeline_gen` |
| Pitfalls + checklist (8.6) | `sec:ch08_pipeline_pitfalls` |
| Engineering patterns | `sec:ch08_pipeline_patterns` |
| Review workflow | `sec:ch08_pipeline_review` |
| Decode benchmarking | `sec:ch08_pipeline_benchmarking` |
| Key Takeaways | `sec:ch08_key_takeaways` |
| Conclusion (8.7) | `sec:ch08_conclusion` |

## Deliverables added
- Figures: `fig:pipeline_theory_pipeline`, `fig:ch08_depth_latency`, `fig:gpu_tma_architecture`, `fig:ch08_tri_hw_pipeline`, `fig:ch08_multi_stream_timeline`, `fig:ch08_yirage_pipeline_pass`
- Tables: `tab:ch08_depth_worked_example`, `tab:ch08_tri_hw_pipeline`, `tab:ch08_cross_hw_decode`, `tab:ch08_pipeline_economics`, `tab:ch08_pipeline_pass_io`, `tab:ch08_pr_template`
- 3-step pipeline depth decision + Llama-3.2-1B@H100 worksheet
- 6 engineering patterns + 5 anti-patterns + 6-item checklist
- TMA vs cp.async boundary, multi-stream weight/KV, barrier walkthrough
- Bridge to Ch9 hierarchical sync + Ch20 megakernel search
