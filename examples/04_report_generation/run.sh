#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent codex \
  --task gb-repository-search-001 \
  --trials 1 \
  --seed 42 \
  --dry-run \
  --name example-report >/tmp/gb_example_report_run.txt

EXP_ID="$(ls -1 results/experiments | tail -n1)"
echo "Using experiment: $EXP_ID"

uv run githubbench report generate \
  -e "$EXP_ID" \
  -t ci_summary \
  -f markdown \
  -f json \
  -o reports/examples
