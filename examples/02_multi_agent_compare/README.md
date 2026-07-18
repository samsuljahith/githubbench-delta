# Example 02 — Multi-agent comparison (dry-run)

Evaluates MiniCPM, Claude, and Codex on one task in dry-run mode, then prints experiment status.

```bash
./examples/02_multi_agent_compare/run.sh
```

After a real (non-dry-run) pair of experiments exists, compare with:

```bash
uv run githubbench report compare -b <baseline_id> -c <candidate_id> -f markdown
```
