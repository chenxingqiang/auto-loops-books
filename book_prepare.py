"""
Fixed book preparation and evaluation harness for autobooks experiments.

Usage:
    uv run book_prepare.py                    # evaluate all chapters (full book compile)
    uv run book_prepare.py --chapter ch01     # evaluate one chapter (standalone ch01.pdf)
    uv run book_prepare.py --chapter ch01 --full-book  # evaluate ch01 metrics, compile main.pdf
    uv run book_prepare.py --list             # show outline

Do not change scoring logic during loops. The OUTLINE tuple may grow or change when 目录 iterates (see program_books.md).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOOKS = ROOT / "books"
PDF_DIR = BOOKS / "pdf"
BUILD_DIR = BOOKS / "build"
CHAPTER_INPUT_DIR = "build/chapters"
CHAPTER_COMPILE_TIMEOUT = 180
BOOK_COMPILE_TIMEOUT = 900
_build_chapters = BOOKS / "build" / "chapters"
_legacy_chapters = BOOKS / "chapters"
CHAPTERS = (
    _build_chapters
    if _build_chapters.is_dir()
    else _legacy_chapters
)


@dataclass(frozen=True)
class SectionSpec:
    label: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class ChapterSpec:
    chapter_id: str
    filename: str
    title: str
    min_words: int
    max_words: int
    min_citations: int
    sections: tuple[SectionSpec, ...]


OUTLINE: tuple[ChapterSpec, ...] = (
    ChapterSpec(
        chapter_id="ch01",
        filename="ch01_llm_decode_bottlenecks.tex",
        title="LLM Inference Performance Bottlenecks: From Symptoms to Root Causes",
        min_words=5000,
        max_words=8000,
        min_citations=8,
        sections=(
            SectionSpec("industrial_hook", (r"decode|bottleneck|goodput|deepseek", r"sla|industrial|opex")),
            SectionSpec("prefill_decode", (r"prefill", r"decode")),
            SectionSpec("decode_pain_points", (r"memory|launch|fragment", r"bandwidth|orchestr|pain")),
            SectionSpec("framework_issues", (r"pytorch|vllm|flash", r"framework|fusion|operator")),
            SectionSpec("goodput_metrics", (r"goodput|kernels/token|bytes/token", r"hdbi|r.?floor")),
            SectionSpec("diagnosis", (r"taxbreak|memory.?floor|diagnos", r"worksheet|step")),
            SectionSpec("multi_hardware", (r"gpu|cpu|npu", r"hardware|simd|adf")),
            SectionSpec("benchmark_gap", (r"benchmark|baseline|leaderboard", r"flash|vllm")),
            SectionSpec("yirage_preview", (r"yirage|megakernel|r[1-5]", r"compiler|fusion")),
            SectionSpec("book_roadmap", (r"roadmap|part [ivx]+", r"learning|read")),
        ),
    ),
    ChapterSpec(
        chapter_id="ch02",
        filename="ch02_dataflow_mindset.tex",
        title="Two Kernel Design Mindsets: Operator-Driven vs Dataflow-Driven",
        min_words=5000,
        max_words=7000,
        min_citations=6,
        sections=(
            SectionSpec("industrial_hook", (r"hook|quarter|kernel.*tun|delay",)),
            SectionSpec("two_mindsets", (r"operator|dataflow|mindset",)),
            SectionSpec("data_residency", (r"residen|iron.?rule|register|shared",)),
            SectionSpec("cross_hardware", (r"xdna|cuda|cpu|npu|hardware",)),
            SectionSpec("megakernel_automation", (r"megakernel|yirage|automat",)),
            SectionSpec("migration_playbook", (r"migrat|five.?step|playbook",)),
            SectionSpec("verification_method", (r"verif|export.?edge|benchmark",)),
        ),
    ),
    ChapterSpec(
        chapter_id="ch03",
        filename="ch03_hardware_constraints.tex",
        title="AI Hardware Architecture and Compiler Constraints",
        min_words=5000,
        max_words=9000,
        min_citations=10,
        sections=(
            SectionSpec("industrial_hook", (r"hook|spill|production|laboratory",)),
            SectionSpec("hardware_landscape", (r"nvidia|amd|x86|arm|npu",)),
            SectionSpec("constraint_matrix", (r"bandwidth|memory hierarchy|parallel",)),
            SectionSpec("gpu_constraints", (r"warp|shared memory|tensor core|TMA",)),
            SectionSpec("cpu_constraints", (r"cache|simd|numa",)),
            SectionSpec("npu_constraints", (r"static|npu|edge|tile",)),
            SectionSpec("hardware_aware_compile", (r"tiling|layout|pass",)),
            SectionSpec("benchmark_method", (r"benchmark|metric|methodology",)),
            SectionSpec("yirage_modeling", (r"yirage|chip.?arch|model",)),
        ),
    ),
)

_OUTLINE_CORE: tuple[ChapterSpec, ...] = OUTLINE


def _load_extended_outline() -> tuple[ChapterSpec, ...]:
    """Load ch04+ from outline_extended.json (aligned with Chinese spec)."""
    path = ROOT / "outline_extended.json"
    if not path.exists():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    compiler_tpl: list[tuple[str, list[str]]] = data.get("compiler_section_template", [])
    chapters: list[ChapterSpec] = []
    for entry in data.get("chapters", []):
        if entry.get("template") == "compiler":
            prefix = entry["prefix"]
            sections_raw = [(tpl[0].format(p=prefix), tpl[1]) for tpl in compiler_tpl]
        else:
            sections_raw = entry.get("sections", [])
        sections = tuple(
            SectionSpec(label, tuple(pats)) for label, pats in sections_raw
        )
        chapters.append(
            ChapterSpec(
                chapter_id=entry["id"],
                filename=entry["file"],
                title=entry["title"],
                min_words=entry["min_words"],
                max_words=entry["max_words"],
                min_citations=entry["min_citations"],
                sections=sections,
            )
        )
    return tuple(chapters)


def _load_book_parts() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    path = ROOT / "outline_extended.json"
    if not path.exists():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple((pid, title, tuple(ch_ids)) for pid, title, ch_ids in data.get("parts", []))


BOOK_PARTS: tuple[tuple[str, str, tuple[str, ...]], ...] = _load_book_parts()
OUTLINE = _OUTLINE_CORE + _load_extended_outline()


def read_chapter_text(spec: ChapterSpec) -> str:
    path = CHAPTERS / spec.filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def count_words(text: str) -> int:
    body = re.sub(r"\\[a-zA-Z@]+(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    body = re.sub(r"%.*", " ", body)
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]+", body)
    return len(tokens)


def count_citations(text: str) -> int:
    keys = set(re.findall(r"\\cite[tp]?\{([^}]+)\}", text))
    expanded: set[str] = set()
    for group in keys:
        for key in group.split(","):
            expanded.add(key.strip())
    return len(expanded)


def section_covered(text: str, section: SectionSpec) -> bool:
    lowered = text.lower()
    return all(re.search(pat, lowered) for pat in section.patterns)


def word_score(count: int, spec: ChapterSpec) -> float:
    if count < spec.min_words:
        return max(0.0, count / spec.min_words)
    if count > spec.max_words:
        return max(0.5, spec.max_words / count)
    mid = (spec.min_words + spec.max_words) / 2
    if count <= mid:
        return 0.7 + 0.3 * (count - spec.min_words) / (mid - spec.min_words)
    return 1.0 - 0.2 * (count - mid) / (spec.max_words - mid)


def citation_score(count: int, spec: ChapterSpec) -> float:
    return min(1.0, count / spec.min_citations)


def sync_main_tex_inputs() -> list[str]:
    """Rewrite main.tex chapter \\input lines to match OUTLINE order (existing files only)."""
    main_tex = BOOKS / "main.tex"
    if not main_tex.exists():
        return []
    text = main_tex.read_text(encoding="utf-8")
    specs = [s for s in OUTLINE if (CHAPTERS / s.filename).exists()]
    if not specs:
        return []
    block = "\n\n".join(
        f"\\input{{{CHAPTER_INPUT_DIR}/{s.filename}}}" for s in specs
    ) + "\n\n"
    pattern = re.compile(
        r"(\\mainmatter\s*\n)(.*?)(\n\\small\{\s*\n\\typeout\{START_CHAPTER \"bib\")",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return []
    new_text = text[: match.start(2)] + block + text[match.start(3) :]
    if new_text != text:
        main_tex.write_text(new_text, encoding="utf-8")
    return [s.chapter_id for s in specs]


def chapter_spec_by_id(chapter_id: str) -> ChapterSpec | None:
    for spec in OUTLINE:
        if spec.chapter_id == chapter_id:
            return spec
    return None


def write_standalone_tex(spec: ChapterSpec) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    target = BUILD_DIR / f"{spec.chapter_id}.tex"
    target.write_text(
        f"""\\documentclass[11pt,oneside,a4paper]{{book}}
\\input{{chapter_preamble.tex}}

\\title{{AI Compiler Performance Engineering}}
\\author{{Auto-Loops Books — {spec.chapter_id}}}
\\date{{}}

\\begin{{document}}

\\setlength{{\\parskip}}{{0.25 \\baselineskip}}
\\newlength{{\\figwidth}}
\\setlength{{\\figwidth}}{{26pc}}

\\frontmatter
\\maketitle
\\tableofcontents
\\mainmatter

\\input{{build/chapters/{spec.filename}}}

\\small{{
\\bibliography{{book,citations_merged}}
\\bibliographystyle{{natbib}}
\\clearpage
}}
\\printindex

\\end{{document}}
""",
        encoding="utf-8",
    )
    return target


def compile_stem(stem: str, *, verbose: bool = False) -> bool:
    env = os.environ.copy()
    env["BOOK"] = stem
    try:
        proc = subprocess.run(
            ["bash", "make.sh"],
            cwd=BOOKS,
            capture_output=not verbose,
            text=True,
            timeout=CHAPTER_COMPILE_TIMEOUT if stem != "main" else BOOK_COMPILE_TIMEOUT,
            check=False,
            env=env,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False

    pdf_src = BOOKS / f"{stem}.pdf"
    if not pdf_src.exists():
        if not verbose:
            tail = (proc.stdout or "") + (proc.stderr or "")
            if tail.strip():
                print(tail[-5000:], file=sys.stderr)
        return False

    if stem != "main":
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        dest = PDF_DIR / f"{stem}.pdf"
        dest.write_bytes(pdf_src.read_bytes())
        if verbose:
            print(f"Wrote {dest}")
    elif verbose:
        print(f"Wrote {pdf_src}")
    return True


def compile_chapter(chapter_id: str, *, verbose: bool = False) -> bool:
    spec = chapter_spec_by_id(chapter_id)
    if not spec:
        return False
    if not (CHAPTERS / spec.filename).exists():
        return False
    write_standalone_tex(spec)
    return compile_stem(spec.chapter_id, verbose=verbose)


def compile_all_chapters(*, verbose: bool = False) -> bool:
    ok = True
    for spec in OUTLINE:
        if not (CHAPTERS / spec.filename).exists():
            continue
        if not compile_chapter(spec.chapter_id, verbose=verbose):
            ok = False
    return ok


def compile_book(*, verbose: bool = False) -> bool:
    try:
        sync_main_tex_inputs()
        return compile_stem("main", verbose=verbose)
    except OSError:
        return False


def _visual_audit(spec: ChapterSpec) -> dict:
    try:
        from book_visuals import audit_chapter

        return audit_chapter(spec.chapter_id)
    except Exception:
        return {}


def evaluate_chapter(spec: ChapterSpec, compile_ok: bool) -> dict:
    text = read_chapter_text(spec)
    visual = _visual_audit(spec)
    if not text.strip():
        return {
            "chapter": spec.chapter_id,
            "coverage_pct": 0.0,
            "word_count": 0,
            "citation_count": 0,
            "compile_ok": compile_ok,
            "quality_score": 0.0,
            "missing_sections": [s.label for s in spec.sections],
            "table_count": visual.get("table_count", 0),
            "figure_count": visual.get("figure_count", 0),
            "visual_missing": visual.get("missing_ids", []),
        }

    covered = [s for s in spec.sections if section_covered(text, s)]
    missing = [s.label for s in spec.sections if s not in covered]
    coverage_pct = 100.0 * len(covered) / len(spec.sections)

    words = count_words(text)
    cites = count_citations(text)

    cov_s = coverage_pct / 100.0
    word_s = word_score(words, spec)
    cite_s = citation_score(cites, spec)
    compile_s = 1.0 if compile_ok else 0.0

    quality = 100.0 * (0.4 * cov_s + 0.2 * word_s + 0.2 * cite_s + 0.2 * compile_s)

    return {
        "chapter": spec.chapter_id,
        "coverage_pct": round(coverage_pct, 1),
        "word_count": words,
        "citation_count": cites,
        "compile_ok": compile_ok,
        "quality_score": round(quality, 1),
        "missing_sections": missing,
        "table_count": visual.get("table_count", 0),
        "figure_count": visual.get("figure_count", 0),
        "visual_missing": visual.get("missing_ids", []),
    }


def print_summary(result: dict) -> None:
    print("---")
    print(f"chapter:          {result['chapter']}")
    print(f"coverage_pct:     {result['coverage_pct']:.1f}")
    print(f"word_count:       {result['word_count']}")
    print(f"citation_count:   {result['citation_count']}")
    print(f"compile_ok:       {str(result['compile_ok']).lower()}")
    print(f"quality_score:    {result['quality_score']:.1f}")
    if result.get("missing_sections"):
        print(f"missing_sections: {','.join(result['missing_sections'])}")
    if "table_count" in result:
        print(f"table_count:      {result['table_count']}")
        print(f"figure_count:     {result['figure_count']}")
        if result.get("visual_missing"):
            print(f"visual_missing:   {','.join(result['visual_missing'])}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", help="chapter id, e.g. ch01")
    parser.add_argument(
        "--full-book",
        action="store_true",
        help="with --chapter, compile main.pdf instead of standalone chapter PDF",
    )
    parser.add_argument(
        "--compile-all-chapters",
        action="store_true",
        help="build pdf/chXX.pdf for every existing chapter tex",
    )
    parser.add_argument("--skip-compile", action="store_true")
    parser.add_argument("--verbose-compile", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for spec in OUTLINE:
            print(f"{spec.chapter_id}\t{spec.filename}\t{spec.title}")
        return 0

    if args.compile_all_chapters:
        if args.skip_compile:
            print("skip-compile: no PDFs built", file=sys.stderr)
            return 0
        ok = compile_all_chapters(verbose=args.verbose_compile)
        return 0 if ok else 1

    compile_ok = True
    if not args.skip_compile:
        if args.chapter and not args.full_book:
            compile_ok = compile_chapter(args.chapter, verbose=args.verbose_compile)
        else:
            compile_ok = compile_book(verbose=args.verbose_compile)

    specs = OUTLINE
    if args.chapter:
        specs = tuple(s for s in OUTLINE if s.chapter_id == args.chapter)
        if not specs:
            print(f"unknown chapter: {args.chapter}", file=sys.stderr)
            return 1

    for spec in specs:
        result = evaluate_chapter(spec, compile_ok)
        print_summary(result)

    return 0 if compile_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
