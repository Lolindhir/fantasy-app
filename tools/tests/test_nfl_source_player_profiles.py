import csv
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset, load_registry
from nfl_source_data_lib.phase1 import build_phase1_outputs
from nfl_source_data_lib.player_profiles import PLAYER_PROFILES_RELATIVE_PATH, build_player_profiles

FIELDS = [
    "gsis_id", "display_name", "short_name", "birth_date", "position_group", "position", "headshot",
    "rookie_season", "last_season", "latest_team", "status",
]


def players_dataset(raw: Path) -> Dataset:
    return Dataset(
        "nflverse.players", "nflverse", "test", "https://example.invalid/players.csv", raw, Path("metadata.json"),
        ("gsis_id",), 1, "identity", "periodic", "latest-with-git-history", "test", "test",
        lifecycle_class="dynamic", partition_key="none", finalization_policy="never", repair_policy="normal",
        source_mode="fixed", source_format="csv", availability_policy="required", materialize=True,
    )


def canonical(player_id: str, gsis: str, aliases: list[str] | None = None) -> dict:
    return {"CanonicalPlayerID": player_id, "IDs": {"GSIS": gsis}, "IDAliases": {"GSIS": aliases or []}}


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def row(gsis: str, **extra) -> dict:
    base = {
        "gsis_id": gsis, "display_name": f"Name {gsis}", "short_name": "N.Name", "birth_date": "2000-01-02",
        "position_group": "WR", "position": "WR", "headshot": f"https://img.invalid/{gsis}.png",
        "rookie_season": "2022", "last_season": "2025", "latest_team": "KC", "status": "ACT",
    }
    base.update(extra)
    return base


class PlayerProfileTests(unittest.TestCase):
    def build(self, rows: list[dict], identities: list[dict]):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "players.csv"
            write_rows(raw, rows)
            return build_player_profiles(Path(tmp), players_dataset(raw), identities)

    def test_repository_registry_materializes_players_dataset(self):
        active = {dataset.id: dataset for dataset in load_registry(REPO_ROOT)}
        self.assertTrue(active["nflverse.players"].materialize)

    def test_projects_profile_fields_onto_resolved_identity_and_is_deterministic(self):
        rows = [row("00-A"), row("00-B", short_name="", headshot="NA", rookie_season="", status="")]
        identities = [canonical("CP-b", "00-B"), canonical("CP-a", "00-A")]
        (path, payload), = self.build(rows, identities)[0]
        self.assertEqual(PLAYER_PROFILES_RELATIVE_PATH, str(path.relative_to(path.parents[3])))
        self.assertEqual(payload, self.build(list(reversed(rows)), identities)[0][0][1])
        by_id = {r["CanonicalPlayerID"]: r for r in payload["Records"]}
        full = by_id["CP-a"]
        self.assertEqual(
            ("N.Name", "https://img.invalid/00-A.png", "WR", 2022, 2025, "ACT"),
            (full["ShortName"], full["Headshot"], full["PositionGroup"], full["RookieSeason"], full["LastSeason"], full["Status"]),
        )
        sparse = by_id["CP-b"]
        for key in ("ShortName", "Headshot", "RookieSeason", "Status"):
            self.assertIsNone(sparse[key])

    def test_unresolved_rows_are_counted_not_persisted_and_never_create_identity(self):
        rows = [row("00-A"), row("00-UNKNOWN")]
        outputs, audit, _ = self.build(rows, [canonical("CP-a", "00-A")])
        self.assertEqual(["CP-a"], [r["CanonicalPlayerID"] for r in outputs[0][1]["Records"]])
        self.assertEqual({"sourceRowCount": 2, "recordCount": 1, "unresolvedIdentityCount": 1}, audit)

    def test_duplicate_gsis_fails_closed(self):
        with self.assertRaises(ValueError):
            self.build([row("00-A"), row("00-A")], [canonical("CP-a", "00-A")])

    def test_two_rows_resolving_to_one_canonical_player_fail_closed(self):
        with self.assertRaises(ValueError):
            self.build([row("00-A"), row("00-A2")], [canonical("CP-a", "00-A", ["00-A2"])])

    def test_phase1_wires_profiles_and_dataset_is_not_identity_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "players.csv"
            write_rows(raw, [row("00-A")])
            dataset = players_dataset(raw)
            outputs, audit, _ = build_phase1_outputs(root, {dataset.id: dataset}, [canonical("CP-a", "00-A")], 2026)
            self.assertEqual(1, audit["playerProfiles"]["recordCount"])
            self.assertIn("nflverse.players", audit["activeDatasetIDs"])
            # the projection only references identities that already exist; it never adds one
            self.assertEqual({"CP-a"}, {r["CanonicalPlayerID"] for _, p in outputs for r in p["Records"]})


if __name__ == "__main__":
    unittest.main()
