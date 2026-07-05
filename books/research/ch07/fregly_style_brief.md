## Gate (2026-07-05)
`python3 book_prepare.py --chapter ch07` → cov=100% words=5000+ q≥94 compile_ok figures=6 tables=6 visual_missing=∅

## Gap summary (from user content audit)
- Chapter 1 numbering / placeholder refs → `\label{chap:ch07}` + Ch4/5/6/8/20 bridges
- GPU/NPU hardware + residency repetition → **deleted**; forward refs to Ch4–6
- Citation stuffing → ≤2 cites/paragraph, 18 total
- FA3/prefill bias → decode-first ratio worksheet + anti-pattern 5
- Flat concept essay → **staticization landing path**: hook → principles → 3-axis decision → tri-hardware → L1–L3 ladder → YiRage tiling pass → pitfalls

## Section map
| Section | Label |
|---------|-------|
| Industrial hook (7.0) | `sec:industrial_hook` |
| Static roles principles (7.1) | `sec:ch07_static_roles` |
| Joint residency (Ch6 coupling) | `sec:ch07_joint_residency` |
| Quantitative decision (7.2) | `sec:ch07_role_decision` |
| Tri-hardware mapping (7.3) | `sec:ch07_tri_hw_role_mapping` |
| GPU mapping | `sec:ch07_thread_mapping` |
| Staticization ladder (7.4) | `sec:ch07_static_levels` |
| No runtime sched (dispatch table) | `sec:ch07_no_runtime_sched` |
| YiRage tiling pass (7.5) | `sec:ch07_yirage_tiling` |
| Pitfalls + checklist (7.6) | `sec:ch07_role_pitfalls` |
| Engineering patterns | `sec:ch07_role_patterns` |
| Review workflow | `sec:ch07_role_review` |
| Key Takeaways | `sec:ch07_key_takeaways` |
| Conclusion (7.7) | `sec:ch07_conclusion` |

## Deliverables added
- Figures: `fig:static_roles_pipeline`, `fig:ch07_producer_consumer_timeline`, `fig:thread_mapping_architecture`, `fig:ch07_tri_hw_roles`, `fig:ch07_static_levels`, `fig:ch07_yirage_tiling_pass`
- Tables: `tab:ch07_role_worked_example`, `tab:ch07_tri_hw_roles`, `tab:ch07_static_levels`, `tab:ch07_dispatch`, `tab:ch07_tiling_pass_io`, `tab:ch07_static_economics`
- 3-axis decision framework (ratio, register skew, barriers)
- 6 engineering patterns + 5 anti-patterns + 6-item checklist
- L1/L2/L3 staticization ladder with qualitative economics
- Bridge to Ch8 TMA pipelines + Ch20 megakernel search
