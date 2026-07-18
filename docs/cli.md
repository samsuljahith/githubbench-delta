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
