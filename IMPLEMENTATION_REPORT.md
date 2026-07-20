# Implementation Report — Half-Life Observatory (v2)

## Summary

Added an **additive** `githubbench_delta.observatory` package that records historical benchmark snapshots from existing experiment artifacts, estimates differentiation half-life / saturation trends, and ships CLI + JSON/Markdown/Plotly exports + docs. Evaluators, ResultStore schemas, and experiment artifact shapes are unchanged.

Branch: `feature/half-life-observatory`.

## Architecture

| Layer | Components |
|-------|------------|
| Ingest | `SnapshotIngestor` (`ingest.py`) reads `ExperimentRepository` evaluation + trajectory fields |
| Store | `BenchmarkHistory` — JSONL + index under `results/observatory/` |
| Math | `DecayModel`, `HalfLifeEstimator`, `TrendAnalyzer`, `RegressionDetector` |
| Export | `ObservatoryExporter` + Plotly `charts.py` |
| CLI | `githubbench observatory {ingest,analyze,trend,report,export}`; optional `--record-observatory` on `experiment run` |

History is intentionally separate from experiment directories so longitudinal analysis never mutates run artifacts.

## Design decisions

1. **Idempotent snapshots keyed by `(experiment_id, agent_id)`** — re-ingest is safe; avoids duplicate cohorts.
2. **Primary path = `observatory ingest`** — recording after `experiment run` is opt-in via `--record-observatory` (default off) so CI / dry-runs stay quiet.
3. **Log-linear least squares (numpy)** — no scipy dependency; exponential decay is transparent and deterministic.
4. **Two-model gap = max−min** — stddev of two points equals half the range with `pstdev` scaling quirks avoided by using the absolute gap when \(n=2\).
5. **Charts via existing Plotly stack** — HTML always; PNG when Kaleido is available (same pattern as publication reports).
6. **Demo assets under `docs/assets/observatory/`** — tracked synthetic history for docs/CI-friendly demos; runtime history remains gitignored.

## Math assumptions

- Differentiation \(D(t)\): contemporaneous model-score spread (stddev / pairwise gap).
- Saturation \(S(t)\): mean overall score with ceiling 1.0.
- Model: \(D(t) \approx D_0 e^{-\lambda t}\); \(t_{1/2}=\ln 2/\lambda\) iff \(\lambda>0\).
- Confidence blends \(R^2\), cohort count, span, and multi-model presence.
- Reliable half-life needs ≥3 timestamps and ≥2 models; otherwise underdetermined with confidence penalty.

## Known limitations

- A **single** experiment run cannot identify half-life (needs multi-run history).
- Cohorts are bucketed by snapshot timestamp (second precision); clock skew across machines can split cohorts.
- Exponential form is a convenience fit — real aging may be stepwise (new models, dataset revisions).
- Regression detection uses simple z/absolute thresholds; noisy short series can miss or over-flag events.
- Ingest assumes evaluation artifacts already exist; it does not re-score.

## Future extensions

- Multi-benchmark corpora (separate histories per dataset version)
- Bayesian λ with posterior half-life credible intervals
- Dashboard panels (score vs time, differentiation curve) on the FastAPI explorer
- Automatic dataset-version gating when corpus revisions reset saturation
- Per-metric-group half-lives (correctness vs trajectory vs grounding)

## Test coverage

- `tests/unit/test_observatory_history.py` — history idempotency, decay recovery, estimator, trends, regression, exporter, CLI
- `tests/unit/test_observatory_ingest.py` — ingest from minimal fixtures, decay edge cases

No live LLM calls.

## Docs touchpoints

- [`docs/observatory.md`](docs/observatory.md)
- Links from [`docs/index.md`](docs/index.md), [`docs/cli.md`](docs/cli.md), README Documentation table
- Demo: [`docs/assets/observatory/`](docs/assets/observatory/)
