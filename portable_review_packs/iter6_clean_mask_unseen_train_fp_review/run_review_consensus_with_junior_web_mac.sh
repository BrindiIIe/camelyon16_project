#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python ./review_web.py --csv review_consensus.csv --reference-csv review_junior.csv --sorted-dir review_sorted_consensus --port 8765
