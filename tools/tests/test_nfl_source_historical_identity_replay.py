"""Full real-source replay gate for #1061. Never writes into the live checkout."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from ci_tier import deep_only  # noqa: E402
from nfl_source_data_lib.common import load_registry  # noqa: E402
from nfl_source_data_lib.materialize import materialize  # noqa: E402
from nfl_source_data_lib.phase1 import _ODDS_FIELD_NAMES  # noqa: E402
from nfl_source_data_lib.player_profiles import _PROFILE_FIELDS  # noqa: E402
from nfl_source_data_lib.common import CANONICAL_SCHEMA_VERSION  # noqa: E402
from historical_fantasy_scoring_parity import build_parity_report  # noqa: E402
from player_week_fantasy_materialize import (  # noqa: E402
    _week_finality, build_player_week_fantasy_dataset,
    output_path as pwf_output_path, write_dataset,
)
from team_week_performance_materialize import (  # noqa: E402
    discover_finalized_weeks, materialize_all_finalized,
)

SOURCE = TOOLS.parent
TARGETS = ((2024, 1), (2024, 2), (2025, 1))
POSITIONS = {"QB", "RB", "WR", "TE", "FB", "K"}


def snapshot(root: Path) -> dict[str, str]:
    """Hash all canonical NFL and source-audit outputs; raw evidence is input."""
    result = {}
    for directory in ("data-source/nfl", "data-source/audits"):
        for path in sorted((root / directory).rglob("*.json")):
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            result[str(path.relative_to(root))] = digest.hexdigest()
    return result


def safe_frozen_enrichment(old: dict, new: dict) -> tuple[bool, int]:
    """Non-ID payloads, record ordering, and all existing IDs must be equal."""
    before = json.loads(json.dumps(old))
    after = json.loads(json.dumps(new))
    old_rows, new_rows = before.get("Records"), after.get("Records")
    if not isinstance(old_rows, list) or not isinstance(new_rows, list):
        return False, 0
    if len(old_rows) != len(new_rows):
        return False, 0
    filled = 0
    for old_row, new_row in zip(old_rows, new_rows, strict=True):
        old_id = old_row.pop("CanonicalPlayerID", None)
        new_id = new_row.pop("CanonicalPlayerID", None)
        if old_id not in (None, "") and old_id != new_id:
            return False, filled
        if old_id in (None, "") and new_id not in (None, ""):
            filled += 1
    return before == after, filled




def safe_current_roster_refresh(old: dict, new: dict) -> tuple[bool, int, int]:
    """Accept mutable live roster facts, never reassignment of an existing GSIS owner.

    Historical/finalized weekly rosters still use safe_frozen_enrichment and
    require exact non-identity parity. The current-season roster is not frozen:
    a newer persisted provider raw snapshot can legitimately change its facts.
    """
    if (old.get("Season") != new.get("Season") or
            old.get("Season") != 2026 or
            old.get("SourceDataset") != new.get("SourceDataset") or
            not old.get("SourceDataset")):
        return False, 0, 0

    def by_gsis(payload: dict) -> dict[str, str | None] | None:
        rows = payload.get("Records")
        if not isinstance(rows, list) or not rows:
            return None
        result: dict[str, str | None] = {}
        for row in rows:
            if not isinstance(row, dict):
                return None
            source_ids = row.get("SourceIDs") or {}
            if not isinstance(source_ids, dict):
                return None
            gsis = source_ids.get("GSIS")
            owner = row.get("CanonicalPlayerID")
            if owner and not gsis:
                return None  # Cannot audit an existing owner without its provider key.
            if gsis:
                key = str(gsis)
                if key in result and result[key] != owner:
                    return None  # A player on multiple teams must retain one owner.
                result[key] = owner
        return result if result else None

    before, after = by_gsis(old), by_gsis(new)
    if before is None or after is None:
        return False, 0, 0
    shared = before.keys() & after.keys()
    protected = [key for key in shared if before[key]]
    if not protected or any(before[key] != after[key] for key in protected):
        return False, 0, len(protected)
    filled = sum(1 for key in shared if not before[key] and after[key])
    return True, filled, len(protected)


def safe_weekly_roster_replay(old: dict, new: dict) -> tuple[bool, int, bool]:
    """Frozen weekly facts must match; mutable current-season weeks keep GSIS owners."""
    if old.get("Finalized") is True or new.get("Finalized") is True:
        # Source partitions frozen after season close: only null -> player ID.
        safe, filled = safe_frozen_enrichment(old, new)
        return safe, filled, False
    if (old.get("Finalized") is not False or new.get("Finalized") is not False or
            old.get("Week") != new.get("Week") or
            not isinstance(old.get("Week"), int) or
            old.get("SourceDataset") != "nflverse.weekly-rosters" or
            new.get("SourceDataset") != "nflverse.weekly-rosters"):
        return False, 0, True
    safe, filled, _ = safe_current_roster_refresh(old, new)
    return safe, filled, True


def safe_current_profile_refresh(old: dict, new: dict) -> tuple[bool, int]:
    """Permit refreshed nflverse profile *facts*, never reassigned player identities.

    A profile is a derived projection of mutable provider raw facts, not a
    canonical identity owner. Its GSIS <-> CanonicalPlayerID pairs are stable for
    all continuing IDs; adding/removing provider rows is allowed.
    """
    expected_fields = {"CanonicalPlayerID", "GSISID"} | {
        output_field for output_field, _, _ in _PROFILE_FIELDS
    }

    def index(payload: dict) -> tuple[dict[str, str], dict[str, str]] | None:
        if (payload.get("SchemaVersion") != CANONICAL_SCHEMA_VERSION
                or payload.get("SourceDataset") != "nflverse.players"
                or set(payload) != {"SchemaVersion", "SourceDataset", "Records"}):
            return None
        records = payload.get("Records")
        if not isinstance(records, list) or not records:
            return None
        by_canonical: dict[str, str] = {}
        by_gsis: dict[str, str] = {}
        for row in records:
            if not isinstance(row, dict) or set(row) != expected_fields:
                return None
            cid, gsis = row["CanonicalPlayerID"], row["GSISID"]
            if not isinstance(cid, str) or not cid or not isinstance(gsis, str) or not gsis:
                return None
            if cid in by_canonical or gsis in by_gsis:
                return None
            by_canonical[cid] = gsis
            by_gsis[gsis] = cid
        return by_canonical, by_gsis

    previous, rebuilt = index(old), index(new)
    if previous is None or rebuilt is None:
        return False, 0
    old_canonical, old_gsis = previous
    new_canonical, new_gsis = rebuilt
    if any(old_canonical[cid] != new_canonical[cid] for cid in old_canonical.keys() & new_canonical.keys()):
        return False, 0
    if any(old_gsis[gsis] != new_gsis[gsis] for gsis in old_gsis.keys() & new_gsis.keys()):
        return False, 0
    return True, len(old_canonical.keys() & new_canonical.keys())


def safe_current_odds_refresh(old: dict, new: dict) -> bool:
    """A live odds refresh may update market quotes, never schedule identity."""
    before = json.loads(json.dumps(old))
    after = json.loads(json.dumps(new))
    if not isinstance(before.get("Games"), list) or not isinstance(after.get("Games"), list):
        return False
    for payload in (before, after):
        for game in payload["Games"]:
            for field in _ODDS_FIELD_NAMES.values():
                game.pop(field, None)
    return before == after


def safe_current_sleeper_refresh(old: dict, new: dict) -> bool:
    """Provider roster refresh must not reassign previously owned Sleeper IDs."""
    before, after = old.get("Records"), new.get("Records")
    if not isinstance(before, list) or not isinstance(after, list):
        return False
    new_by_id = {row.get("SleeperPlayerID"): row for row in after}
    if len(new_by_id) != len(after) or None in new_by_id:
        return False
    old_by_id = {row.get("SleeperPlayerID"): row for row in before}
    if len(old_by_id) != len(before) or None in old_by_id:
        return False
    return all(
        not record.get("CanonicalPlayerID")
        or player_id not in new_by_id
        or record["CanonicalPlayerID"] == new_by_id[player_id].get("CanonicalPlayerID")
        for player_id, record in old_by_id.items()
    )


def audit_provider_mapping_and_possible_duplicates(source, root, weekly_changed, previous, rebuilt):
    """Read-only provider mapping and potential cross-provider duplicate risk audit."""
    from collections import defaultdict

    old_ids = {row["CanonicalPlayerID"] for row in previous}
    fresh = {row["CanonicalPlayerID"] for row in rebuilt if row["CanonicalPlayerID"] not in old_ids}

    def provider_index(rows):
        index = defaultdict(set)
        for row in rows:
            cid = row["CanonicalPlayerID"]
            for provider, token in (row.get("IDs") or {}).items():
                if token:
                    index[(provider, str(token))].add(cid)
            for provider, aliases in (row.get("IDAliases") or {}).items():
                for token in aliases or []:
                    if token:
                        index[(provider, str(token))].add(cid)
        return index

    old_tokens = provider_index(previous)
    relative_mapping = "data-source/nfl/identities/provider-mappings.json"
    oldmap = json.loads((source / relative_mapping).read_text(encoding="utf-8"))
    newmap = json.loads((root / relative_mapping).read_text(encoding="utf-8"))

    def claim_intervals(rows):
        claims = defaultdict(list)
        for row in rows:
            key = (str(row.get("Provider")), str(row.get("ExternalID")),
                   str(row.get("CanonicalPlayerID")))
            low = int(row.get("FirstObservedSeason") or 0)
            high = int(row.get("LastObservedSeason") or low)
            claims[key].append((low, high))
        return claims

    before = claim_intervals(oldmap.get("Mappings", []))
    after = claim_intervals(newmap.get("Mappings", []))

    def covered(low, high, intervals):
        cursor = low
        for first, last in sorted(intervals):
            if first > cursor:
                break
            cursor = max(cursor, last + 1)
            if cursor > high:
                return True
        return False

    lost_claims = [
        (key, interval) for key, spans in before.items()
        for interval in spans if not covered(*interval, after.get(key, []))
    ]
    old_by_token = defaultdict(list)
    for (provider, token, cid), intervals in before.items():
        for low, high in intervals:
            old_by_token[(provider, token)].append((cid, low, high))

    def conflict_signature(row):
        return (str(row.get("Provider")), str(row.get("ExternalID")),
                tuple(sorted(row.get("CanonicalPlayerIDs") or [])),
                int(row.get("FirstObservedSeason") or 0),
                int(row.get("LastObservedSeason") or 0))

    oldconf = {conflict_signature(row) for row in oldmap.get("Conflicts", [])}
    newconf = {conflict_signature(row) for row in newmap.get("Conflicts", [])}
    new_ambiguous = newconf - oldconf
    new_ambiguous_for_fresh = [entry for entry in new_ambiguous
                               if any(owner in fresh for owner in entry[2])]
    old_history = {json.dumps(row, sort_keys=True)
                   for row in oldmap.get("HistoricalResolutionConflicts", [])}
    new_history = {json.dumps(row, sort_keys=True)
                   for row in newmap.get("HistoricalResolutionConflicts", [])}
    old_name_dob = defaultdict(set)
    for row in previous:
        name = " ".join(str(row.get("Name") or "").casefold().split())
        dob = str(row.get("BirthDate") or "").strip()
        if name and dob:
            old_name_dob[(name, dob)].add(row["CanonicalPlayerID"])

    active_overlaps = {}
    season_overlaps = {}
    name_dob_matches = {}
    gsis_birthdays = defaultdict(set)
    seen_new = set()
    for relative_path in weekly_changed:
        year = int(relative_path.split("/")[3])
        records = json.loads((root / relative_path).read_text(encoding="utf-8"))["Records"]
        for row in records:
            cid = row.get("CanonicalPlayerID")
            if cid not in fresh:
                continue
            seen_new.add(cid)
            src = row.get("SourceIDs") or {}
            gsis = src.get("GSIS")
            dob = str(row.get("BirthDate") or "").strip()
            name = " ".join(str(row.get("PlayerName") or "").casefold().split())
            if gsis and dob:
                gsis_birthdays[gsis].add(dob)
            if name and dob and (matches := old_name_dob.get((name, dob))):
                name_dob_matches.setdefault(cid, [gsis, name, dob, sorted(matches)])
            for provider, token in src.items():
                if provider == "GSIS" or not token:
                    continue
                key = (provider, str(token))
                matches = old_tokens.get(key, set())
                if matches:
                    active_overlaps.setdefault((cid, provider, str(token)),
                                               [gsis, year, sorted(matches)])
                historical = sorted({owner for owner, low, high in old_by_token.get(key, [])
                                     if low <= year <= high})
                if historical:
                    season_overlaps.setdefault((cid, provider, str(token)),
                                               [gsis, year, historical])

    conflicting_birthdays = {gsis: sorted(dobs)
                             for gsis, dobs in gsis_birthdays.items() if len(dobs) > 1}
    report = {
        "old_mapping_count": len(oldmap.get("Mappings", [])),
        "new_mapping_count": len(newmap.get("Mappings", [])),
        "old_conflict_count": len(oldmap.get("Conflicts", [])),
        "new_conflict_count": len(newmap.get("Conflicts", [])),
        "lost_prior_mapping_intervals": len(lost_claims),
        "lost_prior_mapping_sample": lost_claims[:8],
        "new_ambiguous_conflict_keys": len(new_ambiguous),
        "removed_ambiguous_conflict_keys": len(oldconf - newconf),
        "new_conflicts_involving_new_identity": len(new_ambiguous_for_fresh),
        "new_identity_conflict_sample": new_ambiguous_for_fresh[:8],
        "prior_historical_resolution_conflicts": len(old_history),
        "rebuilt_historical_resolution_conflicts": len(new_history),
        "new_historical_resolution_conflicts": len(new_history - old_history),
        "lost_historical_resolution_conflicts": len(old_history - new_history),
        "new_identities_present_in_rewritten_rosters": len(seen_new),
        "new_identity_provider_overlap_count": len(active_overlaps),
        "new_identity_provider_overlap_sample": list(active_overlaps.items())[:12],
        "new_identity_season_valid_provider_overlap_count": len(season_overlaps),
        "new_identity_season_valid_provider_overlap_sample": list(season_overlaps.items())[:12],
        "name_and_dob_possible_duplicate_count": len(name_dob_matches),
        "name_and_dob_possible_duplicate_sample": list(name_dob_matches.items())[:12],
        "same_gsis_contradictory_birthdays_count": len(conflicting_birthdays),
        "same_gsis_contradictory_birthdays_sample": list(conflicting_birthdays.items())[:8],
    }
    print("#1061 provider and potential-duplicate audit: "
          + json.dumps(report, ensure_ascii=False), flush=True)
    return report


class MutableProfileRefreshTests(unittest.TestCase):
    @staticmethod
    def profile(records: list[dict]) -> dict:
        return {"SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "SourceDataset": "nflverse.players", "Records": records}

    @staticmethod
    def row(cid: str, gsis: str, status: str = "ACT") -> dict:
        return {
            "CanonicalPlayerID": cid, "GSISID": gsis,
            **{field: None for field, _, _ in _PROFILE_FIELDS},
            "Status": status,
        }

    def test_mutable_facts_and_new_or_retired_profiles_do_not_change_owners(self):
        before = self.profile([self.row("NFLP-one", "00-001"),
                               self.row("NFLP-retired", "00-002")])
        after = self.profile([self.row("NFLP-one", "00-001", "INA"),
                              self.row("NFLP-new", "00-003")])
        self.assertEqual(safe_current_profile_refresh(before, after), (True, 1))

    def test_existing_canonical_or_gsis_identity_reassignment_is_rejected(self):
        old = self.profile([self.row("NFLP-one", "00-001")])
        for changed in (self.row("NFLP-one", "00-002"),
                        self.row("NFLP-two", "00-001")):
            with self.subTest(changed=changed):
                self.assertFalse(safe_current_profile_refresh(old, self.profile([changed]))[0])

    def test_duplicate_profile_keys_and_malformed_records_are_rejected(self):
        old = self.profile([self.row("NFLP-one", "00-001")])
        variants = [
            [self.row("NFLP-one", "00-001"), self.row("NFLP-one", "00-002")],
            [self.row("NFLP-one", "00-001"), self.row("NFLP-two", "00-001")],
            [{**self.row("NFLP-one", "00-001"), "Other": "unclassified"}],
            [{**self.row("NFLP-one", "00-001"), "GSISID": ""}],
        ]
        for rows in variants:
            with self.subTest(rows=rows):
                self.assertFalse(safe_current_profile_refresh(old, self.profile(rows))[0])

    def test_schema_and_source_contract_mismatch_fail_closed(self):
        old = self.profile([self.row("NFLP-one", "00-001")])
        for key, value in (("SourceDataset", "other"),
                           ("SchemaVersion", CANONICAL_SCHEMA_VERSION + 1),
                           ("Unclassified", "value")):
            with self.subTest(key=key):
                changed = {**old, key: value}
                self.assertFalse(safe_current_profile_refresh(old, changed)[0])


class MutableCurrentRosterRefreshTests(unittest.TestCase):
    @staticmethod
    def roster(records: list[dict]) -> dict:
        return {"Season": 2026, "SourceDataset": "nflverse.rosters", "Records": records}

    @staticmethod
    def player(gsis: str, owner: str | None, status: str = "ACT") -> dict:
        return {"SourceIDs": {"GSIS": gsis}, "CanonicalPlayerID": owner,
                "Status": status}

    def test_live_fact_and_population_changes_preserve_existing_owners(self):
        old = self.roster([self.player("00-001", "NFLP-one"),
                           self.player("00-002", None)])
        new = self.roster([self.player("00-001", "NFLP-one", "INA"),
                           self.player("00-002", "NFLP-two"),
                           self.player("00-003", "NFLP-three")])
        self.assertEqual(safe_current_roster_refresh(old, new), (True, 1, 1))
        self.assertFalse(safe_frozen_enrichment(old, new)[0])

    def test_previous_gsis_owner_cannot_be_reassigned_or_lost(self):
        old = self.roster([self.player("00-001", "NFLP-one")])
        for owner in ("NFLP-other", None):
            with self.subTest(owner=owner):
                new = self.roster([self.player("00-001", owner, "INA")])
                self.assertFalse(safe_current_roster_refresh(old, new)[0])

    def test_same_gsis_can_move_teams_without_losing_stable_identity(self):
        old = self.roster([self.player("00-001", "NFLP-one")])
        # The canonical season roster is keyed by (Team, GSIS), so a trade
        # can legitimately leave two rows for one player across teams.
        new = self.roster([self.player("00-001", "NFLP-one", "ACT"),
                           self.player("00-001", "NFLP-one", "INA")])
        self.assertEqual(safe_current_roster_refresh(old, new), (True, 0, 1))

    def test_conflicting_duplicate_or_unkeyed_resolved_player_fails_closed(self):
        old = self.roster([self.player("00-001", "NFLP-one")])
        conflicts = self.roster([self.player("00-001", "NFLP-one"),
                                 self.player("00-001", "NFLP-other")])
        unkeyed = self.roster([self.player("00-001", "NFLP-one"),
                               self.player("", "NFLP-two")])
        self.assertFalse(safe_current_roster_refresh(old, conflicts)[0])
        self.assertFalse(safe_current_roster_refresh(old, unkeyed)[0])

    def test_source_identity_and_season_contract_must_stay_equal(self):
        old = self.roster([self.player("00-001", "NFLP-one")])
        changed = self.roster([self.player("00-001", "NFLP-one", "INA")])
        for field, value in (("Season", 2025), ("SourceDataset", "different")):
            with self.subTest(field=field):
                bad = {**changed, field: value}
                self.assertFalse(safe_current_roster_refresh(old, bad)[0])

    def test_nonfinal_current_week_may_refresh_facts_not_gsis_owner(self):
        old = {**self.roster([self.player("00-001", "NFLP-one")]),
               "Week": 1, "Finalized": False,
               "SourceDataset": "nflverse.weekly-rosters"}
        new = {**old, "Records": [self.player("00-001", "NFLP-one", "INA")]}
        self.assertEqual(safe_weekly_roster_replay(old, new), (True, 0, True))
        switched = {**new, "Records": [self.player("00-001", "NFLP-other", "INA")]}
        self.assertFalse(safe_weekly_roster_replay(old, switched)[0])
        different_week = {**new, "Week": 2}
        self.assertFalse(safe_weekly_roster_replay(old, different_week)[0])

    def test_finalized_week_requires_full_nonidentity_parity(self):
        old = {**self.roster([self.player("00-001", "NFLP-one")]),
               "Season": 2025, "Week": 1, "Finalized": True,
               "SourceDataset": "nflverse.weekly-rosters"}
        changed_facts = {**old, "Records": [self.player("00-001", "NFLP-one", "INA")]}
        self.assertFalse(safe_weekly_roster_replay(old, changed_facts)[0])
        enriched = {**old, "Records": [self.player("00-001", "NFLP-one")]}
        self.assertEqual(safe_weekly_roster_replay(old, enriched), (True, 0, False))


@deep_only("full real-source scratch replay (15-20 min)")
class HistoricalIdentityIsolatedFullReplay(unittest.TestCase):
    @unittest.skipUnless(
        (SOURCE / "data-source/nfl/identities/players.json").is_file(),
        "Requires persisted canonical NFL sources",
    )
    def test_real_source_materialization_and_second_no_op(self):
        with tempfile.TemporaryDirectory(prefix="nfl-1061-source-replay-") as scratch:
            root = Path(scratch)
            # Real copies, NEVER hardlinks or symlinks for writable canonical data.
            shutil.copytree(SOURCE / "data-source", root / "data-source")
            app = root / "public/data"
            app.mkdir(parents=True)
            players = SOURCE / "public/data/Players.json"
            if players.is_file():
                shutil.copy2(players, app / "Players.json")
            past = SOURCE / "public/data/past_seasons"
            if past.is_dir():
                (app / "past_seasons").mkdir()
                for file in sorted(past.glob("Players_*.json")):
                    shutil.copy2(file, app / "past_seasons" / file.name)

            # Downstream producers also need canonical manual league metadata and
            # the unchanged FantasyRelevance PowerShell slot-eligibility bridge.
            # These are disposable test copies, never production write targets.
            shutil.copytree(SOURCE / "data-meta", root / "data-meta")
            shutil.copytree(SOURCE / "public/requests/utils", root / "public/requests/utils")

            baseline = snapshot(root)
            old_rosters = {
                (year, week): json.loads((root /
                    f"data-source/nfl/weekly-rosters/{year}/{week:02d}.json").read_text(encoding="utf-8"))
                for year, week in TARGETS
            }
            datasets = {d.id: d for d in load_registry(root) if d.materialize}
            first = materialize(root, datasets, force=False)
            once = snapshot(root)
            paths = sorted(set(baseline) | set(once))
            changed = [p for p in paths if baseline.get(p) != once.get(p)]
            fixed = {
                "data-source/nfl/identities/players.json",
                "data-source/nfl/identities/provider-mappings.json",
                "data-source/audits/nfl-source-data-audit.json",
            }
            prefixes = ("data-source/nfl/weekly-rosters/", "data-source/nfl/player-stats/")
            # Current-season roster facts are mutable between provider raw
            # fetch and canonical publication. Preserve the strict identity-only
            # check when facts are equal; otherwise require unchanged ownership
            # for every continuing GSIS rather than rejecting legitimate facts.
            # Frozen historical weekly rosters below retain full field parity.
            current_roster = "data-source/nfl/rosters/2026.json"
            if current_roster in changed:
                old_current = json.loads((SOURCE / current_roster).read_text(encoding="utf-8"))
                new_current = json.loads((root / current_roster).read_text(encoding="utf-8"))
                identity_only, current_filled = safe_frozen_enrichment(old_current, new_current)
                if identity_only:
                    self.assertGreater(current_filled, 0, "Current roster changed without identity enrichment")
                    preserved = None
                else:
                    current_safe, current_filled, preserved = safe_current_roster_refresh(
                        old_current, new_current,
                    )
                    self.assertTrue(
                        current_safe,
                        "Current roster 2026 changed an existing GSIS identity or its source contract",
                    )
                print(
                    f"#1061 current roster 2026: identity_only={identity_only}, "
                    f"newly_filled={current_filled}, preserved_owners={preserved}",
                    flush=True,
                )
                fixed.add(current_roster)

            weekly_changed = [p for p in changed if p.startswith("data-source/nfl/weekly-rosters/")]
            weekly_filled = 0
            live_weekly_refreshes = 0
            for relative_path in weekly_changed:
                old_week = json.loads((SOURCE / relative_path).read_text(encoding="utf-8"))
                new_week = json.loads((root / relative_path).read_text(encoding="utf-8"))
                safe, filled, is_live = safe_weekly_roster_replay(old_week, new_week)
                self.assertTrue(safe, f"Unexpected factual/identity drift in {relative_path}")
                weekly_filled += filled
                live_weekly_refreshes += int(is_live)
            print(
                f"#1061 all changed weekly rosters: "
                f"partitions={len(weekly_changed)}, "
                f"mutable_current_partitions={live_weekly_refreshes}, "
                f"newly_filled={weekly_filled}, frozen_non_identity_drift=0",
                flush=True,
            )
            # This test compares a live repository snapshot with a full rebuild.
            # Concurrent NFL Source raw updates can leave *other* canonical
            # read models temporarily stale while the identity fix remains
            # isolated. Classify only the two known independently owned live
            # producer outputs, and validate their unaffected invariant fields:
            # never ignore arbitrary new changed paths or identity reassignment.
            live_odds = "data-source/nfl/schedule-odds/2026.json"
            if live_odds in changed:
                old_odds = json.loads((SOURCE / live_odds).read_text(encoding="utf-8"))
                new_odds = json.loads((root / live_odds).read_text(encoding="utf-8"))
                self.assertTrue(
                    safe_current_odds_refresh(old_odds, new_odds),
                    "Odds refresh changed schedule facts, not just market quotes",
                )
                fixed.add(live_odds)
            live_sleeper = "data-source/nfl/platform/sleeper/players.json"
            if live_sleeper in changed:
                old_sleeper = json.loads((SOURCE / live_sleeper).read_text(encoding="utf-8"))
                new_sleeper = json.loads((root / live_sleeper).read_text(encoding="utf-8"))
                self.assertTrue(
                    safe_current_sleeper_refresh(old_sleeper, new_sleeper),
                    "Sleeper raw refresh re-mapped a previously owned provider ID",
                )
                fixed.add(live_sleeper)
            print(
                "#1061 independent live raw refresh outputs: "
                f"odds={live_odds in changed}, sleeper={live_sleeper in changed}, "
                "schedule_identity_and_sleeper_owner_safe=True",
                flush=True,
            )
            # nflverse.players raw is refreshed independently of the last
            # canonical profile projection. Mutable profile attributes (e.g.
            # Status/LatestTeam) are not identity drift; all continuing source
            # GSIS-to-canonical assignments must remain unchanged.
            live_profiles = "data-source/nfl/player-profiles/nflverse.json"
            if live_profiles in changed:
                old_profiles = json.loads((SOURCE / live_profiles).read_text(encoding="utf-8"))
                new_profiles = json.loads((root / live_profiles).read_text(encoding="utf-8"))
                safe_profiles, preserved_profiles = safe_current_profile_refresh(
                    old_profiles, new_profiles,
                )
                self.assertTrue(safe_profiles, "Live NFL profile refresh changed an existing GSIS identity or schema")
                print(
                    f"#1061 independent live nflverse player profiles: "
                    f"stable_existing_owners={preserved_profiles}",
                    flush=True,
                )
                fixed.add(live_profiles)
            unexpected = [p for p in changed if p not in fixed and not p.startswith(prefixes)]
            print(
                "#1061 real isolated materialization: "
                f"canonical_players={first['identityCount']}, "
                f"changed_outputs={len(changed)}, unexpected={len(unexpected)}, "
                f"changed_paths={changed[:90]}, unexpected_paths={unexpected[:30]}",
                flush=True,
            )

            prior_ids = {
                row["CanonicalPlayerID"]
                for row in json.loads((SOURCE / "data-source/nfl/identities/players.json")
                                      .read_text(encoding="utf-8"))["Players"]
            }
            replay_ids = {
                row["CanonicalPlayerID"]
                for row in json.loads((root / "data-source/nfl/identities/players.json")
                                      .read_text(encoding="utf-8"))["Players"]
            }
            self.assertFalse(prior_ids - replay_ids, "Previously issued identities disappeared")
            print(f"#1061 newly added canonical identities={len(replay_ids - prior_ids)}", flush=True)
            old_players = json.loads((SOURCE / "data-source/nfl/identities/players.json")
                                     .read_text(encoding="utf-8"))["Players"]
            new_players = json.loads((root / "data-source/nfl/identities/players.json")
                                     .read_text(encoding="utf-8"))["Players"]
            impact = audit_provider_mapping_and_possible_duplicates(
                SOURCE, root, weekly_changed, old_players, new_players,
            )
            self.assertFalse(impact["lost_prior_mapping_intervals"],
                             "Existing provider mapping validity was lost in source replay")
            self.assertFalse(impact["new_conflicts_involving_new_identity"],
                             "New canonical identity appears in ambiguous provider claim")
            self.assertFalse(impact["new_identity_season_valid_provider_overlap_count"],
                             "New roster-only GSIS identity overlaps an existing provider owner in the same season; adjudication required")
            self.assertFalse(impact["lost_historical_resolution_conflicts"],
                             "Existing historical mapping conflict provenance was lost")

            for year, week in TARGETS:
                path = root / f"data-source/nfl/weekly-rosters/{year}/{week:02d}.json"
                result = json.loads(path.read_text(encoding="utf-8"))
                safe, filled = safe_frozen_enrichment(old_rosters[(year, week)], result)
                unresolved = [
                    row for row in result["Records"]
                    if row.get("Position") in POSITIONS
                    and row.get("Status") != "RET"
                    and not row.get("CanonicalPlayerID")
                ]
                print(
                    f"#1061 {year}/W{week:02d}: "
                    f"frozen_non_id_equal={safe}, newly_filled={filled}, "
                    f"relevant_unresolved={len(unresolved)}",
                    flush=True,
                )
                self.assertTrue(safe, f"Frozen facts or existing identities changed: {path}")
                self.assertFalse(unresolved, f"Unresolved PWF-relevant rows: {path}")
                old_relevant_unresolved = [
                    row for row in old_rosters[(year, week)]["Records"]
                    if row.get("Position") in POSITIONS
                    and row.get("Status") != "RET"
                    and not row.get("CanonicalPlayerID")
                ]
                if old_relevant_unresolved:
                    self.assertGreater(filled, 0, f"No identity enrichment: {path}")

            second = materialize(root, datasets, force=False)
            twice = snapshot(root)
            drift = sorted(p for p in set(once) | set(twice) if once.get(p) != twice.get(p))
            print(
                f"#1061 second isolated materialization: changed={len(drift)}, "
                f"identityChanged={second['identityChanged']}, "
                f"mappingsChanged={second['providerMappingsChanged']}, "
                f"drift_paths={drift[:30]}",
                flush=True,
            )
            self.assertFalse(drift, f"Second run not a no-op: {drift[:30]}")
            self.assertFalse(unexpected, f"Unexpected canonical outputs: {unexpected[:30]}")

            # Cross-PR acceptance: #1060's historical producer is not merged,
            # so exercise its existing PWF calculation/finality primitives on
            # this safely corrected Source copy, then the real strict TWP
            # materializer. No derived data or app output leaves the scratch root.
            targets = discover_finalized_weeks(root, league_id="nfl-reise")
            self.assertGreaterEqual(len(targets), 39, "Expected at least 39 finalized league weeks")
            pwf_blocked = []
            pwf_ready = 0
            pwf_compared = 0
            for league_id, year, week in targets:
                try:
                    complete, game_ids = _week_finality(root, season=year, week=week)
                    if complete is not True or not game_ids:
                        raise ValueError("NFL week finality not proven")
                    payload = build_player_week_fantasy_dataset(
                        root, league_id=league_id, season=year, week=week,
                    )
                    metadata = payload.get("Materialization") or {}
                    if (
                        metadata.get("ActualScoringEvidenceFinalized") is not True
                        or metadata.get("TargetRosterProvisional") is not False
                        or not isinstance(payload.get("Records"), list)
                        or not payload["Records"]
                    ):
                        raise ValueError("PWF final actual or target roster evidence incomplete")
                    target = pwf_output_path(
                        root, league_id=league_id, season=year, week=week,
                    )
                    write_dataset(target, payload)
                    pwf_compared += len(payload["Records"])
                    pwf_ready += 1
                except (ValueError, TypeError, KeyError, OSError) as error:
                    pwf_blocked.append((year, week, str(error)))
            print(
                f"#1061 downstream historical PWF strict preflight: "
                f"targets={len(targets)}, ready={pwf_ready}, "
                f"blocked={len(pwf_blocked)}, records={pwf_compared}, "
                f"blockers={pwf_blocked[:10]}",
                flush=True,
            )
            self.assertFalse(pwf_blocked, f"Historical PWF source preflight blocked: {pwf_blocked[:10]}")

            # Explicitly require the just-rebuilt final PWF records for every
            # week; never substitute existing published Derived/App snapshots.
            twp = materialize_all_finalized(
                root, league_id="nfl-reise", require_pwf=True, write=False,
            )
            failed_parity = [
                (row["Season"], row["Week"], row.get("Reason"))
                for row in twp["Weeks"] if row["Status"] != "ready"
            ]
            unverified = [
                (row["Season"], row["Week"], row.get("PlayerWeekFantasyParity"))
                for row in twp["Weeks"]
                if (row.get("PlayerWeekFantasyParity") or {}).get("State") != "verified"
            ]
            print(
                f"#1061 downstream TWP strict PWF parity: "
                f"targets={twp['TargetCount']}, ready={twp['ReadyCount']}, "
                f"blocked={twp['BlockedCount']}, "
                f"unverified={len(unverified)}, blockers={failed_parity[:12]}, "
                f"unverified_sample={unverified[:5]}",
                flush=True,
            )
            self.assertEqual(twp["TargetCount"], len(targets))

            # Issue #698 / merged PR #733 independently established one
            # provider-stat divergence: Caleb Williams, 2025 W06 (nflverse
            # 20.38 vs Sleeper 19.88). Only the exact documented exception
            # is accepted; every other divergence still fails closed.
            known_provider = build_parity_report(
                root, league_id="nfl-reise", nfl_season=2025,
                scoring_season=2025, first_week=6, last_week=6,
            )
            self.assertFalse(known_provider["MissingNonZeroCanonicalStats"])
            self.assertFalse(known_provider["UnsupportedPlayerWeeks"])
            self.assertEqual(
                len(known_provider["Mismatches"]), 1,
                "Previously classified provider divergence changed; adjudicate anew",
            )
            divergence = known_provider["Mismatches"][0]
            self.assertEqual(
                (divergence["PlayerName"], divergence["Week"],
                 divergence["DerivedPoints"], divergence["LeaguePoints"]),
                ("Caleb Williams", 6, 20.38, 19.88),
                "The #698 historical provider-stat discrepancy has changed",
            )
            self.assertEqual(failed_parity, [], "Unexpected TWP blocker with documented #698 exception")
            self.assertEqual(
                [(year, week) for year, week, _ in unverified], [(2025, 6)],
                "Unexpected weeks lack verified PWF parity",
            )
            self.assertEqual(twp["ReadyCount"], len(targets))
            self.assertEqual(twp["BlockedCount"], 0)
            self.assertEqual(unverified[0][2]["State"], "accepted-divergence")
            self.assertEqual(unverified[0][2]["AcceptedDivergences"], 1)
            print(
                "#1061 downstream acceptance classification: 39/39 PWF source "
                "builds pass; TWP 39/39 ready (38 strictly verified plus "
                "one audited #698 provider-stat divergence in 2025 W06). "
                "No blanket waiver or Derived production publication.",
                flush=True,
            )



if __name__ == "__main__":
    unittest.main()
