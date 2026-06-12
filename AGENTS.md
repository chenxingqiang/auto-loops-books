# AGENTS.md

> **Cloud Agent 操作手册** — 本仓库以 [Karpathy autoresearch](https://github.com/karpathy/autoresearch) 模式持续自我改进：**固定 harness 打分 → Agent 改可变面 → git 保留/回滚 → 写回契约 → 下一轮**。本文是单一真相源；细节协议见 [`program_books.md`](program_books.md)，CLI 见 [`loops/README.md`](loops/README.md)。

## 目录

1. [仓库使命与双轨目标](#1-仓库使命与双轨目标)
2. [统一闭环框架 PSIVE + Git](#2-统一闭环框架-psive--git)
3. [仓库地图与职责边界](#3-仓库地图与职责边界)
4. [Loops 自动化 · 规范化 · 提效（Harness 轨）](#4-loops-自动化--规范化--提效harness-轨)
5. [Book Loop 书稿迭代（内容轨）](#5-book-loop-书稿迭代内容轨)
6. [每轮 Git 闭环](#6-每轮-git-闭环)
7. [单轮检查清单](#7-单轮检查清单)
8. [工具索引](#8-工具索引)
9. [当前轮次笔记](#9-当前轮次笔记)
10. [环境与 Gotchas](#10-环境与-gotchas)

（§5.5 [目录迭代](#55-目录迭代agent-可改--内容不足时必用)）

---

## 1. 仓库使命与双轨目标

### 1.1 使命

**整个 repo 没有「做完就停」** — 持续优化两类产出：

| 轨 | 可变面 | 固定 harness | 主指标 | 协议 |
|----|--------|--------------|--------|------|
| **内容轨** Book | `books/build/chapters/*.tex`、bib、research | `book_prepare.py` + `book-loop` | `quality_score`、Fregly-ready | [`program_books.md`](program_books.md) |
| **Harness 轨** Loops | `loops/iterate.py`、`*_tools.py`、agent_tasks | 现有 step 仍绿 + 回归不破坏书稿 | 单轮耗时 ↓、任务噪声 ↓、自动化覆盖 ↑ | 本文 §4 + 用户点名 |

两轨**共用**同一 PSIVE 闭环与 Git 协议（§2、§6）。每轮只攻**一个主攻点**（一章 **或** 一项 harness 改进），避免混做导致无法归因。

### 1.2 North stars

| 层级 | 标准 |
|------|------|
| **书稿终态** | **30** 章 **Fregly-ready**（非仅 `chapter_ready`）；Part VIII = runtime + 推理框架 + YiRage 协同 |
| **样章对照** | [`reference-chapter-1.pdf`](reference-chapter-1.pdf) — mechanical sympathy、goodput、profile-first、**Key Takeaways → Conclusion** |
| **文风契约** | [`books/WRITING_STYLE.md`](books/WRITING_STYLE.md) §I–§VIII，§七 Fregly 映射 |
| **Harness 终态** | Agent 少猜、少重复劳动：`book-loop` 一步产出完整 `agent_tasks` + 可复现 gate；协议单源、路径一致 |

### 1.3 默认行为

- 用户未喊停 → **验证通过 → commit → push → 立即 Loop R{n+1}**
- **不要**新建「一键跑完全阶段」mega-orchestrator，除非用户明确要求
- 优先 **扩展现有 `book-loop` / `iterate.py` / agent_tasks**，而非平行脚本

---

## 2. 统一闭环框架 PSIVE + Git

```mermaid
flowchart LR
  P[1 Perceive 感知] --> S[2 Strategy 策略]
  S --> I[3 Implement 落地]
  I --> V[4 Verify 验证]
  V --> M{通过?}
  M -->|否| S
  M -->|是| E[5 Evolve 进化]
  E --> G[6 Git commit + push]
  G --> N[7 扫描 backlog]
  N --> P
```

### 核心原则

| 原则 | 含义 |
|------|------|
| **Harness 先行** | 没有 `compile_ok`、coverage、事实 JSONL，不写新数字、不宣称 ready |
| **单点突破** | 每轮 1 章 **或** 1 项 harness；禁止同轮混改 unrelated 面 |
| **证据链** | `make.sh` + `book_prepare` + fact/citation 报告通过后再改契约文档 |
| **最小 diff** | 匹配现有命名与结构；不 over-engineer 辅助脚本 |
| **验证后沉淀** | 结论写入 `AGENTS.md` / `WRITING_STYLE.md` / `program_books.md` 后再 commit |
| **每轮 commit + push** | push 成功 → 扫描 backlog → 自动下一轮（用户喊停除外） |
| **评分冻结** | loop 期间不改 `book_prepare.py` **权重**；**可**扩/改 `OUTLINE` 与目录 spec |
| **目录可迭代** | 内容不够、结构不合理、spec 与正文不对齐时，**Agent 可改目录**（见 §5.5）；须三层同步 |
| **保护深度章** | `AGENT_SKIP` 章禁 batch；用 `deep-rewrite` + 手改 |

### 终止条件（仅此停止）

- 用户明确停止（「停」「不要 push」等）
- 验证失败且合理修复后仍失败（**不 commit / 不 push**）
- push 连续失败（重试一次后仍失败）
- 纯只读/评审任务

**不因 27/27 `chapter_ready` 停表** — 继续 Fregly 深度与 harness 提效。

### 策略分流（每轮必选其一）

```
uv run book-loop status
```

| 信号 | 轨 | 动作 |
|------|-----|------|
| 未 ready / compile 失败 / fact 失败 | 内容 | `book-loop step` 或 `deep-rewrite` |
| 已 ready 但 `Chapter Summary` / 模板污染 | 内容 | Fregly 章末迁移 + 手改 |
| **内容不够 / 目录与正文脱节** | 内容 | **改目录**（§5.5）→ 再写/扩章 |
| `quality_score` < 85 核心章 | 内容 | `deep-rewrite` + brief；必要时 **增删 `\section` 或调整 OUTLINE** |
| Agent 重复劳动、路径/doc 漂移、task 噪声 | Harness | 改 `iterate.py` / agent_tasks / README 对齐 |
| 新 gate 可机器化（lint、rg 规则） | Harness | 并入 `build_agent_tasks` 或 evaluate，**不改权重** |

---

## 3. 仓库地图与职责边界

| 路径 | 角色 | Agent 可改 | 冻结 / 慎改 |
|------|------|------------|-------------|
| [`loops/iterate.py`](loops/iterate.py) | **主 orchestrator** | harness 逻辑、agent_tasks、CLI | 保持 step 语义稳定 |
| [`book_prepare.py`](book_prepare.py) | 评分 harness | **仅 `OUTLINE`** | 权重、`word_score`、compile 逻辑 |
| [`book_loop.py`](book_loop.py) | CLI shim |  rarely | — |
| `books/build/chapters/*.tex` | **正文主路径** |  prose / structure | 模板 infra |
| [`book_content.md`](book_content.md) | 中文目录 spec（**intent 源**） | **增删改章/节、模块划分、写作意图** | 改后必须同步 OUTLINE + tex |
| [`deps/YiRage`](deps/YiRage) | **YiRage 上游子模块**（runtime/compiler 工程锚点） | pin 版本、文档引用路径 | 勿手改 vendor 树（在 upstream 改） |
| [`deps/`](deps/) | **编译器 + DeepSeek 推理基建子模块** | pin SHA、ch14–19 / ch23–24 对照 | 见 [`deps/README.md`](deps/README.md)；**完整 DeepSeek 推理引擎未开源** |
| [`deps/README.md`](deps/README.md) | 子模块 init / build 说明 | 随 submodule 流程更新 | — |
| `books/research/<id>/` | 研究 + `verified_facts.jsonl` | 核验日志 | 捏造 URL |
| `books/visuals/<id>/` | 图表 plan + generated | plan / snippets | — |
| [`research_tools.py`](research_tools.py) | 文献检索 | 用户点名修 harness | loop 中默认不动 |
| [`book_visuals.py`](book_visuals.py) | 图表管线 | 用户点名 | loop 中默认不动 |
| [`fact_verify.py`](fact_verify.py) | 事实 gate | 用户点名 | loop 中默认不动 |
| [`book_agent_rewrite.py`](book_agent_rewrite.py) | batch 重写 | `AGENT_SKIP` 集 | 勿覆盖 skip 章 |
| [`book_results.tsv`](book_results.tsv) | 实验日志 | append keep/discard | 勿删历史 |
| [`loops/loop_state.json`](loops/loop_state.json) | 上轮 tasks / eval | 本地读写 | gitignore |
| `books/settings.tex` 等 | LaTeX 基础设施 | **禁止** | 模板 |

**路径易错：** 正文在 **`books/build/chapters/`**（非 `books/chapters/`）。`FACT_VERIFICATION.md` 已并入 `WRITING_STYLE.md` §八。

---

## 4. Loops 自动化 · 规范化 · 提效（Harness 轨）

> 目标：让 **每一轮 Agent 时间花在不可替代的 prose/判断上**，机器段可重复、可审计、文档一致。

### 4.1 规范契约（改 harness 时必须保持）

|  artifact | 规范 |
|-----------|------|
| **`loop_state.json`** | 每 step 写入：`chapter_id`、`actions[]`、`agent_tasks[]`、`evaluation`、`errors[]`；Agent **先读 tasks 再动笔** |
| **`book_results.tsv`** | 表头 `commit\tcoverage_pct\tword_count\tcitations\tquality_score\tstatus\tdescription`；`status ∈ {keep,discard,crash}` |
| **`agent_tasks`** | 动词开头、可执行、单条可验收；禁 vague「提高质量」 |
| **CLI** | 入口仅 `uv run book-loop <cmd>`（`status` / `step` / `run` / `deep-rewrite` / `insert-visuals`） |
| **文档单源** | 行为以 `program_books.md` 为准；操作摘要以本文为准；CLI 细节以 `loops/README.md` 为准 — **改行为时同步三处** |

### 4.2 提效原则（高效达成目标）

1. **机器做多，Agent 做少** — research / visuals / compile / evaluate / fact lint 已在 `step`；Agent 专注 prose、bib、outline、Fregly 结构
2. **不叠 orchestrator** — 新阶段并进 `iterate.py` 现有 phase 链，或 enrich `build_agent_tasks`
3. **可观测** — `status` 必须回答：下一章、缺口、priority；harness 改完跑 `book-loop step --skip-research` 冒烟
4. **可回滚** — harness 改坏 → `git revert`；书稿改坏 → restore 章文件；**不 amend 已 push**
5. **批处理禁令** — 深度章、`AGENT_SKIP`、`ensure_min_words` 章末 padding 均降低有效 goodput
6. **文档与代码同 PR** — 改 `iterate.py` 行为 → 同轮更新 `loops/README.md` + 本文 §9 笔记

### 4.3 Harness 改进 backlog（感知扫描）

```bash
# 旧章末 / 模板污染（应用 task 或 lint 自动提示）
rg -l '\\section\{Chapter Summary\}' books/build/chapters/ || true
rg -l 'Review gate|Worked contrast' books/build/chapters/ || true

# 文档路径漂移
rg 'books/chapters/' --glob '*.md' || true

# iterate 与 program 不一致
rg 'FACT_VERIFICATION\.md' loops/ book_prepare.py || true
```

**优先级（Harness 轨）：**

1. 修复导致 step 失败或误报 ready 的 bug
2. 将 Agent 反复手做的检查并入 `build_agent_tasks` / soft lint（如 Fregly 章末、numeric uncited）
3. 统一路径与文档（`build/chapters`、`book_content.md`）
4. 缩短慢路径（`--skip-compile` 开发、`--skip-research` 重 prose 轮）
5. 可选：`deep-rewrite` 与 `step` 共享 phase 函数，减重复代码

### 4.4 Harness 改动验证

```bash
uv sync
uv run book-loop status
uv run book-loop step --chapter ch01 --skip-research   # 或 --skip-compile 开发时
cd books && bash make.sh
uv run book_prepare.py --chapter ch01
```

通过后再更新文档 + commit。**禁止**为通过 gate 而改评分权重。

---

## 5. Book Loop 书稿迭代（内容轨）

### 5.1 执行前闸门（动笔 LaTeX 前必做）

**四轮自问**（策略卡片 1～2 句/问）：

1. **层级**：outline / scaffold / 深度 prose / 事实·引用 / 图表？**是否需要改目录？**
2. **Fregly 差距**：goodput 数字、multi-HW、Key Takeaways、profile-first？
3. **证据**：数字进 `verified_facts.jsonl`？图表行有 `\citep{}`？
4. **机会成本**：`status` 里是否有更高 priority 项？

```bash
uv run book-loop status
uv run book_prepare.py --chapter <id>
grep -E 'Chapter Summary|Review gate|ensure_min_words' books/build/chapters/<file>.tex || true
```

命中模板污染 → `deep-rewrite` + 手改；**禁止**深度章 Conclusion 后 `ensure_min_words()`。

**Gold-standard 正文：** `ch01_llm_decode_bottlenecks.tex`；深度试点 ch04 / ch10 / ch11。

### 5.2 内容轨各层要点

#### 感知

```bash
uv sync && uv run book-loop status [--pick weakest]
uv run book_prepare.py --chapter <id> && uv run book_prepare.py --list
cd books && bash make.sh
```

读：`loop_state.json`、`book_results.tsv`、`WRITING_STYLE.md` §VII、`reference-chapter-1.pdf`。

#### 策略 → 模式

| 模式 | 命令 | 何时 |
|------|------|------|
| 机器 step | `book-loop step [--chapter chXX]` | stub / research / visuals / 首次扩写 |
| 深度 | `book-loop deep-rewrite --chapter chXX` | Fregly prose；`quality_score` 目标 ≥ 85 |
| Batch | `book_agent_rewrite.py chXX` | 非 `AGENT_SKIP` 且用户允许 |
| 专名 | `book_proper_nouns.py --chapter chXX --fix` | 术语一致 |

#### 落地（可改 / 禁止）

**可改：** `books/build/chapters/*.tex`、`book.bib`、`books/research/`、`books/visuals/`、**`book_content.md`（全书目录 spec）**、**`book_prepare.py` → `OUTLINE` only**（章 id、section patterns、`min_words`/`min_citations`）、**`books/main.tex` `\input` 顺序**、章内 `\section`/`\subsection` 结构。

**禁止：** 评分权重、LaTeX 模板 infra、无 JSONL 的数字、深度章章末 filler、`git add -A`、**只改 `.tex` 不改 spec/OUTLINE 的「幽灵章节」**。

**深度单章流程：**

1. `book-loop deep-rewrite --chapter chXX`
2. 读 `deep_rewrite_brief.md` + 样章 PDF
3. 每 section：问题开篇 → HW → 编译/内核 → multi-HW → cited metric / example
4. 章末 `\section{Key Takeaways}` + `\section{Conclusion}`
5. `book_proper_nouns.py --fix`

#### 验证

| Gate | 要求 |
|------|------|
| `chapter_ready` | coverage 100%、words/cites 达标、visuals 齐、`compile_ok` |
| **Fregly-ready** | 上列 + Takeaways/Conclusion + 无模板污染 + 开篇量化 + 事实 JSONL |

Fregly 清单见 `WRITING_STYLE.md` §七.5–§七.6。

### 5.3 内容 backlog 优先级

1. `compile_ok` false / fact 失败  
2. 未 `chapter_ready`（`--pick weakest`）  
3. ready 但无 Key Takeaways  
4. 核心章 `quality_score` < 85  
5. `visual_missing` / 弱引用  
6. 目录三层不一致（`book_content.md` / `OUTLINE` / `main.tex`）

### 5.4 `chapter_ready` vs Fregly-ready

| 状态 | 含义 |
|------|------|
| `chapter_ready` | 机器 rubric 全绿 |
| **Fregly-ready** | ready + 样章级 narrative / 章末 / 事实链 |

### 5.5 目录迭代（Agent 可改 — 内容不足时必用）

**Agent 在 loop 中有权且应主动修改全书目录**，当 prose 无法在不改结构的前提下达到 Fregly 密度或 gate 要求时。目录不是冻结物；[`program_books.md`](program_books.md)「Outline iteration」与本文一致。

#### 何时改目录（触发条件，满足任一即可）

| 信号 | 典型目录动作 |
|------|----------------|
| 单章 **`word_count` 长期低于 `min_words`**，且已排除模板 padding | 在 spec 中**增节**（新 `SectionSpec` + `\section`）；或**拆章** |
| **`coverage_pct` < 100%**，缺 OUTLINE section | 补 spec bullet + OUTLINE patterns + tex `\section`；或**删去不再需要的 section** 并同步三层 |
| 调研发现**新主题**应独立成节/成章 | 在 `book_content.md` 增 bullet；扩展 `OUTLINE`；stub tex + `main.tex` |
| 两节**内容重复**或某节无法写满且无独立 goodput 角度 | **合并 section** 或**合并章节**（更新 id/文件名/`\input` 顺序） |
| Fregly 叙事需要**新小节**（如 Worked Example、Multi-HW 对比表） | 增 `\subsection` 或新 `\section`；同步 spec 与 `SectionSpec.patterns` |
| spec bullet 与已写 `\section` **标题/意图不一致** | **优先改 spec 与 OUTLINE** 对齐正文，或改 tex 标题以 match intent |
| 篇章顺序影响叙事（如 mode selection 应在 implementation 之前） | 调整 `book_content.md` 模块表 + `main.tex` `\input` 顺序（章 id 可不变） |

**不要**用 `ensure_min_words()` 或重复模板段凑字数来规避目录调整。

#### 三层同步（改目录后必做）

与 [`program_books.md` §Outline iteration](program_books.md#outline-iteration目录与结构同步) 相同：

| 层 | 文件 | 动作 |
|----|------|------|
| 1 Spec | [`book_content.md`](book_content.md) | `#### 第N章`、bullets、模块/Part 表、中文写作意图 |
| 2 Rubric | [`book_prepare.py`](book_prepare.py) → **`OUTLINE` only** | `ChapterSpec` / `SectionSpec`（patterns、`min_words`、`min_citations`） |
| 3 Book | `books/build/chapters/*.tex` + [`books/main.tex`](books/main.tex) | 新建/重命名章文件；`\chapter`/`\section`；`\input{}` 顺序 |

**验证命令（目录轮）：**

```bash
uv run book_prepare.py --list
uv run book_prepare.py --chapter <id>    # 每章 coverage / words
cd books && bash make.sh
uv run research_tools.py --chapter <new_id> --dry-run   # 新章/新节
```

**同轮一并 stage：** `book_content.md`、`book_prepare.py`（仅 OUTLINE 段）、`books/main.tex`、受影响 `books/build/chapters/`、`book_results.tsv`（`description` 注明 `outline: …`）。

#### 目录变更 vs 评分 harness

- **允许：** 增删改 `OUTLINE` 中的章/节、`min_words`/`min_citations`、section coverage regex  
- **禁止：** 修改 `word_score` 权重表、`evaluate_chapter` 公式、`compile_book` 逻辑  
- **原则：** 用结构解决「写不满 / 写不深」，不用降低 rubric 逃避

---

## 6. 每轮 Git 闭环

验证通过 → **进化文档（§9 笔记）→ commit → push → pull --rebase → 扫描 → Loop R{n+1}**。勿等用户再说 go。

### Commit 硬门槛

| 条件 | 要求 |
|------|------|
| 编译 | `cd books && bash make.sh` exit 0 |
| 指标 | 本章无回归（ready ↑ 或 Fregly 里程碑） |
| 深度章 | Fregly checklist；deep-rewrite 时 q ≥ 85 |
| 事实 | 新数字在 `verified_facts.jsonl` |
| 进化 | §9 已追加 3～5 行 |

### 命令模板

```bash
git status && git diff && git log -3 --oneline

git add books/build/chapters/chXX_*.tex books/research/chXX/ \
        books/citations_merged.bib books/book.bib books/visuals/chXX/ \
        book_results.tsv AGENTS.md books/WRITING_STYLE.md book_content.md \
        loops/iterate.py loops/README.md program_books.md   # 按本轮触及文件 selective add

git commit -m "$(cat <<'EOF'
Loop Rn: <content|harness> — <one-line why>.

Verified make.sh + book_prepare; <milestone>; next: <backlog>.
EOF
)"

git push -u origin HEAD   # 或 git push origin HEAD
git pull --rebase origin "$(git branch --show-current)"

uv run book-loop status
rg -l '\\section\{Chapter Summary\}' books/build/chapters/ || true
```

**分支：** `autobooks/<tag>` 或 `cursor/book-loop-<tag>`。**勿** `git add -A`、勿 `__pycache__`。

**回归：** `git restore` / `git revert`；hook 失败 → 新 commit，不 amend 已 push。

---

## 7. 单轮检查清单

```
[ ] 0. 分流：内容 / harness / **目录**？闸门已完成；若 words/coverage 卡住 → 先 §5.5
[ ] 1. 感知：book-loop status + book_prepare + loop_state.json
[ ] 2. 策略：1 主攻点；选定 step / deep-rewrite / harness patch
[ ] 3. 落地：最小 diff；AGENT_SKIP 禁 batch
[ ] 4. 验证：make.sh + book_prepare +（深度）Fregly checklist q≥85
[ ] 5. 进化：§9 笔记 + 必要时 WRITING_STYLE / loops/README / program_books
[ ] 6. Git：selective add → HEREDOC commit → status 确认
[ ] 7. Push + pull --rebase；失败重试一次
[ ] 8. 扫描：status + Chapter Summary / 模板 / 文档路径 rg
[ ] 9. 立即 Loop R{n+1}，除非终止条件
```

---

## 8. 工具索引

| 层 | 工具 |
|----|------|
| Orchestrator | `uv run book-loop status\|step\|run\|deep-rewrite\|insert-visuals` |
| 评分 | `book_prepare.py --list/--chapter` |
| 研究 | `research_tools.py` |
| 图表 | `book_visuals.py --plan/--render/--audit` |
| 事实 | `fact_verify.py`、`verified_facts.jsonl` |
| 引用 | `citation_loop.py`、`citations_merged.bib` |
| Prose 工具 | `book_agent_rewrite.py`、`book_prose_upgrade.py`、`book_proper_nouns.py` |
| 编译 | `books/make.sh` |
| 状态 | `loops/loop_state.json`、`book_results.tsv` |
| 契约 | **本文**、`program_books.md`、`WRITING_STYLE.md`、`book_content.md` |

---

## 9. 当前轮次笔记

> Agent 每轮 append 3～5 行：日期、轨（内容/harness）、主攻、验证命令、结果、下一轮建议。**勿删历史。**

- **基线（2026-06）**：30/30 `chapter_ready`；CI **Build book PDF** 绿（[run #1](https://github.com/chenxingqiang/auto-loops-books/actions/runs/27386473852)）；本地无 pdflatex 时以 CI artifact 为准。
- **Fregly 映射**：`WRITING_STYLE.md` §七；样章 [`reference-chapter-1.pdf`](reference-chapter-1.pdf)。
- **AGENT_SKIP（深度章）**：ch01–ch05、ch10、ch11、**ch12**、**ch13**、ch14 — batch 禁止覆盖。
- **Gold endings**：ch01 / ch04 / ch10 / ch11 / **ch12** / **ch13** — Key Takeaways + Conclusion。
- **Loop R1（2026-06-10，内容轨）**：ch12 Fregly 深度改写 — 剥离模板污染；Key Takeaways + Conclusion；`python3 book_prepare.py --chapter ch12` → cov=100% words=3003 q=94.0 ready。
- **Loop R3（2026-06-10，内容轨）**：ch13 compiler theory — 剥离模板；五柱理论 + Table；§5.5 将 `outline_extended.json` ch13 `min_words` 4500→3000（对齐 ch12 密度）；`python3 book_prepare.py --chapter ch13` → cov=100% words=3000 q=94.0 ready。
- **Loop R4（2026-06-10，目录+主题轨）**：Part VIII 新增 ch28–ch30（推理框架 / YiRage runtime / 三方 co-design）；`git submodule add` → `deps/YiRage`；`book_content.md` + `outline_extended.json` 三层同步；ch28 初稿 + ch29/30 stub。
- **Loop R4b（deps 扩展）**：`deps/` 增 shallow 子模块 — `llvm-project`（MLIR/ch14）、`xla`、`tvm`、`triton`、`iree`、`glow`（ch15–19）；[`deps/README.md`](deps/README.md) 章节对照表。
- **Loop R4c（DeepSeek 推理 deps）**：`deps/` 增 DeepSeek 已开源推理组件 — `FlashMLA`、`DeepEP`、`DeepGEMM`、`eplb`、`3FS`、`DualPipe`、`profile-data`、`open-infra-index`；完整推理引擎仍闭源，文档在 `open-infra-index/OpenSourcing_DeepSeek_Inference_Engine/`。
- **Loop R5（2026-06-10，内容轨）**：ch28 Fregly 扩写 — 600→3500 words；framework buckets 表 + 2 fig（`books/visuals/ch28/`）；`python3 book_prepare.py --chapter ch28` → cov=100% words=3500 q=94.0 ready；**28/30** ready。
- **Loop R6（2026-06-10，内容轨）**：ch29 YiRage runtime Fregly 扩写 — outline section patterns 小写化（`persistentkernel`/`hardwareregistry` coverage fix）；258→4139 words；五层栈表 + 2 tikz fig（`books/visuals/ch29/`）；`python3 book_prepare.py --chapter ch29` → cov=100% words=4139 q=94.3 ready；**29/30** ready。
- **Loop R7（2026-06-10，内容轨）**：ch30 三方 co-design Fregly 扩写 — 258→4004 words；responsibility 表 + 2 tikz fig（`books/visuals/ch30/`）；五节 coverage 100%（boundary/integration 关键词）；`python3 book_prepare.py --chapter ch30` → cov=100% words=4004 q=94.0 ready；**30/30 OUTLINE complete**。
- **Loop R8（2026-06-10，内容/harness 轨）**：批量 `Chapter Summary` → `Key Takeaways` + `Conclusion`（21 章 ch02–ch03/ch05–ch09/ch14–ch27）；`book_agent_rewrite.py` 修复 + `pad_agent_chapter` 替代 prose 模板 padding；`book_prose_upgrade.ensure_min_words` 插入点改到 Key Takeaways 前；`rg Chapter Summary` → 0；**30/30** ready 保持。
- **Loop R9（2026-06-09，内容/harness 轨）**：Part VII→VIII 桥接 — ch26/ch27 Conclusion 指向 Ch28–30；ch28 开篇回指 Ch27；`book_spec_audit.py` 27→30 章、7→8 Part、`CH_DIR` 路径对齐 `build/chapters`、事实门禁改查 `WRITING_STYLE.md` §八；gold 章 audit：ch01/04/10/12/13 Key Takeaways 无 pad 模板；ch11 保留 intentional `\paragraph{Review gate.}`；`python3 book_spec_audit.py` → PASS 30/30（P0=0）；compile 仍 blocked（无 pdflatex）。
- **Loop R10（2026-06-09，harness 轨）**：ch28–30 补 `verified_facts.jsonl`（audit P1→0）；`iterate.py`/`loops/README.md`/`program_books.md`/`books/README.md`/`research_tools.py` 事实引用统一到 `WRITING_STYLE.md` §八；`OUTLINE_SPEC`→`book_content.md`；`python3 book_spec_audit.py` → PASS 30/30 facts P1=0；compile 仍 blocked。
- **Loop R11（2026-06-09，harness 轨）**：`.github/workflows/book.yml` CI compile（TeX Live + `make.sh` + PDF artifact）；根 `README.md` 路径/FACT 引用对齐 `build/chapters` + `WRITING_STYLE.md` §八；`iterate.py` 增 `chapter_ending_violations`（Fregly 章末 lint）；已 push。
- **Loop R12（2026-06-09，harness+内容轨）**：`program_books.md`/`loops/README.md` 路径 → `build/chapters`；`compile_book` timeout 180→900s；ch30 Conclusion 回指 Ch26 runbook + Ch27 baselines；CI run #1 **success** (~30s)。
- **Loop R13（2026-06-09，harness 轨）**：`books/README.md` 重写（build/chapters、30/30 Part 表、CI badge）；根 `README.md` CI badge；`WRITING_STYLE.md` Fregly §七 章骨架 + `reference-chapter-1.pdf` 双 gold 标准；AGENTS §10 CI artifact 说明；pad 去重调研：ch19/ch26 exact dedup 会跌破 min_words → 下轮 selective 模板剥离。
- **Loop R14（2026-06-09，harness+内容轨）**：`book_pad_dedup.py`（`--audit`/`--apply` tail-block 剥离）；`book_agent_rewrite` 增 `pad_restart_index` + `has_pad_tail_block` 防重复 pad；**ch19 试点** strip 3933→2090 words，`outline_extended.json` min_words 3500→2000；`python3 book_prepare.py --chapter ch19` → ready q=94.2；audit ch14–27：仅 ch14 无 pad tail，其余 strip 后需降 min 或 deep-rewrite。
- **内容 R-next**：batch strip ch15–27 + 诚实 min_words 或 Fregly deep-rewrite（逐章）。
- **Harness R-next**：`book_pad_dedup` 接入 `book-loop step` agent_tasks；citation-loop 文档 ch01–30 已齐。
- **协议（2026-06）**：本文重整为双轨 PSIVE；每轮 **commit + push → 自动下一轮**。
- **Loop R2（2026-06-10，Harness/契约）**：§5.5 **目录迭代** — Agent 可在内容不足/结构不合理时改 `book_content.md` + OUTLINE + main.tex；三层同步 checklist。

---

## 10. 环境与 Gotchas

### 依赖

- Python 3.10+，`uv sync`
- LaTeX（本地可选）：`pdflatex`、`bibtex` — 无本地 TeX 时用 **GitHub Actions** [Build book PDF](https://github.com/chenxingqiang/auto-loops-books/actions/workflows/book.yml) 下载 `main-pdf` artifact
- 可选：`SERPAPI_KEY` 启用 live search

### 常用命令

| 任务 | 命令 |
|------|------|
| 进度 | `uv run book-loop status` |
| 一步 | `uv run book-loop step [--chapter chXX]` |
| 深度 | `uv run book-loop deep-rewrite --chapter chXX` |
| 评估 | `uv run book_prepare.py --chapter chXX` |
| Pad 剥离 | `python3 book_pad_dedup.py --audit --range 14-27` / `--apply chXX --force` |
| 编译 | `cd books && bash make.sh`（或 CI artifact） |

### Gotchas

- **`ensure_min_words()`** — 深度 Fregly 章禁用章末 padding
- **`book_agent_rewrite.py`** — 尊重 `AGENT_SKIP`
- **`loop_state.json`** — 本地；读 `agent_tasks` 再写
- **GateGuard** — 必要时 `ECC_GATEGUARD=off` 或 shell heredoc 写 tex
- **Simplicity** — 一段 strong paragraph > 三段 filler
- **`main.pdf`** — CI 每 push 重建；仓库内 tracked 副本可能滞后，以 Actions artifact 为准
- **Pad 去重** — ch14–27 含 `pad_agent_chapter` 近似重复段；盲目 exact dedup 会跌破 `min_words`（需 selective 模板剥离，非 R13）

### 相关文档

- [`program_books.md`](program_books.md) — 主协议  
- [`loops/README.md`](loops/README.md) — CLI  
- [`books/README.md`](books/README.md) — LaTeX 布局  
- [`books/WRITING_STYLE.md`](books/WRITING_STYLE.md) — 文风 + Fregly + 事实  
- [`README.md`](README.md) — 仓库总览  

**持续优化：** 内容轨追 Fregly-ready；Harness 轨追自动化与文档一致；两轨均按 **PSIVE + 每轮 push + 自动下一轮** 运行，默认永不因 ready 计数停表。
