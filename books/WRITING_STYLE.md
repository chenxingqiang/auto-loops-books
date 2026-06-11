# AI Compiler Performance Engineering — Unified Writing Voice & Style

**Canonical spec (Chinese):** sections I–VI below.
**Manuscript language:** English (`books/chapters/*.tex`).
**Gold-standard reference:** Chapter 1 (`ch01_llm_decode_bottlenecks.tex`) — all chapters must match its engineering narrative density, problem-first structure, and hardware–software coupling.

**Loop enforcement:** Every `agent_tasks` block from `uv run book-loop step` assumes compliance with this file. Read before editing any chapter.

---

## 一、核心定位：本书专属文风（区别于普通技术书）

**一句话总基调：工程师叙事型硬核干货文风**

拒绝高校教科书式的定义堆砌、刻板说教、平铺罗列；拒绝浅层工具教程、流水账式步骤讲解。全书以「踩坑复盘 + 问题溯源 + 硬件本质拆解 + 工程最优解」为核心叙事逻辑，高级、干练、落地、有行业深度，兼顾学术严谨性与工程实战感。

**适配读者：** 中高级 AI 软件/硬件工程师。整体口吻不科普入门、不废话解释基础、直击工业级痛点与底层本质。

### English manuscript equivalent

**One-line tone:** Engineer-narrative, hard-edged, production-grade technical prose.

Reject textbook definition dumps, lecture-style framing, and shallow tool walkthroughs. Every section follows: **pitfall recap → root-cause trace → hardware truth → compiler/kernel fix → measured trade-offs**.

**Audience:** Mid/senior AI systems engineers. Assume fluency in CUDA, deep learning serving, and compiler basics. No primers.

---

## 二、四大核心写作口吻准则（全书强制执行）

### 1. 问题前置，先破后立，拒绝平铺直叙

每小节开篇优先抛出行业普遍误区、工程诡异现象、线上真实瓶颈、传统方案短板，再逐层拆解原理、归因问题、给出优化方案。

- **禁止：** 直接定义概念、罗列知识点、从起源和基础原理慢慢铺垫。
- **标准：** 先讲「为什么传统方式不行、为什么线上跑分翻车、不同硬件为什么性能分化」，再讲「底层硬件约束是什么、编译怎么改、内核怎么适配、收益在哪里」。

**EN:** Open each `\section` with a production contradiction, misconception, or measured failure mode—not a definition. Then trace to hardware constraints, compiler strategy, kernel shape, and quantified upside.

### 2. 软硬件双视角绑定，贯穿全书

所有软件优化、编译策略、内核设计，绝不孤立讲软件，必须同步绑定硬件架构本质；所有硬件特性讲解，绝不单纯讲硬件参数，必须落地软件编译与内核实现。

**固定叙事链路：** 硬件架构约束 → 产生工程瓶颈 → 推导编译策略 → 落地内核实现 → 量化多硬件收益与取舍。

杜绝单一软件视角、单一 GPU 视角、只讲操作不讲本质的碎片化内容。

**EN:** Mandatory chain in every technical argument:

`hardware constraint → engineering bottleneck → compile pass / IR strategy → kernel realization → multi-hardware delta`

Never GPU-only generalizations. Tie every optimization claim to memory hierarchy, scheduling, or on-chip residency.

### 3. 去教科书化，重工程体感与踩坑复盘

弱化系统化、教条式的理论堆砌，增加工程师专属「体感叙事」：行业通病、落地坑点、理论与线上不符的矛盾、硬件差异化玄学、优化无效的核心归因。

语言风格：干练、锋利、精准，少长句、少冗余修饰，每一段都解决一个具体工程疑问，无废话、无套话。

全书贯穿反常识纠正、误区拆解、现象归因、最优取舍。

**EN:** Short, sharp sentences. Each paragraph answers one engineering question. Include "why the obvious fix failed" and "what production metrics actually showed."

### 4. 多硬件差异化贯穿，拒绝通用废话

所有技术点默认携带 **GPU / CPU / NPU / XDNA / AIE** 差异化结论，不写放之四海而皆准的空泛理论。

不追求统一万能解法；突出同一思路在不同硬件上的适配差异、收益差异、约束差异、取舍差异。

**EN:** Default to comparative conclusions across at least two hardware classes. State when a CUDA win is a CPU/NPU loss and why.

---

## 三、绝对禁止的写作风格（全书红线）

| 禁止 | English examples to avoid |
|------|---------------------------|
| 教科书式说教 | "This section will introduce…", "In this chapter we focus on…", "As is well known…", "Simply put…" |
| 入门级科普 | Explaining what a tensor is, what backprop is, what CUDA is |
| 流水账罗列 | Feature lists, API parameter catalogs, step-by-step tool clicks without causality |
| 空洞理论 | Claims without citations, measurements, or hardware-bound reasoning |
| 单一硬件视角 | GPU-only advice when the chapter topic applies to CPU/NPU/dataflow accelerators |

---

## 四、全书统一标准句式与叙事模板（可直接复用）

### 1. 现象引入（每小节开篇）

- 在工业落地中，绝大多数工程师都会遇到一个典型矛盾：xxx
- 行业长期存在一个认知误区：xxx，这也是多数团队优化无效的核心原因
- 理论上 xxx 可行，但线上真实场景中，往往会出现 xxx 性能退化问题
- 传统方案看似逻辑完整，但在多硬件适配场景下，会暴露致命短板：xxx

**EN templates:**

- *In production, most teams hit the same contradiction: …*
- *A durable industry misconception is …—which is why many optimizations never move p99 latency.*
- *The technique is sound in theory; in live serving it often regresses because …*
- *The conventional stack looks coherent until multi-hardware deployment exposes …*

### 2. 归因分析（原理讲解）

- 造成该现象的根本原因，并非算力不足，而是 xxx 硬件架构约束导致的 xxx 开销
- 从硬件底层来看，xxx 架构特性决定了该优化思路的收益边界与适用场景
- 软件层面的所有性能瓶颈，最终都可以溯源到硬件存储、调度、并行的底层约束

**EN templates:**

- *The root cause is not raw FLOPs but … imposed by the memory/scheduling model.*
- *At the silicon level, … caps the upside of this compile strategy.*
- *Every software-side stall traces to residency, bandwidth, or launch/orchestration limits.*

### 3. 差异化对比（多硬件）

- 对于 GPU 而言，xxx 是核心优化收益点；但在 CPU/NPU 架构下，该策略反而会带来性能损耗
- CUDA 架构允许 xxx 灵活调度，而 XDNA/AIE 专用硬件则强制要求 xxx 静态约束
- 三类硬件的优化优先级完全不同：GPU 侧重访存合并，CPU 侧重 Cache 局部性，NPU 侧重静态固化

**EN templates:**

- *On GPUs, … pays off; on CPUs/NPUs the same rewrite often hurts because …*
- *CUDA permits dynamic …; XDNA/AIE paths require static …*
- *Optimization rank differs by class: GPU → coalescing & tensor cores; CPU → cache locality & SIMD; NPU → static fusion & DMA schedules.*

### 4. 结论落地（收尾）

- 这也印证了全书核心结论：xxx
- 因此工业级落地不能套用通用模板，必须基于硬件架构做差异化适配
- 该原理最终沉淀为 YiRage 编译器的 xxx 专属优化 Pass 与自动适配逻辑

**EN templates:**

- *This is the book's recurring thesis: …*
- *Industrial deployment cannot copy a single template—hardware class dictates the pass order.*
- *YiRage materializes this as … (named pass / fusion rule / layout decision).*

---

## 五、文风质感关键词（全书统一调性）

精准、锋利、务实、溯源、辩证、落地

无空话、无科普、无说教、无冗余。每一段对应：**一个工程问题 · 一个误区纠正 · 一个硬件本质 · 一套编译/内核方案**。

**EN keywords:** precise, sharp, pragmatic, traceable, dialectical, shippable.

---

## 六、对标参考（已定型优质文风）

全书所有章节严格对标 **第 1 章定稿**（`ch01_llm_decode_bottlenecks.tex`）：

- 工程叙事感强、问题导向清晰
- 软硬件联动、多硬件对比
- 有踩坑、有复盘、有结论
- 无教科书刻板感

When expanding ch02+, read ch01's section openings and paragraph rhythm before drafting.

---

## 七、O'Reilly 对齐：*AI Systems Performance Engineering*（Fregly）风格映射

**Reference sample:** `chapter1-AI Systems Performance Engineering - Chris Fregly.pdf` (repo root).

本书与 Fregly 同属 **中高阶 AI 系统性能工程专著**，但聚焦 **编译器 + 多硬件 decode/MegaKernel**（YiRage），而非 PyTorch 全栈 + NVIDIA 集群运维。对齐的是 **叙事范式与章节结构**，不是复制其 CUDA/PyTorch 生态边界。

### 1. 双线主轴对照（全书贯穿）

| Fregly 主线 | 本书等价 |
|-------------|----------|
| **Mechanical Sympathy**（软硬件协同） | **Hardware–software codesign**：硬件约束 → 编译 Pass → 内核/静态图；每节必须绑定 residency |
| **Goodput**（有效吞吐） | **Useful decode metrics**：`kernels/token`、`bytes/token`、batch-1 `ms/token`、`R_floor`、HDBI——拒绝裸 FLOPs / 利用率 |
| DeepSeek 等工业标杆 | TaxBreak、Memory-Floor、FlashAttention/Flash-Decoding、DeepSeek-V3 部署比、YiRage 回归矩阵 |
| Profile-driven tuning | TaxBreak 分解 + Nsight/roofline 思维 + IR diff 回归门 |

**EN:** Open chapters by naming the **constraint** (hardware export rules, SRAM ceiling, launch floor), not by defining softmax/attention from first principles.

### 2. 单章固定范式（Fregly 对齐，全书强制）

每章按以下顺序组织（与 Fregly 的 *Key Takeaways → Conclusion* 一致）：

1. **Opening** — 行业痛点 / 约束 / 量化锚点（1–3 段）
2. **`\section{…}` 正文** — 每节 = 一个具体工程问题；小节标题可检索
3. **Figure / Table / Example** — 数据优先
4. **`\section{Key Takeaways}`** — 5–8 条 bullet，可碎片化查阅
5. **`\section{Conclusion}`** — 串联本章、引出下一章

**LaTeX 模板：**

```latex
\section{Key Takeaways}
\label{sec:chXX_key_takeaways}
\begin{itemize}
\item \textbf{Measure …} — … \citep{…}
\end{itemize}

\section{Conclusion}
\label{sec:chXX_conclusion}
… bridge to Chapter~YY …
```

**迁移：** 深度 Agent 润色章用 `Key Takeaways` + `Conclusion`；旧 `Chapter Summary` 在改版时替换。

### 3. 叙事模板（问题驱动 + 量化）

`工程痛点 → 约束 → 底层机制 → 分层方案（GPU/CPU/NPU）→ 基准/数字 → 取舍`

### 4. 与 Fregly 的刻意差异

| 维度 | Fregly | 本书 |
|------|--------|------|
| 硬件 | NVIDIA 为主 | GPU + CPU + XDNA/AIE |
| 软件 | PyTorch / CUDA / K8s | YiRage IR、MegaKernel |
| 附录 | 175+ 优化清单 | 回归基准 + verified_facts JSONL |

### 5. 深度 Agent 润色（选项 2）Fregly 验收

1. 章首 200 词内：**可核验数字** 或 **named benchmark**
2. 每 `\section`：**multi-hardware delta**
3. 结尾：**Key Takeaways + Conclusion**（非 padding）
4. 禁止 `Review gate` 机械复读
5. `verified_facts.jsonl` 为技术主张，非 meta 描述

---

## Agent checklist (per editing session)

Before committing chapter prose:

1. Does each `\section` open with a production problem or misconception (not a definition)?
2. Does every optimization claim name a hardware constraint and a measurable effect?
3. Are GPU, CPU, and NPU/edge angles addressed where the topic applies?
4. Are forbidden lecture phrases absent (see Section III)?
5. Are citations tied to real benchmarks or architecture docs—not hand-wavy theory?
6. Does the section close with an industrial takeaway or YiRage/compiler mapping where relevant?
7. Are all numbers and examples web-verified with URLs logged in `books/research/<id>/verified_facts.jsonl` (see `FACT_VERIFICATION.md`)?


---

## 八、事实核验门禁（与 FACT_VERIFICATION.md 同步）

凡**事实描述、数据举例、厂商参数、性能数字**，必须先 **Web 检索 ≥2 轮、交叉验证**，写入 `books/research/<chapter_id>/verified_facts.jsonl` 并附 **可靠链接**，方可进入 `books/chapters/*.tex`。

- 禁止无 URL 的数字、禁止单一路径未核对就写入
- 未通过核验：仅用 `\vispending{}` / TBD，不得冒充实测
- 正文数字旁必须有 `\citep{}`；`book.bib` 中 URL 与核验日志一致

**EN:** No numeric fact ships without web verification, JSONL log, and matching bibliography URL.
