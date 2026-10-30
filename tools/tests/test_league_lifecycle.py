"""League lifecycle (ADR-073, Issue #1199): every rule branch of lifecycle-v1 with constructed seasons and a fixed AtUtc,
the pure-function contract, and the fact loader on a synthetic repository. No real league data is hard-wired."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import derived_data_lib.league_lifecycle as lifecycle  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.lifecycle import v1  # noqa: E402

REPO_ROOT = TOOLS.parent
UTC = timezone.utc
SEASON = 2030
LEAGUE = "test-league"


def at(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def encode_days(modes: list[int]) -> int:
    """Seven base-4 digits Monday..Sunday (Sleeper daily_waivers_days)."""
    value = 0
    for mode in modes:
        value = value * 4 + mode
    return value


# Sunday 2030-09-08 is the first kickoff; the season window opens 7 days earlier (2030-09-01 same time).
KICKOFF = at("2030-09-08T17:00:00Z")
CAP_DEADLINE = at("2030-06-30T23:59:59Z")


def games(final_weeks: int = 0, *, weeks: int = 4) -> list[v1.Game]:
    result = []
    for week in range(1, weeks + 1):
        day = KICKOFF + timedelta(days=7 * (week - 1))
        result.append(v1.Game(week, f"{day:%Y%m%d}_AAA@BBB", day, week <= final_weeks))
        result.append(v1.Game(week, f"{day:%Y%m%d}_CCC@DDD", day + timedelta(hours=3), week <= final_weeks))
    return result


def draft(status: str, *, season: int = SEASON, start: object = None, utc: object = None) -> dict:
    return {"Season": str(season), "Status": status, "SleeperStartTime": start, "DraftStartTimeUtc": utc}


def facts(**overrides) -> v1.Facts:
    base = dict(
        season=SEASON,
        provider_status="in_season",
        settings={"disable_trades": 0, "trade_review_days": 0, "trade_deadline": 99, "disable_adds": 0,
                  "daily_waivers": 1, "daily_waivers_days": encode_days([2, 2, 1, 2, 2, 2, 1]), "daily_waivers_hour": 3,
                  "playoff_week_start": 14},
        final_scored_week=0,
        last_league_week=17,
        drafts=[draft("Complete")],
        games=games(),
        cap_deadline=CAP_DEADLINE,
        cap_buffer_days=2,
    )
    base.update(overrides)
    return v1.Facts(**base)


def settings(**changes) -> dict:
    merged = dict(facts().settings)
    merged.update(changes)
    return merged


IN_SEASON_AT = at("2030-10-01T12:00:00Z")


class StatusRuleTests(unittest.TestCase):
    """One test per rule of league-lifecycle.yaml statusRules (the twelve branches)."""

    def state(self, f: v1.Facts, when: datetime = IN_SEASON_AT) -> tuple[str, str]:
        result = v1.resolve(f, when)
        return result["Status"], result["Phase"]

    def test_01_provider_complete_is_completed_and_closes_everything(self) -> None:
        result = v1.resolve(facts(provider_status="complete"), IN_SEASON_AT)
        self.assertEqual(("Completed", ""), (result["Status"], result["Phase"]))
        self.assertEqual((False, False, None, False), (result["TradesOpen"], result["WaiversOpen"], result["NextWaiverRun"], result["CutsAllowed"]))

    def test_02_provider_playoffs_and_scored_playoff_start_week_are_playoffs(self) -> None:
        self.assertEqual(("Playoffs", ""), self.state(facts(provider_status="playoffs")))
        self.assertEqual(("Playoffs", ""), self.state(facts(final_scored_week=14)))
        self.assertEqual(("Playoffs", ""), self.state(facts(final_scored_week=16)))
        self.assertEqual(("In-Season", ""), self.state(facts(final_scored_week=13)))
        no_playoff_week = facts(final_scored_week=16, settings=settings(playoff_week_start=None))
        self.assertEqual(("In-Season", ""), self.state(no_playoff_week))

    def test_03_all_drafts_complete_depends_on_the_season_window(self) -> None:
        start = KICKOFF - timedelta(days=7)
        self.assertEqual(("Pre-Season", ""), self.state(facts(), start - timedelta(seconds=1)))
        self.assertEqual(("In-Season", ""), self.state(facts(), start))
        self.assertEqual(("In-Season", ""), self.state(facts(), start + timedelta(days=30)))

    def test_04_a_live_draft_is_in_draft(self) -> None:
        self.assertEqual(("Draft-Season", "In Draft"), self.state(facts(drafts=[draft("Complete"), draft("Drafting")])))
        self.assertEqual(("Draft-Season", "In Draft"), self.state(facts(drafts=[draft("Virtual"), draft("Drafting")])))

    def test_05_completed_plus_open_draft_with_start_time_is_pre_draft(self) -> None:
        for open_draft in (draft("PreDraft", start=1_900_000_000_000), draft("Virtual", utc="2030-08-01T10:00:00Z")):
            self.assertEqual(("Draft-Season", "Pre Draft"), self.state(facts(drafts=[draft("Complete"), open_draft])))

    def test_06_completed_plus_open_draft_without_start_time_is_between_drafts(self) -> None:
        blank = draft("Virtual", start="", utc="  ")
        self.assertEqual(("Draft-Season", "Between Drafts"), self.state(facts(drafts=[draft("Complete"), blank])))
        self.assertEqual(("Draft-Season", "Between Drafts"), self.state(facts(drafts=[draft("Complete"), draft("PreDraft")])))

    def test_07_trades_open_inside_the_cap_window_is_cap_deadline_open(self) -> None:
        only_open = facts(drafts=[draft("Virtual")])
        self.assertEqual(("Off-Season", "Cap Deadline Open"), self.state(only_open, at("2030-06-30T10:00:00Z")))
        self.assertEqual(("Off-Season", "Cap Deadline Open"), self.state(only_open, at("2030-07-02T23:59:59Z")))
        self.assertEqual(("Off-Season", "Post Cap Check"), self.state(only_open, at("2030-07-03T00:00:00Z")))

    def test_07_cap_window_applies_without_any_draft(self) -> None:
        no_drafts = facts(drafts=[])
        self.assertEqual(("Off-Season", "Cap Deadline Open"), self.state(no_drafts, at("2030-07-01T00:00:00Z")))

    def test_08_open_draft_and_closed_trades_is_cap_check(self) -> None:
        closed = facts(drafts=[draft("Virtual")], settings=settings(disable_trades=1))
        self.assertEqual(("Off-Season", "Cap Check"), self.state(closed, at("2030-07-10T00:00:00Z")))
        review = facts(drafts=[draft("Virtual")], settings=settings(trade_review_days=2))
        self.assertEqual(("Off-Season", "Cap Check"), self.state(review, at("2030-06-30T00:00:00Z")))

    def test_09_open_draft_open_trades_no_start_time_is_post_cap_check(self) -> None:
        self.assertEqual(("Off-Season", "Post Cap Check"), self.state(facts(drafts=[draft("Virtual")]), at("2030-07-10T00:00:00Z")))

    def test_10_open_draft_open_trades_start_time_is_pre_draft(self) -> None:
        scheduled = facts(drafts=[draft("PreDraft", start=1_900_000_000_000)])
        self.assertEqual(("Draft-Season", "Pre Draft"), self.state(scheduled, at("2030-07-10T00:00:00Z")))

    def test_11_without_drafts_before_the_season_window_is_pre_season(self) -> None:
        self.assertEqual(("Pre-Season", ""), self.state(facts(drafts=[]), at("2030-08-01T00:00:00Z")))

    def test_12_without_drafts_inside_the_season_window_is_in_season(self) -> None:
        self.assertEqual(("In-Season", ""), self.state(facts(drafts=[]), IN_SEASON_AT))

    def test_rule_order_completed_beats_playoffs_and_playoffs_beat_drafts(self) -> None:
        self.assertEqual(("Completed", ""), self.state(facts(provider_status="Complete", final_scored_week=15)))
        self.assertEqual(("Playoffs", ""), self.state(facts(provider_status="playoffs", drafts=[draft("Drafting")])))

    def test_drafts_of_other_seasons_are_ignored(self) -> None:
        other = facts(drafts=[draft("Complete"), draft("Drafting", season=SEASON + 1), draft("Virtual", season=SEASON + 2)])
        self.assertEqual(("In-Season", ""), self.state(other))

    def test_no_current_season_draft_is_not_all_complete(self) -> None:
        self.assertEqual(("In-Season", ""), self.state(facts(drafts=[draft("Complete", season=SEASON - 1)]), IN_SEASON_AT))
        self.assertEqual(("Pre-Season", ""), self.state(facts(drafts=[draft("Complete", season=SEASON - 1)]), at("2030-08-20T00:00:00Z")))

    def test_status_text_comparison_ignores_case_like_powershell(self) -> None:
        self.assertEqual(("Playoffs", ""), self.state(facts(provider_status="PLAYOFFS")))
        self.assertEqual(("Draft-Season", "In Draft"), self.state(facts(drafts=[draft("drafting")])))

    def test_missing_kickoff_never_starts_the_season_window(self) -> None:
        self.assertEqual(("Pre-Season", ""), self.state(facts(games=[]), at("2031-01-01T00:00:00Z")))


class TradeAndWaiverTests(unittest.TestCase):
    def test_trade_flags_and_reasons(self) -> None:
        open_trades = v1.resolve(facts(), IN_SEASON_AT)
        self.assertEqual((True, [], 0, None), (open_trades["TradesOpen"], open_trades["TradesClosedBy"], open_trades["TradeReviewDays"], open_trades["TradeDeadlineWeek"]))
        both = v1.resolve(facts(settings=settings(disable_trades=1, trade_review_days=3)), IN_SEASON_AT)
        self.assertEqual((False, ["DisabledInProvider", "CommissionerReview"], 3), (both["TradesOpen"], both["TradesClosedBy"], both["TradeReviewDays"]))

    def test_trade_deadline_compares_against_current_week_then_final_scored_week(self) -> None:
        week_two = games(final_weeks=1)  # current week 2
        reached = v1.resolve(facts(games=week_two, settings=settings(trade_deadline=2)), IN_SEASON_AT)
        self.assertEqual((False, ["TradeDeadlineReached"], 2), (reached["TradesOpen"], reached["TradesClosedBy"], reached["TradeDeadlineWeek"]))
        before = v1.resolve(facts(games=week_two, settings=settings(trade_deadline=3)), IN_SEASON_AT)
        self.assertTrue(before["TradesOpen"])
        all_final = games(final_weeks=4)  # no open game: falls back to FinalScoredWeek
        fallback = v1.resolve(facts(games=all_final, final_scored_week=4, settings=settings(trade_deadline=4)), IN_SEASON_AT)
        self.assertEqual((0, False), (fallback["CurrentWeek"], fallback["TradesOpen"]))
        self.assertTrue(v1.resolve(facts(games=all_final, final_scored_week=3, settings=settings(trade_deadline=4)), IN_SEASON_AT)["TradesOpen"])

    def test_trade_deadline_week_normalisation(self) -> None:
        for value in (None, "", "  ", 0, -1, 99, "99", "abc", "1.5"):
            self.assertIsNone(v1.trade_deadline_week(value), repr(value))
        self.assertEqual(9, v1.trade_deadline_week(9))
        self.assertEqual(9, v1.trade_deadline_week(" 9 "))

    def test_waivers_open_follows_disable_adds(self) -> None:
        self.assertTrue(v1.resolve(facts(), IN_SEASON_AT)["WaiversOpen"])
        closed = v1.resolve(facts(settings=settings(disable_adds=1)), IN_SEASON_AT)
        self.assertEqual((False, None), (closed["WaiversOpen"], closed["NextWaiverRun"]))

    def test_next_waiver_run_is_the_first_mode_one_day_strictly_after_the_instant(self) -> None:
        # Wednesday and Sunday (mode 1) at 03:00 America/Los_Angeles. 2030-10-01 is a Tuesday (PDT, UTC-7).
        self.assertEqual("2030-10-02T10:00:00Z", v1.resolve(facts(), at("2030-10-01T12:00:00Z"))["NextWaiverRun"])
        self.assertEqual("2030-10-06T10:00:00Z", v1.resolve(facts(), at("2030-10-02T10:00:00Z"))["NextWaiverRun"])  # strictly after
        self.assertEqual("2030-10-02T10:00:00Z", v1.resolve(facts(), at("2030-10-02T09:59:59Z"))["NextWaiverRun"])

    def test_next_waiver_run_after_the_daylight_saving_change(self) -> None:
        # DST ends 2030-11-03; Sunday 03:00 PST is 11:00Z.
        self.assertEqual("2030-11-03T11:00:00Z", v1.resolve(facts(), at("2030-11-01T00:00:00Z"))["NextWaiverRun"])

    def test_next_waiver_run_decoding_and_undecidable_cases(self) -> None:
        self.assertEqual([2, 2, 1, 2, 2, 2, 1], v1._daily_waiver_modes(encode_days([2, 2, 1, 2, 2, 2, 1])))
        self.assertIsNone(v1._daily_waiver_modes(-1))
        self.assertIsNone(v1._daily_waiver_modes(4 ** 7))
        for changes in ({"daily_waivers": 0}, {"daily_waivers_days": None}, {"daily_waivers_hour": None}, {"daily_waivers_hour": 24},
                        {"daily_waivers_hour": -1}, {"daily_waivers_days": encode_days([2] * 7)}, {"daily_waivers_days": 4 ** 7}):
            result = v1.resolve(facts(settings=settings(**changes)), IN_SEASON_AT)
            self.assertIsNone(result["NextWaiverRun"], changes)
            self.assertEqual([], result["Warnings"], changes)

    def test_unvalidated_modes_and_daylight_saving_edges_give_none_with_a_warning(self) -> None:
        unvalidated = v1.resolve(facts(settings=settings(daily_waivers_days=encode_days([3, 2, 1, 2, 2, 2, 1]))), IN_SEASON_AT)
        self.assertIsNone(unvalidated["NextWaiverRun"])
        self.assertIn("unvalidated Sleeper mode(s): 3", unvalidated["Warnings"][0])
        sunday_only = settings(daily_waivers_days=encode_days([2, 2, 2, 2, 2, 2, 1]))
        ambiguous = v1.resolve(facts(settings=settings(**{**sunday_only, "daily_waivers_hour": 1})), at("2030-10-30T00:00:00Z"))  # 2030-11-03 01:00 repeats
        self.assertIsNone(ambiguous["NextWaiverRun"])
        self.assertIn("DST transition", ambiguous["Warnings"][0])
        invalid = v1.resolve(facts(settings=settings(**{**sunday_only, "daily_waivers_hour": 2})), at("2031-03-05T00:00:00Z"))  # 2031-03-09 02:00 skipped
        self.assertIsNone(invalid["NextWaiverRun"])
        self.assertIn("DST transition", invalid["Warnings"][0])

    def test_cuts_are_allowed_except_when_completed(self) -> None:
        self.assertTrue(v1.resolve(facts(), IN_SEASON_AT)["CutsAllowed"])
        self.assertFalse(v1.resolve(facts(provider_status="complete"), IN_SEASON_AT)["CutsAllowed"])


class OutputTests(unittest.TestCase):
    def test_weeks_kickoffs_and_boundaries(self) -> None:
        result = v1.resolve(facts(games=games(final_weeks=1), final_scored_week=1), IN_SEASON_AT)
        self.assertEqual((2, 1, 17, 14), (result["CurrentWeek"], result["FinalScoredWeek"], result["LastLeagueWeek"], result["PlayoffStartWeek"]))
        self.assertEqual("2030-09-08T17:00:00Z", result["SeasonKickoff"])
        self.assertIsNone(result["PlayoffStart"])  # no week 14 in the constructed schedule
        with_playoff = v1.resolve(facts(settings=settings(playoff_week_start=3)), IN_SEASON_AT)
        self.assertEqual("2030-09-22T17:00:00Z", with_playoff["PlayoffStart"])
        self.assertEqual({"CapWindowEnd": "2030-07-03T00:00:00Z", "SeasonWindowStart": "2030-09-01T17:00:00Z",
                          "NextWaiverRun": result["NextWaiverRun"]}, result["Boundaries"])

    def test_no_cap_deadline_means_no_cap_window(self) -> None:
        result = v1.resolve(facts(cap_deadline=None, drafts=[]), at("2030-07-01T00:00:00Z"))
        self.assertIsNone(result["Boundaries"]["CapWindowEnd"])
        self.assertEqual(("Pre-Season", ""), (result["Status"], result["Phase"]))

    def test_current_week_is_zero_without_games_or_when_all_are_final(self) -> None:
        self.assertEqual(0, v1.resolve(facts(games=[]), IN_SEASON_AT)["CurrentWeek"])
        self.assertEqual(0, v1.resolve(facts(games=games(final_weeks=4)), IN_SEASON_AT)["CurrentWeek"])

    def test_current_week_follows_game_date_order_not_week_order(self) -> None:
        postponed = [v1.Game(1, "20300909_AAA@BBB", KICKOFF, True), v1.Game(2, "20300922_AAA@BBB", KICKOFF + timedelta(days=14), False),
                     v1.Game(1, "20300929_CCC@DDD", KICKOFF + timedelta(days=21), False)]
        self.assertEqual(2, v1.current_week(postponed))

    def test_result_is_a_pure_function_of_facts_and_instant(self) -> None:
        f = facts(drafts=[draft("Virtual")])
        self.assertEqual(v1.resolve(f, IN_SEASON_AT), v1.resolve(f, IN_SEASON_AT))
        # A different instant changes only clock-dependent parts, never the inputs.
        self.assertNotEqual(v1.resolve(f, at("2030-06-30T10:00:00Z"))["Phase"], v1.resolve(f, at("2030-07-04T10:00:00Z"))["Phase"])
        offset = datetime(2030, 10, 1, 14, 0, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(v1.resolve(f, IN_SEASON_AT), v1.resolve(f, offset))

    def test_naive_instant_and_bad_settings_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            v1.resolve(facts(), datetime(2030, 10, 1, 12, 0))
        with self.assertRaises(ValueError):
            v1.resolve(facts(settings=settings(disable_trades="maybe")), IN_SEASON_AT)
        with self.assertRaises(ValueError):
            v1.resolve(facts(settings=settings(trade_review_days=True)), IN_SEASON_AT)

    def test_model_is_registered_with_pinned_parameters(self) -> None:
        self.assertIs(v1, registry.get_model("lifecycle-v1", kind="lifecycle"))
        self.assertEqual("lifecycle-v1", v1.MODEL_ID)
        self.assertEqual(
            {"SeasonStartLeadDays": 7, "OpenDraftStatuses": ("Virtual", "PreDraft", "Drafting"), "LiveDraftStatus": "Drafting",
             "CompletedDraftStatus": "Complete", "WaiverTimeZone": "America/Los_Angeles", "ValidatedWaiverModes": (1, 2),
             "WaiverLookaheadDays": 7, "TradeDeadlineDisabledWeek": 99},
            dict(v1.PARAMS))
        with self.assertRaises(TypeError):
            v1.PARAMS["Injected"] = 1  # type: ignore[index]


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_repo(root: Path, *, status: str = "in_season", drafts=None, final_weeks: int = 1, scored: int = 1) -> None:
    """A synthetic repository with exactly the inputs of the lifecycle loader (and no public/data)."""
    meta = json.loads((REPO_ROOT / "data-meta/nfl-reise/metadata.json").read_text(encoding="utf-8"))
    meta["CanonicalLeagueID"] = LEAGUE
    models = dict(meta["Seasons"]["2026"]["Models"])
    meta["Seasons"] = {str(SEASON): {"CapDeadline": "2030-06-30T23:59:59Z", "CapDeadlineBufferDays": 2, "Models": models}}
    write(root / f"data-meta/{LEAGUE}/metadata.json", meta)
    write(root / f"data-source/leagues/{LEAGUE}/seasons/{SEASON}/league.json", {
        "CanonicalLeagueID": LEAGUE, "Season": SEASON, "Status": status,
        "Settings": settings(playoff_week_start=3),
        "WeekStructure": {"StartWeek": 1, "ExpectedLastLeagueWeek": 4, "LastScoredLeg": scored, "PlayoffStartWeek": 3},
    })
    write(root / f"data-derived/league-drafts/{LEAGUE}/{SEASON}.json", {
        "CanonicalLeagueID": LEAGUE, "Season": SEASON, "Drafts": [draft("Complete")] if drafts is None else drafts})
    write(root / "data-source/nfl/teams.json", {"Teams": [{"TeamAbbr": abbr} for abbr in ("AAA", "BBB", "CCC", "DDD")]})
    schedule_games, finality_games, weeks = [], [], []
    for week in range(1, 5):
        day = datetime(2030, 9, 8, tzinfo=UTC) + timedelta(days=7 * (week - 1))
        for index, (away, home) in enumerate((("AAA", "BBB"), ("CCC", "DDD"))):
            game_id = f"{SEASON}_{week:02d}_{away}_{home}"
            schedule_games.append({
                "GameID": game_id, "GameType": "REG", "Week": week, "GameDay": f"{day:%Y-%m-%d}", "GameTime": "13:00" if index == 0 else "16:25",
                "AwayTeam": away, "HomeTeam": home, "Location": "Home", "Overtime": "0", "AwayScore": 10, "HomeScore": 20,
                "ProviderGameIDs": {"ESPN": f"4{week}{index}"}})
            finality_games.append({"GameID": game_id, "GameType": "REG", "Week": week, "Final": week <= final_weeks})
        weeks.append({"GameType": "REG", "Week": week, "ApplicableGameCount": 2, "FinalGameCount": 2 if week <= final_weeks else 0,
                      "WeekFinal": week <= final_weeks})
    write(root / f"data-source/nfl/schedules/{SEASON}.json", {"SchemaVersion": 1, "Season": SEASON, "SourceDataset": "nflverse.schedules", "Finalized": False, "Games": schedule_games})
    write(root / f"data-source/nfl/game-finality/{SEASON}.json", {"SchemaVersion": 1, "Season": SEASON, "SourceDataset": "nflverse.game-finality",
                                                                  "ScheduleDataset": "nflverse.schedules", "Finalized": False, "Games": finality_games, "Weeks": weeks})


class LoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_resolves_from_canonical_facts_only(self) -> None:
        build_repo(self.root)
        self.assertFalse((self.root / "public").exists())
        result = lifecycle.resolve_lifecycle(self.root, LEAGUE, SEASON, at("2030-10-01T12:00:00Z"))
        self.assertEqual(("lifecycle-v1", "In-Season", ""), (result["Model"], result["Status"], result["Phase"]))
        self.assertEqual((2, 1, 4, 3), (result["CurrentWeek"], result["FinalScoredWeek"], result["LastLeagueWeek"], result["PlayoffStartWeek"]))
        self.assertEqual(("2030-09-08T17:00:00Z", "2030-09-22T17:00:00Z"), (result["SeasonKickoff"], result["PlayoffStart"]))
        self.assertEqual("2030-10-01T12:00:00Z", result["AtUtc"])
        self.assertEqual("2030-10-02T10:00:00Z", result["NextWaiverRun"])

    def test_drafts_come_from_the_product_and_phase_follows_the_instant(self) -> None:
        build_repo(self.root, drafts=[draft("Complete"), draft("Virtual")])
        self.assertEqual("Between Drafts", lifecycle.resolve_lifecycle(self.root, LEAGUE, SEASON, at("2030-10-01T00:00:00Z"))["Phase"])
        build_repo(self.root, drafts=[draft("Drafting")])
        self.assertEqual("In Draft", lifecycle.resolve_lifecycle(self.root, LEAGUE, SEASON, at("2030-10-01T00:00:00Z"))["Phase"])

    def test_provider_status_complete_passes_through(self) -> None:
        build_repo(self.root, status="complete", final_weeks=4, scored=4)
        result = lifecycle.resolve_lifecycle(self.root, LEAGUE, SEASON, at("2030-12-30T00:00:00Z"))
        self.assertEqual(("Completed", 0, 4), (result["Status"], result["CurrentWeek"], result["FinalScoredWeek"]))

    def test_every_missing_input_fails_closed(self) -> None:
        for missing in (f"data-meta/{LEAGUE}/metadata.json", f"data-source/leagues/{LEAGUE}/seasons/{SEASON}/league.json",
                        f"data-derived/league-drafts/{LEAGUE}/{SEASON}.json", f"data-source/nfl/schedules/{SEASON}.json",
                        f"data-source/nfl/game-finality/{SEASON}.json", "data-source/nfl/teams.json"):
            with self.subTest(missing=missing):
                shutil_root = Path(tempfile.mkdtemp(dir=self.root))
                build_repo(shutil_root)
                (shutil_root / missing).unlink()
                with self.assertRaises(lifecycle.LifecycleError):
                    lifecycle.resolve_lifecycle(shutil_root, LEAGUE, SEASON, at("2030-10-01T00:00:00Z"))

    def test_foreign_or_naive_inputs_fail_closed(self) -> None:
        build_repo(self.root)
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.resolve_lifecycle(self.root, LEAGUE, SEASON, datetime(2030, 10, 1))
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.resolve_lifecycle(self.root, LEAGUE, 2031, at("2030-10-01T00:00:00Z"))
        write(self.root / f"data-derived/league-drafts/{LEAGUE}/{SEASON}.json", {"CanonicalLeagueID": "other", "Season": SEASON, "Drafts": []})
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.resolve_lifecycle(self.root, LEAGUE, SEASON, at("2030-10-01T00:00:00Z"))
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.parse_instant("2030-10-01T12:00:00", "--at")

    def test_no_lifecycle_input_reads_public_data(self) -> None:
        for path in (TOOLS / "derived_data_lib/league_lifecycle.py", TOOLS / "derived_data_lib/models/lifecycle/v1.py"):
            source = path.read_text(encoding="utf-8")
            for forbidden in ("public/data", "public\\data", "PUBLIC_DATA"):
                self.assertNotIn(forbidden, source, f"{path.name} mentions {forbidden}")

    def test_cli_prints_json_and_fails_closed(self) -> None:
        build_repo(self.root)
        run = subprocess.run([sys.executable, str(TOOLS / "league_lifecycle.py"), "resolve", "--league", LEAGUE, "--season", str(SEASON),
                              "--at", "2030-10-01T12:00:00Z", "--repo-root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual("In-Season", json.loads(run.stdout)["Status"])
        failing = subprocess.run([sys.executable, str(TOOLS / "league_lifecycle.py"), "resolve", "--league", "nope", "--season", "2030",
                                  "--repo-root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(1, failing.returncode)
        self.assertIn("league_lifecycle:", failing.stderr)


if __name__ == "__main__":
    unittest.main()
