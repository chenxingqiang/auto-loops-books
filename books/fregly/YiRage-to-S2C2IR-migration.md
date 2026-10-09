# YiRage → S2C2IR 迁移计划（全书叙事主线切换）

> 决策日期：2026-10-09。政策：`AGENTS.md` §1.4（S2C2IR-first）。术语映射与架构事实见 [`S2C2IR-alignment.md`](S2C2IR-alignment.md)。
> 原则：**不改章 id、不动 OUTLINE 结构**（`book_prepare.py` 评分冻结），只替换叙事主角、术语与事实锚点。YiRage 降级为「历史实现/对照引擎」，可在正文以对照形式保留 1–2 处。

## 迁移优先级与分章动作

### P0 — 骨干章（先改，其他章引用它们）

| 章 | 现状（YiRage 叙事） | 迁移动作（S2C2IR 叙事） |
|---|---|---|
| **ch13**（编译理论五支柱） | Roofline-guided pass ordering，泛化 | 五支柱直接绑定 S²C² 四域 + Cost 四分量（`Cost = C_compute + C_storage + C_comm + C_synchronization − C_overlap`）；「合法空间」概念改用 `R(P,D)` 与 `HB_M = HB_source` |
| **ch14**（MLIR 基础设施） | YiRage MLIR integration points | 以本地 S2C2IR 工程为教材：四方言、`stor.object/materialize/transfer`、`--convert-stor-to-memref` space-map、Phase 1.5 语义规范化、`--s2c2-lower`（sequential ≠ 语义 ≠ async lowering 三分） |
| **ch21**（统一评测/triplet） | YiRage benchmark suite / triplet regression | harness 改为 `--s2c2-cost / --s2c2-enumerate / --s2c2-argmin / --s2c2-walk` 冻结命令族；triplet = 同一 IR + 不同 CapabilityProfile（4090/910B 实测 `v3-dataset/`）；新增「`Rank(Cost) ≈ Rank(Latency)` 相关性验证」小节（Fregly 完全没有的层） |
| **ch25**（自动优化/RL autotune） | YiRage search / superoptimize / RL | Evidence-Bounded Search（walk 契约 `A=(N,S,Rst,Nxt,Acc)`）+ **Rewrite License 五级门禁**（sufficient→authorized→licensed→plan→applied）；RL 降级为「未来前端提议源之一」，且必须过 License 门禁 |
| **ch29**（runtime 章） | YiRage 五层栈 runtime | 重写为 **S2C2IR 编译执行脊柱**：6C-M→7A→7B→Baseline v1→IR Apply Contract（#136–#141）；YiRage 五层栈保留为一个对照小节；标题按「读者能力产出」规则改（如 *S2C2IR Runtime Spine and Evidence-Bounded Rewrites*） |

### P1 — 深度绑定章

| 章 | 迁移动作 |
|---|---|
| **ch03**（硬件约束矩阵） | Constraint Matrix 改述为 Capability Schema v1 的 record 字段（compute_domain/transfer_domain/memory_class/pair/regime）；910B 实测数据进正文；「同一 Pass 在 GPU/CPU/NPU 上 legality 不同」用 capability-aware-schedule 的形式化表述 |
| **ch05**（XDNA 对标） | 增 S2C2IR Ascend 910B adapter 作第三执行形态对标（`backend-adapter-ascend.md`：AI Core/DMA/静态图 vs XDNA tiles）；XDNA 章地位不变，但「adapter ≠ backend」边界要写清 |
| **ch22**（profiling 工作流） | 证据采集对接：profiler 输出 → CapabilityRecord / measured evidence → License 门禁输入（「把 Fregly 的人工调优循环编译器化」的核心落点章） |
| **ch06/ch07/ch08/ch09**（驻留/静态角色/双缓冲/同步） | 各章的「YiRage xxx pass」小节改为 S2C2IR 对应冻结设计引用：ch06→storage-hierarchy/ntile/loop（residency、scf.for 双缓冲）；ch07→sched.concurrent/静态角色；ch08→pipeline semantics + storage-aware-pipeline；ch09→HB 语义 + `--check-s2c2-execution`（E1–E8）作「同步正确性可机检」示范 |

### P2 — 尾部章（随上文自然替换）

- **ch15–ch20**：编译器后端章中的「Versus YiRage …」对比句改为「Versus S²C² evidence-bounded …」；XLA/TVM/Triton/IREE 对比锚点换成 S2C2IR 冻结命令族与 License 门禁。
- **ch23/ch24/ch27/ch28/ch30**：MoE/KV/部署/框架协同章中的 YiRage 引用替换为 S2C2IR（KV 布局→Storage 语义注解；graph bucket→sched/execution 脊柱；co-design 三方表→framework × S2C2IR × hardware）。
- **附录 E/F/G**（YiRage 手册）→ 改为 S2C2IR 手册：命令行（`--s2c2-cost/enumerate/argmin/walk/check-s2c2-execution`）、CapabilityRecord schema、设计文档阅读指南（roadmap.md + 关键 frozen 文档路径）。

## 执行规范（对齐 loops 协议）

1. 每轮 1 章（PSIVE 单点突破）；改章时**必须**先读 `books/fregly/S2C2IR-alignment.md` + 对应 `chNN_analysis.md`（Fregly 侧）。
2. 事实锚点用本地路径（`docs/design/<doc>.md`）；数字来自 `v3-dataset/` 或设计文档，进 `verified_facts.jsonl`。
3. 禁止表述「S2C2IR 已生产代码生成」——当前 CUDA/Ascend 是 measurement adapter；V3 未 claim。
4. 术语替换对照 `AGENTS.md` §1.4 映射表；`grep -ri yirage books/build/chapters/` 应随迁移递减（终态：仅对照性提及 ≤10 处）。
5. 每章迁移后跑 `book_prepare.py --chapter <id>` 保持 gate 绿；`book_results.tsv` 记录 keep/discard。
