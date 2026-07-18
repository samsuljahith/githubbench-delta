# Plugin Development Guide

GitHubBench-Delta uses registries rather than a separate plugin package format. Extensions should follow existing patterns.

## Agents

- Implement the agent protocol used by [`agents/`](../src/githubbench_delta/agents/)
- Register in the agent registry and add a provider block to `configs/agents.yaml`
- Provide unit tests with mocked providers (no network)

## Tasks / datasets

- Tasks are data files under `datasets/` (JSONL / authors) — prefer contributing curated tasks with fixtures
- Validate with `githubbench dataset validate … --strict`

## Metrics

- Methodology metrics are the fixed set of 18 evaluators
- Adding a **new** metric is a design change (not a drive-by PR); discuss first
- Existing metric classes live under `src/githubbench_delta/metrics/`

## Tools

- Tool adapters live under `src/githubbench_delta/tools/`
- Prefer deterministic, sandboxed behavior and unit tests

## Reports / dashboard

- Reports consume artifacts only; do not call agents from report code
- Dashboard is read-only exploration

## Testing expectations

- Unit tests for new code paths
- Keep `uv run pytest` green
- Do not weaken coverage or typecheck gates without discussion
