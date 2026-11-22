"""Issue #1627: ESPN snapshot tool and its wiring into the canonical schedule materializer (ADR-097)."""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from espn_schedule_snapshot import build_snapshot, snapshot_path, sync  # noqa: E402
from nfl_source_data_lib import common as common_mod  # noqa: E402
from nfl_source_data_lib.phase1 import _build_schedules  # noqa: E402

FIELDS = ["game_id", "season", "game_type", "week", "gameday", "weekday", "gametime", "away_team", "away_score",
          "home_team", "home_score", "espn"]


def row(game_id: str, espn: str, gameday: str = "2026-11-22", gametime: str = "13:00", **extra: str) -> dict[str, str]:
    base = {f: "" for f in FIELDS}
    base.update(game_id=game_id, season="2026", game_type="REG", week="11", gameday=gameday, weekday="Sunday",
                gametime=gametime, away_team="AAA", home_team="BBB", espn=espn)
    base.update(extra)
    return base


def make_dataset(root: Path, rows: list[dict[str, str]]) -> common_mod.Dataset:
    raw = root / "providers/nflverse/schedules/raw-latest.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    with raw.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return common_mod.Dataset(
        id="nflverse.schedules", provider="nflverse", upstream="test", source_url="https://example.invalid/g.csv",
        raw_path=raw, metadata_path=raw.parent / "metadata.json", required_columns=("game_id",), minimum_rows=1,
        kind="test", refresh_policy="current-season", retention_policy="permanent-by-season", license="test",
        attribution="test", lifecycle_class="seasonal-finalizable", partition_key="season",
        finalization_policy="freeze-prior-seasons", repair_policy="explicit-force", source_mode="fixed",
        source_format="csv", availability_policy="required",
    )


def write_snapshot(root: Path, observations: list[dict[str, str]]) -> None:
    path = snapshot_path(root, 2026)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"Observations": observations}), encoding="utf-8")


class MaterializerWiringTest(unittest.TestCase):
    def build(self, root: Path, rows: list[dict[str, str]]):
        # build() reads <root>/data-source/providers/espn/schedule; the dataset raw path is arbitrary.
        dataset = make_dataset(root / DATA_SOURCE_ROOT, rows)
        outputs, audit, _, index = _build_schedules(root, dataset, 2026, force=True)
        return outputs[0][1]["Games"], audit, index

    def test_snapshot_changes_kickoff_keeps_game_identity_and_marks_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_snapshot(root, [{"EspnGameID": "401", "KickoffUtc": "2026-11-22T21:25:00Z"}])
            games, audit, index = self.build(root, [row("2026_11_AAA_BBB", "401"), row("2026_11_CCC_DDD", "402")])
            by_id = {g["GameID"]: g for g in games}
            moved = by_id["2026_11_AAA_BBB"]
            self.assertEqual(("2026-11-22", "16:25", "espn"), (moved["GameDay"], moved["GameTime"], moved["TimeSource"]))
            self.assertEqual({"GameDay": "2026-11-22", "GameTime": "13:00"}, moved["TimeSourceNflverse"])
            self.assertNotIn("TimeSource", by_id["2026_11_CCC_DDD"])
            self.assertEqual("16:25", index["2026_11_AAA_BBB"]["GameTime"])
            self.assertEqual(1, len(audit["kickoffOverlayApplied"]))

    def test_without_snapshot_or_with_broken_snapshot_nflverse_is_unchanged(self) -> None:
        for broken in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                if broken:
                    path = snapshot_path(root, 2026)
                    path.parent.mkdir(parents=True)
                    path.write_text("{not json", encoding="utf-8")
                games, audit, _ = self.build(root, [row("2026_11_AAA_BBB", "401")])
                self.assertEqual("13:00", games[0]["GameTime"])
                self.assertNotIn("TimeSource", games[0])
                self.assertNotIn("kickoffOverlayApplied", audit)

    def test_repeated_build_is_identical_and_override_vanishes_when_nflverse_catches_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_snapshot(root, [{"EspnGameID": "401", "KickoffUtc": "2026-11-22T21:25:00Z"}])
            first, _, _ = self.build(root, [row("2026_11_AAA_BBB", "401")])
            second, _, _ = self.build(root, [row("2026_11_AAA_BBB", "401")])
            self.assertEqual(first, second)
            caught_up, audit, _ = self.build(root, [row("2026_11_AAA_BBB", "401", gametime="16:25")])
            self.assertNotIn("TimeSource", caught_up[0])
            self.assertNotIn("kickoffOverlayApplied", audit)

    def test_scored_game_is_never_overlaid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_snapshot(root, [{"EspnGameID": "401", "KickoffUtc": "2026-11-22T21:25:00Z"}])
            games, _, _ = self.build(root, [row("2026_11_AAA_BBB", "401", away_score="20", home_score="17")])
            self.assertEqual("13:00", games[0]["GameTime"])


class SnapshotToolTest(unittest.TestCase):
    GAMES = [
        {"GameID": "g1", "GameDay": "2026-11-22", "GameTime": "13:00", "ProviderGameIDs": {"ESPN": "401"}},
        {"GameID": "g2", "GameDay": "2026-11-22", "GameTime": "13:00", "ProviderGameIDs": {"ESPN": "402"}},
        {"GameID": "g3", "GameDay": "2026-11-01", "GameTime": "13:00", "AwayScore": 3, "HomeScore": 0,
         "ProviderGameIDs": {"ESPN": "403"}},
    ]
    TODAY = date(2026, 11, 22)

    @staticmethod
    def board(*events: tuple[str, str]):
        return lambda day: {"events": [{"id": i, "date": d} for i, d in events]}

    def test_merge_keeps_old_observations_on_outage_and_prunes_scored_games(self) -> None:
        def down(day: str):
            raise OSError("espn down")

        previous = {"401": "2026-11-22T21:25:00Z", "403": "2026-11-01T18:00:00Z"}
        payload, errors = build_snapshot(self.GAMES, previous, self.TODAY, 14, down, 2026)
        self.assertEqual(1, len(errors))
        self.assertEqual([{"EspnGameID": "401", "KickoffUtc": "2026-11-22T21:25:00Z"}], payload["Observations"])

    def test_fresh_observation_overrides_and_unparsable_is_ignored(self) -> None:
        payload, errors = build_snapshot(
            self.GAMES, {"401": "2026-11-22T18:00:00Z"}, self.TODAY, 14,
            self.board(("401", "2026-11-22T21:25Z"), ("402", "garbage")), 2026,
        )
        self.assertEqual([], errors)
        self.assertEqual([{"EspnGameID": "401", "KickoffUtc": "2026-11-22T21:25:00Z"}], payload["Observations"])

    def test_sync_writes_only_on_semantic_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schedule = root / DATA_SOURCE_ROOT / "nfl/schedules/2026.json"
            schedule.parent.mkdir(parents=True)
            schedule.write_text(json.dumps({"Games": self.GAMES}), encoding="utf-8")
            fetcher = self.board(("401", "2026-11-22T21:25Z"))
            first = sync(root, 2026, self.TODAY, 14, fetcher)
            second = sync(root, 2026, self.TODAY, 14, fetcher)
            self.assertTrue(first["Changed"])
            self.assertFalse(second["Changed"])


if __name__ == "__main__":
    unittest.main()
