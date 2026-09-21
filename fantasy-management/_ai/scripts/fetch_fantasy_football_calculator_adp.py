#!/usr/bin/env python3
"""Fetch and normalize Fantasy Football Calculator ADP rankings.

Stores independent PPR 8-team and 2-QB 10-team redraft signals. The PPR payload
also materializes a separate kicker-only ranking without an additional request.
Insufficient kicker coverage preserves the last-good kicker snapshot without
blocking healthy PPR/2-QB publication. Each ranking keeps only the latest raw
response and archives changed normalized rankings.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fantasy_football_calculator_adp_core import (  # noqa: E402
    CSV_FIELDS,
    DEFAULT_MAX_STALE_DAYS,
    FORMAT_CONFIGS,
    SCHEMA_VERSION,
    FantasyFootballCalculatorFetchError,
    build_source_url,
    fetch_payload,
    parse_players,
    parse_timestamp,
    request_parameters,
    validate_payload,
)
from fantasy_football_calculator_adp_storage import (  # noqa: E402
    ranking_root,
    write_format,
)
from fantasy_football_calculator_kicker_adp import (  # noqa: E402
    FantasyFootballCalculatorKickerError,
    RANKING_ID as KICKER_RANKING_ID,
    parse_kickers,
    write_kicker_format,
)
from fantasy_football_calculator_source_quality import (  # noqa: E402
    FantasyFootballCalculatorQualityError,
    evaluate_dataset_coverage,
    load_contract,
    write_observation,
)
from tools.nfl_season_context import (  # noqa: E402
    NflSeasonContextError,
    resolve_nfl_season_context,
)


def parse_input_mapping(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--input must use FORMAT=PATH")
        key, path = value.split("=", 1)
        if key not in FORMAT_CONFIGS:
            raise ValueError(f"Unknown --input format: {key}")
        result[key] = Path(path).expanduser()
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--season",
        type=int,
        default=datetime.now(timezone.utc).year,
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--max-stale-days",
        type=int,
        default=DEFAULT_MAX_STALE_DAYS,
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
    )
    parser.add_argument("--fetched-at")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="FORMAT=PATH",
    )
    parser.add_argument("--skip-unchanged", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.season < 2000 or args.max_stale_days < 0:
            raise ValueError("Invalid season or max-stale-days")
        fetched_at = parse_timestamp(args.fetched_at)
        repo_root = args.repo_root.resolve()
        saved = parse_input_mapping(args.input)
        season_context = resolve_nfl_season_context(
            repo_root,
            as_of=fetched_at,
            season=args.season,
        )
        contract = load_contract(repo_root)

        prepared: list[dict[str, Any]] = []
        kicker_prepared: dict[str, Any] | None = None
        observations: dict[str, dict[str, Any]] = {}

        # Validate both source formats technically before publishing any normalized dataset.
        for key, config in FORMAT_CONFIGS.items():
            if key in saved:
                payload = json.loads(saved[key].read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise FantasyFootballCalculatorFetchError(
                        f"Saved FFC payload is not an object for {config['ranking_id']}"
                    )
                response_headers: dict[str, str] = {}
                source_url = build_source_url(config, args.season)
            else:
                payload, response_headers, source_url = fetch_payload(
                    config,
                    args.season,
                    args.timeout,
                )

            sample = validate_payload(
                payload,
                config,
                season=args.season,
                fetched_at=fetched_at,
                max_stale_days=args.max_stale_days,
            )
            rows, diagnostics = parse_players(payload, config, sample)
            quality = evaluate_dataset_coverage(
                contract,
                dataset_id=config["ranking_id"],
                phase=season_context["phase"],
                observed_rows=len(rows),
            )
            observations[config["ranking_id"]] = {
                "dataset_id": config["ranking_id"],
                "technical_status": "valid",
                **quality,
                "sample": sample,
                "diagnostics": diagnostics,
            }
            if quality["publishable"]:
                prepared.append({
                    "key": key,
                    "config": config,
                    "payload": payload,
                    "response_headers": response_headers,
                    "source_url": source_url,
                    "sample": sample,
                    "rows": rows,
                    "diagnostics": diagnostics,
                })

            if key == "ppr-8-team":
                kicker_rows, kicker_diagnostics = parse_kickers(payload, sample)
                kicker_quality = evaluate_dataset_coverage(
                    contract,
                    dataset_id=KICKER_RANKING_ID,
                    phase=season_context["phase"],
                    observed_rows=len(kicker_rows),
                )
                observations[KICKER_RANKING_ID] = {
                    "dataset_id": KICKER_RANKING_ID,
                    "technical_status": "valid",
                    **kicker_quality,
                    "sample": sample,
                    "diagnostics": kicker_diagnostics,
                }
                if kicker_quality["publishable"]:
                    kicker_prepared = {
                        "payload": payload,
                        "response_headers": response_headers,
                        "source_url": source_url,
                        "sample": sample,
                        "rows": kicker_rows,
                        "diagnostics": kicker_diagnostics,
                    }

        if args.dry_run:
            for dataset_id, observation in observations.items():
                print(
                    f"FFC ADP ranking={dataset_id} "
                    f"rows={observation['observed_rows']} "
                    f"coverage={observation['coverage_status']} "
                    f"minimum={observation['minimum_usable_rows']} "
                    f"expected={observation['expected_minimum_rows']} "
                    f"phase={season_context['phase']}"
                )
            return 0

        for item in prepared:
            paths, created = write_format(
                repo_root=repo_root,
                rows=item["rows"],
                payload=item["payload"],
                config=item["config"],
                sample=item["sample"],
                diagnostics=item["diagnostics"],
                fetched_at=fetched_at,
                source_url=item["source_url"],
                response_headers=item["response_headers"],
                season=args.season,
                skip_unchanged=args.skip_unchanged,
            )
            action = "snapshot-created" if created else "ranking-unchanged"
            print(f"[ffc-adp:{item['key']}] {action}")
            for path in paths:
                print(path)

        if kicker_prepared is not None:
            kicker_paths, kicker_created = write_kicker_format(
                repo_root=repo_root,
                rows=kicker_prepared["rows"],
                payload=kicker_prepared["payload"],
                sample=kicker_prepared["sample"],
                diagnostics=kicker_prepared["diagnostics"],
                fetched_at=fetched_at,
                source_url=kicker_prepared["source_url"],
                response_headers=kicker_prepared["response_headers"],
                season=args.season,
                skip_unchanged=args.skip_unchanged,
            )
            kicker_action = "snapshot-created" if kicker_created else "ranking-unchanged"
            print(f"[ffc-adp:ppr-8-team-kicker] {kicker_action}")
            for path in kicker_paths:
                print(path)

        for dataset_id, observation in observations.items():
            if not observation["publishable"]:
                print(
                    f"[ffc-adp:{dataset_id}] preserving-last-good: "
                    f"coverage={observation['coverage_status']} "
                    f"rows={observation['observed_rows']}",
                    file=sys.stderr,
                )

        observation_path = write_observation(
            repo_root,
            {
                "schema_version": 1,
                "source_id": "fantasy-football-calculator",
                "technical_status": "success",
                "checked_at": fetched_at.isoformat().replace("+00:00", "Z"),
                "season_context": season_context,
                "datasets": observations,
            },
        )
        print(observation_path)
        return 0
    except (
        FantasyFootballCalculatorFetchError,
        FantasyFootballCalculatorKickerError,
        FantasyFootballCalculatorQualityError,
        NflSeasonContextError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"[ffc-adp] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
