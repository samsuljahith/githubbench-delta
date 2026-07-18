# Release Checklist

Final documentation and presentation review for a public-facing release of **GitHubBench-Delta** `0.1.0`.

**Scope of this review:** documentation and repository presentation only.  
**Not in scope:** Python source changes, benchmark re-runs, or artifact edits.

Reviewed: 2026-07-18  
Authoritative live experiment: **`exp_6afa2ce533ba4e0a`**

---

## Documentation status

| Item | Status | Notes |
|------|--------|-------|
| [README.md](README.md) as public entry point | Done | Badges, hero, TOC, links to docs hub |
| [docs/index.md](docs/index.md) docs hub | Done | Organizes guides; points back to README |
| [docs/architecture.md](docs/architecture.md) | Done | Mermaid + package map |
| [docs/evaluation.md](docs/evaluation.md) | Done | Overview; formulas in methodology doc |
| [docs/evaluation_methodology.md](docs/evaluation_methodology.md) | Done | Formula reference |
| [docs/benchmark.md](docs/benchmark.md) | Done | Live numbers for `exp_6afa2ce533ba4e0a` only |
| [docs/providers.md](docs/providers.md) | Done | MiniCPM / Claude / Codex |
| [docs/installation.md](docs/installation.md) | Done | Real clone URL; uv / pip / Docker |
| [docs/quickstart.md](docs/quickstart.md) | Done | Copy-paste dry-run path |
| Screenshots | Done | Four PNGs under `docs/assets/screenshots/` (no placeholders) |
| Markdown links (local) | Verified | 0 broken links in README + `docs/**` + `examples/**` |
| Mermaid diagrams | Verified | No spaces in node IDs; labels quoted where needed |
| Dry-run vs live labeling | Done | Showcase dry-run clearly separated from live benchmark |
| Duplication reduced | Done | README summarizes; detail lives in `docs/benchmark.md` |

---

## Benchmark status

| Item | Status | Notes |
|------|--------|-------|
| Live experiment | `exp_6afa2ce533ba4e0a` | `showcase-v1-openai-local`, completed |
| Agents | MiniCPM, Codex | Claude **not** in this live run |
| Tasks / units | 6 / 12 | Seed 42, trials 1 |
| Pipeline | 12 / 12 | 0 harness failures |
| Agent success | 9 / 12 (75%) | MiniCPM 6/6; Codex 3/6 |
| Mean overall | MiniCPM 0.539 · Codex **0.682** | Codex won 6/6 task head-to-heads |
| Cost | Total **$0.033166** | MiniCPM $0.00 · Codex $0.033166 |
| Artifacts | Present | `experiment.json`, `run.json`, `evaluation_results.json`, `trajectory.jsonl`, `BENCHMARK_REPORT.md` |
| Numbers invented? | No | Docs cite only this experiment for live scores |
| Dry-run demo | Separate | `exp_3c790a482f784d21` — UX only, not live rankings |

---

## Code status

| Item | Status | Notes |
|------|--------|-------|
| Package version | `0.1.0` | From `pyproject.toml` |
| Python | 3.12 / 3.13 | `requires-python = ">=3.12,<3.14"` |
| CLI entry | `githubbench` | `uv run githubbench version` → `githubbench-delta 0.1.0` |
| Agents registered | minicpm, claude, codex | Verified via `githubbench list agents` |
| Dataset v1 | 60 tasks | `githubbench dataset validate datasets/v1` → OK |
| CI | `.github/workflows/ci.yml` | Badge linked from README |
| License | Apache-2.0 | [LICENSE](LICENSE) |
| Source modified in this review? | **No** | Documentation only |
| Benchmark artifacts modified? | **No** | Read-only |

---

## Known limitations

1. **Showcase scale** — Live published comparison is 6 tasks × 2 agents × 1 trial, not the full 60-task corpus.
2. **Provider quota** — Three Codex units in `exp_6afa2ce533ba4e0a` failed with OpenAI rate-limit / insufficient-quota errors.
3. **Claude absent from live showcase** — Supported in product; not included in the live experiment above.
4. **Single trial** — `reproducibility` / peer metrics are weak at `trial_count=1`.
5. **Calibration** — Skipped when agents do not state confidence.
6. **Dry-run scores** — Multi-agent dry-run showcase is for pipeline/UX demos only; identical gold synthesis is not a model ranking.
7. **PDF reports** — May require WeasyPrint system libraries; HTML/Markdown are the reliable formats.
8. **Secrets** — Live runs need `.env` keys; never commit `.env`.

---

## Future work

- Multi-trial live leaderboards (`trial_count ≥ 3`)
- Live multi-agent runs including Claude (with adequate API quota)
- Broader live coverage beyond the 6-task showcase
- Stronger calibration when agents emit stated confidence
- Dashboard / report UX polish
- Optional: regenerate screenshots against `exp_6afa2ce533ba4e0a` for visual/numeric alignment

---

## Repository readiness checklist

Use this before making the repository public or cutting a release tag.

### Presentation

- [x] README has badges, hero, TOC, and clear value proposition
- [x] Screenshots render from `docs/assets/screenshots/`
- [x] Architecture Mermaid diagram present
- [x] Live benchmark summary uses only `exp_6afa2ce533ba4e0a`
- [x] Limitations and roadmap documented honestly
- [x] License and acknowledgements present
- [x] [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) published

### Developer experience

- [x] Clone URL is the real GitHub remote
- [x] `uv sync --group dev` install path documented
- [x] Quick Start commands match current CLI flags
- [x] `--dry-run` path works without API keys
- [x] Provider env vars documented (`.env.example` + `docs/providers.md`)
- [x] Docs hub at `docs/index.md` linked from README

### Safety / honesty

- [x] Dry-run showcase not presented as live rankings
- [x] Codex quota failures disclosed
- [x] Claude not claimed in live experiment
- [x] No invented benchmark numbers

### Pre-publish operator steps (manual)

- [ ] Confirm GitHub repo visibility / description / topics
- [ ] Confirm CI green on `main`
- [ ] Confirm `.env` is gitignored and not committed
- [ ] Optional: pin a release tag `v0.1.0` after CI passes
- [ ] Optional: re-run live showcase with adequate OpenAI quota for a cleaner Codex success rate

---

## Verification commands (copy-paste)

```bash
cd githubbench-delta
uv sync --group dev
uv run githubbench version
uv run githubbench list agents
uv run githubbench dataset validate datasets/v1

# Offline smoke (no API keys)
uv run githubbench experiment run \
  --dataset datasets/v1 \
  --agent codex \
  --task gb-repository-search-001 \
  --trials 1 \
  --seed 42 \
  --dry-run
```

---

## Sign-off

| Area | Ready for public viewing? |
|------|---------------------------|
| Documentation & presentation | **Yes** |
| Live benchmark narrative (`exp_6afa2ce533ba4e0a`) | **Yes** (with documented limitations) |
| Full 60-task live multi-agent ranking | **No** — future work |
| Source code changes in this review | N/A — none made |
