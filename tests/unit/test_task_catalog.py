"""TaskCatalog filtering tests."""

from __future__ import annotations

from githubbench_delta.core.models import Difficulty, TaskCategory, TaskInput
from githubbench_delta.tasks.catalog import TaskCatalog
from githubbench_delta.tasks.registry import create_task


def test_catalog_filters() -> None:
    catalog = TaskCatalog(
        [
            create_task(
                TaskCategory.BUG_FIX,
                id="b1",
                difficulty=Difficulty.HARD,
                language="python",
                dataset_version="v1",
                tags=["x", "y"],
                input=TaskInput(prompt="bug", repository_url="https://example.com/r1"),
            ),
            create_task(
                TaskCategory.DOCUMENTATION,
                id="d1",
                difficulty=Difficulty.EASY,
                language="markdown",
                dataset_version="v2",
                tags=["x"],
                input=TaskInput(prompt="docs"),
            ),
        ]
    )
    assert len(catalog.filter(difficulty="hard")) == 1
    assert len(catalog.filter(language="markdown")) == 1
    assert len(catalog.filter(category=TaskCategory.BUG_FIX)) == 1
    assert len(catalog.filter(dataset_version="v1")) == 1
    assert len(catalog.filter(tags=["x", "y"])) == 1
    assert len(catalog.filter(repository="https://example.com/r1")) == 1
    assert catalog.get("d1") is not None
