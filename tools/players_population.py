#!/usr/bin/env python3
"""Players.json population and platform fields from canonical source data (#347 H1b).

Replaces the Tank01 ``getNFLPlayerList`` population of RequestPlayers.ps1. The population is the
Fantasy Management rule (ADR-043): a Sleeper player belongs in Players.json when it has an app
fantasy position (QB, RB, WR, TE, K), a valid birth date and at least one reason:

  nfl_roster_current_season  canonical NFL season roster or any weekly roster of the season
                             (identity resolved to exactly one CanonicalPlayerID)
  nfl_draft_current_season   canonical NFL draft of the season (same identity rule)
  league_owned               on a current fantasy roster (taxi and IR included); needs no unique
                             identity, the scoring export then holds the last published values

While the season roster is not yet published (not-yet-available) the previous season roster is
used and the export says so (``RosterBasis.UsedPreviousSeasonRoster``). Without both rosters the
export fails closed.

Platform fields (H5) come from the canonical Sleeper snapshot (``sleeper.players``) through the
canonical NFL team registry: ``TeamAbbr`` and ``TeamID`` are the canonical abbreviation (null for a
player without a team), ``IsFreeAgent`` is NFL free agency (no Sleeper team), ``Status`` is the
Sleeper status. An unknown team abbreviation or a missing snapshot field set fails closed.

The export is deterministic (no timestamps) and not persisted; RequestPlayers.ps1 rebuilds it on
every run.

Usage:
  players_population.py export --season 2026 --out population.json
  players_population.py shadow --season 2026 --published public/data/Players.json --report-dir DIR
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_fantasy_scoring import read_json  # noqa: E402
from nfl_source_data_lib.teams import NflTeamRegistry, NflTeamRegistryError  # noqa: E402
from players_league_scoring import (  # noqa: E402
    LEAGUE_ID,
    SleeperIdentityResolver,
    league_owned_sleeper_ids,
)

SCHEMA_VERSION = 1
APP_FANTASY_POSITIONS = ("TE", "QB", "RB", "WR", "K")
SNAPSHOT_PATH = "source-data/nfl/platform/sleeper/players.json"
PROFILES_PATH = "source-data/nfl/player-profiles/nflverse.json"
FANTASYPROS_URL = "https://www.fantasypros.com/nfl/players/{slug}.php"
ESPN_PLAYER_URL = "https://www.espn.com/nfl/player/_/id/{espn_id}/{slug}"
# The NFL image CDN serves the original (3400x2450 px, 1 to 5 MB); the app shows 34 to 60 px, so request 160 px (about 6 KB).
HEADSHOT_WIDTH = 160
HEADSHOT_LARGE_WIDTH = 480  # detail and desktop portraits (about 20 to 30 KB)
ESPN_HEADSHOT_URL = "https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
REQUIRED_SNAPSHOT_FIELDS = (
    "Status", "Team", "Position", "FantasyPositions", "BirthDate", "FullName", "FirstName", "LastName",
    "YearsExp", "College", "HighSchool", "Number", "ESPNID", "InjuryStatus", "InjuryStartDate",
    "InjuryBodyPart", "InjuryNotes", "PracticeParticipation", "PracticeDescription",
)
REASON_ROSTER = "nfl_roster_current_season"
REASON_DRAFT = "nfl_draft_current_season"
REASON_LEAGUE = "league_owned"


class PopulationError(RuntimeError):
    """Raised when the population cannot be built safely."""


def app_fantasy_position(position: Any, fantasy_positions: Any) -> str | None:
    """Port of PlayerUtils.psm1::Get-AppFantasyPosition."""
    primary = str(position or "").strip().upper()
    if primary in APP_FANTASY_POSITIONS:
        return primary
    for candidate in fantasy_positions or []:
        value = str(candidate).strip().upper()
        if value in APP_FANTASY_POSITIONS:
            return value
    return None


def valid_birth_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return len(value) == 10


def _canonical_ids(document: Any, source: str) -> set[str]:
    records = document.get("Records") if isinstance(document, dict) else None
    if not isinstance(records, list):
        raise PopulationError(f"{source} must contain Records[]")
    return {str(r["CanonicalPlayerID"]) for r in records if isinstance(r, dict) and r.get("CanonicalPlayerID")}


def roster_basis(repo_root: Path, season: int) -> tuple[set[str], dict[str, Any]]:
    """Canonical roster membership of the season; previous season while the current one is unpublished."""
    rosters = repo_root / "source-data/nfl/rosters"
    current = rosters / f"{season}.json"
    used_season = season
    previous = False
    if not current.is_file():
        used_season = season - 1
        previous = True
        if not (rosters / f"{used_season}.json").is_file():
            raise PopulationError(
                f"No canonical NFL roster for {season} or {used_season}; refusing to publish an empty population"
            )
    ids = _canonical_ids(read_json(rosters / f"{used_season}.json"), f"rosters/{used_season}.json")
    weekly_dir = repo_root / "source-data/nfl/weekly-rosters" / str(used_season)
    weekly_files = sorted(weekly_dir.glob("*.json")) if weekly_dir.is_dir() else []
    for path in weekly_files:
        ids |= _canonical_ids(read_json(path), f"weekly-rosters/{used_season}/{path.name}")
    return ids, {
        "Season": season,
        "RosterSeason": used_season,
        "UsedPreviousSeasonRoster": previous,
        "WeeklyRosterPartitions": len(weekly_files),
    }


def draft_basis(repo_root: Path, season: int) -> set[str]:
    path = repo_root / "source-data/nfl/draft" / f"{season}.json"
    if not path.is_file():
        return set()
    picks = read_json(path).get("Picks")
    if not isinstance(picks, list):
        raise PopulationError(f"{path} must contain Picks[]")
    return {str(p["CanonicalPlayerID"]) for p in picks if isinstance(p, dict) and p.get("CanonicalPlayerID")}


def load_snapshot(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / SNAPSHOT_PATH
    if not path.is_file():
        raise PopulationError(f"Canonical Sleeper snapshot is required: {SNAPSHOT_PATH}")
    payload = read_json(path)
    if payload.get("SourceDataset") != "sleeper.players" or not isinstance(payload.get("Records"), list):
        raise PopulationError(f"Unexpected canonical Sleeper snapshot layout: {SNAPSHOT_PATH}")
    records = payload["Records"]
    if not records:
        raise PopulationError("Canonical Sleeper snapshot is empty")
    missing = [f for f in REQUIRED_SNAPSHOT_FIELDS if f not in records[0]]
    if missing:
        raise PopulationError(
            f"Canonical Sleeper snapshot lacks fields {missing}; the NFL source sync must materialize it first (#347 F1)"
        )
    return records


def provider_ids_by_canonical(repo_root: Path) -> dict[str, dict[str, str]]:
    """Provider IDs RequestPlayers still needs per CanonicalPlayerID.

    ESPN is the athlete ID for the ESPN profile link and the headshot fallback (H2).
    """
    payload = read_json(repo_root / "source-data/nfl/identities/players.json")
    out: dict[str, dict[str, str]] = {}
    for record in payload.get("Players") or []:
        ids = record.get("IDs") or {}
        wanted = {name: str(ids[name]) for name in ("ESPN",) if ids.get(name)}
        if wanted:
            out[str(record["CanonicalPlayerID"])] = wanted
    return out


def load_profiles(repo_root: Path) -> dict[str, dict[str, Any]]:
    """nflverse player profiles (F2) by CanonicalPlayerID."""
    path = repo_root / PROFILES_PATH
    if not path.is_file():
        raise PopulationError(f"Canonical nflverse player profiles are required: {PROFILES_PATH}")
    payload = read_json(path)
    if payload.get("SourceDataset") != "nflverse.players" or not isinstance(payload.get("Records"), list):
        raise PopulationError(f"Unexpected canonical player profile layout: {PROFILES_PATH}")
    return {str(r["CanonicalPlayerID"]): r for r in payload["Records"] if r.get("CanonicalPlayerID")}


def profile_slug(name: str) -> str:
    """Lower-case ASCII slug used by the FantasyPros and ESPN profile URLs (apostrophes and dots dropped)."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    ascii_name = re.sub(r"[.'\u2019,]", "", ascii_name)
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")


def short_name(display_name: str) -> str | None:
    """First initial plus the rest of the display name ("Marvin Harrison Jr." -> "M. Harrison Jr.")."""
    parts = display_name.strip().split(None, 1)
    if len(parts) < 2 or not parts[0]:
        return None
    return f"{parts[0][0]}. {parts[1]}"


# Public (`upload`) and private (`private`) delivery types both serve the 1 to 5 MB original without a width.
NFL_IMAGE_URL = re.compile(r"^(?P<head>https://static\.www\.nfl\.com/image/(?:upload|private)/)(?P<transform>[^/]+)/(?P<rest>.+)$")


def sized_headshot(url: str | None, width: int = HEADSHOT_WIDTH) -> str | None:
    """Add a width transformation to an NFL image CDN link; other links and already sized links stay unchanged."""
    match = NFL_IMAGE_URL.match(url or "")
    if not match:
        return url
    transform = match["transform"]
    if any(part.startswith("w_") for part in transform.split(",")):
        return url
    return f"{match['head']}{transform},w_{width}/{match['rest']}"


def derive_profile(display_name: str | None, headshot: str | None, espn_id: str | None) -> dict[str, Any]:
    """Name short, picture and profile links from canonical facts; nothing is taken from the published file.

    Picture is a small (list) and PictureLarge a large (detail) rendition of the nflverse headshot, falling back to the ESPN headshot of the canonical ESPN athlete ID.
    Links are null when the name slug or the ESPN athlete ID is missing (never a link with an empty part).
    """
    name = (display_name or "").strip()
    slug = profile_slug(name) if name else ""
    espn_headshot = ESPN_HEADSHOT_URL.format(espn_id=espn_id) if espn_id else None
    picture = sized_headshot(headshot) or espn_headshot
    picture_large = sized_headshot(headshot, HEADSHOT_LARGE_WIDTH) or espn_headshot
    return {
        "NameShort": short_name(name) if name else None,
        "Picture": picture,
        "PictureLarge": picture_large,
        "FantasyPros": FANTASYPROS_URL.format(slug=slug) if slug else None,
        "ESPN": ESPN_PLAYER_URL.format(espn_id=espn_id, slug=slug) if slug and espn_id else None,
    }


def _team(registry: NflTeamRegistry, value: Any, season: int, label: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return registry.resolve(str(value), season)
    except NflTeamRegistryError as error:
        raise PopulationError(f"{label}: {error}") from error


def build_population(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    records = load_snapshot(repo_root)
    registry = NflTeamRegistry.load(repo_root)
    resolver = SleeperIdentityResolver.from_repo(repo_root)
    roster_ids, basis = roster_basis(repo_root, season)
    draft_ids = draft_basis(repo_root, season)
    owned = league_owned_sleeper_ids(repo_root, league_id, season)
    provider_ids = provider_ids_by_canonical(repo_root)
    profiles = load_profiles(repo_root)

    players: list[dict[str, Any]] = []
    skipped: Counter = Counter()
    seen: set[str] = set()
    for row in records:
        sleeper_id = str(row["SleeperPlayerID"])
        if sleeper_id in seen:
            raise PopulationError(f"Duplicate Sleeper player ID in the canonical snapshot: {sleeper_id}")
        seen.add(sleeper_id)
        position = app_fantasy_position(row.get("Position"), row.get("FantasyPositions"))
        if position is None:
            skipped["no_app_position"] += 1
            continue
        if not valid_birth_date(row.get("BirthDate")):
            skipped["no_valid_birth_date"] += 1
            continue
        cid, status = resolver.resolve(sleeper_id, season)
        reasons: list[str] = []
        if cid is not None:
            if cid in roster_ids:
                reasons.append(REASON_ROSTER)
            if cid in draft_ids:
                reasons.append(REASON_DRAFT)
        if sleeper_id in owned:
            reasons.append(REASON_LEAGUE)
        if not reasons:
            skipped["no_reason" if status == SleeperIdentityResolver.RESOLVED else f"no_reason_{status}"] += 1
            continue
        team = _team(registry, row.get("Team"), season, f"Sleeper player {sleeper_id}")
        profile = profiles.get(cid) if cid else None
        espn_id = provider_ids.get(cid, {}).get("ESPN") if cid else None
        espn_id = espn_id or (str(row["ESPNID"]) if row.get("ESPNID") else None)
        derived = derive_profile(
            (profile or {}).get("DisplayName") or row.get("FullName"), (profile or {}).get("Headshot"), espn_id
        )
        players.append({
            "SleeperID": sleeper_id,
            "CanonicalPlayerID": cid,
            "IdentityStatus": status,
            "Reasons": reasons,
            "Position": position,
            "TeamAbbr": team,
            "TeamID": team,
            "IsFreeAgent": team is None,
            "Status": row.get("Status"),
            "FullName": row.get("FullName"),
            "FirstName": row.get("FirstName"),
            "LastName": row.get("LastName"),
            "YearsExp": row.get("YearsExp"),
            "College": row.get("College"),
            "HighSchool": row.get("HighSchool"),
            "Number": row.get("Number"),
            "NameShort": derived["NameShort"],
            "Picture": derived["Picture"],
            "PictureLarge": derived["PictureLarge"],
            "FantasyPros": derived["FantasyPros"],
            "ESPN": derived["ESPN"],
            "BirthDate": row["BirthDate"],
            "Injury": {
                "Status": row.get("InjuryStatus"),
                "StartDate": row.get("InjuryStartDate"),
                "BodyPart": row.get("InjuryBodyPart"),
                "Notes": row.get("InjuryNotes"),
                "PracticeParticipation": row.get("PracticeParticipation"),
                "PracticeDescription": row.get("PracticeDescription"),
            },
        })
    if not players:
        raise PopulationError("Population is empty; refusing to publish")
    players.sort(key=lambda p: p["SleeperID"])
    reason_counts = Counter(reason for p in players for reason in p["Reasons"])
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "RosterBasis": basis,
        "Counts": {
            "Players": len(players),
            "Reasons": dict(sorted(reason_counts.items())),
            "Skipped": dict(sorted(skipped.items())),
            "IdentityHold": sum(1 for p in players if p["CanonicalPlayerID"] is None),
        },
        "Players": players,
    }


def build_shadow(repo_root: Path, league_id: str, season: int, published_path: Path, report_dir: Path) -> dict[str, Any]:
    """Compare the export with the published Players.json; list every population and field difference."""
    export = build_population(repo_root, league_id, season)
    published = {str(p["ID"]): p for p in json.loads(published_path.read_text(encoding="utf-8-sig"))}
    new = {p["SleeperID"]: p for p in export["Players"]}
    registry = NflTeamRegistry.load(repo_root)
    removed = sorted(set(published) - set(new))
    added = sorted(set(new) - set(published))
    common = sorted(set(new) & set(published))

    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "population-delta.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Change", "SleeperID", "Name", "Position", "PublishedTeam", "SnapshotTeam", "Reasons", "Salary"])
        for sid in removed:
            p = published[sid]
            writer.writerow(["removed", sid, p.get("Name"), p.get("Position"), p.get("TeamAbbr"), "", "", p.get("Salary")])
        for sid in added:
            p = new[sid]
            writer.writerow(["added", sid, p["FullName"], p["Position"], "", p["TeamAbbr"] or "", "|".join(p["Reasons"]), ""])

    def canonical_team(value: Any) -> str | None:
        return registry.resolve(value, season) if value else None

    diffs: Counter = Counter()
    rows: list[list[Any]] = []
    for sid in common:
        old, cur = published[sid], new[sid]
        old_team = canonical_team(old.get("TeamAbbr"))
        checks = {
            "TeamAbbr": (old_team, cur["TeamAbbr"]),
            "IsFreeAgent": (old.get("IsFreeAgent"), cur["IsFreeAgent"]),
            "Number": (None if old.get("Number") in (None, "") else str(old.get("Number")),
                       None if cur["Number"] is None else str(cur["Number"])),
            "Injured": (bool(old.get("Injured")), bool(cur["Injury"]["Status"])),
            "Status": (old.get("Status"), cur["Status"]),
            "Name": (old.get("Name"), cur["FullName"]),
            "Position": (old.get("Position"), cur["Position"]),
            "NameShort": (old.get("NameShort") or short_name(str(old.get("Name") or "")), cur["NameShort"]),
            "Picture": (old.get("Picture"), cur["Picture"]),
            "FantasyPros": (old.get("FantasyPros"), cur["FantasyPros"]),
            "ESPN": (old.get("ESPN"), cur["ESPN"]),
        }
        for field, (a, b) in checks.items():
            if a != b:
                diffs[field] += 1
                rows.append([sid, old.get("Name"), field, a, b])
    with (report_dir / "field-differences.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["SleeperID", "Name", "Field", "Published", "Export"])
        writer.writerows(rows)

    summary = {
        "Published": len(published),
        "Export": len(new),
        "Removed": len(removed),
        "Added": len(added),
        "Common": len(common),
        "FieldDifferences": dict(sorted(diffs.items())),
        "RosterBasis": export["RosterBasis"],
        "Counts": export["Counts"],
    }
    (report_dir / "shadow-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default=LEAGUE_ID)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write the population export consumed by RequestPlayers.ps1")
    export.add_argument("--season", type=int, required=True)
    export.add_argument("--out", type=Path, required=True)
    shadow = sub.add_parser("shadow", help="compare the export with the published Players.json")
    shadow.add_argument("--season", type=int, required=True)
    shadow.add_argument("--published", type=Path, required=True)
    shadow.add_argument("--report-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "export":
            payload = build_population(args.repo_root, args.league, args.season)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            print(f"Exported {payload['Counts']['Players']} players ({payload['Counts']['IdentityHold']} identity hold).")
            return 0
        summary = build_shadow(args.repo_root, args.league, args.season, args.published, args.report_dir)
    except (PopulationError, ValueError, KeyError, OSError) as error:
        print(f"Players population unavailable: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
