"""Season-aware, consumer-neutral league-history player display references (Issue #1100).

Canonical identity is resolved only by the existing season-aware Sleeper bridge. A
name from a completed provider draft is evidence for display, never a join key.
Profile and Sleeper snapshot facts enrich an already uniquely identified player;
they do not establish historical membership or a historical NFL team.
"""
from __future__ import annotations

from typing import Any, Callable

from data_roots import DATA_SOURCE_ROOT
from historical_fantasy_scoring import read_json
from players_league_scoring import SleeperIdentityResolver
from players_population import app_fantasy_position, sized_headshot


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _index(records: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in records:
        identifier = _clean(row.get(key))
        if identifier is None:
            raise ValueError(f"{label} record without {key}")
        if identifier in indexed:
            raise ValueError(f"Duplicate {label} identity {identifier}")
        indexed[identifier] = row
    return indexed


def provider_draft_names(drafts: list[dict[str, Any]]) -> dict[str, str]:
    """Unique provider-name hint per Sleeper ID within a single draft season.

    Conflicting pick names are not silently selected; each event retains its
    own original PlayerName independently of the aggregate reference.
    """
    names: dict[str, set[str]] = {}
    spellings: dict[str, str] = {}
    for draft in drafts:
        for pick in draft.get("Picks") or []:
            identifier = _clean(pick.get("PlayerID"))
            name = _clean(pick.get("PlayerName"))
            if identifier is None or name is None:
                continue
            names.setdefault(identifier, set()).add(name.casefold())
            spellings.setdefault(identifier, name)
    return {identifier: spellings[identifier] for identifier, variants in names.items() if len(variants) == 1}


class LeaguePlayerReferenceResolver:
    """One shared mapping and display-evidence resolver for both history products."""

    def __init__(
        self,
        identity: SleeperIdentityResolver,
        profiles: list[dict[str, Any]],
        sleeper_players: list[dict[str, Any]],
    ) -> None:
        self.identity = identity
        self.profiles = _index(profiles, "CanonicalPlayerID", "NFL profile")
        self.sleeper_players = _index(sleeper_players, "SleeperPlayerID", "Sleeper snapshot")

    @classmethod
    def from_repo(cls, root: Any) -> "LeaguePlayerReferenceResolver":
        identity = SleeperIdentityResolver.from_repo(root)
        profiles = read_json(root / DATA_SOURCE_ROOT / "nfl/player-profiles/nflverse.json")
        sleeper = read_json(root / DATA_SOURCE_ROOT / "nfl/platform/sleeper/players.json")
        if profiles.get("SourceDataset") != "nflverse.players" or not isinstance(profiles.get("Records"), list):
            raise ValueError("Unexpected canonical NFL player profiles layout")
        if sleeper.get("SourceDataset") != "sleeper.players" or not isinstance(sleeper.get("Records"), list):
            raise ValueError("Unexpected canonical Sleeper players layout")
        return cls(identity, profiles["Records"], sleeper["Records"])

    def resolve(self, player_id: str, season: int, event_name: str | None = None) -> dict[str, Any]:
        sleeper_id = str(player_id)
        canonical_id, status = self.identity.resolve(sleeper_id, int(season))
        profile = self.profiles.get(canonical_id) if canonical_id is not None else None
        candidate = self.sleeper_players.get(sleeper_id)
        # The current snapshot may refer to a later owner of a reused provider ID.
        # Never retroactively decorate a historical identity with that person's facts.
        snapshot = candidate if canonical_id is not None and candidate is not None and (
            _clean(candidate.get("CanonicalPlayerID")) == canonical_id
        ) else None

        name = _clean(profile.get("DisplayName")) if profile else None
        name_source = "nflverse.players" if name else None
        if name is None and snapshot:
            name = _clean(snapshot.get("FullName"))
            name_source = "sleeper.players" if name else None
        if name is None:
            name = _clean(event_name)
            name_source = "league.draft.pick.PlayerName" if name else None

        # Same rule as Players.json (Get-AppFantasyPosition): a known fantasy position of the
        # identified player wins over a non-fantasy primary position such as CB for a WR/CB player.
        position = app_fantasy_position(snapshot.get("Position"), snapshot.get("FantasyPositions")) if snapshot else None
        position_source = "sleeper.players.fantasy-position" if position else None
        if position is None and profile:
            position = _clean(profile.get("Position"))
            position_source = "nflverse.players" if position else None
        if position is None and snapshot:
            position = _clean(snapshot.get("Position"))
            position_source = "sleeper.players" if position else None
        # An unsized NFL image link serves the 1 to 5 MB original; display needs a small rendition.
        picture = sized_headshot(_clean(profile.get("Headshot"))) if profile else None

        return {
            "CanonicalPlayerID": canonical_id,
            "Name": name,
            "Position": position,
            "Picture": picture,
            "ResolutionStatus": status,
            "Provenance": {
                "Identity": "nfl.identities.provider-mappings" if canonical_id is not None else None,
                "Name": name_source,
                "Position": position_source,
                "Picture": "nflverse.players" if picture else None,
            },
        }


def player_refs(
    player_ids: list[str],
    season: int,
    resolver: Callable[[str, int, str | None], dict[str, Any]],
    event_names: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    hints = event_names or {}
    return {player_id: resolver(player_id, season, hints.get(player_id)) for player_id in sorted(set(player_ids))}
