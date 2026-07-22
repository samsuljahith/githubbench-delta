# Research Execution Platform

Additive orchestration layer for **reproducibility-focused research experiments**. It registers YAML experiment manifests, checks evidence readiness, writes provenance artifacts, and exports publication tables **only from real evaluation aggregates**. It does **not** run live LLM agents, change metrics/evaluators, or invent statistical results.

## Constraints

| Rule | Behavior |
|------|----------|
| Additive | Package `githubbench_delta.research` only; `app.add_typer(..., name="research")` |
| No schema churn | Does not modify `experiment.json` / `evaluation_results.json` / metrics |
| No fabrication | Insufficient `n` → `StatResult.ok=False`, `notes=["insufficient_data"]` |
| Numpy only | Bootstrap / permutation / Normal rank approximations — **no scipy** |
| Evidence honesty | Dashboard mirrors [`research_evidence_gaps.md`](research_evidence_gaps.md) |

## CLI

```bash
githubbench research list
githubbench research status [--experiment ID]
githubbench research artifacts --experiment ID [-o DIR]
githubbench research publish --experiment ID [-o DIR]
githubbench research repro --experiment ID [-o DIR]
githubbench research validate [-o DIR]
githubbench research power --pilot-json PATH [--alpha 0.05] [--power 0.8] [--mde DELTA]
```

Adding a new experiment: drop a YAML file under `configs/research/experiments/` (or a `@register_experiment` / `@experiment_plugin` module). **No CLI edits required.**

## YAML experiments

Each file under `configs/research/experiments/*.yaml` defines one `ResearchExperiment` (`id`, `project`, `hypothesis`, `status`, `requires`, `stats_plan`, `artifact_globs`, …).

Seed catalog (declarative; **no fabricated results**):

| ID | Status | Role |
|----|--------|------|
| E0a–E0d | `runnable` | Limited-claim demos (ranking / MDS proxy / Trust / Observatory demo) |
| E1–E10 | `blocked` | Publishable claims awaiting evidence nodes T/A/C/M/F/H/L/X/W |

Companion: `configs/research/evidence_registry.yaml` + `configs/research/projects.yaml`.

## Statistics & power

Public APIs return `StatResult` / `PowerEstimate`:

- Bootstrap CI, paired bootstrap, permutation test
- Wilcoxon / Mann–Whitney (Normal + continuity correction; documented)
- McNemar, BH-FDR, Cohen’s d, Cliff’s delta, Normal mean CI
- `SampleSizeEstimator`, `MDEEstimator`, `VarianceEstimator` from **caller-provided** pilot arrays

Empty or tiny pilots never yield fake p-values or sample sizes.

## Artifacts

Default root: `results/research/<experiment_id>/<UTC>/`

| File | Contents |
|------|----------|
| `experiment_manifest.json` | Id, hypothesis, requires, git commit, config hash |
| `experiment_metadata.json` | Seed, timestamp, hardware, optional model/provider |
| `experiment_summary.md` | Human-readable status + source artifact links |
| `repro/` | `environment.json`, `dependencies.txt`, `config_snapshot.yaml`, `seeds.json` |
| `publication_tables.csv` / `.tex` | Real aggregate rows only (else empty) |
| `publication_figures.json` | Refs or `[]` |
| `validation_report.html` | Global dashboard (`research validate`) |

## Validation dashboard

`githubbench research validate` builds HTML sections for runnable/blocked/pending experiments, evidence registry status, missing datasets, and publication readiness. It never invents significance claims.

## Related

- [Research evidence gaps](research_evidence_gaps.md) — what is still missing for publishability
- [Memorization (MDS)](memorization.md) — MDS software (separate package)
- [CLI reference](cli.md) — command index
- [IMPLEMENTATION_REPORT.md](../IMPLEMENTATION_REPORT.md) — architecture & limitations
