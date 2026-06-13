# AI Compiler Performance Engineering — Unified Writing Voice & Style

**Canonical spec (Chinese):** sections I–VI below.
**Manuscript language:** English (`books/build/chapters/*.tex`).
**Gold-standard references:**
- **本书 rhythm：** `ch01_llm_decode_bottlenecks.tex` — multi-HW + YiRage + decode metrics
- **O'Reilly 章骨架：** [`reference-chapter-1.pdf`](../reference-chapter-1.pdf) — opening hook, goodput/mechanical sympathy sections, Takeaways granularity (§七)

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

全书章节对标 **两层 gold standard**：

| 层 | 参考 | 用途 |
|----|------|------|
| **本书定稿** | `ch01_llm_decode_bottlenecks.tex` | 多硬件 + YiRage + decode goodput 指标链 |
| **O'Reilly 样章** | [`reference-chapter-1.pdf`](../reference-chapter-1.pdf) | 章结构、Takeaways 粒度、案例叙事、profile-first 方法论 |

When expanding ch02+, read **ch01 的节奏** + **Fregly Ch.1 的章骨架** before drafting.

---

## 七、O'Reilly 对齐：*AI Systems Performance Engineering*（Fregly）风格映射

**Reference sample:** [`reference-chapter-1.pdf`](../reference-chapter-1.pdf) — *AI Systems Performance Engineering* (Chris Fregly), **Ch.1 Introduction and AI System Overview** (repo root).

本书与 Fregly 同属 **中高阶 AI 系统性能工程专著**，但聚焦 **编译器 + 多硬件 decode/MegaKernel**（YiRage），而非 PyTorch 全栈 + NVIDIA 集群运维/K8s。对齐的是 **叙事范式、章骨架与 Takeaways 粒度**，不是复制其 CUDA/PyTorch/K8s 边界。

### 0. Fregly Ch.1 章骨架（逐段对照，Agent 必遵）

样章 **Table of Contents** 与正文顺序如下——深度改写章应 mimic 此 **节奏**，替换为本书主题：

| 顺序 | Fregly Ch.1 节 | 样章做法 | 本书等价 |
|------|----------------|----------|----------|
| 1 | **Opening hook**（DeepSeek / H800 / $6M） | 具名案例 + 出口限制 + 可核验数字 + 「skill beats brute force」 | TaxBreak / Memory-Floor / DeepSeek-V3 / 出口限制类比；**禁止**「In this chapter we will…」式 meta 段（样章 p.2 那段为反例） |
| 2 | **The AI Systems Performance Engineer** | 角色 + 职责清单（benchmark / scale / resources） | 解码/MegaKernel 工程师视角：launches/token、bytes/token、编译 Pass |
| 3 | **Benchmarking and Profiling** | Nsight + PyTorch profiler；自动化回归测试 callout | TaxBreak 分解 + Nsight + `book-loop` 回归矩阵 |
| 4 | **DeepSeek case study**（长节 + Figure） | 约束 → DualPipe / FlashMLA / 开源透明 | DeepSeek MLA、FlashAttention、YiRage triplet 回归 |
| 5 | **Mechanical Sympathy** | Martin Thompson；FlashAttention 2–4×；MLA | residency-first fusion；FlashAttention / online softmax |
| 6 | **Measuring Goodput** | Meta ETR；**算例**（100k tokens / 10s → 83.3%） | `kernels/token`、`bytes/token`、`R_floor`；附算例或 cited cell |
| 7 | **Book Roadmap** | 映射 Part II–IV 各章 | 桥接 `\part{}` / 下一章 `\ref` |
| 8 | **Key Takeaways** | 6 条：**粗体祈使标题 + 2–4 句段落**（非单行 dash） | 5–8 条；每条 `\textbf{Title}` + 解释段 + `\citep{}` |
| 9 | **Conclusion** |  synthesis + **明确 bridge 到 Ch.2 硬件** | synthesis + bridge 到下一章 `\ref` |

**Opening hook 模板（Fregly 实测有效）：**

```latex
In [year/context], [named team] [surprising outcome] despite [hard constraint] \citep{…}.
They treated [scarce resource] as the bottleneck and [codesign action] \citep{…}.
Contrast this with [brute-force path]: [cost/scale numbers] \citep{…}.
The takeaway: at scale, [goodput insight]---not raw [FLOPs/utilization] \citep{…}.
```

**Side note / callout（样章 tip 框）：** 关键工程纪律用独立 `\paragraph{…}` 短段突出（如 automated perf tests、MLPerf 使用 caution）。不要用无内容的 `\paragraph{Review gate}` 复读。

### 1. 双线主轴对照（全书贯穿）

| Fregly 主线 | 样章原文要点 | 本书等价 |
|-------------|--------------|----------|
| **Mechanical Sympathy** | Martin Thompson；算法贴合 memory hierarchy；FlashAttention tile | **Hardware–software codesign**：约束 → Pass → kernel；**禁止** isolated GEMM 微基准 |
| **Goodput** | Useful work / time；discount stalled comm、failed restarts、data wait | **`kernels/token`、`bytes/token`、batch-1 `ms/token`、`R_floor`、HDBI** |
| **Profile-first** | Nsight Systems + Compute + PyTorch profiler；hypothesis → measure → adjust | TaxBreak + Nsight + IR diff；**先 profile 再 TC tile** |
| **Skill vs brute force** | DeepSeek on H800 vs GPT-4 $100M train | Memory-Floor fusion vs graph-only；multi-HW triplet |
| **Transparency** | Open-Source Week；MLPerf；reproducible benchmarks | `verified_facts.jsonl` + cited URLs + appendix regression |
| **Holistic stack** | HW + SW + algorithms 任一层弱则全栈 bottleneck | GPU + CPU + XDNA + compiler IR 同章对比 |

**EN:** Open chapters by naming the **constraint** (export rules, SRAM ceiling, launch floor), not by defining softmax from first principles.

### 2. 单章固定范式（Fregly 对齐，全书强制）

1. **Opening** — 具名案例 / 约束 / 量化锚点（1–4 段，**无** chapter meta-summary）
2. **`\section{…}` 正文** — 可检索标题；每节一个问题；**Figure/Table** 支撑论点
3. **Mechanism / Goodput 节**（核心章）— 至少一节显式 goodput 或 mechanical sympathy
4. **`\section{Key Takeaways}`** — 5–8 条；**标题 + 段落**（见下）
5. **`\section{Conclusion}`** — 串联 + **下一章 bridge**（必须 `\ref` 或 explicit chapter number）

**Key Takeaways 模板（对齐样章 p.47–48，非单行 bullet）：**

```latex
\section{Key Takeaways}
\label{sec:chXX_key_takeaways}

\begin{itemize}
\item \textbf{Measure goodput, not peak FLOPs.}
Raw tensor-core utilization misleads when communication, launches, or HBM bytes dominate decode \citep{taxbreak2026,memoryfloor2026,patel2025llminference}.
Profile end-to-end ms/token and decompose launches/token and bytes/token before tuning MMA tiles \citep{…}.

\item \textbf{Prefer skillful residency over brute-force silicon.}
…
\end{itemize}

\section{Conclusion}
\label{sec:chXX_conclusion}
… This chapter established … Chapter~\ref{chap:chYY} applies the same mechanical-sympathy lens to … \citep{…}.
```

**迁移：** 深度 Agent 润色章用上述 Takeaways + Conclusion；旧 `\section{Chapter Summary}` 与 Conclusion 后的 template padding **必须删除**。

### 3. Goodput 叙事模板（样章 §「Measuring Goodput」）

Fregly 给出 **定义 + 算例 + Meta 引用 + 行动项**。本书 decode 章应包含：

1. **定义一句**：useful tokens（或 useful layer output bytes）per unit time，扣除 materialized activations / 多余 launches / spill。
2. **算例或 cited cell**：TaxBreak launches/token、Memory-Floor $R_{\mathrm{floor}}$、或 fusion ablation 行。
3. **错误指标警示**：裸 FLOPs、SM util、peak bandwidth  alone。
4. **行动项**：先 fix bytes/token 或 launches/token，再 TC。

**EN sketch:** *If fusion removes six $d$-vector HBM round trips at $d{=}4096$ BF16, activation bytes drop $\approx 49$ KB/layer/token before KV reads—TC util can rise with flat ms/token.*

### 4. Mechanical Sympathy 叙事模板（样章 §「Mechanical Sympathy」）

1. 点名 **Martin Thompson / Jackie Stewart** 类比（一句即可）。
2. **Named algorithm**：FlashAttention / MLA / online softmax — tile 或 residency 如何贴合 hierarchy。
3. **Virtuous cycle**：算法 ↔ 硬件（Transformer Engine、TMA、SFU exp2）— 一句闭环。
4. **本书落点**：YiRage Pass / MegaKernel / XDNA static slot。

### 5. 与 Fregly 的刻意差异

| 维度 | Fregly 样章 | 本书 |
|------|-------------|------|
| 硬件 | NVIDIA GB200/NVL72、K8s、NCCL | GPU + **CPU + XDNA/AIE** |
| 软件 | PyTorch、Triton、vLLM 运维 | **YiRage IR**、decoder MegaKernel |
| 指标 | Training goodput、cluster $ | **Batch-1 decode** goodput |
| 附录 | 175+ checklist | Appendix regression + `verified_facts.jsonl` |
| 章首 | 含一段 meta overview（**勿学**） | **禁止** meta chapter summary 段 |

### 6. 深度 Agent 润色（选项 2）Fregly 验收清单

对照 [`reference-chapter-1.pdf`](../reference-chapter-1.pdf) 与 ch01，**全部**满足才记 **Fregly-ready**：

1. 章首 200 词内：**具名案例** + **≥2 个可核验数字**（已入 `verified_facts.jsonl`）
2. 无 Fregly 反模式 meta 段（「This chapter serves as…」「By the end of Chapter N, readers will…」）
3. 至少一节显式 **goodput** 或 **mechanical sympathy**（含 named kernel/Pass）
4. 每 `\section`：**multi-hardware delta**（GPU vs CPU vs NPU/XDNA 其二以上）
5. **Key Takeaways**：每条 = **粗体标题 + 解释段**（≥2 句），非单行 `\textbf{X} — one line`
6. **Conclusion**：≥1 段 synthesis + **明确 bridge** 到下一章
7. 禁止 `Review gate` / `Worked contrast` / `ensure_min_words` 模板污染
8. `verified_facts.jsonl` 覆盖正文关键数字；`\citep{}` 与 bib URL 一致

---

## Agent checklist (per editing session)

Before committing chapter prose, read [`reference-chapter-1.pdf`](../reference-chapter-1.pdf) §Key Takeaways for bullet granularity.

1. Does the chapter open with a **named case + constraint + numbers** (not a chapter roadmap paragraph)?
2. Does each `\section` open with a production problem or misconception (not a definition)?
3. Does every optimization claim name a hardware constraint and a measurable **goodput** effect?
4. Are GPU, CPU, and NPU/edge angles addressed where the topic applies?
5. Are forbidden lecture phrases absent (see Section III)?
6. Are citations tied to real benchmarks or architecture docs—not hand-wavy theory?
7. Does the section close with an industrial takeaway or YiRage/compiler mapping where relevant?
8. Do **Key Takeaways** use **bold title + explanatory paragraph** per item (Fregly style)?
9. Does **Conclusion** bridge explicitly to the next chapter?
10. Are all numbers web-verified with URLs in `books/research/<id>/verified_facts.jsonl` (§八)?

---

## 八、事实核验门禁

凡**事实描述、数据举例、厂商参数、性能数字**，必须先 **Web 检索 ≥2 轮、交叉验证**，写入 `books/research/<chapter_id>/verified_facts.jsonl` 并附 **可靠链接**，方可进入 `books/build/chapters/*.tex`。

- 禁止无 URL 的数字、禁止单一路径未核对就写入
- 未通过核验：仅用 `\vispending{}` / TBD，不得冒充实测
- 正文数字旁必须有 `\citep{}`；`book.bib` 中 URL 与核验日志一致
- **Fregly 对齐：** 样章 Ch.1 每个 major claim（DeepSeek cost、H800 bandwidth、MLPerf speedup）均带 source；本书同等标准

**EN:** No numeric fact ships without web verification, JSONL log, and matching bibliography URL.
