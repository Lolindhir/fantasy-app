from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_free_agent_movement_dataset.py"
SPEC = importlib.util.spec_from_file_location("build_free_agent_movement_dataset", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FreeAgentMovementDatasetTests(unittest.TestCase):
    def write_json(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def write_csv(self, root: Path, relative: str, rows: list[dict[str, object]]) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def player(self, player_id: str, position: str, ownership: str, *, market=None, adp=None, projection=None, depth=1) -> dict:
        return {
            "player_id": player_id,
            "name": player_id,
            "position": position,
            "nfl_team": "AAA",
            "population_reasons": ["has_nfl_team"],
            "ownership": {"status": ownership, "teams": []},
            "app_data": {"espn_id": None},
            "injury": {"is_injured": False, "designation": None, "return_date": None},
            "role": {"sleeper_depth_chart_position": position, "sleeper_depth_chart_order": depth},
            "source_signals": {},
            "market": {"fantasypros": {"listed": True, "percentile": market}} if market is not None else {},
            "redraft_adp": {"primary": {"listed": True, "percentile": adp} if adp is not None else None},
            "projections": {"providers": {}, "summary": {"consensus_percentile": projection, "listed_provider_count": 1 if projection is not None else 0}},
            "activity": {"listed": False, "add": {"rank": None, "count": None}, "drop": {"rank": None, "count": None}},
        }

    def source(self, source_id: str, kind: str, position: str, section: str, signals: list[str], *, primary=False) -> dict:
        return {
            "source_id": source_id,
            "active": True,
            "source_kind": kind,
            "provider": source_id,
            "dataset_id": source_id,
            "access": {"type": "repo_latest_pointer", "location": f"sources/{source_id}/latest.json", "ranking_path_field": "ranking_file", "timestamp_fields": ["ranking_fetched_at", "snapshot_date"]},
            "applicability": {"entity_types": ["player"], "positions": [position]},
            "absence_policy": {"inapplicable": "not_applicable", "missing": "not_listed", "ambiguous": "ambiguous_join"},
            "join": {"strategies": [{"type": "id", "method": "player_id", "player_field": "ID", "source_field": "player_id"}]},
            "output": {"section": section, "key": source_id, "signals": [{"target": signal, "source_field": signal, "type": "text" if signal == "tier" else "number"} for signal in signals]},
            "roles": {"primary_for_positions": [position]} if primary else {},
            "quality": {"minimum_rows": 1, "missing_severity": "none", "ambiguous_severity": "warning", "row_count_severity": "error"},
            "freshness": {"max_age_hours": 72},
            "format_context": {"position_scope": position},
        }

    def snapshots(self, root: Path, source_id: str, current: dict[str, object], baseline: dict[str, object]) -> None:
        current_path = f"sources/{source_id}/snapshots/2026-08-16/ranking.csv"
        baseline_path = f"sources/{source_id}/snapshots/2026-08-09/ranking.csv"
        self.write_csv(root, current_path, [current])
        self.write_csv(root, baseline_path, [baseline])
        self.write_json(root, f"sources/{source_id}/latest.json", {"snapshot_date": "2026-08-16", "ranking_fetched_at": "2026-08-16T05:00:00Z", "ranking_file": current_path})

    def profiles(self, root: Path) -> dict[str, str]:
        refs = {"redraft_adp": "profiles/adp.json", "market": "profiles/market.json", "projections": "profiles/projections.json", "kicker": "profiles/kicker.json"}
        self.write_json(root, refs["redraft_adp"], {"criteria": [
            {"id": "primary-percentile-movement", "condition": {"all": [{"signal": "adp.primary_percentile", "operator": "absolute_delta_gte", "value": 10}, {"signal": "adp.primary_times_drafted", "operator": "gte", "value": 50}]}},
            {"id": "large-primary-percentile-movement", "condition": {"signal": "adp.primary_percentile", "operator": "absolute_delta_gte", "value": 20}},
        ]})
        self.write_json(root, refs["market"], {"criteria": [
            {"id": "overall-rank-movement", "condition": {"signal": "market.dynasty_overall_rank", "operator": "absolute_delta_gte", "value": 20}},
            {"id": "position-rank-movement", "condition": {"signal": "market.position_rank", "operator": "absolute_delta_gte", "value": 8}},
        ]})
        self.write_json(root, refs["projections"], {"criteria": [
            {"id": "material-consensus-movement", "condition": {"all": [{"signal": "projection.consensus_percentile", "operator": "absolute_delta_gte", "value": 10}, {"signal": "projection.provider_count", "operator": "gte", "value": 1}]}},
            {"id": "large-consensus-movement", "condition": {"signal": "projection.consensus_percentile", "operator": "absolute_delta_gte", "value": 20}},
        ]})
        self.write_json(root, refs["kicker"], {"criteria": [
            {"id": "material-ffc-adp-movement", "condition": {"all": [{"signal": "kicker.ffc_percentile", "operator": "absolute_delta_gte", "value": 15}, {"signal": "kicker.ffc_times_drafted", "operator": "gte", "value": 50}]}},
            {"id": "material-projection-consensus-movement", "condition": {"all": [{"signal": "kicker.projection_consensus_percentile", "operator": "absolute_delta_gte", "value": 15}, {"signal": "kicker.projection_provider_count", "operator": "gte", "value": 2}]}},
        ]})
        return refs

    def fixture(self, root: Path) -> tuple[Path, Path]:
        rostered = [
            self.player("rostered-wr", "WR", "mighty_giants", market=60, adp=55, projection=58),
            self.player("rostered-k", "K", "opponent_rostered", adp=55, projection=55),
        ]
        wr = self.player("fa-wr", "WR", "fantasy_free_agent", market=65, adp=62, projection=66, depth=1)
        kicker = self.player("fa-k", "K", "fantasy_free_agent", adp=58, projection=58)
        self.write_json(root, "generated/player-signals.json", {"schema_version": 1, "dataset_id": "player-signals", "generated_at": "2026-08-16T06:30:00Z", "input_fingerprint": "a" * 64, "players": rostered + [wr, kicker], "quality": {"status": "ok", "issue_count": 0, "issues": []}})
        self.write_json(root, "generated/free-agent-signals.json", {"schema_version": 1, "dataset_id": "free-agent-signals", "generated_at": "2026-08-16T06:30:00Z", "input_fingerprint": "b" * 64, "players": [wr, kicker], "quality": {"status": "ok", "source_quality_status": "ok", "source_issue_count": 0, "selection_count_matches_source": True}})
        previous = root / "generated/free-agent-signals.previous.json"
        self.write_json(root, "generated/free-agent-signals.previous.json", {"schema_version": 1, "dataset_id": "free-agent-signals", "generated_at": "2026-08-15T06:30:00Z", "input_fingerprint": "c" * 64, "players": [self.player("fa-wr", "WR", "fantasy_free_agent", depth=3), self.player("fa-k", "K", "fantasy_free_agent")], "quality": {"status": "ok"}})
        self.write_json(root, "league.json", {"ScoringType": {}})

        definitions = [
            self.source("wr-adp", "adp", "WR", "redraft_adp", ["rank", "percentile", "adp", "times_drafted"], primary=True),
            self.source("k-adp", "adp", "K", "redraft_adp", ["rank", "percentile", "adp", "times_drafted"], primary=True),
            self.source("wr-market", "expert_consensus", "WR", "market", ["overall_rank", "position_rank", "percentile", "tier"]),
            self.source("wr-proj", "projection", "WR", "projections", ["rank", "percentile"]),
            self.source("k-proj-a", "projection", "K", "projections", ["rank", "percentile"]),
            self.source("k-proj-b", "projection", "K", "projections", ["rank", "percentile"]),
        ]
        self.write_json(root, "catalog.json", {"schema_version": 1, "catalog_id": "test", "sources": definitions})
        self.snapshots(root, "wr-adp", {"player_id": "fa-wr", "rank": 40, "percentile": 75, "adp": 40, "times_drafted": 100}, {"player_id": "fa-wr", "rank": 70, "percentile": 55, "adp": 70, "times_drafted": 100})
        self.snapshots(root, "k-adp", {"player_id": "fa-k", "rank": 8, "percentile": 70, "adp": 150, "times_drafted": 100}, {"player_id": "fa-k", "rank": 15, "percentile": 50, "adp": 170, "times_drafted": 100})
        self.snapshots(root, "wr-market", {"player_id": "fa-wr", "overall_rank": 60, "position_rank": 25, "percentile": 68, "tier": 5}, {"player_id": "fa-wr", "overall_rank": 90, "position_rank": 35, "percentile": 48, "tier": 6})
        self.snapshots(root, "wr-proj", {"player_id": "fa-wr", "rank": 20, "percentile": 72}, {"player_id": "fa-wr", "rank": 40, "percentile": 52})
        self.snapshots(root, "k-proj-a", {"player_id": "fa-k", "rank": 5, "percentile": 72}, {"player_id": "fa-k", "rank": 12, "percentile": 52})
        self.snapshots(root, "k-proj-b", {"player_id": "fa-k", "rank": 6, "percentile": 68}, {"player_id": "fa-k", "rank": 13, "percentile": 48})

        config = root / "config.json"
        self.write_json(root, "config.json", {
            "schema_version": 1,
            "source": {"free_agent_signals": "generated/free-agent-signals.json", "player_signals": "generated/player-signals.json", "league": "league.json", "source_catalog": "catalog.json", "source_catalog_extensions": []},
            "materiality_profiles": self.profiles(root),
            "comparison_windows_days": [7],
            "cross_signal": {"minimum_percentile_delta_points": 5},
            "replacement_relevance": {"owned_boundary_quantile": 0.1, "near_distance_percentile_points": 10},
            "activity": {"near_replacement_top_n": 20},
            "output": {"free_agent_movement_signals": "generated/movement.json"},
        })
        return config, previous

    def test_wr_and_kicker_share_one_discovery_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config, previous = self.fixture(Path(directory))
            result = MODULE.build(Path(directory), config, previous)
            by_id = {item["player_id"]: item for item in result["discoveries"]}
            self.assertEqual(set(by_id), {"fa-wr", "fa-k"})
            self.assertEqual(by_id["fa-wr"]["materiality"]["research_priority"], "high")
            self.assertEqual(by_id["fa-k"]["materiality"]["research_priority"], "high")
            self.assertIn("redraft_adp", by_id["fa-k"]["materiality"]["material_families"])
            self.assertIn("season_projection", by_id["fa-k"]["materiality"]["material_families"])
            kicker_thresholds = [x["threshold"] for x in by_id["fa-k"]["materiality"]["thresholds_crossed"] if x["family"] == "redraft_adp"]
            self.assertIn(15, kicker_thresholds)
            self.assertIn("depth_chart_order_change", {x["kind"] for x in by_id["fa-wr"]["movement"]["structural_day_over_day"]["changes"]})
            self.assertEqual(set(result["population"]["positions"]), {"QB", "RB", "WR", "TE", "K"})

    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = SCRIPT_PATH.parents[3]
        result = MODULE.build(root, root / "fantasy-management/automation/free-agent-movement-materialization.json")
        schema = json.loads((root / "fantasy-management/_ai/schemas/free-agent-movement-dataset.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)
        self.assertGreater(result["population"]["free_agent_count"], 0)
        self.assertTrue(all(item["ownership"]["status"] == "fantasy_free_agent" for item in result["discoveries"]))

    def test_production_workflow_materializes_after_free_agents(self) -> None:
        root = SCRIPT_PATH.parents[3]
        workflow = (root / ".github/workflows/materialize-fantasy-operations-inputs.yml").read_text(encoding="utf-8")
        free_agent = "python fantasy-management/_ai/scripts/build_free_agent_dataset.py"
        movement = "python fantasy-management/_ai/scripts/build_free_agent_movement_dataset.py"
        self.assertLess(workflow.index(free_agent), workflow.index(movement))
        self.assertIn("free-agent-signals.previous.json", workflow)
        self.assertIn("fantasy-management/generated/operations/free-agent-movement-signals.json", workflow)


if __name__ == "__main__":
    unittest.main()
