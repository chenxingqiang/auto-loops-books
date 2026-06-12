#!/usr/bin/env python3
"""Selective removal of pad_agent_chapter tail blocks before Key Takeaways."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTLINE_JSON = ROOT / "outline_extended.json"
sys.path.insert(0, str(ROOT))

from book_agent_rewrite import pad_restart_index  # noqa: E402
from book_prepare import (  # noqa: E402
    CHAPTERS,
    OUTLINE,
    ChapterSpec,
    count_words,
    read_chapter_text,
    section_covered,
)

KEY_TAKEAWAYS = "\\section{Key Takeaways}"


def honest_min_words(words_after: int) -> int:
    """Round down to nearest 50, floor at 1000."""
    return max(1000, (words_after // 50) * 50)


def strip_pad_tail_block(text: str, spec: ChapterSpec) -> tuple[str, bool]:
    if KEY_TAKEAWAYS not in text:
        return text, False
    idx = text.index(KEY_TAKEAWAYS)
    before = text[:idx]
    after = text[idx:]
    cut = pad_restart_index(before, spec)
    if cut is None or cut >= len(before):
        return text, False
    cleaned = before[:cut].rstrip() + "\n\n" + after
    return cleaned, True


def audit_chapter(spec: ChapterSpec) -> dict:
    text = read_chapter_text(spec)
    words_before = count_words(text)
    cleaned, changed = strip_pad_tail_block(text, spec)
    words_after = count_words(cleaned)
    cov = sum(1 for s in spec.sections if section_covered(cleaned, s))
    honest = honest_min_words(words_after)
    safe = (not changed) or words_after >= spec.min_words
    return {
        "chapter": spec.chapter_id,
        "words_before": words_before,
        "words_after": words_after,
        "min_words": spec.min_words,
        "honest_min_words": honest,
        "changed": changed,
        "coverage": f"{cov}/{len(spec.sections)}",
        "safe": safe,
    }


def update_outline_min_words(chapter_id: str, min_words: int, *, dry_run: bool = False) -> int | None:
    if not OUTLINE_JSON.exists():
        return None
    data = json.loads(OUTLINE_JSON.read_text(encoding="utf-8"))
    old: int | None = None
    for entry in data.get("chapters", []):
        if entry.get("id") != chapter_id:
            continue
        old = int(entry["min_words"])
        entry["min_words"] = min_words
        if not dry_run:
            OUTLINE_JSON.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        return old
    return None


def apply_chapter(
    spec: ChapterSpec,
    *,
    dry_run: bool = False,
    force: bool = False,
    adjust_min: bool = False,
) -> dict:
    text = read_chapter_text(spec)
    cleaned, changed = strip_pad_tail_block(text, spec)
    words_after = count_words(cleaned)
    cov = sum(1 for s in spec.sections if section_covered(cleaned, s))
    honest = honest_min_words(words_after)
    report = {
        "chapter": spec.chapter_id,
        "words_before": count_words(text),
        "words_after": words_after,
        "min_words": spec.min_words,
        "honest_min_words": honest,
        "changed": changed,
        "coverage": f"{cov}/{len(spec.sections)}",
        "safe": (not changed) or words_after >= spec.min_words,
        "dry_run": dry_run,
        "applied": False,
    }
    if not changed:
        return report
    if words_after < spec.min_words and not force and not adjust_min:
        report["blocked"] = "below min_words (use --force or --adjust-min)"
        return report
    if adjust_min and words_after < spec.min_words:
        prev = update_outline_min_words(spec.chapter_id, honest, dry_run=dry_run)
        report["min_words_adjusted"] = f"{prev}->{honest}" if prev is not None else str(honest)
        report["safe"] = True
    elif not force and words_after < spec.min_words:
        report["blocked"] = "below min_words (use --force or --adjust-min)"
        return report
    if not dry_run:
        (CHAPTERS / spec.filename).write_text(cleaned, encoding="utf-8")
    report["applied"] = not dry_run
    return report


def specs_for_range(ch_range: str) -> list[ChapterSpec]:
    lo, hi = (int(x) for x in ch_range.split("-", 1))
    return [s for s in OUTLINE if lo <= int(s.chapter_id[2:]) <= hi]


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip duplicate pad_agent tail blocks")
    parser.add_argument("chapters", nargs="*", help="chapter ids (e.g. ch19)")
    parser.add_argument("--audit", action="store_true", help="audit chapter range")
    parser.add_argument("--apply", action="store_true", help="write cleaned tex")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="apply even if below min_words")
    parser.add_argument(
        "--adjust-min",
        action="store_true",
        help="after strip, set outline_extended.json min_words to honest floor",
    )
    parser.add_argument("--range", dest="ch_range", default="14-27", help="audit range like 14-27")
    args = parser.parse_args()

    if args.chapters:
        want = set(args.chapters)
        specs = [s for s in OUTLINE if s.chapter_id in want]
    elif args.audit or args.apply:
        specs = specs_for_range(args.ch_range)
    else:
        parser.print_help()
        return 1

    failed = 0
    for spec in specs:
        if args.apply:
            r = apply_chapter(
                spec,
                dry_run=args.dry_run,
                force=args.force,
                adjust_min=args.adjust_min,
            )
        else:
            r = audit_chapter(spec)
        flag = "OK" if r.get("safe", True) else "LOW"
        extra = ""
        if r.get("blocked"):
            extra = f"\t{r['blocked']}"
        if r.get("min_words_adjusted"):
            extra += f"\tmin {r['min_words_adjusted']}"
        if args.apply:
            extra += f"\tapplied={r.get('applied')}"
        print(
            f"{r['chapter']}\t{flag}\tchanged={r.get('changed', False)}\t"
            f"words {r['words_before']}->{r['words_after']}/{r['min_words']}\t"
            f"cov {r['coverage']}{extra}"
        )
        if not r.get("safe", True) and not args.force and not args.adjust_min:
            failed += 1

    return 1 if failed and not args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
