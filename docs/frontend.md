# Frontend (ElderWise + GitHubBench-Delta)

The Lovable/TanStack app lives in [`frontend/`](../frontend/). It is a **thin UI** over the FastAPI facade — no evaluator logic in the browser.

## Run locally

Terminal 1 — API:

```bash
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — UI:

```bash
cd frontend
cp .env.example .env   # if needed
npm install
npm run dev
```

Open the Vite URL (typically `http://localhost:5173`).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend origin |
| `VITE_DEFAULT_EXPERIMENT_ID` | `exp_6afa2ce533ba4e0a` | Experiment used by pages |

Backend CORS: `GITHUBBENCH_CORS_ORIGINS` (see [api.md](api.md)).

## API surface used by the UI

- `GET /health`
- `POST /assessment`
- `POST /evaluate`
- `POST /trust`
- `POST /memorization`

Client: [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts).

## What remains synthetic

Patients, conversation transcript, demo timeline, and research-insight copy are **labeled narrative** only (`SyntheticBadge`). They are not evaluator claims.

## Related

- [INTEGRATION_REPORT.md](../INTEGRATION_REPORT.md)
- [API reference](api.md)
