"""Central definition of the repository data root directories (Issue #788, step 0).

Every Python module under ``tools/`` takes the root directory names from here instead of
spelling them out. A later rename of a root therefore changes one constant. The PowerShell
counterpart lives in ``public/requests/utils/ConfigUtils.psm1`` (``Get-DataSourceRoot``,
``Get-DataDerivedRoot``, ``Get-DataMetaRoot``, ``Get-DataCanonicalRoot``); ``tools/tests/test_data_roots.py`` keeps both
in sync and forbids the spelled-out names in production code.

All values are repository-root-relative POSIX paths.
"""
from __future__ import annotations

from pathlib import Path

# Persistent provider raw data plus canonical NFL and League facts (written by sync workflows only).
DATA_SOURCE_ROOT = "data-source"
# Issue #1618 M2a: reserved root; no production partition is routed here yet.
DATA_CANONICAL_ROOT = "data-canonical"
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



def data_canonical_dir(repo_root: Path) -> Path:
    return repo_root / DATA_CANONICAL_ROOT


# Only the proposed pilot family is modeled until its dependency closure is proven.
# The explicit migration set is empty in M2a; it is not an environment override.
_MIGRATED_PARTITIONS: frozenset[tuple[str, int]] = frozenset()


def canonical_partition_path(
    repo_root: Path, dataset: str, season: int, *, allow_create: bool = False,
) -> Path:
    """Resolve one supported Canonical partition identically for reads and writes.

    A caller may allow creation only after establishing a genuinely new partition.
    Existing and migrated partitions must be present. No fallback to a second root
    is permitted. M2a has no production callers; activation requires the pilot
    cutover and its writer/restore/CI gates.
    """
    if dataset != "nflverse.combine":
        raise ValueError(f"Unsupported canonical dataset: {dataset!r}")
    if type(season) is not int or not 1000 <= season <= 9999:
        raise ValueError(f"Invalid canonical season: {season!r}")
    relative = Path("nfl", "combine", f"{season}.json")
    legacy = data_source_dir(repo_root) / relative
    canonical = data_canonical_dir(repo_root) / relative
    migrated = (dataset, season) in _MIGRATED_PARTITIONS
    selected, other = (canonical, legacy) if migrated else (legacy, canonical)
    if other.exists() or other.is_symlink():
        raise ValueError(f"Unexpected partition at inactive route: {other}")
    # Disallow a symlink anywhere below the supplied root for this writer-capable
    # locator; shadow fixtures must use isolated real directories.
    for path in (selected, *selected.parents):
        if path == repo_root:
            break
        if path.is_symlink():
            raise ValueError(f"Symlink in canonical partition route: {path}")
    if selected.exists():
        if not selected.is_file():
            raise ValueError(f"Canonical partition is not a file: {selected}")
    elif migrated or not allow_create:
        raise FileNotFoundError(f"Expected canonical partition is absent: {selected}")
    return selected
