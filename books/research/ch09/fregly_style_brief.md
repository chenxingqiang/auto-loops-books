## Gate (2026-07-05)
`python3 book_prepare.py --chapter ch09` → cov=100% words=**5000+** q=**94+** compile_ok figures=6 tables=6 visual_missing=∅

## Gap summary (from user content audit)
- Chapter 1 numbering / placeholder refs → `\label{chap:ch09}` + Ch3/4/5/6/7/8/10 bridges
- GPU/NPU/CPU hardware repetition → **deleted**; forward refs to Ch4–5/8
- Citation stuffing → ≤2 cites/paragraph target; 18 total
- Flat concept essay → **sync design path**: hook → scope ladder → tri-hardware → deadlock → YiRage pass → joint budget → pitfalls → patterns → review → benchmarking → megakernel composition
- Missing engineering depth → H100 cost ladder, Llama decode worksheet, mbarrier ring walkthrough, static analysis steps, Nsight interpretation, hang bisect

## Section map
| Section | Label |
|---------|-------|
| Industrial hook (9.0) | `sec:industrial_hook` |
| Sync hierarchy (9.1) | `sec:ch09_sync_hierarchy` |
| Tri-hardware sync (9.2) | `sec:ch09_hardware_sync_pick` |
| Deadlock detection (9.3) | `sec:ch09_deadlock_detection` |
| Joint budget Ch6–8 | `sec:ch09_joint_budget` |
| YiRage sync pass (9.4) | `sec:ch09_yirage_sync_pass` |
| Pitfalls + checklist (9.5) | `sec:ch09_sync_pitfalls` |
| Engineering patterns | `sec:ch09_sync_patterns` |
| Review workflow | `sec:ch09_sync_review` |
| Decode benchmarking | `sec:ch09_sync_benchmarking` |
| Megakernel composition | `sec:ch09_megakernel_composition` |
| Key Takeaways | `sec:ch09_key_takeaways` |
| Conclusion (9.6) | `sec:ch09_conclusion` |

## Deliverables added
- Figures: `fig:sync_hierarchy_pipeline`, `fig:ch09_sync_cost_ladder`, `fig:hardware_sync_pick_architecture`, `fig:ch09_tri_hw_sync`, `fig:ch09_deadlock_flow`, `fig:ch09_yirage_sync_pass`
- Tables: `tab:ch09_sync_cost_ladder`, `tab:ch09_sync_economics`, `tab:ch09_tri_hw_sync` (**6-dim overview at §9.2 open**: primitives, scheduling, cost, decode rules, deadlock proof; footnotes to `sec:ch08_gpu_tma`, `sec:ch05_static_dataflow_rules`), `tab:ch09_deadlock_checks`, `tab:ch09_sync_pass_io`, `tab:ch09_pr_template`
- H100 sync cost ladder + decode economics table
- Llama-3.2-1B decode sync audit worksheet
- mbarrier ring walkthrough (D=2)
- Five-step static analysis algorithm
- 6 engineering patterns + 5 anti-patterns (decode notes) + 7-item checklist
- Bridge to Ch10 online softmax + Ch20 megakernel search
