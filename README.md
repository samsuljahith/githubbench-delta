# GitHubBench-Delta

Production-quality evaluation framework for comparing AI coding agents on real GitHub engineering tasks.

**Agents:** MiniCPM (local via Ollama), Claude (Anthropic), Codex (OpenAI)

**Methodology:** 18 first-class production evaluators (Task Resolution, Engineering Usefulness, Diff Minimality, Tool Economy, Unnecessary Tool Calls, Recovery Score, Planning Quality, Branch Safety, Blast Radius, Safe Failure, Grounding Ratio, Hallucinated API, Test Honesty, Calibration, Cross Trial Consistency, Reproducibility, Cost-Normalized Capability, Local-vs-Hosted Parity).

## Status

| Phase | Focus | Status |
|-------|--------|--------|
| 1 | Scaffolding, config, interfaces, registries, CLI/API stubs | **Complete** |
| 2 | Agent lifecycle, providers, tools, trajectory, event store | **Complete** |
| 3 | Task/dataset framework, manifests, BenchmarkRunner | **Complete** |
| 3.5 | Production 60-task corpus + fixtures + strict validation | **Complete** |
| 4 | Evaluation engine (18 deterministic methodology metrics) | **Complete** |
| 5 | Evaluation pipeline + ResultStore (JSONL/SQLite) | **Complete** |
| 6 | Interactive dashboard (FastAPI + Plotly) | **Complete** |
| 7 | Reporting & publication (MD/HTML/PDF/JSON/CSV) | **Complete** |
| 8 | Production hardening (CI, docs, packaging, DX) | **Complete** |

## Requirements

- Python **3.12** or **3.13**
- [uv](https://github.com/astral-sh/uv)

## Install

```bash
cd githubbench-delta
uv sync --group dev
uv run pre-commit install   # optional local hooks
```

See [Installation](docs/installation.md). Copy `.env.example` to `.env` for live provider keys (not required for `--dry-run`).

## Showcase

Published 6-task × 3-agent example (dashboard screenshots, HTML report, leaderboard CSV):

- [Showcase write-up](docs/showcase.md)
- Screenshots: [docs/assets/screenshots/](docs/assets/screenshots/)
- Example report: [docs/assets/example-report/](docs/assets/example-report/)
- Benchmark summary: [docs/assets/example-benchmark/](docs/assets/example-benchmark/)

![Dashboard overview](docs/assets/screenshots/overview.png)

Architecture: [docs/architecture.md](docs/architecture.md). Install: [docs/installation.md](docs/installation.md).

**Note:** The multi-agent showcase artifacts were produced with `--dry-run` (reproducible offline). Live MiniCPM/Ollama was smoke-tested separately. Claude/Codex live runs need API keys in `.env`.

## Quick start

```bash
uv run githubbench dataset validate datasets/v1
uv run githubbench experiment run \
  --dataset datasets/v1 --agent codex \
  --task gb-repository-search-001 --trials 1 --seed 42 --dry-run
```

Full walkthrough: [Quick Start](docs/quickstart.md). Examples: [examples/](examples/README.md).

## CLI

```bash
uv run githubbench version
uv run githubbench config show
uv run githubbench list agents
uv run githubbench list tasks
uv run githubbench list metrics
```

See [CLI Reference](docs/cli.md).

## API & dashboard

```bash
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload
```

- `GET /health`
- `GET /metrics/catalog`
- `GET /dashboard/` and `/dashboard/api/*`

See [API](docs/api.md) and [Dashboard](docs/dashboard.md).

## Datasets

```bash
uv run githubbench dataset validate datasets/v1
uv run githubbench dataset validate datasets/v1 --strict
uv run githubbench dataset manifest datasets/v1
```

## Experiments

```bash
uv run githubbench experiment run --dataset datasets/v1 --agent codex --task gb-repository-search-001 --dry-run
uv run githubbench experiment status <experiment_id>
```

See [Pipeline](docs/pipeline.md).

## Reports

```bash
uv run githubbench report generate -e <experiment_id> -t technical -f markdown -f html
uv run githubbench report compare -b <baseline_id> -c <candidate_id> -f markdown
uv run githubbench report export -e <experiment_id> -f csv
```

See [Reports](docs/reports.md).

## Tests & quality

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest --cov=githubbench_delta
bash scripts/check_packaging.sh
```

## Documentation

- [Installation](docs/installation.md)
- [Quick Start](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Evaluation methodology](docs/evaluation_methodology.md)
- [CLI](docs/cli.md) · [API](docs/api.md) · [Configuration](docs/configuration.md)
- [Pipeline](docs/pipeline.md) · [Dashboard](docs/dashboard.md) · [Reports](docs/reports.md)
- [Plugins](docs/plugins.md) · [Contributing](docs/contributing.md)
- [Troubleshooting](docs/troubleshooting.md) · [FAQ](docs/faq.md) · [Release](docs/release.md)
- [Phases](docs/phases.md)
- [Engineering audit](docs/engineering_audit.md)
- [Showcase](docs/showcase.md)
- [Self-study notes](docs/self_study_notes.md)
- [Mentor session prep](docs/mentor_session_prep.md)

## Layout

```
src/githubbench_delta/   # installable package
configs/                 # default.yaml, agents.yaml, metrics.yaml, samples/
datasets/ logs/ results/ reports/
examples/ tests/ docs/
.github/workflows/       # CI + release
```

## License

Apache-2.0 — see [LICENSE](LICENSE).
