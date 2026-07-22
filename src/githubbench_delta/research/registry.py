"""YAML-driven experiment registry with auto-discovery."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import yaml

from githubbench_delta.research.models import EvidenceNode, ResearchExperiment, ResearchProject
from githubbench_delta.research.plugins import registered_plugins

DEFAULT_EXPERIMENTS_DIR = Path("configs/research/experiments")
DEFAULT_EVIDENCE_PATH = Path("configs/research/evidence_registry.yaml")
DEFAULT_PROJECTS_PATH = Path("configs/research/projects.yaml")


class ExperimentRegistry:
    """Load all research experiments from YAML + optional Python plugins."""

    def __init__(
        self,
        *,
        experiments_dir: Path | str | None = None,
        evidence_path: Path | str | None = None,
        projects_path: Path | str | None = None,
    ) -> None:
        self.experiments_dir = Path(experiments_dir or DEFAULT_EXPERIMENTS_DIR)
        self.evidence_path = Path(evidence_path or DEFAULT_EVIDENCE_PATH)
        self.projects_path = Path(projects_path or DEFAULT_PROJECTS_PATH)
        self._experiments: dict[str, ResearchExperiment] = {}
        self._evidence: dict[str, EvidenceNode] = {}
        self._projects: dict[str, ResearchProject] = {}

    @classmethod
    def load_default(cls) -> ExperimentRegistry:
        reg = cls()
        reg.reload()
        return reg

    def reload(self) -> None:
        self._experiments.clear()
        self._load_yaml_experiments()
        self._discover_python_plugins()
        # Plugins overlay / add
        for exp in registered_plugins().values():
            self._experiments[exp.id] = exp
        self._load_evidence()
        self._load_projects()

    def _load_yaml_experiments(self) -> None:
        if not self.experiments_dir.is_dir():
            return
        for path in sorted(self.experiments_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not data:
                continue
            exp = ResearchExperiment.model_validate(data)
            self._experiments[exp.id] = exp

    def _discover_python_plugins(self) -> None:
        """Import research.experiments submodules so @experiment_plugin runs."""

        try:
            pkg = importlib.import_module("githubbench_delta.research.experiments")
        except ModuleNotFoundError:
            return
        if not hasattr(pkg, "__path__"):
            return
        for mod in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
            importlib.import_module(mod.name)

    def _load_evidence(self) -> None:
        self._evidence.clear()
        if not self.evidence_path.is_file():
            return
        raw = yaml.safe_load(self.evidence_path.read_text(encoding="utf-8")) or {}
        for node in raw.get("nodes", []):
            n = EvidenceNode.model_validate(node)
            self._evidence[n.id] = n

    def _load_projects(self) -> None:
        self._projects.clear()
        if not self.projects_path.is_file():
            return
        raw = yaml.safe_load(self.projects_path.read_text(encoding="utf-8")) or {}
        for proj in raw.get("projects", []):
            p = ResearchProject.model_validate(proj)
            self._projects[p.id] = p

    def get(self, experiment_id: str) -> ResearchExperiment | None:
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[ResearchExperiment]:
        return sorted(self._experiments.values(), key=lambda e: e.id)

    def list_by_status(self, status: str) -> list[ResearchExperiment]:
        return [e for e in self.list_experiments() if e.status == status]

    def evidence_nodes(self) -> list[EvidenceNode]:
        return sorted(self._evidence.values(), key=lambda n: n.id)

    def get_evidence(self, node_id: str) -> EvidenceNode | None:
        return self._evidence.get(node_id)

    def projects(self) -> list[ResearchProject]:
        return sorted(self._projects.values(), key=lambda p: p.id)
