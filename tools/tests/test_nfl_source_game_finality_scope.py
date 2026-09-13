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
from nfl_source_data_lib.finality_materialize import materialize_game_finality
from nfl_source_data_lib.phase1 import build_phase1_outputs


SCHEDULE_FIELDS = [
    "game_id",
    "season",
    "game_type",
    "week",
    "gameday",
    "weekday",
    "gametime",
    "away_team",
    "away_score",
    "home_team",
    "home_score",
]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fixed_seasonal_dataset(root: Path, dataset_id: str) -> Dataset:
    return Dataset(
        id=dataset_id,
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/raw.csv",
        raw_path=root / dataset_id / "raw.csv",
        metadata_path=root / dataset_id / "metadata.json",
        required_columns=("game_id",),
        minimum_rows=1,
        kind="test",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="fixed",
        source_format="csv",
        availability_policy="required",
        materialize=True,
    )


def write_league(root: Path, season: int) -> None:
    path = root / "public/data/League.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"Season": season}), encoding="utf-8")


def schedule_row(
    game_id: str,
    *,
    season: int = 2026,
    week: int = 1,
    away: str = "A",
    home: str = "B",
    away_score: int | None = None,
    home_score: int | None = None,
) -> dict[str, object]:
    return {
        "game_id": game_id,
        "season": season,
        "game_type": "REG",
        "week": week,
        "gameday": f"{season}-09-13",
        "weekday": "Sunday",
        "gametime": "13:00",
        "away_team": away,
        "away_score": "" if away_score is None else away_score,
        "home_team": home,
        "home_score": "" if home_score is None else home_score,
    }


class ScopedGameFinalityMaterializationTests(unittest.TestCase):
    def _datasets(self, root: Path) -> tuple[Dataset, Dataset, dict[str, Dataset]]:
        schedules = fixed_seasonal_dataset(root / "raw", "nflverse.schedules")
        finality = fixed_seasonal_dataset(root / "raw", "nflverse.game-finality")
        return schedules, finality, {schedules.id: schedules, finality.id: finality}

    def test_scoped_output_matches_full_phase1_and_second_run_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            write_csv(
                schedules.raw_path,
                SCHEDULE_FIELDS,
                [
                    schedule_row("2026_01_A_B", away_score=31, home_score=20),
                    schedule_row("2026_01_C_D", away="C", home="D", away_score=27, home_score=24),
                ],
            )
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])

            full_outputs, full_audit, _ = build_phase1_outputs(root, datasets, [], 2026)
            expected = next(
                payload
                for path, payload in full_outputs
                if path.as_posix().endswith("source-data/nfl/game-finality/2026.json")
            )

            first = materialize_game_finality(root, datasets)
            output_path = root / "source-data/nfl/game-finality/2026.json"
            actual = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(expected, actual)
            self.assertEqual(full_audit["gameFinality"], first["gameFinalityDiagnostics"])
            self.assertEqual(1, first["gameFinalityFilesChanged"])
            self.assertEqual(["source-data/nfl/game-finality/2026.json"], first["gameFinalityChangedPaths"])
            self.assertEqual(["source-data/nfl/game-finality/**"], first["writeSet"])

            by_game = {game["GameID"]: game for game in actual["Games"]}
            self.assertTrue(by_game["2026_01_A_B"]["Final"])
            self.assertFalse(by_game["2026_01_C_D"]["Final"])
            self.assertFalse(actual["Weeks"][0]["WeekFinal"])

            second = materialize_game_finality(root, datasets)
            self.assertEqual(0, second["gameFinalityFilesChanged"])
            self.assertEqual([], second["gameFinalityChangedPaths"])

    def test_changed_finality_evidence_updates_then_becomes_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            write_csv(
                schedules.raw_path,
                SCHEDULE_FIELDS,
                [
                    schedule_row("2026_01_A_B"),
                    schedule_row("2026_01_C_D", away="C", home="D"),
                ],
            )
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])
            materialize_game_finality(root, datasets)

            write_csv(
                finality.raw_path,
                ["game_id"],
                [{"game_id": "2026_01_A_B"}, {"game_id": "2026_01_C_D"}],
            )
            changed = materialize_game_finality(root, datasets)
            self.assertEqual(1, changed["gameFinalityFilesChanged"])
            payload = json.loads(
                (root / "source-data/nfl/game-finality/2026.json").read_text(encoding="utf-8")
            )
            self.assertTrue(all(game["Final"] for game in payload["Games"]))
            self.assertTrue(payload["Weeks"][0]["WeekFinal"])

            noop = materialize_game_finality(root, datasets)
            self.assertEqual(0, noop["gameFinalityFilesChanged"])

    def test_schedule_change_updates_finality_even_when_released_evidence_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            rows = [schedule_row("2026_01_A_B")]
            write_csv(schedules.raw_path, SCHEDULE_FIELDS, rows)
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])
            materialize_game_finality(root, datasets)

            rows.append(schedule_row("2026_01_C_D", away="C", home="D"))
            write_csv(schedules.raw_path, SCHEDULE_FIELDS, rows)
            changed = materialize_game_finality(root, datasets)
            self.assertEqual(1, changed["gameFinalityFilesChanged"])
            payload = json.loads(
                (root / "source-data/nfl/game-finality/2026.json").read_text(encoding="utf-8")
            )
            self.assertEqual(2, payload["Weeks"][0]["ApplicableGameCount"])
            self.assertEqual(1, payload["Weeks"][0]["FinalGameCount"])
            self.assertFalse(payload["Weeks"][0]["WeekFinal"])

    def test_missing_finality_output_is_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            write_csv(schedules.raw_path, SCHEDULE_FIELDS, [schedule_row("2026_01_A_B")])
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])
            materialize_game_finality(root, datasets)
            output_path = root / "source-data/nfl/game-finality/2026.json"
            output_path.unlink()

            rebuilt = materialize_game_finality(root, datasets)
            self.assertEqual(1, rebuilt["gameFinalityFilesChanged"])
            self.assertTrue(output_path.exists())

    def test_observation_season_switch_recomputes_partition_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            write_csv(
                schedules.raw_path,
                SCHEDULE_FIELDS,
                [
                    schedule_row("2026_01_A_B", season=2026),
                    schedule_row("2027_01_C_D", season=2027, away="C", home="D"),
                ],
            )
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])
            materialize_game_finality(root, datasets)
            payload_2026 = json.loads(
                (root / "source-data/nfl/game-finality/2026.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload_2026["Finalized"])

            write_league(root, 2027)
            switched = materialize_game_finality(root, datasets)
            self.assertEqual(1, switched["gameFinalityFilesChanged"])
            payload_2026 = json.loads(
                (root / "source-data/nfl/game-finality/2026.json").read_text(encoding="utf-8")
            )
            payload_2027 = json.loads(
                (root / "source-data/nfl/game-finality/2027.json").read_text(encoding="utf-8")
            )
            self.assertTrue(payload_2026["Finalized"])
            self.assertFalse(payload_2027["Finalized"])
            self.assertEqual(0, materialize_game_finality(root, datasets)["gameFinalityFilesChanged"])

    def test_unknown_released_game_id_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            write_csv(schedules.raw_path, SCHEDULE_FIELDS, [schedule_row("2026_01_A_B")])
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_UNKNOWN_X"}])
            with self.assertRaisesRegex(ValueError, "unknown schedule game_id"):
                materialize_game_finality(root, datasets)

    def test_duplicate_released_and_schedule_game_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            row = schedule_row("2026_01_A_B")
            write_csv(schedules.raw_path, SCHEDULE_FIELDS, [row])
            write_csv(
                finality.raw_path,
                ["game_id"],
                [{"game_id": "2026_01_A_B"}, {"game_id": "2026_01_A_B"}],
            )
            with self.assertRaisesRegex(ValueError, "Duplicate released-games game_id"):
                materialize_game_finality(root, datasets)

            write_csv(schedules.raw_path, SCHEDULE_FIELDS, [row, row])
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])
            with self.assertRaisesRegex(ValueError, "Duplicate nflverse schedule game_id"):
                materialize_game_finality(root, datasets)

    def test_historical_partition_stays_frozen_unless_force_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2027)
            schedules, finality, datasets = self._datasets(root)
            write_csv(
                schedules.raw_path,
                SCHEDULE_FIELDS,
                [
                    schedule_row("2026_01_A_B", season=2026),
                    schedule_row("2026_01_C_D", season=2026, away="C", home="D"),
                ],
            )
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])
            materialize_game_finality(root, datasets)
            output_path = root / "source-data/nfl/game-finality/2026.json"
            before = output_path.read_text(encoding="utf-8")

            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_C_D"}])
            frozen = materialize_game_finality(root, datasets)
            self.assertEqual(0, frozen["gameFinalityFilesChanged"])
            self.assertEqual(1, frozen["gameFinalityPartitionsPreserved"])
            self.assertEqual(before, output_path.read_text(encoding="utf-8"))

            repaired = materialize_game_finality(root, datasets, force=True)
            self.assertEqual(1, repaired["gameFinalityFilesChanged"])
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            by_game = {game["GameID"]: game for game in payload["Games"]}
            self.assertFalse(by_game["2026_01_A_B"]["Final"])
            self.assertTrue(by_game["2026_01_C_D"]["Final"])

    def test_scoped_run_does_not_touch_full_audit_or_foreign_canonical_areas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_league(root, 2026)
            schedules, finality, datasets = self._datasets(root)
            write_csv(schedules.raw_path, SCHEDULE_FIELDS, [schedule_row("2026_01_A_B")])
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2026_01_A_B"}])

            audit_path = root / "source-data/audits/nfl-source-data-audit.json"
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            audit_sentinel = '{"sentinel":"full-audit"}\n'
            audit_path.write_text(audit_sentinel, encoding="utf-8")
            foreign_path = root / "source-data/nfl/player-stats/2026/01.json"
            foreign_path.parent.mkdir(parents=True, exist_ok=True)
            foreign_sentinel = '{"sentinel":"foreign"}\n'
            foreign_path.write_text(foreign_sentinel, encoding="utf-8")

            result = materialize_game_finality(root, datasets)
            self.assertEqual(audit_sentinel, audit_path.read_text(encoding="utf-8"))
            self.assertEqual(foreign_sentinel, foreign_path.read_text(encoding="utf-8"))
            self.assertTrue(
                all(path.startswith("source-data/nfl/game-finality/") for path in result["gameFinalityChangedPaths"])
            )


if __name__ == "__main__":
    unittest.main()
