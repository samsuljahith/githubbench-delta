# Troubleshooting

## `githubbench` not found

Use `uv run githubbench …` or activate the venv after `uv sync` / `pip install -e .`.

## Dataset validation failures

- Ensure fixture repos under `datasets/fixtures/` are present
- Run without `--strict` first, then with `--strict` for corpus gates
- Check `local_path` fields resolve from the repo root

## Dry-run experiment fails

- Confirm task id exists in `datasets/v1/tasks.jsonl`
- Check `results/experiments/` is writable
- Inspect `run.json` `failed_units` for error strings

## Dashboard empty

- Dashboard only reads completed experiment artifacts under `results/experiments/`
- Run a dry-run experiment first
- Confirm `pipeline.results_dir` matches where artifacts were written

## PDF reports missing

- PDF requires WeasyPrint system libraries and Kaleido for charts
- Use `-f markdown` / `-f html` if PDF dependencies are unavailable

## MyPy / Ruff CI failures

- Run the same commands locally (`uv run ruff …`, `uv run mypy src`)
- Locked packages (`metrics`, `pipeline`, `dashboard`, `reports`, `datasets`, `evals`) have MyPy `ignore_errors` — prefer not editing them in drive-by PRs

## Coverage gate

- `fail_under` is configured in `pyproject.toml`
- New code should include tests; do not lower the gate without discussion
