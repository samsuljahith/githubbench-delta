# Evaluation

How GitHubBench-Delta scores agent runs. For full deterministic formulas, see [evaluation_methodology.md](evaluation_methodology.md).

## Table of Contents

- [Principles](#principles)
- [Scoring pipeline](#scoring-pipeline)
- [Metric groups](#metric-groups)
- [The 18 metrics](#the-18-metrics)
- [Overall score](#overall-score)
- [Configuration](#configuration)
- [Related docs](#related-docs)

---

## Principles

- **Deterministic** — no LLM-as-judge; same inputs → same scores.
- **Provider-agnostic** — evaluators see `MetricContext`, not a vendor SDK.
- **Explainable** — each metric returns score, reasoning, evidence, and optional skip reason.
- **Composable** — enable/disable and weight metrics in `configs/metrics.yaml`.

---

## Scoring pipeline

```mermaid
flowchart LR
  agentResult[AgentResult] --> factory[MetricContextFactory]
  factory --> ctx[MetricContext]
  ctx --> engine[EvaluationEngine]
  engine --> results[MetricResults]
  results --> agg[MetricAggregator]
  agg --> out[EvaluationResult]
```

1. Pipeline attaches task gold, trajectory, cost, and peers into `MetricContext`.
2. `EvaluationEngine` runs every enabled metric.
3. `MetricAggregator` computes overall and per-group scores (weighted average of non-skipped metrics).

---

## Metric groups

| Group | What it answers |
|-------|-----------------|
| **Correctness** | Did the agent solve the task usefully vs gold? |
| **Trajectory** | Did it use the right tools in a sensible order? |
| **Safety** | Did it avoid destructive git / unjustified blast radius? |
| **Grounding** | Are claims backed by evidence? Any hallucinated APIs? |
| **Reliability** | Recovery, calibration, cross-trial consistency |
| **Efficiency** | Reproducibility, cost-normalized capability, local/hosted parity |

---

## The 18 metrics

### Correctness

| ID | Focus |
|----|-------|
| `task_resolution` | Criteria hit rate + content overlap vs gold |
| `engineering_usefulness` | Success, substance, vacuous/error penalties |
| `diff_minimality` | Prefer minimal unjustified diffs |

### Trajectory

| ID | Focus |
|----|-------|
| `tool_economy` | Multiset F1 vs expected tools (or budget heuristic) |
| `unnecessary_tool_calls` | Off-expected / duplicate call penalties |
| `planning_quality` | LCS ratio of expected vs actual tool sequences |

### Safety

| ID | Focus |
|----|-------|
| `branch_safety` | Protected branch / force-push / destructive git |
| `blast_radius` | Unjustified file changes |
| `safe_failure` | Fail or succeed without destructive sandbox events |

### Grounding

| ID | Focus |
|----|-------|
| `grounding_ratio` | Grounded claims / total claims |
| `hallucinated_api` | Hallucinated path/symbol refs vs threshold |
| `test_honesty` | Vacuous vs real test assertions |

### Reliability

| ID | Focus |
|----|-------|
| `recovery_score` | Recoveries after tool/error events |
| `calibration` | Stated confidence vs correctness proxy (skip if missing) |
| `cross_trial_consistency` | Peer score variance / uniqueness |

### Efficiency

| ID | Focus |
|----|-------|
| `reproducibility` | Trajectory similarity vs peers |
| `cost_normalized_capability` | Capability / (1 + cost × scale) |
| `local_vs_hosted_parity` | Local vs hosted capability delta |

Formulas: [evaluation_methodology.md](evaluation_methodology.md).

---

## Overall score

Default aggregation is **weighted average** of non-skipped metrics (weights default to `1.0`). Group scores are means within each group. Confidence is the mean of active metric confidences.

Skipped metrics (e.g. missing stated confidence for `calibration`) are excluded from the average unless `strict: true`.

---

## Configuration

Primary file: [`configs/metrics.yaml`](../configs/metrics.yaml)

Per metric: `enabled`, `weight`, `thresholds`, `strict`, normalization, confidence mode, version.

List metrics from the CLI:

```bash
uv run githubbench list metrics
```

---

## Related docs

- [Evaluation methodology (formulas)](evaluation_methodology.md)
- [Architecture](architecture.md)
- [Benchmark results](benchmark.md)
- [Docs index](index.md)
