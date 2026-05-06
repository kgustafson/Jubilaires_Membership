#!/usr/bin/env bash
set -euo pipefail

DOCX_PATH="${1:-/Users/kurtgustafson/Downloads/ChapterMembership2026.docx}"
textutil -convert txt -stdout "$DOCX_PATH"
