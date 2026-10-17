#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python ./review_candidates_keyboard.py --mode fp --csv ./review_consensus.csv --reference-csv ./review_junior.csv --sorted-dir ./review_sorted_consensus --include-reviewed --fig-width 16 --fig-height 12 --max-display-dim 1800 --no-overview
