#!/usr/bin/env python3
"""Build the deterministic Fantasy Operations free-agent signal dataset.

The input is the already materialized central player-signal dataset. This layer
only selects players that are currently unowned in the fantasy league according
to the central ownership model. It does not browse, call providers, read the
Players.json IsFreeAgent field, or emit roster recommendations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
DATASET_ID = "free-agent-signals"
SOURCE_DATASET_ID = "player-signals"
SELECTION_RULE = (
    "configured fantasy positions with ownership.status == fantasy_free_agent in player-signals"
)


class FreeAgentMaterializationError(RuntimeError):
    """Raised when the free-agent dataset cannot be built safely."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FreeAgentMaterializationError(f"Could not load JSON from {path}: {exc}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise FreeAgentMaterializationError("Unexpected free-agent materialization config schema version")
    if (config.get("population") or {}).get("ownership_status") != "fantasy_free_agent":
        raise FreeAgentMaterializationError(
            "Free-agent materialization must select ownership_status=fantasy_free_agent"
        )
    positions = (config.get("population") or {}).get("positions")
    if not isinstance(positions, list) or not positions:
        raise FreeAgentMaterializationError("Free-agent materialization requires configured positions")
    normalized = [str(position).upper() for position in positions]
    if len(normalized) != len(set(normalized)):
        raise FreeAgentMaterializationError("Free-agent materialization positions must be unique")
    if any(position not in {"QB", "RB", "WR", "TE", "K"} for position in normalized):
        raise FreeAgentMaterializationError("Unsupported free-agent materialization position")


def validate_source(source: dict[str, Any]) -> None:
    if source.get("schema_version") != 1 or source.get("dataset_id") != SOURCE_DATASET_ID:
        raise FreeAgentMaterializationError("Input is not a schema-version-1 player-signals dataset")
    fingerprint = source.get("input_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise FreeAgentMaterializationError("player-signals input_fingerprint is missing or invalid")
    players = source.get("players")
    if not isinstance(players, list) or not players:
        raise FreeAgentMaterializationError("player-signals must contain a non-empty players array")
    quality = source.get("quality")
    if not isinstance(quality, dict) or quality.get("status") not in {"ok", "warning"}:
        raise FreeAgentMaterializationError("player-signals quality must be ok or warning")


def source_ownership_status(player: dict[str, Any]) -> str:
    ownership = player.get("ownership")
    if not isinstance(ownership, dict):
        raise FreeAgentMaterializationError(
            f"Player {player.get('player_id')} has no structured ownership record"
        )
    status = ownership.get("status")
    if not isinstance(status, str) or not status:
        raise FreeAgentMaterializationError(
            f"Player {player.get('player_id')} has no ownership status"
        )
    return status


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "generated_at",
        "input_fingerprint",
        "source",
        "population",
        "players",
        "quality",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise FreeAgentMaterializationError(f"Output missing required keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION or data["dataset_id"] != DATASET_ID:
        raise FreeAgentMaterializationError("Unexpected free-agent output identity")
    player_ids = [str(player.get("player_id")) for player in data["players"]]
    if len(player_ids) != len(set(player_ids)):
        raise FreeAgentMaterializationError("Free-agent output contains duplicate player IDs")
    if data["population"]["player_count"] != len(data["players"]):
        raise FreeAgentMaterializationError("Free-agent population count does not match players array")
    if any(source_ownership_status(player) != "fantasy_free_agent" for player in data["players"]):
        raise FreeAgentMaterializationError("Free-agent output contains a rostered player")


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise FreeAgentMaterializationError("Free-agent materialization config must be an object")
    validate_config(config)

    source_relative = config["source"]["player_signals"]
    source_path = root / source_relative
    source = load_json(source_path)
    if not isinstance(source, dict):
        raise FreeAgentMaterializationError("player-signals input must be an object")
    validate_source(source)

    allowed_positions = {str(position).upper() for position in config["population"]["positions"]}
    source_players = source["players"]
    expected_ids: list[str] = []
    selected: list[dict[str, Any]] = []
    position_counts: Counter[str] = Counter()

    for player in source_players:
        if not isinstance(player, dict):
            raise FreeAgentMaterializationError("player-signals contains a non-object player row")
        player_id = player.get("player_id")
        position = str(player.get("position") or "").upper()
        if player_id is None:
            raise FreeAgentMaterializationError("player-signals contains a player without player_id")
        if position not in allowed_positions:
            continue
        if source_ownership_status(player) != "fantasy_free_agent":
            continue

        expected_ids.append(str(player_id))
        selected.append(dict(player))
        position_counts[position] += 1

    selected.sort(
        key=lambda player: (
            str(player.get("position") or ""),
            str(player.get("name") or "").casefold(),
            str(player.get("player_id")),
        )
    )

    selected_ids = [str(player["player_id"]) for player in selected]
    if len(expected_ids) != len(set(expected_ids)):
        raise FreeAgentMaterializationError("player-signals contains duplicate eligible free-agent IDs")
    if set(selected_ids) != set(expected_ids) or len(selected_ids) != len(expected_ids):
        raise FreeAgentMaterializationError("Free-agent selection is incomplete")

    source_quality = source["quality"]
    fingerprint_payload = {
        "config": config,
        "source_dataset_id": source["dataset_id"],
        "source_input_fingerprint": source["input_fingerprint"],
        "selected_player_ids": selected_ids,
    }

    result = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": source.get("generated_at"),
        "input_fingerprint": sha256_text(canonical_json(fingerprint_payload)),
        "source": {
            "dataset_id": SOURCE_DATASET_ID,
            "path": source_relative,
            "input_fingerprint": source["input_fingerprint"],
        },
        "population": {
            "source_player_count": len(source_players),
            "player_count": len(selected),
            "positions": sorted(allowed_positions),
            "position_counts": dict(sorted(position_counts.items())),
            "selection_rule": SELECTION_RULE,
        },
        "players": selected,
        "quality": {
            "status": source_quality["status"],
            "source_quality_status": source_quality["status"],
            "source_issue_count": int(source_quality.get("issue_count") or 0),
            "selection_count_matches_source": True,
        },
    }
    validate_output(result)
    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/free-agent-materialization.json"),
    )
    parser.add_argument("--check", action="store_true", help="Build and validate without writing output")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise FreeAgentMaterializationError("Free-agent materialization config must be an object")
    result = build(root, config_path)
    if args.check:
        print(
            f"Validated {result['population']['player_count']} fantasy free agents; "
            f"quality={result['quality']['status']}."
        )
        return 0

    output_path = root / config["output"]["free_agent_signals"]
    write_json(output_path, result)
    print(
        f"Wrote {output_path.relative_to(root)} with "
        f"{result['population']['player_count']} fantasy free agents."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
