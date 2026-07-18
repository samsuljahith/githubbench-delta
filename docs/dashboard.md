# Dashboard (Phase 6)

Read-only FastAPI + Plotly explorer for completed experiment artifacts.

## Run

```bash
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload
```

Open [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/).

## Pages

| Path | Purpose |
|------|---------|
| `/dashboard/` | Overview |
| `/dashboard/experiments` | Experiment list |
| `/dashboard/experiments/{id}` | Experiment details + manifests |
| `/dashboard/leaderboard` | Sortable leaderboard |
| `/dashboard/agents` | Radar / bars / metric table |
| `/dashboard/tasks` | Task analysis + filters |
| `/dashboard/metrics` | Distributions, correlation, importance |
| `/dashboard/trajectories` | Trajectory timeline viewer |
| `/dashboard/settings` | Read-only settings |

## Data sources

- `results/experiments/{id}/experiment.json`
- `run.json`
- `evaluation_results.json`
- `trajectory.jsonl`
- optional SQLite index

No evaluation or agent execution occurs in the dashboard.

## REST API

Base: `/dashboard/api`

Key endpoints: `overview`, `experiments`, `leaderboard`, `agents/compare`, `tasks`, `metrics/summary`, `metrics/correlation`, `charts/{name}`, `export/{csv|json|markdown}`, `settings`, `ws/status` (stub).

Supports `page`, `page_size`, `sort`, `order`, and resource filters.

## Auth

`get_current_principal` currently returns an anonymous viewer. Ready for future authentication middleware.
