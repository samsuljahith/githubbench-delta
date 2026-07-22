"""Deterministic twin-task generation (sidecar only; no corpus mutation)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from githubbench_delta.datasets.factory import load_tasks
from githubbench_delta.memorization.helpers import normalize_prompt
from githubbench_delta.memorization.models import GENERATOR_VERSION, TwinTaskSpec
from githubbench_delta.tasks.base import BaseTask

# Ordered synonym replacements for deterministic paraphrases (no LLM).
_SYNONYM_PAIRS: tuple[tuple[str, str], ...] = (
    (r"\bfind\b", "locate"),
    (r"\blocate\b", "identify"),
    (r"\bwhere is\b", "what is the location of"),
    (r"\bexplain\b", "describe"),
    (r"\bdescribe\b", "summarize"),
    (r"\blist\b", "enumerate"),
    (r"\bshow\b", "present"),
    (r"\bwhich module\b", "what module"),
    (r"\bkeep it to\b", "limit the answer to"),
    (r"\brepository\b", "codebase"),
    (r"\bfile\b", "source file"),
)


def _paraphrase_text(text: str) -> str:
    out = text
    for pattern, repl in _SYNONYM_PAIRS:
        out = re.sub(pattern, repl, out, count=1, flags=re.IGNORECASE)
    # Light clause reorder: if two sentences, swap them
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", out) if p.strip()]
    if len(parts) >= 2:
        out = " ".join([parts[1], parts[0], *parts[2:]])
    if normalize_prompt(out) == normalize_prompt(text):
        out = f"Rephrase and answer carefully: {text}"
    return out


def _task_to_record(task: BaseTask) -> dict[str, Any]:
    """Best-effort serialization of a loaded BaseTask to a dict."""

    if hasattr(task, "model_dump"):
        data = task.model_dump(mode="json")  # type: ignore[attr-defined]
        if isinstance(data, dict) and "id" in data:
            return data
    # Fallback via common attributes
    prompt = ""
    files: list[str] = []
    if task.input is not None:
        prompt = getattr(task.input, "prompt", "") or ""
        files = list(getattr(task.input, "files", []) or [])
    repo = None
    if task.repository is not None:
        repo = {
            "url": getattr(task.repository, "url", None),
            "local_path": getattr(task.repository, "local_path", None),
            "branch": getattr(task.repository, "branch", None),
            "commit_sha": getattr(task.repository, "commit_sha", None),
        }
    gold = None
    if task.gold_answer is not None:
        gold = {
            "format": getattr(task.gold_answer, "format", None),
            "content": getattr(task.gold_answer, "content", None),
        }
    return {
        "id": task.id,
        "category": str(task.category),
        "title": task.title,
        "description": task.description,
        "difficulty": str(getattr(task, "difficulty", "medium")),
        "language": getattr(task, "language", None),
        "repository": repo,
        "input": {"prompt": prompt, "files": files},
        "gold_answer": gold,
        "expected_tool_calls": [
            t.model_dump(mode="json") if hasattr(t, "model_dump") else t
            for t in (task.expected_tool_calls or [])
        ],
        "metadata": {"extra": dict(getattr(getattr(task, "metadata", None), "extra", {}) or {})},
    }


def _load_raw_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


class TwinTaskGenerator:
    """Generate paraphrase twin task specs without mutating the corpus."""

    def __init__(self, *, generator_version: str = GENERATOR_VERSION) -> None:
        self.generator_version = generator_version

    def generate_from_records(self, records: list[dict[str, Any]]) -> list[TwinTaskSpec]:
        specs: list[TwinTaskSpec] = []
        for parent in records:
            parent_id = str(parent.get("id", "")).strip()
            if not parent_id:
                continue
            twin_id = f"{parent_id}__twin_para_01"
            twin = copy.deepcopy(parent)
            twin["id"] = twin_id
            title = str(twin.get("title") or "")
            desc = str(twin.get("description") or "")
            prompt = ""
            inp = twin.get("input") or {}
            if isinstance(inp, dict):
                prompt = str(inp.get("prompt") or "")
                inp = dict(inp)
                inp["prompt"] = _paraphrase_text(prompt)
                twin["input"] = inp
            twin["title"] = _paraphrase_text(title) if title else title
            twin["description"] = _paraphrase_text(desc) if desc else desc

            meta = twin.get("metadata") if isinstance(twin.get("metadata"), dict) else {}
            meta = dict(meta or {})
            extra = dict(meta.get("extra") or {})
            extra.update(
                {
                    "parent_task_id": parent_id,
                    "twin_kind": "paraphrase",
                    "generator_version": self.generator_version,
                }
            )
            meta["extra"] = extra
            twin["metadata"] = meta
            twin["tags"] = list(twin.get("tags") or []) + ["mds_twin", "paraphrase"]

            specs.append(
                TwinTaskSpec(
                    id=twin_id,
                    parent_task_id=parent_id,
                    twin_kind="paraphrase",
                    generator_version=self.generator_version,
                    record=twin,
                )
            )
        return specs

    def generate_from_dataset(self, dataset_path: Path | str) -> list[TwinTaskSpec]:
        path = Path(dataset_path)
        # Prefer raw JSONL to preserve full SerializedTaskRecord fields
        if path.is_dir():
            jsonl = path / "tasks.jsonl"
            if jsonl.is_file():
                return self.generate_from_records(_load_raw_jsonl(jsonl))
            # Fall back to loader on directory metadata file
            raise FileNotFoundError(f"No tasks.jsonl under {path}")
        if path.suffix == ".jsonl":
            return self.generate_from_records(_load_raw_jsonl(path))
        tasks = load_tasks(path)
        records = [_task_to_record(t) for t in tasks]
        return self.generate_from_records(records)

    def write_jsonl(self, specs: list[TwinTaskSpec], output_path: Path | str) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(s.record, ensure_ascii=False) for s in specs]
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        # Also write an index of TwinTaskSpec metadata
        index = out.with_suffix(".index.json")
        index.write_text(
            json.dumps(
                [s.model_dump(mode="json") for s in specs],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return out
