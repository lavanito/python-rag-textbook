#!/usr/bin/env bash
# Extract text from the source PDFs so the corpus can be checked against them.
# Usage: tools/extract_text.sh /path/to/rag_corpus_sources
# Writes plain and layout text to data/raw/text/ (ignored by git).
# Needs pdftotext (poppler-utils). File names must match SOURCE_FILES in build_corpus.py.
set -euo pipefail
SRC="${1:?give the folder holding the source PDFs}"
OUT="$(dirname "$0")/../data/raw/text"
mkdir -p "$OUT/corpus_raw" "$OUT/corpus_text"
declare -A NAMES=(
  ["SNA2008.pdf"]="SNA2008.txt"
  ["2025_SNA_Pre-edit.pdf"]="sna25.txt"
  ["QNAManual2017text.pdf"]="QNAManual2017text.txt"
  ["9789264214637-en.pdf"]="9789264214637-en.txt"
  ["KS-02-13-269-EN.PDF.pdf"]="KS-02-13-269-EN.PDF.txt"
  ["all-chapters.pdf"]="all-chapters.txt"
  ["Modified GNI - CSO - Central Statistics Office.pdf"]="Modified GNI - CSO - Central Statistics Office.txt"
  ["KS-GQ-24-011-EN-N.pdf"]="KS-GQ-24-011-EN-N.txt"
)
for pdf in "${!NAMES[@]}"; do
  txt="${NAMES[$pdf]}"
  pdftotext "$SRC/$pdf" "$OUT/corpus_raw/$txt"
  pdftotext -layout "$SRC/$pdf" "$OUT/corpus_text/$txt"
  echo "extracted $pdf"
done
