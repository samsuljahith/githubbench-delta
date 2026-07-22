# API Reference

Start the server:

```bash
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload
```

CORS origins (comma-separated): `GITHUBBENCH_CORS_ORIGINS` (default `http://localhost:5173,http://127.0.0.1:5173`).

Default experiment for facade bodies that omit `experiment_id`: `GITHUBBENCH_DEFAULT_EXPERIMENT` (default `exp_6afa2ce533ba4e0a`).

## Core endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/metrics/catalog` | Methodology metric catalog JSON |

## Frontend facade (ElderWise React)

Thin wrappers over `ExperimentRepository` + `MemorizationEngine`. **Never fabricate** scores — empty artifacts return `status: insufficient_data`.

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/assessment` | `{ experiment_id?, agent_id? }` | Domains from mean `group_scores` (0–5) |
| POST | `/evaluate` | `{ experiment_id?, agent_id? }` | Per-metric means as `%` |
| POST | `/trust` | `{ experiment_id?, agent_id? }` | Equal-weight composite 0–100 + breakdown |
| POST | `/memorization` | `{ experiment_ids?, experiment_id?, twins_path? }` | MDS report JSON |

Envelope:

```json
{ "ok": true, "status": "ok", "experiment_id": "…", "data": { } }
```

or

```json
{ "ok": false, "status": "insufficient_data", "detail": "…", "data": null }
```

See [Frontend](frontend.md) and [INTEGRATION_REPORT.md](../INTEGRATION_REPORT.md).

## Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/` | Overview UI |
| GET | `/dashboard/health` | Dashboard health |
| GET | `/dashboard/experiments` | Experiments page |
| GET | `/dashboard/leaderboard` | Leaderboard page |
| GET | `/dashboard/api/*` | REST JSON for charts/tables/export |

Details: [Dashboard](dashboard.md).

## Notes

- The dashboard is **read-only** over experiment artifacts.
- The React facade is also **read-only** (no live agent execution).
- Authentication is stubbed (anonymous viewer).
