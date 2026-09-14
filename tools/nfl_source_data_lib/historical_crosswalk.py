from __future__ import annotations

import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .common import (
    current_source_season,
    inspect_csv,
    load_json,
    sha256_file,
    utc_now,
    write_json_if_changed,
)

_CONFIG_KEY = "historicalIdentityBackfill"
_GITHUB_API = "https://api.github.com"
_USER_AGENT = "Lolindhir-fantasy-app-historical-player-identity/1.0"


def _config(repo_root: Path) -> dict[str, Any] | None:
    raw = load_json(repo_root / "source-data/historical-identity-backfill.json")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{_CONFIG_KEY} must be an object")

    start_season = raw.get("startSeason")
    source = raw.get("source")
    if not isinstance(start_season, int) or start_season < 1990:
        raise ValueError(f"{_CONFIG_KEY}.startSeason must be an NFL season >= 1990")
    if not isinstance(source, dict):
        raise ValueError(f"{_CONFIG_KEY}.source must be an object")

    required = (
        "id",
        "provider",
        "upstream",
        "repository",
        "path",
        "rawPath",
        "metadataPath",
        "requiredColumns",
        "minimumRows",
        "license",
        "attribution",
    )
    missing = [key for key in required if not source.get(key)]
    if missing:
        raise ValueError(
            f"{_CONFIG_KEY}.source is missing required fields: {', '.join(missing)}"
        )
    if "{season}" not in str(source["rawPath"]) or "{role}" not in str(source["rawPath"]):
        raise ValueError("historical identity rawPath must contain {season} and {role}")
    if "{season}" not in str(source["metadataPath"]):
        raise ValueError("historical identity metadataPath must contain {season}")
    if not isinstance(source["requiredColumns"], list) or not source["requiredColumns"]:
        raise ValueError("historical identity requiredColumns must be a non-empty list")
    if int(source["minimumRows"]) < 1:
        raise ValueError("historical identity minimumRows must be >= 1")
    return {"startSeason": start_season, "source": source}


def _season_window(season: int) -> tuple[str, str]:
    return (
        f"{season}-08-01T00:00:00Z",
        f"{season + 1}-03-02T00:00:00Z",
    )


def _request_json(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": _USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("PAT_PUSH")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _commit_time(item: dict[str, Any]) -> str:
    commit = item.get("commit") or {}
    committer = commit.get("committer") or {}
    author = commit.get("author") or {}
    value = committer.get("date") or author.get("date")
    return str(value or "")


def _history_commits(repository: str, path: str, season: int) -> list[dict[str, str]]:
    since, until = _season_window(season)
    commits: list[dict[str, str]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "path": path,
                "since": since,
                "until": until,
                "per_page": 100,
                "page": page,
            }
        )
        payload = _request_json(
            f"{_GITHUB_API}/repos/{repository}/commits?{query}"
        )
        if not isinstance(payload, list):
            raise ValueError(
                f"Unexpected GitHub commit-history payload for {repository}:{path}"
            )
        for item in payload:
            if not isinstance(item, dict) or not item.get("sha"):
                continue
            commits.append(
                {
                    "sha": str(item["sha"]),
                    "committedAtUtc": _commit_time(item),
                }
            )
        if len(payload) < 100:
            break
        page += 1
        if page > 20:
            raise ValueError(
                f"Historical identity commit history exceeded 2000 commits for season {season}"
            )
    commits.sort(key=lambda item: (item["committedAtUtc"], item["sha"]))
    return commits


def _select_boundary_commits(commits: list[dict[str, str]]) -> list[dict[str, str]]:
    if not commits:
        return []
    if len(commits) == 1:
        return [{"role": "opening", **commits[0]}]
    return [
        {"role": "opening", **commits[0]},
        {"role": "closing", **commits[-1]},
    ]


def _raw_url(repository: str, sha: str, path: str) -> str:
    encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    return f"https://raw.githubusercontent.com/{repository}/{sha}/{encoded_path}"


def _existing_snapshot_matches(
    repo_root: Path,
    source: dict[str, Any],
    metadata: dict[str, Any],
    selected: list[dict[str, str]],
    season: int,
) -> bool:
    snapshots = metadata.get("snapshots")
    if not isinstance(snapshots, list):
        return False
    existing = [
        (str(item.get("role")), str(item.get("commitSha")))
        for item in snapshots
        if isinstance(item, dict)
    ]
    expected = [(item["role"], item["sha"]) for item in selected]
    if existing != expected:
        return False

    source_root = repo_root / "source-data"
    for item in snapshots:
        raw_relative = item.get("rawPath")
        if not raw_relative:
            return False
        path = source_root / str(raw_relative)
        if not path.exists():
            return False
        inspect_csv(
            path,
            source["requiredColumns"],
            int(source["minimumRows"]),
        )
    return True


def _sync_season(
    repo_root: Path,
    source: dict[str, Any],
    season: int,
    current_season: int,
    *,
    force: bool,
    offline: bool,
) -> dict[str, Any]:
    source_root = repo_root / "source-data"
    metadata_path = source_root / str(source["metadataPath"]).format(season=season)
    existing = load_json(metadata_path, {}) or {}

    if season < current_season and metadata_path.exists() and not force:
        status = str(existing.get("availabilityStatus") or "unknown")
        for snapshot in existing.get("snapshots") or []:
            raw_relative = snapshot.get("rawPath")
            if raw_relative:
                path = source_root / str(raw_relative)
                if path.exists():
                    inspect_csv(
                        path,
                        source["requiredColumns"],
                        int(source["minimumRows"]),
                    )
        return {
            "season": season,
            "status": f"frozen-{status}",
            "snapshotCount": len(existing.get("snapshots") or []),
        }

    if offline:
        if not metadata_path.exists():
            return {
                "season": season,
                "status": "offline-missing-evidence",
                "snapshotCount": 0,
            }
        snapshots = existing.get("snapshots") or []
        for snapshot in snapshots:
            raw_relative = snapshot.get("rawPath")
            if not raw_relative:
                raise ValueError(
                    f"Historical identity metadata for {season} is missing rawPath"
                )
            inspect_csv(
                source_root / str(raw_relative),
                source["requiredColumns"],
                int(source["minimumRows"]),
            )
        return {
            "season": season,
            "status": "offline-existing",
            "snapshotCount": len(snapshots),
        }

    commits = _history_commits(
        str(source["repository"]),
        str(source["path"]),
        season,
    )
    selected = _select_boundary_commits(commits)
    since, until = _season_window(season)

    if not selected:
        payload = {
            "schemaVersion": 1,
            "source": source["id"],
            "provider": source["provider"],
            "upstream": source["upstream"],
            "repository": source["repository"],
            "path": source["path"],
            "season": season,
            "queryWindow": {"since": since, "until": until},
            "availabilityStatus": "no-contemporaneous-history",
            "snapshots": [],
            "license": source["license"],
            "attribution": source["attribution"],
        }
        changed = write_json_if_changed(metadata_path, payload)
        return {
            "season": season,
            "status": "no-contemporaneous-history" if changed else "unchanged-no-history",
            "snapshotCount": 0,
        }

    if (
        not force
        and existing.get("availabilityStatus") == "available"
        and _existing_snapshot_matches(repo_root, source, existing, selected, season)
    ):
        return {
            "season": season,
            "status": "unchanged",
            "snapshotCount": len(selected),
        }

    snapshots: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="historical-player-identity-") as temp_dir:
        for selected_item in selected:
            role = selected_item["role"]
            sha = selected_item["sha"]
            relative_path = str(source["rawPath"]).format(season=season, role=role)
            target = source_root / relative_path
            candidate = Path(temp_dir) / f"{season}-{role}.csv"
            url = _raw_url(str(source["repository"]), sha, str(source["path"]))
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response, candidate.open("wb") as output:
                shutil.copyfileobj(response, output)

            columns, row_count = inspect_csv(
                candidate,
                source["requiredColumns"],
                int(source["minimumRows"]),
            )
            content_hash = sha256_file(candidate)
            old_hash = sha256_file(target) if target.exists() else None
            if force or old_hash != content_hash:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, target)
            snapshots.append(
                {
                    "role": role,
                    "commitSha": sha,
                    "committedAtUtc": selected_item["committedAtUtc"],
                    "sourceUrl": url,
                    "rawPath": relative_path,
                    "contentHashSha256": content_hash,
                    "rowCount": row_count,
                    "columns": columns,
                }
            )

    payload = {
        "schemaVersion": 1,
        "source": source["id"],
        "provider": source["provider"],
        "upstream": source["upstream"],
        "repository": source["repository"],
        "path": source["path"],
        "season": season,
        "queryWindow": {"since": since, "until": until},
        "availabilityStatus": "available",
        "snapshots": snapshots,
        "license": source["license"],
        "attribution": source["attribution"],
        "retrievedAtUtc": utc_now(),
    }
    changed = write_json_if_changed(metadata_path, payload)
    return {
        "season": season,
        "status": "updated" if changed else "unchanged",
        "snapshotCount": len(snapshots),
    }


def sync_historical_crosswalk_evidence(
    repo_root: Path,
    *,
    current_season: int,
    force: bool = False,
    offline: bool = False,
) -> dict[str, Any]:
    config = _config(repo_root)
    if config is None:
        return {
            "enabled": False,
            "startSeason": None,
            "endSeason": current_season,
            "seasonCount": 0,
            "availableSeasonCount": 0,
            "noHistorySeasonCount": 0,
            "updatedSeasonCount": 0,
            "snapshotCount": 0,
        }

    start_season = int(config["startSeason"])
    source = config["source"]
    results = [
        _sync_season(
            repo_root,
            source,
            season,
            current_season,
            force=force,
            offline=offline,
        )
        for season in range(start_season, current_season + 1)
    ]
    return {
        "enabled": True,
        "startSeason": start_season,
        "endSeason": current_season,
        "seasonCount": len(results),
        "availableSeasonCount": sum(
            1
            for result in results
            if result["status"] not in {
                "no-contemporaneous-history",
                "unchanged-no-history",
                "frozen-no-contemporaneous-history",
                "offline-missing-evidence",
            }
        ),
        "noHistorySeasonCount": sum(
            1
            for result in results
            if "no-history" in result["status"]
            or result["status"] == "no-contemporaneous-history"
            or result["status"] == "frozen-no-contemporaneous-history"
        ),
        "updatedSeasonCount": sum(1 for result in results if result["status"] == "updated"),
        "snapshotCount": sum(int(result["snapshotCount"]) for result in results),
        "results": results,
    }


def iter_historical_crosswalk_snapshots(repo_root: Path) -> list[dict[str, Any]]:
    config = _config(repo_root)
    if config is None:
        return []

    source = config["source"]
    source_root = repo_root / "source-data"
    snapshots: list[dict[str, Any]] = []
    start_season = int(config["startSeason"])
    end_season = current_source_season(repo_root)

    for season in range(start_season, end_season + 1):
        metadata_path = source_root / str(source["metadataPath"]).format(season=season)
        metadata = load_json(metadata_path, {}) or {}
        if metadata.get("availabilityStatus") != "available":
            continue
        for item in metadata.get("snapshots") or []:
            if not isinstance(item, dict) or not item.get("rawPath") or not item.get("commitSha"):
                continue
            path = source_root / str(item["rawPath"])
            if not path.exists():
                raise FileNotFoundError(
                    f"Historical identity metadata references missing raw evidence: {path}"
                )
            snapshots.append(
                {
                    "season": season,
                    "role": str(item.get("role") or ""),
                    "commitSha": str(item["commitSha"]),
                    "path": path,
                    "sourceId": source["id"],
                }
            )
    snapshots.sort(
        key=lambda item: (
            int(item["season"]),
            str(item["role"]),
            str(item["commitSha"]),
        )
    )
    return snapshots
