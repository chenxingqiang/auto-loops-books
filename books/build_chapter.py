#!/usr/bin/env python3
"""Build standalone PDF per chapter or sync/compile main.tex."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book_prepare import BOOKS, CHAPTERS, OUTLINE, ChapterSpec, sync_main_tex_inputs  # noqa: E402

PDF_DIR = BOOKS / "pdf"
BUILD_DIR = BOOKS / "build"


def chapter_by_id(chapter_id: str) -> ChapterSpec | None:
    for spec in OUTLINE:
        if spec.chapter_id == chapter_id:
            return spec
    return None


def existing_chapters() -> list[ChapterSpec]:
    return [s for s in OUTLINE if (CHAPTERS / s.filename).exists()]


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

\\input{{chapters/{spec.filename}}}

\\small{{
\\bibliography{{book}}
\\bibliographystyle{{natbib}}
\\clearpage
}}
\\printindex

\\end{{document}}
""",
        encoding="utf-8",
    )
    return target


def compile_stem(stem: str) -> bool:
    env = os.environ.copy()
    env["BOOK"] = stem
    proc = subprocess.run(
        ["bash", "make.sh"],
        cwd=BOOKS,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env=env,
    )
    pdf_src = BOOKS / f"{stem}.pdf"
    if not pdf_src.exists():
        tail = (proc.stdout or "") + (proc.stderr or "")
        if tail.strip():
            print(tail[-5000:], file=sys.stderr)
        return False
    if stem != "main":
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        dest = PDF_DIR / f"{stem}.pdf"
        dest.write_bytes(pdf_src.read_bytes())
        print(f"Wrote {dest}")
    else:
        print(f"Wrote {pdf_src}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build chapter PDFs and/or main.pdf")
    parser.add_argument("--chapter", help="chapter id, e.g. ch01")
    parser.add_argument("--all-chapters", action="store_true")
    parser.add_argument("--sync-main", action="store_true")
    parser.add_argument("--main", action="store_true")
    args = parser.parse_args()

    default = not (args.chapter or args.all_chapters or args.main or args.sync_main)

    if args.sync_main or default:
        synced = sync_main_tex_inputs()
        print(f"synced main.tex: {', '.join(synced) or '(none)'}")

    if args.main or default:
        if not compile_stem("main"):
            return 1

    if args.all_chapters:
        ok = True
        for spec in existing_chapters():
            tex = write_standalone_tex(spec)
            if not compile_stem(spec.chapter_id):
                ok = False
        return 0 if ok else 1

    if args.chapter:
        spec = chapter_by_id(args.chapter)
        if not spec:
            print(f"unknown chapter: {args.chapter}", file=sys.stderr)
            return 1
        write_standalone_tex(spec)
        return 0 if compile_stem(spec.chapter_id) else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
