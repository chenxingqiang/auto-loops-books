#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [[ "${1:-}" == "--all" ]]; then
  python3 ../book_prepare.py --compile-all-chapters --verbose-compile
elif [[ "${1:-}" == "--list" ]]; then
  python3 ../book_prepare.py --list
elif [[ -n "${1:-}" ]]; then
  python3 ../book_prepare.py --chapter "$1" --verbose-compile
else
  cat >&2 <<'EOF'
Usage:
  bash make-chapter.sh ch01          # standalone → books/pdf/ch01.pdf
  bash make-chapter.sh --all         # build pdf/ch01.pdf … pdf/ch30.pdf
  bash make-chapter.sh --list        # list chapter ids

From repo root:
  python3 book_prepare.py --chapter ch01
  python3 book_prepare.py --compile-all-chapters
EOF
  exit 1
fi
