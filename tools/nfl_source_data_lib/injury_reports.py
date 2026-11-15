"""Strict, side-effect-free parser for nflverse historical injury-report CSV assets.

This module intentionally does not fetch, persist, join players, deduplicate reports,
interpret availability, or infer injury episodes. Registry activation and publication
have separate source-rights and writer-scope gates (Issue #1421).
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from typing import Any

_SOURCE = "nflverse.injuries"
_GSIS_ID = re.compile(r"^00-[0-9]{7}$")
_COMMON_COLUMNS = frozenset(
    {
        "season", "game_type", "team", "week", "gsis_id", "position",
        "full_name", "first_name", "last_name", "report_primary_injury",
        "report_secondary_injury", "report_status", "practice_primary_injury",
        "practice_secondary_injury", "practice_status",
    }
)
_LEGACY_COLUMNS = _COMMON_COLUMNS | {"date_modified"}
_NEW_COLUMNS = _COMMON_COLUMNS | {"season_type"}


def parse_injury_report_csv(asset: bytes, *, season: int) -> dict[str, Any]:
    """Parse one official-style season asset without changing any provider field.

    Only the audited 2012–2024 and 2025+ header variants are supported. Years
    2009–2011 remain gated until their actual source schemas can be verified.
    A source observation is identified by the full asset hash and logical row
    ordinal; this is not a stable event identifier across upstream revisions.
    """
    if not isinstance(asset, bytes):
        raise TypeError("Injury CSV asset must be bytes")
    if not isinstance(season, int) or isinstance(season, bool) or not 2012 <= season <= 2099:
        raise ValueError("Injury CSV season must be in audited schema range 2012+ (2012–2024 legacy, 2025+ current schema; future headers checked strictly)")

    digest = hashlib.sha256(asset).hexdigest()
    try:
        decoded = asset.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Injury CSV must be UTF-8") from exc

    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("Injury CSV is empty") from exc
    expected = _LEGACY_COLUMNS if season <= 2024 else _NEW_COLUMNS
    if len(header) != len(expected) or set(header) != expected:
        raise ValueError(
            f"Injury CSV {season}: unexpected header; "
            f"missing={sorted(expected - set(header))}, "
            f"unexpected={sorted(set(header) - expected)}"
        )
    if len(set(header)) != len(header):
        raise ValueError("Injury CSV contains duplicate header names")

    rows: list[dict[str, Any]] = []
    for ordinal, values in enumerate(reader, start=1):
        if len(values) != len(header):
            raise ValueError(
                f"Injury CSV {season}: logical data row {ordinal} has "
                f"{len(values)} fields, expected {len(header)}"
            )
        fields = dict(zip(header, values))
        if fields["season"] != str(season):
            raise ValueError(f"Injury CSV {season}: row {ordinal} has wrong season")
        try:
            week = int(fields["week"])
        except ValueError as exc:
            raise ValueError(f"Injury CSV {season}: row {ordinal} has invalid week") from exc
        if not 1 <= week <= 22 or fields["week"] != str(week):
            raise ValueError(f"Injury CSV {season}: row {ordinal} has invalid week")
        if not _GSIS_ID.fullmatch(fields["gsis_id"]):
            raise ValueError(f"Injury CSV {season}: row {ordinal} has invalid GSIS ID")
        if not fields["team"] or not fields["game_type"]:
            raise ValueError(f"Injury CSV {season}: row {ordinal} lacks team/game_type")

        rows.append(
            {
                "ObservationKey": f"sha256:{digest}:row:{ordinal}",
                "RowOrdinal": ordinal,
                "Fields": fields,
            }
        )

    return {
        "Source": _SOURCE,
        "ParserSchemaVersion": 1,
        "Season": season,
        "SourceSchema": "date-modified" if season <= 2024 else "season-type",
        "AssetSha256": digest,
        "AssetByteSize": len(asset),
        "Header": header,
        "RowCount": len(rows),
        "Rows": rows,
    }
