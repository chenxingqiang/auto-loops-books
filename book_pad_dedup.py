#!/usr/bin/env python3
"""Selective removal of pad_agent_chapter tail blocks before Key Takeaways."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
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
    safe = (not changed) or words_after >= spec.min_words
    return {
        "chapter": spec.chapter_id,
        "words_before": words_before,
        "words_after": words_after,
        "min_words": spec.min_words,
        "changed": changed,
        "coverage": f"{cov}/{len(spec.sections)}",
        "safe": safe,
    }


def apply_chapter(spec: ChapterSpec, *, dry_run: bool = False, force: bool = False) -> dict:
    text = read_chapter_text(spec)
    cleaned, changed = strip_pad_tail_block(text, spec)
    report = audit_chapter(spec)
    report["dry_run"] = dry_run
    if not changed:
        report["applied"] = False
        return report
    if not force and count_words(cleaned) < spec.min_words:
        report["applied"] = False
        report["blocked"] = "below min_words (use --force or lower min_words in outline_extended.json)"
        return report
    if not dry_run:
        (CHAPTERS / spec.filename).write_text(cleaned, encoding="utf-8")
    report["applied"] = not dry_run
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip duplicate pad_agent tail blocks")
    parser.add_argument("chapters", nargs="*", help="chapter ids (e.g. ch19)")
    parser.add_argument("--audit", action="store_true", help="audit chapter range")
    parser.add_argument("--apply", action="store_true", help="write cleaned tex")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="apply even if below min_words")
    parser.add_argument("--range", dest="ch_range", default="14-27", help="audit range like 14-27")
    args = parser.parse_args()

    if args.chapters:
        want = set(args.chapters)
        specs = [s for s in OUTLINE if s.chapter_id in want]
    elif args.audit or args.apply:
        lo, hi = (int(x) for x in args.ch_range.split("-", 1))
        specs = [s for s in OUTLINE if lo <= int(s.chapter_id[2:]) <= hi]
    else:
        parser.print_help()
        return 1

    failed = 0
    for spec in specs:
        if args.apply:
            r = apply_chapter(spec, dry_run=args.dry_run, force=args.force)
        else:
            r = audit_chapter(spec)
        flag = "OK" if r.get("safe", True) else "LOW"
        extra = ""
        if r.get("blocked"):
            extra = f"\t{r['blocked']}"
        if args.apply:
            extra += f"\tapplied={r.get('applied')}"
        print(
            f"{r['chapter']}\t{flag}\tchanged={r.get('changed', False)}\t"
            f"words {r['words_before']}->{r['words_after']}/{r['min_words']}\t"
            f"cov {r['coverage']}{extra}"
        )
        if not r.get("safe", True) and not args.force:
            failed += 1

    return 1 if failed and not args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
