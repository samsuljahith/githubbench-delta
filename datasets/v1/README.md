# GitHubBench-Delta v1 corpus

Production curated dataset for Phase 3.5: **exactly 60** GitHub engineering tasks.

## Layout

| Path | Role |
|------|------|
| `dataset.yaml` | Dataset metadata (`dataset_version: v1`) |
| `tasks.jsonl` | Generated task records (do not hand-edit) |
| `manifest.json` | Content hash + category/language counts |
| `authors/` | Curated author modules (language-first; see below) |

### Author modules

| Module | Role |
|--------|------|
| `_common.py` | Shared helpers (`task`, `tools`, `failures`, fixture refs) |
| `python_tasks.py` | Python fixture tasks (`py_cli`, `py_rag`) |
| `typescript_tasks.py` | TypeScript tasks (`ts_frontend`) |
| `go_tasks.py` | Go tasks (`go_rest_api`) |
| `rust_tasks.py` | Rust tasks (`rust_service`) |
| `java_tasks.py` | Java tasks (`java_backend`) |
| `edge_cases.py` | Cross-cutting / adversarial cases (empty in v1) |
| `corpus.py` | Aggregates language modules → stable 60-task list |

## Distribution

| Category | Count |
|----------|------:|
| Repository Search | 6 |
| Architecture Understanding | 6 |
| Code Explanation | 6 |
| Bug Fix | 8 |
| Commit Summary | 4 |
| README Generation | 4 |
| Documentation | 4 |
| Pull Request Review | 5 |
| Code Refactoring | 5 |
| Dead Code Detection | 4 |
| Issue Analysis | 4 |
| Unit Test Generation | 4 |

Difficulty bands: Easy 15 / Medium 30 / Hard 15.

Languages: Python, TypeScript, Go, Rust, Java (each ≥6 tasks), via fixtures under `datasets/fixtures/`.

## Rebuild

From the repository root:

```bash
python scripts/build_fixtures.py   # if fixtures need regenerating
python scripts/build_v1_corpus.py
githubbench dataset validate datasets/v1 --strict
```

Author modules live in `authors/`; the builder writes `tasks.jsonl`, runs `CorpusQualityValidator`, and refreshes `manifest.json`.
