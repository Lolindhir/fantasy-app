#!/usr/bin/env python3
"""Build provider-neutral Fantasy Operations inputs from repository data.

The script performs deterministic data preparation only. It does not browse the
web, call an AI service, make fantasy recommendations, or persist monitoring
state. Its output is a neutral read model for external research and analysis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


class MaterializationError(RuntimeError):
    """Raised when a required input cannot be materialized safely."""


@dataclass(frozen=True)
class SourceFile:
    id: str
    path: Path
    relative_path: str
    content_sha256: str
    source_timestamp: str | None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MaterializationError(f"Missing required JSON input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MaterializationError(f"Invalid JSON input {path}: {exc}") from exc


def load_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise MaterializationError(f"Missing required CSV input: {path}") from exc


def relative_to_root(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z0-9]+", text.casefold())
    while tokens and tokens[-1] in NAME_SUFFIXES:
        tokens.pop()
    return "".join(tokens)


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def optional_number(value: Any) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 4)


def optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_datetime(value: Any) -> datetime | None:
    text = optional_text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def max_timestamp(values: Iterable[Any]) -> str | None:
    parsed = [item for item in (parse_datetime(value) for value in values) if item]
    if not parsed:
        return None
    return max(parsed).isoformat().replace("+00:00", "Z")


def source_file(source_id: str, path: Path, root: Path, timestamp: Any = None) -> SourceFile:
    content = path.read_text(encoding="utf-8")
    return SourceFile(
        id=source_id,
        path=path,
        relative_path=relative_to_root(path, root),
        content_sha256=sha256_text(content),
        source_timestamp=max_timestamp([timestamp]),
    )


def index_rows(rows: list[dict[str, str]], *, sleeper_field: str | None = None) -> dict[str, Any]:
    by_sleeper: dict[str, dict[str, str]] = {}
    by_name_position: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if sleeper_field:
            sleeper_id = optional_text(row.get(sleeper_field))
            if sleeper_id:
                by_sleeper[sleeper_id] = row
        key = (normalize_name(row.get("name")), str(row.get("position") or "").upper())
        if key[0] and key[1]:
            by_name_position[key].append(row)
    return {
        "by_sleeper": by_sleeper,
        "by_name_position": by_name_position,
        "row_count": len(rows),
    }


def match_row(
    player: dict[str, Any],
    index: dict[str, Any],
    *,
    allow_sleeper: bool,
) -> tuple[dict[str, str] | None, str, list[str]]:
    player_id = str(player.get("ID") or "")
    if allow_sleeper and player_id and player_id in index["by_sleeper"]:
        return index["by_sleeper"][player_id], "sleeper_id", []

    key = (normalize_name(player.get("Name")), str(player.get("Position") or "").upper())
    candidates = index["by_name_position"].get(key, [])
    if len(candidates) == 1:
        return candidates[0], "normalized_name_position", []
    if len(candidates) > 1:
        team = str(player.get("TeamAbbr") or "").upper()
        team_candidates = [
            row
            for row in candidates
            if str(row.get("team") or "").upper() == team
        ]
        if len(team_candidates) == 1:
            return team_candidates[0], "normalized_name_position_team", []
        return None, "ambiguous", [str(row.get("name") or "") for row in candidates]
    return None, "missing", []


def percentile(rank: Any, row_count: int) -> float | None:
    parsed = optional_number(rank)
    if parsed is None or row_count <= 0:
        return None
    if row_count == 1:
        return 100.0
    value = ((row_count - float(parsed)) / (row_count - 1)) * 100
    return round(max(0.0, min(100.0, value)), 2)


def derive_injury_signal(player: dict[str, Any]) -> dict[str, Any]:
    details = (
        player.get("InjuryDetails")
        if isinstance(player.get("InjuryDetails"), dict)
        else {}
    )
    injured = bool(player.get("Injured"))
    designation = optional_text(details.get("Designation"))
    description = optional_text(details.get("Description"))
    return_date = optional_text(details.get("ReturnDate"))
    report_date = optional_text(details.get("Date"))
    has_signal = injured or any((designation, description, return_date, report_date))

    if injured and designation:
        coverage_status = "current_injury_signal"
    elif has_signal:
        coverage_status = "partial_injury_signal"
    else:
        coverage_status = "no_current_injury_signal"

    return {
        "coverage_status": coverage_status,
        "is_injured": injured,
        "designation": designation,
        "description": description,
        "reported_date": report_date,
        "return_date": return_date,
        "external_verification_priority": "high" if has_signal else "routine",
        "limitations": [
            "A missing structured signal is not proof of full health.",
            "Descriptions and designations are secondary-source inputs and require external verification when decision-relevant.",
        ],
    }


def extract_market(
    player: dict[str, Any],
    fp_index: dict[str, Any],
    fc_index: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    fp_row, fp_join, fp_candidates = match_row(player, fp_index, allow_sleeper=False)
    fc_row, fc_join, fc_candidates = match_row(player, fc_index, allow_sleeper=True)

    if not fp_row:
        issues.append(
            {"source": "fantasypros", "kind": fp_join, "candidates": fp_candidates}
        )
    if not fc_row:
        issues.append(
            {"source": "fantasycalc", "kind": fc_join, "candidates": fc_candidates}
        )

    return {
        "fantasypros": {
            "listed": fp_row is not None,
            "join_method": fp_join,
            "overall_rank": optional_number(fp_row.get("Rank")) if fp_row else None,
            "position_rank": optional_text(fp_row.get("position_rank")) if fp_row else None,
            "tier": optional_text(fp_row.get("tier")) if fp_row else None,
        },
        "fantasycalc": {
            "listed": fc_row is not None,
            "join_method": fc_join,
            "overall_rank": optional_number(fc_row.get("Rank")) if fc_row else None,
            "position_rank": optional_number(fc_row.get("position_rank")) if fc_row else None,
            "tier": optional_text(fc_row.get("tier")) if fc_row else None,
            "value": optional_number(fc_row.get("value")) if fc_row else None,
            "trend_30_day": optional_number(fc_row.get("trend_30_day")) if fc_row else None,
            "roster_percent": optional_number(fc_row.get("roster_percent")) if fc_row else None,
            "trade_frequency": optional_number(fc_row.get("trade_frequency")) if fc_row else None,
        },
    }, issues


def extract_adp(
    player: dict[str, Any],
    ppr_index: dict[str, Any],
    two_qb_index: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    ppr_row, ppr_join, ppr_candidates = match_row(
        player, ppr_index, allow_sleeper=False
    )
    two_row, two_join, two_candidates = match_row(
        player, two_qb_index, allow_sleeper=False
    )
    position = str(player.get("Position") or "").upper()
    primary_id = "two_qb_10_team" if position == "QB" else "ppr_8_team"
    primary_row = two_row if position == "QB" else ppr_row

    if not ppr_row:
        issues.append(
            {"source": "ffc_ppr_8_team", "kind": ppr_join, "candidates": ppr_candidates}
        )
    if not two_row and position == "QB":
        issues.append(
            {
                "source": "ffc_two_qb_10_team",
                "kind": two_join,
                "candidates": two_candidates,
            }
        )

    def row_view(
        row: dict[str, str] | None,
        join_method: str,
        row_count: int,
    ) -> dict[str, Any]:
        return {
            "listed": row is not None,
            "join_method": join_method,
            "rank": optional_number(row.get("Rank")) if row else None,
            "percentile": percentile(row.get("Rank"), row_count) if row else None,
            "adp": optional_number(row.get("adp")) if row else None,
            "times_drafted": optional_number(row.get("times_drafted")) if row else None,
            "stdev": optional_number(row.get("stdev")) if row else None,
            "sample_total_drafts": (
                optional_number(row.get("sample_total_drafts")) if row else None
            ),
            "sample_start_date": (
                optional_text(row.get("sample_start_date")) if row else None
            ),
            "sample_end_date": (
                optional_text(row.get("sample_end_date")) if row else None
            ),
        }

    ppr_view = row_view(ppr_row, ppr_join, ppr_index["row_count"])
    two_view = row_view(two_row, two_join, two_qb_index["row_count"])
    primary_view = two_view if position == "QB" else ppr_view
    return {
        "primary_format": primary_id,
        "primary_listed": primary_row is not None,
        "primary": primary_view,
        "ppr_8_team": ppr_view,
        "two_qb_10_team": two_view,
        "format_gap": (
            round(
                float(two_view["percentile"]) - float(ppr_view["percentile"]),
                2,
            )
            if two_view["percentile"] is not None
            and ppr_view["percentile"] is not None
            else None
        ),
    }, issues


def resolve_pointer(
    root: Path,
    source_id: str,
    pointer_path: str,
    timestamp_fields: list[str],
) -> tuple[SourceFile, SourceFile, list[dict[str, str]]]:
    pointer_file = root / pointer_path
    pointer = load_json(pointer_file)
    ranking_path = optional_text(pointer.get("ranking_file"))
    if not ranking_path:
        raise MaterializationError(f"Pointer has no ranking_file: {pointer_file}")
    ranking_file = root / ranking_path
    timestamp = max_timestamp(pointer.get(field) for field in timestamp_fields)
    return (
        source_file(f"{source_id}_pointer", pointer_file, root, timestamp),
        source_file(f"{source_id}_ranking", ranking_file, root, timestamp),
        load_csv(ranking_file),
    )


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "generated_at",
        "input_fingerprint",
        "managed_team",
        "sources",
        "players",
        "quality",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise MaterializationError(f"Output missing required keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise MaterializationError("Unexpected output schema version")
    player_ids = [player["player_id"] for player in data["players"]]
    if len(player_ids) != len(set(player_ids)):
        raise MaterializationError("Output contains duplicate player IDs")


def build(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_json(config_path)
    sources = config["sources"]
    league_path = root / sources["league"]
    players_path = root / sources["players"]
    timestamps_path = root / sources["timestamps"]

    league = load_json(league_path)
    players = load_json(players_path)
    timestamps = load_json(timestamps_path)
    if not isinstance(players, list):
        raise MaterializationError("Players input must be a JSON array")

    managed_config = config["managed_team"]
    team_id = str(managed_config["team_id"])
    teams = league.get("Teams") or []
    managed_team = next(
        (
            team
            for team in teams
            if str(team.get(managed_config["identity_field"])) == team_id
        ),
        None,
    )
    if managed_team is None:
        raise MaterializationError(f"Managed team {team_id} not found")

    fp_pointer_source, fp_ranking_source, fp_rows = resolve_pointer(
        root,
        "fantasypros",
        sources["fantasypros_latest"],
        ["fetched_at", "ranking_fetched_at", "snapshot_date"],
    )
    fc_pointer_source, fc_ranking_source, fc_rows = resolve_pointer(
        root,
        "fantasycalc",
        sources["fantasycalc_latest"],
        ["ranking_fetched_at", "raw_fetched_at", "snapshot_date"],
    )
    ppr_pointer_source, ppr_ranking_source, ppr_rows = resolve_pointer(
        root,
        "ffc_ppr",
        sources["adp_ppr_latest"],
        ["ranking_fetched_at", "raw_fetched_at", "snapshot_date"],
    )
    two_pointer_source, two_ranking_source, two_rows = resolve_pointer(
        root,
        "ffc_two_qb",
        sources["adp_two_qb_latest"],
        ["ranking_fetched_at", "raw_fetched_at", "snapshot_date"],
    )

    player_timestamp = timestamps.get("Players") if isinstance(timestamps, dict) else None
    league_timestamp = timestamps.get("League") if isinstance(timestamps, dict) else None
    source_files = [
        source_file("league", league_path, root, league_timestamp),
        source_file("players", players_path, root, player_timestamp),
        source_file(
            "timestamps",
            timestamps_path,
            root,
            max_timestamp(timestamps.values()) if isinstance(timestamps, dict) else None,
        ),
        fp_pointer_source,
        fp_ranking_source,
        fc_pointer_source,
        fc_ranking_source,
        ppr_pointer_source,
        ppr_ranking_source,
        two_pointer_source,
        two_ranking_source,
    ]

    player_lookup = {
        str(player.get("ID")): player
        for player in players
        if player.get("ID") is not None
    }
    sections_by_player: dict[str, list[str]] = defaultdict(list)
    for section in ("Roster", "Reserve", "Taxi"):
        for player_id in managed_team.get(section) or []:
            section_name = section.casefold()
            if section_name not in sections_by_player[str(player_id)]:
                sections_by_player[str(player_id)].append(section_name)
    starters = {str(player_id) for player_id in managed_team.get("Starter") or []}

    fp_index = index_rows(fp_rows)
    fc_index = index_rows(fc_rows, sleeper_field="sleeper_id")
    ppr_index = index_rows(ppr_rows)
    two_index = index_rows(two_rows)

    output_players: list[dict[str, Any]] = []
    quality_issues: list[dict[str, Any]] = []
    for player_id in sorted(sections_by_player, key=lambda value: (len(value), value)):
        player = player_lookup.get(player_id)
        if player is None:
            quality_issues.append(
                {"severity": "error", "kind": "missing_player", "player_id": player_id}
            )
            continue

        market, market_issues = extract_market(player, fp_index, fc_index)
        adp, adp_issues = extract_adp(player, ppr_index, two_index)
        for issue in market_issues + adp_issues:
            quality_issues.append(
                {
                    "severity": "warning",
                    "kind": "source_join",
                    "player_id": player_id,
                    **issue,
                }
            )

        injury = derive_injury_signal(player)
        research_reasons = ["role_opportunity_requires_qualitative_context"]
        if injury["external_verification_priority"] == "high":
            research_reasons.insert(
                0,
                "current_structured_injury_signal_requires_verification",
            )

        output_players.append(
            {
                "player_id": player_id,
                "name": optional_text(player.get("Name")),
                "position": optional_text(player.get("Position")),
                "nfl_team": optional_text(player.get("TeamAbbr")),
                "roster_sections": sorted(sections_by_player[player_id]),
                "is_starter": player_id in starters,
                "app_data": {
                    "status": optional_text(player.get("Status")),
                    "age": optional_number(player.get("Age")),
                    "years_experience": optional_number(player.get("Year")),
                    "salary": optional_number(player.get("Salary")),
                    "salary_projected": optional_number(
                        player.get("SalaryProjected")
                    ),
                    "is_free_agent": optional_bool(player.get("IsFreeAgent")),
                },
                "injury": injury,
                "market": market,
                "redraft_adp": adp,
                "external_research": {
                    "injury_priority": injury["external_verification_priority"],
                    "role_opportunity_priority": "routine",
                    "reasons": research_reasons,
                },
            }
        )

    source_records = [
        {
            "id": item.id,
            "path": item.relative_path,
            "content_sha256": item.content_sha256,
            "source_timestamp": item.source_timestamp,
        }
        for item in source_files
    ]
    generated_at = max_timestamp(item.source_timestamp for item in source_files)
    input_fingerprint = sha256_text(canonical_json(source_records))
    data = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "managed-roster-signals",
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "managed_team": {
            "team_id": managed_team.get(managed_config["identity_field"]),
            "name": optional_text(managed_team.get("Team")),
            "abbreviation": optional_text(managed_team.get("TeamAbbr")),
            "player_count": len(output_players),
        },
        "sources": source_records,
        "players": output_players,
        "quality": {
            "status": (
                "error"
                if any(issue["severity"] == "error" for issue in quality_issues)
                else ("warning" if quality_issues else "ok")
            ),
            "issue_count": len(quality_issues),
            "issues": quality_issues,
            "coverage": {
                "managed_roster_ids": len(sections_by_player),
                "resolved_players": len(output_players),
                "players_with_current_injury_signal": sum(
                    1
                    for item in output_players
                    if item["injury"]["coverage_status"]
                    != "no_current_injury_signal"
                ),
                "fantasypros_listed": sum(
                    1
                    for item in output_players
                    if item["market"]["fantasypros"]["listed"]
                ),
                "fantasycalc_listed": sum(
                    1
                    for item in output_players
                    if item["market"]["fantasycalc"]["listed"]
                ),
                "primary_adp_listed": sum(
                    1
                    for item in output_players
                    if item["redraft_adp"]["primary_listed"]
                ),
            },
        },
    }
    validate_output(data)

    quality_report = {
        "schema_version": 1,
        "report_id": "fantasy-operations-data-quality",
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "status": data["quality"]["status"],
        "coverage": data["quality"]["coverage"],
        "issues": quality_issues,
        "source_freshness": [
            {
                "id": source["id"],
                "path": source["path"],
                "source_timestamp": source["source_timestamp"],
            }
            for source in source_records
        ],
        "interpretation_limits": [
            "Structured injury data is a secondary signal and not a substitute for current external verification.",
            "Role and opportunity are intentionally not inferred by this deterministic materialization.",
            "Missing ranking or ADP rows are represented as data-quality issues, not as negative player evaluations.",
        ],
    }
    return data, quality_report


def write_json_if_changed(path: Path, data: dict[str, Any]) -> bool:
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/input-materialization.json"),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated files are not current.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    data, quality = build(root, config_path)
    output_path = root / config["outputs"]["managed_roster_signals"]
    quality_path = root / config["outputs"]["data_quality"]

    if args.check:
        expected = {
            output_path: json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            quality_path: json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        }
        stale = [
            relative_to_root(path, root)
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print("Generated Fantasy Operations inputs are stale:")
            for path in stale:
                print(f"- {path}")
            return 1
        print("OK: Fantasy Operations inputs are current.")
        return 0

    changed = [
        (
            relative_to_root(output_path, root)
            if write_json_if_changed(output_path, data)
            else None
        ),
        (
            relative_to_root(quality_path, root)
            if write_json_if_changed(quality_path, quality)
            else None
        ),
    ]
    written = [path for path in changed if path]
    if written:
        print("Updated:")
        for path in written:
            print(f"- {path}")
    else:
        print("No Fantasy Operations input changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
