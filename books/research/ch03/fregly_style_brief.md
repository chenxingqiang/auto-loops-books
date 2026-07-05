# ch03 Fregly style rewrite brief (2026-07-05)

## Gap summary
- Flat parameter dump → industrial hook + constraint→impact→debug loops
- Review gate → 实践验收点 (practice checkpoint)
- Add tri-hardware summary table + 3 memory hierarchy figures + compile flow
- Terminology bridge (SIMT, WGMMA, TMA, NUMA, DMA)
- Key Takeaways → principle + action
- Bridge ch02 dataflow → hardware constraints; conclusion → ch04 Hopper

## Section map
| Section | Label |
|---------|-------|
| Industrial hook | `sec:industrial_hook` |
| Hardware landscape | `sec:hardware_landscape` |
| Constraint matrix | `sec:constraint_matrix` |
| GPU constraints | `sec:gpu_constraints` |
| CPU constraints | `sec:cpu_constraints` |
| NPU constraints | `sec:npu_constraints` |
| Hardware-aware compile | `sec:hardware_aware_compile` |
| Benchmark method | `sec:benchmark_method` |
| YiRage modeling | `sec:yirage_modeling` |
| Key Takeaways | `sec:ch03_key_takeaways` |
| Conclusion | `sec:ch03_conclusion` |
| Migration mistakes | `sec:migration_mistakes` |

## Gate (2026-07-05)
`python3 book_prepare.py --chapter ch03` → cov=100% words=5003 q=94.0 compile_ok figures=5 tables=3
