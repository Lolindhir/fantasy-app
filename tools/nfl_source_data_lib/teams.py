"""Canonical NFL team registry (#347 F3a): materialization from nflverse and a fail-closed resolver."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .common import CANONICAL_SCHEMA_VERSION, Dataset, clean, iter_csv, load_json

TEAMS_DATASET_ID = "nflverse.teams"
TEAMS_RELATIVE_PATH = "source-data/nfl/teams.json"
EXPECTED_TEAM_COUNT = 32

CONFERENCE_NAMES = {
    "AFC": "American Football Conference",
    "NFC": "National Football Conference",
}

# Provider spellings of a current team that nflverse does not carry as its own row.
# WSH is the ESPN/Tank01 spelling of WAS. LAR is also a nflverse row, but is registered here
# as a spelling of LA so the alias set does not depend on the CSV layout.
PROVIDER_SPELLING_ALIASES: dict[str, str] = {
    "LAR": "LA",
    "WSH": "WAS",
}

# Historical abbreviations of a relocated franchise, with the last season they were in use.
# nflverse lists the rows but not the season bounds, so the bounds are static NFL history.
HISTORICAL_ALIAS_LAST_SEASON: dict[str, tuple[str, int]] = {
    "OAK": ("LV", 2019),
    "SD": ("LAC", 2016),
    "STL": ("LA", 2015),
}

# Numeric team keys of the app before the canonical-abbreviation cutover. Frozen once from the
# published public/data/Teams.json (static history, not a provider call). They let old archives
# (Schedule_2022-2025, FantasyGameContext_2025, WeeklyRecaps_2025, ...) keep resolving.
LEGACY_APP_TEAM_IDS: dict[str, str] = {
    "ARI": "1", "ATL": "2", "BAL": "3", "BUF": "4", "CAR": "5", "CHI": "6", "CIN": "7",
    "CLE": "8", "DAL": "9", "DEN": "10", "DET": "11", "GB": "12", "HOU": "13", "IND": "14",
    "JAX": "15", "KC": "16", "LV": "17", "LAC": "18", "LA": "19", "MIA": "20", "MIN": "21",
    "NE": "22", "NO": "23", "NYG": "24", "NYJ": "25", "PIT": "26", "PHI": "27", "SF": "28",
    "SEA": "29", "TB": "30", "TEN": "31", "WAS": "32",
}

_NON_CURRENT_ROWS = set(PROVIDER_SPELLING_ALIASES) | set(HISTORICAL_ALIAS_LAST_SEASON)


def build_teams_payload(dataset: Dataset) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the canonical team registry from the persisted nflverse team CSV."""
    rows = list(iter_csv(dataset.raw_path))
    by_abbr: dict[str, dict[str, str]] = {}
    for row in rows:
        abbr = clean(row.get("team_abbr"))
        if not abbr:
            raise ValueError("nflverse team row without team_abbr")
        if abbr in by_abbr:
            raise ValueError(f"Duplicate nflverse team_abbr: {abbr}")
        by_abbr[abbr] = row

    current = {abbr: row for abbr, row in by_abbr.items() if abbr not in _NON_CURRENT_ROWS}
    if len(current) != EXPECTED_TEAM_COUNT:
        raise ValueError(
            f"nflverse team CSV must list {EXPECTED_TEAM_COUNT} current teams, found {len(current)}: {sorted(current)}"
        )
    if set(current) != set(LEGACY_APP_TEAM_IDS):
        raise ValueError(
            "Current nflverse teams disagree with the frozen legacy app team keys: "
            f"{sorted(set(current) ^ set(LEGACY_APP_TEAM_IDS))}"
        )

    franchise_ids: dict[str, str] = {}
    for abbr, row in current.items():
        franchise_id = clean(row.get("team_id"))
        if not franchise_id:
            raise ValueError(f"nflverse team {abbr} has no team_id")
        if franchise_id in franchise_ids:
            raise ValueError(f"Franchise ID {franchise_id} is shared by {franchise_ids[franchise_id]} and {abbr}")
        franchise_ids[franchise_id] = abbr

    aliases: dict[str, list[dict[str, Any]]] = {abbr: [] for abbr in current}
    for alias, target in sorted(PROVIDER_SPELLING_ALIASES.items()):
        if target not in current:
            raise ValueError(f"Provider alias {alias} points to unknown team {target}")
        if alias in by_abbr and clean(by_abbr[alias].get("team_id")) != clean(current[target].get("team_id")):
            raise ValueError(f"nflverse row {alias} does not share the franchise ID of {target}")
        aliases[target].append({"Alias": alias, "Kind": "provider-spelling"})
    for alias, (target, last_season) in sorted(HISTORICAL_ALIAS_LAST_SEASON.items()):
        if target not in current:
            raise ValueError(f"Historical alias {alias} points to unknown team {target}")
        if alias in by_abbr and clean(by_abbr[alias].get("team_id")) != clean(current[target].get("team_id")):
            raise ValueError(f"nflverse row {alias} does not share the franchise ID of {target}")
        aliases[target].append({"Alias": alias, "Kind": "historical", "LastSeason": last_season})

    teams: list[dict[str, Any]] = []
    for abbr in sorted(current):
        row = current[abbr]
        full_name = clean(row.get("team_name"))
        nickname = clean(row.get("team_nick"))
        conference = clean(row.get("team_conf"))
        division_name = clean(row.get("team_division"))
        logo = clean(row.get("team_logo_espn"))
        if not full_name or not nickname or not full_name.endswith(nickname):
            raise ValueError(f"nflverse team {abbr} has an inconsistent name/nickname")
        if conference not in CONFERENCE_NAMES:
            raise ValueError(f"nflverse team {abbr} has unsupported conference {conference!r}")
        if not division_name or not division_name.startswith(f"{conference} "):
            raise ValueError(f"nflverse team {abbr} has an inconsistent division {division_name!r}")
        if not logo:
            raise ValueError(f"nflverse team {abbr} has no ESPN logo")
        teams.append({
            "TeamAbbr": abbr,
            "FranchiseID": clean(row.get("team_id")),
            "FullName": full_name,
            "Name": nickname,
            "City": full_name[: -len(nickname)].strip(),
            "Conference": CONFERENCE_NAMES[conference],
            "ConferenceAbv": conference,
            "Division": division_name[len(conference) + 1:],
            "DivisionName": division_name,
            "Logo": logo,
            "Aliases": aliases[abbr],
            "LegacyAppTeamID": LEGACY_APP_TEAM_IDS[abbr],
        })

    payload = {
        "SchemaVersion": CANONICAL_SCHEMA_VERSION,
        "SourceDataset": dataset.id,
        "Teams": teams,
    }
    audit = {
        "teamCount": len(teams),
        "aliasCount": sum(len(team["Aliases"]) for team in teams),
        "sourceRowCount": len(rows),
    }
    return payload, audit


class NflTeamRegistryError(ValueError):
    """Raised when a team key cannot be resolved against the canonical registry."""


class NflTeamRegistry:
    """Fail-closed resolver for canonical team abbreviations, provider spellings and legacy keys."""

    def __init__(self, payload: dict[str, Any]) -> None:
        teams = payload.get("Teams")
        if not isinstance(teams, list) or len(teams) != EXPECTED_TEAM_COUNT:
            raise NflTeamRegistryError(f"Team registry must list {EXPECTED_TEAM_COUNT} teams")
        self.teams: dict[str, dict[str, Any]] = {}
        self._alias: dict[str, tuple[str, int | None]] = {}
        self._legacy: dict[str, str] = {}
        for team in teams:
            abbr = team["TeamAbbr"]
            if abbr in self.teams:
                raise NflTeamRegistryError(f"Duplicate team {abbr}")
            self.teams[abbr] = team
            legacy = clean(team.get("LegacyAppTeamID"))
            if legacy:
                if legacy in self._legacy:
                    raise NflTeamRegistryError(f"Duplicate legacy team ID {legacy}")
                self._legacy[legacy] = abbr
            for alias in team.get("Aliases", []):
                key = alias["Alias"].upper()
                if key in self._alias or key in self.teams:
                    raise NflTeamRegistryError(f"Ambiguous team alias {key}")
                self._alias[key] = (abbr, alias.get("LastSeason"))

    @classmethod
    def load(cls, repo_root: Path) -> "NflTeamRegistry":
        payload = load_json(repo_root / TEAMS_RELATIVE_PATH)
        if not isinstance(payload, dict):
            raise NflTeamRegistryError(f"Canonical team registry is missing: {TEAMS_RELATIVE_PATH}")
        return cls(payload)

    def resolve(self, value: str | None, season: int | None = None) -> str:
        """Return the canonical abbreviation for an abbreviation, provider spelling or legacy key.

        Historical aliases (OAK, SD, STL) only resolve for seasons up to their last season; without a
        season they are rejected rather than guessed. Unknown values raise.
        """
        text = clean(value)
        if text is None:
            raise NflTeamRegistryError("Empty NFL team key")
        key = text.upper()
        if key in self.teams:
            return key
        alias = self._alias.get(key)
        if alias is not None:
            abbr, last_season = alias
            if last_season is None:
                return abbr
            if season is None:
                raise NflTeamRegistryError(f"Historical team alias {key} requires a season")
            if season > last_season:
                raise NflTeamRegistryError(f"Team alias {key} is not valid after season {last_season}")
            return abbr
        if text in self._legacy:
            return self._legacy[text]
        raise NflTeamRegistryError(f"Unknown NFL team key: {text}")

    def abbreviations(self) -> Iterable[str]:
        return sorted(self.teams)
