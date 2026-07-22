# Integration Report — ElderWise Frontend + GitHubBench-Delta

## Summary

Integrated the Lovable ElderWise React app as a **thin UI** under `frontend/` against the existing Python package in `src/githubbench_delta/` (no package relocation). Added a FastAPI facade (`POST /assessment`, `/evaluate`, `/trust`, `/memorization` + existing `GET /health`) with CORS, env-based API URLs, loading/error states, and an honesty rule: **no fabricated evaluator numbers**.

## Architecture

```text
frontend/  (TanStack Start + Vite)
  src/lib/api.ts          → VITE_API_BASE_URL
  routes/*                → loading / error / insufficient_data UI

src/githubbench_delta/
  api/app.py              → CORS + mount facade
  api/facade.py           → thin wrappers
  dashboard/repository.py → evaluation_results.json
  memorization/engine.py  → MDS
```

Backend remains the single source of truth. The UI does not reimplement metrics, MDS, or ranking logic.

## Endpoint map

| Frontend call | Backend | Provenance |
|---------------|---------|------------|
| `getHealth()` | `GET /health` | Package version |
| `postAssessment()` | `POST /assessment` | Mean `evaluation.group_scores` → domains 0–5 |
| `postEvaluate()` | `POST /evaluate` | Mean per-metric scores → `%` |
| `postTrust()` | `POST /trust` | Equal-weight mean of group_scores × 100 |
| `postMemorization()` | `POST /memorization` | `MemorizationEngine.analyze` |

Missing experiment / empty rows → `{ ok: false, status: "insufficient_data", data: null }`.

## Data provenance vs synthetic chrome

| Surface | Source |
|---------|--------|
| Assessment / Evaluation / TrustScore / Benchmark metrics | Live facade APIs |
| Dashboard TrustScore + metric snapshot | Live APIs |
| Patients, conversation, demo timeline, insights copy | Labeled synthetic narrative only |
| Fabricated baseline competitor rows | Removed from Benchmark |

## How to run

```bash
# API
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000

# UI
cd frontend && npm install && npm run dev
```

Env: see `.env.example`, `frontend/.env.example`.

## Tests

```bash
.venv/bin/pytest tests/unit/test_api_facade.py -q
```

Covers health, live evaluate/assessment/trust when `exp_6afa2ce533ba4e0a` artifacts exist, insufficient_data, memorization envelope.

## Limitations

- Trust composite is equal-weight `group_scores` (full TrustScore package not restored from incomplete stash).
- Assessment domains are metric-group mappings, not a clinical RGA model.
- Patients/conversation remain demo narrative.
- Default experiment must exist under `results/experiments/` for happy-path UI.

## Future work

- Restore dedicated TrustScore engine and point `POST /trust` at it.
- Optional agent picker in the UI (`agent_id` already supported by the facade).
- Serve SPA from FastAPI in production compose.

## Related docs

- [docs/frontend.md](docs/frontend.md)
- [docs/api.md](docs/api.md)
