#!/usr/bin/env python3
"""Build standalone PDF per chapter or sync/compile main.tex."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book_prepare import (  # noqa: E402
    OUTLINE,
    CHAPTERS,
    compile_all_chapters,
    compile_book,
    compile_chapter,
    sync_main_tex_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build chapter PDFs and/or main.pdf")
    parser.add_argument("--chapter", help="chapter id, e.g. ch01")
    parser.add_argument("--all-chapters", action="store_true")
    parser.add_argument("--sync-main", action="store_true")
    parser.add_argument("--main", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    default = not (args.chapter or args.all_chapters or args.main or args.sync_main)

    if args.sync_main or default:
        synced = sync_main_tex_inputs()
        print(f"synced main.tex: {', '.join(synced) or '(none)'}")

    if args.main or default:
        if not compile_book(verbose=args.verbose):
            return 1

    if args.all_chapters:
        return 0 if compile_all_chapters(verbose=args.verbose) else 1

    if args.chapter:
        if not compile_chapter(args.chapter, verbose=args.verbose):
            return 1
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
