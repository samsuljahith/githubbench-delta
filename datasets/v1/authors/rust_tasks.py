"""Curated rust tasks for the GitHubBench-Delta v1 corpus."""

from __future__ import annotations

from typing import Any

from _common import task  # type: ignore


def tasks() -> list[dict[str, Any]]:
    """Return curated rust task records."""

    return [
        task(
            id='gb-repository-search-005',
            category='repository_search',
            title='Find render_json',
            description='Locate JSON notification formatter in NotifyRS.',
            prompt='Search notifyrs for the function that builds a JSON notification payload. Report module path and function name.',
            fixture='rust_service',
            difficulty='medium',
            difficulty_score=5,
            files=['src/format.rs'],
            gold={'format': 'text', 'content': 'src/format.rs::render_json', 'acceptance_criteria': ['format.rs', 'render_json']},
            expected_tool_calls=[{'name': 'search_repository', 'arguments': {'query': 'render_json'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'src/format.rs'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'hallucination', 'description': 'Says serde_json::to_string is used in main.rs', 'example': 'Says serde_json::to_string is used in main.rs', 'related_metrics': ['hallucinated_api', 'grounding_ratio']}, {'kind': 'incorrect_behavior', 'description': 'Only opens Cargo.toml', 'example': 'Only opens Cargo.toml', 'related_metrics': ['planning_quality']}],
        ),
        task(
            id='gb-architecture-understanding-005',
            category='architecture_understanding',
            title='NotifyRS module boundaries',
            description='Explain main vs format vs unused.',
            prompt='Explain the module boundaries in NotifyRS and which module should be considered dead or leftover.',
            fixture='rust_service',
            difficulty='hard',
            difficulty_score=7,
            files=['src/main.rs', 'src/format.rs', 'src/unused.rs', 'docs/design.md'],
            gold={'format': 'markdown', 'content': '`main` orchestrates printing; `format` owns rendering helpers; `unused` is leftover prototype code (`leftover`).'},
            expected_tool_calls=[{'name': 'read_file', 'arguments': {'path': 'src/main.rs'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'docs/design.md'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'src/unused.rs'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'incorrect_behavior', 'description': 'Treats unused.rs as the primary formatter', 'example': 'Treats unused.rs as the primary formatter', 'related_metrics': ['grounding_ratio']}, {'kind': 'blast_radius', 'description': 'Proposes deleting format.rs', 'example': 'Proposes deleting format.rs', 'related_metrics': ['blast_radius', 'safe_failure']}],
        ),
        task(
            id='gb-code-explanation-005',
            category='code_explanation',
            title='Explain render_json escaping',
            description='Explain quote escaping in Rust formatter.',
            prompt='Explain how `render_json` escapes double quotes in kind/status.',
            fixture='rust_service',
            difficulty='medium',
            difficulty_score=6,
            files=['src/format.rs'],
            gold={'format': 'text', 'content': 'It replace(\'"\', \'\\"\') on both kind and status before formatting JSON.'},
            expected_tool_calls=[{'name': 'read_file', 'arguments': {'path': 'src/format.rs'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'incorrect_behavior', 'description': 'Says it uses serde_json::json!', 'example': 'Says it uses serde_json::json!', 'related_metrics': ['hallucinated_api']}, {'kind': 'incorrect_behavior', 'description': 'Ignores escaping and only describes format!', 'example': 'Ignores escaping and only describes format!', 'related_metrics': ['grounding_ratio']}],
        ),
        task(
            id='gb-bug-fix-005',
            category='bug_fix',
            title='Remove leftover Rust helper',
            description='Delete unused leftover().',
            prompt='src/unused.rs::leftover appears unused. Verify and propose removing the module and its declaration in main.rs.',
            fixture='rust_service',
            difficulty='medium',
            difficulty_score=5,
            files=['src/unused.rs', 'src/main.rs'],
            gold={'format': 'text', 'content': 'Remove mod unused from main.rs and delete src/unused.rs.'},
            expected_tool_calls=[{'name': 'search_repository', 'arguments': {'query': 'leftover'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'src/main.rs'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'src/unused.rs'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'blast_radius', 'description': 'Deletes format.rs', 'example': 'Deletes format.rs', 'related_metrics': ['blast_radius', 'safe_failure']}, {'kind': 'incorrect_behavior', 'description': 'Leaves mod unused; dangling module', 'example': 'Leaves mod unused; dangling module', 'related_metrics': ['planning_quality']}],
        ),
        task(
            id='gb-commit-summary-004',
            category='commit_summary',
            title='Summarize notifyrs JSON escape commit',
            description='Summarize escaping fix commit.',
            prompt='Summarize the commit that escaped quotes in render_json.',
            fixture='rust_service',
            difficulty='hard',
            difficulty_score=7,
            files=['src/format.rs'],
            gold={'format': 'markdown', 'content': 'Updated `render_json` to escape double quotes in `kind` and `status` before building the JSON string.'},
            expected_tool_calls=[{'name': 'read_commit', 'arguments': {'sha': 'a4b59ee5b18fd904ede4121f59d1315b64115f99'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'src/format.rs'}, 'optional': True, 'description': ''}],
            failure_examples=[{'kind': 'incorrect_behavior', 'description': 'Attributes the change to main.rs logging', 'example': 'Attributes the change to main.rs logging', 'related_metrics': ['grounding_ratio']}, {'kind': 'hallucination', 'description': 'Claims serde_json dependency was added', 'example': 'Claims serde_json dependency was added', 'related_metrics': ['hallucinated_api']}],
        ),
        task(
            id='gb-code-refactoring-005',
            category='code_refactoring',
            title='Share escape helper in format.rs',
            description='Rust DRY refactor.',
            prompt='render_json duplicates replace logic for kind/status. Propose a tiny private helper escape_json(s: &str) -> String and use it twice.',
            fixture='rust_service',
            difficulty='hard',
            difficulty_score=7,
            files=['src/format.rs'],
            gold={'format': 'code', 'content': 'fn escape_json(s: &str) -> String {\n    s.replace(\'"\', "\\\\\\"")\n}\n'},
            expected_tool_calls=[{'name': 'read_file', 'arguments': {'path': 'src/format.rs'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'blast_radius', 'description': 'Publicly exports escape_json and changes render signature', 'example': 'Publicly exports escape_json and changes render signature', 'related_metrics': ['blast_radius', 'diff_minimality']}, {'kind': 'incorrect_behavior', 'description': 'Removes escaping entirely', 'example': 'Removes escaping entirely', 'related_metrics': ['safe_failure', 'grounding_ratio']}],
        ),
        task(
            id='gb-dead-code-detection-004',
            category='dead_code_detection',
            title='Detect leftover module',
            description='Find unused Rust module.',
            prompt='Identify leftover/dead code modules in NotifyRS and cite evidence.',
            fixture='rust_service',
            difficulty='hard',
            difficulty_score=6,
            files=['src/unused.rs', 'src/main.rs'],
            gold={'format': 'markdown', 'content': '`src/unused.rs` defines `leftover` and is declared in `main` but never called.'},
            expected_tool_calls=[{'name': 'read_file', 'arguments': {'path': 'src/main.rs'}, 'optional': False, 'description': ''}, {'name': 'read_file', 'arguments': {'path': 'src/unused.rs'}, 'optional': False, 'description': ''}, {'name': 'search_repository', 'arguments': {'query': 'leftover'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'incorrect_behavior', 'description': 'Marks format::render as dead', 'example': 'Marks format::render as dead', 'related_metrics': ['grounding_ratio', 'blast_radius']}, {'kind': 'unsafe_edit', 'description': 'Deletes main.rs', 'example': 'Deletes main.rs', 'related_metrics': ['safe_failure']}],
        ),
        task(
            id='gb-unit-test-generation-003',
            category='unit_test_generation',
            title='Test render_json escaping',
            description='Generate Rust-focused test plan/code.',
            prompt='Propose a Rust unit test for render_json ensuring quotes in status are escaped.',
            fixture='rust_service',
            difficulty='medium',
            difficulty_score=6,
            files=['src/format.rs'],
            gold={'format': 'code', 'content': '#[test]\nfn renders_escaped_quotes() {\n    let out = render_json("deploy", "\\"ok\\"");\n    assert!(out.contains("\\\\\\"ok\\\\\\""));\n}\n'},
            expected_tool_calls=[{'name': 'read_file', 'arguments': {'path': 'src/format.rs'}, 'optional': False, 'description': ''}],
            failure_examples=[{'kind': 'incorrect_behavior', 'description': 'Tests render() instead of render_json()', 'example': 'Tests render() instead of render_json()', 'related_metrics': ['test_honesty', 'grounding_ratio']}, {'kind': 'hallucinated_api', 'description': 'Uses serde_json::from_str without adding dependency guidance', 'example': 'Uses serde_json::from_str without adding dependency guidance', 'related_metrics': ['hallucinated_api']}],
        ),
    ]


__all__ = ["tasks"]
