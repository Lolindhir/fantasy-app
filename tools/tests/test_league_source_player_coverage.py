from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.coverage import build_season_player_reference_coverage  # noqa: E402
from nfl_source_data_lib.mapping_history import build_historical_app_mapping_claims  # noqa: E402
from source_data_readiness import build_league_readiness  # noqa: E402


def player_ref(sleeper_id: str, canonical: str | None) -> dict:
    return {
        "CanonicalPlayerID": canonical,
        "ProviderMappings": [
            {"Provider": "Sleeper", "ProviderPlayerID": sleeper_id}
        ],
    }


class LeagueSourcePlayerCoverageTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, payload: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _init_git(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)

    def _commit_players(self, root: Path, when: str, rows: list[dict]) -> str:
        self._write(root, "public/data/Players.json", rows)
        subprocess.run(["git", "add", "public/data/Players.json"], cwd=root, check=True)
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        subprocess.run(
            ["git", "commit", "-m", "Players Update"],
            cwd=root,
            check=True,
            capture_output=True,
            env=env,
        )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _configure_league(self, root: Path, roster_payload: object) -> Path:
        self._write(
            root,
            "source-data/leagues/_bootstrap/nfl-reise.json",
            {
                "CanonicalLeagueID": "nfl-reise",
                "Provider": "Sleeper",
                "CurrentProviderLeagueID": "123",
            },
        )
        self._write(
            root,
            "source-data/leagues/nfl-reise/manifest.json",
            {
                "Seasons": [
                    {
                        "Season": 2025,
                        "CanonicalLeagueSeasonID": "nfl-reise-2025",
                        "ProviderMappings": [
                            {"Provider": "Sleeper", "ProviderLeagueID": "123"}
                        ],
                    }
                ]
            },
        )
        season_root = root / "source-data/leagues/nfl-reise/seasons/2025"
        self._write(
            season_root,
            "league.json",
            {
                "WeekStructure": {"ExpectedFinalWeek": 17},
                "ScoringSettings": {"pass_td": 4},
            },
        )
        self._write(season_root, "members.json", [])
        self._write(season_root, "rosters.json", roster_payload)
        self._write(season_root, "drafts.json", [])
        self._write(season_root, "winners-bracket.json", [])
        self._write(season_root, "losers-bracket.json", [])
        return season_root

    def test_counts_unresolved_player_references_across_all_league_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            season_root = Path(tmp) / "source-data/leagues/nfl-reise/seasons/2025"
            self._write(
                season_root,
                "rosters.json",
                [{"Players": [player_ref("S1", None), player_ref("S2", "NFLP-2")]}],
            )
            self._write(
                season_root,
                "matchups/week-1.json",
                [{"Players": [player_ref("S1", None)]}],
            )
            self._write(
                season_root,
                "transactions/week-1.json",
                [{"Adds": [{"Player": player_ref("S3", None)}]}],
            )
            self._write(
                season_root,
                "drafts.json",
                [{"Picks": [{"Player": player_ref("S4", "NFLP-4")}]}],
            )

            coverage = build_season_player_reference_coverage(season_root)

            self.assertEqual(5, coverage["ReferenceCount"])
            self.assertEqual(2, coverage["ResolvedReferenceCount"])
            self.assertEqual(3, coverage["UnresolvedReferenceCount"])
            self.assertEqual(4, coverage["UniqueSleeperPlayerIDCount"])
            self.assertEqual(2, coverage["UnresolvedUniqueSleeperPlayerIDCount"])
            self.assertEqual(["S1", "S3"], coverage["UnresolvedSleeperPlayerIDs"])
            self.assertFalse(coverage["Ready"])
            self.assertEqual(2, coverage["ByDomain"]["Rosters"]["ReferenceCount"])
            self.assertEqual(1, coverage["ByDomain"]["Transactions"]["UnresolvedReferenceCount"])

    def test_empty_or_fully_resolved_season_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            season_root = Path(tmp) / "season"
            self._write(
                season_root,
                "rosters.json",
                [{"Players": [player_ref("S1", "NFLP-1")]}],
            )

            coverage = build_season_player_reference_coverage(season_root)

            self.assertTrue(coverage["Ready"])
            self.assertEqual(0, coverage["UnresolvedReferenceCount"])
            self.assertEqual([], coverage["UnresolvedSleeperPlayerIDs"])

    def test_readiness_fails_closed_for_unresolved_player_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._configure_league(
                root,
                [{"Players": [player_ref("S1", None), player_ref("S2", "NFLP-2")]}],
            )

            readiness = build_league_readiness(root)

            self.assertFalse(readiness["Ready"])
            self.assertEqual(1, len(readiness["HardFailures"]))
            self.assertIn("1 unresolved canonical player references", readiness["HardFailures"][0])
            coverage = readiness["Leagues"][0]["Seasons"][0]["PlayerReferenceCoverage"]
            self.assertEqual(["S1"], coverage["UnresolvedSleeperPlayerIDs"])

    def test_historical_backfill_uses_contemporaneous_two_provider_git_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_git(root)
            self._write(root, "public/data/past_seasons/Players_2025.json", [])
            commit = self._commit_players(
                root,
                "2025-10-15T12:00:00Z",
                [{"ID": "S1", "TankID": "T1", "Name": "Player A", "Position": "WR"}],
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-a",
                    "IDs": {"Sleeper": "S1", "Tank01": "T1"},
                    "IDAliases": {},
                }
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)

            self.assertEqual([], conflicts)
            self.assertEqual(1, stats["gitResolvedPlayerCount"])
            by_provider = {item["Provider"]: item for item in claims}
            self.assertEqual("NFLP-a", by_provider["Sleeper"]["CanonicalPlayerID"])
            self.assertEqual("NFLP-a", by_provider["Tank01"]["CanonicalPlayerID"])
            self.assertIn(
                f"app.Players.git.2025@{commit[:12]}",
                by_provider["Sleeper"]["Sources"],
            )


if __name__ == "__main__":
    unittest.main()
