# CLI Reference

Entrypoint: `githubbench` (`uv run githubbench …`).

## Global options

| Option | Description |
|--------|-------------|
| `--verbose` / `-v` | DEBUG logging |
| `--log-level` | `critical\|error\|warning\|info\|debug` |
| `--structured-logs` / `--plain-logs` | JSON vs plain stderr logs |

## Commands

### `version`

Print package version.

### `config show`

Show aggregated runtime configuration.

### `list`

| Command | Description |
|---------|-------------|
| `list agents` | Registered agent ids |
| `list tasks` | Task categories |
| `list metrics` | 18 methodology evaluators |

### `dataset`

| Command | Description |
|---------|-------------|
| `dataset validate PATH [--strict]` | Schema / corpus validation |
| `dataset manifest PATH` | Write `manifest.json` |

### `experiment`

| Command | Description |
|---------|-------------|
| `experiment create` | Create manifest only |
| `experiment run` | Execute evaluation (`--dry-run` supported) |
| `experiment status ID` | Show experiment/run status |

Common `run` flags: `--dataset`, `--agent`, `--task`, `--trials`, `--seed`, `--concurrency`, `--resume/--no-resume`, `--cache/--no-cache`, `--dry-run`, `--name`.

### `report`

| Command | Description |
|---------|-------------|
| `report generate` | Build publication report |
| `report compare` | Baseline vs candidate regression report |
| `report export` | Flat CSV/JSON/… dump |

See also [Reports](reports.md) and [Pipeline](pipeline.md).

### `memorization`

Memorization Discounted Scoring — optional post-processing (\(S_{\mathrm{obs}}=G+L\)). See [Memorization](memorization.md).

| Command | Description |
|---------|-------------|
| `memorization analyze` | Estimate lift + write JSON / Markdown / HTML |
| `memorization report` | Full report bundle (alias of `analyze`) |
| `memorization export` | Export selected formats (`-f json\|markdown\|html`) |
| `memorization generate-twins` | Emit paraphrase twin sidecar JSONL (no agent runs) |

### `research`

Research execution platform — YAML experiment registry, readiness, artifacts, validation dashboard. Does not run live agents or fabricate statistics. See [Research execution](research_execution.md).

| Command | Purpose |
|---------|---------|
| `research list` | List YAML/plugin-registered experiments |
| `research status` | Readiness (runnable / blocked / pending) |
| `research artifacts` | Write manifest / metadata / summary (+ repro) |
| `research publish` | Export publication tables from real aggregates only |
| `research repro` | Environment / deps / config / seeds package |
| `research validate` | Build `validation_report.html` |
| `research power` | Sample size / MDE from a real pilot JSON array |

Common flags: `--experiment` / `-e`, `--output` / `-o`, `--experiments-dir`, `--twins-path`.
