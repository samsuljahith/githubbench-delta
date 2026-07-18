# Evaluation Pipeline (Phase 5)

End-to-end wiring from dataset load through persistence.

## Flow

```text
Dataset (BenchmarkRunner)
  → ExperimentRunner
    → PipelineRunner (per work unit)
        → Agent.run_task (+ retry)
        → Trajectory / ResultStore
        → MetricContextFactory
        → EvaluationEngine (+ MetricAggregator)
    → Peer attachment re-eval
  → Artifacts + SQLite index
```

## Work unit

One unit = `(task_id, agent_id, trial_index)` with deterministic seed derived from the experiment seed.

## Artifacts

Under `results/experiments/{experiment_id}/`:

| File | Description |
|------|-------------|
| `experiment.json` | Experiment metadata and status |
| `run.json` | Progress, completed/failed units |
| `evaluation_results.json` | All `EvaluationResult` rows |
| `trajectory.jsonl` | One agent result / trajectory per line |

SQLite (`results/githubbench.db`) mirrors evaluations, work units, and eval cache for resume/query.

## Features

- **Batch / multi-agent / multi-trial** via `ExperimentSpec`
- **Parallelism** — `max_concurrency` (asyncio semaphore)
- **Resume** — skip successfully completed units
- **Evaluation cache** — keyed by task/agent/trial/seed + agent-result content hash
- **Dry run** — synthesize `AgentResult` from gold (no live providers)
- **Peer pass** — after primary runs, re-evaluate with `peer_results` for peer metrics

## CLI

```bash
uv run githubbench experiment create --dataset datasets/v1 --agent codex --task gb-repository-search-001
uv run githubbench experiment run --dataset datasets/v1 --agent codex --trials 1 --dry-run
uv run githubbench experiment status exp_...
```

## Config (`configs/default.yaml`)

```yaml
pipeline:
  max_concurrency: 1
  resume: true
  cache_evaluations: true
  results_dir: results/experiments
```

## Programmatic

```python
from githubbench_delta.pipeline import ExperimentRunner, ExperimentSpec

runner = ExperimentRunner()
manifest = await runner.run_dataset("datasets/v1", agent_ids=["codex"], dry_run=True)
```
