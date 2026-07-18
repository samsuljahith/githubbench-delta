# Self-study map (Day 4 — read only)

Use this as a checklist while you read the code **without Cursor**. Write your own notes beside each line.

## Execution flow

```text
CLI (src/githubbench_delta/cli.py)
  → ExperimentRunner (pipeline/experiment.py)
    → Agent.run_task (agents/minicpm.py | claude.py | codex.py)
    → EvaluationEngine (metrics/engine.py) × 18 metrics
    → ResultStore (storage/results/*) → results/experiments/<id>/
  → Dashboard reads artifacts (dashboard/repository.py)
  → Reports read artifacts (reports/builder.py)
```

## Phase boundaries

| Phase | Where it “starts / ends” |
|-------|--------------------------|
| 1–2 Agents/tools | `agents/`, `tools/`, `trajectory/`, `observability/` |
| 3–3.5 Datasets | `tasks/`, `datasets/`, `benchmark/`, `datasets/v1` |
| 4 Metrics | `metrics/` + `configs/metrics.yaml` |
| 5 Pipeline | `pipeline/`, `storage/results/` |
| 6 Dashboard | `dashboard/`, `api/app.py` |
| 7 Reports | `reports/` |
| 8 Hardening | `.github/`, Docker, docs, examples |

## Folder pass (one sentence each)

Fill in while reading:

| Package | Purpose (your words) | Key class |
|---------|----------------------|-----------|
| `core` | | |
| `agents` | | |
| `tools` | | |
| `trajectory` | | |
| `observability` | | |
| `tasks` | | |
| `datasets` | | |
| `prompts` | | |
| `benchmark` | | |
| `metrics` | | |
| `pipeline` | | |
| `storage` | | |
| `dashboard` | | |
| `reports` | | |
| `api` | | |
| `cli` | | |

## 18 metrics (name them from memory)

Groups: correctness · trajectory · safety · grounding · reliability · efficiency

1. …
2. …

## Architecture decisions to explain tomorrow

- Why deterministic metrics (no LLM judge)?
- Why dry-run exists?
- Why dashboard/reports are read-only over artifacts?
- Why ResultStore is JSON + SQLite?
- Trade-off: reports currently import dashboard aggregations

## Demo checklist

- [ ] Open `docs/assets/example-report/*.html` in browser
- [ ] `uvicorn … --host 127.0.0.1 --port 8000` → show screenshots pages live
- [ ] Show `docs/assets/example-benchmark/leaderboard.csv`
- [ ] Narrate CLI → runner → metrics → store → dashboard
