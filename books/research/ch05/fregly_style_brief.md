## Gate (2026-07-05)
`python3 book_prepare.py --chapter ch05` → cov=100% words=5000+ q≥94 compile_ok figures=2 tables=8

## Gap summary (from user content audit)
- Wrong chapter numbering / placeholder refs → fixed via `\label{chap:ch05}` + Ch3–4/6 bridges
- Post–1.8 duplicate boilerplate (~lines 250–375 old file) → **deleted** entire auto-repeat block
- Citation stuffing (10+ cites/paragraph) → trimmed to ≤2 per paragraph, 16 total
- Benchmark bloat vs Ch1–4 → slim 4-class verification + Appendix A pointer
- Handbook catalog → optimization-path narrative (hook → rules → map → practice → gates → verify)

## Section map
| Section | Label |
|---------|-------|
| Industrial hook | `sec:industrial_hook` |
| XDNA tiles | `sec:ch05_xdna_tiles` |
| Static dataflow rules | `sec:ch05_static_dataflow_rules` |
| CUDA→XDNA mapping | `sec:ch05_cuda_xdna_mapping` |
| Online softmax HW | `sec:ch05_online_softmax_hw` |
| Architecture tradeoffs | `sec:ch05_architecture_tradeoffs` |
| Dataflow conclusion | `sec:ch05_dataflow_conclusion` |
| YiRage XDNA backend | `sec:ch05_yirage_xdna_backend` |
| Review gates | `sec:ch05_review_gates` |
| Benchmark (slim) | `sec:ch05_ryzen_benchmark` |
| Key Takeaways | `sec:ch05_key_takeaways` |
| Conclusion | `sec:ch05_conclusion` |

## Deliverables added
- `tab:ch05_static_rules`, `tab:ch05_tile_budget`, `tab:ch05_worked_results`
- `tab:yirage_xdna_lowering` with pass I/O
- 6 engineering patterns (Scene/Solution/Benefit/Notes)
- 5 review gates with Symptom/Debug
- Key Takeaways: principle + Action (5 items)
