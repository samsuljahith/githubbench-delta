# Examples

Runnable recipes using the `githubbench` CLI (prefer `--dry-run` so no API keys are required).

| Example | Description |
|---------|-------------|
| [01_single_experiment](01_single_experiment/) | One task, one agent |
| [02_multi_agent_compare](02_multi_agent_compare/) | MiniCPM + Claude + Codex |
| [03_benchmark_execution](03_benchmark_execution/) | Validate dataset + small task slice |
| [04_report_generation](04_report_generation/) | CI summary report |
| [05_dashboard](05_dashboard/) | Local dashboard server |

From the repo root:

```bash
chmod +x examples/**/*.sh
./examples/01_single_experiment/run.sh
```
