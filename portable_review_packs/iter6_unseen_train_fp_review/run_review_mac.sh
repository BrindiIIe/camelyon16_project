#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python ./review_candidates_keyboard.py --mode fp --csv ./review_template.csv --sorted-dir ./review_sorted --fig-width 16 --fig-height 12
