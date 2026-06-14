# AI Compiler Performance Engineering：跨硬件数据流驱动内核与编译优化实战

> **仓库文件：** 全书中文目录与写作意图 → 本文件 [`book_content.md`](book_content.md)；英文正文 → `books/build/chapters/*.tex`；Fregly 风格样章 → [`reference-chapter-1.pdf`](reference-chapter-1.pdf)。

## 一、书籍整体定位与受众适配

### 1. 目标受众

本书精准面向**软件、硬件开发工程师**，针对性匹配两类人群的核心需求，打通软硬件技术壁垒：

- **AI软件工程师**：从事CUDA内核开发、LLM推理部署、AI编译器优化、算子开发的工程人员，解决传统算子拆分优化的性能瓶颈，掌握极致内核融合设计方法论

- **硬件开发工程师**：从事NPU、AMD XDNA/AIE、数据流加速器架构设计、硬件指令集、片上存储与DMA设计人员，理解硬件架构对应的上层软件编程范式，实现软硬件协同优化

规避纯理论堆砌、入门级基础内容，聚焦**工业级极致优化落地**，所有内容均配套底层原理、硬件约束、实战代码、性能对比，适配中高级工程师进阶提升需求。

### 2. 书籍核心定位

市面上绝大多数AI优化书籍均为「算子驱动、软件视角」，仅讲解CUDA单硬件调优、算子融合基础，忽略**硬件架构本质**与**数据流统一设计哲学**。本书为填补行业空白的跨硬件实战专著：

- 打破CUDA通用GPU与XDNA/AIE专用数据流加速器的技术壁垒，提炼统一的AI内核设计方法论

- 颠覆传统「先写算子、再做优化」的思维，建立**数据驻留优先、数据流全局规划**的极致优化思维

- 从硬件原理、编程模型、内核实战、编译器自动化、跨硬件协同落地五个维度，完整拆解LLM推理Decode阶段性能天花板优化方案

### 3. 核心价值

让软件工程师懂硬件架构约束，写出贴合硬件极致性能的内核；让硬件工程师懂软件落地逻辑，指导硬件架构迭代与指令设计，实现**软硬件协同极致加速**。依托完整AI编译栈与跨硬件适配体系，补齐「手工极致优化→工业化自动编译→多硬件量产部署」的全链路能力。

## 二、书籍整体写作规划

### 1. 写作核心原则

> **全书文风规范（强制执行）：** 见 [`books/WRITING_STYLE.md`](books/WRITING_STYLE.md) §一–§七 — 工程师叙事 + Fregly 章骨架（[`reference-chapter-1.pdf`](reference-chapter-1.pdf)）；对标 `ch01` 节奏。loops 每轮 `agent_tasks` 均引用该文件。
>
> **事实核验门禁（强制执行）：** 凡事实描述、数据举例须 **Web 检索反复验证** 后方可入稿，并记录可靠链接 → [`books/WRITING_STYLE.md`](books/WRITING_STYLE.md) §八（`books/research/<章>/verified_facts.jsonl`）。

- **软硬件双视角并行**：每一个软件优化技巧，必对应硬件底层原理；每一个硬件架构特性，必配套软件落地实现，贯穿「硬件约束→编译策略→性能结果」核心链路

- **问题导向，拒绝堆砌**：从LLM推理真实性能痛点、跨硬件编译适配痛点出发，逐层拆解问题、解法、原理、落地、迭代优化

- **理论+源码+实测+跨硬件对比**：核心章节配套950行级融合内核源码、多硬件benchmark数据、编译踩坑指南、差异化适配方案

- **通用化可迁移**：从Pythia-2.8B/Qwen2.5案例提炼通用方法论，可迁移至所有LLM Decoder内核、各类数据流AI加速器、全品类主流硬件

### 2. 全书结构规划（对标 Fregly 全栈目录）

**组织金标准：** [`chapter1-AI Systems Performance Engineering - Chris Fregly.pdf`](chapter1-AI%20Systems%20Performance%20Engineering%20-%20Chris%20Fregly.pdf) 目录 + [`reference-chapter-1.pdf`](reference-chapter-1.pdf) 章骨架。原则：**问题/产出优先**（非工具名堆砌）、**全栈递进**（goodput → 硬件 → CUDA 机制 → MegaKernel → Graph → 编译栈 → 推理 fleet）、**小节标题可检索**（TMA / Continuous Batching / FlashMLA 等具名机制）。

全书 **8 个 Part、30 章**，LaTeX 章 id（ch01–ch30）保持不变；**目录叙事**按 Fregly 价值链重排读者预期：

| Part | Fregly 对标层 | 本书 Part 主题 | 章 |
|------|----------------|----------------|-----|
| I | Ch1 Introduction & Goodput | 瓶颈、goodput、数据流思维 | ch01–02 |
| II | Ch2 Hardware Overview | 全栈硬件约束总纲 | ch03 |
| III | Ch6–7 CUDA memory & access | Hopper CUDA + XDNA 数据流对标 | ch04–05 |
| IV | Ch9–10 Kernel fusion & MegaKernels | 片上驻留、流水线、同步 | ch06–09 |
| V | Ch10–12 Persistent kernels & CUDA Graphs | MegaKernel 实现与执行模式 | ch10–12 |
| VI | Ch13–14 PyTorch & compiler backends | 编译理论 + MLIR→生产后端 lowering 弧 | ch13–21 |
| VII | Ch15–19 Inference at scale & adaptive | Profiling、异构部署、MoE、自动调优 | ch22–27 |
| VIII | Ch16–18 Frameworks & KV / disagg | 推理框架、YiRage runtime、三方 co-design | ch28–30 |

**与旧版差异（为何旧目录「无价值感」）：** 旧 Part 名（「思维革新」「MegaKernel Core Techniques」）不告诉读者**学完能做什么**；Part VI 把 MLIR/XLA/TVM… 平铺成「编译器图鉴」，缺少 Fregly 式 **一条 lowering 故事线**。新版目录每章小节按 **机制/指标/案例** 命名，编译器章归入「Backend Lowering Arc」而非独立产品宣传。

## 三、现有框架核心短板与优化思路

### 1. 原有框架核心问题

- **软硬件解耦严重**：原有内容侧重单一GPU优化，未区分NVIDIA GPU、AMD GPU、CPU、NPU等主流硬件架构差异，缺失编译策略与硬件特性的强绑定关系

- **缺少跨硬件编译对比**：同类编译优化（Tiling、算子融合、内存复用）在不同硬件的实现、收益、约束差异未体现，不符合工业落地场景

- **缺失硬件感知编译核心逻辑**：泛谈编译原理，未承接「硬件特性→编译Pass设计→调度分块策略→最终性能」的核心技术链路

- **落地场景缺失**：未覆盖云端GPU、通用CPU、边缘NPU、异构集群四大工业核心部署场景，工程实用性不足

### 2. 整体优化原则（最小改动、强衔接、保风格）

- 前置硬件总纲，搭建全书统一硬件适配标尺，所有后续编译内容以此为基础

- 统一所有编译器章节模板，强制植入跨硬件适配、差异化优化小节

- 改造原有核心章节，全链路绑定硬件约束，补齐硬件感知编译逻辑

- 新增异构编译专项章节，补齐多硬件集群部署工程短板

- 区分云端、通用端侧、边缘NPU三大场景，实现场景化差异化教学

**全书核心主线**：硬件架构约束 → 编译IR设计 → 优化Pass策略 → 调度/分块/内存规划 → 硬件专属指令生成 → 最终性能差异化结果

## 四、分步改造与增补落地方案

### 1. 新增核心前置硬件总纲章节（全书基础底座）

在原第2章后新增**Chapter3 AI Hardware Architecture & Compiler Constraints**，作为全书硬件适配唯一标准，原3章及后续章节整体顺移后位，解决软硬件解耦核心问题。

### 2. 全编译器章节标准化改造（统一全书口径）

对MLIR/XLA/TVM/Triton/IREE/Glow/Mirage所有编译器章节，统一新增5大固定小节，保证全书体系一致、落地性统一：

- Hardware Target Support Matrix（硬件支持矩阵）

- Architecture-Specific Optimization Passes（硬件专属编译优化）

- Cross-Platform Code Generation & Adaptation（跨硬件代码生成）

- Performance Tuning for Different Hardware（分硬件专项调优+踩坑总结）

- Case Study：Same Model, Different Hardware Compilation Result（同模型跨硬件对比实战）

### 3. 存量章节针对性升级改造

- **核心编译理论章节**：将分块、数据布局、算子融合、并行调度理论，拆分GPU/CPU/NPU差异化实现逻辑，绑定对应硬件约束

- **编译器横向对比章节**：升级为「跨编译器+跨硬件联合对比」，新增多硬件适配能力、编译开销、搜索空间差异对比

- **端到端调优章节**：新增硬件感知Profiling体系，基于显存带宽、Cache Miss、Warp Stall、NUMA延迟等硬件指标定位编译瓶颈

### 4. 新增高阶专项工程章节

新增**异构编译与多硬件部署专项章节**，补齐工业级异构集群、跨平台统一编译、动态硬件适配核心能力。

## 四点五、Fregly 目录对标原则（2026-06 目录迭代）

| Fregly 章节主题 | 本书承接章 | 本书增量（相对 Fregly） |
|-----------------|------------|-------------------------|
| Introduction, Goodput, Mechanical Sympathy | ch01–02 | TaxBreak / Memory-Floor 计数器；数据流 vs 算子驱动 |
| AI System Hardware Overview | ch03–05 | XDNA/AIE 静态数据流 + triplet 硬件标尺 |
| GPU Architecture & Memory Hierarchy | ch04, ch06–08 | Hopper TMA/Cluster；编译 legality 不变量 |
| Persistent Kernels & Megakernels | ch10–12 | 950 行 Decoder MegaKernel；三种执行模式 |
| CUDA Graphs & Orchestration | ch12, ch28 | Graph bucket + 框架 continuous batching |
| Profiling & Scaling PyTorch | ch13, ch22 | 编译器瓶颈 vs framework queue 分离 |
| torch.compile, Triton, XLA | ch14–20 | **多后端 lowering 弧**（非单章工具手册） |
| Multinode Inference & Decoding | ch23, ch28–30 | MoE 编译 + vLLM/YiRage 协同 |
| Disaggregated Prefill/Decode & KV | ch24, ch28 | DeepEP / FlashMLA / paging ABI |
| Dynamic & AI-Assisted Optimization | ch25–27 | RL autotune + YiRage search |
| 175+ Item Checklist (Appendix) | 附录 A–H | 跨硬件 + 编译 + runtime 双维 checklist |

**目录写作硬规则（loops 扩章时强制）：**

1. 章标题 = **读者能力产出**（例：Profiling Hopper Decode Changes），禁止仅写产品名（例：MLIR Chapter）。
2. 小节标题 = **可检索机制**（TMA、PagedAttention、FlashMLA、Continuous Batching），禁止「1.1 概述」式空壳。
3. 每章必须显式挂钩 Chapter~1 三角：**launches/token · bytes/token · ms/token（goodput）**。
4. Part VI 编译器章统一叙事：**同一 IR → 多后端 legality → 同模型 triplet benchmark**（对齐 Fregly Ch14 把 PyTorch Compiler/Triton/XLA 串成一条线）。

## 五、全书目录（Fregly 全栈对标版 · ch01–ch30）

### Part I — Introduction, Goodput & Dataflow Mindset（ch01–02）

> **Fregly 对标：** Ch1 *Introduction and AI System Overview* — mechanical sympathy、goodput、benchmarking discipline。

#### 第1章 LLM Inference Performance Bottlenecks: From Symptoms to Root Causes（ch01）

**读者产出：** 用 TaxBreak / Memory-Floor 工作表定位 decode 根因，拒绝「先调 Tensor Core」。

- The AI Compiler Performance Engineer（编译器×硬件×推理三角角色）
- Benchmarking and Profiling Decode（launches/token、bytes/token、Nsight 分工）
- Measuring Goodput Useful Throughput（ms/token 必须与 counter 同屏）
- Prefill Versus Decode: Different Bottleneck Profiles
- Kernel Launch Storms and Framework Orchestration Tax
- Memory Bandwidth Versus Arithmetic Intensity at Batch-1
- Multi-Hardware Pain Points: GPU / CPU / NPU Priority Matrix
- DeepSeek-Scale Inference Under Export Hardware Constraints（案例）
- Mechanical Sympathy: Hardware–Software Codesign for Decode
- YiRage Triplet Preview: Same IR, Three Backends
- Key Takeaways · Conclusion · Worksheet Gate

#### 第2章 Two Kernel Design Mindsets: Operator-Driven vs Dataflow-Driven（ch02）

**读者产出：** 选择 data-residency-first 设计，并解释对 triplet 编译 legality 的影响。

- Operator Lists First: Why Frameworks Split Decode into Dozens of Kernels
- Data Residency First: On-Chip Lifetime Before Compute Ordering
- Dataflow Philosophy: Static Roles, Streamed DMA, Minimal Sync
- Cross-Hardware Paradigm: CUDA Discipline vs XDNA Static Tiles vs CPU Cache Locality
- Iron Rules: Register → Shared → Global（分硬件落地表）
- MegaKernel Preview: One Fused Decode Cell Versus Thirteen Launches
- Automation Path: Hand-Tuned Dataflow → YiRage Compiler Passes
- Key Takeaways · Conclusion

---

### Part II — Full-Stack Hardware & Compiler Constraints（ch03）

> **Fregly 对标：** Ch2 *AI System Hardware Overview* — 具体 SKU、互联、roofline；本书增 **XDNA + 编译约束矩阵**。

#### 第3章 AI Hardware Architecture and Compiler Constraints（ch03）

**读者产出：** 用统一约束矩阵解释「同一 Pass 在 GPU/CPU/NPU 上为何 legality 不同」。

- Mainstream AI Hardware Landscape（NVIDIA / AMD / x86 / ARM / Edge NPU）
- Constraint Matrix: Bandwidth, Hierarchy, Parallel Grain, ISA
- GPU Compiler Constraints: Warp, Shared Memory, Tensor Core Trade-offs
- CPU Compiler Constraints: Cache, SIMD, NUMA, Pipeline
- Edge NPU Constraints: Static Schedules, Shape Limits, Memory Walls
- Hardware-Aware Tiling, Layout, and Parallel Rules
- Cross-Hardware Benchmark Methodology（统一模型·统一指标）
- YiRage ChipArchitecture Modeling
- Key Takeaways · Conclusion

---

### Part III — Hopper CUDA & XDNA Dataflow Architecture（ch04–05）

> **Fregly 对标：** Ch6–7 GPU architecture & memory access + Ch9 TMA/tensor cores；本书增 **XDNA 静态数据流对标**。

#### 第4章 CUDA Hopper/Blackwell: Hardware Properties and Optimization Bounds（ch04）

**读者产出：** 列出 Hopper decode 优化边界表；Profiling 顺序：bytes → launches → TC。

- CUDA Memory Hierarchy for Decode MegaKernels（Table: tier assignments）
- Tensor Memory Accelerator: Async Bulk Copy and Legality at Batch-1
- Thread Block Clusters and Distributed Shared Memory
- Synchronization: Warp Shuffle → Block → Cluster → Grid（选型规则）
- Tensor Core Bounds at Batch-1 Decode（何时 TC 是干扰项）
- PTX and Online Softmax Micro-ops（exp2, FTZ, ABI stability）
- YiRage CUDA Backend Legality Invariants
- Profiling Hopper Decode Changes（Nsight Systems + Compute）
- Hopper Decode Engineering Patterns and Worked Layer Example
- Hopper Decode Benchmarking Methodology（counter worksheet + CI gate）
- Compiler Author Checklist and Handoff to XDNA（Ch5）
- Key Takeaways · Conclusion

#### 第5章 AMD XDNA/AIE Dataflow Architecture（ch05）

**读者产出：** 完成 CUDA↔XDNA 原语映射表；解释 static legality 如何约束 IR。

- XDNA/AIE Tiles, Local Memory, and DMA Pipelines
- Hardware-Forced Dataflow Rules（no dynamic scheduler）
- CUDA ↔ XDNA Primitive Mapping（TMA ↔ buffer descriptors）
- Online Softmax Carriers on XDNA Versus CUDA Registers
- Architecture Trade-offs: Freedom Versus Static Enforcement
- Cross-Hardware Conclusion: Dataflow as Optimal Inference Form
- Ryzen AI Decode Benchmarking（DDR bytes/token, DMA edges）
- YiRage XDNA Backend Passes and Codegen
- Key Takeaways · Conclusion

---

### Part IV — On-Chip Residency, Pipelining & Synchronization（ch06–09）

> **Fregly 对标：** Ch7–8 memory access & occupancy + Ch9 fusion/arithmetic intensity + Ch10 intra-kernel pipelining。

#### 第6章 Data Residency and On-Chip Memory Design（ch06）

- Lifetime Planning Across GPU / CPU / NPU Tiers
- GPU Shared-Memory Budgeting for Fused Decode Regions
- CPU Cache-Aware Layout and NUMA Pinning
- NPU SRAM Slot Assignment and Time Multiplexing
- YiRage Bufferization and Memory Reuse Passes

#### 第7章 Static Role Assignment and Schedule-Free Kernels（ch07）

- Static Warp/Tile Roles Versus Runtime Schedulers
- Thread Mapping Without Dispatch Queues
- Multi-Hardware Static Partitioning Rules
- YiRage Dimension Tiling for Heterogeneous Cores

#### 第8章 TMA Double-Buffer Pipelines and Async Copy（ch08）

- Double-Buffering TMA with MMA Overlap（Hopper）
- CPU DMA and NPU Pipeline Equivalents
- Compiler-Generated Pipeline Stages and Hazard Checks
- YiRage Auto-Pipeline Insertion

#### 第9章 Four-Level Synchronization and Communication（ch09）

- Picking the Narrowest Sync Scope for Each Seam
- GPU Barriers Versus Warp Shuffles in Softmax Loops
- Cross-Hardware Sync Cost Models
- YiRage Sync Optimization and Deadlock Detection

---

### Part V — MegaKernel Implementation & Execution Modes（ch10–12）

> **Fregly 对标：** Ch10 Persistent Kernels & Megakernels + Ch11 Streams + Ch12 CUDA Graphs。

#### 第10章 Attention Online Softmax Optimization（ch10）

- Online Softmax Numerics and Carrier Layout
- FlashAttention / Flash-Decoding Control-Flow Spine
- Paged KV and Softmax Carrier Residency
- Cross-Hardware Softmax Lowering

#### 第11章 Complete Decoder MegaKernel Implementation（ch11）

- End-to-End Fused Decode Cell Structure
- QKV → Attention → Softmax → MLP Seam Planning
- PagedAttention Gather Inside MegaKernel
- Source Walkthrough and Profiling Gates

#### 第12章 Three Kernel Execution Modes（ch12）

- Eager Launches Versus CUDA Graph Capture Versus Persistent MegaKernel
- Graph Buckets, Memory Pools, and Context-Length Growth
- When Frameworks Must Stay Eager（sampling hull）
- Mode Selection Worksheet for Fleet Goodput

---

### Part VI — Compiler Theory & Multi-Backend Lowering Arc（ch13–21）

> **Fregly 对标：** Ch13–14 PyTorch profiling + torch.compile/Triton/XLA **一条 lowering 线**；本书扩展为 MLIR 基础设施 + 多生产后端 + **triplet 基准**（非九本独立产品手册）。

**Arc 叙事（目录强制顺序）：** 理论柱（ch13）→ MLIR 基础设施（ch14）→ 生产编译器后端（ch15–20，各章含 HW matrix / passes / codegen / tuning / case study）→ 统一 benchmark（ch21）。

#### 第13章 Core Compiler Theory for AI Workloads（ch13）

- Five Pillars: Tiling, Fusion, Layout, Parallelism, Memory Planning
- Hardware-Bound Split for GPU / CPU / NPU
- Decode-Specific Fusion Granularity Rules
- Roofline-Guided Pass Ordering

#### 第14章 MLIR: Modern Compiler Infrastructure（ch14）

- Dialect Stack and Bufferization for Decode IR
- Hardware Target Matrix and Lowering Pipeline
- MLIR Decode Benchmarking Methodology
- YiRage MLIR Integration Points

#### 第15章 XLA: Production-Grade Graph Compiler（ch15）

- XLA GPU/CPU/TPU Split and Fusion Limits
- Same-Model Cross-Hardware Case Study
- Versus YiRage LLM-Specialized Legality

#### 第16章 TVM & AutoTVM / Ansor（ch16）

- Schedule Templates Across Hardware
- Search-Space Differences by SKU
- Versus YiRage RL Hardware-Aware Search

#### 第17章 OpenAI Triton: Pythonic GPU Kernels（ch17）

- Triton on NVIDIA Versus AMD HIP
- Autotune and Register Pressure at Batch-1
- YiRage Triton Backend Hooks

#### 第18章 IREE: MLIR-Native Runtime Stack（ch18）

- Unified Deployment IR and Runtimes
- GPU/CPU/Edge Codegen Paths
- Versus YiRage Five-Layer Stack

#### 第19章 Glow: Lightweight Edge Compiler（ch19）

- CPU/Edge NPU Constraints and Static Graphs
- Low-Power Codegen Patterns

#### 第20章 Mirage & Emerging AI Compilers（ch20）

- Emerging Tooling Limits on LLM Decode
- YiRage as Multi-Hardware LLM Compiler Benchmark

#### 第21章 Unified Compiler Analysis & Cross-Hardware Benchmark（ch21）

- Cross-Compiler × Cross-Hardware Rating Matrix
- Compile Time Versus Runtime Goodput
- YiRage Benchmark Suite and Triplet Regression Policy

---

### Part VII — Fleet Tuning, Heterogeneous Deploy & Auto-Optimization（ch22–27）

> **Fregly 对标：** Ch15–19 multinode inference, profiling at scale, disagg P/D, KV/FlashMLA, dynamic adaptive + RL。

#### 第22章 Compiler-Driven End-to-End Performance Tuning Workflow（ch22）

- Hardware-Aware Profiling（framework queue vs in-step counters）
- Nsight / PyTorch Profiler / Roofline for Compile Bottlenecks
- Parameter Sweeps Tied to TaxBreak Cells

#### 第23章 LLM & MoE Specialized Compilation（ch23）

- MoE Routing, Expert Parallelism, and Compile Schedules
- KV Hardware Layout and Paging ABI
- Heterogeneous MoE Load Balancing

#### 第24章 Heterogeneous Compilation & Multi-Hardware Deployment（ch24）

- GPU+CPU Cluster Graph Splitting
- Unified MLIR/IR Multi-Target Deploy
- DeepSeek Infra: FlashMLA, DeepEP, DeepGEMM, eplb, 3FS（deps 锚点）
- Runtime Hardware Detect and Fallback

#### 第25章 Auto-Optimization & AI-Assisted Compiler Technology（ch25）

- RL Autotune with Hardware-Aware Rewards
- Search Budgets per Registry SKU
- YiRage superoptimize in CI

#### 第26章 Production Deployment & Engineering Best Practices（ch26）

- Multi-Hardware Build Matrices and Submodule Pinning
- Framework–Compiler–Runtime Runbooks
- Fleet Rollout and Artifact Manifests

#### 第27章 Future Trends of AI Compilers（ch27）

- Co-Design, Edge–Cloud Adaptive Compile, Autonomous Kernel Gen
- Bridge to Part VIII Serving Stack

---

### Part VIII — Inference Frameworks, Runtime & Full-Stack Co-Design（ch28–30）

> **Fregly 对标：** Ch16 Continuous Batching / KV / quantization + Ch17–18 disagg P/D & FlashMLA + runtime orchestration；本书以 **vLLM + YiRage PK** 为参考栈。

#### 第28章 LLM Inference Frameworks and Serving Runtimes（ch28）

- Framework Landscape: Eager / Partial Export / Compiler-Owned Core
- Continuous Batching and Fleet Goodput Versus BS=1 Counters
- PagedAttention: Framework Memory vs Compiler Layout IR
- Framework Bottlenecks: Scheduling, Python Tax, Unfused Chains
- Compiler Insertion Points and CUDA Graph Buckets

#### 第29章 YiRage Runtime Layer and Persistent Kernel Execution（ch29）

- Five-Layer Stack: API → Backend → Search → Threadblock → PK Runtime
- PersistentKernel Decode Mode and superoptimize Handoff
- HardwareRegistry / detect_current_chip and Fleet Labels
- deps/YiRage Native Build and Same-Backend Rule
- YiRage Runtime Decode Benchmarking Methodology

#### 第30章 Framework, Compiler, and Runtime Co-Design（ch30）

- Three-Party Responsibility Table
- Prefill/Decode Split and Sampling Eager Hull
- vLLM Paging + YiRage Fused Decode Integration Pattern
- Fleet Mode Selection: Eager / Graph / MegaKernel
- Submodule Pin, Triplet Regression, PK Warmup CI
- Conclusion: Full-Stack Goodput Checklist（对接附录 F）

---

### 目录—正文一致性说明

| 层级 | 文件 | 作用 |
|------|------|------|
| 意图 | 本文件 §五 | Fregly 式 Part/章/机制小节（中文 spec） |
| 机器 | `outline_extended.json` + `book_prepare.py` OUTLINE | 章 id、SectionSpec、min_words gate |
| 排版 | `books/main.tex` | `\input` 顺序（当前与 ch01–ch30 一致，**未物理重排**） |

**后续 loop 动作：** 扩章时优先补 **Fregly 式具名小节**（非 numbered 空壳）；Part VI 写作按 **Lowering Arc** 互引，禁止孤立「编译器宣传章」。


## 六、全书附录体系（升级补齐跨硬件工程能力）

- 附录A 核心源码：Pythia-2.8B MegaKernel完整工程代码

- 附录B 实测Benchmark数据集：多硬件、多编译器全维度性能对比

- 附录C 关键硬件指令与API手册（CUDA/XDNA/CPU/NPU）

- 附录D 跨硬件编译常见报错、性能退化问题排查手册

- 附录E YiRage环境配置、命令行与核心参数手册

- 附录F YiRage跨硬件数据流优化Checklist（编译+内核双维度）

- 附录G YiRage源码架构阅读指南与多后端适配开发教程

- 附录H 主流AI编译器跨硬件适配速查表

## 七、全书统一落地规范与细节标准

### 1. 三类硬件编译核心侧重点（全书统一口径）

- **NVIDIA GPU**：Warp效率、共享内存复用、合并访存、Tensor Core取舍、CUDA Stream调度、细粒度算子融合

- **通用CPU(x86/ARM)**：Cache局部性优化、SIMD/AVX向量化、多核负载均衡、NUMA感知、计算图粗粒度拆分

- **边缘NPU**：静态图优先、大算子合并、动态形状限制、内存分片复用、极简指令生成、低功耗编译策略

### 2. 所有编译器章节固定落地要点

- 明确编译器原生主打硬件场景与适配定位

- 剖析跨硬件移植成本、技术局限与性能取舍

- 落地同模型多硬件下的编译参数、优化开关差异化配置

- 实战硬件独有特性的编译Pass落地与收益量化分析

### 3. 全书统一实战案例体系

固定 **ResNet（通用模型）+ LLaMA/Qwen2.5（LLM模型）** 双案例，贯穿全书：基于XLA/TVM/Triton/MLIR/YIRAGE多编译器，分别部署至NVIDIA GPU/AMD GPU/x86 CPU/边缘NPU，对比编译IR、优化策略、硬件适配逻辑、最终性能差异，印证「硬件决定编译效果」的核心结论。

## 八、YiRage全书深度适配总结（升级后核心价值强化）

升级后YiRage从「LLM专用编译引擎」升级为全书**跨硬件软硬件协同编译的唯一工业级标杆**，完美承接全书「硬件架构差异化编译优化」核心主线：

- 唯一覆盖全书所有硬件品类的开源编译引擎，支撑多硬件对比实战全流程

- 将全书手工数据流优化经验、硬件适配规则全部固化为自动化编译Pass与搜索策略

- 补齐传统编译器无全局数据流规划、跨硬件适配碎片化的核心短板

- 提供从硬件探测、自动适配、内核生成、跨硬件部署、性能调优的完整工程闭环

## 九、最终全书升级价值总结

1. **体系完整性**：形成「硬件架构约束→编译理论→主流编译器跨硬件实战→手工极致内核→自动化编译→异构部署→生产落地」的完整闭环，逻辑严谨、层层递进

2. **专业稀缺性**：补齐行业空白，成为国内首本聚焦「编译器×硬件架构联动差异化优化」的AI性能工程专著，摆脱纯工具讲解的同质化问题

3. **工程实用性**：全章节配套多硬件实操、调优、踩坑、对比案例，完全贴合工业界云端、端侧、异构集群三大核心场景

4. **技术前瞻性**：依托YiRage[https://github.com/chenxingqiang/YiRage]前沿技术，覆盖RL自动调优、跨硬件统一数据流编译、异构集群自适应部署等行业前沿方向
> （注：文档部分内容可能由 AI 生成）