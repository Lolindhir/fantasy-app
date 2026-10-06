import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset, load_registry
from nfl_source_data_lib.phase1 import build_phase1_outputs
from nfl_source_data_lib.teams import (
    LEGACY_APP_TEAM_IDS,
    NflTeamRegistry,
    NflTeamRegistryError,
    build_teams_payload,
)

FIELDS = [
    "team_abbr", "team_name", "team_id", "team_nick", "team_conf", "team_division", "team_logo_espn",
]


def write_teams_csv(path: Path, mutate=None) -> None:
    rows = list(csv.DictReader((REPO_ROOT / "source-data/providers/nflverse/teams/raw-latest.csv").open(encoding="utf-8")))
    if mutate:
        rows = mutate(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def teams_dataset(raw: Path) -> Dataset:
    return Dataset(
        "nflverse.teams", "nflverse", "test", "https://example.invalid/teams.csv", raw, Path("metadata.json"),
        tuple(FIELDS), 32, "team-registry", "periodic", "latest-with-git-history", "test", "test",
    )


class TeamRegistryTests(unittest.TestCase):
    def build(self, mutate=None):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "teams.csv"
            write_teams_csv(raw, mutate)
            return build_teams_payload(teams_dataset(raw))

    def test_repository_registry_activates_teams_dataset(self):
        active = {dataset.id: dataset for dataset in load_registry(REPO_ROOT)}
        self.assertIn("nflverse.teams", active)
        self.assertTrue(active["nflverse.teams"].materialize)

    def test_builds_32_teams_with_aliases_and_legacy_ids(self):
        payload, audit = self.build()
        self.assertEqual(32, audit["teamCount"])
        teams = {team["TeamAbbr"]: team for team in payload["Teams"]}
        self.assertEqual("Los Angeles", teams["LA"]["City"])
        self.assertEqual("Rams", teams["LA"]["Name"])
        self.assertEqual("West", teams["LA"]["Division"])
        self.assertEqual("National Football Conference", teams["LA"]["Conference"])
        self.assertEqual("19", teams["LA"]["LegacyAppTeamID"])
        self.assertEqual({"LAR", "STL"}, {alias["Alias"] for alias in teams["LA"]["Aliases"]})
        self.assertEqual({"WSH"}, {alias["Alias"] for alias in teams["WAS"]["Aliases"]})
        self.assertEqual(set(LEGACY_APP_TEAM_IDS), set(teams))
        self.assertTrue(all(team["Logo"].startswith("https://") for team in teams.values()))

    def test_build_is_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_fails_closed_on_missing_team(self):
        with self.assertRaises(ValueError):
            self.build(lambda rows: [row for row in rows if row["team_abbr"] != "KC"])

    def test_fails_closed_on_alias_with_foreign_franchise(self):
        def mutate(rows):
            for row in rows:
                if row["team_abbr"] == "OAK":
                    row["team_id"] = "9999"
            return rows

        with self.assertRaises(ValueError):
            self.build(mutate)

    def test_fails_closed_on_duplicate_franchise(self):
        def mutate(rows):
            for row in rows:
                if row["team_abbr"] == "KC":
                    row["team_id"] = next(r["team_id"] for r in rows if r["team_abbr"] == "BUF")
            return rows

        with self.assertRaises(ValueError):
            self.build(mutate)

    def test_phase1_writes_registry_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw/teams.csv"
            write_teams_csv(raw)
            dataset = teams_dataset(raw)
            outputs, audit, _ = build_phase1_outputs(root, {dataset.id: dataset}, [], 2026)
            self.assertEqual([root / "source-data/nfl/teams.json"], [path for path, _ in outputs])
            self.assertEqual(32, audit["teams"]["teamCount"])
            self.assertIn("nflverse.teams", audit["activeDatasetIDs"])


class TeamResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload, _ = build_teams_payload(teams_dataset(REPO_ROOT / "source-data/providers/nflverse/teams/raw-latest.csv"))
        cls.registry = NflTeamRegistry(payload)

    def test_resolves_abbreviations_spellings_and_legacy_keys(self):
        r = self.registry
        self.assertEqual("LA", r.resolve("LA"))
        self.assertEqual("LA", r.resolve("lar"))
        self.assertEqual("WAS", r.resolve("WSH"))
        self.assertEqual("LA", r.resolve("19"))
        self.assertEqual("WAS", r.resolve("32"))

    def test_historical_aliases_require_valid_season(self):
        r = self.registry
        self.assertEqual("LV", r.resolve("OAK", 2019))
        self.assertEqual("LAC", r.resolve("SD", 2016))
        with self.assertRaises(NflTeamRegistryError):
            r.resolve("OAK", 2020)
        with self.assertRaises(NflTeamRegistryError):
            r.resolve("STL")

    def test_unknown_or_empty_keys_fail_closed(self):
        for value in (None, "", "  ", "XXX", "33", "0"):
            with self.assertRaises(NflTeamRegistryError):
                self.registry.resolve(value)


class PersistedRegistryTests(unittest.TestCase):
    """Run against the committed canonical output; skipped until it is materialized."""

    path = REPO_ROOT / "source-data/nfl/teams.json"

    def test_registry_matches_canonical_schedule_abbreviations(self):
        self.assertTrue(self.path.exists(), "source-data/nfl/teams.json must be materialized")
        registry = NflTeamRegistry.load(REPO_ROOT)
        schedule_files = sorted((REPO_ROOT / "source-data/nfl/schedules").glob("*.json"))
        latest = json.loads(schedule_files[-1].read_text(encoding="utf-8"))
        schedule_teams = {game[side] for game in latest["Games"] for side in ("HomeTeam", "AwayTeam")}
        self.assertEqual(set(registry.abbreviations()), schedule_teams)

    def test_published_app_teams_resolve_through_legacy_ids(self):
        registry = NflTeamRegistry.load(REPO_ROOT)
        teams = json.loads((REPO_ROOT / "public/data/Teams.json").read_text(encoding="utf-8-sig"))
        for team in teams:
            self.assertIn(registry.resolve(team["Abv"]), registry.teams)
            self.assertEqual(registry.resolve(team["Abv"]), registry.resolve(team["ID"]))


if __name__ == "__main__":
    unittest.main()
