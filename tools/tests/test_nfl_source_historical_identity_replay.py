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
from nfl_source_data_lib.common import load_registry  # noqa: E402
from nfl_source_data_lib.materialize import materialize  # noqa: E402
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
            # Current-season roster output is not frozen, but identity-only
            # enrichment must still preserve all other fields and existing owners.
            current_roster = "data-source/nfl/rosters/2026.json"
            if current_roster in changed:
                old_current = json.loads((SOURCE / current_roster).read_text(encoding="utf-8"))
                new_current = json.loads((root / current_roster).read_text(encoding="utf-8"))
                current_safe, current_filled = safe_frozen_enrichment(old_current, new_current)
                print(
                    f"#1061 current roster 2026: identity_only={current_safe}, "
                    f"newly_filled={current_filled}",
                    flush=True,
                )
                self.assertTrue(current_safe, "Current roster 2026 changed non-identity facts")
                self.assertGreater(current_filled, 0, "Current roster changed without identity enrichment")
                fixed.add(current_roster)

            weekly_changed = [p for p in changed if p.startswith("data-source/nfl/weekly-rosters/")]
            weekly_filled = 0
            for relative_path in weekly_changed:
                old_week = json.loads((SOURCE / relative_path).read_text(encoding="utf-8"))
                new_week = json.loads((root / relative_path).read_text(encoding="utf-8"))
                safe, filled = safe_frozen_enrichment(old_week, new_week)
                self.assertTrue(safe, f"Unexpected factual/identity drift in {relative_path}")
                weekly_filled += filled
            print(
                f"#1061 all changed weekly rosters: "
                f"partitions={len(weekly_changed)}, newly_filled={weekly_filled}, "
                "non_identity_drift=0",
                flush=True,
            )
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
            # 20.38 vs Sleeper 19.88). Strict TWP parity MUST still block this
            # week. Keep that production gate unchanged, but prove its sole
            # blocker comes from the pre-existing documented scoring evidence,
            # not from this Issue #1061 identity repair. No ID join is hardcoded.
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
            expected_reason = (
                "PlayerWeekFantasy scoring mismatch for "
                f"{divergence['CanonicalPlayerID']}: "
                f"league={divergence['LeaguePoints']}, "
                f"pwf={divergence['DerivedPoints']}"
            )
            self.assertEqual(
                failed_parity, [(2025, 6, expected_reason)],
                "Strict TWP parity has unexpected blockers besides #698",
            )
            self.assertEqual(
                [(year, week) for year, week, _ in unverified], [(2025, 6)],
                "Unexpected weeks lack verified PWF parity",
            )
            self.assertEqual(twp["ReadyCount"], len(targets) - 1)
            print(
                "#1061 downstream acceptance classification: 39/39 PWF source "
                "builds pass; TWP 38/39 strictly verified, with sole known "
                "#698 provider-stat divergence (2025 W06) still blocking "
                "strict full-release parity. No TWP acceptance waiver.",
                flush=True,
            )



if __name__ == "__main__":
    unittest.main()
