# Implementation Report — Research Execution Platform

## Summary

Added an **additive** `githubbench_delta.research` package that turns GitHubBench-Delta into a reproducibility-focused research execution layer: YAML experiment registry, numpy-only stats/power tools, artifact/repro/publication exporters, and a validation dashboard. Metrics, evaluators, ResultStore writers, and `experiment.json` / `evaluation_results.json` shapes are unchanged. **No fabricated** scores, p-values, CIs, or publication tables.

Branch: `feature/research-execution` (from `feature/memorization-discounted-scoring`).

## Architecture

```text
configs/research/experiments/*.yaml  →  ExperimentRegistry
configs/research/evidence_registry.yaml → ValidationDashboard
ExperimentScheduler → ReadinessStatus
ExperimentArtifactManager / ReproducibilityPackage / PublicationExporter → results/research/
StatisticalAnalysis (stats.py) + Power estimators → StatResult / PowerEstimate
CLI: githubbench research …
```

| Module | Responsibility |
|--------|----------------|
| `models.py` | Pydantic: experiments, manifests, readiness, `StatResult` |
| `registry.py` | Auto-load YAML + optional Python plugins |
| `plugins.py` | `@register_experiment` / `@experiment_plugin` |
| `scheduler.py` | Runnable / blocked / pending from evidence + probes |
| `stats.py` | Bootstrap, permutation, rank tests, BH-FDR, effect sizes |
| `power.py` | Sample size / MDE / variance from pilot arrays |
| `artifacts.py` | Manifest, metadata, summary |
| `repro.py` | Environment / deps / config / seeds package |
| `publish.py` | CSV/TeX/figures from **real** aggregates only |
| `dashboard.py` | `validation_report.html` |
| `cli.py` | Typer subcommands |

## Design decisions

1. **YAML-first registration** — new experiments are new files; CLI never lists them manually.
2. **Honesty over completeness** — `insufficient_data` instead of placeholder statistics.
3. **Numpy only** — Normal/rank approximations documented where exact scipy tables would apply.
4. **Does not run agents** — orchestrates manifests and reads existing artifacts.
5. **Evidence registry** — machine-readable mirror of `docs/research_evidence_gaps.md`.
6. **Seed E0–E10** — runnable limited claims (E0*) vs blocked publishable campaigns (E1–E10).

## Extension points

- Drop `configs/research/experiments/<id>.yaml`
- Optional module under `research/experiments/` with `@experiment_plugin`
- Update `evidence_registry.yaml` node `status` when real evidence lands
- Call `stats.*` / `power.*` from notebooks with real arrays

## Limitations

- Rank tests are approximate (no exact Wilcoxon/MWU tables without scipy).
- Power uses z-based Normal formulas (not t-power).
- Filesystem probes for evidence are conservative heuristics; YAML status is authoritative.
- Publication exporter only understands common evaluation JSON aggregate shapes.
- Runnable E0* demos remain **limited claims** until blocked evidence nodes are filled.

## Future work

- Wire multi-trial `trial_count` probes into scheduler for node `M`
- Optional Plotly figure writers when real series exist
- CI job that regenerates `validation_report.html` and fails on accidental fabricated tables

## Related

- [`docs/research_execution.md`](docs/research_execution.md)
- [`docs/research_evidence_gaps.md`](docs/research_evidence_gaps.md)
- MDS package remains on the parent branch lineage for twin/proxy scoring software
