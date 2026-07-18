"""Dataset loading, validation, and manifest generation."""

from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.datasets.factory import get_loader_for_path, load_tasks
from githubbench_delta.datasets.manifest import (
    DatasetManifest,
    compute_content_hash,
    generate_manifest,
    load_dataset_metadata,
    write_manifest,
)
from githubbench_delta.datasets.metadata import DatasetMetadata
from githubbench_delta.datasets.repositories import (
    RepositoryRef,
    clone_repository,
    compute_local_fingerprint,
    fingerprint_repository,
    resolve_local_path,
)
from githubbench_delta.datasets.validators import CorpusQualityValidator, DatasetValidator

__all__ = [
    "BaseDatasetLoader",
    "CorpusQualityValidator",
    "DatasetMetadata",
    "DatasetManifest",
    "DatasetValidator",
    "RepositoryRef",
    "clone_repository",
    "compute_content_hash",
    "compute_local_fingerprint",
    "fingerprint_repository",
    "generate_manifest",
    "get_loader_for_path",
    "load_dataset_metadata",
    "load_tasks",
    "resolve_local_path",
    "write_manifest",
]
