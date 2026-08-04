#!/usr/bin/env python3
"""Fetch and normalize public FantasyPros redraft ADP composites.

Both the PPR overall and Half-PPR Superflex pages are fetched and validated
before either format is published. The current parsed source tables are kept as
raw-latest.json; normalized history retains the latest four changed snapshots.

The active-season canonical page is attempted first. If FantasyPros returns its
JavaScript page shell without a ranking table, the fetcher reuses the same
cookie session and tries the official ``export=xls`` response. If that response
also contains only the page shell, a locally installed headless Chrome/Chromium
renders the canonical page and returns the resulting DOM. The canonical page
remains the source for page identity and visible source dates in every mode.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fantasypros_adp_browser import render_adp_page_with_browser  # noqa: E402
from fantasypros_adp_core import (  # noqa: E402
    CSV_FIELDS,
    DEFAULT_RETENTION_COUNT,
    FORMAT_CONFIGS,
    SOURCE_ROOT,
    FantasyProsAdpError,
    build_export_url,
    build_source_url,
    create_http_opener,
    fetch_url,
    parse_adp_page,
    parse_timestamp,
)
from fantasypros_adp_storage import (  # noqa: E402
    ranking_root,
    snapshot_dates,
    write_format,
)

MISSING_TABLE_ERROR = "FantasyPros ADP ranking table not found"


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
    parser.add_argument("--season", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--request-delay-seconds", type=float, default=5.0)
    parser.add_argument("--retention-count", type=int, default=DEFAULT_RETENTION_COUNT)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--fetched-at")
    parser.add_argument("--input", action="append", default=[], metavar="FORMAT=PATH")
    parser.add_argument("--skip-unchanged", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _live_requester(
    *,
    timeout: int,
    delay_seconds: float,
) -> Callable[[str, str], tuple[str, dict[str, str], str]]:
    opener = create_http_opener()
    request_count = 0

    def request(url: str, referer: str = "") -> tuple[str, dict[str, str], str]:
        nonlocal request_count
        if request_count:
            time.sleep(delay_seconds)
        result = fetch_url(
            url,
            timeout=timeout,
            opener=opener,
            referer=referer,
        )
        request_count += 1
        return result

    return request


def _prepare_live_format(
    *,
    config: dict[str, Any],
    season: int,
    request: Callable[[str, str], tuple[str, dict[str, str], str]],
    render: Callable[[str], tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    official_url = build_source_url(config, season)
    canonical_payload, canonical_headers, canonical_final_url = request(official_url, "")
    try:
        rows, diagnostics, raw_payload = parse_adp_page(
            canonical_payload,
            config,
            season=season,
            source_url=official_url,
            extraction_method="canonical_public_html_table",
            ranking_fetch_url=canonical_final_url,
        )
        response_headers: dict[str, Any] = {"canonical": canonical_headers}
        ranking_fetch_url = canonical_final_url
    except FantasyProsAdpError as exc:
        if str(exc) != MISSING_TABLE_ERROR:
            raise

        export_url = build_export_url(config, season)
        export_payload, export_headers, export_final_url = request(
            export_url, canonical_final_url
        )
        try:
            rows, diagnostics, raw_payload = parse_adp_page(
                export_payload,
                config,
                season=season,
                source_url=official_url,
                identity_html=canonical_payload,
                extraction_method="official_export_fallback",
                ranking_fetch_url=export_final_url,
            )
        except FantasyProsAdpError as export_exc:
            if str(export_exc) != MISSING_TABLE_ERROR or render is None:
                raise FantasyProsAdpError(
                    "FantasyPros canonical ADP page contained no ranking table and "
                    f"the official export fallback failed for {config['ranking_id']}: "
                    f"{export_exc}; canonical_url={canonical_final_url}; "
                    f"export_url={export_final_url}"
                ) from export_exc

            try:
                rendered_payload, browser_metadata = render(official_url)
                rows, diagnostics, raw_payload = parse_adp_page(
                    rendered_payload,
                    config,
                    season=season,
                    source_url=official_url,
                    identity_html=canonical_payload,
                    extraction_method="headless_browser_dom_fallback",
                    ranking_fetch_url=official_url,
                )
            except FantasyProsAdpError as browser_exc:
                raise FantasyProsAdpError(
                    "FantasyPros canonical ADP page and official export both contained "
                    f"no ranking table, and browser rendering failed for "
                    f"{config['ranking_id']}: {browser_exc}; "
                    f"canonical_url={canonical_final_url}; export_url={export_final_url}"
                ) from browser_exc

            response_headers = {
                "canonical": canonical_headers,
                "ranking_export": export_headers,
                "browser_render": browser_metadata,
            }
            ranking_fetch_url = official_url
            raw_payload["fallback_reason"] = (
                f"{MISSING_TABLE_ERROR}; official export also contained no ranking table"
            )
        else:
            response_headers = {
                "canonical": canonical_headers,
                "ranking_export": export_headers,
            }
            ranking_fetch_url = export_final_url
            raw_payload["fallback_reason"] = MISSING_TABLE_ERROR

    raw_payload["fetch_provenance"] = {
        "official_source_url": official_url,
        "canonical_fetch_url": canonical_final_url,
        "ranking_fetch_url": ranking_fetch_url,
        "extraction_method": raw_payload["extraction_method"],
        "response_headers": response_headers,
    }
    return {
        "config": config,
        "rows": rows,
        "diagnostics": diagnostics,
        "raw_payload": raw_payload,
        "response_headers": response_headers,
        "source_url": official_url,
    }


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
        live_request = _live_requester(
            timeout=args.timeout,
            delay_seconds=args.request_delay_seconds,
        )

        def live_render(url: str) -> tuple[str, dict[str, Any]]:
            # Keep the same polite minimum spacing before opening a browser,
            # which performs its own page and JavaScript data requests.
            if args.request_delay_seconds:
                time.sleep(args.request_delay_seconds)
            return render_adp_page_with_browser(url, timeout=args.timeout)

        for key, config in FORMAT_CONFIGS.items():
            if key in saved:
                payload = saved[key].read_text(encoding="utf-8")
                source_url = build_source_url(config, args.season)
                rows, diagnostics, raw_payload = parse_adp_page(
                    payload,
                    config,
                    season=args.season,
                    source_url=source_url,
                    extraction_method="saved_input_fixture",
                    ranking_fetch_url=source_url,
                )
                item = {
                    "config": config,
                    "rows": rows,
                    "diagnostics": diagnostics,
                    "raw_payload": raw_payload,
                    "response_headers": {},
                    "source_url": source_url,
                }
            else:
                item = _prepare_live_format(
                    config=config,
                    season=args.season,
                    request=live_request,
                    render=live_render,
                )
            item["key"] = key
            item["raw_payload"]["fetched_at"] = fetched_at.isoformat()
            prepared.append(item)

        if args.dry_run:
            for item in prepared:
                counts = Counter(row["position"] for row in item["rows"])
                print(
                    f"FantasyPros ADP ranking={item['config']['ranking_id']} "
                    f"rows={len(item['rows'])} "
                    f"method={item['raw_payload']['extraction_method']} "
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
            print(
                f"[fantasypros-adp:{item['key']}] {action} "
                f"method={item['raw_payload']['extraction_method']}"
            )
            if removed:
                print(f"[fantasypros-adp:{item['key']}] pruned={','.join(removed)}")
            for path in paths:
                print(path)
        return 0
    except (FantasyProsAdpError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[fantasypros-adp] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
