#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent minicpm \
  --agent claude \
  --agent codex \
  --task gb-repository-search-001 \
  --trials 1 \
  --seed 42 \
  --dry-run \
  --name example-multi-agent
