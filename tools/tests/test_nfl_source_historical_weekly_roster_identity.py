"""Regression tests for Issue #1061 historical weekly-roster GSIS identity repair."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset
from nfl_source_data_lib.identity_model import IdentityCandidate
from nfl_source_data_lib.identity_sources import historical_weekly_roster_identity_candidates
from nfl_source_data_lib.lifecycle import effective_partition_payload


def weekly_dataset(root: Path) -> Dataset:
    return Dataset(
        id="nflverse.weekly-rosters", provider="nflverse", upstream="test",
        source_url="https://example.invalid/weekly-{season}.csv",
        raw_path=root / "raw-weekly-{season}.csv",
        metadata_path=root / "metadata-{season}.json",
        required_columns=(), minimum_rows=1, kind="test",
        refresh_policy="test", retention_policy="test", license="test",
        attribution="test", source_mode="season-partitioned",
        lifecycle_class="seasonal-finalizable", partition_key="season-week",
        finalization_policy="freeze-prior-seasons", repair_policy="explicit-force",
    )


def known(gsis: str, source: str = "nflverse.players") -> IdentityCandidate:
    return IdentityCandidate(
        ids={"GSIS": gsis}, name=None, first_name=None, last_name=None,
        birth_date=None, position=None, latest_team=None, source=source, priority=10,
    )


class HistoricalWeeklyRosterIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dataset = weekly_dataset(self.root)
        self.datasets = {self.dataset.id: self.dataset}

    def raw(self, year: int, gsis: list[str]):
        with (self.root / f"raw-weekly-{year}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["gsis_id", "full_name", "week", "status"])
            writer.writeheader()
            for gsis_id in gsis:
                writer.writerow({
                    "gsis_id": gsis_id, "full_name": "Untrusted Name",
                    "week": 1, "status": "CUT",
                })

    def persisted(self, players: list[dict]):
        target = self.root / "data-source/nfl/identities/players.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"Players": players}), encoding="utf-8")

    def test_new_real_weekly_roster_gsis_becomes_provider_only_candidate(self):
        self.raw(2024, ["00-0039723", "00-0039723", "0", "XX-3"])
        self.raw(2025, ["00-0040381"])
        rows = historical_weekly_roster_identity_candidates(self.root, self.datasets, [])
        self.assertEqual([c.ids for c in rows], [
            {"GSIS": "00-0039723"}, {"GSIS": "00-0040381"},
        ])
        self.assertTrue(all(c.name is None and c.birth_date is None and c.position is None for c in rows))
        self.assertTrue(all(c.source == "nflverse.weekly-rosters" for c in rows))

    def test_already_known_gsis_is_not_reassigned(self):
        self.raw(2024, ["00-0039723", "00-0040381"])
        candidates = historical_weekly_roster_identity_candidates(
            self.root, self.datasets, [known("00-0039723")],
        )
        self.assertEqual([c.ids["GSIS"] for c in candidates], ["00-0040381"])

    def test_roster_owned_identity_replays_after_first_materialization(self):
        self.raw(2024, ["00-0039723"])
        self.persisted([{
            "CanonicalPlayerID": "NFLP-persisted", "IDs": {"GSIS": "00-0039723"},
            "Sources": ["nflverse.weekly-rosters"],
        }])
        rows = historical_weekly_roster_identity_candidates(
            self.root, self.datasets, [known("00-0039723", "canonical-existing")],
        )
        self.assertEqual([c.ids["GSIS"] for c in rows], ["00-0039723"])
        self.assertEqual(rows[0].source, "nflverse.weekly-rosters")

    def test_no_replay_of_other_source_without_roster_provenance(self):
        self.raw(2024, ["00-0039723"])
        self.persisted([{
            "CanonicalPlayerID": "NFLP-existing", "IDs": {"GSIS": "00-0039723"},
            "Sources": ["nflverse.players"],
        }])
        rows = historical_weekly_roster_identity_candidates(
            self.root, self.datasets, [known("00-0039723", "canonical-existing")],
        )
        self.assertEqual(rows, [])

    def test_frozen_week_enriches_only_null_identity(self):
        old = self.payload([None, "NFLP-existing"])
        new = self.payload(["NFLP-new", "NFLP-existing"])
        self.assertEqual(self.effective(old, new), (new, False))

    def test_frozen_week_never_changes_known_identity(self):
        old = self.payload(["NFLP-existing"])
        new = self.payload(["NFLP-someone-else"])
        self.assertEqual(self.effective(old, new), (old, True))

    def test_frozen_week_rejects_other_fact_mutation(self):
        old = self.payload([None])
        new = self.payload(["NFLP-new"])
        new["Records"][0]["Status"] = "ACT"
        self.assertEqual(self.effective(old, new), (old, True))

    def test_frozen_week_rejects_deleted_existing_identity(self):
        old = self.payload(["NFLP-existing"])
        new = self.payload([None])
        self.assertEqual(self.effective(old, new), (old, True))

    def payload(self, ids: list[str | None]):
        return {
            "SchemaVersion": 2, "Season": 2024, "Week": 1,
            "SourceDataset": "nflverse.weekly-rosters", "Finalized": True,
            "Records": [
                {"CanonicalPlayerID": cid, "SourceIDs": {"GSIS": f"00-{i:07d}"},
                 "Team": "SEA", "Position": "WR", "Status": "CUT"}
                for i, cid in enumerate(ids, 39000)
            ],
        }

    def effective(self, old, candidate):
        path = self.root / "derived-frozen.json"
        path.write_text(json.dumps(old), encoding="utf-8")
        return effective_partition_payload(
            self.dataset, path=path, candidate=candidate,
            partition_season=2024, observation_season=2026,
        )


class CurrentRepositoryHistoricalIdentityAudit(unittest.TestCase):
    @unittest.skipUnless(
        (TOOLS.parent / "data-source/nfl/identities/players.json").is_file(),
        "Requires persisted canonical source data",
    )
    def test_missing_2024_2025_gsis_are_source_owned_and_count_impact(self):
        from nfl_source_data_lib.common import load_registry

        root = TOOLS.parent
        datasets = {item.id: item for item in load_registry(root)}
        identity = json.loads(
            (root / "data-source/nfl/identities/players.json").read_text(encoding="utf-8")
        )
        existing_gsis = {
            token
            for row in identity["Players"]
            for token in [row.get("IDs", {}).get("GSIS"),
                          *(row.get("IDAliases", {}).get("GSIS") or [])]
            if token
        }
        known_candidates = [known(token, "canonical-existing") for token in existing_gsis]
        fallback = historical_weekly_roster_identity_candidates(
            root, datasets, known_candidates,
        )
        fallback_ids = {row.ids["GSIS"] for row in fallback}
        target: set[str] = set()
        for season, week in ((2024, 1), (2024, 2), (2025, 1)):
            payload = json.loads((root / (
                f"data-source/nfl/weekly-rosters/{season}/{week:02d}.json"
            )).read_text(encoding="utf-8"))
            for row in payload["Records"]:
                if (row.get("Position") in {"QB", "RB", "WR", "TE", "FB", "K"}
                        and row.get("Status") != "RET"
                        and not row.get("CanonicalPlayerID")):
                    gsis = row.get("SourceIDs", {}).get("GSIS")
                    if gsis not in existing_gsis:
                        target.add(gsis)
        missing = target - fallback_ids
        print(
            f"Historical roster-only identity candidate impact: total={len(fallback_ids)} "
            f"target={len(target)} missing={len(missing)}", flush=True,
        )
        self.assertFalse(missing, sorted(missing)[:15])
        self.assertGreaterEqual(len(target), 100)

    @unittest.skipUnless(
        (TOOLS.parent / "data-source/nfl/identities/players.json").is_file(),
        "Requires persisted canonical source data",
    )
    def test_read_only_identity_rebuild_impact_and_existing_gsis_owners(self):
        """Inspect actual full-graph effects before publishing roster-only identities."""
        from collections import defaultdict

        from nfl_source_data_lib.common import load_registry
        from nfl_source_data_lib.identity import build_identities

        root = TOOLS.parent
        datasets = {item.id: item for item in load_registry(root)}
        previous = json.loads(
            (root / "data-source/nfl/identities/players.json").read_text(encoding="utf-8")
        )["Players"]
        rebuilt, _, conflicts, provider_claims, mapping_conflicts = build_identities(
            root, datasets,
        )

        def gsis_owners(rows):
            owners = defaultdict(set)
            for player in rows:
                gsis = [
                    (player.get("IDs") or {}).get("GSIS"),
                    *((player.get("IDAliases") or {}).get("GSIS") or []),
                ]
                for value in gsis:
                    if value:
                        owners[value].add(player["CanonicalPlayerID"])
            return owners

        old_owners = gsis_owners(previous)
        new_owners = gsis_owners(rebuilt)
        previous_ids = {row["CanonicalPlayerID"] for row in previous}
        rebuilt_ids = {row["CanonicalPlayerID"] for row in rebuilt}
        new_only = rebuilt_ids - previous_ids
        lost = previous_ids - rebuilt_ids
        reassigned_gsis = {
            token: (sorted(owners), sorted(new_owners.get(token, set())))
            for token, owners in old_owners.items()
            if owners != new_owners.get(token, set())
        }
        added_gsis = set(new_owners) - set(old_owners)
        print(
            "Historical weekly-roster full-graph impact (read-only): "
            f"prior_players={len(previous_ids)} rebuilt_players={len(rebuilt_ids)} "
            f"new_players={len(new_only)} lost_players={len(lost)} "
            f"new_gsis={len(added_gsis)} changed_existing_gsis={len(reassigned_gsis)} "
            f"provider_claims={len(provider_claims)} "
            f"mapping_conflicts={len(mapping_conflicts)} "
            f"source_conflicts={len(conflicts)}",
            flush=True,
        )
        print(
            f"New identity sample: {sorted(new_only)[:10]}; "
            f"existing GSIS change sample: {list(sorted(reassigned_gsis.items()))[:10]}",
            flush=True,
        )
        self.assertFalse(lost, sorted(lost)[:20])
        self.assertFalse(reassigned_gsis, list(sorted(reassigned_gsis.items()))[:20])



if __name__ == "__main__":
    unittest.main()
