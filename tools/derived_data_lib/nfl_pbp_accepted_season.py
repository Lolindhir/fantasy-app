"""Load accepted original NFL PBP evidence for dynamic GameDetail-v2 derivation.

The Source manifest, not the consumer, selects available seasons. Large original
archives stay immutable in their accepted GitHub Release; only the fields
needed for the compact derived metrics enter memory. Missing manifests mean
unavailable PBP (not an empty game or a false zero).
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.common import download
from .nfl_game_detail_core import _V2_PBP_SOURCE_FIELDS

_PBP_REQUIRED = frozenset((
    "game_id", "play_id", "season", "season_type", "week",
    "home_team", "away_team", "qtr", "down", "ydstogo", "yardline_100",
    "posteam", "defteam", "play_type", "desc", "epa", "success",
))
# Additional fields consumed by the existing original-play validator and
# its in-memory, unpublished candidate analytics. Never strip columns used
# by the ten canonical v2 observations.
_PBP_PROJECTION = frozenset(_V2_PBP_SOURCE_FIELDS) | _PBP_REQUIRED | {
    "drive", "game_seconds_remaining", "third_down_converted", "first_down",
    "yards_after_catch", "yards_gained", "air_yards",
}
_SOURCE_PATH = "providers/nflverse/play-by-play-original"


def _manifest(root: Path, season: int) -> dict[str, Any] | None:
    path = root / DATA_SOURCE_ROOT / _SOURCE_PATH / f"metadata-{season}.json"
    if not path.is_file():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid PBP original Source manifest {season}")
    sha = manifest.get("UpstreamSHA256")
    if (manifest.get("SchemaVersion") != 1
            or manifest.get("Status") != "accepted-original-byte-identity"
            or manifest.get("Provider") != "nflverse"
            or manifest.get("Season") != season
            or not isinstance(sha, str) or len(sha) != 64
            or any(char not in "0123456789abcdef" for char in sha)
            or type(manifest.get("CompressedBytes")) is not int
            or manifest["CompressedBytes"] <= 0
            or type(manifest.get("SourceCompletenessCertified")) is not bool):
        raise ValueError(f"Unaccepted PBP original Source manifest {season}")
    expected_url = (
        f"https://github.com/Lolindhir/fantasy-app/releases/download/"
        f"nfl-pbp-source-{season}-{sha[:12]}/play_by_play_{season}.csv.gz"
    )
    if manifest.get("ArchiveURL") != expected_url:
        raise ValueError(f"Unsafe/mismatched accepted PBP archive URL {season}")
    return manifest


def _verified_rows(
    original: Path, manifest: Mapping[str, Any],
    games: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    with original.open("rb") as handle:
        actual_sha = hashlib.file_digest(handle, "sha256").hexdigest()
    if (original.stat().st_size != manifest["CompressedBytes"]
            or actual_sha != manifest["UpstreamSHA256"]):
        raise ValueError(f"Original PBP archive does not match accepted Source bytes: {manifest['Season']}")
    by_game: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_ids: set[str] = set()
    scanned = 0
    with gzip.open(original, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if (not fields or len(fields) != len(set(fields)) or any(not name for name in fields)
                or not _PBP_REQUIRED.issubset(fields)):
            raise ValueError(f"Original PBP CSV header invalid: {manifest['Season']}")
        selected = sorted(_PBP_PROJECTION.intersection(fields))
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed original PBP CSV row: {manifest['Season']}")
            scanned += 1
            game_id = (row["game_id"] or "").strip()
            if game_id not in games:
                raise ValueError(f"Original PBP unknown canonical GameID: {game_id}")
            seen_ids.add(game_id)
            by_game[game_id].append({key: row[key] for key in selected})
    audit = manifest.get("Audit")
    if isinstance(audit, dict):
        count = audit.get("SourceRowCount")
        if type(count) is int and scanned != count:
            raise ValueError(f"Original PBP Source row-count drift: {manifest['Season']}")
        game_count = audit.get("ObservedGameIDs")
        if type(game_count) is int and len(seen_ids) != game_count:
            raise ValueError(f"Original PBP Source game-count drift: {manifest['Season']}")
    # Defend against local asset mutation after the first hash and full replay.
    with original.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != actual_sha:
            raise ValueError(f"Original PBP bytes changed during replay: {manifest['Season']}")
    return dict(by_game)


class AcceptedPBPSeasons:
    """One verified download/CSV replay per accepted season in a materialization."""

    def __init__(
        self, root: Path, *, local_assets: Mapping[int, Path] | None = None,
    ) -> None:
        self.root = root
        self.local_assets = dict(local_assets or {})
        self._cache: dict[int, tuple[dict[str, list[dict[str, str]]], str] | None] = {}

    def get(
        self, season: int, games: Mapping[str, Mapping[str, Any]],
    ) -> tuple[dict[str, list[dict[str, str]]], str] | None:
        if season in self._cache:
            return self._cache[season]
        manifest = _manifest(self.root, season)
        if manifest is None:
            if season in self.local_assets:
                raise ValueError(f"Local PBP asset without accepted manifest: {season}")
            self._cache[season] = None
            return None
        original = self.local_assets.get(season)
        if original is not None:
            payload = _verified_rows(original, manifest, games)
        else:
            with tempfile.TemporaryDirectory(prefix=f"nfl-pbp-derived-{season}-") as tmp:
                original = Path(tmp) / f"play_by_play_{season}.csv.gz"
                download(manifest["ArchiveURL"], original)
                payload = _verified_rows(original, manifest, games)
        evidence = (payload, manifest["UpstreamSHA256"])
        self._cache[season] = evidence
        return evidence
