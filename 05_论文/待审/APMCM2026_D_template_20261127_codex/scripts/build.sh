#!/usr/bin/env bash
set -euo pipefail
APMCM_WORK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APMCM_TEXBIN="${APMCM_TEXBIN:-$HOME/.local/share/texlive/2026/bin/x86_64-linux}"
export PATH="$APMCM_TEXBIN:$PATH"
export BIBINPUTS="$APMCM_WORK_DIR:"
export BSTINPUTS="$APMCM_WORK_DIR:"
export SOURCE_DATE_EPOCH=1795737600
export FORCE_SOURCE_DATE=1
cd -- "$APMCM_WORK_DIR"
mkdir -p build
APMCM_JOB="${1:-main}"
APMCM_ENGINE="${APMCM_ENGINE:-xelatex}"
case "$APMCM_JOB" in
  main) APMCM_SOURCE=main.tex ;;
  style_smoke) APMCM_SOURCE=examples/style_smoke.tex ;;
  f1_smoke) APMCM_SOURCE=examples/f1_smoke.tex ;;
  *) printf 'Unknown build target: %s\n' "$APMCM_JOB" >&2; exit 2 ;;
esac
for APMCM_TOOL in "$APMCM_ENGINE" bibtex; do
  command -v "$APMCM_TOOL" >/dev/null || { printf 'Missing tool: %s\n' "$APMCM_TOOL" >&2; exit 1; }
done
"$APMCM_ENGINE" -no-shell-escape -halt-on-error -file-line-error -interaction=nonstopmode \
  -recorder -output-directory=build -jobname="$APMCM_JOB" "$APMCM_SOURCE" >"build/$APMCM_JOB.pass1.log" 2>&1
if [[ "$APMCM_JOB" != f1_smoke ]]; then
  bibtex "build/$APMCM_JOB" >"build/$APMCM_JOB.bibtex.log" 2>&1
fi
for APMCM_PASS in 2 3; do
  "$APMCM_ENGINE" -no-shell-escape -halt-on-error -file-line-error -interaction=nonstopmode \
    -recorder -output-directory=build -jobname="$APMCM_JOB" "$APMCM_SOURCE" >"build/$APMCM_JOB.pass$APMCM_PASS.log" 2>&1
done
if [[ "$APMCM_JOB" == main ]]; then
  cp -- build/main.pdf main.pdf
elif [[ "$APMCM_JOB" == f1_smoke ]]; then
  cp -- build/f1_smoke.pdf verification/f1_inclusion_smoke.pdf
fi
printf 'Compiled %s.\n' "$APMCM_JOB"
