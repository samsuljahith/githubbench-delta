# Synthetic patient fixtures

Versioned caregiver–coordinator conversations for reproducible ElderWise demos.

## Scenario types (exactly one each)

| `scenario_type` | Intent |
|-----------------|--------|
| `complete` | All four RGA domains clearly covered (frailty/fatigue, sarcopenia/mobility, appetite/weight, cognition) |
| `missing_finding` | Fall/near-fall casually embedded mid-anecdote; other domains covered |
| `hallucination_risk` | Caregiver uncertain about a medication name — models must not invent a drug |
| `contraindication` | Age 80+ on a Beers-Criteria medication (e.g. benzodiazepine); otherwise complete |
| `incomplete` | Only two of four RGA domains discussed |

## Files

See [`manifest.json`](manifest.json). Each file includes `id`, `scenario_type`, `patient` chrome, `conversation_text`, and structured `conversation` turns.

Load via `GET /cases/fixture-patients` (additive). Do not regenerate randomly for the Saturday demo.
