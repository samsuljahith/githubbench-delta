#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

uv run githubbench dataset validate datasets/v1

for task in \
  gb-repository-search-001 \
  gb-issue-analysis-001
do
  uv run githubbench experiment run \
    --dataset datasets/v1 \
    --agent codex \
    --task "$task" \
    --trials 1 \
    --seed 42 \
    --dry-run \
    --name "example-bench-${task}"
done
