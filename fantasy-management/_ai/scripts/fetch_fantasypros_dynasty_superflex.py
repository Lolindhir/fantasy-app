#!/usr/bin/env python3
"""Public FantasyPros Dynasty fetcher entry point for the categorized ranking layout."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_IMPL_PATH = Path(__file__).with_name("fetch_fantasypros_dynasty_superflex_impl.py")
_SPEC = importlib.util.spec_from_file_location("_fantasypros_dynasty_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Cannot load FantasyPros Dynasty implementation: {_IMPL_PATH}")
_IMPL = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _IMPL
_SPEC.loader.exec_module(_IMPL)

_OLD_ROOT = "fantasy-management/sources/external-rankings/fantasypros"
_NEW_ROOT = "fantasy-management/sources/external-rankings/expert-consensus/fantasypros"


def _replace_paths(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(_OLD_ROOT, _NEW_ROOT)
    if isinstance(value, dict):
        return {key: _replace_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_paths(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_paths(item) for item in value)
    return value


def ranking_root(repo_root: Path) -> Path:
    return (
        repo_root
        / "fantasy-management"
        / "sources"
        / "external-rankings"
        / "expert-consensus"
        / "fantasypros"
        / _IMPL.RANKING_ID
    )


_ORIGINAL_BUILD_METADATA = _IMPL.build_metadata


def build_metadata(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _replace_paths(_ORIGINAL_BUILD_METADATA(*args, **kwargs))


# Schema 6 forces one canonical-path refresh after the directory migration.
_IMPL.SCHEMA_VERSION = max(int(_IMPL.SCHEMA_VERSION), 6)
_IMPL.ranking_root = ranking_root
_IMPL.build_metadata = build_metadata

for _name in dir(_IMPL):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_IMPL, _name)


if __name__ == "__main__":
    raise SystemExit(_IMPL.main())
