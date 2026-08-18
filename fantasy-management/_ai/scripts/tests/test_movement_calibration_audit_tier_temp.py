from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path


class MovementCalibrationTierAuditTemp(unittest.TestCase):
    def test_print_tier_and_fantasycalc_audit(self) -> None:
        root = Path(__file__).resolve().parents[4]
        scripts = root / "fantasy-management/_ai/scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import build_free_agent_movement_dataset as movement

        config = movement.load_json(root / "fantasy-management/automation/free-agent-movement-materialization.json")
        windows = sorted(config["comparison_windows_days"])
        thresholds = movement._load_thresholds(root, config)
        free_agents = movement.load_json(root / config["source"]["free_agent_signals"])
        players = movement.load_json(root / config["source"]["player_signals"])
        league = movement.load_json(root / config["source"]["league"])
        current_movement = movement.load_json(root / config["output"]["free_agent_movement_signals"])

        catalog, _ = movement._load_merged_catalog(root, config)
        histories = {
            definition["source_id"]: movement._build_source_history(root, definition, windows)
            for definition in catalog["sources"]
            if definition.get("active")
        }
        fp_history = next(
            history for history in histories.values()
            if str(history.definition.get("provider") or "").casefold() == "fantasypros"
            and history.definition.get("source_kind") == "expert_consensus"
        )
        fc_history = next(
            history for history in histories.values()
            if str(history.definition.get("provider") or "").casefold() == "fantasycalc"
            and history.definition.get("source_kind") == "market_value"
        )
        replacement_cfg = config["replacement_relevance"]
        boundaries = movement._replacement_boundaries(
            players.get("players") or [], float(replacement_cfg["owned_boundary_quantile"])
        )
        scoring = league.get("ScoringType") if isinstance(league.get("ScoringType"), dict) else {}

        numeric_by_window = {w: set() for w in windows}
        numeric_by_family_window = {
            f: {w: set() for w in windows}
            for f in ("redraft_adp", "dynasty_market", "season_projection")
        }
        numeric_player_crossings = {}
        tier_by_window = {w: set() for w in windows}
        tier_transitions = {w: Counter() for w in windows}
        tier_small_rank_moves = {
            w: Counter({"lt5": 0, "lt10": 0, "lt20": 0, "gte20": 0, "rank_unavailable": 0})
            for w in windows
        }
        tier_current_distribution = Counter()
        fc_rows = []

        for player in free_agents.get("players") or []:
            if not isinstance(player, dict):
                continue
            position = str(player.get("position") or "").upper()
            if position not in movement.POSITIONS:
                continue
            pid = str(player.get("player_id"))
            replacement = movement._replacement_relevance(
                player, boundaries, float(replacement_cfg["near_distance_percentile_points"])
            )
            adp, adp_crossed, _, _ = movement._adp_movement(
                player, movement._primary_adp_source(histories, position), windows, thresholds["adp"]
            )
            market, market_crossed, _, _ = movement._market_movement(
                player, movement._market_histories(histories, position), windows, thresholds["market"]
            )
            projections, projection_crossed, _, _ = movement._projection_movement(
                player, movement._projection_histories(histories, position), windows, thresholds["projections"], scoring
            )
            numeric_crossed = adp_crossed + projection_crossed + [
                item for item in market_crossed if item.get("kind") != "tier_change"
            ]
            numeric_player_crossings[pid] = numeric_crossed
            for item in numeric_crossed:
                w = int(item["window_days"])
                family = str(item["family"])
                numeric_by_window[w].add(pid)
                numeric_by_family_window[family][w].add(pid)

            fp_cur = movement._eval(player, fp_history.current)
            fp_sig = fp_cur.get("signals") or {}
            if fp_cur.get("listed"):
                tier_current_distribution[str(fp_sig.get("tier"))] += 1
            for w in windows:
                baseline_source = fp_history.baselines.get(w)
                if baseline_source is None:
                    continue
                fp_old = movement._eval(player, baseline_source)
                if not fp_cur.get("listed") or not fp_old.get("listed"):
                    continue
                old_sig = fp_old.get("signals") or {}
                cur_tier = movement.ops.optional_text(fp_sig.get("tier"))
                old_tier = movement.ops.optional_text(old_sig.get("tier"))
                if cur_tier == old_tier:
                    continue
                tier_by_window[w].add(pid)
                tier_transitions[w][f"{old_tier}->{cur_tier}"] += 1
                rank_delta = movement._numeric_delta(fp_sig.get("overall_rank"), old_sig.get("overall_rank"))
                if rank_delta is None:
                    tier_small_rank_moves[w]["rank_unavailable"] += 1
                else:
                    magnitude = abs(float(rank_delta))
                    if magnitude < 5:
                        tier_small_rank_moves[w]["lt5"] += 1
                    if magnitude < 10:
                        tier_small_rank_moves[w]["lt10"] += 1
                    if magnitude < 20:
                        tier_small_rank_moves[w]["lt20"] += 1
                    else:
                        tier_small_rank_moves[w]["gte20"] += 1

            fc_cur = movement._eval(player, fc_history.current)
            if not fc_cur.get("listed"):
                continue
            fc_sig = fc_cur.get("signals") or {}
            market_numeric = [item for item in market_crossed if item.get("kind") != "tier_change"]
            market_tier = [item for item in market_crossed if item.get("kind") == "tier_change"]
            row = {
                "player_id": pid,
                "name": player.get("name"),
                "position": position,
                "replacement": replacement.get("classification"),
                "current_value": movement.ops.optional_number(fc_sig.get("value")),
                "current_percentile": movement.ops.optional_number(fc_sig.get("percentile")),
                "has_existing_market_numeric": bool(market_numeric),
                "has_existing_any_numeric": bool(numeric_crossed),
                "has_existing_tier_change": bool(market_tier),
                "windows": {},
            }
            for w in windows:
                baseline_source = fc_history.baselines.get(w)
                baseline = movement._eval(player, baseline_source) if baseline_source is not None else None
                old_sig = (baseline or {}).get("signals") or {}
                delta_pct = movement._numeric_delta(fc_sig.get("percentile"), old_sig.get("percentile"))
                delta_value = movement._numeric_delta(fc_sig.get("value"), old_sig.get("value"))
                old_value = movement.ops.optional_number(old_sig.get("value"))
                value_pct = None
                if delta_value is not None and old_value not in (None, 0):
                    value_pct = round((delta_value / float(old_value)) * 100, 2)
                row["windows"][str(w)] = {
                    "delta_percentile": delta_pct,
                    "delta_value": delta_value,
                    "value_percent_change": value_pct,
                }
            fc_rows.append(row)

        numeric_earliest = Counter()
        numeric_slow = set()
        for pid, items in numeric_player_crossings.items():
            ws = sorted({int(item["window_days"]) for item in items})
            if not ws:
                continue
            numeric_earliest[ws[0]] += 1
            if 1 not in ws and any(w > 1 for w in ws):
                numeric_slow.add(pid)

        current_composition = Counter()
        for discovery in current_movement.get("discoveries") or []:
            materiality = discovery.get("materiality") if isinstance(discovery.get("materiality"), dict) else {}
            thresholds_crossed = [item for item in materiality.get("thresholds_crossed") or [] if isinstance(item, dict)]
            kinds = {str(item.get("kind")) for item in thresholds_crossed}
            numeric = {k for k in kinds if k != "tier_change" and k not in {"injury_flag_change", "injury_designation_change", "return_timeline_change", "nfl_team_change", "depth_chart_order_change", "depth_chart_position_change"}}
            structural = {str(item.get("family")) for item in thresholds_crossed} & {"injury_availability", "team_transaction", "role_opportunity"}
            reasons = set(str(value) for value in materiality.get("reasons") or [])
            if "tier_change" in kinds:
                current_composition["has_tier_change"] += 1
            if numeric:
                current_composition["has_numeric_threshold"] += 1
            if kinds == {"tier_change"}:
                current_composition["tier_change_only_threshold"] += 1
            if structural:
                current_composition["has_structural_threshold"] += 1
            if "activity_near_replacement_boundary" in reasons:
                current_composition["has_activity_reason"] += 1
            if "relevant_source_coverage_change" in reasons:
                current_composition["has_coverage_reason"] += 1
            if not thresholds_crossed:
                current_composition["no_threshold_crossed"] += 1

        def fc_grid(kind: str, threshold: float, abs_value_min: float = 0.0):
            candidates = []
            for row in fc_rows:
                qualifying = []
                for w in windows:
                    data = row["windows"][str(w)]
                    if kind == "percentile":
                        value = data.get("delta_percentile")
                        if isinstance(value, (int, float)) and abs(float(value)) >= threshold:
                            qualifying.append((w, float(value)))
                    else:
                        pct = data.get("value_percent_change")
                        delta = data.get("delta_value")
                        if isinstance(pct, (int, float)) and isinstance(delta, (int, float)) and abs(float(pct)) >= threshold and abs(float(delta)) >= abs_value_min:
                            qualifying.append((w, float(pct), float(delta)))
                if qualifying:
                    candidates.append((row, qualifying))
            near = [x for x in candidates if x[0]["replacement"] in {"near_rostered_boundary", "at_or_above_rostered_boundary"}]
            return {
                "all": len(candidates),
                "near_or_above": len(near),
                "without_existing_market_numeric": sum(not x[0]["has_existing_market_numeric"] for x in candidates),
                "without_existing_market_numeric_near_or_above": sum((not x[0]["has_existing_market_numeric"]) and x[0]["replacement"] in {"near_rostered_boundary", "at_or_above_rostered_boundary"} for x in candidates),
                "without_any_existing_numeric": sum(not x[0]["has_existing_any_numeric"] for x in candidates),
                "tier_only_market_signal": sum((not x[0]["has_existing_market_numeric"]) and x[0]["has_existing_tier_change"] for x in candidates),
            }

        fc_percentile_grid = {str(t): fc_grid("percentile", t) for t in (5, 7.5, 10, 12.5, 15)}
        fc_value_grid = {
            f"pct{pct}_abs{abs_min}": fc_grid("value", pct, abs_min)
            for pct, abs_min in ((15, 100), (20, 100), (20, 250), (25, 250), (30, 250), (30, 500), (40, 500))
        }

        top_fc = []
        for row in fc_rows:
            if row["has_existing_market_numeric"]:
                continue
            best_pct = None
            best_w = None
            best_value_pct = None
            best_value_delta = None
            for w in windows:
                data = row["windows"][str(w)]
                pct = data.get("delta_percentile")
                if isinstance(pct, (int, float)) and (best_pct is None or abs(float(pct)) > abs(best_pct)):
                    best_pct = float(pct)
                    best_w = w
                vp = data.get("value_percent_change")
                vd = data.get("delta_value")
                if isinstance(vp, (int, float)) and (best_value_pct is None or abs(float(vp)) > abs(best_value_pct)):
                    best_value_pct = float(vp)
                    best_value_delta = float(vd) if isinstance(vd, (int, float)) else None
            if best_pct is None:
                continue
            top_fc.append({
                "name": row["name"], "position": row["position"], "replacement": row["replacement"],
                "current_value": row["current_value"], "current_percentile": row["current_percentile"],
                "max_percentile_delta": best_pct, "window": best_w,
                "max_value_percent_change": best_value_pct, "value_delta_at_max_pct_change": best_value_delta,
                "has_existing_any_numeric": row["has_existing_any_numeric"],
                "has_existing_tier_change": row["has_existing_tier_change"],
            })
        top_fc.sort(key=lambda x: (0 if x["replacement"] in {"near_rostered_boundary", "at_or_above_rostered_boundary"} else 1, -abs(x["max_percentile_delta"])))

        report = {
            "numeric_hard_players_by_window_excluding_tier": {str(w): len(numeric_by_window[w]) for w in windows},
            "numeric_hard_players_by_family_window_excluding_tier": {f: {str(w): len(v[w]) for w in windows} for f, v in numeric_by_family_window.items()},
            "numeric_earliest_visible_window": {str(w): numeric_earliest[w] for w in windows},
            "numeric_no_1d_but_longer": len(numeric_slow),
            "tier_change_players_by_window": {str(w): len(tier_by_window[w]) for w in windows},
            "tier_change_rank_magnitude": {str(w): dict(tier_small_rank_moves[w]) for w in windows},
            "tier_top_transitions": {str(w): tier_transitions[w].most_common(12) for w in windows},
            "tier_current_distribution": dict(tier_current_distribution.most_common()),
            "current_discovery_composition": dict(current_composition),
            "fantasycalc_percentile_grid_vs_numeric_market": fc_percentile_grid,
            "fantasycalc_value_grid_vs_numeric_market": fc_value_grid,
            "fantasycalc_top_without_existing_market_numeric": top_fc[:30],
        }
        print("CALIBRATION_TIER_AUDIT_JSON=" + json.dumps(report, separators=(",", ":"), sort_keys=True))
        self.assertGreater(len(fc_rows), 0)
        self.assertGreater(sum(len(v) for v in tier_by_window.values()), 0)


if __name__ == "__main__":
    unittest.main()
