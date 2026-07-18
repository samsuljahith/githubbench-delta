# Contributing Guide

Thanks for contributing to GitHubBench-Delta.

## Setup

```bash
uv sync --group dev
uv run pre-commit install
```

## Development loop

```bash
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src
uv run pytest
```

## Pull requests

- Prefer small, focused PRs
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes
- Use the PR template checklist
- Do not expand methodology metrics or rewrite evaluation logic without design review

## Code of conduct

See [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

## Security

See [SECURITY.md](../SECURITY.md).
