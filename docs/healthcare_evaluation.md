# Healthcare Evaluation Layer

Additive clinical layer: **live LLM Rapid Geriatric Assessment (RGA)** from conversation, then rule-based completeness / findings / safety / review. This package does **not** score GitHub engineering tasks and does **not** invent clinical scores from experiment artifacts or Gemini patient chrome.

## How this differs from GitHubBench

| Layer | What it evaluates | Source of truth |
|-------|-------------------|-----------------|
| **GitHubBench (18 metrics)** | Coding-agent trajectories on GitHub tasks | Experiment artifacts under the metrics registry |
| **Healthcare Evaluation Layer** | Clinical completeness, critical findings, safety **warnings**, human review | **Live LLM RGA** (`POST /healthcare/assess`) then rule engine |

- GitHubBench remains the engineering benchmark. Its formulas, YAML registry, and `/cases/run` path are unchanged.
- Gemini is for synthetic patient chrome only — **not** the RGA extractor.
- This is **not** a diagnostic system and **not** a substitute for clinician judgment or for the 18 engineering metrics.

## Event-driven workflow

1. User selects a synthetic patient → conversation chrome only; **no** healthcare metrics yet.
2. User clicks **Run Live Evaluation**.
3. `POST /healthcare/assess` sends the conversation to the configured LLM (OpenAI if `OPENAI_API_KEY`, else MiniCPM via `MINICPM_BASE_URL`).
4. LLM returns structured RGA fields (omit domains not supported by the transcript — never fabricate).
5. Assessment is stored under `results/healthcare/assessments/`.
6. Rule engine runs on **only** that `clinical_output` → report under `results/healthcare/`.
7. UI refreshes via `GET /healthcare/report/{id}`.

Incomplete LLM extraction → lower Clinical Completeness. Full RGA domains → completeness approaches 100%.

## LLM configuration

| Env | Role |
|-----|------|
| `OPENAI_API_KEY` | Prefer OpenAI Chat Completions for RGA extract |
| `HEALTHCARE_ASSESS_MODEL` | Model override (default `gpt-4o-mini` on OpenAI) |
| `MINICPM_BASE_URL` / `MINICPM_API_KEY` / `MINICPM_MODEL` | Fallback local OpenAI-compatible endpoint |

If neither OpenAI nor MiniCPM base URL is configured → `insufficient_data` (no fake RGA).

## What the rule engine evaluates

1. **Clinical Completeness** — present vs required RGA fields from the live assessment.
2. **Missing Critical Findings** — keyword heuristics on extracted narrative/fields.
3. **Clinical Safety Rules** — warnings only.
4. **Human Review Status** — `pending` | `approved` | `needs_review`.

### Required RGA fields

`chief_complaint`, `falls_history`, `weight_change`, `medications`, `cognition`, `mood`, `mobility`, `adls_iadls`, `living_situation`, `social_support`, `comorbidities`, `risk_flags`.

## API

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/healthcare/assess` | Live LLM RGA from `transcript` / `conversation` → persist assessment → evaluate → return `assessment_id` + `report_id` |
| `POST` | `/healthcare/evaluate` | Rule engine only on caller-supplied `clinical_output` (no LLM) |
| `GET` | `/healthcare/report/{id}` | Load stored report; `insufficient_data` if missing |

Envelope: `ok`, `status`, `detail`, `data`.

## Package layout

```text
src/githubbench_delta/healthcare_evaluation/
  models.py
  rga_extract.py
  assess.py
  completeness.py
  critical_findings.py
  safety_rules.py
  review.py
  engine.py
  store.py
  api.py
```

See also [API reference](api.md).
