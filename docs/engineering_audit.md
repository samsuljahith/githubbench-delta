# GitHubBench-Delta — Final Engineering Audit

**Scope:** Full repository review. No redesign. No new features in this phase.

**Verdict:** Ready with Minor Changes

**Production readiness score: 68 / 100**

Breakdown (indicative): architecture/layering 12/20 · reliability 10/15 · security 8/15 · testing quality 10/15 · performance 8/10 · docs/release 10/10 · packaging/CI 10/15.

---

## 1. Critical blockers

For a **trusted-operator open-source v0.1** release (local CLI, trusted datasets only): **no critical blockers**, provided C1–C4 are documented as out of scope for that threat model.

The following are **critical** if the project is marketed as production-safe for untrusted datasets, multi-user dashboard exposure, or sandbox isolation:

### C1 — Sandbox config is documentation-only (policy not enforced)

- **Severity:** Critical (for production / untrusted agents)
- **Evidence:** `SandboxConfig.allow_network` / `allow_push` / `protected_branches` exist only in [`configs/default.yaml`](../configs/default.yaml) and [`src/githubbench_delta/core/config.py`](../src/githubbench_delta/core/config.py). No enforcement in tools/providers. Defaults claim `allow_network: false` while live agents and PyGithub tools still call the network when keys exist.
- **Fix:** Enforce fail-closed gates in tool executor / providers, or rename defaults and document “advisory scoring only” until enforced.

### C2 — Untrusted `experiment_id` / path join without jail

- **Severity:** Critical (if CLI/API accepts attacker-controlled ids)
- **Evidence:** [`ExperimentManager.experiment_dir`](../src/githubbench_delta/pipeline/experiment_manager.py) does `self.results_dir / experiment_id` then `mkdir` with no charset/jail check. Same class of risk for report output stems using raw ids ([`reports/export.py`](../src/githubbench_delta/reports/export.py)).
- **Fix:** Allowlist `^[A-Za-z0-9._-]+$`; `resolve().relative_to(results_dir)`; never mkdir on invalid ids.

### C3 — Dataset `local_path` / `repo_path` not jailed to dataset root

- **Severity:** Critical (untrusted corpus)
- **Evidence:** [`tasks/base.py`](../src/githubbench_delta/tasks/base.py) copies `repository.local_path` into tool context; tools treat it as filesystem root. Absolute paths escape fixtures.
- **Fix:** Resolve under dataset/fixtures base; reject absolute / `..` escapes with `Path.is_relative_to`.

### C4 — Tool path check uses string `startswith` (prefix bypass)

- **Severity:** Critical (filesystem jail bypass)
- **Evidence:** [`tools/github/_helpers.py`](../src/githubbench_delta/tools/github/_helpers.py) `str(candidate).startswith(str(root))` — `/tmp/repo` prefixes `/tmp/repo_evil`.
- **Fix:** Use `candidate.is_relative_to(root)`.

---

## 2. High priority improvements

### H1 — `pipeline ↔ storage` circular dependency

- **Evidence:** [`storage/results/base.py`](../src/githubbench_delta/storage/results/base.py) imports `pipeline.models`; pipeline imports `storage.results`. Papered over by `__getattr__` in package `__init__` modules.
- **Fix:** Move `WorkUnit` / `CachedEvaluation` to `core` (or storage DTOs); storage must not import pipeline.

### H2 — Reports depends on Dashboard (wrong layer)

- **Evidence:** `reports/context.py`, `compare.py`, `builder.py`, `charts_bridge.py` import `dashboard.*`. Eager `dashboard/__init__.py` pulls FastAPI routers into report imports.
- **Fix:** Extract shared artifact reader + aggregations; both packages depend downward.

### H3 — Resume flag is misleading / largely ineffective via CLI

- **Evidence:** CLI `experiment run` always creates a new experiment + new `run_id`. Resume key is `(experiment_id, run_id, unit_key)`. Test `test_resume_marks_units_complete` is a single fresh run, not a resume.
- **Fix:** Implement `--experiment-id` continue path, or remove/relabel `--resume` and fix docs/tests.

### H4 — JSONL ResultStore rewrite is O(n²) per experiment

- **Evidence:** [`jsonl_store.py`](../src/githubbench_delta/storage/results/jsonl_store.py) reads entire evaluation JSON, filters, pretty-prints rewrite on every save; peer pass doubles writes.
- **Fix:** Append-only JSONL + compaction, or SQLite-canonical with export.

### H5 — Dashboard/report hot paths load all evaluations + trajectories

- **Evidence:** `ExperimentRepository.evaluation_rows` loads eval JSON + full `trajectory.jsonl`; overview/report call `all_evaluation_rows` repeatedly. Report warnings rescan trajectories per unit.
- **Fix:** Persist summary stats at write time; one-pass trajectory index; single load for report context.

### H6 — Regression / report tests assert almost nothing

- **Evidence:** `MIN_OVERALL_FLOOR = 0.0` in `tests/regression/test_dry_run_benchmark.py`; report tests accept `"#"`.
- **Fix:** Pin score bands for dry-run gold task; assert report-type-specific headings/tables.

### H7 — Dashboard auth stub + public bind

- **Evidence:** `dashboard/auth.py` always anonymous; Docker/compose expose `0.0.0.0:8000`.
- **Fix:** Document localhost-only for v0.1; bind `127.0.0.1` by default; real auth before any remote exposure.

### H8 — Silent failure modes hide corruption

- **Evidence:** SQLite errors → `[]` in dashboard repository; bad JSONL lines skipped; chart/PDF `except Exception` skips.
- **Fix:** Log + surface errors; CLI non-zero when required format fails.

---

## 3. Medium improvements

| ID | Issue | Evidence | Fix |
|----|-------|----------|-----|
| M1 | No `.dockerignore` | Missing file | Add excludes for `.env`, `.venv`, artifacts |
| M2 | Dev Docker runs as root | `Dockerfile.dev` | Match prod non-root |
| M3 | CI missing least-privilege permissions | `.github/workflows/ci.yml` | `permissions: contents: read` |
| M4 | `uv:latest` unpinned in Docker | `Dockerfile` | Pin digest |
| M5 | DuckDB / CSV / Parquet stubs exposed | storage/datasets loaders | Remove from factories or mark experimental |
| M6 | Fake pipeline report/dashboard stages | `pipeline/base.py` | Delete unused stage names |
| M7 | Peer pass re-evaluates all 18 metrics | `experiment.py` `_peer_pass` | Re-score peer metrics only |
| M8 | Full corpus load for single-task runs | `experiment.py` `_load_tasks` | Id-filtered / cached catalog |
| M9 | Duplicate export/aggregation logic | dashboard vs reports export | Shared read-model |
| M10 | Eager package `__init__` import bombs | dashboard, reports, metrics, agents | Narrow re-exports |
| M11 | MyPy `ignore_errors` on core packages | `pyproject.toml` | Gradual tighten |
| M12 | Example 04 picks wrong experiment | `examples/04_report_generation/run.sh` | Parse CLI-printed id |
| M13 | Docs claim resume / DuckDB completeness | pipeline.md, phases, architecture | Align with reality |
| M14 | No integration/e2e suite | tests layout | Peer-pass + SQLite edge cases |
| M15 | Perf tests are absolute wall-clock | `tests/perf/` | Relative/baseline or non-gating |
| M16 | WeasyPrint/Kaleido hard deps | `pyproject.toml` | Optional extras |
| M17 | Tool `max_bytes` uncapped | GitHub tools | Clamp DoS bounds |
| M18 | Trajectory double-stored | ResultStore artifacts | Store once |

---

## 4. Low priority improvements

- Placeholder clone URL in `docs/installation.md`; homepage URL may not match actual remote
- Historical “11 tasks” wording in `docs/phases.md` vs 60-task corpus
- Category-only task subclasses with Phase 3 TODOs
- `DistributedExecutor` TODO in `benchmark/runner.py` while Phase 5 marked complete
- Jinja custom `--template-dir` trust boundary
- Provider unit tests only mock SDK shapes
- PDF path often skipped in CI
- Naming: `MetricEngineStage` no-ops vs real `EvaluationEngine`
- `MINICPM_API_KEY=ollama` placeholder in `.env.example` can confuse

---

## 5. Technical debt

- **Cycle debt:** `pipeline ↔ storage` + lazy `__getattr__` shims
- **Layer debt:** reports → dashboard → FastAPI; parallel artifact readers vs ResultStore
- **Stub debt:** DuckDB EventStore, CSV/Parquet loaders, unused pipeline stage names, WebSocket 501, auth stub
- **Test debt:** resume test false confidence; regression floor 0.0; auth dependency overridden in API tests; mypy ignores on largest packages
- **Perf debt:** JSON rewrite, peer double-eval, full-corpus load, N× trajectory rescan
- **Docs debt:** “production” marketing vs stubbed/enforcement gaps

---

## 6. Production readiness score: 68 / 100

| Audience | Fit |
|----------|-----|
| Open-source release (trusted local use) | Suitable after documenting limitations + fixing H3/H6/H7 defaults |
| Production multi-user / untrusted data | Not suitable until C1–C4 + H7 addressed |
| Research publication / methodology showcase | Suitable (deterministic metrics + corpus + dry-run are real) |
| Portfolio showcase | Suitable with honest README limitations section |

---

## 7. Final verdict

**Ready with Minor Changes**

For a **v0.1 open-source / research / portfolio** release: no architecture rewrite required. Before calling it “production-ready,” ship at minimum:

1. Path jailing (`is_relative_to` + experiment id allowlist + dataset path jail) — C2–C4
2. Honest sandbox/resume/auth/docs (enforce or demote claims) — C1, H3, H7, M13
3. Meaningful regression assertions — H6
4. `.dockerignore` + localhost bind defaults — M1, H7

**Explicit:** For trusted-operator offline dry-run / local evaluation, **no critical blockers** if C1–C4 are accepted as out-of-scope for that threat model and documented as such. For production or untrusted workloads, **C1–C4 are blockers**.

---

*This audit phase delivers findings only; it does not implement fixes.*
