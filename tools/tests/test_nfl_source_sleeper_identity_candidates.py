"""Sleeper platform snapshot as identity evidence replacing app.Players (#347 H1a)."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from nfl_source_data_lib.common import Dataset  # noqa: E402
from nfl_source_data_lib.identity import _build_components  # noqa: E402
from nfl_source_data_lib.identity_model import (  # noqa: E402
    ATTACH_ID_KEYS,
    PRIMARY_SOURCE_PREFERENCE,
    IdentityCandidate,
)
from nfl_source_data_lib.identity_sources import (  # noqa: E402
    normalize_nfl_team,
    sleeper_player_candidates,
)


def _dataset(root: Path, dataset_id: str, raw: str, **extra) -> Dataset:
    return Dataset(
        id=dataset_id,
        provider="test",
        upstream="test",
        source_url="https://example.invalid",
        raw_path=root / raw,
        metadata_path=root / "meta.json",
        required_columns=(),
        minimum_rows=1,
        kind="test",
        refresh_policy="periodic",
        retention_policy="latest",
        license="test",
        attribution="test",
        **extra,
    )


def _sleeper_row(sleeper_id, **overrides):
    row = {
        "player_id": sleeper_id,
        "full_name": f"Player {sleeper_id}",
        "first_name": "Player",
        "last_name": sleeper_id,
        "birth_date": "2003-06-12",
        "position": "WR",
        "fantasy_positions": ["WR"],
        "team": "GB",
        "espn_id": None,
        "gsis_id": "00-9999999",
    }
    row.update(overrides)
    return row


class SleeperIdentityCandidateTests(unittest.TestCase):
    def _fixture(self, sleeper_rows, roster_rows):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "sleeper.json").write_text(
            json.dumps({row["player_id"]: row for row in sleeper_rows}), encoding="utf-8"
        )
        roster_dir = root / "rosters"
        roster_dir.mkdir()
        with (roster_dir / "raw-2026.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["season", "team", "position", "birth_date", "gsis_id", "week"]
            )
            writer.writeheader()
            writer.writerows(roster_rows)
        datasets = {
            "sleeper.players": _dataset(root, "sleeper.players", "sleeper.json"),
            "nflverse.rosters": _dataset(
                root,
                "nflverse.rosters",
                "rosters/raw-{season}.csv",
                source_mode="season-partitioned",
            ),
        }
        return root, datasets

    def _run(self, datasets, root, **overrides):
        kwargs = dict(
            external_anchor_candidates={},
            persisted_sleeper_ids=set(),
            other_sleeper_ids=set(),
        )
        kwargs.update(overrides)
        return sleeper_player_candidates(root, datasets, 2026, **kwargs)

    def test_tank01_is_no_attach_key_and_sleeper_snapshot_replaces_app_players(self):
        self.assertEqual({"Sleeper"}, ATTACH_ID_KEYS)
        self.assertNotIn("app.Players", PRIMARY_SOURCE_PREFERENCE)
        self.assertIn("sleeper.players", PRIMARY_SOURCE_PREFERENCE)

    def test_population_needs_fantasy_position_birth_date_and_team_or_persisted_id(self):
        rows = [
            _sleeper_row("1"),
            _sleeper_row("2", position="LB", fantasy_positions=["LB"]),
            _sleeper_row("3", birth_date=None),
            _sleeper_row("4", team=None),
            _sleeper_row("5", team=None),
            _sleeper_row("6", position="DB", fantasy_positions=["DB", "WR"]),
        ]
        root, datasets = self._fixture(rows, [])
        candidates, _ = self._run(datasets, root, persisted_sleeper_ids={"5"})
        self.assertEqual(["1", "5", "6"], [c.ids["Sleeper"] for c in candidates])
        self.assertTrue(all(c.ids == {"Sleeper": c.ids["Sleeper"]} for c in candidates))
        self.assertEqual("WR", candidates[2].position)

    def test_sleeper_birth_date_is_descriptive_and_never_vetoes_a_merge(self):
        root, datasets = self._fixture([_sleeper_row("1")], [])
        candidates, _ = self._run(datasets, root)
        self.assertIsNone(candidates[0].birth_date)
        self.assertEqual("2003-06-12", candidates[0].descriptive_birth_date)

    def test_espn_bridge_only_for_new_sleeper_ids_with_corroborated_anchor(self):
        anchor = IdentityCandidate(
            ids={"GSIS": "00-1", "ESPN": "77"}, name=None, first_name=None, last_name=None,
            birth_date=None, position=None, latest_team=None, source="nflverse.players", priority=10,
        )
        rows = [
            _sleeper_row("1", espn_id=77),
            _sleeper_row("2", espn_id=77),
            _sleeper_row("3", espn_id=88),
        ]
        root, datasets = self._fixture(rows, [])
        candidates, _ = self._run(
            datasets,
            root,
            external_anchor_candidates={("ESPN", "77"): [anchor]},
            other_sleeper_ids={"2"},
        )
        by_id = {c.ids["Sleeper"]: c.ids for c in candidates}
        self.assertEqual({"Sleeper": "1", "ESPN": "77"}, by_id["1"])
        self.assertEqual({"Sleeper": "2"}, by_id["2"])  # known Sleeper ID: no ESPN claim
        self.assertEqual({"Sleeper": "3"}, by_id["3"])  # ESPN not corroborated

    def test_attribute_bridge_requires_unique_match_and_new_sleeper_id(self):
        rows = [
            _sleeper_row("1"),
            _sleeper_row("2", birth_date="2001-01-01"),
            _sleeper_row("3", birth_date="2002-02-02", team="LAR"),
            _sleeper_row("4", birth_date="2000-05-05"),
            _sleeper_row("5", birth_date="2000-05-05", last_name="twin"),
        ]
        roster = [
            {"season": "2026", "team": "GB", "position": "WR", "birth_date": "2003-06-12", "gsis_id": "00-1", "week": "3"},
            {"season": "2026", "team": "GB", "position": "WR", "birth_date": "2003-06-12", "gsis_id": "00-1", "week": "4"},
            {"season": "2026", "team": "GB", "position": "WR", "birth_date": "2001-01-01", "gsis_id": "00-2", "week": "4"},
            {"season": "2026", "team": "GB", "position": "WR", "birth_date": "2001-01-01", "gsis_id": "00-3", "week": "4"},
            {"season": "2026", "team": "LA", "position": "WR", "birth_date": "2002-02-02", "gsis_id": "00-4", "week": "4"},
            {"season": "2026", "team": "GB", "position": "WR", "birth_date": "2000-05-05", "gsis_id": "00-5", "week": "4"},
        ]
        root, datasets = self._fixture(rows, roster)
        candidates, diagnostics = self._run(datasets, root)
        bridge = {c.ids["Sleeper"]: c.bridge_gsis for c in candidates}
        self.assertEqual("00-1", bridge["1"])  # one roster record, latest week wins
        self.assertIsNone(bridge["2"])  # two roster records share the attributes
        self.assertEqual("00-4", bridge["3"])  # LAR is the same franchise as LA
        self.assertIsNone(bridge["4"])  # two Sleeper records share the attributes
        self.assertIsNone(bridge["5"])
        self.assertEqual(
            {"2001-01-01", "2000-05-05"}, {item["BirthDate"] for item in diagnostics}
        )
        persisted_candidates, _ = self._run(datasets, root, persisted_sleeper_ids={"1", "3"})
        self.assertTrue(all(c.bridge_gsis is None for c in persisted_candidates if c.ids["Sleeper"] in {"1", "3"}))

    def test_bridge_attaches_to_roster_component_and_respects_contradicting_ids(self):
        def nfl(gsis, sleeper=None):
            ids = {"GSIS": gsis}
            if sleeper:
                ids["Sleeper"] = sleeper
            return IdentityCandidate(
                ids=ids, name=None, first_name=None, last_name=None,
                birth_date="2003-06-12", position="WR", latest_team="GB",
                source="nflverse.players", priority=10,
            )

        def sleeper(sleeper_id, gsis):
            return IdentityCandidate(
                ids={"Sleeper": sleeper_id}, name=None, first_name=None, last_name=None,
                birth_date="2003-06-12", position="WR", latest_team="GB",
                source="sleeper.players", priority=30, bridge_gsis=gsis,
            )

        candidates = [nfl("00-1"), sleeper("S1", "00-1"), nfl("00-2", "S-other"), sleeper("S2", "00-2")]
        uf = _build_components(candidates)
        self.assertEqual(uf.find(0), uf.find(1))
        self.assertNotEqual(uf.find(2), uf.find(3))  # contradicting Sleeper ID keeps it separate


if __name__ == "__main__":
    unittest.main()
