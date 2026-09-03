from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.materialize import (  # noqa: E402
    PlayerMappingResolver,
    persist_canonical_outputs,
    plan_canonical_materialization,
)
from league_source_data_lib.registry import load_league_registry  # noqa: E402


class LeagueSourceMaterializeTests(unittest.TestCase):
    def _repo(self) -> tuple[tempfile.TemporaryDirectory, Path, str, str]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        canonical_league_id = "cl-220306ac3f9b480fa865e124098d8f56"
        provider_league_id = "1257421353431080960"

        registry_source = Path(__file__).resolve().parents[2] / "source-data" / "league-registry.json"
        registry_target = root / "source-data" / "league-registry.json"
        registry_target.parent.mkdir(parents=True, exist_ok=True)
        registry_target.write_text(registry_source.read_text(encoding="utf-8"), encoding="utf-8")

        schedule_path = root / "source-data" / "nfl" / "schedules" / "2025.json"
        schedule_path.parent.mkdir(parents=True, exist_ok=True)
        schedule_path.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "Season": 2025,
                    "Games": [
                        {"GameID": f"2025_{week:02d}_A_B", "GameType": "REG", "Week": week}
                        for week in range(1, 19)
                    ],
                }
            ),
            encoding="utf-8",
        )

        mappings_path = root / "source-data" / "nfl" / "identities" / "provider-mappings.json"
        mappings_path.parent.mkdir(parents=True, exist_ok=True)
        mappings_path.write_text(
            json.dumps(
                {
                    "Mappings": [
                        {
                            "Provider": "Sleeper",
                            "ExternalID": "p1",
                            "CanonicalPlayerID": "cp-one",
                            "FirstObservedSeason": 2025,
                            "LastObservedSeason": 2025,
                            "Sources": ["fixture"],
                        }
                    ],
                    "Conflicts": [],
                }
            ),
            encoding="utf-8",
        )

        manifest_path = root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "CanonicalLeagueID": canonical_league_id,
                    "Provider": "Sleeper",
                    "CurrentCanonicalLeagueSeasonID": "cls-fixture",
                    "CurrentProviderLeagueID": provider_league_id,
                    "Seasons": [
                        {
                            "CanonicalLeagueSeasonID": "cls-fixture",
                            "Season": 2025,
                            "PreviousCanonicalLeagueSeasonID": None,
                            "ProviderMappings": [
                                {
                                    "Provider": "Sleeper",
                                    "ProviderLeagueID": provider_league_id,
                                    "PreviousProviderLeagueID": None,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        raw = root / "source-data" / "providers" / "sleeper" / "leagues" / provider_league_id
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "league.json").write_text(
            json.dumps(
                {
                    "league_id": provider_league_id,
                    "season": "2025",
                    "status": "complete",
                    "name": "Fixture League",
                    "settings": {
                        "start_week": 1,
                        "playoff_week_start": 14,
                        "playoff_teams": 4,
                        "playoff_round_type": 2,
                        "last_scored_leg": 17,
                    },
                    "scoring_settings": {},
                    "roster_positions": ["QB"],
                }
            ),
            encoding="utf-8",
        )
        (raw / "members.json").write_text(
            json.dumps([{"user_id": "u1", "display_name": "Owner"}]), encoding="utf-8"
        )
        (raw / "rosters.json").write_text(
            json.dumps(
                [
                    {
                        "roster_id": 1,
                        "owner_id": "u1",
                        "players": ["p1", "unmapped"],
                        "starters": ["p1"],
                        "reserve": [],
                        "taxi": [],
                    }
                ]
            ),
            encoding="utf-8",
        )
        (raw / "winners-bracket.json").write_text(
            json.dumps([{"r": 1, "m": 1, "t1": 1}, {"r": 2, "m": 2, "t1": 1}]),
            encoding="utf-8",
        )
        (raw / "losers-bracket.json").write_text("[]", encoding="utf-8")
        (raw / "drafts").mkdir(parents=True, exist_ok=True)
        (raw / "drafts" / "index.json").write_text("[]", encoding="utf-8")
        (raw / "matchups").mkdir(parents=True, exist_ok=True)
        (raw / "transactions").mkdir(parents=True, exist_ok=True)
        for week in range(1, 19):
            matchup_payload = (
                [{"matchup_id": 1, "roster_id": 1, "players": ["p1"], "starters": ["p1"], "points": 10.0}]
                if week <= 17
                else []
            )
            (raw / "matchups" / f"week-{week}.json").write_text(
                json.dumps(matchup_payload), encoding="utf-8"
            )
            (raw / "transactions" / f"week-{week}.json").write_text("[]", encoding="utf-8")

        return temporary, root, canonical_league_id, provider_league_id

    def test_materializes_provider_independent_facts_and_week_structure(self) -> None:
        temporary, root, canonical_league_id, _ = self._repo()
        try:
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)
            outputs = plan_canonical_materialization(root, canonical_league_id, registry, resolver)
            result = persist_canonical_outputs(outputs)
            self.assertGreater(result["CanonicalFilesChanged"], 0)

            season_root = root / "source-data" / "leagues" / canonical_league_id / "seasons" / "2025"
            league = json.loads((season_root / "league.json").read_text(encoding="utf-8"))
            rosters = json.loads((season_root / "rosters.json").read_text(encoding="utf-8"))
            self.assertEqual(league["WeekStructure"]["ObservedPlayoffFormat"], "two-week-rounds")
            self.assertEqual(league["WeekStructure"]["FinalLeagueWeek"], 17)
            self.assertEqual(rosters[0]["Players"][0]["CanonicalPlayerID"], "cp-one")
            self.assertIsNone(rosters[0]["Players"][1]["CanonicalPlayerID"])

            second_outputs = plan_canonical_materialization(root, canonical_league_id, registry, resolver)
            second = persist_canonical_outputs(second_outputs)
            self.assertEqual(second["CanonicalFilesChanged"], 0)
        finally:
            temporary.cleanup()

    def test_ambiguous_player_mapping_fails_closed(self) -> None:
        temporary, root, canonical_league_id, _ = self._repo()
        try:
            mapping_path = root / "source-data" / "nfl" / "identities" / "provider-mappings.json"
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            mapping["Conflicts"] = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "p1",
                    "CanonicalPlayerIDs": ["cp-one", "cp-two"],
                    "FirstObservedSeason": 2025,
                    "LastObservedSeason": 2025,
                }
            ]
            mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)
            with self.assertRaises(ValueError):
                plan_canonical_materialization(root, canonical_league_id, registry, resolver)
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
