#!/usr/bin/env python3
"""Public FantasyCalc fetcher entry point for the categorized ranking layout."""

from __future__ import annotations

import importlib.util
import json
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
_CANONICAL_PLAYERS_PATH = Path("public/data/Players.json")


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
_ORIGINAL_PARSE_ASSETS = _IMPL.parse_assets
_ORIGINAL_MAIN = _IMPL.main
_ACTIVE_REPO_ROOT: Path | None = None


def build_metadata(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _replace_paths(_ORIGINAL_BUILD_METADATA(*args, **kwargs))


def load_canonical_player_positions(repo_root: Path) -> dict[str, str]:
    """Load supported canonical offense positions keyed by Sleeper player ID."""

    players_path = repo_root / _CANONICAL_PLAYERS_PATH
    try:
        payload = json.loads(players_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _IMPL.FantasyCalcFetchError(
            f"Cannot read canonical player positions from {players_path}: {exc}"
        ) from exc
    if not isinstance(payload, list):
        raise _IMPL.FantasyCalcFetchError(
            f"Canonical Players.json is not an array: {players_path}"
        )

    positions: dict[str, str] = {}
    for player in payload:
        if not isinstance(player, dict):
            raise _IMPL.FantasyCalcFetchError(
                f"Canonical Players.json contains a non-object entry: {players_path}"
            )
        sleeper_id = str(player.get("ID") or "").strip()
        position = str(player.get("Position") or "").strip().upper()
        if not sleeper_id or position not in _IMPL.PLAYER_POSITIONS:
            continue
        previous = positions.get(sleeper_id)
        if previous is not None and previous != position:
            raise _IMPL.FantasyCalcFetchError(
                "Conflicting canonical positions for Sleeper player "
                f"{sleeper_id}: {previous!r} vs {position!r}"
            )
        positions[sleeper_id] = position
    return positions


def parse_assets(
    payload: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    canonical_player_positions: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Normalize FantasyCalc rows, resolving only explicit ``UNK`` via canonical IDs.

    FantasyCalc normally supplies one of QB/RB/WR/TE/PICK. A two-way player can be
    emitted as ``UNK`` even though the repository already has a canonical fantasy
    position for the same Sleeper ID. Only that explicit unknown sentinel is eligible
    for canonical resolution; every other unexpected provider position remains
    fail-closed in the implementation parser.
    """

    has_unknown = any(
        isinstance(entry.get("player"), dict)
        and str(entry["player"].get("position") or "").strip().upper() == "UNK"
        for entry in payload
        if isinstance(entry, dict)
    )
    if not has_unknown:
        return _ORIGINAL_PARSE_ASSETS(payload, config)

    positions = canonical_player_positions
    if positions is None and _ACTIVE_REPO_ROOT is not None:
        positions = load_canonical_player_positions(_ACTIVE_REPO_ROOT)
    if not positions:
        return _ORIGINAL_PARSE_ASSETS(payload, config)

    normalized_payload: list[dict[str, Any]] = []
    for entry in payload:
        player = entry.get("player") if isinstance(entry, dict) else None
        raw_position = (
            str(player.get("position") or "").strip().upper()
            if isinstance(player, dict)
            else ""
        )
        if raw_position != "UNK":
            normalized_payload.append(entry)
            continue

        sleeper_id = str(player.get("sleeperId") or "").strip()
        canonical_position = str(positions.get(sleeper_id) or "").strip().upper()
        if canonical_position not in _IMPL.PLAYER_POSITIONS:
            normalized_payload.append(entry)
            continue

        player_copy = dict(player)
        player_copy["position"] = canonical_position
        entry_copy = dict(entry)
        entry_copy["player"] = player_copy
        normalized_payload.append(entry_copy)
        name = str(player.get("name") or sleeper_id).strip()
        print(
            "[fantasycalc] note: resolved provider position UNK for "
            f"{name} via canonical Sleeper ID {sleeper_id} -> {canonical_position}",
            file=sys.stderr,
        )

    return _ORIGINAL_PARSE_ASSETS(normalized_payload, config)


def main(argv: list[str] | None = None) -> int:
    """Run the implementation with repository canonical positions available lazily."""

    args = _IMPL.parse_args(argv)
    global _ACTIVE_REPO_ROOT
    previous_repo_root = _ACTIVE_REPO_ROOT
    _ACTIVE_REPO_ROOT = args.repo_root.resolve()
    try:
        return _ORIGINAL_MAIN(argv)
    finally:
        _ACTIVE_REPO_ROOT = previous_repo_root


# Schema 3 forces one canonical-path refresh after the directory migration.
_IMPL.SCHEMA_VERSION = max(int(_IMPL.SCHEMA_VERSION), 3)
_IMPL.ANALYSIS_METADATA_FILE = f"{_NEW_ROOT}/analysis-metadata.json"
_IMPL.ranking_root = ranking_root
_IMPL.build_metadata = build_metadata
_IMPL.parse_assets = parse_assets
_IMPL.main = main

for _name in dir(_IMPL):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_IMPL, _name)


if __name__ == "__main__":
    raise SystemExit(_IMPL.main())
