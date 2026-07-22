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
| GET | `/cases/agents` | — | Agent catalog for setup wizard (minicpm / claude / codex) |
| POST | `/cases/generate-patients` | `{ count? }` | Gemini synthetic patients (1–5); requires `GEMINI_API_KEY` |
| POST | `/cases/run` | `{ patient, agent_id?, force? }` | Live 1-unit experiment; returns scores + `loop_engineering` (trajectory stats + **all** scored metrics as `related_metrics`); failed agent → `insufficient_data` |
| POST | `/assessment` | `{ experiment_id?, agent_id? }` | Domains from mean `group_scores` (0–5) |
| POST | `/evaluate` | `{ experiment_id?, agent_id? }` | Per-metric means as `%` plus deterministic `reasoning` / `evidence` / `suggested_improvements` from latest `metric_results` (not LLM-as-judge) |
| POST | `/trust` | `{ experiment_id?, agent_id? }` | Equal-weight composite 0–100 + breakdown |
| POST | `/memorization` | `{ experiment_ids?, experiment_id?, twins_path? }` | MDS report JSON |

Case runs: `agent_id` overrides `GITHUBBENCH_CASE_AGENT`. Cache only on successful agent runs (`results/cases/{patient_id}__{agent_id}.json`). Gemini is for synthetic chrome only — not judging.

Envelope:

```json
{ "ok": true, "status": "ok", "experiment_id": "…", "data": { } }
```

or

```json
{ "ok": false, "status": "insufficient_data", "detail": "…", "data": null }
```

See [Frontend](frontend.md) and [INTEGRATION_REPORT.md](../INTEGRATION_REPORT.md).

## Healthcare evaluation (additive)

Event-driven: live LLM RGA from conversation, then rule checks. Separate from the 18 engineering metrics and from `/cases/run` scoring. Details: [Healthcare Evaluation Layer](healthcare_evaluation.md).

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/healthcare/assess` | `{ patient?, transcript?, conversation? }` | LLM extract RGA → persist → evaluate; returns `assessment_id` + `report_id` |
| POST | `/healthcare/evaluate` | `{ patient?, clinical_output?, transcript?, review_status? }` | Rule engine only on supplied evidence |
| GET | `/healthcare/report/{id}` | — | Load stored report; missing → `insufficient_data` |

Requires `OPENAI_API_KEY` or `MINICPM_BASE_URL`. Empty transcript / no LLM / empty extraction → `insufficient_data` (no fabricated scores).

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
