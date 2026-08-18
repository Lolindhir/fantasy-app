from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

import build_free_agent_movement_dataset as movement


class PostCalibrationAuditTemp(unittest.TestCase):
    def test_print_post_calibration_metrics(self) -> None:
        root = Path(__file__).resolve().parents[3]
        config = root / "fantasy-management/automation/free-agent-movement-materialization.json"
        result = movement.build(root, config)

        kinds: Counter[str] = Counter()
        sources: Counter[str] = Counter()
        tier_sources: Counter[str] = Counter()
        fantasycalc_only = 0
        fantasycalc_any = 0
        fantasycalc_high = 0
        fantasycalc_near = 0
        numeric_discoveries = 0
        earliest_windows: Counter[int] = Counter()

        numeric_kinds = {
            "overall_rank_movement",
            "position_rank_movement",
            "fantasycalc_percentile_movement",
            "fantasycalc_value_movement",
            "percentile_movement",
            "consensus_percentile_movement",
        }
        fc_kinds = {"fantasycalc_percentile_movement", "fantasycalc_value_movement"}

        for discovery in result["discoveries"]:
            crossed = discovery["materiality"]["thresholds_crossed"]
            threshold_kinds = {str(item.get("kind")) for item in crossed}
            numeric = [item for item in crossed if item.get("kind") in numeric_kinds]
            if numeric:
                numeric_discoveries += 1
                earliest_windows[min(int(item["window_days"]) for item in numeric)] += 1
            if threshold_kinds.intersection(fc_kinds):
                fantasycalc_any += 1
                other_numeric = [
                    item for item in numeric
                    if item.get("kind") not in fc_kinds
                ]
                if not other_numeric:
                    fantasycalc_only += 1
                if any(item.get("severity") == "high" and item.get("kind") in fc_kinds for item in crossed):
                    fantasycalc_high += 1
                if discovery["replacement_relevance"]["classification"] in {
                    "at_or_above_rostered_boundary",
                    "near_rostered_boundary",
                }:
                    fantasycalc_near += 1
            for item in crossed:
                kind = str(item.get("kind"))
                kinds[kind] += 1
                source_id = item.get("source_id")
                if source_id:
                    sources[str(source_id)] += 1
                if kind == "tier_change":
                    tier_sources[str(source_id)] += 1

        payload = {
            "free_agents": result["population"]["free_agent_count"],
            "discoveries": result["population"]["discovery_count"],
            "position_counts": result["population"]["discovery_position_counts"],
            "priority_counts": result["population"]["priority_counts"],
            "material_family_counts": result["population"]["material_family_counts"],
            "numeric_discoveries": numeric_discoveries,
            "numeric_earliest_window": dict(sorted(earliest_windows.items())),
            "threshold_kind_counts": dict(sorted(kinds.items())),
            "threshold_source_counts": dict(sorted(sources.items())),
            "tier_change_sources": dict(sorted(tier_sources.items())),
            "fantasycalc_discoveries": fantasycalc_any,
            "fantasycalc_only_numeric_discoveries": fantasycalc_only,
            "fantasycalc_high_discoveries": fantasycalc_high,
            "fantasycalc_near_or_above_boundary": fantasycalc_near,
            "comparison_anchor_date": result["source"]["comparison_anchor_date"],
        }
        print("POST_CALIBRATION_AUDIT_JSON=" + json.dumps(payload, sort_keys=True))
        self.assertEqual(
            set(payload["tier_change_sources"]) - {"fantasypros-dynasty-superflex-ppr"},
            set(),
        )


if __name__ == "__main__":
    unittest.main()
