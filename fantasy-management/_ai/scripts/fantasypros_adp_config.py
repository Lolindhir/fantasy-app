"""Source configuration and identity validation for FantasyPros ADP."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from fantasypros_adp_html import FantasyProsAdpError, build_source_url, token

SOURCE_ID = "fantasypros"
SOURCE_NAME = "FantasyPros"
SOURCE_ROOT = "fantasy-management/sources/external-rankings/adp/fantasypros"
ANALYSIS_METADATA = f"{SOURCE_ROOT}/analysis-metadata.json"
DIRECT_FETCHER = "fantasy-management/_ai/scripts/fetch_fantasypros_adp.py"
SCHEMA_VERSION = 1
ACTUAL_LEAGUE_TEAM_COUNT = 6
DEFAULT_RETENTION_COUNT = 4
OFFENSIVE_POSITIONS = {"QB", "RB", "WR", "TE"}
USER_AGENT = "Mozilla/5.0 (compatible; MightyGiantsFantasy/1.0)"

FORMAT_CONFIGS: dict[str, dict[str, Any]] = {
    "ppr-overall": {
        "ranking_id": "redraft-ppr-overall",
        "ranking_name": "FantasyPros Redraft PPR Overall ADP",
        "url": "https://www.fantasypros.com/nfl/adp/ppr-overall.php",
        "scoring": "ppr",
        "superflex": False,
        "rank_header": "Rank",
        "overall_header": None,
        "min_rows": 100,
        "primary_for_positions": ["RB", "WR", "TE"],
        "role": "broad_full_ppr_platform_composite",
    },
    "half-ppr-superflex": {
        "ranking_id": "redraft-half-ppr-superflex",
        "ranking_name": "FantasyPros Redraft Half-PPR Superflex ADP",
        "url": "https://www.fantasypros.com/nfl/adp/half-point-ppr-superflex.php",
        "scoring": "half_ppr",
        "superflex": True,
        "rank_header": "OP",
        "overall_header": "Overall",
        "min_rows": 80,
        "primary_for_positions": ["QB"],
        "role": "superflex_quarterback_scarcity_platform_composite",
    },
}

CSV_FIELDS = [
    "name",
    "Rank",
    "source_format_rank",
    "source_overall_rank",
    "position",
    "position_rank",
    "team",
    "bye",
    "source_player_id",
    "player_slug",
    "adp_average",
    "realtime_value",
    "source_ranks_json",
    "contributing_source_count",
    "source_rank_min",
    "source_rank_max",
    "source_rank_range",
    "source_rank_std",
    "source_format",
    "actual_league_team_count",
]

def fetch_html(
    config: dict[str, Any],
    season: int,
    timeout: int,
) -> tuple[str, dict[str, str], str]:
    url = build_source_url(config, season)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset, errors="replace")
            headers = {
                "etag": response.headers.get("ETag") or "",
                "last_modified": response.headers.get("Last-Modified") or "",
                "content_type": response.headers.get("Content-Type") or "",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FantasyProsAdpError(
            f"FantasyPros ADP fetch failed for {config['ranking_id']}: {exc}"
        ) from exc
    if not html.strip():
        raise FantasyProsAdpError(
            f"FantasyPros returned an empty page for {config['ranking_id']}"
        )
    return html, headers, url


def validate_source_identity(
    parsed: dict[str, Any],
    config: dict[str, Any],
    season: int,
    headers: list[str],
) -> None:
    title_text = f"{parsed.get('title', '')} {parsed.get('document_text', '')}"
    normalized = token(title_text)
    if str(season) not in title_text:
        raise FantasyProsAdpError(
            f"FantasyPros page does not identify expected season {season} for {config['ranking_id']}"
        )
    if "averagedraftposition" not in normalized:
        raise FantasyProsAdpError(
            f"FantasyPros page is not an ADP page for {config['ranking_id']}"
        )
    header_tokens = {token(value) for value in headers}
    required = {token(config["rank_header"]), "avg"}
    if not required.issubset(header_tokens):
        raise FantasyProsAdpError(
            f"FantasyPros headers do not match {config['ranking_id']}: {headers}"
        )
    if config["superflex"]:
        if "overall" not in header_tokens or "halfppr" not in normalized:
            raise FantasyProsAdpError(
                f"FantasyPros page is not Half-PPR Superflex for {config['ranking_id']}"
            )
    elif "pprleagues" not in token(parsed.get("title", "")):
        raise FantasyProsAdpError(
            f"FantasyPros page is not PPR for {config['ranking_id']}"
        )

