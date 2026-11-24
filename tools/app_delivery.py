#!/usr/bin/env python3
"""Neutral helpers shared by the App consumer generators (tools/*_app_publish.py).

Consumer generators must not import each other (tools/tests/test_derived_layer_import_gate.py); the semantic no-op
writer, the JSON helpers and the warning annotation live here instead. This module is neither a Shared Derived root
nor a consumer: it holds no domain rule and reads no product.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from matchup_context import diff_values  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def warn(title: str, message: str) -> None:
    print(f"::warning title={title}::{message}", file=sys.stderr)


def history_matchup_seasons(repo_root: Path, league_id: str, current: int) -> list[int]:
    """Earlier seasons whose canonical league source is complete (the Matchups history rule)."""
    root = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons"
    seasons: list[int] = []
    for folder in sorted(root.iterdir()) if root.is_dir() else []:
        if not folder.name.isdigit() or int(folder.name) >= current:
            continue
        league_file = folder / "league.json"
        if league_file.is_file() and load_json(league_file).get("Status") == "complete":
            seasons.append(int(folder.name))
    return seasons


class Writer:
    """Writes App files only where they differ semantically and records the Timestamps.json keys to refresh."""

    def __init__(self, repo_root: Path, now: datetime) -> None:
        self.data = repo_root / "public" / "data"
        self.stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.changed: list[str] = []
        self._stamped: list[str] = []

    def put(self, relative: str, payload: Any, timestamp_key: str | None = None) -> None:
        path = self.data / relative
        if path.is_file() and not diff_values(load_json(path), json.loads(json.dumps(payload))):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_json(payload), encoding="utf-8")
        self.changed.append(f"public/data/{relative}")
        if timestamp_key:
            self._stamped.append(timestamp_key)

    def finish(self) -> list[str]:
        if self._stamped:
            path = self.data / "Timestamps.json"
            timestamps = load_json(path) if path.is_file() else {}
            for key in self._stamped:
                timestamps[key] = self.stamp
            path.write_text(dump_json(timestamps), encoding="utf-8")
            self.changed.append("public/data/Timestamps.json")
        return self.changed
