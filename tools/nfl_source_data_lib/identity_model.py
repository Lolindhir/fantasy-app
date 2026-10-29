from __future__ import annotations

from dataclasses import dataclass

from .common import IDENTITY_ID_KEYS, clean

SLEEPER_PLAYERS_SOURCE = "sleeper.players"
SLEEPER_ATTRIBUTE_BRIDGE_PROVENANCE = "auto.sleeper-roster-attribute-bridge"
ANCHOR_ID_KEYS = ("GSIS", "ESPN", "PFR", "PFF")
LINK_ID_KEYS = {"GSIS", "Sleeper", "ESPN", "PFR", "PFF", "Tank01"}
ATTACH_ID_KEYS = {"Sleeper"}
WEAK_ID_KEYS = set(IDENTITY_ID_KEYS) - LINK_ID_KEYS
ALIAS_MIN_CORROBORATORS = {"ESPN": 1, "PFR": 2}
PRIMARY_SOURCE_PREFERENCE = (
    "nflverse.ff-player-ids",
    "nflverse.players",
    SLEEPER_PLAYERS_SOURCE,
    "canonical-existing",
)


@dataclass
class IdentityCandidate:
    ids: dict[str, str]
    name: str | None
    first_name: str | None
    last_name: str | None
    birth_date: str | None
    position: str | None
    latest_team: str | None
    source: str
    priority: int
    existing_internal_id: str | None = None
    # GSIS of the single current roster record a Sleeper candidate was bridged to
    # by the bounded attribute rule (sleeperCurrentRosterAttributeBridge).
    bridge_gsis: str | None = None
    bridge_applied: bool = False
    # Descriptive-only birth date that never takes part in merge or veto decisions
    # (Sleeper's date can differ from nflverse's); used for the attribute bridge
    # and as a last fallback for the canonical record's BirthDate.
    descriptive_birth_date: str | None = None


def ids_from_players(row: dict[str, str]) -> dict[str, str]:
    mapping = {
        "GSIS": "gsis_id",
        "ESPN": "espn_id",
        "PFR": "pfr_id",
        "PFF": "pff_id",
        "OTC": "otc_id",
        "NFL": "nfl_id",
        "ESB": "esb_id",
    }
    return {key: value for key, field in mapping.items() if (value := clean(row.get(field)))}


def ids_from_ff(row: dict[str, str]) -> dict[str, str]:
    mapping = {
        "GSIS": "gsis_id",
        "Sleeper": "sleeper_id",
        "ESPN": "espn_id",
        "PFR": "pfr_id",
        "PFF": "pff_id",
        "NFLCom": "nfl_id",
        "FantasyPros": "fantasypros_id",
        "MFL": "mfl_id",
        "Sportradar": "sportradar_id",
        "Yahoo": "yahoo_id",
        "Fleaflicker": "fleaflicker_id",
        "CBS": "cbs_id",
        "CFBRef": "cfbref_id",
        "Rotowire": "rotowire_id",
        "KTC": "ktc_id",
        "FantasyData": "fantasy_data_id",
    }
    return {key: value for key, field in mapping.items() if (value := clean(row.get(field)))}
