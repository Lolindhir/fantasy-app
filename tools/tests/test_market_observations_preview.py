"""#988 4B: read-only preview of every market-observations dataset/season key."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source.identity import MappingIndex  # noqa: E402
from external_source.market_observations import (  # noqa: E402
    MarketObservationError,
    candidate_path,
    canonical_json,
    digest,
    inventory,
    main,
    render_partition,
)
from external_source.registry import load_registry  # noqa: E402
from ci_tier import deep_only  # noqa: E402


class MarketObservationsReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.datasets = load_registry(REPO_ROOT)["datasets"]
        cls.empty_mappings = MappingIndex([])

    def test_registry_declares_19_datasets_with_rights_fields(self) -> None:
        self.assertEqual(19, len(self.datasets))
        self.assertTrue(all(d["rights"].get("storage") and d["rights"].get("publication") for d in self.datasets))

    @deep_only("full real-source market preview")
    def test_19_dataset_inventory_is_source_discovered_and_deterministic(self) -> None:
        entries = inventory(REPO_ROOT)
        self.assertEqual(19, len({e["DatasetID"] for e in entries}))
        self.assertEqual(19, len(self.datasets))
        self.assertTrue(all(e["ObservationCount"] >= 1 for e in entries))
        self.assertEqual(entries, sorted(entries, key=lambda e: (e["DatasetID"], e["ObservationSeason"])))
        self.assertEqual(entries, inventory(REPO_ROOT))
        self.assertEqual(2, sum(e["HistoryMode"] == "latest-only" for e in entries))
        self.assertTrue(all(e["ObservationSeason"] == 2026 for e in entries))

    @deep_only("full real-source market preview")
    def test_full_real_fftoday_history_is_deterministic_and_never_written(self) -> None:
        dataset_id = "fftoday.projection.redraft-qb-preseason"
        expected = next(e for e in inventory(REPO_ROOT) if e["DatasetID"] == dataset_id)
        before = candidate_path(REPO_ROOT, dataset_id, 2026)
        existed = before.exists()
        data = render_partition(REPO_ROOT, dataset_id, 2026, mapping_index=self.empty_mappings)
        self.assertEqual("market-observations", data["Product"])
        self.assertEqual(1, data["SchemaVersion"])
        self.assertEqual(expected["ObservationCount"], len(data["Observations"]))
        self.assertEqual("persisted-snapshots", data["HistoryMode"])
        self.assertTrue(all(o["SourceHash"] and o["Rows"] and o["SourcePath"] for o in data["Observations"]))
        self.assertTrue(all(o["Rows"][0]["IdentityStatus"] == "no-provider-key" for o in data["Observations"]))
        self.assertEqual(
            canonical_json(data),
            canonical_json(render_partition(REPO_ROOT, dataset_id, 2026, mapping_index=self.empty_mappings)),
        )
        self.assertEqual(existed, before.exists())
        self.assertEqual(digest(data), digest(data))

    @deep_only("full real-source market preview")
    def test_fantasycalc_pick_identity_provider_ownership_and_rights(self) -> None:
        data = render_partition(
            REPO_ROOT, "fantasycalc.value.dynasty-superflex-ppr-8-team", 2026,
            mapping_index=self.empty_mappings,
        )
        self.assertEqual(8, data["Format"]["providerTeamCount"])
        self.assertEqual("unknown", data["Rights"]["storage"])
        self.assertEqual("unknown", data["Rights"]["publication"])
        self.assertGreater(len(data["Observations"]), 2)
        observed = [row for snap in data["Observations"] for row in snap["Rows"]]
        self.assertTrue(any(row["AssetType"] == "draft_pick" for row in observed))
        self.assertTrue(all(
            row["IdentityStatus"] == "not-a-player" and row["CanonicalPlayerID"] is None
            for row in observed if row["AssetType"] == "draft_pick"
        ))
        self.assertTrue(all("actual_league_team_count" not in row["ProviderValues"] for row in observed))

    @deep_only("full real-source market preview")
    def test_sleeper_actions_share_existing_latest_without_inventing_archive(self) -> None:
        results = {
            action: render_partition(
                REPO_ROOT, f"sleeper.trending.{action}", 2026,
                mapping_index=self.empty_mappings,
            )
            for action in ("add", "drop")
        }
        a, d = results["add"]["Observations"][0], results["drop"]["Observations"][0]
        self.assertEqual("latest-only", results["add"]["HistoryMode"])
        self.assertEqual(1, len(results["add"]["Observations"]))
        self.assertEqual(a["SourcePath"], d["SourcePath"])
        self.assertEqual(a["SourceHash"], d["SourceHash"])
        self.assertNotEqual(a["SnapshotID"], d["SnapshotID"])
        self.assertEqual(len(a["Rows"]), len(d["Rows"]))
        self.assertTrue(any(row["ProviderValues"]["status"] == "not_listed" for row in a["Rows"]))
        self.assertTrue(all("comparison" not in row["ProviderValues"] for row in a["Rows"]))
        self.assertFalse(any(row["CanonicalPlayerID"] for row in a["Rows"]))

    def test_nonexistent_season_and_unknown_dataset_fail_closed(self) -> None:
        with self.assertRaisesRegex(MarketObservationError, "No observed Source partition"):
            render_partition(REPO_ROOT, "fftoday.projection.redraft-qb-preseason", 2021)
        with self.assertRaises(ValueError):
            render_partition(REPO_ROOT, "does.not.exist", 2026)

    @deep_only("full real-source market preview")
    def test_cli_preview_outputs_only_counts_hash_and_rights_no_player_content(self) -> None:
        # Avoid writing even to temporary folders: this is a pure in-memory CLI.
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            code = main([
                "--repo-root", str(REPO_ROOT), "preview", "--dataset-id",
                "fftoday.projection.redraft-qb-preseason", "--season", "2026",
            ])
        self.assertEqual(0, code)
        info = json.loads(output.getvalue())
        self.assertEqual("market-observations", info["Product"])
        self.assertEqual(64, len(info["CandidateSha256"]))
        self.assertGreater(info["RowCount"], 0)
        self.assertNotIn("Rows", info)
        self.assertEqual("read-only; no output file written", info["Mode"])


if __name__ == "__main__":
    unittest.main()
