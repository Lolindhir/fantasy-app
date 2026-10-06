from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import jsonschema

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "build_kicker_weekly_research_plan",
    SCRIPTS_DIR / "build_kicker_weekly_research_plan.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KickerWeeklyResearchPlanTests(unittest.TestCase):
    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = Path(__file__).resolve().parents[4]
        source = json.loads((root / "fantasy-management/generated/operations/kicker-streaming-inputs.json").read_text(encoding="utf-8"))
        analysis_config = json.loads((root / "fantasy-management/_ai/kicker-streaming-analysis-config.json").read_text(encoding="utf-8"))
        research_config = json.loads((root / "fantasy-management/_ai/kicker-weekly-research-config.json").read_text(encoding="utf-8"))
        registry = MODULE.NflTeamRegistry.load(root)
        schedule = MODULE.load_canonical_schedule(root, int(source["league"]["season"]), registry)
        schema = json.loads((root / "fantasy-management/_ai/schemas/kicker-weekly-research-plan.schema.json").read_text(encoding="utf-8"))

        payload = MODULE.build_research_plan(source, analysis_config, research_config, schedule, None, registry)
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)

        league = source["league"]
        self.assertEqual(payload["dataset_id"], "kicker-weekly-research-plan")
        self.assertEqual(payload["season"], str(league["season"]))
        self.assertEqual(payload["week"], int(league["current_week"]))

        candidates = payload["candidates"]
        candidate_ids = [candidate["player_id"] for candidate in candidates]
        held_candidates = [candidate for candidate in candidates if candidate["availability"] == "held"]
        free_agent_candidates = [candidate for candidate in candidates if candidate["availability"] == "free_agent"]
        source_held_ids = {
            str(candidate["player_id"])
            for candidate in source["candidates"]
            if candidate.get("availability") == "held"
        }
        source_free_agent_ids = {
            str(candidate["player_id"])
            for candidate in source["candidates"]
            if candidate.get("availability") == "free_agent"
        }

        self.assertEqual(len(candidate_ids), len(set(candidate_ids)))
        self.assertEqual(payload["population"]["candidate_count"], len(candidates))
        self.assertEqual(payload["population"]["held_count"], len(held_candidates))
        self.assertEqual(payload["population"]["shortlisted_free_agent_count"], len(free_agent_candidates))
        self.assertEqual(len(candidates), len(held_candidates) + len(free_agent_candidates))
        self.assertEqual({candidate["player_id"] for candidate in held_candidates}, source_held_ids)
        self.assertTrue({candidate["player_id"] for candidate in free_agent_candidates}.issubset(source_free_agent_ids))
        self.assertLessEqual(
            len(free_agent_candidates),
            int(analysis_config["baseline"]["shortlist_free_agent_count"]),
        )

        season_type = str(research_config["schedule"].get("season_type", "Regular Season"))
        known_schedule_teams = MODULE.schedule_team_universe(schedule, payload["season"], season_type)
        target_games = [
            row
            for row in schedule
            if isinstance(row, dict)
            and str(row.get("season")) == payload["season"]
            and row.get("seasonType") == season_type
            and MODULE.parse_week_label(row.get("gameWeek")) == payload["week"]
        ]
        self.assertTrue(target_games)

        for candidate in candidates:
            team = registry.resolve(candidate["nfl_team"], int(payload["season"]))
            self.assertIn(team, known_schedule_teams)
            matches = [game for game in target_games if team in {game.get("home"), game.get("away")}]
            self.assertLessEqual(len(matches), 1, f"{team} has multiple games in current repository week")

            schedule_view = candidate["schedule"]
            venue_research = candidate["venue_research"]
            if not matches:
                self.assertEqual(schedule_view["status"], "bye")
                self.assertEqual(schedule_view["team_side"], "bye")
                self.assertIsNone(schedule_view["game_id"])
                self.assertIsNone(schedule_view["opponent"])
                self.assertIsNone(venue_research["expected_home_team"])
                continue

            game = matches[0]
            expected_side = "home" if game["home"] == team else "away"
            expected_opponent = game["away"] if expected_side == "home" else game["home"]
            neutral_site = MODULE.parse_bool(game.get("neutralSite", False), f"neutralSite for {game['gameID']}")
            expected_home_team = None if neutral_site else game["home"]

            self.assertEqual(schedule_view["status"], "scheduled")
            self.assertEqual(schedule_view["game_id"], game["gameID"])
            self.assertEqual(schedule_view["home"], game["home"])
            self.assertEqual(schedule_view["away"], game["away"])
            self.assertEqual(schedule_view["team_side"], expected_side)
            self.assertEqual(schedule_view["opponent"], expected_opponent)
            self.assertEqual(schedule_view["neutral_site"], neutral_site)
            self.assertEqual(venue_research["expected_home_team"], expected_home_team)
            self.assertEqual(venue_research["neutral_site_override_required"], neutral_site)

    def test_canonical_schedule_adapter_uses_registry_and_eastern_kickoff(self) -> None:
        import tempfile

        root = Path(__file__).resolve().parents[4]
        registry = MODULE.NflTeamRegistry.load(root)
        abbrs = list(registry.abbreviations())
        away, home = abbrs[0], abbrs[1]
        provider_alias = next(
            (key for key, (abbr, last) in registry._alias.items() if abbr == home and last is None), None
        )
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "source-data/nfl/schedules").mkdir(parents=True)
            (base / "source-data/nfl/game-finality").mkdir(parents=True)
            games = [
                {"GameID": "g1", "GameType": "REG", "Week": 3, "GameDay": "2030-09-22", "GameTime": "13:00",
                 "AwayTeam": away, "HomeTeam": provider_alias or home, "Location": "Neutral", "Overtime": "1",
                 "ProviderGameIDs": {"ESPN": "42"}},
                {"GameID": "g2", "GameType": "REG", "Week": 3, "GameDay": "2030-09-22", "GameTime": None,
                 "AwayTeam": abbrs[2], "HomeTeam": abbrs[3], "Location": "Home", "ProviderGameIDs": {"ESPN": "43"}},
            ]
            (base / "source-data/nfl/schedules/2030.json").write_text(
                json.dumps({"Season": 2030, "SourceDataset": "nflverse.schedules", "Games": games}), encoding="utf-8")
            (base / "source-data/nfl/game-finality/2030.json").write_text(
                json.dumps({"Season": 2030, "SourceDataset": "nflverse.game-finality",
                            "Games": [{"GameID": "g1", "Final": True}, {"GameID": "g2", "Final": False}]}),
                encoding="utf-8")
            rows = MODULE.load_canonical_schedule(base, 2030, registry)
            first, second = (rows[0], rows[1])
            self.assertEqual(first["home"], home)
            self.assertEqual(first["neutralSite"], "True")
            self.assertEqual(first["gameStatus"], "Final/OT")
            # 13:00 Eastern daylight time on 2030-09-22 is 17:00 UTC.
            from datetime import datetime, timezone
            self.assertEqual(float(first["gameTime_epoch"]), datetime(2030, 9, 22, 17, tzinfo=timezone.utc).timestamp())
            self.assertEqual(second["gameTime_epoch"], "")
            self.assertEqual(second["gameStatus"], "Scheduled")
            self.assertEqual(MODULE.resolve_team_schedule(provider_alias or home, [], {home}, registry, 2030)["status"], "bye")

            (base / "source-data/nfl/game-finality/2030.json").write_text(
                json.dumps({"Season": 2030, "SourceDataset": "nflverse.game-finality", "Games": []}), encoding="utf-8")
            with self.assertRaises(MODULE.KickerWeeklyResearchPlanError):
                MODULE.load_canonical_schedule(base, 2030, registry)

    def test_schedule_resolution_supports_bye(self) -> None:
        games = [{"game_id": "g1", "home": "LAR", "away": "SF", "neutral_site": True}]
        bye = MODULE.resolve_team_schedule("DET", games, {"DET", "LAR", "SF"})
        self.assertEqual(bye["status"], "bye")
        self.assertEqual(bye["team_side"], "bye")
        self.assertIsNone(bye["game_id"])

    def test_multiple_games_fail_closed(self) -> None:
        games = [
            {"game_id": "g1", "home": "DET", "away": "NO"},
            {"game_id": "g2", "home": "DET", "away": "GB"},
        ]
        with self.assertRaises(MODULE.KickerWeeklyResearchPlanError):
            MODULE.resolve_team_schedule("DET", games, {"DET", "NO", "GB"})

    def test_unknown_team_is_not_treated_as_bye(self) -> None:
        games = [{"game_id": "g1", "home": "LAR", "away": "SF", "neutral_site": False}]
        with self.assertRaisesRegex(MODULE.KickerWeeklyResearchPlanError, "not schedule-resolvable"):
            MODULE.resolve_team_schedule("XXX", games, {"LAR", "SF", "DET"})


if __name__ == "__main__":
    unittest.main()
