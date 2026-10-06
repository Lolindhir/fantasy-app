import json
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import current_source_season
from nfl_source_data_lib.materialize import _observation_season


def write_manifest(root: Path, league: str, current: int, seasons: list[int]) -> None:
    path = root / "source-data/leagues" / league / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "CanonicalLeagueID": league,
                "CurrentCanonicalLeagueSeasonID": f"{league}-{current}",
                "Seasons": [{"CanonicalLeagueSeasonID": f"{league}-{s}", "Season": s} for s in seasons],
            }
        ),
        encoding="utf-8",
    )


class NflSourceCurrentSeasonTests(unittest.TestCase):
    def test_season_comes_from_canonical_league_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_manifest(root, "league-a", 2031, [2029, 2030, 2031])
            self.assertEqual(2031, current_source_season(root))
            self.assertEqual(2031, _observation_season(root))

    def test_app_read_models_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_manifest(root, "league-a", 2031, [2031])
            (root / "public/data").mkdir(parents=True)
            (root / "public/data/League.json").write_text(json.dumps({"Season": 1999}), encoding="utf-8")
            (root / "public/data/Metadata.json").write_text(json.dumps({"LeagueYear": 1998}), encoding="utf-8")
            self.assertEqual(2031, current_source_season(root))

    def test_latest_current_season_wins_across_leagues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_manifest(root, "league-a", 2030, [2030])
            write_manifest(root, "league-b", 2032, [2031, 2032])
            self.assertEqual(2032, current_source_season(root))

    def test_unresolvable_current_season_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_manifest(root, "league-a", 2031, [2030])
            with self.assertRaises(ValueError):
                current_source_season(root)

    def test_without_league_facts_uses_current_utc_year(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(datetime.now(timezone.utc).year, current_source_season(Path(tmp)))

    def test_real_repository_current_season_matches_canonical_manifest(self) -> None:
        root = TOOLS.parent
        manifest = json.loads((root / "source-data/leagues/nfl-reise/manifest.json").read_text(encoding="utf-8"))
        current = manifest["CurrentCanonicalLeagueSeasonID"]
        expected = next(s["Season"] for s in manifest["Seasons"] if s["CanonicalLeagueSeasonID"] == current)
        self.assertEqual(expected, current_source_season(root))

    def test_source_layer_does_not_read_app_league_or_metadata(self) -> None:
        pattern = re.compile(r"public/data/(League|Metadata)\.json")
        offenders = [
            str(path.relative_to(TOOLS.parent))
            for path in sorted((TOOLS / "nfl_source_data_lib").rglob("*.py"))
            if pattern.search(path.read_text(encoding="utf-8"))
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
