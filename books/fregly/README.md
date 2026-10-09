# Fregly《AI Systems Performance Engineering》逐章分析索引

> 用途：为新书《AI Compiler Performance Engineering》提供 Fregly 每章的**写作逻辑、核心价值、关键事实、对齐建议**参考。
> 来源 PDF：`~/Downloads/AI Systems Performance Engineering-Chapter/01–20_*.pdf`（提取文本为 `chNN.txt`，分析为 `chNN_analysis.md`）。
> 对齐基准：`book_content.md` §四点五（Fregly ↔ 本书 ch01–ch30 映射表）。

## 与本书的章节映射总表

| Fregly 章 | 主题 | 本书承接章 | 分析文件 |
|---|---|---|---|
| Ch1 | Introduction, Goodput, Mechanical Sympathy | ch01–02 | [ch01_analysis.md](ch01_analysis.md) |
| Ch2 | AI System Hardware Overview | ch03–05 | [ch02_analysis.md](ch02_analysis.md) |
| Ch3 | OS/Docker/K8s Tuning | ch03/ch26 底座素材 | [ch03_analysis.md](ch03_analysis.md) |
| Ch4 | Distributed Networking (NCCL/NIXL) | ch24/ch28 | [ch04_analysis.md](ch04_analysis.md) |
| Ch5 | GPU Storage I/O | ch22 素材 | [ch05_analysis.md](ch05_analysis.md) |
| Ch6 | GPU Architecture & Occupancy | ch04, ch06–08 | [ch06_analysis.md](ch06_analysis.md) |
| Ch7 | GPU Memory Access Patterns | ch04, ch06–08 | [ch07_analysis.md](ch07_analysis.md) |
| Ch8 | Occupancy, Warp Efficiency, ILP | ch06–09 | [ch08_analysis.md](ch08_analysis.md) |
| Ch9 | Kernel Efficiency & Arithmetic Intensity | ch06–09 | [ch09_analysis.md](ch09_analysis.md) |
| Ch10 | Intra-Kernel Pipelining, Clusters | ch08, ch10–12 | [ch10_analysis.md](ch10_analysis.md) |
| Ch11 | Streams, Sync, PDL | ch08–09, ch12 | [ch11_analysis.md](ch11_analysis.md) |
| Ch12 | CUDA Graphs, Device Orchestration | ch12, ch28 | [ch12_analysis.md](ch12_analysis.md) |
| Ch13 | Profiling & Scaling PyTorch | ch13, ch22 | [ch13_analysis.md](ch13_analysis.md) |
| Ch14 | torch.compile / Triton / XLA | ch14–20 | [ch14_analysis.md](ch14_analysis.md) |
| Ch15 | Multinode Inference & Decoding | ch23, ch28–30 | [ch15_analysis.md](ch15_analysis.md) |
| Ch16 | Inference at Scale | ch22, ch28 | [ch16_analysis.md](ch16_analysis.md) |
| Ch17 | Disaggregated P/D Scaling | ch24, ch28 | [ch17_analysis.md](ch17_analysis.md) |
| Ch18 | P/D & KV Cache Tuning | ch24, ch28 | [ch18_analysis.md](ch18_analysis.md) |
| Ch19 | Dynamic Adaptive Inference | ch25–27 | [ch19_analysis.md](ch19_analysis.md) |
| Ch20 | AI-Assisted Optimization & Future | ch25, ch27 | [ch20_analysis.md](ch20_analysis.md) |

## 与 S2C2IR 的对齐要点

> **深度对齐文档：[S2C2IR-alignment.md](S2C2IR-alignment.md)**（基于本地仓库 `/Users/xingqiangchen/S2C2IR`，106 份设计文档，内容以下文摘要为准）。

S2C2IR（本地：`/Users/xingqiangchen/S2C2IR`）：MLIR 方言族 = Storage + Compute + Communication + Execution 语义 IR + 硬件能力模型（硬件中立 Capability Schema v1，4090 + Ascend 910B 双实测）+ **证据约束调度优化器**（五级门禁：sufficient → authorized → rewrite-license → rewrite-plan → applied；无测量/许可证据不做破坏性重写）。与 Fregly 分析的结合点：

1. Fregly「profiling 先行、counter 驱动决策」的叙事 ⇔ S2C2IR evidence-bounded 重写许可（Rewrite License 是产品）
2. Fregly 硬件层级（NVLink/HBM/Shared Memory）⇔ S2C2IR storage dialect + capability model（`v3-dataset/` 实测数据可直接作书内跨硬件素材）
3. Fregly Streams/Graphs/PDL 执行编排 ⇔ S2C2IR sched dialect（HB = happens-before 语义，`HB_M = HB_source` 是 realization 合法性标准）
4. Fregly 手工调优循环 ⇔ S2C2IR 编译执行脊柱（IR Apply Contract，#136–#141 冻结链）——正确性由门禁构造保证
