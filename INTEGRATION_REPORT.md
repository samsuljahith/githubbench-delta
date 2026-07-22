# Integration Report — ElderWise Frontend + GitHubBench-Delta

## Summary

Setup wizard: **pick agent → Gemini-generate (appends cohort) → Synthetic Patients by day → Patient Dashboard**. Day-level **evaluate this day** + day-vs-day compare use live `POST /cases/run` aggregates only. Scores from `ExperimentRunner` + deterministic evaluators. Failed agent runs are not cached as success.

## Flow

```text
/setup agent → POST /cases/generate-patients (Gemini, append cohort)
           → /patients (group by generation day)
           → evaluate this day → POST /cases/run per patient → day aggregate
           → compare two days (live TrustScore delta)
           → /?agent=&patient= (unified dashboard)
           → run live evaluation → POST /cases/run
           → sections: conversation chrome + assessment / evaluate / trust / benchmark / insights
```

## Endpoints

| Call | Role |
|------|------|
| `GET /cases/agents` | Wizard catalog |
| `POST /cases/generate-patients` | Gemini synth chrome |
| `POST /cases/run` | Live 1-unit eval; `loop_engineering`; fail → `insufficient_data` |

## Honesty

- Patient narrative: synthetic (Gemini only — no hardcoded Margaret cohort)
- Metrics / Insights: live agent + deterministic evaluators (no fabricated insight charts)
- No LLM-as-judge; no multi-agent merge
- Provider errors (e.g. MiniCPM down) surface as errors, not fake scores

## Tests

```bash
.venv/bin/pytest tests/unit/test_api_facade.py tests/unit/test_api_cases.py tests/unit/test_api_synthetic.py -q
```

## Related

- [docs/frontend.md](docs/frontend.md)
- [docs/api.md](docs/api.md)
