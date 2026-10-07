"""#347 H1b: Players.json population and platform fields from canonical source data."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import players_population as pop  # noqa: E402

SEASON = 2026
LEAGUE = "test-league"
GENERATOR = ROOT / "public" / "requests" / "RequestPlayers.ps1"


def write(root: Path, relative: str, payload: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def snapshot_row(sleeper_id: str, **overrides: object) -> dict:
    row = {
        "CanonicalPlayerID": None, "SleeperPlayerID": sleeper_id, "Status": "Active", "Team": "KC", "Position": "WR",
        "FantasyPositions": ["WR"], "InjuryStatus": None, "InjuryStartDate": None, "PracticeParticipation": None,
        "DepthChartPosition": None, "DepthChartOrder": None, "FirstName": "F", "LastName": sleeper_id,
        "FullName": f"F {sleeper_id}", "YearsExp": 2, "College": None, "HighSchool": None, "Number": 11,
        "ESPNID": None, "BirthDate": "1999-01-02", "InjuryBodyPart": None, "InjuryNotes": None,
        "PracticeDescription": None,
    }
    row.update(overrides)
    return row


class PopulationFixture:
    """Synthetic repository: identities NFLP-<id> for Sleeper <id>, rosters, draft and one league roster."""

    def __init__(self, rows: list[dict], *, roster: list[str], weekly: list[str] = (), draft: list[str] = (),
                 owned: list[str] = (), current_roster: bool = True, previous_roster: list[str] | None = None,
                 identity_ids: list[str] | None = None) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        ids = identity_ids if identity_ids is not None else [r["SleeperPlayerID"] for r in rows]
        write(self.root, "source-data/nfl/platform/sleeper/players.json",
              {"SchemaVersion": 2, "SourceDataset": "sleeper.players", "Records": rows})
        (self.root / "source-data/nfl").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "source-data/nfl/teams.json", self.root / "source-data/nfl/teams.json")
        write(self.root, "source-data/nfl/identities/players.json", {"Players": [
            {"CanonicalPlayerID": f"NFLP-{i}", "IDs": {"Sleeper": i, "Tank01": f"T{i}", "ESPN": f"E{i}"}} for i in ids]})
        write(self.root, "source-data/nfl/player-profiles/nflverse.json", {
            "SourceDataset": "nflverse.players",
            "Records": [{"CanonicalPlayerID": f"NFLP-{i}", "DisplayName": f"Prof {i} Jr.", "Headshot": f"https://img/{i}.png"}
                        for i in ids if i != "nohead"]})
        write(self.root, "source-data/nfl/identities/provider-mappings.json", {"Mappings": [
            {"Provider": "Sleeper", "ExternalID": i, "CanonicalPlayerID": f"NFLP-{i}", "FirstObservedSeason": 2020,
             "LastObservedSeason": SEASON} for i in ids], "Conflicts": []})

        def records(sids: list[str]) -> dict:
            return {"Records": [{"CanonicalPlayerID": f"NFLP-{i}"} for i in sids]}

        if current_roster:
            write(self.root, f"source-data/nfl/rosters/{SEASON}.json", records(roster))
        if previous_roster is not None:
            write(self.root, f"source-data/nfl/rosters/{SEASON - 1}.json", records(previous_roster))
        if weekly:
            write(self.root, f"source-data/nfl/weekly-rosters/{SEASON}/01.json", records(list(weekly)))
        write(self.root, f"source-data/nfl/draft/{SEASON}.json", {"Picks": [{"CanonicalPlayerID": f"NFLP-{i}"} for i in draft]})
        write(self.root, f"source-data/leagues/{LEAGUE}/seasons/{SEASON}/rosters.json", [
            {"Players": [{"ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": i}]} for i in owned]}])

    def build(self) -> dict:
        return pop.build_population(self.root, LEAGUE, SEASON)

    def close(self) -> None:
        self.tmp.cleanup()


class PopulationRuleTests(unittest.TestCase):
    def build(self, rows: list[dict], **kwargs: object) -> dict:
        fixture = PopulationFixture(rows, **kwargs)
        self.addCleanup(fixture.close)
        return fixture.build()

    def test_reasons_and_exclusions(self) -> None:
        rows = [snapshot_row(i) for i in ("1", "2", "3", "4", "5")]
        rows.append(snapshot_row("6", Position="LB", FantasyPositions=["LB"]))
        rows.append(snapshot_row("7", BirthDate=None))
        rows.append(snapshot_row("8", BirthDate="garbage"))
        result = self.build(rows, roster=["1"], weekly=["2"], draft=["3"], owned=["4"], identity_ids=[r["SleeperPlayerID"] for r in rows])
        reasons = {p["SleeperID"]: p["Reasons"] for p in result["Players"]}
        self.assertEqual(reasons, {
            "1": [pop.REASON_ROSTER], "2": [pop.REASON_ROSTER], "3": [pop.REASON_DRAFT], "4": [pop.REASON_LEAGUE],
        })
        self.assertEqual(result["Counts"]["Skipped"]["no_app_position"], 1)
        self.assertEqual(result["Counts"]["Skipped"]["no_valid_birth_date"], 2)
        self.assertEqual(result["Counts"]["Skipped"]["no_reason"], 1)

    def test_league_owned_without_identity_is_kept_as_hold(self) -> None:
        rows = [snapshot_row("1"), snapshot_row("2")]
        result = self.build(rows, roster=["1"], owned=["2"], identity_ids=["1"])
        by_id = {p["SleeperID"]: p for p in result["Players"]}
        self.assertIsNone(by_id["2"]["CanonicalPlayerID"])
        self.assertEqual(by_id["2"]["Reasons"], [pop.REASON_LEAGUE])
        self.assertEqual(result["Counts"]["IdentityHold"], 1)

    def test_platform_fields_from_snapshot_through_registry(self) -> None:
        rows = [
            snapshot_row("1", Team="LAR"),
            snapshot_row("2", Team=None, Status="Inactive"),
            snapshot_row("3", Team="WSH", FantasyPositions=["DB", "RB"], Position="DB"),
        ]
        result = self.build(rows, roster=["1", "2", "3"])
        by_id = {p["SleeperID"]: p for p in result["Players"]}
        self.assertEqual((by_id["1"]["TeamAbbr"], by_id["1"]["TeamID"], by_id["1"]["IsFreeAgent"]), ("LA", "LA", False))
        self.assertEqual((by_id["2"]["TeamAbbr"], by_id["2"]["TeamID"], by_id["2"]["IsFreeAgent"]), (None, None, True))
        self.assertEqual(by_id["2"]["Status"], "Inactive")
        self.assertEqual((by_id["3"]["TeamAbbr"], by_id["3"]["Position"]), ("WAS", "RB"))
        self.assertNotIn("Tank01ID", by_id["1"])

    def test_profile_fields_derive_from_canonical_profile_and_identity(self) -> None:
        rows = [snapshot_row("1"), snapshot_row("nohead", FullName="Zoë O'Neil-Smith Jr.", ESPNID="777")]
        result = self.build(rows, roster=["1", "nohead"])
        by_id = {p["SleeperID"]: p for p in result["Players"]}
        one = by_id["1"]
        self.assertEqual(one["Picture"], "https://img/1.png")
        self.assertEqual(one["NameShort"], "P. 1 Jr.")
        self.assertEqual(one["FantasyPros"], "https://www.fantasypros.com/nfl/players/prof-1-jr.php")
        self.assertEqual(one["ESPN"], "https://www.espn.com/nfl/player/_/id/E1/prof-1-jr")
        fallback = by_id["nohead"]  # no nflverse profile: Sleeper name, ESPN headshot of the canonical ESPN ID
        self.assertEqual(fallback["Picture"], "https://a.espncdn.com/i/headshots/nfl/players/full/Enohead.png")
        self.assertEqual(fallback["FantasyPros"], "https://www.fantasypros.com/nfl/players/zoe-oneil-smith-jr.php")

    def test_derive_profile_leaves_unknown_parts_null(self) -> None:
        derived = pop.derive_profile("Cher", None, None)
        self.assertEqual(derived, {"NameShort": None, "Picture": None, "PictureLarge": None,
                                   "FantasyPros": "https://www.fantasypros.com/nfl/players/cher.php", "ESPN": None})
        self.assertEqual(pop.derive_profile(None, None, "5")["FantasyPros"], None)
        self.assertEqual(pop.short_name("Marvin Harrison Jr."), "M. Harrison Jr.")
        self.assertEqual(pop.profile_slug("Amon-Ra St. Brown"), "amon-ra-st-brown")

    def test_sized_headshot_requests_a_small_nfl_cdn_image(self) -> None:
        base = "https://static.www.nfl.com/image/upload/f_auto,q_auto/league/abc"
        sized = pop.sized_headshot(base)
        self.assertEqual(sized, f"https://static.www.nfl.com/image/upload/f_auto,q_auto,w_{pop.HEADSHOT_WIDTH}/league/abc")
        self.assertEqual(pop.sized_headshot(sized), sized)
        private = "https://static.www.nfl.com/image/private/f_auto,q_auto/league/abc"
        self.assertEqual(pop.sized_headshot(private),
                         f"https://static.www.nfl.com/image/private/f_auto,q_auto,w_{pop.HEADSHOT_WIDTH}/league/abc")
        self.assertEqual(pop.sized_headshot("https://img/1.png"), "https://img/1.png")
        self.assertIsNone(pop.sized_headshot(None))
        self.assertEqual(pop.derive_profile("Cher", base, None)["Picture"], sized)
        self.assertEqual(pop.derive_profile("Cher", base, None)["PictureLarge"],
                         f"https://static.www.nfl.com/image/upload/f_auto,q_auto,w_{pop.HEADSHOT_LARGE_WIDTH}/league/abc")
        espn = "https://a.espncdn.com/i/headshots/nfl/players/full/5.png"
        fallback = pop.derive_profile("Cher", None, "5")
        self.assertEqual((fallback["Picture"], fallback["PictureLarge"]), (espn, espn))

    def test_missing_profiles_fail_closed(self) -> None:
        fixture = PopulationFixture([snapshot_row("1")], roster=["1"])
        self.addCleanup(fixture.close)
        (fixture.root / "source-data/nfl/player-profiles/nflverse.json").unlink()
        with self.assertRaises(pop.PopulationError):
            fixture.build()

    def test_unknown_team_fails_closed(self) -> None:
        with self.assertRaises(pop.PopulationError):
            self.build([snapshot_row("1", Team="XXX")], roster=["1"])

    def test_previous_season_roster_while_current_is_unpublished(self) -> None:
        rows = [snapshot_row("1"), snapshot_row("2")]
        result = self.build(rows, roster=[], current_roster=False, previous_roster=["1"])
        self.assertEqual([p["SleeperID"] for p in result["Players"]], ["1"])
        self.assertTrue(result["RosterBasis"]["UsedPreviousSeasonRoster"])
        self.assertEqual(result["RosterBasis"]["RosterSeason"], SEASON - 1)

    def test_no_roster_at_all_fails_closed(self) -> None:
        with self.assertRaises(pop.PopulationError):
            self.build([snapshot_row("1")], roster=[], current_roster=False)

    def test_snapshot_without_profile_fields_fails_closed(self) -> None:
        row = snapshot_row("1")
        del row["BirthDate"]
        with self.assertRaises(pop.PopulationError):
            self.build([row], roster=["1"])

    def test_empty_population_fails_closed(self) -> None:
        with self.assertRaises(pop.PopulationError):
            self.build([snapshot_row("1")], roster=[], identity_ids=["1"], current_roster=True)

    def test_export_is_deterministic(self) -> None:
        rows = [snapshot_row(i) for i in ("3", "1", "2")]
        fixture = PopulationFixture(rows, roster=["1", "2", "3"])
        self.addCleanup(fixture.close)
        first, second = fixture.build(), fixture.build()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual([p["SleeperID"] for p in first["Players"]], ["1", "2", "3"])


class GeneratorCutoverTests(unittest.TestCase):
    def test_generator_has_no_tank01_or_live_sleeper_population(self) -> None:
        source = GENERATOR.read_text(encoding="utf-8")
        self.assertNotIn("getNFLPlayerList", source)
        self.assertNotIn("api.sleeper.app", source)
        self.assertNotIn("$tankPlayers", source)
        self.assertIn("Invoke-PlayerPopulationExport", source)
        self.assertNotIn("Get-InterimPlayerProfileLinks", source)
        self.assertNotIn("$profileLinks", source)
        self.assertNotRegex(source, r"TankID\s+=\s+\$entry")


if __name__ == "__main__":
    unittest.main()
