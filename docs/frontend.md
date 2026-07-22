# Frontend (ElderWise + GitHubBench-Delta)

Thin UI over the FastAPI facade — no evaluator logic in the browser.

## Workflow

1. **`/setup`** — pick agent (`minicpm` / `claude` / `codex`)
2. **Generate synthetic data** — `POST /cases/generate-patients` via **Gemini** (Singaporean-style names, diverse medical issues). Each generate **appends** to the session cohort (3 → 6 → 9…); you land on **`/patients`** immediately
3. **Synthetic Patients** — cohort grouped by **generation calendar day** (`DD/MM/YYYY`)
   - **evaluate this day** — live `POST /cases/run` for every patient that day (prefer cache); day aggregate (mean TrustScore + metrics) stored in sessionStorage
   - **Compare days** — pick two days and see live TrustScore delta (“today vs yesterday”)
4. Pick a patient → **Patient Dashboard** — Conversation always visible; live sections use **run live evaluation**

Sidebar: **Setup · Synthetic Patients · Patient Dashboard**. Legacy paths redirect to `/#section`.

- Gemini = synthetic patient generation only (not judge, not agent under test)
- Research Insights / day means = derived from live case-run outputs only (never fabricated)
- Failed agent/provider runs → `insufficient_data` (excluded from day means)

## Run locally

```bash
# API (set GEMINI_API_KEY in .env)
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000

# UI
cd frontend && npm run dev
```

Open `/setup` first.

## Environment

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Backend origin |
| `GEMINI_API_KEY` | Required for Generate |
| `GEMINI_MODEL` | Default `gemini-2.5-flash` |
| `GITHUBBENCH_CASE_AGENT` | Fallback if `agent_id` omitted |
| `GITHUBBENCH_CASE_DRY_RUN` | Offline gold dry-run |

## API used

- `GET /cases/agents`
- `POST /cases/generate-patients`
- `POST /cases/run` (+ `loop_engineering` in response)
- Facade `/assessment` `/evaluate` `/trust` `/memorization`
- Healthcare layer (event-driven): `POST /healthcare/assess` (LLM RGA) then `GET /healthcare/report/{id}`; optional direct `POST /healthcare/evaluate`

## Engineering vs Healthcare on the dashboard

The patient dashboard shows two distinct evaluation layers. Both start only after **run live evaluation** (no precomputed healthcare placeholders):

| Section | Source | Meaning |
|---------|--------|---------|
| **Engineering Evaluation** | Live `POST /cases/run` | GitHubBench metrics / loop engineering |
| **Healthcare Evaluation** | `POST /healthcare/assess` then `GET /healthcare/report/{id}` | Live LLM Rapid Geriatric Assessment → completeness, findings, safety, review |

Before live run, Healthcare shows: “Healthcare evaluation has not been run yet.” Completeness reflects LLM extraction quality only (incomplete → lower ratio). See [healthcare_evaluation.md](healthcare_evaluation.md).

## Related

- [INTEGRATION_REPORT.md](../INTEGRATION_REPORT.md)
- [API reference](api.md)
- [Healthcare Evaluation Layer](healthcare_evaluation.md)
