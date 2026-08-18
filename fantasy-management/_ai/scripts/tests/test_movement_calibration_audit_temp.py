from __future__ import annotations

import json
import math
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path


class MovementCalibrationAuditTemp(unittest.TestCase):
    def test_print_calibration_audit(self) -> None:
        root = Path(__file__).resolve().parents[4]
        scripts = root / "fantasy-management/_ai/scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))

        import build_free_agent_movement_dataset as movement

        config_path = root / "fantasy-management/automation/free-agent-movement-materialization.json"
        config = movement.load_json(config_path)
        windows = sorted(config["comparison_windows_days"])
        thresholds = movement._load_thresholds(root, config)
        free_agents = movement.load_json(root / config["source"]["free_agent_signals"])
        players = movement.load_json(root / config["source"]["player_signals"])
        league = movement.load_json(root / config["source"]["league"])
        current_movement = movement.load_json(
            root / config["output"]["free_agent_movement_signals"]
        )
        discovery_ids = {
            str(item.get("player_id"))
            for item in current_movement.get("discoveries") or []
            if isinstance(item, dict) and item.get("player_id") is not None
        }

        catalog, pending = movement._load_merged_catalog(root, config)
        histories = {}
        for definition in catalog["sources"]:
            if definition.get("active"):
                histories[definition["source_id"]] = movement._build_source_history(
                    root, definition, windows
                )

        history_coverage = {}
        for source_id, history in sorted(histories.items()):
            history_coverage[source_id] = {
                "provider": history.definition.get("provider"),
                "source_kind": history.definition.get("source_kind"),
                "current_snapshot_date": history.current_snapshot_date.isoformat(),
                "baseline_dates": {
                    str(window): history.baseline_dates.get(window) for window in windows
                },
            }

        replacement_cfg = config["replacement_relevance"]
        boundaries = movement._replacement_boundaries(
            players.get("players") or [], float(replacement_cfg["owned_boundary_quantile"])
        )
        scoring = league.get("ScoringType") if isinstance(league.get("ScoringType"), dict) else {}

        by_window = {window: set() for window in windows}
        by_family_window = {
            family: {window: set() for window in windows}
            for family in ("redraft_adp", "dynasty_market", "season_projection")
        }
        crossing_kind_counts = Counter()
        crossing_severity_counts = Counter()
        player_crossings = defaultdict(list)
        replacement_counts = Counter()
        position_counts = Counter()

        fc_records = []
        slow_examples = []
        free_agent_players = [
            item for item in (free_agents.get("players") or [])
            if isinstance(item, dict) and str(item.get("position") or "").upper() in movement.POSITIONS
        ]

        for player in free_agent_players:
            player_id = str(player.get("player_id"))
            position = str(player.get("position") or "").upper()
            replacement = movement._replacement_relevance(
                player, boundaries, float(replacement_cfg["near_distance_percentile_points"])
            )
            replacement_counts[str(replacement.get("classification"))] += 1
            position_counts[position] += 1

            adp, adp_crossed, _, _ = movement._adp_movement(
                player,
                movement._primary_adp_source(histories, position),
                windows,
                thresholds["adp"],
            )
            market, market_crossed, _, _ = movement._market_movement(
                player,
                movement._market_histories(histories, position),
                windows,
                thresholds["market"],
            )
            projections, projection_crossed, _, _ = movement._projection_movement(
                player,
                movement._projection_histories(histories, position),
                windows,
                thresholds["projections"],
                scoring,
            )
            crossed = adp_crossed + market_crossed + projection_crossed
            for item in crossed:
                window = int(item["window_days"])
                family = str(item["family"])
                by_window[window].add(player_id)
                by_family_window[family][window].add(player_id)
                crossing_kind_counts[(family, str(item.get("kind")), window)] += 1
                crossing_severity_counts[(str(item.get("severity")), window)] += 1
                player_crossings[player_id].append(item)

            fc_provider = None
            for provider in (market.get("providers") or {}).values():
                if str(provider.get("provider") or "").casefold() == "fantasycalc":
                    fc_provider = provider
                    break
            if fc_provider is not None and fc_provider.get("current_listed"):
                fc_windows = {}
                for window in windows:
                    data = (fc_provider.get("windows") or {}).get(str(window)) or {}
                    fc_windows[str(window)] = {
                        "delta_percentile": data.get("delta_percentile"),
                        "delta_value": data.get("delta_value"),
                        "value_percent_change": data.get("value_percent_change"),
                    }
                activity = movement._activity_context(player)
                fc_records.append({
                    "player_id": player_id,
                    "name": player.get("name"),
                    "position": position,
                    "replacement": replacement.get("classification"),
                    "current_value": fc_provider.get("current_value"),
                    "current_percentile": fc_provider.get("current_percentile"),
                    "current_discovery": player_id in discovery_ids,
                    "existing_quantitative_crossing": bool(crossed),
                    "sleeper_add_rank": activity.get("add_rank"),
                    "windows": fc_windows,
                })

        earliest_window_counts = Counter()
        slow_only_ids = set()
        for player_id, crossings in player_crossings.items():
            crossed_windows = sorted({int(item["window_days"]) for item in crossings})
            earliest = crossed_windows[0]
            earliest_window_counts[earliest] += 1
            if 1 not in crossed_windows and any(window > 1 for window in crossed_windows):
                slow_only_ids.add(player_id)

        for player in free_agent_players:
            player_id = str(player.get("player_id"))
            if player_id not in slow_only_ids:
                continue
            crossings = player_crossings[player_id]
            slow_examples.append({
                "player_id": player_id,
                "name": player.get("name"),
                "position": player.get("position"),
                "windows": sorted({int(item["window_days"]) for item in crossings}),
                "crossings": [
                    {
                        "family": item.get("family"),
                        "kind": item.get("kind"),
                        "window": item.get("window_days"),
                        "delta": item.get("delta"),
                        "threshold": item.get("threshold"),
                        "severity": item.get("severity"),
                    }
                    for item in crossings
                ],
            })
        slow_examples.sort(key=lambda item: (min(item["windows"]), str(item["name"] or "")))

        def quantile(values, q):
            vals = sorted(float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v)))
            if not vals:
                return None
            if len(vals) == 1:
                return round(vals[0], 3)
            pos = (len(vals) - 1) * q
            lo = math.floor(pos)
            hi = math.ceil(pos)
            if lo == hi:
                return round(vals[lo], 3)
            value = vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
            return round(value, 3)

        fc_distribution = {}
        for window in windows:
            pct = []
            value_pct = []
            value_abs = []
            for record in fc_records:
                data = record["windows"][str(window)]
                if isinstance(data.get("delta_percentile"), (int, float)):
                    pct.append(abs(float(data["delta_percentile"])))
                if isinstance(data.get("value_percent_change"), (int, float)):
                    value_pct.append(abs(float(data["value_percent_change"])))
                if isinstance(data.get("delta_value"), (int, float)):
                    value_abs.append(abs(float(data["delta_value"])))
            fc_distribution[str(window)] = {
                "comparable_percentile_count": len(pct),
                "abs_percentile_delta_q50_q75_q90_q95_q99": [quantile(pct, q) for q in (0.5, 0.75, 0.9, 0.95, 0.99)],
                "abs_value_percent_change_q50_q75_q90_q95_q99": [quantile(value_pct, q) for q in (0.5, 0.75, 0.9, 0.95, 0.99)],
                "abs_value_delta_q50_q75_q90_q95_q99": [quantile(value_abs, q) for q in (0.5, 0.75, 0.9, 0.95, 0.99)],
            }

        fc_percentile_grid = {}
        for threshold in (3, 5, 7.5, 10, 12.5, 15, 20):
            candidates = []
            for record in fc_records:
                qualifying = []
                for window in windows:
                    delta = record["windows"][str(window)].get("delta_percentile")
                    if isinstance(delta, (int, float)) and abs(float(delta)) >= threshold:
                        qualifying.append((window, float(delta)))
                if qualifying:
                    candidates.append((record, qualifying))
            near = [item for item in candidates if item[0]["replacement"] in {"near_rostered_boundary", "at_or_above_rostered_boundary"}]
            uncovered = [item for item in candidates if not item[0]["current_discovery"]]
            uncovered_near = [item for item in near if not item[0]["current_discovery"]]
            no_quant = [item for item in candidates if not item[0]["existing_quantitative_crossing"]]
            fc_percentile_grid[str(threshold)] = {
                "all": len(candidates),
                "near_or_above_boundary": len(near),
                "not_in_current_discovery": len(uncovered),
                "not_in_current_discovery_near_or_above": len(uncovered_near),
                "without_existing_quantitative_crossing": len(no_quant),
            }

        fc_value_grid = {}
        for pct_threshold, abs_threshold in ((10, 100), (15, 100), (20, 100), (20, 250), (25, 250), (30, 250), (30, 500), (40, 500)):
            candidates = []
            for record in fc_records:
                qualifying = []
                for window in windows:
                    data = record["windows"][str(window)]
                    pct = data.get("value_percent_change")
                    absolute = data.get("delta_value")
                    if (
                        isinstance(pct, (int, float))
                        and isinstance(absolute, (int, float))
                        and abs(float(pct)) >= pct_threshold
                        and abs(float(absolute)) >= abs_threshold
                    ):
                        qualifying.append((window, float(pct), float(absolute)))
                if qualifying:
                    candidates.append((record, qualifying))
            near = [item for item in candidates if item[0]["replacement"] in {"near_rostered_boundary", "at_or_above_rostered_boundary"}]
            uncovered = [item for item in candidates if not item[0]["current_discovery"]]
            uncovered_near = [item for item in near if not item[0]["current_discovery"]]
            fc_value_grid[f"pct{pct_threshold}_abs{abs_threshold}"] = {
                "all": len(candidates),
                "near_or_above_boundary": len(near),
                "not_in_current_discovery": len(uncovered),
                "not_in_current_discovery_near_or_above": len(uncovered_near),
            }

        top_uncovered = []
        for record in fc_records:
            if record["current_discovery"]:
                continue
            max_pct = None
            max_pct_window = None
            max_value_pct = None
            max_value_pct_window = None
            max_abs_value = None
            for window in windows:
                data = record["windows"][str(window)]
                delta_pct = data.get("delta_percentile")
                if isinstance(delta_pct, (int, float)) and (max_pct is None or abs(float(delta_pct)) > abs(max_pct)):
                    max_pct = float(delta_pct)
                    max_pct_window = window
                value_pct = data.get("value_percent_change")
                if isinstance(value_pct, (int, float)) and (max_value_pct is None or abs(float(value_pct)) > abs(max_value_pct)):
                    max_value_pct = float(value_pct)
                    max_value_pct_window = window
                value_abs = data.get("delta_value")
                if isinstance(value_abs, (int, float)) and (max_abs_value is None or abs(float(value_abs)) > abs(max_abs_value)):
                    max_abs_value = float(value_abs)
            if max_pct is None and max_value_pct is None:
                continue
            top_uncovered.append({
                "player_id": record["player_id"],
                "name": record["name"],
                "position": record["position"],
                "replacement": record["replacement"],
                "current_value": record["current_value"],
                "current_percentile": record["current_percentile"],
                "max_percentile_delta": max_pct,
                "max_percentile_window": max_pct_window,
                "max_value_percent_change": max_value_pct,
                "max_value_percent_window": max_value_pct_window,
                "max_abs_value_delta": max_abs_value,
                "sleeper_add_rank": record["sleeper_add_rank"],
            })
        top_uncovered.sort(
            key=lambda item: (
                0 if item["replacement"] in {"at_or_above_rostered_boundary", "near_rostered_boundary"} else 1,
                -(abs(item["max_percentile_delta"]) if item["max_percentile_delta"] is not None else -1),
                -(abs(item["max_value_percent_change"]) if item["max_value_percent_change"] is not None else -1),
            )
        )

        report = {
            "audit_commit": "17490093b94c5f3d7d2e9b957267ba0302b96874",
            "windows": windows,
            "thresholds": thresholds,
            "population": {
                "free_agents": len(free_agent_players),
                "current_discoveries": len(discovery_ids),
                "positions": dict(sorted(position_counts.items())),
                "replacement": dict(sorted(replacement_counts.items())),
            },
            "history_coverage": history_coverage,
            "pending_sources": pending,
            "hard_threshold_players_by_window": {str(w): len(by_window[w]) for w in windows},
            "hard_threshold_players_by_family_window": {
                family: {str(w): len(values[w]) for w in windows}
                for family, values in by_family_window.items()
            },
            "earliest_visible_hard_window": {str(w): earliest_window_counts[w] for w in windows},
            "players_with_no_1d_hard_crossing_but_longer_window_crossing": len(slow_only_ids),
            "slow_examples": slow_examples[:20],
            "crossing_kind_counts": {
                f"{family}|{kind}|{window}d": count
                for (family, kind, window), count in sorted(crossing_kind_counts.items())
            },
            "crossing_severity_counts": {
                f"{severity}|{window}d": count
                for (severity, window), count in sorted(crossing_severity_counts.items())
            },
            "fantasycalc": {
                "listed_free_agents": len(fc_records),
                "distribution_by_window": fc_distribution,
                "percentile_threshold_grid": fc_percentile_grid,
                "value_threshold_grid": fc_value_grid,
                "top_uncovered": top_uncovered[:30],
            },
        }
        print("CALIBRATION_AUDIT_JSON=" + json.dumps(report, separators=(",", ":"), sort_keys=True))
        self.assertGreater(len(free_agent_players), 0)
        self.assertGreater(len(histories), 0)


if __name__ == "__main__":
    unittest.main()
