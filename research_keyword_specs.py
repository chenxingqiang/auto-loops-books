#!/usr/bin/env python3
"""
Per-chapter literature search keyword specs for research_tools.py.

Edit books/research/keyword_specs.json to customize Scholar queries and
keyword weights per chapter. Run:

    python3 research_keyword_specs.py --validate
    python3 research_keyword_specs.py --generate   # refresh baseline from OUTLINE
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from book_prepare import OUTLINE, ChapterSpec

ROOT = Path(__file__).resolve().parent
SPECS_PATH = ROOT / "books" / "research" / "keyword_specs.json"

# Curated Scholar queries (latest literature) — merged with auto queries at runtime.
CHAPTER_QUERY_SEEDS: dict[str, list[str]] = {
    "ch01": [
        "TaxBreak kernel launch overhead LLM decode 2024 2025",
        "Memory-Floor LLM inference bandwidth batch-1",
        "vLLM PagedAttention continuous batching decode latency",
        "Flash-Decoding long context batch-1 attention",
        "LLM prefill decode disaggregated serving",
        "kernel fusion megakernel decoder LLM",
        "CUDA graphs LLM inference decode",
        "MoE decode kernel launch storm",
    ],
    "ch02": [
        "dataflow-driven kernel optimization deep learning",
        "operator fusion vs data residency on-chip",
        "static dataflow accelerator inference",
        "megakernel fused decoder transformer",
        "compiler automated kernel fusion LLM",
        "XDNA AIE dataflow graph inference",
    ],
    "ch03": [
        "AI accelerator memory hierarchy roofline 2024",
        "GPU CPU NPU inference compiler constraints",
        "hardware-aware tiling layout parallel scheduling",
        "edge NPU static scheduling inference",
        "cross-platform ML compiler benchmark methodology",
    ],
    "ch04": [
        "Hopper TMA tensor memory accelerator decode",
        "Blackwell GPU memory hierarchy inference",
        "thread block cluster distributed shared memory",
        "tensor core utilization batch-1 decode",
        "PTX softmax exp2 inference kernel",
    ],
    "ch05": [
        "AMD XDNA Ryzen AI inference dataflow",
        "AIE tile DMA pipeline static graph",
        "edge NPU LLM decode optimization",
        "CUDA XDNA primitive mapping compiler",
    ],
    "ch06": [
        "on-chip memory residency fused kernel",
        "shared memory budgeting transformer decode",
        "NUMA cache-aware LLM inference layout",
        "bufferization memory reuse compiler pass",
    ],
    "ch07": [
        "static warp assignment GPU kernel",
        "schedule-free persistent kernel inference",
        "heterogeneous core tiling compiler",
    ],
    "ch08": [
        "TMA double buffering MMA overlap Hopper",
        "async copy pipeline GPU inference",
        "compiler pipeline stage hazard check",
    ],
    "ch09": [
        "warp shuffle vs block sync softmax",
        "GPU synchronization cost model inference",
        "cross-hardware barrier optimization",
    ],
    "ch10": [
        "online softmax numerics attention decode",
        "FlashAttention IO-aware attention 2024",
        "paged KV cache softmax residency",
    ],
    "ch11": [
        "fused decoder megakernel transformer",
        "QKV attention MLP single kernel",
        "PagedAttention gather fused kernel",
    ],
    "ch12": [
        "CUDA graphs LLM decode capture",
        "persistent kernel vs eager launch inference",
        "graph bucket memory pool context length",
    ],
    "ch13": [
        "AI compiler tiling fusion layout theory",
        "roofline-guided compiler pass ordering",
        "decode fusion granularity GPU CPU NPU",
    ],
    "ch14": [
        "MLIR bufferization dialect lowering inference",
        "MLIR GPU CPU codegen optimization 2024",
        "multi-level IR deep learning compiler",
    ],
    "ch15": [
        "XLA GPU fusion limits inference",
        "XLA cross-hardware graph compiler benchmark",
    ],
    "ch16": [
        "TVM AutoTVM Ansor schedule search",
        "TVM hardware-aware autotuning inference",
    ],
    "ch17": [
        "OpenAI Triton autotune register pressure",
        "Triton HIP AMD inference kernel",
    ],
    "ch18": [
        "IREE MLIR runtime deployment inference",
        "IREE GPU CPU edge codegen",
    ],
    "ch19": [
        "Glow compiler graph optimization inference",
        "Glow backend quantization fusion",
    ],
    "ch20": [
        "Mirage LLM compiler fusion",
        "Mirage multi-GPU inference kernel",
    ],
    "ch21": [
        "multi-backend compiler benchmark same model",
        "cross-hardware LLM inference triplet benchmark",
    ],
    "ch22": [
        "LLM inference profiling Nsight decode",
        "framework queue vs kernel bottleneck inference",
    ],
    "ch23": [
        "MoE inference routing scheduling GPU",
        "mixture of experts decode latency",
        "heterogeneous MoE deployment",
    ],
    "ch24": [
        "disaggregated prefill decode serving",
        "KV cache transfer network inference",
        "DeepEP expert parallel communication",
    ],
    "ch25": [
        "reinforcement learning compiler autotuning",
        "hardware-aware search space LLM kernel",
    ],
    "ch26": [
        "LLM inference packaging deployment ops",
        "production inference scheduling pitfalls",
    ],
    "ch27": [
        "edge cloud LLM inference co-design",
        "autonomous compiler optimization inference",
    ],
    "ch28": [
        "vLLM continuous batching scheduler 2024 2025",
        "inference framework paging plugin architecture",
        "LLM serving framework decode throughput",
    ],
    "ch29": [
        "YiRage LLM compiler runtime",
        "persistent kernel runtime inference compiler",
    ],
    "ch30": [
        "framework compiler runtime co-design inference",
        "end-to-end LLM serving stack optimization",
    ],
}

# High-signal keyword seeds (weight 15–18) — supplement auto-extracted terms.
CHAPTER_KEYWORD_SEEDS: dict[str, list[tuple[str, int]]] = {
    "ch01": [
        ("TaxBreak HDBI kernel launch", 17),
        ("Memory-Floor R_floor bandwidth", 17),
        ("prefill decode disaggregation", 16),
        ("PagedAttention vLLM", 15),
        ("Flash-Decoding attention kernel", 15),
        ("megakernel whole-decoder fusion", 14),
    ],
    "ch02": [
        ("dataflow-driven optimization", 17),
        ("data residency on-chip", 16),
        ("operator-driven kernel design", 15),
        ("static pipeline dataflow", 14),
    ],
    "ch03": [
        ("hardware constraint matrix", 16),
        ("memory hierarchy roofline", 15),
        ("warp SIMD NUMA static NPU", 14),
    ],
    "ch04": [
        ("Hopper TMA tensor memory", 17),
        ("thread block cluster DSM", 15),
        ("tensor core batch-1 decode", 15),
    ],
    "ch05": [
        ("XDNA AIE dataflow", 17),
        ("ADF static graph DMA", 15),
        ("Ryzen AI edge inference", 14),
    ],
    "ch28": [
        ("continuous batching scheduler", 17),
        ("PagedAttention serving framework", 16),
        ("inference framework plugin", 14),
    ],
    "ch29": [
        ("YiRage compiler runtime", 17),
        ("persistent kernel capture", 15),
    ],
    "ch30": [
        ("framework compiler co-design", 17),
        ("runtime compiler boundary inference", 15),
    ],
}


def _keywords_from_spec(spec: ChapterSpec) -> list[dict[str, int | str]]:
    items: list[tuple[str, int]] = []
    items.append((spec.title, 18))
    for section in spec.sections:
        label = section.label.replace("_", " ")
        items.append((label, 14))
        for pat in section.patterns[:2]:
            term = re.sub(r"[\\^$()\[\]|.?]", " ", pat)
            term = re.sub(r"\s+", " ", term).strip()
            if len(term) >= 3:
                items.append((term, 12))
    for term, weight in CHAPTER_KEYWORD_SEEDS.get(spec.chapter_id, []):
        items.append((term, weight))
    seen: dict[str, int] = {}
    for term, weight in items:
        key = term.lower().strip()
        if len(key) < 3:
            continue
        seen[key] = max(seen.get(key, 0), weight)
    return [{"term": t, "weight": w} for t, w in sorted(seen.items(), key=lambda x: (-x[1], x[0]))[:24]]


def _queries_from_spec(spec: ChapterSpec) -> list[str]:
    queries: list[str] = list(CHAPTER_QUERY_SEEDS.get(spec.chapter_id, []))
    if not queries:
        queries.append(f'"{spec.title}" LLM inference 2024 2025')
        for section in spec.sections[:4]:
            label = section.label.replace("_", " ")
            queries.append(f'"{label}" LLM compiler optimization')
    queries.append(f'"{spec.title}"')
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        qn = q.strip().lower()
        if qn and qn not in seen:
            seen.add(qn)
            out.append(q.strip())
    return out


def build_specs_document() -> dict:
    chapters: dict[str, dict] = {}
    order = [s.chapter_id for s in OUTLINE]
    for spec in OUTLINE:
        inherit = spec.chapter_id != order[0]
        chapters[spec.chapter_id] = {
            "title": spec.title,
            "keywords": _keywords_from_spec(spec),
            "queries": _queries_from_spec(spec),
            "year_lo": 2019 if spec.chapter_id in ("ch01", "ch02", "ch03") else 2020,
            "inherit_prior_chapters": inherit,
            "reuse_min_score": 12,
            "max_inherited_papers": 25,
        }
    return {
        "version": 1,
        "description": "Per-chapter Scholar keywords/queries. Edit queries for latest literature; prior-chapter papers are reused when inherit_prior_chapters is true.",
        "defaults": {
            "year_lo": 2019,
            "year_hi": None,
            "inherit_prior_chapters": True,
            "reuse_min_score": 12,
            "max_inherited_papers": 25,
            "max_pages_per_query": None,
            "query_delay_s": 2.0,
        },
        "chapters": chapters,
    }


def load_specs(path: Path = SPECS_PATH) -> dict:
    if not path.exists():
        return build_specs_document()
    return json.loads(path.read_text(encoding="utf-8"))


def chapter_spec_entry(chapter_id: str, doc: dict | None = None) -> dict:
    doc = doc or load_specs()
    defaults = doc.get("defaults", {})
    entry = doc.get("chapters", {}).get(chapter_id, {})
    merged = {**defaults, **entry}
    return merged


def validate_specs(path: Path = SPECS_PATH) -> list[str]:
    doc = load_specs(path)
    issues: list[str] = []
    outline_ids = {s.chapter_id for s in OUTLINE}
    spec_ids = set(doc.get("chapters", {}).keys())
    missing = outline_ids - spec_ids
    extra = spec_ids - outline_ids
    if missing:
        issues.append(f"missing chapter entries: {sorted(missing)}")
    if extra:
        issues.append(f"unknown chapter ids: {sorted(extra)}")
    for cid in sorted(outline_ids & spec_ids):
        entry = doc["chapters"][cid]
        if not entry.get("keywords"):
            issues.append(f"{cid}: empty keywords")
        if not entry.get("queries"):
            issues.append(f"{cid}: empty queries")
    return issues


def write_specs(path: Path = SPECS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_specs_document(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage per-chapter research keyword specs")
    parser.add_argument("--generate", action="store_true", help="Write keyword_specs.json from OUTLINE")
    parser.add_argument("--validate", action="store_true", help="Validate keyword_specs.json")
    args = parser.parse_args()
    if args.generate:
        path = write_specs()
        print(f"Wrote {path} ({len(OUTLINE)} chapters)")
        return 0
    if args.validate:
        issues = validate_specs()
        if issues:
            for i in issues:
                print(f"  WARN: {i}")
            return 1
        print(f"OK: {SPECS_PATH} covers {len(OUTLINE)} chapters")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
