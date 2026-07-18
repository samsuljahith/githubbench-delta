# Reports (Phase 7)

Publication-quality reporting from completed experiment artifacts. No evaluation or agent execution.

## Run

```bash
# Technical report (Markdown + HTML)
uv run githubbench report generate -e exp_... -t technical -f markdown -f html

# Compare two experiments (regression report)
uv run githubbench report compare -b exp_baseline -c exp_candidate -f markdown -f json

# Flat data export
uv run githubbench report export -e exp_... -f csv -o reports/export.csv
```

Default output directory: `reports/` (from config `paths.reports`).

## Report types

| Type | Purpose |
|------|---------|
| `executive` | Short score snapshot + recommendations |
| `technical` | Full section set for stakeholders |
| `experiment` | Single-experiment focus |
| `agent_comparison` | Radar/bars-oriented agent compare |
| `metric` | 18-metric stats and methodology |
| `task_analysis` | Per-task and category performance |
| `regression` | Diff + regression highlights (needs baseline/candidate) |
| `ci_summary` | Compact overall + regressions + warnings |

## Formats

`markdown` · `html` · `pdf` · `json` · `csv`

PDF uses WeasyPrint (HTML→PDF) with Kaleido chart PNGs. HTML embeds interactive Plotly figures. Markdown links chart images when PNGs were generated (PDF export), otherwise notes a placeholder. If native PDF libraries are unavailable, other formats still work.

## Sections

Experiment metadata, dataset summary, agent/benchmark configuration, evaluation methodology, overall results, 18-metric breakdown, category scores, task performance, failure analysis, trajectory/tool usage, latency, cost, confidence, warnings, deterministic recommendations, appendix. Diff/regression sections appear for compare workflows.

## Custom templates & branding

```bash
uv run githubbench report generate -e exp_... --template-dir ./my_templates -f html
```

Override `base.html` / `base.md` (or `types/<report_type>.*`). Branding CSS variables and optional logo are controlled via `BrandConfig` (`product_name`, `logo_path`, colors, footer).

## Data sources

- `results/experiments/{id}/experiment.json`
- `run.json`
- `evaluation_results.json`
- `trajectory.jsonl`

Charts reuse Phase 6 Plotly builders (`radar`, `bars`, `histogram`, `corr_heatmap`, `importance`).

## Recommendations

Rule-based thresholds only (overall/group scores, confidence, cost, latency, failure rate, regressions). No LLM text generation.
