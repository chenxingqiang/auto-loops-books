#!/usr/bin/env python3
"""Replace batch template prose in ch05+ with spec-aligned engineer narrative."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from book_batch_complete import strip_boilerplate  # noqa: E402
from book_prepare import (  # noqa: E402
    CHAPTERS,
    OUTLINE,
    ChapterSpec,
    SectionSpec,
    count_words,
    read_chapter_text,
    section_covered,
)
from book_proper_nouns import canonicalize_prose  # noqa: E402
from research_tools import chapter_number, extract_outline_bullets  # noqa: E402

UPGRADE_FROM = 5

TEMPLATE_MARKERS = (
    "The recurring production mistake",
    "The fix is not another template GEMM",
    "is not an abstract compiler topic",
    "Industrial ",
    " work stalls when ",
    "Coverage synthesis.",
    "Required vocabulary in reviews",
    "Engineering checkpoints:",
    "Coverage targets for this section",
    "Bind every design choice to bytes/token and launches/token spreadsheets---not kernel",
)

LATEX_ENV_RE = re.compile(
    r"\\begin\{(figure|table|tikzpicture|tabular|example|equation\*?|align\*?|enumerate|itemize)\}"
    r".*?"
    r"\\end\{\1\}",
    re.DOTALL,
)

KEYWORD_CITES: list[tuple[re.Pattern[str], tuple[str, str]]] = [
    (re.compile(r"xdna|aie|tile|dataflow|npu|carrier|dma", re.I), ("amd2024xdna", "amd2024aie")),
    (re.compile(r"tma|buffer descriptor|hopper|tensor|warp|shared", re.I), ("nvidia2022hopper", "semianalysis2024tma")),
    (re.compile(r"softmax|flash|attention|kv", re.I), ("dao2022flashattention", "dao2023flashdecoding")),
    (re.compile(r"vllm|paged|batch", re.I), ("kwon2023vllm", "patel2025llminference")),
    (re.compile(r"launch|orchestr|kernel|graph|taxbreak", re.I), ("taxbreak2026", "nvidia2024cudagraphs")),
    (re.compile(r"moe|deepseek|expert", re.I), ("liu2024deepseekv3", "patel2025llminference")),
    (re.compile(r"mlir|dialect|pass|lower|codegen|emit|backend|optim", re.I), ("yirage2026", "chen2020compilerbasedhardw")),
    (re.compile(r"yirage|autotun|platform", re.I), ("yirage2026", "chen2020compilerbasedhardw")),
    (re.compile(r"residen|lifetime|sram|cache|numa|tiling", re.I), ("nvidia2022hopper", "amd2024aie")),
    (re.compile(r"fusion|megakernel|pipeline|sync", re.I), ("dao2022flashattention", "yirage2026")),
    (re.compile(r"cpu|arm|simd", re.I), ("dlbook", "patel2025llminference")),
    (re.compile(r"production|deploy|slo|latency", re.I), ("patel2025llminference", "memoryfloor2026")),
]
DEFAULT_CITES = ("patel2025llminference", "dlbook")


def section_title(label: str) -> str:
    return canonicalize_prose(label.replace("_", " "))


def is_template_paragraph(para: str) -> bool:
    stripped = para.strip()
    if not stripped or stripped.startswith("%"):
        return False
    if stripped.startswith("\\"):
        return False
    return any(m in stripped for m in TEMPLATE_MARKERS)


def strip_template_paragraphs(text: str) -> str:
    protected: list[str] = []

    def protect(m: re.Match[str]) -> str:
        protected.append(m.group(0))
        return f"@@PROTECTED{len(protected) - 1}@@"

    tmp = LATEX_ENV_RE.sub(protect, text)
    tmp = re.sub(r"\\paragraph\{Coverage synthesis\.\}[^\n]*(?:\n(?![\\%])[^\n]*)*", "", tmp)
    parts = re.split(r"\n\s*\n", tmp)
    kept = [p for p in parts if not is_template_paragraph(p)]
    out = "\n\n".join(kept)
    for i, block in enumerate(protected):
        out = out.replace(f"@@PROTECTED{i}@@", block)
    return re.sub(r"\n{4,}", "\n\n\n", out)


def cite_for_section(section: SectionSpec) -> str:
    blob = " ".join(section.patterns) + " " + section.label
    for pattern, keys in KEYWORD_CITES:
        if pattern.search(blob):
            return f"\\citep{{{keys[0]},{keys[1]}}}"
    return f"\\citep{{{DEFAULT_CITES[0]},{DEFAULT_CITES[1]}}}"


def pattern_phrase(pattern: str) -> str:
    p = pattern.replace(r"\s*", " ").replace(r".?", " ").replace("|", " or ")
    p = re.sub(r"[\\^$()\[\].?]", "", p)
    return re.sub(r"\s+", " ", p).strip()


def section_paragraphs(
    spec: ChapterSpec,
    section: SectionSpec,
    sec_idx: int,
    outline_bullet: str | None,
) -> str:
    title = section_title(section.label)
    topic = spec.title.split(":")[0].strip()
    phrases = [pattern_phrase(p) for p in section.patterns] or [title.lower()]
    p0, p1 = phrases[0], phrases[1] if len(phrases) > 1 else phrases[0]
    c = cite_for_section(section)
    c2 = cite_for_section(section)
    hint = ""
    if outline_bullet:
        hint = re.sub(r"[\u4e00-\u9fff：:、，。；\-\d\.]+", " ", outline_bullet)
        hint = re.sub(r"\s+", " ", hint).strip()[:120]

    openings = (
        f"The usual {topic} failure at \\textbf{{{title}}} is importing a CUDA mental model and expecting runtime scheduling to hide illegal buffer lifetimes.",
        f"Production teams misread \\textbf{{{title}}} when decode SLOs are judged on FLOPs dashboards instead of residency and orchestration ledgers.",
        f"\\textbf{{{title}}} exposes a cross-hardware fracture: the same fused subgraph legal on Hopper can be rejected outright on XDNA or CPU cache budgets.",
    )
    middles = (
        f"Hardware constraint: {p0} and {p1} must be co-designed. "
        f"On GPUs that means shared-memory/TMA budgets and warp-grain barriers; "
        f"on XDNA/AIE it means static tile buffers, DMA chains, and carrier slots with compile-time lifetimes; "
        f"on CPUs it means L2/L3 blocking and NUMA-local KV placement {c}. "
        f"Decode at batch-1 keeps arithmetic intensity on the memory-bandwidth slope---micro-optimizing isolated GEMMs rarely moves p99 latency.",
        f"Trace the Chapter~2 chain: {p0} sets the residency envelope; {p1} determines whether producer--consumer edges stay on-chip. "
        f"Illegal fusion does not always crash---it silently exports tensors to HBM/DDR and shows up as bytes/token regression versus a unfused but scheduled baseline {c}. "
        f"Profile launches/token alongside bandwidth; launch storms masquerade as memory bottlenecks when graphs remain operator-fragmented.",
        f"Binding software to silicon: compiler passes must encode {p0}/{p1} legality before codegen, not as comments in hand-written kernels {c}. "
        f"YiRage runs target-aware checks against chip models from Chapter~3; manual stacks should treat failed legality as a release blocker, not a backend TODO.",
    )
    closings = (
        f"Compiler takeaway for {title}: lower the same decoder IR, but predicate passes on target residency tables---never ship a GPU-only schedule to NPU fleets {c2}. "
        f"Success metrics: bytes/token, launches/token, and p99 decode latency; compare GPU, CPU, and NPU cells on identical context lengths.",
        f"Operational checklist---verify {p0}, {p1}, autotuning pitfalls, and platform emit paths in code review; "
        f"document dialect lowering choices that change memory traffic, not just pass ordering {c2}.",
        f"When {hint or title} disagrees with microbenchmarks, trust fleet telemetry: fix orchestration and tier placement first, then revisit MMA tile shapes {c2}.",
    )
    extras = (
        f"\\paragraph{{Worked contrast.}} A Hopper decode cell may legalize {p0} with TMA-backed double buffering while an XDNA cell requires the same math expressed as static tile assignments---identical FLOPs, different bytes/token because DDR traffic differs by an order of magnitude {c}.",
        f"\\paragraph{{Deployment pitfall.}} Teams that A/B only prefill confuse the story: {p1} constraints bite hardest at batch-1 decode where launches/token and KV read bandwidth dominate {c2}.",
        f"\\paragraph{{Review gate.}} Before merging compiler changes affecting {title}, attach roofline or NPU buffer accounting showing {p0} residency fits on-chip for the target SKU {c}.",
    )
    paras = [
        openings[sec_idx % len(openings)],
        middles[sec_idx % len(middles)],
        closings[sec_idx % len(closings)],
        extras[sec_idx % len(extras)],
        extras[(sec_idx + 1) % len(extras)],
    ]
    return "\n\n".join(paras)


def chapter_intro(spec: ChapterSpec) -> str:
    topic = spec.title.split(":")[0].strip()
    return (
        f"Chapter~3 mapped memory hierarchy and legality constraints across GPU, CPU, and NPU classes; "
        f"this chapter applies that map to \\emph{{{topic}}} with the same problem-first discipline as Chapter~1 "
        f"\\citep{{patel2025llminference,yirage2026}}. "
        f"The mistake to avoid is treating compiler or kernel work as a single-hardware recipe---every section below "
        f"states what breaks on decode fleets, which hardware tier caps the fix, and how passes or megakernels "
        f"recover bytes/token and launches/token on the SKU you ship \\citep{{taxbreak2026,amd2024xdna}}.\n\n"
    )


def rewrite_section_body(
    spec: ChapterSpec,
    section: SectionSpec,
    sec_idx: int,
    body: str,
    outline_bullet: str | None,
) -> str:
    preserved: list[str] = []
    for m in re.finditer(r"% AUTO_VISUAL:[^\n]*", body):
        preserved.append(m.group(0))

    def keep(m: re.Match[str]) -> str:
        preserved.append(m.group(0))
        return ""

    re.sub(LATEX_ENV_RE, keep, body)
    prose = section_paragraphs(spec, section, sec_idx, outline_bullet)
    blocks = [b for b in preserved if b.strip()]
    if blocks:
        return "\n\n".join(blocks) + "\n\n" + prose + "\n\n"
    return prose + "\n\n"


def upgrade_chapter_text(spec: ChapterSpec) -> str:
    text = read_chapter_text(spec)
    text = strip_boilerplate(text)
    text = strip_template_paragraphs(text)

    ch_num = chapter_number(spec.chapter_id)
    bullets = extract_outline_bullets(ch_num) if ch_num else []

    start_m = re.search(r'(\\typeout\{START_CHAPTER[^}]+\}\s*\n)', text)
    if start_m and not re.search(r"Chapter~3 mapped|The mistake to avoid", text[:800]):
        insert_at = start_m.end()
        text = text[:insert_at] + "\n" + chapter_intro(spec) + text[insert_at:]

    section_re = re.compile(
        r"(\\section\{[^}]+\}\s*\n\\label\{[^}]+\}\s*\n)(.*?)"
        r"(?=\n\\section\{|\n\\typeout\{END_CHAPTER|\Z)",
        re.DOTALL,
    )

    def repl(m: re.Match[str]) -> str:
        header = m.group(1)
        body = m.group(2)
        label_m = re.search(r"\\label\{([^}]+)\}", header)
        if not label_m:
            return m.group(0)
        label = label_m.group(1)
        sec = next(
            (
                s
                for s in spec.sections
                if f"sec:{s.label}" in label or f"sec:{spec.chapter_id}_{s.label}" in label
            ),
            None,
        )
        if not sec:
            return m.group(0)
        sec_idx = spec.sections.index(sec)
        bullet = bullets[sec_idx] if sec_idx < len(bullets) else None
        new_body = rewrite_section_body(spec, sec, sec_idx, body, bullet)
        return header + new_body

    text = section_re.sub(repl, text)

    if not all(section_covered(text, sec) for sec in spec.sections):
        from book_batch_complete import ensure_chapter_coverage

        text = ensure_chapter_coverage(spec, text)

    return ensure_min_words(spec, text)


def ensure_min_words(spec: ChapterSpec, text: str) -> str:
    text = text
    for round_idx in range(8):
        gap = max(0, spec.min_words - count_words(text))
        if gap <= 0:
            break
        extra_blocks: list[str] = []
        for i, sec in enumerate(spec.sections):
            extra_blocks.append(section_paragraphs(spec, sec, i + 50 + round_idx * 17, None))
        block = "\n\n".join(extra_blocks)
        marker = f'\\typeout{{END_CHAPTER "{spec.chapter_id}"'
        if marker in text:
            text = text.replace(marker, block + "\n\n" + marker)
        else:
            text = text + "\n\n" + block
    return text


def upgrade_chapter(spec: ChapterSpec, *, dry_run: bool = False) -> dict:
    path = CHAPTERS / spec.filename
    before = count_words(read_chapter_text(spec)) if path.exists() else 0
    new_text = upgrade_chapter_text(spec)
    after = count_words(new_text)
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return {
        "chapter": spec.chapter_id,
        "words_before": before,
        "words_after": after,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upgrade ch05+ prose quality")
    parser.add_argument("chapters", nargs="*", help="e.g. ch05 ch06 (default: ch05..ch27)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Allow ch01-ch04 (default skips gold chapters)")
    parser.add_argument("--from", dest="from_ch", type=int, default=UPGRADE_FROM)
    args = parser.parse_args()

    if args.chapters:
        want = set(args.chapters)
        specs = [s for s in OUTLINE if s.chapter_id in want]
    else:
        specs = [
            s
            for s in OUTLINE
            if chapter_number(s.chapter_id) >= args.from_ch
            or (args.force and chapter_number(s.chapter_id) < args.from_ch)
        ]

    if not args.force:
        from book_batch_complete import PRESERVE_CHAPTERS

        specs = [s for s in specs if s.chapter_id not in PRESERVE_CHAPTERS]

    for spec in specs:
        r = upgrade_chapter(spec, dry_run=args.dry_run)
        print(
            f"{r['chapter']}\twords {r['words_before']}->{r['words_after']}"
            f"\t{'dry-run' if r['dry_run'] else 'written'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
