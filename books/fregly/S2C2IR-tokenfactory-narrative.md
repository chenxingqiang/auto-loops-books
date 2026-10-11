# S²C²IR Token Factory 叙事与模型案例（行业汇报沉淀）

> 来源：`~/Downloads/S2C2IR_异构编译与集群编译_行业汇报_Rubin数学建模完整增强版.pptx`（67 页，2026.09 上海，TOKEN 工厂 · 异构混推技术研讨会）。
> 定位：[`S2C2IR-alignment.md`](S2C2IR-alignment.md)（代码仓库视角）的**叙事补充**——提供全书开篇钩子、前沿模型案例与集群形式化入口。
> 边界纪律（汇报全篇贯彻，书稿照搬）：paper-reported / illustrative / not-a-claim-of-native-backend —— 与 evidence-bounded 立场一致。

## 一、Token Factory：全书开篇叙事框架（ch01–02）

**编译对象从 Kernel 扩展到 Token Generation Path。** 三条论证：

1. Token 是推理服务的性能观测单元——TTFT/TPOT/throughput/SLO 均归结为 token generation 的时间特征（对应 Fregly 的 goodput，但把观测单元从"系统"缩到"token path"）
2. KV cache 具有持久状态属性——分块、复用、迁移、卸载直接影响 decode 的内存访问与时延
3. 计算、通信、存储共同决定 token 时间线——prefill/decode 资源特征不同；跨 GPU/NPU/节点后引入通信、拓扑与驻留约束

**结论句（书 ch01 可直接化用）**："Token 工厂"天然同时触发四类编译问题：**数据存在哪里、算在哪里、怎么搬、何时发生** ⇔ stor/comp/comm/sched 四维。

文献支撑链（2018–2026 编译抽象单向扩展：Compute→Memory→Communication→Execution）：TVM→Triton→MLIR/GSPMD→FlashAttention/Orca/Alpa→vLLM/FlexGen→DistServe/Mooncake/Sarathi→FlashInfer/Mirage/Triton-distributed→TileLang/MPK。硬数字（paper-reported）：vLLM 2–4×、DistServe 7.4×、Sarathi-Serve 2.6×（Mistral-7B/A100）、MPK 1.7×。

## 二、Rubin 产业信号（ch03 素材）

Rubin 把 Compute/Memory/Interconnect/**Context storage（CMX）**协同设计为"规模化执行域"。IR 表达关系随之扩展：

| 从 | 到 |
|---|---|
| 单卡 kernel | Token Path |
| device memory | memory hierarchy + context tier |
| PCIe / library call | scale-up fabric / collective |
| static execution | dynamic agentic execution |

S²C²IR 抽象定位四问：STORAGE 保留 object/residency/tier；COMPUTE 保留 attention/MoE/GEMM 共同形状；COMMUNICATION 把 dispatch/collective/KV movement 提到 IR 可见层；EXECUTION 把顺序/并发/pipeline/HB 留到 lowering 前。

**抽象缺口陈述**（operator-centric flow 中跨栈信息落在 extra metadata / runtime policy / custom scheduler / vendor special-case）：S²C²IR 不是替代 vendor backend，而是把跨 backend 的**组合语义**提前到可验证层。

## 三、数学建模（ch13/ch21 形式化入口）

```text
Program = Objects(𝒪) + Compute(𝒦) + Movement(𝓜) + Execution Events(𝓔) + Happens-Before
```

- **Storage**：identity ≠ residency；同一 KV object 可驻留 {HBM, DDR, SSD, UB}；目的地有效性由完成事件见证，不改变逻辑身份；**placement 是 realization 属性，logical dataflow 不随 residency 改变**
- **Execution**：HB 是偏序不是全序；无 HB = 无顺序要求 ≠ 物理并行承诺
- **Realization**：ρ_D 目标映射（GPU: TMA/NCCL/Tensor Core；910B: MTE/HCCL/AI Core；CIM: crossbar/ADC/MVM）；**核心不变量：hardware realization 可变，语义关系不变**
- **Capability 分层**：Evidence→Applicability→Profile→Legality（fact only）；`all-allowed ≠ sufficient`、`unproven ≠ forbidden`、`legality ≠ authorization`
- **集群编译对象**：`Program × Device × Topology × Realization`；多目标 cost（latency/memory/comm/energy）是 selection 层，不在语义定义内

## 四、前沿模型案例（ch10/ch23/ch28 素材，全部配 IR sketch）

### DeepSeek-V4 Pro（1.6T / 激活 49B / 1M ctx / 384 experts Top-6 / CSA+HCA+DSA / FP8+FP4 / MTP）

单 token decode path：Token state→Hybrid Attn(CSA/HCA)→Router→MoE(6 routed+1 shared)→MTP proposal→Logits。
编译视角：稀疏+压缩+长上下文不是单 kernel 问题，是 **storage（压缩 KV+expert 权重）/ routing（dispatch/combine）/ execution（decode 迭代+MTP）的联合问题**。
IR sketch（原文可直接引用）：

```text
stor.object    expert_w[0..383]     # persistent weight identity
stor.object    kv_c[req]            # compressed attention state
comm.dispatch  token → expert shards
comp.attention Q + compressed KV → H
comp.gated_mlp H → expert outputs  # Top-6 + shared
sched.pipeline dispatch(k+1) ∥ compute(k)
```

### Kimi K3（2.8T / 激活 104B / 93 层 = 69 KDA + 24 Gated MLA / 896 experts Top-16+2 shared / MXFP4+MXFP8）

- **Hybrid cache = Storage 语义绝佳实例**：logical prefix object `P = token[0:N]`；paged KV（full-attn 层，按 token/block 复用）；KDA recurrent state（**原地更新语义**）；expert weights（sharded+persistent）。快照策略需结合生命周期与复用关系编译建模
- **MoE 集群案例**：dispatch = permute→all-to-all，combine = reverse permute→weighted reduce；`sched.pipeline dispatch(k+1) ‖ expert_compute(k)`；关键变量 topology/latency/load balance

### 五个编译案例（各章挂载点）

| Case | 内容 | 书稿挂载 |
|---|---|---|
| GPU attention | KV tile prefetch ∥ compute，`comm.prefetch/comp.attn_tile/sched.wait` | ch08（双缓冲）、ch10 |
| 910B | AllGather 结果留 UB/L1 不回 DDR，MatMul 直接消费（CANN 8.5 UB Fusion） | ch05（XDNA/910B 对标）、ch06（驻留） |
| CIM | W@crossbar、MVM、ADC/quant/accum；**weight residency 与 compute mapping 直接耦合** | ch03（第三执行形态）、ch27 |
| KV 分层 | HBM(hot)/DRAM(warm)/SSD(cold)；identify hot→prefetch→overlap→preserve HB | ch06、ch24（Mooncake 对标） |
| Cluster | compute(k) ∥ comm(k−1) 流水 + PD disagg placement | ch24、ch28 |

### 统一坐标系（ch21/ch30 可用）

| 模型 | Storage | Compute | Communication | Execution |
|---|---|---|---|---|
| DeepSeek-V4 | compressed KV + expert W | CSA/HCA + MoE Top-6 | dispatch/combine | decode + MTP |
| Kimi K3 | KDA state + paged KV + expert W | KDA + Gated MLA + Top-16 | dispatch + hybrid cache | decode + prefix reuse |

可复用抽象：**object identity · residency · token movement · HB/concurrency · capability evidence**——模型结构演化，关系跨模型复用。

## 五、语义原则四条（ch09/ch13 小节骨架）

1. **逻辑对象与物理驻留解耦**：`stor.object = "是谁"；materialize/transfer = "现在在哪里"`
2. **Token Dispatch 通信显式表达**：HB 链 Dispatch 完成→Expert 消费→Combine 读取；realization 可换算法/stream/barrier，**不能删依赖**
3. **跨芯片存储—计算—运动解耦**：IR 不保存"哪条厂商指令"，保存"数据从哪里来→到哪里→在哪被消费→与谁同步"
4. **Capability/Legality 事实语义**：allowed/forbidden/not-applicable/**unproven** 四值；`all-allowed ≠ sufficient`、`legality ≠ authorization`

## 六、对迁移计划的影响（增量）

- **ch01–02**：开篇钩子换用 Token Factory 框架（四类编译问题一句话立论），保留 TaxBreak/Memory-Floor 计数器增量
- **ch10**：online softmax 章可引 DeepSeek-V4 CSA/HCA 压缩 KV 作前沿案例
- **ch23**：MoE 编译章用 Kimi K3 Top-16/896 + dispatch pipeline IR sketch 作集群级案例
- **ch28**：hybrid cache（paged KV + KDA state + prefix object）作 S2C2IR Storage 语义的 serving 实例
- **ch24/ch21**：集群编译对象四元组 + 统一坐标系表直接入正文
- **ch03**：Rubin 四问表（kernel→path/memory→hierarchy+context/PCIe→fabric/static→agentic）作产业信号小节
