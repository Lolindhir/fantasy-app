#!/usr/bin/env python3
"""Fetch and normalize Fantasy Football Calculator ADP rankings.

Stores independent PPR 8-team and 2-QB 10-team redraft signals. The PPR payload
also materializes a separate kicker-only ranking without an additional request.
Each ranking keeps only the latest raw response and archives changed normalized
rankings.
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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

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
    parse_kickers,
    write_kicker_format,
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
        default=Path(__file__).resolve().parents[3],
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
        prepared: list[dict[str, Any]] = []
        kicker_prepared: dict[str, Any] | None = None

        # Validate both source formats before publishing either one.
        for key, config in FORMAT_CONFIGS.items():
            if key in saved:
                payload = json.loads(saved[key].read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise FantasyFootballCalculatorFetchError(
                        f"Saved FFC payload is not an object for "
                        f"{config['ranking_id']}"
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
                kicker_prepared = {
                    "payload": payload,
                    "response_headers": response_headers,
                    "source_url": source_url,
                    "sample": sample,
                    "rows": kicker_rows,
                    "diagnostics": kicker_diagnostics,
                }

        if kicker_prepared is None:
            raise FantasyFootballCalculatorKickerError(
                "PPR 8-team payload was not prepared for kicker materialization"
            )

        if args.dry_run:
            for item in prepared:
                counts = Counter(row["position"] for row in item["rows"])
                print(
                    f"FFC ADP ranking={item['config']['ranking_id']} "
                    f"rows={len(item['rows'])} "
                    f"drafts={item['sample']['total_drafts']} "
                    f"quality={item['sample']['quality']} "
                    + " ".join(
                        f"{position}={counts[position]}"
                        for position in sorted(counts)
                    )
                )
            print(
                "FFC ADP ranking=redraft-ppr-8-team-kicker "
                f"rows={len(kicker_prepared['rows'])} "
                f"drafts={kicker_prepared['sample']['total_drafts']} "
                f"quality={kicker_prepared['sample']['quality']} "
                f"K={len(kicker_prepared['rows'])}"
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
        return 0
    except (
        FantasyFootballCalculatorFetchError,
        FantasyFootballCalculatorKickerError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"[ffc-adp] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
