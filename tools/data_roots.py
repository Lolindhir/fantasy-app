"""Central definition of the repository data root directories (Issue #788, step 0).

Every Python module under ``tools/`` takes the root directory names from here instead of
spelling them out. A later rename of a root therefore changes one constant. The PowerShell
counterpart lives in ``public/requests/utils/ConfigUtils.psm1`` (``Get-DataSourceRoot``,
``Get-DataDerivedRoot``, ``Get-DataMetaRoot``); ``tools/tests/test_data_roots.py`` keeps both
in sync and forbids the spelled-out names in production code.

All values are repository-root-relative POSIX paths.
"""
from __future__ import annotations

from pathlib import Path

# Persistent provider raw data plus canonical NFL and League facts (written by sync workflows only).
DATA_SOURCE_ROOT = "data-source"
# Shared Derived Data with full history (written by materializers only, ADR-038).
DATA_DERIVED_ROOT = "data-derived"
# Hand-maintained league metadata (introduced by #986; no producer yet).
DATA_META_ROOT = "data-meta"


def data_source_dir(repo_root: Path) -> Path:
    return repo_root / DATA_SOURCE_ROOT


def data_derived_dir(repo_root: Path) -> Path:
    return repo_root / DATA_DERIVED_ROOT


def data_meta_dir(repo_root: Path) -> Path:
    return repo_root / DATA_META_ROOT
