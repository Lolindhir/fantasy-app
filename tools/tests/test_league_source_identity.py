from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data import combine_sync_results  # noqa: E402
from league_source_data_lib.core import (  # noqa: E402
    LeagueBootstrap,
    build_manifest,
    canonical_league_season_id,
    discover_sleeper_lineage,
    load_bootstraps,
    sync_bootstrap,
)


CANONICAL_ID = "cl-220306ac3f9b480fa865e124098d8f56"
IDS = {
    2026: "1354177383984267264",
    2025: "1257421353431080960",
    2024: "1133541805053714432",
}


def league(season: int, previous: str | None) -> dict:
    return {
        "league_id": IDS.get(season, str(9000000000000000000 + season)),
        "season": str(season),
        "previous_league_id": previous,
        "name": "Fixture League",
        "settings": {"playoff_week_start": 15},
    }


class LeagueSourceIdentityTests(unittest.TestCase):
    def test_canonical_season_id_is_stable_and_provider_independent(self) -> None:
        first = canonical_league_season_id(CANONICAL_ID, 2026)
        second = canonical_league_season_id(CANONICAL_ID, 2026)
        other = canonical_league_season_id(CANONICAL_ID, 2025)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("cls-"))
        self.assertNotEqual(first, other)
        self.assertNotIn(IDS[2026], first)

    def test_discovers_current_to_historical_lineage(self) -> None:
        fixtures = {
            IDS[2026]: league(2026, IDS[2025]),
            IDS[2025]: league(2025, IDS[2024]),
            IDS[2024]: league(2024, None),
        }
        found = discover_sleeper_lineage(IDS[2026], fixtures.__getitem__)
        self.assertEqual([item.season for item in found], [2026, 2025, 2024])

    def test_cycle_fails_closed(self) -> None:
        fixtures = {
            IDS[2026]: league(2026, IDS[2025]),
            IDS[2025]: league(2025, IDS[2026]),
        }
        with self.assertRaisesRegex(ValueError, "cycle"):
            discover_sleeper_lineage(IDS[2026], fixtures.__getitem__)

    def test_non_decreasing_previous_season_fails_closed(self) -> None:
        fixtures = {
            IDS[2026]: league(2026, IDS[2025]),
            IDS[2025]: {**league(2025, None), "season": "2026"},
        }
        with self.assertRaisesRegex(ValueError, "must decrease"):
            discover_sleeper_lineage(IDS[2026], fixtures.__getitem__)

    def test_new_current_must_attach_to_known_latest_provider_instance(self) -> None:
        bootstrap = LeagueBootstrap(CANONICAL_ID, "Sleeper", "9000000000000002027", Path("bootstrap.json"))
        old_2025 = league(2025, IDS[2024])
        old_2024 = league(2024, None)
        existing = build_manifest(
            LeagueBootstrap(CANONICAL_ID, "Sleeper", IDS[2025], Path("bootstrap.json")),
            discover_sleeper_lineage(IDS[2025], {IDS[2025]: old_2025, IDS[2024]: old_2024}.__getitem__),
            {},
        )
        wrong_current = {
            "league_id": "9000000000000002027",
            "season": "2027",
            "previous_league_id": IDS[2024],
        }
        lineage = discover_sleeper_lineage(
            "9000000000000002027",
            {
                "9000000000000002027": wrong_current,
                IDS[2024]: old_2024,
            }.__getitem__,
        )
        with self.assertRaisesRegex(ValueError, "does not connect"):
            build_manifest(bootstrap, lineage, {CANONICAL_ID: existing})

    def test_cross_league_provider_mapping_conflict_fails_closed(self) -> None:
        fixtures = {
            IDS[2026]: league(2026, IDS[2025]),
            IDS[2025]: league(2025, IDS[2024]),
            IDS[2024]: league(2024, None),
        }
        lineage = discover_sleeper_lineage(IDS[2026], fixtures.__getitem__)
        other_id = "cl-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        conflicting = {
            "schemaVersion": 1,
            "CanonicalLeagueID": other_id,
            "Provider": "Sleeper",
            "CurrentCanonicalLeagueSeasonID": canonical_league_season_id(other_id, 2025),
            "CurrentProviderLeagueID": IDS[2025],
            "Seasons": [
                {
                    "CanonicalLeagueSeasonID": canonical_league_season_id(other_id, 2025),
                    "Season": 2025,
                    "PreviousCanonicalLeagueSeasonID": None,
                    "ProviderMappings": [
                        {
                            "Provider": "Sleeper",
                            "ProviderLeagueID": IDS[2025],
                            "PreviousProviderLeagueID": None,
                        }
                    ],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "already mapped"):
            build_manifest(
                LeagueBootstrap(CANONICAL_ID, "Sleeper", IDS[2026], Path("bootstrap.json")),
                lineage,
                {other_id: conflicting},
            )

    def test_sync_is_semantic_noop_on_second_identical_pass(self) -> None:
        fixtures = {
            IDS[2026]: league(2026, IDS[2025]),
            IDS[2025]: league(2025, IDS[2024]),
            IDS[2024]: league(2024, None),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_dir = root / "source-data/leagues/_bootstrap"
            bootstrap_dir.mkdir(parents=True)
            bootstrap_path = bootstrap_dir / f"{CANONICAL_ID}.json"
            bootstrap_path.write_text(
                json.dumps(
                    {
                        "CanonicalLeagueID": CANONICAL_ID,
                        "Provider": "Sleeper",
                        "CurrentProviderLeagueID": IDS[2026],
                    }
                ),
                encoding="utf-8",
            )
            bootstrap = load_bootstraps(root)[0]
            first = sync_bootstrap(root, bootstrap, fixtures.__getitem__)
            second = sync_bootstrap(root, bootstrap, fixtures.__getitem__)
            self.assertEqual(first["SeasonCount"], 3)
            self.assertGreater(first["RawFilesChanged"], 0)
            self.assertTrue(first["ManifestChanged"])
            self.assertEqual(second["RawFilesChanged"], 0)
            self.assertFalse(second["ManifestChanged"])

    def test_reporting_preserves_bootstrap_raw_changes(self) -> None:
        identity = {
            "CanonicalLeagueID": CANONICAL_ID,
            "SeasonCount": 3,
            "RawFilesChanged": 2,
            "ManifestChanged": False,
        }
        raw = {
            "DatasetPartitions": 138,
            "RawFilesChanged": 0,
            "MetadataFilesChanged": 0,
        }
        combined = combine_sync_results(identity, raw)
        self.assertEqual(combined["RawFilesChanged"], 2)
        self.assertEqual(combined["DatasetPartitions"], 138)
        self.assertEqual(combined["MetadataFilesChanged"], 0)
        self.assertFalse(combined["ManifestChanged"])

    def test_multiple_bootstraps_are_supported_without_single_league_assumption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "source-data/leagues/_bootstrap"
            directory.mkdir(parents=True)
            values = [
                (CANONICAL_ID, IDS[2026]),
                ("cl-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "9999999999999999999"),
            ]
            for canonical_id, provider_id in values:
                (directory / f"{canonical_id}.json").write_text(
                    json.dumps(
                        {
                            "CanonicalLeagueID": canonical_id,
                            "Provider": "Sleeper",
                            "CurrentProviderLeagueID": provider_id,
                        }
                    ),
                    encoding="utf-8",
                )
            loaded = load_bootstraps(root)
            self.assertEqual([item.canonical_league_id for item in loaded], sorted(item[0] for item in values))


if __name__ == "__main__":
    unittest.main()
