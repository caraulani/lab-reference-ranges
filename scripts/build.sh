#!/bin/sh
# Regenerate every output from the archived raw sources, then run the tests.
# Needs uv. The archive lives in ../_raw (not part of this repository); see METHODS.md.
set -eu
cd "$(dirname "$0")/.."
uv run -q --with pdfplumber python -I scripts/extract_text.py
python3 -I scripts/build.py
uv run -q --with pytest --with pdfplumber pytest -q tests
# checksums for every file in the repository except SHA256SUMS itself
find . -type f ! -path './.git/*' ! -path '*/__pycache__/*' ! -path './.pytest_cache/*' ! -path './.venv/*' ! -name .DS_Store ! -name SHA256SUMS \
  | sed 's|^\./||' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS
echo "SHA256SUMS written"
