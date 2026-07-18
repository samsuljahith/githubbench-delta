# Installation

Onboarding hub: [index.md](index.md) · Next: [quickstart.md](quickstart.md) · Providers: [providers.md](providers.md)

## Requirements

- Python **3.12** or **3.13** (`requires-python = ">=3.12,<3.14"`)
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git (for fixture repositories and Docker builds)

## Install with uv (recommended)

```bash
git clone https://github.com/samsuljahith/githubbench-delta.git
cd githubbench-delta
uv sync --group dev
uv run githubbench version
```

## Install with pip

```bash
git clone https://github.com/samsuljahith/githubbench-delta.git
cd githubbench-delta
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
githubbench version
```

## Environment

Copy `.env.example` to `.env` and set provider keys when running **live** agents:

- `OPENAI_API_KEY` / Codex
- `ANTHROPIC_API_KEY` / Claude
- MiniCPM / Ollama settings as documented in `.env.example`

Dry-run experiments (`--dry-run`) do not require provider keys.

## Docker

Production:

```bash
docker compose up api
```

Development (reload):

```bash
docker compose up dev
```

See [Dockerfile](../Dockerfile) and [Dockerfile.dev](../Dockerfile.dev).

## Verify

```bash
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```
