## Gate (2026-07-05)
`python3 book_prepare.py --chapter ch06` → cov=100% words=5000+ q≥94 compile_ok figures=6 tables=5 visual_missing=∅

## Gap summary (from user content audit)
- Chapter 1 numbering / `Chapter ??` placeholders → full restructure as Ch6 with `\label{chap:ch06}`
- GPU/NPU/CPU hardware spec repetition (228KB, TMA, XDNA tiles) → **deleted**; forward refs to Ch3–5
- Citation stuffing → ≤2 cites/paragraph, 18 total
- Flat hardware catalog → **design-flow narrative**: hook → 4-step workflow → tri-hardware adapt → worked example → YiRage pass → patterns → pitfalls
- Missing cross-hardware case → `tab:ch06_tri_hw_allocation` + `tab:ch06_peak_footprint` + `tab:ch06_gpu_peak_line_items`
- YiRage pass shallow → pipeline fig + I/O table + Mirage closed loop + overflow strategies
- Key Takeaways → principle + Action (5 items)

## Section map
| Section | Label |
|---------|-------|
| Industrial hook (6.0) | `sec:industrial_hook` |
| Lifetime four-step workflow (6.1) | `sec:ch06_lifetime_planning` |
| Tri-hardware adaptation (6.2) | `sec:ch06_tri_hardware_residency` |
| GPU adaptation | `sec:ch06_gpu_residency` |
| CPU adaptation | `sec:ch06_cpu_residency` |
| NPU adaptation | `sec:ch06_npu_residency` |
| Cross-hardware worked example (6.3) | `sec:ch06_cross_hw_worked_example` |
| YiRage memory pass (6.4) | `sec:ch06_yirage_memory_pass` |
| Engineering patterns | `sec:ch06_residency_patterns` |
| Review workflow | `sec:ch06_residency_review` |
| Pitfalls + checklist (6.5) | `sec:ch06_residency_pitfalls` |
| Key Takeaways | `sec:ch06_key_takeaways` |
| Conclusion (6.6) | `sec:ch06_conclusion` |

## Deliverables added
- Figures: `fig:ch06_residency_workflow`, `fig:ch06_lifetime_timeline`, `fig:ch06_tri_hw_tiers`, `fig:gpu_residency_architecture`, `fig:ch06_yirage_memory_pass`, `fig:lifetime_planning_pipeline`
- Tables: `tab:ch06_residency_tiers`, `tab:ch06_tri_hw_allocation`, `tab:ch06_peak_footprint`, `tab:ch06_memory_pass_io`, `tab:ch06_gpu_peak_line_items`
- 6 engineering patterns (Scene/Solution/Benefit/Notes)
- 5 anti-patterns (symptom/root cause/fix/prevention)
- 4 review gates (A–D)
- 8-item residency checklist
- Bridge to Ch7 static role assignment + Part IV prerequisites
