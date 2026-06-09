# Fact Verification Protocol — AI Compiler Performance Engineering

**Mandatory gate:** No numeric fact, vendor specification, or worked example enters `books/chapters/*.tex` until web-verified and logged.

**Loop enforcement:** `uv run book-loop step` → `agent_tasks` includes fact reminders + uncited-number lint. Log file: `books/research/<chapter_id>/verified_facts.jsonl`.

---

## 七、事实核验门禁（全书强制执行）

凡涉及**事实描述、数据举例、厂商参数、性能数字、部署配置**的内容，**必须先经 Web 检索反复交叉验证**，方可写入正文，并留存**可访问的可靠链接**。

- **禁止：** 凭模型记忆写数字、单一路径道听途说、无 URL 的「业界公认」、复制未读摘要的二次引用
- **必须：** 至少两轮独立检索 → -primary 来源核对 → 写入 `verified_facts.jsonl` → `\citep{}` + `book.bib` 含同款 URL

### English summary

Every measurement, SKU spec, or illustrative deployment detail must be **web-verified** (≥2 search passes) before landing in the manuscript. Store primary URLs in `verified_facts.jsonl` and mirror them in `book.bib`. Unverified content stays in `\vispending{}` / TBD tables only.

---

## Workflow (agent + human)

### 1. Classify the claim

| Type | Examples | Verification bar |
|------|----------|------------------|
| **Hard number** | ms/token, kernels/token, GB/s, %, speedup × | Tier A source required; log mandatory |
| **Vendor spec** | SRAM size, TMA, wavefront width | Official doc URL required |
| **Qualitative fact** | «vLLM uses PagedAttention» | Paper or docs URL + cite |
| **Book-internal methodology** | YiRage pass names, iron rules | No external log unless citing external inspiration |
| **Projection / placeholder** | Appendix B pending | Mark `\vispending{}`; **no log** until measured |

### 2. Search (repeat until stable)

Run **at least two independent query formulations**:

1. **Primary anchor** — paper title, arXiv id, or official product doc title
2. **Corroboration** — metric + model + hardware keywords, or second vendor/third-party harness

Accept the claim only when:

- The **same number or spec** appears in the primary source (abstract, table, or official spec page)
- No Tier-A contradiction; if sources disagree, **do not publish** until resolved or downgrade to qualitative wording

**Repeat search** after any draft edit that touches numbers—configs drift.

### 3. Log (`verified_facts.jsonl`)

One JSON object per line under `books/research/<chapter_id>/`:

```json
{
  "claim": "CUDA Graphs 1.259× speedup Qwen-2.5-7B H100 ctx2048 batch-1",
  "source_url": "https://arxiv.org/abs/2605.30571",
  "corroboration_url": "https://arxiv.org/abs/2605.30571",
  "bib_key": "memoryfloor2026",
  "verified_at": "2026-06-09",
  "queries": ["Memory-Bound batch-1 LLM decode CUDA Graphs H100", "arXiv 2605.30571 Qwen Graphs speedup"],
  "notes": "Table cell in paper; conditions in caption"
}
```

Fields:

| Field | Required | Purpose |
|-------|----------|---------|
| `claim` | yes | Exact statement as it appears in prose |
| `source_url` | yes | Tier A/B primary link |
| `corroboration_url` | recommended | Second independent URL |
| `bib_key` | yes | Matches `\citep{bib_key}` in `.tex` |
| `verified_at` | yes | ISO date |
| `queries` | yes | Search strings used (audit trail) |
| `notes` | optional | Config caveats, section/table pointer |

### 3b. Web content extraction (`fact_verify.py` + craw4ai)

After logging URLs, run content verification so claims are backed by **fetched page text**, not URL alone:

```bash
uv sync
uv run crawl4ai-setup          # once: installs browser for craw4ai
uv run fact-verify --chapter ch01
uv run book-loop step --chapter ch01 --skip-research
```

- **Input:** `verified_facts.jsonl` (`source_url`, `corroboration_url`, `claim`)
- **Cache:** `books/research/<chapter>/fact_sources/<hash>.json` with `content_excerpt`, `method`, `fetched_at` (ISO-8601 UTC)
- **Report:** `books/research/<chapter>/fact_verify_report.json` — `verified_ok`, `source_content_match`, missing tokens
- **Loop:** `book-loop step` runs fact verify after research; mismatches appear in `agent_tasks`

### 4. Bibliography

Every `bib_key` used for a verified fact must include a resolvable URL:

```bibtex
@article{memoryfloor2026,
  ...
  url = {https://arxiv.org/abs/2605.30571},
}
```

### 5. Manuscript

- Place `\citep{key}` in the **same paragraph** as the number (soft-lint enforces this).
- If verification fails: use `\vispending{reason}` or qualitative wording without numbers.

---

## Trusted source tiers

| Tier | Use | Examples |
|------|-----|----------|
| **A** | Primary for all hard numbers | arXiv/OpenReview, ACM/IEEE, NVIDIA/AMD official architecture pages |
| **B** | Corroboration or reproducible harness | GitHub benchmark repo with pinned config, vendor sample code |
| **C** | Discovery only | Forums, social posts — never sole evidence |

---

## Agent checklist (add to WRITING_STYLE)

Before git **keep**:

1. New numbers in diff? → matching line in `verified_facts.jsonl`?
2. Each log `source_url` still resolves (HTTP 200 or known arXiv redirect)?
3. `book.bib` URL matches log URL for that `bib_key`?
4. Uncited numeric paragraphs cleared (re-run `book-loop step`)?
5. Placeholders clearly marked, not mixed with verified tables?

---

## Related files

| File | Role |
|------|------|
| `program_books.md` | Autobooks protocol § Fact verification |
| `research_tools.py` | Literature discovery (feeds candidates, not a substitute for cross-check) |
| `loops/iterate.py` | `fact_verification_tasks()`, `uncited_numeric_paragraphs()` |
| `books/WRITING_STYLE.md` | Voice + checklist |
