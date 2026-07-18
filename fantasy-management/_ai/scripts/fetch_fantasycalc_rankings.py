#!/usr/bin/env python3
"""Public FantasyCalc fetcher entry point for the categorized ranking layout."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_IMPL_PATH = Path(__file__).with_name("fetch_fantasycalc_rankings_impl.py")
_SPEC = importlib.util.spec_from_file_location("_fantasycalc_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Cannot load FantasyCalc implementation: {_IMPL_PATH}")
_IMPL = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _IMPL
_SPEC.loader.exec_module(_IMPL)

_OLD_ROOT = "fantasy-management/sources/external-rankings/fantasycalc"
_NEW_ROOT = "fantasy-management/sources/external-rankings/market-value/fantasycalc"


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


def ranking_root(repo_root: Path, config: dict[str, Any]) -> Path:
    return (
        repo_root
        / "fantasy-management"
        / "sources"
        / "external-rankings"
        / "market-value"
        / "fantasycalc"
        / str(config["ranking_id"])
    )


_ORIGINAL_BUILD_METADATA = _IMPL.build_metadata


def build_metadata(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _replace_paths(_ORIGINAL_BUILD_METADATA(*args, **kwargs))


# Schema 3 forces one canonical-path refresh after the directory migration.
_IMPL.SCHEMA_VERSION = max(int(_IMPL.SCHEMA_VERSION), 3)
_IMPL.ANALYSIS_METADATA_FILE = f"{_NEW_ROOT}/analysis-metadata.json"
_IMPL.ranking_root = ranking_root
_IMPL.build_metadata = build_metadata

for _name in dir(_IMPL):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_IMPL, _name)


if __name__ == "__main__":
    raise SystemExit(_IMPL.main())
