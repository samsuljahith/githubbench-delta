# Showcase Benchmark

Published example for GitHubBench-Delta (week showcase).

## What was run

| Field | Value |
|-------|--------|
| Experiment id | `exp_3c790a482f784d21` |
| Name | `showcase-v1-6task` |
| Dataset | `datasets/v1` |
| Agents | `minicpm`, `claude`, `codex` |
| Trials | 1 |
| Seed | 42 |
| Units | 18 (6 tasks × 3 agents) |
| Mode | **Dry-run** (gold-answer synthesis) for the multi-agent comparison |

### Tasks

1. `gb-repository-search-001` (Python)
2. `gb-issue-analysis-001` (Python)
3. `gb-architecture-understanding-001` (Python)
4. `gb-architecture-understanding-002` (TypeScript)
5. `gb-architecture-understanding-003` (Go)
6. `gb-architecture-understanding-005` (Rust)

### Live smoke (local MiniCPM / Ollama)

| Field | Value |
|-------|--------|
| Experiment id | `exp_ac0f374eeaff4c85` |
| Agent | `minicpm` via Ollama model `llama3.2:1b` (`MINICPM_MODEL`) |
| Task | `gb-repository-search-001` |
| Mode | **Live** (no `--dry-run`) |

Claude and Codex live multi-agent runs require `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` in `.env`. Those keys were not available in the showcase environment; use the command below when keys are set.

## Reproduce

```bash
# Offline multi-agent showcase (matches published artifacts)
uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent minicpm --agent claude --agent codex \
  --task gb-repository-search-001 \
  --task gb-issue-analysis-001 \
  --task gb-architecture-understanding-001 \
  --task gb-architecture-understanding-002 \
  --task gb-architecture-understanding-003 \
  --task gb-architecture-understanding-005 \
  --trials 1 --seed 42 --concurrency 1 \
  --name showcase-v1-6task --dry-run

# Live (requires keys + Ollama)
# export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
# set MINICPM_MODEL to a pulled Ollama model
uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent minicpm --agent claude --agent codex \
  --task gb-repository-search-001 \
  --task gb-issue-analysis-001 \
  --task gb-architecture-understanding-001 \
  --task gb-architecture-understanding-002 \
  --task gb-architecture-understanding-003 \
  --task gb-architecture-understanding-005 \
  --trials 1 --seed 42 --concurrency 1 \
  --name showcase-v1-6task-live
```

Reports:

```bash
uv run githubbench report generate -e <experiment_id> -t agent_comparison -f html -f markdown -o reports/showcase
uv run githubbench report export -e <experiment_id> -f csv -o reports/showcase/leaderboard.csv
```

Dashboard (localhost only):

```bash
uv run uvicorn githubbench_delta.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

## Published assets

- Screenshots: [assets/screenshots/](assets/screenshots/)
- Example HTML/MD report: [assets/example-report/](assets/example-report/)
- Leaderboard CSV + summary: [assets/example-benchmark/](assets/example-benchmark/)

PDF export was skipped in this environment (WeasyPrint system libraries). HTML + Markdown are the published report formats.

## Honest limitations

- Multi-agent published scores are from **dry-run** (identical gold-based synthesis → same means across agents). Use them to demonstrate the pipeline, dashboard, and report UX—not as a claim of live model ranking.
- Live MiniCPM/Ollama path was verified separately on one task.
- Full 60-task × 3-agent live corpus is out of scope for this showcase.
