from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from odds_observation_buffer import (  # noqa: E402
    plan_observation, read_upstream_lines, serialize_state
)
from odds_observation import run as run_cli, fetch_registered_odds  # noqa: E402

BASE_TIME = datetime(2026, 10, 17, 16, 0, tzinfo=timezone.utc)
GAME = "2026_07_TB_CAR"


def inputs():
    schedule = {
        "Season": 2026, "Games": [{
            "GameID": GAME, "GameType": "REG", "Week": 7,
            "GameDay": "2026-10-18", "GameTime": "13:00",
            "AwayTeam": "TB", "HomeTeam": "CAR",
        }]
    }
    canonical = {
        "Season": 2026, "Games": [{
            "GameID": GAME, "SpreadLine": 3.0, "TotalLine": 44.5,
            "HomeMoneyline": -200, "OverOdds": -115,
        }]
    }
    return schedule, canonical


def plan(observed=None, *, prior=None, canonical=None, now=BASE_TIME):
    schedule, original = inputs()
    return plan_observation(
        season=2026, schedule=schedule,
        canonical_odds=canonical or original,
        observed_lines={GAME: observed or {"SpreadLine": 3.0, "TotalLine": 44.5}},
        previous_state=prior, observed_at=now,
    )


class OddsObservationBufferTests(unittest.TestCase):
    def test_first_small_change_waits_even_after_idle_source_snapshot(self):
        changed = {"SpreadLine": 3.5, "TotalLine": 44.5}
        p1, state = plan(changed)
        self.assertEqual(p1["PublishableGameIDs"], [])
        self.assertEqual(state["Games"][GAME]["PendingSince"], "2026-10-17T16:00:00Z")
        p2, state = plan(changed, prior=state, now=BASE_TIME + timedelta(minutes=10))
        self.assertEqual(p2["PublishableGameIDs"], [])
        p3, state = plan(changed, prior=state, now=BASE_TIME + timedelta(minutes=60))
        self.assertEqual(p3["PublishableGameIDs"], [GAME])
        self.assertEqual(p3["PublicationReasons"][GAME], "maximum_age_with_pending_change")

    def test_cumulative_change_is_immediate_but_state_does_not_claim_published(self):
        p1, state = plan({"SpreadLine": 3.5, "TotalLine": 44.5})
        self.assertFalse(p1["PublishableGameIDs"])
        p2, state = plan({"SpreadLine": 4.0, "TotalLine": 44.5},
                         prior=state, now=BASE_TIME + timedelta(minutes=10))
        self.assertEqual(p2["PublicationReasons"][GAME], "large_cumulative_change")
        self.assertEqual(state["Games"][GAME]["PublishedAt"], "2026-10-17T16:00:00Z")

    def test_reversion_clears_buffer_and_fresh_move_restarts_clock(self):
        _, state = plan({"SpreadLine": 3.5, "TotalLine": 44.5})
        _, state = plan({"SpreadLine": 3.0, "TotalLine": 44.5},
                        prior=state, now=BASE_TIME + timedelta(minutes=20))
        self.assertIsNone(state["Games"][GAME]["PendingSince"])
        proposal, state = plan({"SpreadLine": 3.5, "TotalLine": 44.5},
                               prior=state, now=BASE_TIME + timedelta(minutes=50))
        self.assertFalse(proposal["PublishableGameIDs"])
        self.assertEqual(state["Games"][GAME]["PendingSince"], "2026-10-17T16:50:00Z")

    def test_external_canonical_publish_rebases_checkpoint(self):
        _, state = plan({"SpreadLine": 3.5, "TotalLine": 44.5})
        schedule, canonical = inputs()
        canonical["Games"][0]["SpreadLine"] = 3.5
        p, state = plan({"SpreadLine": 3.5, "TotalLine": 44.5},
                        prior=state, canonical=canonical,
                        now=BASE_TIME + timedelta(minutes=40))
        self.assertEqual(p["PublishableGameIDs"], [])
        self.assertIsNone(state["Games"][GAME]["PendingSince"])
        self.assertEqual(state["Games"][GAME]["PublishedAt"], "2026-10-17T16:40:00Z")

    def test_price_only_canonical_change_not_source_baseline(self):
        _, state = plan()
        schedule, canonical = inputs()
        canonical["Games"][0]["HomeMoneyline"] = -500
        p, state2 = plan(prior=state, canonical=canonical,
                         now=BASE_TIME + timedelta(minutes=40))
        self.assertFalse(p["PublishableGameIDs"])
        self.assertEqual(state["Games"][GAME]["PublishedAt"],
                         state2["Games"][GAME]["PublishedAt"])

    def test_kickoff_pregame_flush_and_past_game_excluded(self):
        _, state = plan()
        small = {"SpreadLine": 3.5, "TotalLine": 44.5}
        kickoff = datetime(2026, 10, 18, 17, 0, tzinfo=timezone.utc)
        p, state = plan(small, prior=state, now=kickoff - timedelta(minutes=10))
        self.assertEqual(p["PublicationReasons"][GAME], "pregame_last_flush")
        p, _ = plan(small, prior=state, now=kickoff + timedelta(minutes=1))
        self.assertEqual(p["PublishableGameIDs"], [])

    def test_invalid_state_or_feed_fails_closed(self):
        _, state = plan()
        for bad in (
            {**state, "SchemaVersion": 99},
            {**state, "Games": {}},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    plan(prior=bad, now=BASE_TIME + timedelta(minutes=10))
        with self.assertRaises(ValueError):
            plan(prior=state, now=BASE_TIME - timedelta(minutes=1))
        with self.assertRaises(ValueError):
            plan({"SpreadLine": float("nan"), "TotalLine": 44.5})
        with self.assertRaises(ValueError):
            plan({"SpreadLine": 3.0, "TotalLine": -2.0})

    def test_strict_upstream_csv_join_ignores_prices(self):
        rows = [{
            "game_id": GAME, "spread_line": "3.5", "total_line": "44.5",
            "home_moneyline": "-1000",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "games.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            observed = read_upstream_lines(path, 2026, {GAME})
            self.assertEqual(observed[GAME], {"SpreadLine": 3.5, "TotalLine": 44.5})
            with self.assertRaises(ValueError):
                read_upstream_lines(path, 2026, {GAME, "2026_07_ARI_NE"})
            with path.open("a", encoding="utf-8") as stream:
                stream.write(f"{GAME},3.5,44.5,-1000\n")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                read_upstream_lines(path, 2026, {GAME})

    def test_cli_strict_bootstrap_and_isolated_atomic_state(self):
        schedule, canonical = inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "main-repo"
            source = root / "data-source" / "nfl"
            for folder, document in (("schedules", schedule), ("schedule-odds", canonical)):
                target = source / folder / "2026.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(document), encoding="utf-8")
            csvpath = Path(tmp) / "upstream.csv"
            csvpath.write_text(
                "game_id,spread_line,total_line\n"
                f"{GAME},3.5,44.5\n", encoding="utf-8"
            )
            state_path = Path(tmp) / "isolated-state" / "state.json"
            preview = run_cli(root, season=2026, upstream_csv=csvpath, observed_at=BASE_TIME)
            self.assertEqual(preview["PublishableGameIDs"], [])
            self.assertFalse(state_path.exists())
            with self.assertRaisesRegex(ValueError, "missing"):
                run_cli(root, season=2026, upstream_csv=csvpath,
                        state_input=state_path, observed_at=BASE_TIME)
            with self.assertRaisesRegex(ValueError, "main repository"):
                run_cli(root, season=2026, upstream_csv=csvpath,
                        state_output=root / "data-source" / "nfl" / "buffer.json",
                        observed_at=BASE_TIME)
            run_cli(root, season=2026, upstream_csv=csvpath,
                    state_output=state_path, observed_at=BASE_TIME)
            self.assertTrue(state_path.exists())
            next_plan = run_cli(
                root, season=2026, upstream_csv=csvpath,
                state_input=state_path, state_output=state_path,
                observed_at=BASE_TIME + timedelta(minutes=60),
            )
            self.assertEqual(next_plan["PublishableGameIDs"], [GAME])

    def test_identical_polls_do_not_write_technical_state_again(self):
        _, state = plan()
        previous = serialize_state(state)
        next_plan, after = plan(prior=state, now=BASE_TIME + timedelta(minutes=10))
        self.assertFalse(next_plan["PublishableGameIDs"])
        self.assertEqual(serialize_state(after), previous)
        # Quotenpreise werden nicht eingelesen; sie dürfen den State nicht verändern.
        changed = {"SpreadLine": 3.5, "TotalLine": 44.5}
        _, after = plan(changed, prior=after, now=BASE_TIME + timedelta(minutes=20))
        self.assertNotEqual(serialize_state(after), previous)

    def test_real_2026_canonical_source_projection_is_semantic_noop(self):
        root = TOOLS.parent
        source = root / "data-source" / "nfl"
        schedule = json.loads((source / "schedules" / "2026.json").read_text(encoding="utf-8"))
        canonical = json.loads((source / "schedule-odds" / "2026.json").read_text(encoding="utf-8"))
        ids = {game["GameID"] for game in schedule["Games"]}
        observed = read_upstream_lines(
            root / "data-source" / "providers" / "nflverse" / "schedule-odds" / "raw-latest.csv",
            2026, ids,
        )
        plan_result, state = plan_observation(
            season=2026, schedule=schedule, canonical_odds=canonical,
            observed_lines=observed, previous_state=None, observed_at=BASE_TIME,
        )
        self.assertEqual(plan_result["TotalGames"], 272)
        # The registered raw evidence may legitimately be newer than the daily
        # canonical partition. Compare semantic counts, not a brittle no-drift
        # assumption about independently refreshed source snapshots.
        canonical_by_id = {g["GameID"]: g for g in canonical["Games"]}
        expected_changed = {game_id for game_id, values in observed.items()
                            if any(values.get(field) != canonical_by_id[game_id].get(field)
                                   for field in ("SpreadLine", "TotalLine"))}
        self.assertEqual(plan_result["RelevantNetChanges"], len(expected_changed))
        self.assertTrue(set(plan_result["PublishableGameIDs"]) <= expected_changed)
        self.assertEqual(len(state["Games"]), 272)

    def test_scoped_fetch_uses_only_registered_nflverse_odds_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "data-source" / "registry.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            url = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
            manifest.write_text(json.dumps({"datasets": [
                {"id": "nflverse.schedule-odds", "sourceUrl": url},
                {"id": "nflverse.schedules", "sourceUrl": "https://example.invalid/schedules"}
            ]}), encoding="utf-8")
            dest = root / "games.csv"
            with patch("odds_observation.download") as downloader:
                fetch_registered_odds(root, dest)
                downloader.assert_called_once_with(url, dest)
            manifest.write_text(json.dumps({"datasets": [
                {"id": "nflverse.schedule-odds", "sourceUrl": "http://attacker.invalid/data"}
            ]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unexpected registered"):
                fetch_registered_odds(root, dest)

    def test_serialized_state_is_byte_stable_after_recovery(self):
        _, state = plan()
        raw = serialize_state(state)
        self.assertEqual(raw, serialize_state(json.loads(raw)))


if __name__ == "__main__":
    unittest.main()
