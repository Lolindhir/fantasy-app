from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_fa_board_readmodel.py"
SPEC = importlib.util.spec_from_file_location("build_fa_board_readmodel", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

NOW = "2026-09-03T08:00:00Z"
KICKOFF = "2026-09-10T00:20:00Z"


def source_market(provider: str) -> dict:
    signals = {"overall_rank": 10, "percentile": 92.5, "position_rank": 3, "tier": 2}
    if provider == "fantasycalc":
        signals.update({"value": 6500, "trend_30_day": 120, "roster_percent": 88, "trade_frequency": 4})
    return {
        "source_id": f"{provider}-source",
        "source_kind": "market_value" if provider == "fantasycalc" else "expert_consensus",
        "provider": provider,
        "dataset_id": f"{provider}-dataset",
        "applicable": True,
        "coverage_status": "listed",
        "listed": True,
        "join_method": "sleeper_id",
        "signals": signals,
        "format_context": {"horizon": "dynasty"},
        "freshness": {"source_timestamp": NOW, "max_age_hours": 48, "age_hours_at_materialization": 0, "status": "current"},
    }


def player(pid: str, name: str, *, years: int = 2, designation: str | None = None) -> dict:
    return {
        "player_id": pid,
        "name": name,
        "position": "WR",
        "nfl_team": "SF",
        "app_data": {"status": designation, "years_experience": years},
        "injury": {
            "coverage_status": "current_injury_signal" if designation else "no_current_injury_signal",
            "is_injured": bool(designation),
            "designation": designation,
        },
        "market": {
            "fantasycalc": source_market("fantasycalc"),
            "fantasypros": source_market("fantasypros"),
        },
    }


def league(
    *,
    managed_roster: list[str] | None = None,
    managed_taxi: list[str] | None = None,
    managed_reserve: list[str] | None = None,
    opponent_roster: list[str] | None = None,
    reserve_slots: int = 2,
    taxi_slots: int = 2,
    incomplete_opponent: bool = False,
) -> dict:
    managed_roster = list(managed_roster or [])
    managed_taxi = list(managed_taxi or [])
    managed_reserve = list(managed_reserve or [])
    for pid in managed_taxi + managed_reserve:
        if pid not in managed_roster:
            managed_roster.append(pid)
    opponent = {"TeamID": 2, "Team": "Ruhr Valley Packers", "TeamAbbr": "RVP", "Reserve": None, "Taxi": None}
    if not incomplete_opponent:
        opponent["Roster"] = list(opponent_roster or [])
    return {
        "Season": "2026",
        "Phase": "In Draft",
        "Status": "Draft-Season",
        "CurrentWeek": 1,
        "SeasonKickoff": KICKOFF,
        "RosterSize": ["QB", "QB", "RB", "RB", "WR", "WR", "TE", "TE", "FLEX", "FLEX", "K", "BN", "BN"],
        "Settings": {
            "reserve_slots": reserve_slots,
            "reserve_allow_out": 1,
            "reserve_allow_doubtful": 0,
            "reserve_allow_dnr": 0,
            "reserve_allow_sus": 0,
            "reserve_allow_na": 0,
            "reserve_allow_cov": 0,
            "taxi_slots": taxi_slots,
            "taxi_years": 1,
            "taxi_allow_vets": 0,
            "taxi_deadline": 4,
        },
        "Teams": [
            {"TeamID": 1, "Team": "Mighty Giants", "TeamAbbr": "MiG", "Roster": managed_roster, "Reserve": managed_reserve or None, "Taxi": managed_taxi or None},
            opponent,
        ],
    }


def pick(pid: str, owner: int, overall: int = 1) -> dict:
    return {
        "PickKey": f"2026_Free_Agent_R1_OO{owner}",
        "DisplayPick": f"1.{overall:02d}",
        "OverallPick": overall,
        "CurrentOwnerRosterID": owner,
        "PlayerID": pid,
        "PlayerName": pid,
        "Status": "Picked",
    }


def draft(picks: list[dict] | None = None) -> list[dict]:
    return [{"DraftKey": "2026_Free_Agent", "Season": "2026", "DraftType": "Free_Agent", "Status": "Drafting", "SleeperStatus": "drafting", "Picks": list(picks or [])}]


class Fixture:
    def __init__(self, root: Path, players: list[dict], league_data: dict, draft_data: list[dict]):
        self.root = root
        self.config = root / "fantasy-management/automation/fa-board-materialization.json"
        self.write("public/data/League.json", league_data)
        self.write("public/data/Drafts.json", draft_data)
        self.write("public/data/Timestamps.json", {"League": NOW, "Drafts": NOW, "Players": NOW})
        self.write(
            "fantasy-management/generated/operations/player-signals.json",
            {"schema_version": 1, "dataset_id": "player-signals", "generated_at": NOW, "input_fingerprint": "a" * 64, "players": players, "quality": {"status": "ok"}},
        )
        self.write(
            "fantasy-management/automation/fa-board-materialization.json",
            {
                "schema_version": 1,
                "materialization_id": "fantasy-operations-fa-board-materialization",
                "managed_team": {"team_id": 1},
                "sources": {
                    "player_signals": "fantasy-management/generated/operations/player-signals.json",
                    "league": "public/data/League.json",
                    "drafts": "public/data/Drafts.json",
                    "timestamps": "public/data/Timestamps.json",
                },
                "output": {"fa_board_readmodel": "fantasy-management/generated/operations/fa-board-readmodel.json"},
            },
        )

    def write(self, path: str, value: object) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def build(self) -> dict:
        return MODULE.build(self.root, self.config)


def row(result: dict, pid: str) -> dict:
    return next(item for item in result["players"] if item["player_id"] == pid)


class FaBoardReadmodelTests(unittest.TestCase):
    def run_fixture(self, players: list[dict], league_data: dict, draft_data: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            return Fixture(Path(tmp), players, league_data, draft_data).build()

    def test_opponent_rostered_and_taxi_buckets_block_availability(self) -> None:
        result = self.run_fixture(
            [player("opp", "Opponent"), player("taxi", "Taxi Rookie", years=0)],
            league(managed_roster=["taxi"], managed_taxi=["taxi"], opponent_roster=["opp"]),
            draft(),
        )
        self.assertEqual("rostered", row(result, "opp")["availability_status"])
        self.assertEqual("2", row(result, "opp")["owner_team_id"])
        self.assertEqual("Taxi", row(result, "taxi")["roster_bucket"])

    def test_unmaterialized_picked_player_is_drafted(self) -> None:
        result = self.run_fixture([player("picked", "Picked")], league(), draft([pick("picked", 2)]))
        self.assertEqual("drafted", row(result, "picked")["availability_status"])
        self.assertEqual("picked", row(result, "picked")["current_fa_draft_status"])
        self.assertEqual("deferred", result["current_fa_draft"]["materialization_mode"])

    def test_reserve_eligible_player_uses_zero_materialization_slot(self) -> None:
        result = self.run_fixture([player("ir", "IR Stash", designation="IR")], league(), draft())
        stash = row(result, "ir")
        self.assertTrue(stash["reserve_eligible_now"])
        self.assertEqual(0, stash["active_slot_cost_on_materialization"])
        self.assertEqual(0, stash["active_slot_cost_now"])

    def test_out_status_respects_current_reserve_setting(self) -> None:
        result = self.run_fixture([player("out", "Out", designation="OUT")], league(), draft())
        self.assertTrue(row(result, "out")["reserve_eligible_now"])

    def test_rookie_taxi_prelock_is_current_capacity(self) -> None:
        result = self.run_fixture([player("rookie", "Rookie", years=0)], league(reserve_slots=0, taxi_slots=1), draft())
        rookie = row(result, "rookie")
        self.assertTrue(rookie["taxi_prelock_eligible"])
        self.assertTrue(rookie["taxi_eligible_now"])
        self.assertEqual(0, rookie["active_slot_cost_on_materialization"])

    def test_pending_own_stash_consumes_special_capacity(self) -> None:
        result = self.run_fixture(
            [player("pending", "Pending", designation="IR"), player("candidate", "Candidate", designation="IR")],
            league(reserve_slots=1, taxi_slots=0),
            draft([pick("pending", 1)]),
        )
        self.assertEqual(1, result["managed_team_capacity"]["pending_controlled_draft_count"])
        self.assertEqual(1, row(result, "candidate")["active_slot_cost_on_materialization"])
        self.assertEqual(0, row(result, "candidate")["active_slot_cost_now"])

    def test_materialized_vs_deferred_draft_changes_current_slot_cost(self) -> None:
        deferred = self.run_fixture([player("seed", "Seed"), player("candidate", "Candidate")], league(), draft([pick("seed", 2)]))
        self.assertEqual(1, row(deferred, "candidate")["active_slot_cost_on_materialization"])
        self.assertEqual(0, row(deferred, "candidate")["active_slot_cost_now"])

        materialized = self.run_fixture([player("seed", "Seed"), player("candidate", "Candidate")], league(opponent_roster=["seed"]), draft([pick("seed", 2)]))
        self.assertEqual("materialized", materialized["current_fa_draft"]["materialization_mode"])
        self.assertEqual(1, row(materialized, "candidate")["active_slot_cost_now"])

    def test_incomplete_negative_ownership_fails_closed(self) -> None:
        result = self.run_fixture([player("unknown", "Unknown")], league(incomplete_opponent=True), draft())
        self.assertEqual("unknown", row(result, "unknown")["availability_status"])
        self.assertFalse(result["sources"]["league"]["complete_for_negative_ownership"])
        self.assertEqual("error", result["quality"]["status"])

    def test_missing_current_fa_draft_during_draft_phase_fails_closed(self) -> None:
        result = self.run_fixture([player("unknown", "Unknown")], league(), [])
        self.assertEqual("unknown", row(result, "unknown")["availability_status"])
        self.assertEqual("unknown", result["current_fa_draft"]["resolution_status"])

    def test_market_is_compact_and_schema_validates(self) -> None:
        result = self.run_fixture([player("market", "Market")], league(), draft())
        fantasycalc = row(result, "market")["market"]["fantasycalc"]
        self.assertEqual(6500, fantasycalc["value"])
        self.assertEqual("current", fantasycalc["freshness_status"])
        self.assertNotIn("signals", fantasycalc)
        schema_path = Path(__file__).resolve().parents[2] / "schemas/fa-board-readmodel.schema.json"
        Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(result)


if __name__ == "__main__":
    unittest.main()
