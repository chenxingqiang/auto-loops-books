#!/usr/bin/env python3
"""Scan and fix canonical proper-noun capitalization in chapter LaTeX."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from book_prepare import CHAPTERS, OUTLINE, ChapterSpec, read_chapter_text  # noqa: E402

CANONICAL_TERMS: dict[str, str] = {
    "cuda": "CUDA",
    "pytorch": "PyTorch",
    "huggingface": "Hugging Face",
    "gpu": "GPU",
    "cpu": "CPU",
    "npu": "NPU",
    "llm": "LLM",
    "mlir": "MLIR",
    "tvm": "TVM",
    "xla": "XLA",
    "triton": "Triton",
    "iree": "IREE",
    "glow": "Glow",
    "vllm": "vLLM",
    "nvidia": "NVIDIA",
    "amd": "AMD",
    "hbm": "HBM",
    "tma": "TMA",
    "xdna": "XDNA",
    "aie": "AIE",
    "yirage": "YiRage",
    "mirage": "Mirage",
    "deepseek": "DeepSeek",
    "hopper": "Hopper",
    "blackwell": "Blackwell",
    "llama": "Llama",
    "qwen": "Qwen",
    "flashattention": "FlashAttention",
    "flashdecoding": "Flash-Decoding",
    "pagedattention": "PagedAttention",
    "megakernel": "MegaKernel",
    "rocm": "ROCm",
    "hip": "HIP",
    "gemm": "GEMM",
    "mma": "MMA",
    "ptx": "PTX",
    "sass": "SASS",
    "hw": "HW",
    "ai": "AI",
    "simd": "SIMD",
    "numa": "NUMA",
    "openai": "OpenAI",
    "transformers": "Transformers",
}

PHRASE_TERMS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bhugging\s+face\b", re.I), "Hugging Face"),
    (re.compile(r"\bflash\s+attention\b", re.I), "FlashAttention"),
    (re.compile(r"\bflash\s+decoding\b", re.I), "Flash-Decoding"),
    (re.compile(r"\bpaged\s+attention\b", re.I), "PagedAttention"),
    (re.compile(r"\bcuda\s+graphs?\b", re.I), "CUDA Graphs"),
    (re.compile(r"\bAi-([A-Za-z][A-Za-z0-9]*)"), r"AI-\1"),
    (re.compile(r"\b([A-Za-z]+)-Ai\b"), r"\1-AI"),
)

PROTECTED_PROPER_NAMES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bAi Nozaki\b"),
)

PROTECTED_RE = re.compile(
    r"(%[^\n]*"
    r"|\\(?:cite|citep|citet|label|ref|eqref|input|includegraphics)\{[^}]*\}"
    r"|\\(?:texttt|verb|url|href)\{[^}]*\}"
    r"|\\(?:texttt|verb)\|[^|]*\|"
    r"|\$\$.*?\$\$"
    r"|\$[^$]+\$)",
    re.DOTALL,
)


@dataclass(frozen=True)
class ProperNounHit:
    chapter_id: str
    line: int
    found: str
    expected: str
    context: str


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _context_line(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    return text[start:end].strip()[:160]


def scan_tex(tex: str, *, chapter_id: str = "") -> list[ProperNounHit]:
    hits: list[ProperNounHit] = []
    pos = 0
    for match in PROTECTED_RE.finditer(tex):
        hits.extend(_scan_segment(tex[pos : match.start()], tex, pos, chapter_id))
        pos = match.end()
    hits.extend(_scan_segment(tex[pos:], tex, pos, chapter_id))
    return hits


def _scan_segment(segment: str, full: str, offset: int, chapter_id: str) -> list[ProperNounHit]:
    hits: list[ProperNounHit] = []
    for phrase_pat, canonical in PHRASE_TERMS:
        for m in phrase_pat.finditer(segment):
            found = m.group(0)
            if found != canonical:
                idx = offset + m.start()
                hits.append(
                    ProperNounHit(
                        chapter_id=chapter_id,
                        line=_line_number(full, idx),
                        found=found,
                        expected=canonical,
                        context=_context_line(full, idx),
                    )
                )
    for key, canonical in CANONICAL_TERMS.items():
        pat = re.compile(rf"\b{re.escape(key)}\b", re.I)
        for m in pat.finditer(segment):
            found = m.group(0)
            if found != canonical:
                idx = offset + m.start()
                hits.append(
                    ProperNounHit(
                        chapter_id=chapter_id,
                        line=_line_number(full, idx),
                        found=found,
                        expected=canonical,
                        context=_context_line(full, idx),
                    )
                )
    return hits


def canonicalize_prose(text: str) -> str:
    shields: list[str] = []

    def _shield(match: re.Match[str]) -> str:
        shields.append(match.group(0))
        return f"\x00PN{len(shields) - 1}\x00"

    for pat in PROTECTED_PROPER_NAMES:
        text = pat.sub(_shield, text)

    for phrase_pat, canonical in PHRASE_TERMS:
        text = phrase_pat.sub(canonical, text)
    for key, canonical in sorted(CANONICAL_TERMS.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{re.escape(key)}\b", canonical, text, flags=re.I)
    for idx, original in enumerate(shields):
        text = text.replace(f"\x00PN{idx}\x00", original)
    return text


def fix_tex(tex: str) -> str:
    def fix_segment(segment: str) -> str:
        return canonicalize_prose(segment)

    out: list[str] = []
    pos = 0
    for match in PROTECTED_RE.finditer(tex):
        out.append(fix_segment(tex[pos : match.start()]))
        out.append(match.group(0))
        pos = match.end()
    out.append(fix_segment(tex[pos:]))
    return "".join(out)


def scan_chapter(spec: ChapterSpec) -> list[ProperNounHit]:
    tex = read_chapter_text(spec)
    if not tex.strip():
        return []
    return scan_tex(tex, chapter_id=spec.chapter_id)


def fix_chapter(spec: ChapterSpec) -> tuple[int, Path | None]:
    path = CHAPTERS / spec.filename
    if not path.exists():
        return 0, None
    original = path.read_text(encoding="utf-8")
    fixed = fix_tex(original)
    if fixed == original:
        return 0, path
    path.write_text(fixed, encoding="utf-8")
    before = len(scan_tex(original, chapter_id=spec.chapter_id))
    after = len(scan_tex(fixed, chapter_id=spec.chapter_id))
    return before - after, path


def proper_noun_tasks(spec: ChapterSpec, *, max_hits: int = 5) -> list[str]:
    hits = scan_chapter(spec)
    if not hits:
        return []
    tasks = [
        f"Proper noun: line {h.line} use `{h.expected}` not `{h.found}` — …{h.context[-80:]}"
        for h in hits[:max_hits]
    ]
    if len(hits) > max_hits:
        tasks.append(
            f"Proper noun: {len(hits) - max_hits} more capitalization issue(s) in {spec.chapter_id}"
        )
    return tasks


def chapter_report(spec: ChapterSpec) -> dict[str, object]:
    hits = scan_chapter(spec)
    return {
        "chapter_id": spec.chapter_id,
        "issue_count": len(hits),
        "sample": [
            {"line": h.line, "found": h.found, "expected": h.expected, "context": h.context}
            for h in hits[:8]
        ],
    }


def resolve_specs(chapter_id: str | None) -> tuple[ChapterSpec, ...]:
    if chapter_id:
        specs = tuple(s for s in OUTLINE if s.chapter_id == chapter_id)
        if not specs:
            print(f"Unknown chapter: {chapter_id}", file=sys.stderr)
            sys.exit(1)
        return specs
    return OUTLINE


RESEARCH = ROOT / "books" / "research"
RESEARCH_GLOBS = ("*.json", "*.jsonl", "*.bib")
BOOKS_BIB_PATHS = (
    ROOT / "books" / "citations_merged.bib",
    ROOT / "books" / "book.bib",
)


def iter_research_artifact_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in RESEARCH_GLOBS:
        paths.extend(sorted(RESEARCH.glob(f"**/{pattern}")))
    paths.extend(p for p in BOOKS_BIB_PATHS if p.exists())
    return paths


def fix_research_artifacts() -> int:
    """Apply canonicalize_prose to books/research and shared bib artifacts."""
    changed = 0
    for path in iter_research_artifact_paths():
        original = path.read_text(encoding="utf-8")
        fixed = canonicalize_prose(original)
        if fixed == original:
            continue
        path.write_text(fixed, encoding="utf-8")
        changed += 1
        print(f"research: fixed -> {path.relative_to(ROOT)}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Proper-noun capitalization lint for autobooks")
    parser.add_argument("--chapter", help="Chapter id, e.g. ch01")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--research", action="store_true", help="Fix books/research JSON/JSONL")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.chapter and not args.all and not args.research:
        parser.error("Specify --chapter <id>, --all, or --research")

    if args.research and args.fix:
        n = fix_research_artifacts()
        print(f"\nResearch files updated: {n}")

    if not args.chapter and not args.all:
        return 0

    reports: list[dict[str, object]] = []
    total_issues = 0
    code = 0

    for spec in resolve_specs(args.chapter if not args.all else None):
        if args.fix:
            delta, path = fix_chapter(spec)
            if path and delta:
                print(f"{spec.chapter_id}: fixed ~{delta} issue(s) -> {path.relative_to(ROOT)}")
            elif path:
                print(f"{spec.chapter_id}: ok")
            else:
                print(f"{spec.chapter_id}: missing {spec.filename}", file=sys.stderr)
                code = 1
        rep = chapter_report(spec)
        reports.append(rep)
        n = int(rep["issue_count"])
        total_issues += n
        if not args.fix and n:
            print(f"{spec.chapter_id}: {n} issue(s)")
            for row in rep["sample"]:
                print(f"  L{row['line']}: {row['found']!r} -> {row['expected']!r}")
            code = 1

    if args.json:
        print(json.dumps({"total_issues": total_issues, "chapters": reports}, indent=2, ensure_ascii=False))
    elif args.fix:
        print(f"\nTotal issues remaining: {total_issues} after fix pass")
    else:
        print(f"\nTotal issues: {total_issues} across {len(reports)} chapter(s)")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
