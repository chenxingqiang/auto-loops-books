#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [[ "${1:-}" == "--all" ]]; then
  uv run python build_chapter.py --all-chapters --sync-main
elif [[ -n "${1:-}" ]]; then
  uv run python build_chapter.py --chapter "$1" --sync-main
else
  echo "Usage: bash make-chapter.sh ch01 | --all" >&2
  exit 1
fi
