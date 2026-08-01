#!/usr/bin/env python3
"""Fetch and normalize public FantasyPros redraft ADP composites.

Both the PPR overall and Half-PPR Superflex pages are fetched and validated
before either format is published. The current parsed source tables are kept as
raw-latest.json; normalized history retains the latest four changed snapshots.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fantasypros_adp_core import (  # noqa: E402
    CSV_FIELDS,
    DEFAULT_RETENTION_COUNT,
    FORMAT_CONFIGS,
    SOURCE_ROOT,
    FantasyProsAdpError,
    build_source_url,
    fetch_html,
    parse_adp_page,
    parse_timestamp,
)
from fantasypros_adp_storage import (  # noqa: E402
    ranking_root,
    snapshot_dates,
    write_format,
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
        "--season", type=int, default=datetime.now(timezone.utc).year
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--request-delay-seconds", type=float, default=5.0)
    parser.add_argument(
        "--retention-count", type=int, default=DEFAULT_RETENTION_COUNT
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--fetched-at")
    parser.add_argument(
        "--input", action="append", default=[], metavar="FORMAT=PATH"
    )
    parser.add_argument("--skip-unchanged", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.season < 2000:
            raise ValueError("Invalid season")
        if args.timeout <= 0 or args.request_delay_seconds < 0:
            raise ValueError("Invalid timeout or request delay")
        if args.retention_count < 2:
            raise ValueError("retention-count must be at least 2")
        fetched_at = parse_timestamp(args.fetched_at)
        repo_root = args.repo_root.resolve()
        saved = parse_input_mapping(args.input)
        prepared: list[dict[str, Any]] = []
        live_request_count = 0

        # Fail closed: both formats must parse and validate before either is written.
        for key, config in FORMAT_CONFIGS.items():
            if key in saved:
                html = saved[key].read_text(encoding="utf-8")
                response_headers: dict[str, str] = {}
                source_url = build_source_url(config, args.season)
            else:
                if live_request_count:
                    time.sleep(args.request_delay_seconds)
                html, response_headers, source_url = fetch_html(
                    config, args.season, args.timeout
                )
                live_request_count += 1
            rows, diagnostics, raw_payload = parse_adp_page(
                html,
                config,
                season=args.season,
                source_url=source_url,
            )
            raw_payload["fetched_at"] = fetched_at.isoformat()
            raw_payload["response_headers"] = response_headers
            prepared.append(
                {
                    "key": key,
                    "config": config,
                    "rows": rows,
                    "diagnostics": diagnostics,
                    "raw_payload": raw_payload,
                    "response_headers": response_headers,
                    "source_url": source_url,
                }
            )

        if args.dry_run:
            for item in prepared:
                counts = Counter(row["position"] for row in item["rows"])
                print(
                    f"FantasyPros ADP ranking={item['config']['ranking_id']} "
                    f"rows={len(item['rows'])} "
                    f"sources={','.join(item['diagnostics']['active_source_ids'])} "
                    + " ".join(
                        f"{position}={counts[position]}" for position in sorted(counts)
                    )
                )
            return 0

        for item in prepared:
            paths, created, removed = write_format(
                repo_root=repo_root,
                rows=item["rows"],
                config=item["config"],
                diagnostics=item["diagnostics"],
                raw_payload=item["raw_payload"],
                fetched_at=fetched_at,
                source_url=item["source_url"],
                response_headers=item["response_headers"],
                season=args.season,
                skip_unchanged=args.skip_unchanged,
                retention_count=args.retention_count,
            )
            action = "snapshot-created" if created else "ranking-unchanged"
            print(f"[fantasypros-adp:{item['key']}] {action}")
            if removed:
                print(
                    f"[fantasypros-adp:{item['key']}] pruned={','.join(removed)}"
                )
            for path in paths:
                print(path)
        return 0
    except (FantasyProsAdpError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[fantasypros-adp] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
