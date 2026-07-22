# GitHubBench-Delta

[![CI](https://github.com/samsuljahith/githubbench-delta/actions/workflows/ci.yml/badge.svg)](https://github.com/samsuljahith/githubbench-delta/actions/workflows/ci.yml)
[![Python 3.12 | 3.13](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-informational.svg)](pyproject.toml)
[![Docs](https://img.shields.io/badge/docs-index-purple.svg)](docs/index.md)

**Production evaluation for AI coding agents on real GitHub engineering work.**

GitHubBench-Delta runs local and hosted agents against a curated multi-language task corpus, records full trajectories, scores **18 deterministic methodology metrics**, and publishes results through a dashboard and report pipeline — so comparisons are evidence, not demos.

---

## Table of Contents

- [Why this project exists](#why-this-project-exists)
- [Features](#features)
- [Architecture overview](#architecture-overview)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Example benchmark command](#example-benchmark-command)
- [Supported providers](#supported-providers)
- [Evaluation methodology](#evaluation-methodology)
- [18 GitHubBench-Delta metrics](#18-githubbench-delta-metrics)
- [Repository structure](#repository-structure)
- [Benchmark results](#benchmark-results)
- [Future roadmap](#future-roadmap)
- [Limitations](#limitations)
- [Documentation](#documentation)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Why this project exists

Coding-agent demos look impressive and rarely answer the questions that matter in engineering orgs:

- Did the agent use the **right tools** in a sensible order?
- Is the answer **grounded** in the repository, or hallucinated?
- Did it stay **safe** (no destructive git / blast radius)?
- What did it **cost**, and can a local model compete with a hosted one?

GitHubBench-Delta turns those questions into a repeatable harness: fixed tasks, captured trajectories, deterministic scores, and artifacts you can audit.

---

## Features

- **Multi-agent comparison** — MiniCPM (local / Ollama), Claude (Anthropic), Codex (OpenAI)
- **Curated corpus** — 60-task `datasets/v1` across repository search, issue analysis, architecture understanding, and more (Python, TypeScript, Go, Rust, Java fixtures)
- **18 methodology metrics** — correctness, trajectory, safety, grounding, reliability, efficiency (no LLM-as-judge)
- **Full trajectories** — tool calls, timing, tokens, cost, sandbox events
- **Resume-friendly pipeline** — experiment artifacts in JSON / JSONL / SQLite
- **Dashboard** — FastAPI + Plotly read-only explorer over completed runs
- **Reports** — Markdown, HTML, PDF, JSON, CSV publication formats
- **Dry-run mode** — offline gold synthesis for CI and local smoke tests without API keys

---

## Architecture overview

```mermaid
flowchart LR
  dataset[Dataset_v1] --> runner[ExperimentRunner]
  runner --> agents[Agents_and_Tools]
  agents --> traj[TrajectoryLogger]
  traj --> evals[EvaluationEngine_18_metrics]
  evals --> store[ResultStore]
  store --> dash[Dashboard]
  store --> reports[Reports]
```

| Stage | Role |
|-------|------|
| Dataset | Versioned tasks, gold answers, expected tool calls, fixture repos |
| ExperimentRunner | Orchestrates agents × tasks × trials with seed / concurrency / resume |
| Agents & tools | Provider adapters + read-only GitHub tools |
| Trajectory | Structured execution events for every run |
| EvaluationEngine | Deterministic scoring via `MetricContext` |
| ResultStore | Durable artifacts consumed by dashboard and reports |

Artifacts are the source of truth: the dashboard and reports **never** invoke agents.

Deep dive: [docs/architecture.md](docs/architecture.md).

---

## Screenshots

Dashboard UX (overview, leaderboard, agents, experiment detail). Live numeric results in this README are from experiment `exp_6afa2ce533ba4e0a` only.

![Dashboard overview](docs/assets/screenshots/overview.png)

| Leaderboard | Agents |
|-------------|--------|
| ![Leaderboard](docs/assets/screenshots/leaderboard.png) | ![Agents](docs/assets/screenshots/agents.png) |

![Experiment detail](docs/assets/screenshots/experiment_detail.png)

Assets: [`docs/assets/screenshots/`](docs/assets/screenshots/) (`overview.png`, `leaderboard.png`, `agents.png`, `experiment_detail.png`).

---

## Installation

**Requirements:** Python **3.12** or **3.13**, [uv](https://github.com/astral-sh/uv), Git.

```bash
git clone https://github.com/samsuljahith/githubbench-delta.git
cd githubbench-delta
uv sync --group dev
uv run githubbench version
```

```bash
cp .env.example .env
# Edit .env for live providers (not required for --dry-run)
```

Optional Docker:

```bash
docker compose up api
```

Full guide: [docs/installation.md](docs/installation.md).

---

## Quick Start

Copy-paste dry-run path (no live LLM calls):

```bash
uv run githubbench dataset validate datasets/v1

uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent codex \
  --task gb-repository-search-001 \
  --trials 1 \
  --seed 42 \
  --dry-run

uv run githubbench report generate \
  -e <experiment_id> \
  -t ci_summary \
  -f markdown

uv run uvicorn githubbench_delta.api.app:create_app --factory --reload
# open http://127.0.0.1:8000/dashboard/
```

More recipes: [docs/quickstart.md](docs/quickstart.md) · [examples/](examples/README.md).

---

## Example benchmark command

Reproduce the **same task set** as the live showcase (requires provider keys / local Ollama for live mode). Remove `--dry-run` only when keys and quota are ready:

```bash
uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent minicpm \
  --agent codex \
  --task gb-repository-search-001 \
  --task gb-issue-analysis-001 \
  --task gb-architecture-understanding-001 \
  --task gb-architecture-understanding-002 \
  --task gb-architecture-understanding-003 \
  --task gb-architecture-understanding-005 \
  --trials 1 \
  --seed 42 \
  --concurrency 1 \
  --name showcase-v1-openai-local
```

Published live results for this repository: experiment **`exp_6afa2ce533ba4e0a`**. See [docs/benchmark.md](docs/benchmark.md).

---

## Supported providers

| Agent | Provider | Default model | Env |
|-------|----------|---------------|-----|
| MiniCPM | Ollama (OpenAI-compatible) | `minicpm` (`MINICPM_MODEL`) | `MINICPM_BASE_URL`, `MINICPM_API_KEY` |
| Claude | Anthropic | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| Codex | OpenAI | `gpt-4.1` | `OPENAI_API_KEY` |

Optional: `GITHUB_TOKEN` for live GitHub-backed tools.

Details: [docs/providers.md](docs/providers.md).

---

## Evaluation methodology

All scores are **deterministic**. Evaluators consume a typed `MetricContext` (task, trajectory, gold, cost, peers) and never call a model as judge. Overall score is a weighted average of non-skipped metrics (default weight `1.0`).

```mermaid
flowchart TB
  ctx[MetricContext] --> engine[EvaluationEngine]
  engine --> m1[Correctness]
  engine --> m2[Trajectory]
  engine --> m3[Safety]
  engine --> m4[Grounding]
  engine --> m5[Reliability]
  engine --> m6[Efficiency]
  m1 --> agg[MetricAggregator]
  m2 --> agg
  m3 --> agg
  m4 --> agg
  m5 --> agg
  m6 --> agg
  agg --> result[EvaluationResult]
```

Guide: [docs/evaluation.md](docs/evaluation.md) · Formulas: [docs/evaluation_methodology.md](docs/evaluation_methodology.md).

---

## 18 GitHubBench-Delta metrics

| Group | Metric IDs |
|-------|------------|
| Correctness | `task_resolution` · `engineering_usefulness` · `diff_minimality` |
| Trajectory | `tool_economy` · `unnecessary_tool_calls` · `planning_quality` |
| Safety | `branch_safety` · `blast_radius` · `safe_failure` |
| Grounding | `grounding_ratio` · `hallucinated_api` · `test_honesty` |
| Reliability | `recovery_score` · `calibration` · `cross_trial_consistency` |
| Efficiency | `reproducibility` · `cost_normalized_capability` · `local_vs_hosted_parity` |

---

## Repository structure

```text
githubbench-delta/
├── src/githubbench_delta/     # Installable package
│   ├── agents/                # MiniCPM, Claude, Codex
│   ├── metrics/               # 18 methodology evaluators
│   ├── pipeline/              # Experiments + ResultStore
│   ├── dashboard/ · reports/  # Explore + publish
│   ├── datasets/ · tasks/ · tools/ · cli/ · api/
│   └── ...
├── configs/                   # default / agents / metrics YAML
├── datasets/v1/               # Corpus + multi-language fixtures
├── results/experiments/       # Run artifacts (do not edit by hand)
├── docs/                      # Guides, screenshots, examples
├── examples/                  # Onboarding recipes
├── tests/                     # Unit + integration
└── .github/workflows/         # CI + release
```

---

## Benchmark results

**Source of truth:** experiment `exp_6afa2ce533ba4e0a` only.  
Full tables, costs, and caveats: **[docs/benchmark.md](docs/benchmark.md)** · Narrative: [BENCHMARK_REPORT.md](docs/assets/live-benchmark/exp_6afa2ce533ba4e0a_BENCHMARK_REPORT.md).

| | MiniCPM | Codex |
|--|--------:|------:|
| Mean overall score | 0.539 | **0.682** |
| Agent success | **6 / 6** | 3 / 6 |
| Task wins | 0 | **6** |
| Mean latency | 7.31 s | 6.26 s |
| Total cost | **$0.000000** | $0.033166 |
| Tool calls | 5 | **19** |
| Pipeline units | 12 / 12 completed | 12 / 12 completed |

Codex led every task on overall score. Three Codex failures were OpenAI rate-limit / insufficient-quota errors. MiniCPM finished every unit at $0 but scored poorly on trajectory and `hallucinated_api`. Claude was **not** in this live run. This is a 6-task × 1-trial showcase — not a full 60-task ranking.

---

## Future roadmap

Phases 1–8 (scaffolding through production hardening) are complete. Planned follow-ups:

- Multi-trial live leaderboards (`trial_count ≥ 3`) for stable reproducibility
- Live multi-agent runs including Claude (keys + quota)
- Broader live coverage beyond the 6-task showcase
- Stronger calibration when agents emit stated confidence
- Continued dashboard / report UX polish

Research evidence gaps (what validation can run vs what is blocked):  
**[docs/research_evidence_gaps.md](docs/research_evidence_gaps.md)**.

History: [docs/phases.md](docs/phases.md).

---

## Limitations

- The published **live** showcase is **6 tasks × 2 agents × 1 trial** — not a full 60-task ranking.
- Codex results in `exp_6afa2ce533ba4e0a` were affected by provider **RPM / quota** limits.
- Peer metrics such as `reproducibility` are weak with a single trial.
- `calibration` skipped when agents do not state confidence.
- Dry-run showcase artifacts ([docs/showcase.md](docs/showcase.md)) demonstrate pipeline UX; they are **not** live model rankings.
- PDF report export may require system libraries (WeasyPrint).

---

## Documentation

This **README** is the public entry point. The docs hub is **[docs/index.md](docs/index.md)**. Release readiness: **[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)**.

| Doc | Description |
|-----|-------------|
| [Architecture](docs/architecture.md) | System design and package map |
| [Evaluation](docs/evaluation.md) | How scoring works |
| [Methodology formulas](docs/evaluation_methodology.md) | Deterministic metric formulas |
| [Benchmark](docs/benchmark.md) | Live results for `exp_6afa2ce533ba4e0a` |
| [Providers](docs/providers.md) | Agent backends and env vars |
| [Installation](docs/installation.md) · [Quick Start](docs/quickstart.md) | Onboarding |
| [CLI](docs/cli.md) · [API](docs/api.md) · [Pipeline](docs/pipeline.md) | Operations |
| [Frontend](docs/frontend.md) · [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md) | ElderWise UI + facade |
| [Dashboard](docs/dashboard.md) · [Reports](docs/reports.md) | Explore and publish |
| [Memorization (MDS)](docs/memorization.md) | Post-process memorization vs capability |
| [Research execution](docs/research_execution.md) | YAML registry, artifacts, validation dashboard |
| [Research evidence gaps](docs/research_evidence_gaps.md) | Missing evidence for publishable validation |
| [Showcase (dry-run UX)](docs/showcase.md) | Offline multi-agent demo (not live rankings) |
| [Contributing](docs/contributing.md) · [FAQ](docs/faq.md) · [Troubleshooting](docs/troubleshooting.md) | Community |

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

---

## Acknowledgements

Built with [uv](https://github.com/astral-sh/uv), [Typer](https://github.com/fastapi/typer), [FastAPI](https://github.com/fastapi/fastapi), [Plotly](https://github.com/plotly/plotly.py), and [Pydantic](https://github.com/pydantic/pydantic).

Agent backends use [Ollama](https://ollama.com/), the [Anthropic](https://www.anthropic.com/) API, and the [OpenAI](https://openai.com/) API.

Contributions welcome — see [docs/contributing.md](docs/contributing.md).
