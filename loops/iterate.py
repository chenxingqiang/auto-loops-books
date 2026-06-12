#!/usr/bin/env python3
"""
Autobooks full-book iteration loop.

Orchestrates research → visuals → compile → evaluate for each chapter,
and emits agent_tasks for prose/bib/outline work the LLM must still do.

Usage:
    uv run book-loop status
    uv run book-loop step
    uv run book-loop step --chapter ch01 --skip-research
    uv run book-loop deep-rewrite --chapter ch14
    uv run book-loop run --max-steps 5
    uv run book-loop insert-visuals --chapter ch01
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book_prepare import (  # noqa: E402
    BOOK_PARTS,
    CHAPTERS,
    OUTLINE,
    ChapterSpec,
    compile_book,
    evaluate_chapter,
    read_chapter_text,
)
from book_visuals import cmd_plan, cmd_render, generated_dir, load_plan  # noqa: E402

RESULTS_TSV = ROOT / "book_results.tsv"
STATE_JSON = ROOT / "loops" / "loop_state.json"
RESEARCH_ROOT = ROOT / "books" / "research"
OUTLINE_SPEC = ROOT / "book_content.md"
WRITING_STYLE = ROOT / "books" / "WRITING_STYLE.md"
STYLE_REFERENCE_CHAPTER = "ch01"

# Numeric/unit tokens that trigger fact-verification expectations when uncited.
FACT_NUMERIC_PATTERN = re.compile(
    r"\d[\d,.]*\s*(?:%|×|x|ms|μs|us|gb/s|tb/s|tok/s|kernels?/token|bytes/token|flop/s|gflop)",
    re.IGNORECASE,
)

# Soft lint: forbidden lecture/tutorial phrasing in English manuscript (case-insensitive).
FORBIDDEN_STYLE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"this section (will )?introduc", "lecture opener — use problem-first hook"),
    (r"this chapter (will )?(focus|cover|discuss)", "lecture opener — use production contradiction"),
    (r"as (is )?well[- ]known", "textbook filler"),
    (r"simply put", "oversimplified framing"),
    (r"it is (important|worth) to note that", "empty emphasis"),
    (r"in this section,? we (will )?", "meta narration"),
    (r"let us (first )?(define|introduce|review)", "primer-style opening"),
    (r"basics of (cuda|gpu|deep learning)", "entry-level primer"),
)


@dataclass
class StepReport:
    chapter_id: str
    phase: str
    actions: list[str] = field(default_factory=list)
    agent_tasks: list[str] = field(default_factory=list)
    evaluation: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def chapter_spec(chapter_id: str) -> ChapterSpec | None:
    for spec in OUTLINE:
        if spec.chapter_id == chapter_id:
            return spec
    return None


def chapter_tex_path(spec: ChapterSpec) -> Path:
    return CHAPTERS / spec.filename


def chapter_exists(spec: ChapterSpec) -> bool:
    path = chapter_tex_path(spec)
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def load_results_rows() -> list[dict[str, str]]:
    if not RESULTS_TSV.exists():
        return []
    lines = RESULTS_TSV.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < 2:
        return []
    headers = lines[0].split("\t")
    return [dict(zip(headers, line.split("\t"), strict=False)) for line in lines[1:]]


def chapter_ready(spec: ChapterSpec, ev: dict[str, Any] | None = None) -> bool:
    """True when chapter meets all gates for advancing to the next OUTLINE entry."""
    if ev is None:
        ev = evaluate_chapter(spec, compile_ok=True)
    return (
        ev["coverage_pct"] >= 100.0
        and ev["word_count"] >= spec.min_words
        and ev["citation_count"] >= spec.min_citations
        and not ev.get("visual_missing")
        and ev.get("compile_ok", True)
    )


def chapter_priority(spec: ChapterSpec) -> float:
    """Higher = more machine/agent work still needed (for status display)."""
    tex = read_chapter_text(spec)
    if not tex.strip():
        return 500.0

    ev = evaluate_chapter(spec, compile_ok=True)
    if chapter_ready(spec, ev):
        return 0.0

    score = (100.0 - ev["coverage_pct"]) * 2.0
    score += max(0, spec.min_words - ev["word_count"]) / 100.0
    score += max(0, spec.min_citations - ev["citation_count"]) * 5.0
    score += len(ev.get("missing_sections", [])) * 12.0
    score += len(ev.get("visual_missing", [])) * 4.0
    return score


def book_progress() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ready = 0
    for spec in OUTLINE:
        ev = evaluate_chapter(spec, compile_ok=True)
        ok = chapter_ready(spec, ev)
        if ok:
            ready += 1
        rows.append(
            {
                "chapter_id": spec.chapter_id,
                "title": spec.title,
                "ready": ok,
                "quality_score": ev["quality_score"],
                "priority": chapter_priority(spec),
                "evaluation": ev,
            }
        )
    focus = pick_focus_chapter()
    return {
        "outline_chapters": len(OUTLINE),
        "ready_chapters": ready,
        "all_outline_ready": ready == len(OUTLINE),
        "focus_chapter_id": focus.chapter_id,
        "focus_title": focus.title,
        "chapters": rows,
    }


def pick_focus_chapter(
    explicit: str | None = None,
    *,
    strategy: str = "sequential",
) -> ChapterSpec:
    """
    sequential — first OUTLINE chapter not yet `chapter_ready` (default; full-book order).
    weakest    — highest `chapter_priority` among incomplete chapters.
    """
    if explicit:
        spec = chapter_spec(explicit)
        if not spec:
            raise SystemExit(f"Unknown chapter: {explicit}")
        return spec

    incomplete = [s for s in OUTLINE if not chapter_ready(s)]
    if not incomplete:
        return OUTLINE[-1]

    if strategy == "weakest":
        return max(incomplete, key=chapter_priority)
    return incomplete[0]


def ensure_chapter_stub(spec: ChapterSpec) -> bool:
    if chapter_exists(spec):
        return False

    CHAPTERS.mkdir(parents=True, exist_ok=True)
    sections = "\n\n".join(
        f"\\section{{{s.label.replace('_', ' ').title()}}}\n\\label{{sec:{spec.chapter_id}_{s.label}}}\n\n% TODO: expand"
        for s in spec.sections
    )
    body = (
        f"\\chapter{{{spec.title}}}\n"
        f"\\label{{chap:{spec.chapter_id}}}\n"
        f"\\typeout{{START_CHAPTER \"{spec.chapter_id}\" \\theabspage}}\n\n"
        f"{sections}\n\n"
        f"\\typeout{{END_CHAPTER \"{spec.chapter_id}\" \\theabspage}}\n"
    )
    chapter_tex_path(spec).write_text(body, encoding="utf-8")
    return True


def ensure_main_input(spec: ChapterSpec) -> bool:
    from book_prepare import sync_main_tex_inputs

    main_tex = ROOT / "books" / "main.tex"
    before = set(re.findall(r"\\input\{build/chapters/([^}]+)\}", main_tex.read_text(encoding="utf-8")))
    synced = sync_main_tex_inputs()
    after = set(re.findall(r"\\input\{build/chapters/([^}]+)\}", main_tex.read_text(encoding="utf-8")))
    return spec.filename in after and (spec.filename not in before or bool(synced))


def run_research(spec: ChapterSpec, *, skip: bool, dry_run: bool) -> list[str]:
    if skip:
        return ["research: skipped"]

    if dry_run or not os.environ.get("SERPAPI_KEY"):
        from research_tools import extract_chapter_keywords, generate_chapter_queries

        out = RESEARCH_ROOT / spec.chapter_id
        out.mkdir(parents=True, exist_ok=True)
        keywords = extract_chapter_keywords(spec)
        queries = generate_chapter_queries(spec, keywords)
        (out / "keywords.json").write_text(
            json.dumps([{"term": k, "weight": w} for k, w in keywords], indent=2),
            encoding="utf-8",
        )
        (out / "queries.json").write_text(json.dumps(queries, indent=2), encoding="utf-8")
        reason = "dry-run" if dry_run else "SERPAPI_KEY unset"
        return [f"research: {reason} — keywords/queries only"]

    from research_tools import run_chapter_research

    result = run_chapter_research(spec, dry_run=False)
    return [f"research: {result['paper_count']} papers -> {result.get('output_dir', '')}"]


def run_fact_verification(
    spec: ChapterSpec,
    *,
    skip: bool,
    dry_run: bool,
    force_refresh: bool = False,
) -> list[str]:
    if skip:
        return ["facts: skipped"]
    from fact_verify import run_chapter_fact_verify

    report = run_chapter_fact_verify(
        spec, dry_run=dry_run, force_refresh=force_refresh
    )
    rel = (RESEARCH_ROOT / spec.chapter_id / "fact_verify_report.json").relative_to(ROOT)
    return [
        f"facts: {report['verified_ok_count']}/{report['entry_count']} content-verified "
        f"({report['status']}) -> {rel}"
    ]


def run_reference_verify(
    spec: ChapterSpec,
    *,
    min_citation_score: int = 8,
) -> list[str]:
    from research_tools import verify_chapter_references

    report = verify_chapter_references(spec, min_citation_score=min_citation_score)
    rel = (
        RESEARCH_ROOT / spec.chapter_id / "reference_verify_report.json"
    ).relative_to(ROOT)
    low = len(report.get("low_relevance_citations", []))
    return [
        f"refs: {report['status']} — {report['citation_count']} cites, "
        f"{report['keyword_count']} keywords, low={low} -> {rel}"
    ]


def run_citation_loop(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    min_papers: int = 25,
    apply_tex: bool = True,
    merge_bib: bool = True,
    quality: CitationQualityOptions | None = None,
) -> list[str]:
    from citation_loop import (
        CitationQualityOptions,
        merge_all_chapter_bibs,
        refilter_chapter_bindings,
        redistribute_citations_to_tex,
        run_chapter_citation_plan,
        strict_verify_chapter_citations,
    )

    opts = quality or CitationQualityOptions(tier_a_only=True)
    plan = run_chapter_citation_plan(
        spec, dry_run=dry_run, min_papers=min_papers, quality=opts
    )
    refilter_chapter_bindings(spec, opts)
    verify = strict_verify_chapter_citations(spec, min_papers=min_papers, quality=opts)
    rel = (RESEARCH_ROOT / spec.chapter_id / "citation_strict_report.json").relative_to(ROOT)
    actions = [
        f"citations: plan papers={plan['paper_count']} bindings={plan['binding_count']} "
        f"min_ok={plan['meets_min_papers']}",
        f"citations: strict {verify['status']} -> {rel}",
    ]
    if verify["status"] == "pass" and apply_tex and not dry_run:
        applied = redistribute_citations_to_tex(spec, quality=opts)
        actions.append(
            f"citations: redistributed pool={applied['pool_count']} "
            f"assigned={applied['assigned_count']} sections={applied['sections_with_cites']} "
            f"keys_in_tex={applied['unique_keys_in_tex']} -> {applied['tex_path']}"
        )
    if merge_bib and not dry_run:
        m = merge_all_chapter_bibs(tier_a_only=opts.tier_a_only)
        actions.append(f"citations: merged bib {m['entry_count']} entries -> {m['output']}")
    return actions


def visual_marker(visual_id: str) -> str:
    return f"% AUTO_VISUAL:{visual_id}"


def insert_missing_visuals(spec: ChapterSpec) -> int:
    plan = load_plan(spec.chapter_id)
    if not plan:
        cmd_plan(spec.chapter_id)
        plan = load_plan(spec.chapter_id)
    if not plan:
        return 0

    path = chapter_tex_path(spec)
    tex = path.read_text(encoding="utf-8")
    gen_dir = generated_dir(spec.chapter_id)
    inserted = 0

    for vis in plan:
        if vis.label in tex or visual_marker(vis.id) in tex:
            continue
        snippet_path = gen_dir / f"{vis.id}.tex"
        if not snippet_path.exists():
            continue
        anchor = f"\\label{{sec:{spec.chapter_id}_{vis.section}}}"
        if anchor not in tex:
            continue
        snippet = snippet_path.read_text(encoding="utf-8").strip()
        tex = tex.replace(anchor, anchor + f"\n{visual_marker(vis.id)}\n{snippet}\n", 1)
        inserted += 1

    if inserted:
        path.write_text(tex, encoding="utf-8")
    return inserted


def run_visuals(spec: ChapterSpec) -> list[str]:
    cmd_plan(spec.chapter_id)
    cmd_render(spec.chapter_id, None)
    inserted = insert_missing_visuals(spec)
    return ["visuals: plan synced", "visuals: rendered", f"visuals: inserted {inserted} snippet(s)"]


def style_violations(tex: str) -> list[str]:
    lowered = tex.lower()
    hits: list[str] = []
    for pattern, reason in FORBIDDEN_STYLE_PATTERNS:
        if re.search(pattern, lowered):
            hits.append(reason)
    return hits


def chapter_ending_violations(tex: str) -> list[str]:
    """Fregly gold ending: Key Takeaways + Conclusion; no legacy Chapter Summary."""
    if len(tex.strip()) < 500:
        return []
    hits: list[str] = []
    if re.search(r"\\section\{Chapter Summary\}", tex):
        hits.append("replace \\section{Chapter Summary} with Key Takeaways + Conclusion")
    if "\\section{Key Takeaways}" not in tex:
        hits.append("add \\section{Key Takeaways} before Conclusion (Fregly gold ending)")
    if "\\section{Conclusion}" not in tex:
        hits.append("add \\section{Conclusion} after Key Takeaways")
    return hits


def verified_facts_path(spec: ChapterSpec) -> Path:
    return RESEARCH_ROOT / spec.chapter_id / "verified_facts.jsonl"


def uncited_numeric_paragraphs(tex: str, *, max_hits: int = 5) -> list[str]:
    """Soft lint: paragraphs with benchmark-like numbers but no \\cite."""
    hits: list[str] = []
    chunks = re.split(r"\n\s*\n", tex)
    for chunk in chunks:
        if "%" in chunk and chunk.strip().startswith("%"):
            continue
        if not FACT_NUMERIC_PATTERN.search(chunk):
            continue
        if re.search(r"\\cite[tp]?\{", chunk):
            continue
        if "\\vispending" in chunk or "Pending:" in chunk or "TODO" in chunk:
            continue
        snippet = re.sub(r"\s+", " ", chunk).strip()[:120]
        hits.append(snippet + ("…" if len(chunk) > 120 else ""))
        if len(hits) >= max_hits:
            break
    return hits


def fact_verification_tasks(spec: ChapterSpec, tex: str) -> list[str]:
    tasks: list[str] = []
    log_path = verified_facts_path(spec)
    rel_log = log_path.relative_to(ROOT) if log_path.is_relative_to(ROOT) else log_path

    tasks.append(
        f"Facts: every numeric claim / worked example must pass web verification "
        f"(≥2 independent sources); log to {rel_log} with URLs — see WRITING_STYLE.md §八"
    )

    if not log_path.exists():
        tasks.append(
            f"Fact gate: create {rel_log} before adding new measurements or vendor specs"
        )
    else:
        lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            tasks.append(f"Fact gate: {rel_log} is empty — record verified claims with source URLs")

    for snippet in uncited_numeric_paragraphs(tex):
        tasks.append(f"Fact check (uncited numbers): {snippet}")

    try:
        from fact_verify import fact_verify_tasks

        tasks.extend(fact_verify_tasks(spec.chapter_id))
    except ImportError:
        pass

    return tasks


PAD_DEDUP_DEEP_REWRITE_FLOOR = 1000


def pad_dedup_tasks(spec: ChapterSpec) -> list[str]:
    try:
        from book_pad_dedup import audit_chapter

        report = audit_chapter(spec)
    except ImportError:
        return []
    if not report["changed"]:
        return []
    cmd = f"python3 book_pad_dedup.py --apply {spec.chapter_id}"
    words_after = report["words_after"]
    if words_after < PAD_DEDUP_DEEP_REWRITE_FLOOR:
        return [
            "Pad dedup: duplicate pad_agent tail before Key Takeaways "
            f"({report['words_before']}->{words_after} words). "
            "Strip-only would leave thin filler—run "
            f"`uv run book-loop deep-rewrite --chapter {spec.chapter_id}` "
            "for Fregly prose (do not `--force --adjust-min` alone)."
        ]
    if words_after < report["min_words"]:
        return [
            "Pad dedup: duplicate pad_agent tail before Key Takeaways "
            f"({report['words_before']}->{words_after} words). "
            f"Prefer `uv run book-loop deep-rewrite --chapter {spec.chapter_id}`; "
            f"strip-only fallback: `{cmd} --force --adjust-min`."
        ]
    return [
        f"Pad dedup: run `{cmd}` to remove pad tail "
        f"({report['words_before']}->{words_after} words, coverage {report['coverage']})."
    ]


def build_agent_tasks(spec: ChapterSpec, ev: dict[str, Any]) -> list[str]:
    tasks: list[str] = []
    research_dir = RESEARCH_ROOT / spec.chapter_id

    tasks.append(
        f"Voice: follow {WRITING_STYLE.name} (engineer-narrative; problem-first; HW/SW bound; "
        f"multi-hardware). Gold standard: {STYLE_REFERENCE_CHAPTER}."
    )

    tex = read_chapter_text(spec)
    for issue in style_violations(tex):
        tasks.append(f"Style fix: {issue} (see {WRITING_STYLE.name} §III)")

    for issue in chapter_ending_violations(tex):
        tasks.append(f"Chapter ending: {issue} (see {WRITING_STYLE.name} §VII)")

    tasks.extend(pad_dedup_tasks(spec))

    try:
        from book_proper_nouns import proper_noun_tasks

        tasks.extend(proper_noun_tasks(spec))
    except ImportError:
        pass

    tasks.extend(fact_verification_tasks(spec, tex))

    if not chapter_exists(spec):
        tasks.append(f"Write initial prose for {spec.chapter_id} ({spec.title})")

    for section in ev.get("missing_sections", []):
        tasks.append(f"Expand section `{section}` with cited prose")

    if ev.get("word_count", 0) < spec.min_words:
        tasks.append(f"Word count >= {spec.min_words} (now {ev.get('word_count', 0)})")

    if ev.get("citation_count", 0) < spec.min_citations:
        tasks.append(f"Citations >= {spec.min_citations} (now {ev.get('citation_count', 0)})")

    if (research_dir / "search_data.json").exists():
        tasks.append(f"Add bib entries from {research_dir / 'search_data.json'}")

    if (research_dir / "section_references.md").exists():
        tasks.append(f"Cite from {research_dir / 'section_references.md'}")

    try:
        from research_tools import reference_verify_tasks

        tasks.extend(reference_verify_tasks(spec.chapter_id))
    except ImportError:
        pass

    try:
        from citation_loop import citation_strict_tasks

        tasks.extend(citation_strict_tasks(spec.chapter_id))
    except ImportError:
        pass

    for vid in ev.get("visual_missing", []):
        gen = generated_dir(spec.chapter_id) / f"{vid}.tex"
        tasks.append(f"Insert or refine visual `{vid}` ({gen})")

    if not tasks:
        tasks.append(f"Polish {spec.chapter_id}; re-run book-loop step when gates pass")
    return tasks


def append_results_row(ev: dict[str, Any], description: str, status: str = "keep") -> None:
    if not RESULTS_TSV.exists():
        RESULTS_TSV.write_text(
            "commit\tcoverage_pct\tword_count\tcitations\tquality_score\tstatus\tdescription\n",
            encoding="utf-8",
        )
    commit = f"{ev['chapter']}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    row = (
        f"{commit}\t{ev['coverage_pct']}\t{ev['word_count']}\t{ev['citation_count']}\t"
        f"{ev['quality_score']}\t{status}\t{description}\n"
    )
    with RESULTS_TSV.open("a", encoding="utf-8") as f:
        f.write(row)


def save_loop_state(report: StepReport) -> None:
    STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    STATE_JSON.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "chapter_id": report.chapter_id,
                "phase": report.phase,
                "actions": report.actions,
                "agent_tasks": report.agent_tasks,
                "evaluation": report.evaluation,
                "errors": report.errors,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def part_progress() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ready_ids = {r["chapter_id"] for r in book_progress()["chapters"] if r["ready"]}
    for part_id, title, chapter_ids in BOOK_PARTS:
        n_ready = sum(1 for cid in chapter_ids if cid in ready_ids)
        rows.append(
            {
                "part_id": part_id,
                "title": title,
                "ready": n_ready,
                "total": len(chapter_ids),
                "chapter_ids": chapter_ids,
            }
        )
    return rows




def section_label_display(spec: ChapterSpec, section_label: str) -> str:
    from book_proper_nouns import canonicalize_prose

    return canonicalize_prose(section_label.replace("_", " "))


def write_deep_rewrite_brief(spec: ChapterSpec) -> Path:
    """Write per-section rewrite brief for agent (Chinese spec bullets + EN patterns)."""
    from research_tools import chapter_number, extract_outline_bullets

    ch_num = chapter_number(spec.chapter_id)
    bullets = extract_outline_bullets(ch_num)
    lines = [
        f"# Deep rewrite brief — {spec.chapter_id}",
        "",
        f"**Title:** {spec.title}",
        f"**Gold standard:** `{STYLE_REFERENCE_CHAPTER}` + `books/WRITING_STYLE.md`",
        "",
        "## Machine pass (done by `book-loop deep-rewrite`)",
        "",
        "1. Strip template / batch filler",
        "2. Section-aligned prose scaffold (`book_prose_upgrade.py`)",
        "3. Proper nouns, facts, citations, visuals, compile",
        "",
        "## Agent pass — rewrite each section to ch01 density",
        "",
        "Per section: problem-first hook → HW constraint → compile/kernel fix → "
        "multi-HW delta → cited metric or worked example.",
        "",
    ]
    for i, sec in enumerate(spec.sections):
        title = section_label_display(spec, sec.label)
        bullet = bullets[i] if i < len(bullets) else "(see Chinese spec)"
        patterns = ", ".join(sec.patterns)
        lines.extend(
            [
                f"### {i + 1}. `{sec.label}` — {title}",
                "",
                f"- **Spec bullet:** {bullet}",
                f"- **Coverage patterns:** `{patterns}`",
                f"- **Target:** ≥3 paragraphs + optional table/example; no template rotation",
                f"- **Anchor:** `\\label{{sec:{sec.label}}}` or `sec:{spec.chapter_id}_{sec.label}`",
                "",
            ]
        )
    out = RESEARCH_ROOT / spec.chapter_id / "deep_rewrite_brief.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def build_deep_rewrite_agent_tasks(spec: ChapterSpec, ev: dict[str, Any]) -> list[str]:
    brief = write_deep_rewrite_brief(spec)
    rel_brief = brief.relative_to(ROOT)
    gold = CHAPTERS / f"{STYLE_REFERENCE_CHAPTER}_llm_decode_bottlenecks.tex"
    if not gold.exists():
        gold = next((CHAPTERS / s.filename for s in OUTLINE if s.chapter_id == STYLE_REFERENCE_CHAPTER), None)

    tasks = [
        f"Deep rewrite {spec.chapter_id}: read {rel_brief} and rewrite EVERY section in "
        f"`books/build/chapters/{spec.filename}` to match ch01 engineering narrative density.",
        f"Voice: {WRITING_STYLE.name} — problem-first, HW↔SW chain, GPU/CPU/NPU deltas; "
        "no template paragraphs.",
    ]
    if gold and gold.exists():
        tasks.append(f"Rhythm reference: {gold.relative_to(ROOT)}")

    tasks.extend(build_agent_tasks(spec, ev))

    q = ev.get("quality_score", 0)
    if q < 85:
        tasks.append(
            f"Quality uplift: quality_score={q:.1f} — add cited metrics, tables, or "
            f"\begin{{example}} blocks per section (see ch01)."
        )
    return tasks


def run_deep_rewrite(
    *,
    chapter: str,
    skip_research: bool = False,
    research_dry_run: bool = False,
    skip_fact_verify: bool = False,
    fact_verify_dry_run: bool = False,
    skip_prose: bool = False,
    skip_compile: bool = False,
    force_prose: bool = True,
    citation_redistribute: bool = False,
) -> StepReport:
    spec = chapter_spec(chapter)
    if not spec:
        raise SystemExit(f"Unknown chapter: {chapter}")

    report = StepReport(chapter_id=spec.chapter_id, phase="deep-rewrite")

    brief = write_deep_rewrite_brief(spec)
    report.actions.append(f"brief: {brief.relative_to(ROOT)}")

    if ensure_chapter_stub(spec):
        report.actions.append(f"stub: created {spec.filename}")
    if ensure_main_input(spec):
        report.actions.append("main.tex: added chapter \input")

    if not skip_prose:
        try:
            from book_batch_complete import strip_boilerplate
            from book_prose_upgrade import upgrade_chapter

            tex_path = chapter_tex_path(spec)
            if tex_path.exists():
                cleaned = strip_boilerplate(tex_path.read_text(encoding="utf-8"))
                tex_path.write_text(cleaned, encoding="utf-8")
                report.actions.append("prose: stripped batch boilerplate")
            ur = upgrade_chapter(spec, dry_run=False)
            report.actions.append(
                f"prose: upgraded words {ur['words_before']}->{ur['words_after']}"
            )
        except Exception as exc:
            report.errors.append(f"prose: {exc}")

    try:
        from book_proper_nouns import fix_chapter

        n, _ = fix_chapter(spec)
        if n:
            report.actions.append(f"proper-nouns: fixed {n} issue(s)")
    except Exception as exc:
        report.errors.append(f"proper-nouns: {exc}")

    try:
        report.actions.extend(run_research(spec, skip=skip_research, dry_run=research_dry_run))
    except Exception as exc:
        report.errors.append(f"research: {exc}")

    try:
        report.actions.extend(
            run_fact_verification(
                spec,
                skip=skip_fact_verify,
                dry_run=fact_verify_dry_run,
            )
        )
    except Exception as exc:
        report.errors.append(f"facts: {exc}")

    try:
        report.actions.extend(run_reference_verify(spec))
    except Exception as exc:
        report.errors.append(f"refs: {exc}")

    try:
        report.actions.extend(run_citation_loop(spec))
    except Exception as exc:
        report.errors.append(f"citations: {exc}")

    if citation_redistribute:
        try:
            from citation_loop import merge_all_chapter_bibs, redistribute_citations_to_tex

            redist = redistribute_citations_to_tex(spec)
            report.actions.append(
                f"citations: redistributed assigned={redist.get('assigned_count', 0)} "
                f"keys={redist.get('unique_keys_in_tex', 0)}"
            )
            merge_all_chapter_bibs()
            report.actions.append("citations: merged citations_merged.bib")
        except Exception as exc:
            report.errors.append(f"citations-redistribute: {exc}")
    else:
        report.actions.append("citations: skipped redistribute (agent-safe default)")

    try:
        from book_batch_complete import strip_boilerplate
        from book_prose_upgrade import strip_template_paragraphs

        tex_path = chapter_tex_path(spec)
        cleaned = strip_template_paragraphs(strip_boilerplate(tex_path.read_text(encoding="utf-8")))
        marker = f'\\typeout{{END_CHAPTER "{spec.chapter_id}"'
        if marker in cleaned:
            head, _, tail = cleaned.partition(marker)
            cleaned = head.rstrip() + "\n\n" + marker + tail
        tex_path.write_text(cleaned, encoding="utf-8")
        report.actions.append("prose: post-citation template strip")
    except Exception as exc:
        report.errors.append(f"prose-cleanup: {exc}")

    try:
        report.actions.extend(run_visuals(spec))
    except Exception as exc:
        report.errors.append(f"visuals: {exc}")

    compile_ok = True
    if not skip_compile:
        compile_ok = compile_book()
        report.actions.append(f"compile: {'ok' if compile_ok else 'failed'}")
        if not compile_ok:
            report.errors.append("make.sh failed")

    ev = evaluate_chapter(spec, compile_ok)
    report.evaluation = ev
    report.agent_tasks = build_deep_rewrite_agent_tasks(spec, ev)
    append_results_row(ev, description="deep-rewrite")
    save_loop_state(report)
    return report

def print_status(*, pick: str = "sequential") -> None:
    progress = book_progress()
    print("=== autobooks loop status ===\n")
    print(
        f"Book progress: {progress['ready_chapters']}/{progress['outline_chapters']} "
        f"chapters ready (OUTLINE)"
    )
    if BOOK_PARTS:
        print("Parts:")
        for row in part_progress():
            print(f"  {row['part_id']}\t{row['ready']}/{row['total']}\t{row['title']}")
    if progress["all_outline_ready"]:
        print("\nAll OUTLINE chapters pass gates.\n")
    else:
        print()

    show = progress["chapters"]
    if len(show) > 12:
        for row in show[:3]:
            _print_chapter_row(row)
        print(f"  ... {len(show) - 6} more chapters ...")
        for row in show[-3:]:
            _print_chapter_row(row)
    else:
        for row in show:
            _print_chapter_row(row)

    focus = pick_focus_chapter(strategy=pick)
    print(f"\nNext focus ({pick}): {focus.chapter_id} — {focus.title}")


def _print_chapter_row(row: dict[str, Any]) -> None:
    spec = chapter_spec(row["chapter_id"])
    assert spec is not None
    exists = chapter_exists(spec)
    ev = row["evaluation"]
    gate = "ready" if row["ready"] else "open"
    line = (
        f"{row['chapter_id']}\t{gate}\tpriority={row['priority']:6.1f}\t"
        f"exists={str(exists).lower()}"
    )
    if exists:
        line += (
            f"\tcov={ev['coverage_pct']:.0f}%\twords={ev['word_count']}/"
            f"{spec.min_words}\tcites={ev['citation_count']}/{spec.min_citations}\t"
            f"q={ev['quality_score']:.1f}\tfig={ev.get('figure_count', 0)}"
        )
        if ev.get("visual_missing"):
            line += f"\tmissing_vis={len(ev['visual_missing'])}"
    print(line)


def run_step(
    *,
    chapter: str | None = None,
    skip_research: bool = False,
    research_dry_run: bool = False,
    skip_fact_verify: bool = False,
    fact_verify_dry_run: bool = False,
    skip_compile: bool = False,
    pick: str = "sequential",
) -> StepReport:
    spec = pick_focus_chapter(chapter, strategy=pick)
    progress = book_progress()
    phase = "complete" if progress["all_outline_ready"] and chapter_ready(spec) else "step"
    report = StepReport(chapter_id=spec.chapter_id, phase=phase)

    if ensure_chapter_stub(spec):
        report.actions.append(f"stub: created {spec.filename}")
    if ensure_main_input(spec):
        report.actions.append("main.tex: added chapter \\input")

    if not chapter_ready(spec):
        try:
            from book_batch_complete import complete_chapter

            cr = complete_chapter(spec)
            if cr.get("action") != "skip_ready":
                report.actions.append(
                    f"expand: {cr['action']} -> {cr.get('words', 0)} words "
                    f"(ready={cr.get('ready', False)})"
                )
        except Exception as exc:
            report.errors.append(f"expand: {exc}")

    try:
        report.actions.extend(run_research(spec, skip=skip_research, dry_run=research_dry_run))
    except Exception as exc:
        report.errors.append(f"research: {exc}")

    try:
        report.actions.extend(
            run_fact_verification(
                spec,
                skip=skip_fact_verify,
                dry_run=fact_verify_dry_run,
            )
        )
    except Exception as exc:
        report.errors.append(f"facts: {exc}")

    try:
        report.actions.extend(run_reference_verify(spec))
    except Exception as exc:
        report.errors.append(f"refs: {exc}")

    try:
        report.actions.extend(run_citation_loop(spec))
    except Exception as exc:
        report.errors.append(f"citations: {exc}")

    try:
        report.actions.extend(run_visuals(spec))
    except Exception as exc:
        report.errors.append(f"visuals: {exc}")

    compile_ok = True
    if not skip_compile:
        compile_ok = compile_book()
        report.actions.append(f"compile: {'ok' if compile_ok else 'failed'}")
        if not compile_ok:
            report.errors.append("make.sh failed")

    ev = evaluate_chapter(spec, compile_ok)
    report.evaluation = ev
    report.agent_tasks = build_agent_tasks(spec, ev)
    append_results_row(ev, description="loop-step")
    save_loop_state(report)
    return report


def print_step_report(report: StepReport) -> None:
    print(f"\n=== loop step: {report.chapter_id} ===")
    for action in report.actions:
        print(f"  • {action}")
    for err in report.errors:
        print(f"  ! {err}")

    ev = report.evaluation
    if ev:
        print("\n---")
        print(f"chapter:          {ev['chapter']}")
        print(f"coverage_pct:     {ev['coverage_pct']:.1f}")
        print(f"word_count:       {ev['word_count']}")
        print(f"citation_count:   {ev['citation_count']}")
        print(f"quality_score:    {ev['quality_score']:.1f}")
        if ev.get("visual_missing"):
            print(f"visual_missing:   {','.join(ev['visual_missing'])}")

    print("\n--- agent_tasks ---")
    for i, task in enumerate(report.agent_tasks, 1):
        print(f"  {i}. {task}")
    print(f"\nState: {STATE_JSON}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Autobooks full-book iteration loop")
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status")
    status_p.add_argument("--pick", choices=("sequential", "weakest"), default="sequential")

    step_p = sub.add_parser("step")
    step_p.add_argument("--chapter")
    step_p.add_argument("--skip-research", action="store_true")
    step_p.add_argument("--research-dry-run", action="store_true")
    step_p.add_argument("--skip-fact-verify", action="store_true")
    step_p.add_argument("--fact-verify-dry-run", action="store_true")
    step_p.add_argument("--skip-compile", action="store_true")
    step_p.add_argument(
        "--pick",
        choices=("sequential", "weakest"),
        default="sequential",
        help="Focus chapter when --chapter omitted (default: sequential OUTLINE order)",
    )

    run_p = sub.add_parser("run")
    run_p.add_argument("--max-steps", type=int, default=3)
    run_p.add_argument("--chapter")
    run_p.add_argument("--skip-research", action="store_true")
    run_p.add_argument("--research-dry-run", action="store_true")
    run_p.add_argument("--skip-fact-verify", action="store_true")
    run_p.add_argument("--fact-verify-dry-run", action="store_true")
    run_p.add_argument("--skip-compile", action="store_true")
    run_p.add_argument("--pick", choices=("sequential", "weakest"), default="sequential")
    run_p.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Machine phases only (research/visuals/stub); no expectation of prose improvement",
    )

    dr_p = sub.add_parser(
        "deep-rewrite",
        help="Single-chapter deep rewrite loop (prose scaffold + cite/fact/compile + agent brief)",
    )
    dr_p.add_argument("--chapter", required=True, help="e.g. ch14")
    dr_p.add_argument("--skip-research", action="store_true")
    dr_p.add_argument("--research-dry-run", action="store_true")
    dr_p.add_argument("--skip-fact-verify", action="store_true")
    dr_p.add_argument("--fact-verify-dry-run", action="store_true")
    dr_p.add_argument(
        "--skip-prose",
        action="store_true",
        help="Skip book_prose_upgrade machine scaffold",
    )
    dr_p.add_argument("--skip-compile", action="store_true")
    dr_p.add_argument(
        "--citation-redistribute",
        action="store_true",
        help="Run citation redistribute (can inject template filler; off by default)",
    )

    ins_p = sub.add_parser("insert-visuals")
    ins_p.add_argument("--chapter")
    ins_p.add_argument("--all", action="store_true")

    sub.add_parser("audit", help="Run book_spec_audit.py against Chinese spec")

    pn_p = sub.add_parser("check-proper-nouns", help="Scan/fix canonical term capitalization (ch01–ch27)")
    pn_p.add_argument("--chapter")
    pn_p.add_argument("--all", action="store_true")
    pn_p.add_argument("--fix", action="store_true")

    rv_p = sub.add_parser(
        "verify-references",
        help="Score bib citations vs content keywords (ch01–ch27)",
    )
    rv_p.add_argument("--chapter")
    rv_p.add_argument("--all", action="store_true")
    rv_p.add_argument(
        "--min-citation-score", type=int, default=8,
    )

    cl_p = sub.add_parser(
        "citation-loop",
        help="Per-chapter citation plan + strict verify (>=25 papers)",
    )
    cl_p.add_argument("--chapter")
    cl_p.add_argument("--all", action="store_true")
    cl_p.add_argument("--dry-run", action="store_true")
    cl_p.add_argument("--min-papers", type=int, default=25)
    cl_p.add_argument(
        "--verify-only", action="store_true", help="Skip plan, run strict verify only"
    )
    cl_p.add_argument(
        "--apply-tex",
        action="store_true",
        help="After strict pass, write \\citep from citation_bindings.jsonl",
    )
    cl_p.add_argument(
        "--merge-bib",
        action="store_true",
        help="Merge all chapter.bib into books/citations_merged.bib",
    )
    cl_p.add_argument("--crossref-only", action="store_true")

    args = parser.parse_args()

    if args.command == "status":
        print_status(pick=args.pick)
        return 0

    if args.command == "deep-rewrite":
        report = run_deep_rewrite(
            chapter=args.chapter,
            skip_research=args.skip_research,
            research_dry_run=args.research_dry_run,
            skip_fact_verify=args.skip_fact_verify,
            fact_verify_dry_run=args.fact_verify_dry_run,
            skip_prose=args.skip_prose,
            skip_compile=args.skip_compile,
            citation_redistribute=args.citation_redistribute,
        )
        print_step_report(report)
        return 0 if not report.errors else 1

    if args.command == "insert-visuals":
        if not args.chapter and not args.all:
            print("Specify --chapter <id> or --all", file=sys.stderr)
            return 1
        if args.all:
            targets = OUTLINE
        else:
            spec = chapter_spec(args.chapter)
            if not spec:
                return 1
            targets = (spec,)
        total = 0
        for spec in targets:
            cmd_plan(spec.chapter_id)
            cmd_render(spec.chapter_id, None)
            n = insert_missing_visuals(spec)
            print(f"{spec.chapter_id}: inserted {n} visual(s)")
            total += n
        print(f"Total inserted: {total}")
        return 0

    if args.command == "step":
        report = run_step(
            chapter=args.chapter,
            skip_research=args.skip_research,
            research_dry_run=args.research_dry_run,
            skip_fact_verify=args.skip_fact_verify,
            fact_verify_dry_run=args.fact_verify_dry_run,
            skip_compile=args.skip_compile,
            pick=args.pick,
        )
        print_step_report(report)
        return 0 if not report.errors else 1

    if args.command == "run":
        code = 0
        touched: set[str] = set()
        for i in range(args.max_steps):
            print(f"\n######## run {i + 1}/{args.max_steps} ########")
            chapter_arg = args.chapter
            if args.bootstrap_only and not chapter_arg:
                remaining = [s.chapter_id for s in OUTLINE if s.chapter_id not in touched]
                if not remaining:
                    print("\nBootstrap: all OUTLINE chapters touched.")
                    break
                chapter_arg = remaining[0]

            report = run_step(
                chapter=chapter_arg,
                skip_research=args.skip_research,
                research_dry_run=args.research_dry_run,
                skip_fact_verify=args.skip_fact_verify,
                fact_verify_dry_run=args.fact_verify_dry_run,
                skip_compile=args.skip_compile,
                pick=args.pick,
            )
            print_step_report(report)
            touched.add(report.chapter_id)
            if report.errors:
                code = 1
            if args.bootstrap_only and not args.chapter and len(touched) >= len(OUTLINE):
                print("\nBootstrap: all OUTLINE chapters touched.")
                break
            if report.phase == "complete":
                print("\nAll OUTLINE chapters ready.")
                break
        return code

    if args.command == "citation-loop":
        from citation_loop import (
            apply_citation_bindings_to_tex,
            merge_all_chapter_bibs,
            resolve_specs as cite_specs,
            run_chapter_citation_plan,
            strict_verify_chapter_citations,
        )

        if not args.chapter and not args.all:
            print("Specify --chapter or --all", file=sys.stderr)
            return 1
        specs = cite_specs(args.chapter if not args.all else None)
        if not args.verify_only:
            for spec in specs:
                run_chapter_citation_plan(
                    spec,
                    dry_run=args.dry_run,
                    min_papers=args.min_papers,
                    crossref_only=getattr(args, "crossref_only", False),
                )
        fails = 0
        for spec in specs:
            report = strict_verify_chapter_citations(
                spec, min_papers=args.min_papers
            )
            rel = (
                RESEARCH_ROOT / spec.chapter_id / "citation_strict_report.json"
            ).relative_to(ROOT)
            print(
                f"{spec.chapter_id}: {report['status']} "
                f"papers={report['catalog_count']} "
                f"bindings={report['binding_count']} -> {rel}"
            )
            if report["status"] != "pass":
                fails += 1
        if fails:
            return 1
        if args.apply_tex and not args.dry_run:
            for spec in specs:
                r = apply_citation_bindings_to_tex(spec)
                print(
                    f"{spec.chapter_id}: applied {r['cites_applied']} cites "
                    f"updated={r['updated']}"
                )
        if args.merge_bib and not args.dry_run:
            m = merge_all_chapter_bibs()
            print(f"merged {m['entry_count']} entries -> {m['output']}")
        return 0

    if args.command == "verify-references":
        from research_tools import verify_chapter_references

        if not args.chapter and not args.all:
            print("Specify --chapter <id> or --all", file=sys.stderr)
            return 1
        specs = tuple(
            s for s in OUTLINE if not args.chapter or s.chapter_id == args.chapter
        )
        if args.chapter and not specs:
            print(f"Unknown chapter: {args.chapter}", file=sys.stderr)
            return 1
        warn = 0
        for spec in specs:
            report = verify_chapter_references(
                spec, min_citation_score=args.min_citation_score
            )
            rel = (
                RESEARCH_ROOT / spec.chapter_id / "reference_verify_report.json"
            ).relative_to(ROOT)
            print(
                f"{spec.chapter_id}: {report['status']} — "
                f"{report['citation_count']} cites, {report['keyword_count']} keywords "
                f"-> {rel}"
            )
            if report["status"] != "ok":
                warn += 1
        return 1 if warn else 0

    if args.command == "check-proper-nouns":
        from book_proper_nouns import main as proper_nouns_main

        argv = ["book_proper_nouns.py"]
        if args.all:
            argv.append("--all")
        elif args.chapter:
            argv.extend(["--chapter", args.chapter])
        else:
            argv.append("--all")
        if args.fix:
            argv.append("--fix")
        sys.argv = argv
        return proper_nouns_main()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
