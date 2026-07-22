"""Plugin registration for Python-defined research experiments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from githubbench_delta.research.models import ResearchExperiment

_PLUGIN_EXPERIMENTS: dict[str, ResearchExperiment] = {}


def register_experiment(exp: ResearchExperiment | dict[str, Any]) -> ResearchExperiment:
    """Register a ResearchExperiment (decorator target or direct call)."""

    model = exp if isinstance(exp, ResearchExperiment) else ResearchExperiment.model_validate(exp)
    _PLUGIN_EXPERIMENTS[model.id] = model
    return model


def experiment_plugin(
    fn: Callable[[], ResearchExperiment | dict[str, Any]],
) -> Callable[[], ResearchExperiment]:
    """Decorator: function returns an experiment definition; registered on import."""

    def wrapper() -> ResearchExperiment:
        return register_experiment(fn())

    # Eager registration on decoration
    register_experiment(fn())
    return wrapper


def registered_plugins() -> dict[str, ResearchExperiment]:
    return dict(_PLUGIN_EXPERIMENTS)


def clear_plugins() -> None:
    _PLUGIN_EXPERIMENTS.clear()
