#!/usr/bin/env bash
# Fit cover.pdf to book trim (7in x 9in). Run from books/ after replacing cover art.
set -euo pipefail
src="${1:-cover.pdf}"
tmp="$(mktemp -t cover.XXXXXX.pdf)"
cp "$src" "$tmp.bak"
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dNOPAUSE -dQUIET -dBATCH \
  -dFIXEDMEDIA -dPDFFitPage \
  -dDEVICEWIDTHPOINTS=504 -dDEVICEHEIGHTPOINTS=648 \
  -sOutputFile="$tmp" "$tmp.bak"
mv "$tmp" "$src"
rm -f "$tmp.bak"
pdfinfo "$src" | grep 'Page size'
