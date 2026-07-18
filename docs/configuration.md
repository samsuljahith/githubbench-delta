# Configuration Guide

## Files

| File | Role |
|------|------|
| [`configs/default.yaml`](../configs/default.yaml) | Runtime: seed, paths, storage, sandbox, retry, observability, pipeline |
| [`configs/agents.yaml`](../configs/agents.yaml) | Provider settings for MiniCPM / Claude / Codex |
| [`configs/metrics.yaml`](../configs/metrics.yaml) | 18 evaluator weights / thresholds |
| [`configs/datasets.yaml`](../configs/datasets.yaml) | Dataset roots |
| [`configs/samples/minimal.yaml`](../configs/samples/minimal.yaml) | Sample dry-run-friendly overrides |

Load directory via `--config-dir` or `GITHUBBENCH_CONFIG_DIR`.

## Environment overrides

See `.env.example` for API keys and path overrides (`pydantic-settings`).

## Important knobs

- `paths.reports` / `paths.results` — artifact locations
- `pipeline.results_dir` — experiment directories
- `observability.structured_logging` — JSON logs
- `storage.sqlite_path` — ResultStore index

Changing `metrics.yaml` weights affects scoring; treat as a methodology change and update docs/tests accordingly.
