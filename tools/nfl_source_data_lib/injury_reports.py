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


def valid_injury_season(season: Any) -> bool:
    """Validate a four-digit NFL season identifier, not a hard-coded year range."""
    return (isinstance(season, int) and not isinstance(season, bool)
            and season > 0 and len(str(season)) == 4)


def parse_injury_report_csv(asset: bytes, *, season: int) -> dict[str, Any]:
    """Parse one official-style season asset without changing any provider field.

    The accepted header profiles are selected from the actual asset columns,
    never inferred from a season threshold. This parser's recognition of a
    profile does not approve a historical original or authorize publication.
    A source observation is identified by the full asset hash and logical row
    ordinal; this is not a stable event identifier across upstream revisions.
    """
    if not isinstance(asset, bytes):
        raise TypeError("Injury CSV asset must be bytes")
    if not valid_injury_season(season):
        raise ValueError("Injury CSV season must be a four-digit year")

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
    if len(set(header)) != len(header):
        raise ValueError("Injury CSV contains duplicate header names")
    columns = set(header)
    if columns == _LEGACY_COLUMNS and len(header) == len(_LEGACY_COLUMNS):
        source_schema = "date-modified"
    elif columns == _NEW_COLUMNS and len(header) == len(_NEW_COLUMNS):
        source_schema = "season-type"
    else:
        raise ValueError(
            f"Injury CSV {season}: unexpected header; "
            f"missingCommon={sorted(_COMMON_COLUMNS - columns)}, "
            f"unknownColumns={sorted(columns - (_LEGACY_COLUMNS | _NEW_COLUMNS))}, "
            f"knownProfiles=[date-modified, season-type]"
        )

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
        "SourceSchema": source_schema,
        "AssetSha256": digest,
        "AssetByteSize": len(asset),
        "Header": header,
        "RowCount": len(rows),
        "Rows": rows,
    }
