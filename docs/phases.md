# Development Phases

## Phase 1 — Scaffolding (complete)

- Project layout, uv packaging, Docker stubs
- Pydantic config (default / agents / metrics)
- Core models and error hierarchy
- Agent, task, metric, pipeline, report interfaces
- Registries for 3 agents, 11 tasks, 18 methodology metrics
- Typer CLI + FastAPI health/catalog stubs
- Unit tests for config, registries, models, CLI/API

## Phase 2 — Agents (complete)

- BaseAgent lifecycle: initialize → prepare_task → plan → execute → validate → cleanup
- Swappable providers: MiniCPM (Ollama/OpenAI-compatible), Claude (Anthropic), Codex (Responses API)
- Pluggable tool system + 7 read-only GitHub tools
- TrajectoryLogger + ExecutionEvent capture
- EventStore backends: JSONL, SQLite (DuckDB stub)
- Observability IDs, structured logging, retries, typed errors
- Unit tests for lifecycle, providers, tools, trajectory, event store, retry

## Phase 3 — Tasks / Datasets (complete)

- Enriched BaseTask (versions, repository, gold_answers, tags, duration)
- Extended task categories + aliases (12 Phase 3 families)
- JSON / JSONL / YAML loaders; Parquet/CSV stubs
- DatasetValidator, DatasetManifest, RepositoryRef fingerprints
- TaskCatalog filtering; PromptTemplate registry + hashing
- BenchmarkRunner (single / batch / full, deterministic seeds)
- Sample `datasets/v1` corpus + fixtures/mini_repo
- CLI: `githubbench dataset validate|manifest`

## Phase 3.5 — Production corpus (complete)

- Schema: `difficulty_score`, `prompt_version`, `GoldAnswerFormat.CODE`, `alternate_gold_answers`
- Six multi-language fixture repos (`py_cli`, `py_rag`, `ts_frontend`, `go_rest_api`, `rust_service`, `java_backend`)
- Curated 60-task v1 corpus (`datasets/v1/authors` + `scripts/build_v1_corpus.py`)
- `CorpusQualityValidator` + CLI `githubbench dataset validate … --strict`
- Exact category counts (12 families) and difficulty bands (15/30/15)
- Optional task fields `expected_tool_calls` / `failure_examples` required under strict validation

## Phase 4 — Evaluation Engine (complete)

- Enriched `MetricContext` / `MetricResult` / `MetricConfiguration`
- `BaseMetric` contract: `evaluate`, `score`, `details`, `reasoning`, `metadata`
- `MetricRegistry`, `MetricAggregator` / `WeightedScore`, `EvaluationEngine`
- Deterministic implementations for all 18 methodology evaluators
- YAML: enabled, weight, thresholds, strict, normalization, confidence_mode, version
- Unit tests per group + aggregator/engine; methodology formulas documented

## Phase 5 — Evaluation Pipeline (complete)

- `PipelineRunner` / `ExperimentRunner` / `RunManager` / `ExperimentManager`
- `MetricContextFactory` + evaluation caching + retry orchestration
- `ResultStore` (JSONL artifacts + SQLite) with resume support
- Batch / parallel / multi-agent / multi-trial; peer attachment pass
- Artifacts: `experiment.json`, `run.json`, `evaluation_results.json`, `trajectory.jsonl`
- CLI: `githubbench experiment create|run|status`
- No dashboard/reports; metrics and datasets unchanged

## Phase 6 — Dashboard (complete)

- FastAPI + Plotly read-only explorer over experiment artifacts
- Pages: overview, experiments, leaderboard, agents, tasks, metrics, trajectories, settings
- REST API with pagination/filtering/sorting + CSV/JSON/Markdown export
- Auth stub + WebSocket capability stub; no evaluation execution

## Phase 7 — Reports (complete)

- ReportBuilder + Jinja templates + ExportManager (Markdown / HTML / PDF / JSON / CSV)
- Eight report types including regression and CI summary
- Deterministic recommendations; experiment/agent/dataset/prompt diffs
- CLI: `githubbench report generate|compare|export`

## Phase 8 — Hardening (complete)

- GitHub Actions CI (lint, MyPy, tests 3.12/3.13, packaging, docs, audit, release)
- pre-commit, Ruff format, coverage gate, dependency audit
- Docker production/dev images + compose; examples 01–05
- Deterministic dry-run regression + performance smokes
- Expanded docs, SECURITY/CoC, issue/PR templates, CHANGELOG, LICENSE
