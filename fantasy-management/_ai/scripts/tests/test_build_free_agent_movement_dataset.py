from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_free_agent_movement_dataset.py"
SPEC = importlib.util.spec_from_file_location("build_free_agent_movement_dataset", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
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
        fieldnames = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def player(
        self,
        player_id: str,
        name: str,
        position: str,
        ownership_status: str,
        *,
        market_percentile: float | None = None,
        adp_percentile: float | None = None,
        projection_percentile: float | None = None,
        depth_order: int | None = 1,
    ) -> dict:
        market = {}
        if market_percentile is not None:
            market["fantasypros"] = {"listed": True, "percentile": market_percentile}
        primary = None
        if adp_percentile is not None:
            primary = {"listed": True, "percentile": adp_percentile}
        return {
            "player_id": player_id,
            "name": name,
            "position": position,
            "nfl_team": "AAA",
            "population_reasons": ["has_nfl_team"],
            "ownership": {"status": ownership_status, "teams": []},
            "app_data": {
                "status": "Active",
                "age": 25,
                "years_experience": 2,
                "salary": 5,
                "salary_projected": 6,
                "is_free_agent_source_field": False,
                "espn_id": None,
            },
            "injury": {
                "coverage_status": "no_current_injury_signal",
                "is_injured": False,
                "designation": None,
                "description": None,
                "reported_date": None,
                "return_date": None,
            },
            "role": {
                "sleeper_depth_chart_position": position,
                "sleeper_depth_chart_order": depth_order,
                "coverage_status": "available",
                "interpretation": "nominal_depth_chart_only_not_usage",
            },
            "source_signals": {},
            "market": market,
            "redraft_adp": {
                "primary": primary,
                "primary_listed": bool(primary),
                "formats": {},
            },
            "projections": {
                "providers": {},
                "summary": {
                    "consensus_percentile": projection_percentile,
                    "listed_provider_count": 1 if projection_percentile is not None else 0,
                    "percentile_spread": None,
                },
            },
            "activity": {
                "listed": False,
                "add": {"status": "not_listed", "rank": None, "count": None},
                "drop": {"status": "not_listed", "rank": None, "count": None},
            },
        }

    def source_definition(
        self,
        source_id: str,
        source_kind: str,
        dataset_id: str,
        position: str,
        section: str,
        key: str,
        signals: list[str],
        *,
        primary: bool = False,
    ) -> dict:
        return {
            "source_id": source_id,
            "active": True,
            "source_kind": source_kind,
            "provider": source_id,
            "dataset_id": dataset_id,
            "access": {
                "type": "repo_latest_pointer",
                "location": f"sources/{source_id}/latest.json",
                "ranking_path_field": "ranking_file",
                "timestamp_fields": ["ranking_fetched_at", "snapshot_date"],
            },
            "applicability": {"entity_types": ["player"], "positions": [position]},
            "absence_policy": {"inapplicable": "not_applicable", "missing": "not_listed", "ambiguous": "ambiguous_join"},
            "join": {"strategies": [{"type": "id", "method": "player_id", "player_field": "ID", "source_field": "player_id"}]},
            "output": {
                "section": section,
                "key": key,
                "signals": [
                    {"target": signal, "source_field": signal, "type": "number" if signal not in {"tier"} else "text"}
                    for signal in signals
                ],
            },
            "roles": {"primary_for_positions": [position]} if primary else {},
            "quality": {"minimum_rows": 1, "missing_severity": "none", "ambiguous_severity": "warning", "row_count_severity": "error"},
            "freshness": {"max_age_hours": 72},
            "format_context": {"position_scope": position, "horizon": "redraft" if section != "market" else "dynasty"},
        }

    def write_source_snapshots(
        self,
        root: Path,
        source_id: str,
        current_rows: list[dict[str, object]],
        previous_rows: list[dict[str, object]],
    ) -> None:
        current_path = f"sources/{source_id}/snapshots/2026-08-16/ranking.csv"
        previous_path = f"sources/{source_id}/snapshots/2026-08-09/ranking.csv"
        self.write_csv(root, current_path, current_rows)
        self.write_csv(root, previous_path, previous_rows)
        self.write_json(
            root,
            f"sources/{source_id}/latest.json",
            {
                "snapshot_date": "2026-08-16",
                "ranking_fetched_at": "2026-08-16T05:00:00Z",
                "ranking_file": current_path,
            },
        )

    def write_profiles(self, root: Path) -> dict[str, str]:
        refs = {
            "redraft_adp": "profiles/adp.json",
            "market": "profiles/market.json",
            "projections": "profiles/projections.json",
            "kicker": "profiles/kicker.json",
        }
        self.write_json(
            root,
            refs["redraft_adp"],
            {
                "id": "redraft-adp-movement",
                "criteria": [
                    {"id": "primary-percentile-movement", "condition": {"all": [
                        {"signal": "adp.primary_percentile", "operator": "absolute_delta_gte", "value": 10},
                        {"signal": "adp.primary_times_drafted", "operator": "gte", "value": 50}
                    ]}},
                    {"id": "large-primary-percentile-movement", "condition": {"signal": "adp.primary_percentile", "operator": "absolute_delta_gte", "value": 20}},
                ],
            },
        )
        self.write_json(
            root,
            refs["market"],
            {
                "id": "market-movement",
                "criteria": [
                    {"id": "overall-rank-movement", "condition": {"signal": "market.dynasty_overall_rank", "operator": "absolute_delta_gte", "value": 20}},
                    {"id": "position-rank-movement", "condition": {"signal": "market.position_rank", "operator": "absolute_delta_gte", "value": 8}},
                ],
            },
        )
        self.write_json(
            root,
            refs["projections"],
            {
                "id": "season-projection-movement",
                "criteria": [
                    {"id": "material-consensus-movement", "condition": {"all": [
                        {"signal": "projection.consensus_percentile", "operator": "absolute_delta_gte", "value": 10},
                        {"signal": "projection.provider_count", "operator": "gte", "value": 1}
                    ]}},
                    {"id": "large-consensus-movement", "condition": {"signal": "projection.consensus_percentile", "operator": "absolute_delta_gte", "value": 20}},
                ],
            },
        )
        self.write_json(
            root,
            refs["kicker"],
            {
                "id": "kicker-signal-movement",
                "criteria": [
                    {"id": "material-ffc-adp-movement", "condition": {"all": [
                        {"signal": "kicker.ffc_percentile", "operator": "absolute_delta_gte", "value": 15},
                        {"signal": "kicker.ffc_times_drafted", "operator": "gte", "value": 50}
                    ]}},
                    {"id": "material-projection-consensus-movement", "condition": {"all": [
                        {"signal": "kicker.projection_consensus_percentile", "operator": "absolute_delta_gte", "value": 15},
                        {"signal": "kicker.projection_provider_count", "operator": "gte", "value": 2}
                    ]}},
                ],
            },
        )
        return refs

    def prepare_root(self, root: Path) -> tuple[Path, Path]:
        rostered = [
            self.player("r1", "Roster WR 1", "WR", "mighty_giants", market_percentile=60, adp_percentile=55, projection_percentile=58),
            self.player("r2", "Roster WR 2", "WR", "opponent_rostered", market_percentile=70, adp_percentile=65, projection_percentile=68),
            self.player("k1", "Roster K 1", "K", "mighty_giants", adp_percentile=55, projection_percentile=55),
            self.player("k2", "Roster K 2", "K", "opponent_rostered", adp_percentile=65, projection_percentile=65),
        ]
        wr = self.player("fa-wr", "Rising WR", "WR", "fantasy_free_agent", market_percentile=65, adp_percentile=62, projection_percentile=66, depth_order=1)
        kicker = self.player("fa-k", "Rising K", "K", "fantasy_free_agent", adp_percentile=58, projection_percentile=58, depth_order=1)
        all_players = rostered + [wr, kicker]
        self.write_json(
            root,
            "generated/player-signals.json",
            {
                "schema_version": 1,
                "dataset_id": "player-signals",
                "generated_at": "2026-08-16T06:30:00Z",
                "input_fingerprint": "a" * 64,
                "players": all_players,
                "quality": {"status": "ok", "issue_count": 0, "issues": []},
            },
        )
        self.write_json(
            root,
            "generated/free-agent-signals.json",
            {
                "schema_version": 1,
                "dataset_id": "free-agent-signals",
                "generated_at": "2026-08-16T06:30:00Z",
                "input_fingerprint": "b" * 64,
                "players": [wr, kicker],
                "quality": {"status": "ok", "source_quality_status": "ok", "source_issue_count": 0, "selection_count_matches_source": True},
            },
        )
        previous_wr = self.player("fa-wr", "Rising WR", "WR", "fantasy_free_agent", depth_order=3)
        previous_k = self.player("fa-k", "Rising K", "K", "fantasy_free_agent", depth_order=1)
        previous_path = root / "generated/free-agent-signals.previous.json"
        self.write_json(
            root,
            "generated/free-agent-signals.previous.json",
            {
                "schema_version": 1,
                "dataset_id": "free-agent-signals",
                "generated_at": "2026-08-15T06:30:00Z",
                "input_fingerprint": "c" * 64,
                "players": [previous_wr, previous_k],
                "quality": {"status": "ok", "source_quality_status": "ok", "source_issue_count": 0, "selection_count_matches_source": True},
            },
        )
        self.write_json(root, "league.json", {"ScoringType": {}})

        definitions = [
            self.source_definition("wr-adp", "adp", "wr-adp", "WR", "redraft_adp", "ppr", ["rank", "percentile", "adp", "times_drafted"], primary=True),
            self.source_definition("k-adp", "adp", "k-adp", "K", "redraft_adp", "kicker", ["rank", "percentile", "adp", "times_drafted"], primary=True),
            self.source_definition("wr-market", "expert_consensus", "wr-market", "WR", "market", "fantasypros", ["overall_rank", "position_rank", "percentile", "tier"]),
            self.source_definition("wr-proj", "projection", "wr-proj", "WR", "projections", "projection", ["rank", "percentile"]),
            self.source_definition("k-proj-a", "projection", "k-proj-a", "K", "projections", "provider_a", ["rank", "percentile"]),
            self.source_definition("k-proj-b", "projection", "k-proj-b", "K", "projections", "provider_b", ["rank", "percentile"]),
        ]
        self.write_json(root, "catalog.json", {"schema_version": 1, "catalog_id": "test", "sources": definitions})

        self.write_source_snapshots(root, "wr-adp", [{"player_id": "fa-wr", "rank": 40, "percentile": 75, "adp": 40, "times_drafted": 100}], [{"player_id": "fa-wr", "rank": 70, "percentile": 55, "adp": 70, "times_drafted": 100}])
        self.write_source_snapshots(root, "k-adp", [{"player_id": "fa-k", "rank": 8, "percentile": 70, "adp": 150, "times_drafted": 100}], [{"player_id": "fa-k", "rank": 15, "percentile": 50, "adp": 170, "times_drafted": 100}])
        self.write_source_snapshots(root, "wr-market", [{"player_id": "fa-wr", "overall_rank": 60, "position_rank": 25, "percentile": 68, "tier": 5}], [{"player_id": "fa-wr", "overall_rank": 90, "position_rank": 35, "percentile": 48, "tier": 6}])
        self.write_source_snapshots(root, "wr-proj", [{"player_id": "fa-wr", "rank": 20, "percentile": 72}], [{"player_id": "fa-wr", "rank": 40, "percentile": 52}])
        self.write_source_snapshots(root, "k-proj-a", [{"player_id": "fa-k", "rank": 5, "percentile": 72}], [{"player_id": "fa-k", "rank": 12, "percentile": 52}])
        self.write_source_snapshots(root, "k-proj-b", [{"player_id": "fa-k", "rank": 6, "percentile": 68}], [{"player_id": "fa-k", "rank": 13, "percentile": 48}])

        refs = self.write_profiles(root)
        config_path = root / "config.json"
        self.write_json(
            root,
            "config.json",
            {
                "schema_version": 1,
                "materialization_id": "test",
                "source": {
                    "free_agent_signals": "generated/free-agent-signals.json",
                    "player_signals": "generated/player-signals.json",
                    "league": "league.json",
                    "source_catalog": "catalog.json",
                    "source_catalog_extensions": [],
                },
                "materiality_profiles": refs,
                "comparison_windows_days": [7],
                "cross_signal": {"minimum_percentile_delta_points": 5},
                "replacement_relevance": {"owned_boundary_quantile": 0.1, "near_distance_percentile_points": 10},
                "activity": {"near_replacement_top_n": 20},
                "output": {"free_agent_movement_signals": "generated/movement.json"},
            },
        )
        return config_path, previous_path

    def test_discovers_wr_and_kicker_in_same_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, previous_path = self.prepare_root(root)
            result = MODULE.build(root, config_path, previous_path)

            by_id = {item["player_id"]: item for item in result["discoveries"]}
            self.assertIn("fa-wr", by_id)
            self.assertIn("fa-k", by_id)
            self.assertEqual(by_id["fa-wr"]["materiality"]["research_priority"], "high")
            self.assertEqual(by_id["fa-k"]["materiality"]["research_priority"], "high")
            self.assertIn("K", result["population"]["positions"])
            self.assertIn("WR", result["population"]["positions"])
            self.assertIn("redraft_adp", by_id["fa-k"]["materiality"]["material_families"])
            self.assertIn("season_projection", by_id["fa-k"]["materiality"]["material_families"])
            structural_kinds = {
                change["kind"]
                for change in by_id["fa-wr"]["movement"]["structural_day_over_day"]["changes"]
            }
            self.assertIn("depth_chart_order_change", structural_kinds)

    def test_kicker_uses_kicker_specific_threshold_without_separate_population(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, previous_path = self.prepare_root(root)
            result = MODULE.build(root, config_path, previous_path)
            kicker = next(item for item in result["discoveries"] if item["player_id"] == "fa-k")
            adp_thresholds = [
                item["threshold"]
                for item in kicker["materiality"]["thresholds_crossed"]
                if item["family"] == "redraft_adp"
            ]
            self.assertIn(15, adp_thresholds)
            self.assertEqual(result["population"]["selection_rule"], "all current fantasy free agents QB/RB/WR/TE/K are evaluated; only research-relevant movement discoveries are emitted")

    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/free-agent-movement-materialization.json"
        schema_path = root / "fantasy-management/_ai/schemas/free-agent-movement-dataset.schema.json"
        result = MODULE.build(root, config_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)
        self.assertGreater(result["population"]["free_agent_count"], 0)
        self.assertEqual(set(result["population"]["positions"]), {"QB", "RB", "WR", "TE", "K"})
        self.assertTrue(all(item["ownership"]["status"] == "fantasy_free_agent" for item in result["discoveries"]))

    def test_production_workflow_materializes_movement_after_free_agents(self) -> None:
        root = SCRIPT_PATH.parents[3]
        workflow = (root / ".github/workflows/materialize-fantasy-operations-inputs.yml").read_text(encoding="utf-8")
        free_agent_command = "python fantasy-management/_ai/scripts/build_free_agent_dataset.py"
        movement_command = "python fantasy-management/_ai/scripts/build_free_agent_movement_dataset.py"
        self.assertIn("fantasy-management/automation/free-agent-movement-materialization.json", workflow)
        self.assertIn("fantasy-management/_ai/schemas/free-agent-movement-dataset.schema.json", workflow)
        self.assertIn("fantasy-management/_ai/scripts/tests/test_build_free_agent_movement_dataset.py", workflow)
        self.assertIn(movement_command, workflow)
        self.assertLess(workflow.index(free_agent_command), workflow.index(movement_command))
        self.assertIn("free-agent-signals.previous.json", workflow)
        self.assertIn("fantasy-management/generated/operations/free-agent-movement-signals.json", workflow)


if __name__ == "__main__":
    unittest.main()
