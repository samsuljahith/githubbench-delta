# FAQ

## Which Python versions are supported?

**3.12 and 3.13.** Older versions are not supported because the codebase uses `StrEnum` and targets `requires-python = ">=3.12,<3.14"`.

## Do I need API keys?

Only for live agent runs. Use `--dry-run` for local/CI smoke without keys.

## Is the dashboard required to evaluate?

No. Evaluation is CLI/pipeline-driven. The dashboard explores completed artifacts.

## Can I add a 19th metric easily?

Not as a plugin toggle. Methodology metrics are a fixed design surface — open a design discussion first.

## Where do reports go?

Default: `reports/` (`paths.reports`). Override with `--output`.

## How do I compare two runs?

```bash
uv run githubbench report compare -b <baseline_exp> -c <candidate_exp> -f markdown
```

## Why is Black not used?

Ruff format is the project formatter (single tool for lint + format).
