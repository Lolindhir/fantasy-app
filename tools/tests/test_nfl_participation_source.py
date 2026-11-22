import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import nfl_participation_source as part

HEADER = "nflverse_game_id,play_id,offense_players,defense_players\n"
OWNERS = {"00-0000001": {"C1"}, "00-0000002": {"C2"}, "00-0000003": {"C3", "C4"}}


def build(rows, schedule=("G1",), owners=OWNERS):
    return part.build_projection(HEADER + "".join(rows), 2024, schedule, owners)


class ParticipationProjectionTests(unittest.TestCase):
    def test_union_of_offense_and_defense_counts_distinct_plays(self):
        result = build([
            "G1,1,00-0000001,00-0000002\n",
            "G1,2,00-0000001;00-0000001,\n",
            "G1,1,00-0000001,00-0000002\n",  # duplicate game/play row
        ])
        self.assertEqual([{"GameID": "G1", "Players": {"C1": 2, "C2": 1}}], result["Games"])
        self.assertEqual(1, result["Audit"]["DuplicateGamePlayRows"])

    def test_unresolved_and_ambiguous_ids_are_excluded_and_counted(self):
        result = build(["G1,1,00-0000001;00-0000003;00-0000009,\n"])
        self.assertEqual({"C1": 1}, result["Games"][0]["Players"])
        self.assertEqual(1, result["Audit"]["AmbiguousGsisIds"])
        self.assertEqual(1, result["Audit"]["UnresolvedGsisIds"])

    def test_malformed_tokens_never_become_evidence(self):
        result = build(["G1,1,12345;00-0000001,\n"])
        self.assertEqual({"C1": 1}, result["Games"][0]["Players"])
        self.assertEqual(1, result["Audit"]["MalformedGsisTokens"])

    def test_play_without_players_is_not_evidence(self):
        result = build(["G1,1,,\n", "G1,2,00-0000002,\n"])
        self.assertEqual({"C2": 1}, result["Games"][0]["Players"])
        self.assertEqual(1, result["Audit"]["RowsWithoutPlayers"])

    def test_schedule_games_without_participation_are_reported_not_invented(self):
        result = build(["G1,1,00-0000001,\n"], schedule=("G1", "G2"))
        self.assertEqual(["G1"], [g["GameID"] for g in result["Games"]])
        self.assertEqual(1, result["Audit"]["ScheduleGamesWithoutParticipation"])

    def test_fail_closed_on_structure(self):
        with self.assertRaises(ValueError):
            build(["G9,1,00-0000001,\n"])  # game not in schedule
        with self.assertRaises(ValueError):
            part.build_projection("a,b\n1,2\n", 2024, ["G1"], OWNERS)  # columns
        with self.assertRaises(ValueError):
            build([])  # empty

    def test_attribution_follows_provider_change(self):
        self.assertEqual("NFL NextGenStats via nflverse", part.attribution(2022))
        self.assertEqual("FTN Data via nflverse", part.attribution(2023))

    def test_asset_without_official_digest_is_trusted_by_identity_only(self):
        url = "https://github.com/nflverse/nflverse-data/releases/download/pbp_participation/pbp_participation_2024.csv"
        asset = {"size": 5, "browser_download_url": url, "state": "uploaded"}
        self.assertEqual((url, ""), part._trusted(asset, 2024))
        with self.assertRaises(ValueError):
            part._trusted({**asset, "browser_download_url": "https://x/y"}, 2024)

    def test_gsis_owners_include_aliases(self):
        owners = part.gsis_owners({"Players": [
            {"CanonicalPlayerID": "C1", "IDs": {"GSIS": "00-0000001"}, "IDAliases": {"GSIS": ["00-0000008"]}}]})
        self.assertEqual({"C1"}, owners["00-0000008"])


if __name__ == "__main__":
    unittest.main()
