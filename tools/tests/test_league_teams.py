"""League-teams product: name and abbreviation rules, manager/team separation, season snapshots and parity with League.json (Issue #774)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import league_teams as lt  # noqa: E402
import derived_data  # noqa: E402

REPO = TOOLS.parent
PRODUCT = REPO / "data-derived" / "league-teams" / "nfl-reise.json"
LEAGUE_JSON = REPO / "public" / "data" / "League.json"


def member(member_id, user_id, display, team_name=None, avatar="av", team_avatar=None):
    metadata = {}
    if team_name is not None:
        metadata["team_name"] = team_name
    if team_avatar is not None:
        metadata["avatar"] = team_avatar
    return {"CanonicalLeagueMemberID": member_id, "DisplayName": display, "Avatar": avatar, "Metadata": metadata,
            "ProviderMappings": [{"Provider": "Sleeper", "ProviderUserID": user_id}]}


def roster(roster_id, member_id, user_id, provider_roster_id):
    return {"CanonicalLeagueRosterID": roster_id, "CanonicalLeagueMemberID": member_id, "ProviderOwnerUserID": user_id,
            "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": str(provider_roster_id)}]}


class RuleTests(unittest.TestCase):
    def test_abbreviation_rule(self):
        for name, team_id, expected in (
            ("Mighty Giants", 1, "MiG"), ("Ruhr Valley Packers", 2, "RVP"), ("Just Bill", 3, "JuB"), ("Team DennisLACards", 5, "DLC"),
            ("Team TimpaBay", 6, "TiB"), ("Cowboys", 7, "Cow"), (None, 4, "T04"), ("  ", "x", "TBD"), ("The Team", 9, "T09"),
        ):
            with self.subTest(name=name):
                self.assertEqual(expected, lt.team_abbreviation(name, team_id))

    def test_name_rule_and_source(self):
        self.assertEqual(("Mighty Giants", "provider"), lt.team_name(" Mighty Giants ", "Robert"))
        self.assertEqual(("Team Robert", "owner-fallback"), lt.team_name("  ", " Robert "))
        self.assertEqual(("Team Robert", "owner-fallback"), lt.team_name(None, "Robert"))
        self.assertEqual((None, None), lt.team_name(None, " "))

    def test_avatar_url_only_with_an_id(self):
        self.assertEqual("https://sleepercdn.com/avatars/abc", lt.sleeper_avatar_url("abc"))
        self.assertIsNone(lt.sleeper_avatar_url(None))
        self.assertIsNone(lt.sleeper_avatar_url(" "))


class SeasonTeamsTests(unittest.TestCase):
    def test_manager_and_team_fields_are_separate_and_ordered_by_roster_id(self):
        members = [member("m1", "u1", "Ann", "Alpha Squad", "a1", "https://x/logo1.jpg"), member("m2", "u2", "Bob", None, None)]
        rosters = [roster("r2", "m2", "u2", 2), roster("r1", "m1", "u1", 1)]
        teams = lt.season_teams(members, rosters)
        self.assertEqual([1, 2], [t["TeamID"] for t in teams])
        first, second = teams
        self.assertEqual({"Owner": "Ann", "OwnerID": "u1", "OwnerAvatar": "https://sleepercdn.com/avatars/a1"},
                         {k: first[k] for k in ("Owner", "OwnerID", "OwnerAvatar")})
        self.assertEqual(("Alpha Squad", "provider", "AlS", "https://x/logo1.jpg"),
                         (first["TeamName"], first["TeamNameSource"], first["TeamAbbr"], first["TeamAvatar"]))
        # Without a team name or logo the team fields are fallback/unknown, never the manager's avatar.
        self.assertEqual(("Team Bob", "owner-fallback", "Bob", None, None),
                         (second["TeamName"], second["TeamNameSource"], second["TeamAbbr"], second["TeamAvatar"], second["OwnerAvatar"]))
        self.assertNotIn("Avatar", first)

    def test_fail_closed_on_inconsistent_evidence(self):
        members = [member("m1", "u1", "Ann")]
        for label, rosters, mem in (
            ("unknown member", [roster("r1", "mX", "u1", 1)], members),
            ("owner mismatch", [roster("r1", "m1", "uX", 1)], members),
            ("duplicate roster id", [roster("r1", "m1", "u1", 1), roster("r2", "m1", "u1", 1)], members),
            ("missing display name", [roster("r1", "m1", "u1", 1)], [member("m1", "u1", " ")]),
        ):
            with self.subTest(label), self.assertRaises(lt.LeagueTeamsError):
                lt.season_teams(mem, rosters)


class ProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = lt.resolve(REPO, "nfl-reise")

    def test_every_manifest_season_with_unique_team_ids(self):
        self.assertEqual("league-teams", self.document["Product"])
        self.assertEqual(self.document["CurrentSeason"], self.document["Seasons"][-1]["Season"])
        for season in self.document["Seasons"]:
            ids = [t["TeamID"] for t in season["Teams"]]
            self.assertEqual(len(ids), len(set(ids)), season["Season"])

    def test_season_snapshots_are_not_overwritten_by_later_identity(self):
        by_season = {s["Season"]: {t["TeamID"]: t for t in s["Teams"]} for s in self.document["Seasons"]}
        current = self.document["CurrentSeason"]
        # A team that kept no logo in an older season keeps no logo there, whatever the current logo is.
        for season, teams in by_season.items():
            if season == current:
                continue
            source = json.loads((REPO / "data-source/leagues/nfl-reise/seasons" / season / "members.json").read_text(encoding="utf-8"))
            logos = {str((m.get("Metadata") or {}).get("avatar") or "").strip() or None for m in source}
            self.assertEqual(logos, {t["TeamAvatar"] for t in teams.values()}, season)

    def test_materializer_is_a_semantic_noop_on_a_second_run(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            first = derived_data.materialize_league_teams(REPO, out, "nfl-reise", None, False)
            second = derived_data.materialize_league_teams(REPO, out, "nfl-reise", None, False)
            self.assertEqual(1, first["Seasons"][0]["Written"])
            self.assertEqual(0, second["Seasons"][0]["Written"])
            with self.assertRaises(ValueError):
                derived_data.materialize_league_teams(REPO, out, "nfl-reise", [2026], False)

    def test_persisted_product_matches_the_canonical_sources_when_present(self):
        if not PRODUCT.is_file():
            self.skipTest("league-teams product not materialized yet")
        self.assertEqual(derived_data.serialize(self.document), PRODUCT.read_text(encoding="utf-8"))

    def test_current_season_equals_league_json_identity(self):
        """Parity proof (Issue #774 step 1): the current season's name, abbreviation, logos and manager equal what League.json publishes."""
        league = json.loads(LEAGUE_JSON.read_text(encoding="utf-8-sig"))
        current = {t["TeamID"]: t for t in self.document["Seasons"][-1]["Teams"]}
        published = {t["TeamID"]: t for t in league["Teams"]}
        self.assertEqual(set(published), set(current))
        for team_id, team in published.items():
            with self.subTest(team=team_id):
                product = current[team_id]
                self.assertEqual(team["Team"], product["TeamName"])
                self.assertEqual(team["TeamAbbr"], product["TeamAbbr"])
                self.assertEqual(team["TeamAvatar"], product["TeamAvatar"])
                self.assertEqual(team["Owner"], product["Owner"])
                self.assertEqual(team["OwnerID"], product["OwnerID"])
                self.assertEqual(team["OwnerAvatar"], product["OwnerAvatar"])


if __name__ == "__main__":
    unittest.main()
