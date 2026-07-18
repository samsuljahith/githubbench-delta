# Quick Start

End-to-end dry-run path (no live LLM calls):

```bash
# 1. Validate curated corpus
uv run githubbench dataset validate datasets/v1

# 2. Run a single-task experiment
uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent codex \
  --task gb-repository-search-001 \
  --trials 1 --seed 42 --dry-run

# 3. Generate a CI summary report (replace exp_… with printed id)
uv run githubbench report generate -e <experiment_id> -t ci_summary -f markdown

# 4. Explore artifacts in the dashboard
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload
# open http://127.0.0.1:8000/dashboard/
```

More recipes: [examples/](../examples/README.md).
