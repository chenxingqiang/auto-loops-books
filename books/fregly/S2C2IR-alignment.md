# S2C2IR 本地仓库深度对齐文档

> 来源：`/Users/xingqiangchen/S2C2IR`（本地 checkout，commit `f0ae2ad`，106 份设计文档 + 完整 MLIR 工程）。
> 用途：新书《AI Compiler Performance Engineering》的技术底座对齐——所有引用 S2C2IR 的章节应以下文为准，**取代** `README.md` 中的简要段落与早期分析中基于 GitHub README 的粗粒度描述。

## 一、S2C2IR 实际架构（与 GitHub README 的差异）

本地仓库揭示的关键事实（README 未完整呈现）：

1. **四方言 MLIR 工程**：`include/s2c2/{Storage,Compute,Comm,Schedule}` + `lib/{Analysis,Comm,Compute,Conversion,Schedule,Storage}` + `test/`（lit 测试）——真实可编译的 MLIR out-of-tree 项目，非纸面设计。
2. **执行语义已冻结（Phase 2B）**：`HB = TC(PO ∪ SW ∪ ConstructOrder)`；Token=Event/SW、Concurrent=NoOrderingRequirement、Pipeline=StageOrder。Oracle：`--check-s2c2-execution`（E1–E8）。**HB 保持是所有 lowering 的正确性标准**。
3. **Realization Space v0.4.0 冻结**：`R(P, D) = { M | IsLegal(P, D, M) ∧ HB_M = HB_source }`——成员资格是 **HB 相等**（非细化）。其上叠加冻结的 Cost v0.1–v0.3、Search/Pareto v0.4.1–v0.4.12（`A = (N, S, Rst, Nxt, Acc)` walk 契约）、Realization Transform v0.5.0–v0.5.2（`T : P → P' ∪ {⊥}`，仅当 `HB(P') = HB(P)`）。
4. **Evidence-Bounded 是"三层决策"而非口号**：
   ```text
   1. Semantic     sched.concurrent ≠ 物理并行承诺
   2. Capability   Capability = f(hardware, pair, size, r, residency, sync, resource)
   3. Authorization  serial ∧ applicable ∧ measured ∧ benefit proven ⇒ rewrite_license = yes
   ```
   **Rewrite License 是产品**；Capability 分类本身不是重写。"No evidence ⇒ no destructive optimization"。
5. **硬件中立 Capability Schema v1（冻结）**：单一 `CapabilityRecord`（pair/depth/memory/sync 四类 record_kind；compute_domain、transfer_domain、memory_class 等字段），4090（CUDA）与 **Ascend 910B** 填同一 schema（已实测 `v3-dataset/ascend910b/`），CIM 为第三候选。禁止 `acl_*`/`davinci_*` 厂商键——"Hardware Agnostic ≠ Hardware Universal"。
6. **双后端测量适配器（非编译后端）**：CUDA 4090 与 Ascend 910B 均为 measurement adapter（`Pilot → one legal M → stand-in → latency`），验证 `Rank(Cost) ≈ Rank(Latency)`（V3 尚未 claim）。910B 被选为第二厂商正因它与 GPU 是**异构执行系统差异**（AI Core/DMA/静态图形态），这正是我们书跨硬件主线的现成实验证据。
7. **编译执行脊柱（当前产品锁）**：6C-M Sufficiency(#136) → 7A Authorization(#137) → 7B ONE storage rewrite(#138) → Semantic Baseline v1(#140) → IR Apply Contract(#139 frozen @038f4a1) → W0-3/2 apply inhabitant v0。链条：`sufficient ≠ authorized ≠ rewrite-license ≠ rewrite-plan ≠ rewrite-path ≠ applied`——每一步显式分离。
8. **存储层级调度弧（Phase 3F→5B）**：SSD↔DRAM↔HBM↔Compute 的 materialize/prefetch/residency/overlap 决策；`scf.for` 循环携带 residency（SSA iter_args 即双缓冲）；Phase 5A `policy=measured-storage-v1` 已在 4090+910B 上运行。

## 二、S2C2IR ↔ 新书章节精确映射

| S2C2IR 概念（本地文档锚点） | 新书章节 | 写法建议 |
|---|---|---|
| 四方言（stor/comp/comm/sched）、`stor.object/materialize/transfer`、Phase 1.5 语义规范化 | ch13（编译理论五支柱）、ch14（MLIR 基础设施） | ch14 直接用本地仓库做教材：dialectric 栈 + bufferization + `--convert-stor-to-memref` space-map |
| HB 语义、Token/Concurrent/Pipeline 组合、E1–E8 oracle | ch09（四级同步）、ch13 | 用 `--check-s2c2-execution` 作为"同步正确性可机检"的示范案例 |
| Cost v0.1–v0.3（`Cost = C_compute + C_storage + C_comm + C_synchronization − C_overlap`） | ch13（roofline-guided pass 排序）、ch21（triplet 基准） | 代价模型四分量对应 S²C² 四域——天然的故事线 |
| Realization Space R(P,D)、Enumerator/ArgMin/Pareto、Search walk | ch21（跨硬件基准）、ch25（自动调优） | `--s2c2-enumerate/argmin/walk` 是"合法空间枚举→评分→选择"的完整可运行示范 |
| Evidence-Bounded 三层决策 + Rewrite License | **全书方法论主线**（ch01、ch13、ch22、ch25） | ch01 即引入"No evidence ⇒ no destructive optimization"作为对 Fregly goodput 纪律的编译器化升级 |
| Capability Schema v1 + 4090/910B 数据集 | ch03（硬件约束矩阵）、ch05（XDNA 对标） | `v3-dataset/` 的实测 record 是"硬件能力模型"章节的现成数据；910B 与 XDNA/AIE 同属非 GPU 执行形态 |
| CUDA/Ascend measurement adapter（V3 验证 `Rank(Cost)≈Rank(Latency)`） | ch21、ch22（profiling） | 展示"模型排序 vs 实测排序"相关性验证方法——Fregly 完全没有的一层 |
| 存储层级调度（3F–5B：prefetch/residency/scf.for 双缓冲/measured policy） | ch06（数据驻留）、ch08（双缓冲流水线） | `storage-ntile/storage-loop` 文档即"编译器自动插入双缓冲"的冻结设计文档 |
| IR Apply Contract / 执行脊柱（#136–#141） | ch26（生产落地）、ch29（YiRage runtime） | "sufficient→authorized→licensed→plan→applied"五级门禁 = CI 中合法性验证流水线的蓝本 |
| StableHLO 前端（Phase 2C/8A，later） | ch14–15（前端捕获） | 书中可预告：PyTorch/JAX → StableHLO → S²C² 的路线图位 |

## 三、对 20 份 Fregly 分析的修正与强化

此前分析基于 GitHub README，以下三点需要按本地仓库校准（分析主体结论不变，且得到加强）：

1. **evidence-bounded 有精确形式**：不是泛泛的"无证据不重写"，而是**五级显式门禁**（sufficient/authorized/rewrite-license/rewrite-plan/applied）。各章分析中"差异化"小节引用时应写明链条，这是比 Fregly"人工验证循环"强得多的卖点——正确性由构造与门禁保证。
2. **跨硬件不是愿景而是现状**：4090 + Ascend 910B 双实测数据集已存在（`v3-dataset/ascend910b/`），同一 schema 同一调度器。ch03/ch05/ch21 的"跨硬件对标"应直接引用这些 record；"同一 IR + 不同 CapabilityProfile → 不同合法调度"（capability-aware-schedule.md）就是我们"same IR, three backends"（YiRage triplet）叙事的 S2C2IR 版本。
3. **HB 相等（非细化）是全书正确性叙事的技术钩子**：Realization Space 成员资格 = `HB_M = HB_source`，而 lowering 实现 correctness = `HB_source ⊆ HB_impl`——这一区分（`realization-space.md` 首屏公式组）可贯穿 ch09/ch13/ch21，作为"语义合法 ≠ 实现正确"的形式化注脚，正对应 Fregly 分析中反复出现的"IR 上合法的重排 ≠ 硬件上合法的 realization"。

## 四、写书时的引用规范建议

- 事实锚点：引用本地设计文档相对路径（如 `docs/design/realization-space.md`），而非 GitHub URL——本地是权威版本（含 #139/#141 等未推送 README 的进度）。
- 术语表：Rewrite License / Realization Space / Capability Record / HB oracle / measurement adapter（≠ backend）应进书的前置术语表；尤其"adapter ≠ compiler backend"这一区分要写清，避免读者误解 S2C2IR 已有生产代码生成。
- 冻结纪律作为叙事素材：S2C2IR 的"frozen / do not open X"工作方式（每层设计冻结后才开下一层）本身就是对 Fregly ch20 "verifier 闭环"的方法论升级案例，可在 ch25/ch27 引用。
