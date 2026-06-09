#!/usr/bin/env python3
"""Global compliance audit against AI Compiler Performance Engineering.md."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SPEC_MD = ROOT / "AI Compiler Performance Engineering.md"
BOOKS = ROOT / "books"
CHAPTERS = BOOKS / "chapters"
RESEARCH = BOOKS / "research"

sys.path.insert(0, str(ROOT))
from book_prepare import (  # noqa: E402
    BOOK_PARTS,
    CHAPTERS as CH_DIR,
    OUTLINE,
    ChapterSpec,
    compile_book,
    evaluate_chapter,
    read_chapter_text,
    section_covered,
)
from loops.iterate import chapter_ready, style_violations  # noqa: E402

COMPILER_CHAPTERS = frozenset({"ch14", "ch15", "ch16", "ch17", "ch18", "ch19", "ch20"})
COMPILER_SECTION_SUFFIXES = (
    "_hw_matrix",
    "_arch_passes",
    "_codegen",
    "_tuning",
    "_case_study",
)
EXPECTED_CHAPTER_COUNT = 27
EXPECTED_PART_COUNT = 7
APPENDIX_LABELS = tuple(f"附录{chr}" for chr in "ABCDEFGH")

SPEC_CHAPTER_RE = re.compile(r"#### 第(\d+)章\s+(.+)")
SPEC_PART_RE = re.compile(r"### 第([一二三四五六七])篇\s+(.+?)[（(]")


@dataclass
class Finding:
    severity: str  # P0|P1|P2|P3
    area: str
    message: str
    detail: str = ""


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def add(self, severity: str, area: str, message: str, detail: str = "") -> None:
        self.findings.append(Finding(severity, area, message, detail))

    def score(self) -> float:
        weights = {"P0": 25, "P1": 10, "P2": 3, "P3": 1}
        penalty = sum(weights.get(f.severity, 1) for f in self.findings)
        return max(0.0, 100.0 - penalty)


def parse_spec_chapters() -> dict[int, str]:
    if not SPEC_MD.exists():
        return {}
    text = SPEC_MD.read_text(encoding="utf-8")
    return {int(m.group(1)): m.group(2).strip() for m in SPEC_CHAPTER_RE.finditer(text)}


def parse_spec_parts() -> list[str]:
    if not SPEC_MD.exists():
        return []
    text = SPEC_MD.read_text(encoding="utf-8")
    return [m.group(2).strip() for m in SPEC_PART_RE.finditer(text)]


def audit_structure(report: AuditReport) -> None:
    spec_chs = parse_spec_chapters()
    outline_ids = [s.chapter_id for s in OUTLINE]

    if len(OUTLINE) != EXPECTED_CHAPTER_COUNT:
        report.add("P0", "structure", f"OUTLINE has {len(OUTLINE)} chapters, spec requires {EXPECTED_CHAPTER_COUNT}")

    for n in range(1, EXPECTED_CHAPTER_COUNT + 1):
        cid = f"ch{n:02d}"
        if cid not in outline_ids:
            report.add("P0", "structure", f"Missing OUTLINE entry for spec 第{n}章", cid)

    if len(BOOK_PARTS) != EXPECTED_PART_COUNT:
        report.add("P1", "structure", f"BOOK_PARTS has {len(BOOK_PARTS)} parts, spec requires {EXPECTED_PART_COUNT}")

    part_ch_count = sum(len(ids) for _, _, ids in BOOK_PARTS)
    if part_ch_count != len(OUTLINE):
        report.add("P1", "structure", f"Part chapter ids ({part_ch_count}) != OUTLINE ({len(OUTLINE)})")

    spec_part_titles = parse_spec_parts()
    if len(spec_part_titles) == EXPECTED_PART_COUNT and len(BOOK_PARTS) == EXPECTED_PART_COUNT:
        for i, (_, en_title, _) in enumerate(BOOK_PARTS):
            if i >= len(spec_part_titles):
                break
            # English part titles are mapped; only check count alignment
            pass

    for spec_num, spec_title in spec_chs.items():
        cid = f"ch{spec_num:02d}"
        spec_entry = next((s for s in OUTLINE if s.chapter_id == cid), None)
        if not spec_entry:
            continue
        path = CHAPTERS / spec_entry.filename
        if not path.exists():
            report.add("P1", "files", f"{cid} .tex missing", spec_entry.filename)

    report.stats["spec_chapters_in_md"] = len(spec_chs)
    report.stats["outline_chapters"] = len(OUTLINE)
    report.stats["tex_files"] = len(list(CHAPTERS.glob("ch*.tex")))


def audit_compiler_template(report: AuditReport) -> None:
    tpl_path = ROOT / "outline_extended.json"
    if not tpl_path.exists():
        report.add("P0", "compiler_template", "outline_extended.json missing")
        return
    data = json.loads(tpl_path.read_text(encoding="utf-8"))
    tpl = data.get("compiler_section_template", [])
    if len(tpl) != 5:
        report.add("P1", "compiler_template", f"compiler_section_template has {len(tpl)} sections, spec requires 5")

    for spec in OUTLINE:
        if spec.chapter_id not in COMPILER_CHAPTERS:
            continue
        labels = [s.label for s in spec.sections]
        prefix = spec.chapter_id.replace("ch", "")
        # extract prefix from first section e.g. mlir_hw_matrix
        if labels:
            p = labels[0].split("_")[0]
            for suffix in ("_hw_matrix", "_arch_passes", "_codegen", "_tuning", "_case_study"):
                expected = f"{p}{suffix}"
                if expected not in labels:
                    report.add("P1", "compiler_template", f"{spec.chapter_id} missing section {expected}")


def audit_governance(report: AuditReport) -> None:
    for name, path in [
        ("WRITING_STYLE", BOOKS / "WRITING_STYLE.md"),
        ("FACT_VERIFICATION", BOOKS / "FACT_VERIFICATION.md"),
        ("visuals_style.py", BOOKS / "visuals_style.py"),
        ("program_books", ROOT / "program_books.md"),
    ]:
        if not path.exists():
            report.add("P0", "governance", f"Required file missing: {name}", str(path))

    spec_text = SPEC_MD.read_text(encoding="utf-8") if SPEC_MD.exists() else ""
    if "WRITING_STYLE.md" not in spec_text:
        report.add("P2", "governance", "Spec does not link WRITING_STYLE.md")
    if "FACT_VERIFICATION.md" not in spec_text:
        report.add("P2", "governance", "Spec does not link FACT_VERIFICATION.md")

    pb = (ROOT / "program_books.md").read_text(encoding="utf-8") if (ROOT / "program_books.md").exists() else ""
    if "outline_extended.json" not in pb and "ch04" in pb:
        report.add("P3", "governance", "program_books.md may not document outline_extended.json")


def audit_appendices(report: AuditReport) -> None:
    spec = SPEC_MD.read_text(encoding="utf-8") if SPEC_MD.exists() else ""
    for label in APPENDIX_LABELS:
        if label not in spec:
            continue
    # Check if any appendix tex exists
    appendix_files = list(CHAPTERS.glob("*appendix*")) + list(BOOKS.glob("*appendix*"))
    if not appendix_files:
        report.add("P2", "appendices", "Spec defines 附录A–H but no appendix .tex files in repo")
    report.stats["appendix_files"] = len(appendix_files)


def audit_book_themes(report: AuditReport) -> None:
    """Spec §七: dual case study, three hardware classes, YiRage thread."""
    all_tex = "\n".join(
        (CHAPTERS / s.filename).read_text(encoding="utf-8")
        for s in OUTLINE
        if (CHAPTERS / s.filename).exists()
    ).lower()
    ready_tex = "\n".join(read_chapter_text(s).lower() for s in OUTLINE if chapter_ready(s))

    themes = {
        "yirage": r"yirage|yirage",
        "gpu": r"\bgpu\b|cuda|hopper|tensor core",
        "cpu": r"\bcpu\b|cache|numa|simd",
        "npu": r"\bnpu\b|xdna|aie|edge",
        "llama": r"llama|qwen",
        "resnet": r"resnet",
        "mlir": r"\bmlir\b",
    }
    for name, pat in themes.items():
        report.stats[f"theme_{name}_all_chapters"] = bool(re.search(pat, all_tex, re.I))
        report.stats[f"theme_{name}_ready_chapters"] = bool(re.search(pat, ready_tex, re.I))

    if not report.stats.get("theme_resnet_all_chapters"):
        report.add("P2", "themes", "Spec §七 requires ResNet + LLM dual case study; ResNet not mentioned in any chapter")
    if not report.stats.get("theme_llama_ready_chapters"):
        report.add("P2", "themes", "Ready chapters lack LLaMA/Qwen case references (spec §七)")
    if not report.stats.get("theme_yirage_ready_chapters"):
        report.add("P1", "themes", "Ready chapters lack YiRage mentions (spec §八)")

    yirage_ready = sum(
        1 for s in OUTLINE
        if chapter_ready(s) and re.search(r"yirage", read_chapter_text(s), re.I)
    )
    report.stats["yirage_in_ready_count"] = yirage_ready
    report.stats["ready_count"] = sum(1 for s in OUTLINE if chapter_ready(s))


def audit_facts_and_style(report: AuditReport) -> None:
    for spec in OUTLINE:
        tex = read_chapter_text(spec)
        if not tex.strip():
            continue
        if chapter_ready(spec):
            vf = RESEARCH / spec.chapter_id / "verified_facts.jsonl"
            if not vf.exists():
                report.add("P1", "facts", f"{spec.chapter_id} ready but no verified_facts.jsonl")
            elif not any(ln.strip() for ln in vf.read_text(encoding="utf-8").splitlines()):
                report.add("P1", "facts", f"{spec.chapter_id} verified_facts.jsonl is empty")
        for issue in style_violations(tex):
            if chapter_ready(spec):
                report.add("P2", "style", f"{spec.chapter_id}: {issue}")


def audit_chapter_gates(report: AuditReport) -> None:
    compile_ok = compile_book()
    if not compile_ok:
        report.add("P0", "build", "Full book compile failed (make.sh)")

    ready, open_ch = [], []
    gate_details: list[dict[str, Any]] = []
    for spec in OUTLINE:
        ev = evaluate_chapter(spec, compile_ok=compile_ok)
        ok = chapter_ready(spec, ev)
        row = {
            "id": spec.chapter_id,
            "ready": ok,
            "coverage": ev["coverage_pct"],
            "words": ev["word_count"],
            "min_words": spec.min_words,
            "cites": ev["citation_count"],
            "min_cites": spec.min_citations,
            "quality": ev["quality_score"],
            "missing_sections": ev.get("missing_sections", []),
            "visual_missing": ev.get("visual_missing", []),
        }
        gate_details.append(row)
        (ready if ok else open_ch).append(spec.chapter_id)

    report.stats["ready_chapters"] = ready
    report.stats["open_chapters"] = open_ch
    report.stats["ready_count"] = len(ready)
    report.stats["compile_ok"] = compile_ok
    report.stats["gate_details"] = gate_details

    if len(ready) < 3:
        report.add("P1", "progress", f"Only {len(ready)}/27 chapters pass gates; spec expects full manuscript")

    stub_only = [
        r["id"] for r in gate_details
        if r["words"] < 200 and r["id"] not in ready
    ]
    if stub_only:
        report.add("P2", "progress", f"{len(stub_only)} chapters are stubs (<200 words)", ", ".join(stub_only[:8]) + ("…" if len(stub_only) > 8 else ""))

    # ch03 in main.tex order
    main = (BOOKS / "main.tex").read_text(encoding="utf-8") if (BOOKS / "main.tex").exists() else ""
    inputs = re.findall(r"\\input\{chapters/([^}]+)\}", main)
    outline_files = [s.filename for s in OUTLINE if (CHAPTERS / s.filename).exists()]
    if inputs != outline_files:
        report.add("P1", "build", "main.tex chapter order differs from OUTLINE file existence order")


def audit_main_tex(report: AuditReport) -> None:
    main = BOOKS / "main.tex"
    if not main.exists():
        report.add("P0", "build", "books/main.tex missing")
        return
    text = main.read_text(encoding="utf-8")
    for spec in OUTLINE:
        if (CHAPTERS / spec.filename).exists():
            needle = f"\\input{{chapters/{spec.filename}}}"
            if needle not in text:
                report.add("P2", "build", f"main.tex missing \\input for {spec.chapter_id}")


def run_audit() -> AuditReport:
    report = AuditReport()
    audit_structure(report)
    audit_compiler_template(report)
    audit_governance(report)
    audit_appendices(report)
    audit_book_themes(report)
    audit_facts_and_style(report)
    audit_chapter_gates(report)
    audit_main_tex(report)
    return report


def print_report(report: AuditReport) -> None:
    by_sev: dict[str, list[Finding]] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for f in report.findings:
        by_sev.setdefault(f.severity, []).append(f)

    print("=" * 60)
    print("SPEC COMPLIANCE AUDIT")
    print(f"Source: {SPEC_MD.name}")
    print("=" * 60)
    print(f"\nCompliance score: {report.score():.1f}/100")
    print(f"Findings: P0={len(by_sev['P0'])} P1={len(by_sev['P1'])} P2={len(by_sev['P2'])} P3={len(by_sev['P3'])}")

    stats = report.stats
    print(f"\n--- Progress ---")
    print(f"Chapters ready:  {stats.get('ready_count', 0)}/27")
    print(f"Compile OK:      {stats.get('compile_ok', False)}")
    print(f"OUTLINE entries: {stats.get('outline_chapters', 0)}")
    print(f"Tex files:       {stats.get('tex_files', 0)}")

    if stats.get("ready_chapters"):
        print(f"Ready: {', '.join(stats['ready_chapters'])}")

    print(f"\n--- Spec themes (ready chapters) ---")
    for key in ("theme_yirage", "theme_gpu", "theme_cpu", "theme_npu", "theme_llama", "theme_resnet"):
        v = stats.get(f"{key}_ready_chapters", False)
        print(f"  {key}: {'✓' if v else '✗'}")

    for sev in ("P0", "P1", "P2", "P3"):
        items = by_sev[sev]
        if not items:
            continue
        print(f"\n--- {sev} ({len(items)}) ---")
        for f in items:
            line = f"[{f.area}] {f.message}"
            if f.detail:
                line += f" — {f.detail}"
            print(f"  • {line}")

    print(f"\n--- Chapter gate summary ---")
    for row in stats.get("gate_details", []):
        status = "ready" if row["ready"] else "open"
        miss = ""
        if row.get("missing_sections"):
            miss = f" miss={','.join(row['missing_sections'][:3])}"
        print(
            f"  {row['id']}\t{status}\t"
            f"cov={row['coverage']:.0f}%\twords={row['words']}/{row['min_words']}\t"
            f"q={row['quality']:.1f}{miss}"
        )

    print("\n--- Verdict ---")
    if by_sev["P0"]:
        print("FAIL — resolve P0 blockers before claiming spec compliance.")
    elif len(stats.get("ready_chapters", [])) < 27:
        print(f"PARTIAL — structure aligned; manuscript {stats.get('ready_count', 0)}/27 complete.")
    else:
        print("PASS — all chapters meet gates; review P2/P3 polish items.")


def main() -> int:
    report = run_audit()
    print_report(report)
    if any(f.severity == "P0" for f in report.findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
