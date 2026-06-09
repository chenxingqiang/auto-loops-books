#!/usr/bin/env bash
set -e
TARGET="${BOOK:-main}"
if [[ -f "build/${TARGET}.tex" ]]; then
  TEX="build/${TARGET}.tex"
else
  TEX="${TARGET}.tex"
fi
rm -f "${TARGET}.aux" "${TARGET}.ind" "${TARGET}.toc" "${TARGET}.bbl" "${TARGET}.out" build/"${TARGET}.aux" 2>/dev/null || true
pdflatex -interaction=nonstopmode -jobname="${TARGET}" "${TEX}" || true
bibtex "${TARGET}" || true
makeindex "${TARGET}" 2>/dev/null || true
bibtex "${TARGET}" || true
makeindex "${TARGET}" 2>/dev/null || true
pdflatex -interaction=nonstopmode -jobname="${TARGET}" "${TEX}" || true
pdflatex -interaction=nonstopmode -jobname="${TARGET}" "${TEX}" || true
# pagebackref (hyperref) writes main.brf; one more pass stabilizes back-citations
pdflatex -interaction=nonstopmode -jobname="${TARGET}" "${TEX}" || true
test -f "${TARGET}.pdf"
