#!/usr/bin/env bash
# Full pipeline: data, analysis, figures, notebooks, reports, tests.
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/download_data.py
# Retail sales comes from ALFRED and needs the owner's free FRED API key in
# the environment (or the project .env). Without a key the step is skipped
# and the analysis runs on the already-downloaded retail file if present.
if [ -n "${FRED_API_KEY:-}" ] || [ -f .env ]; then
  python scripts/download_data.py --alfred
fi
python scripts/run_analysis.py
python scripts/make_figures.py
python scripts/make_notebooks.py
python scripts/execute_notebooks.py
python scripts/make_reports.py
python -m pytest tests -q
python -m ruff check src scripts tests
