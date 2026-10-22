#!/usr/bin/env python3
"""CAS-safe, isolated technical odds-buffer state publisher (#471).

Publishes ONLY odds-buffer/<season>.json to the dedicated odds-refresh-state
branch through the GitHub Contents API. It never writes to main, data-source,
data-derived, App data or workflow-scheduler-state. The branch itself must be
provisioned explicitly before use; no implicit create/ref update/force push.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

STATE_BRANCH = "odds-refresh-state"
STATE_SCHEMA_VERSION = 1
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class StatePublicationError(ValueError):
    pass


def _stamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise StatePublicationError("Invalid or missing state observation timestamp")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StatePublicationError("Invalid state observation timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise StatePublicationError("State observation timestamps need an explicit timezone")
    return timestamp


def validate_state(state: object, season: int) -> dict:
    if not isinstance(state, dict) or (
        state.get("SchemaVersion") != STATE_SCHEMA_VERSION
        or state.get("Season") != season
        or not isinstance(state.get("Games"), dict)
        or not state["Games"]
    ):
        raise StatePublicationError("Unexpected odds-buffer schema, season or empty game set")
    for game_id, entry in state["Games"].items():
        if not isinstance(game_id, str) or not game_id.startswith(f"{season}_") or not isinstance(entry, dict):
            raise StatePublicationError(f"Invalid odds-buffer GameID: {game_id}")
        for field in ("ObservedAt", "PublishedAt"):
            _stamp(entry.get(field))
        if entry.get("PendingSince") is not None:
            _stamp(entry["PendingSince"])
        if not isinstance(entry.get("PublishedFingerprint"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["PublishedFingerprint"]):
            raise StatePublicationError(f"{game_id}: invalid published baseline fingerprint")
        for field in ("ObservedSpreadLine", "ObservedTotalLine"):
            if entry.get(field) is not None and (
                isinstance(entry[field], bool) or not isinstance(entry[field], (int, float))
                or not math.isfinite(entry[field])
            ):
                raise StatePublicationError(f"{game_id}: invalid observed line")
        if _stamp(entry["PublishedAt"]) > _stamp(entry["ObservedAt"]):
            raise StatePublicationError(f"{game_id}: published checkpoint after observation")
        if entry.get("PendingSince") is not None and not (
            _stamp(entry["PublishedAt"]) <= _stamp(entry["PendingSince"]) <= _stamp(entry["ObservedAt"])
        ):
            raise StatePublicationError(f"{game_id}: pending timestamp outside published/observed bounds")
    return state


def _decode_file(item: Mapping[str, Any], season: int) -> tuple[dict, str]:
    sha = item.get("sha")
    encoded = item.get("content")
    if not isinstance(sha, str) or not sha or not isinstance(encoded, str):
        raise StatePublicationError("Remote state response has no blob SHA or Base64 content")
    try:
        raw = base64.b64decode("".join(encoded.split()), validate=True)
        state = validate_state(json.loads(raw.decode("utf-8")), season)
    except (ValueError, UnicodeError) as exc:
        raise StatePublicationError("Remote state is corrupt") from exc
    return state, sha


def _assert_not_stale(candidate: dict, remote: dict) -> None:
    if set(candidate["Games"]) != set(remote["Games"]):
        raise StatePublicationError("Stored game population changed unexpectedly")
    for game_id, current in candidate["Games"].items():
        previous = remote["Games"][game_id]
        if _stamp(current["ObservedAt"]) < _stamp(previous["ObservedAt"]):
            raise StatePublicationError(f"{game_id}: stale observer cannot overwrite newer state")
        if _stamp(current["PublishedAt"]) < _stamp(previous["PublishedAt"]):
            raise StatePublicationError(f"{game_id}: published checkpoint regressed")


def publish_state(
    *,
    repository: str,
    season: int,
    candidate: dict,
    call: Callable[[str, str, dict | None], tuple[int, dict]],
    bootstrap: bool = False,
) -> str:
    """Return published/noop; fail closed on CAS races and missing branch.

    call(method, api_path, json_body) performs one REST request and returns
    (HTTP status, JSON response). No retries that can overwrite a newer state.
    """
    if not REPO_NAME.fullmatch(repository):
        raise StatePublicationError("Invalid GitHub repository")
    candidate = validate_state(candidate, season)
    path = f"/repos/{repository}/contents/odds-buffer/{season}.json"
    code, remote_file = call("GET", f"{path}?ref={STATE_BRANCH}", None)
    if code == 200:
        remote, sha = _decode_file(remote_file, season)
        _assert_not_stale(candidate, remote)
        if candidate == remote:
            return "noop"
    elif code == 404:
        if not bootstrap:
            raise StatePublicationError("Technical state file missing; explicitly bootstrap first")
        # Fail closed when only the branch (rather than the state file) is missing.
        ref_code, _ = call("GET", f"/repos/{repository}/git/ref/heads/{STATE_BRANCH}", None)
        if ref_code != 200:
            raise StatePublicationError("Dedicated odds state branch is missing")
        sha = None
    else:
        raise StatePublicationError(f"Could not read technical state: HTTP {code}")

    value: dict[str, Any] = {
        "message": f"state(odds): semantic season {season} observation",
        "branch": STATE_BRANCH,
        "content": base64.b64encode(
            (json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            .encode("utf-8")
        ).decode("ascii"),
    }
    if sha is not None:
        value["sha"] = sha
    code, _ = call("PUT", path, value)
    if code not in (200, 201):
        # Includes 409/422 CAS race and protection/auth failures: never retry
        # the stale state without a fresh observation against the new baseline.
        raise StatePublicationError(f"Isolated odds state write rejected (HTTP {code})")
    return "published"


def github_api_call(token: str) -> Callable[[str, str, dict | None], tuple[int, dict]]:
    if not token:
        raise StatePublicationError("GITHUB_TOKEN is required")
    def call(method: str, path: str, body: dict | None) -> tuple[int, dict]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            "https://api.github.com" + path, data=payload, method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "fantasy-app-odds-state-publisher/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            try:
                return error.code, json.loads(error.read().decode("utf-8"))
            except (ValueError, UnicodeError):
                return error.code, {}
    return call


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--state", type=Path, required=True,
                        help="newly computed durable state file, outside main repository")
    parser.add_argument("--bootstrap", action="store_true",
                        help="explicitly allow the first state file on an existing state branch")
    args = parser.parse_args()
    try:
        repository = os.environ["GITHUB_REPOSITORY"]
        candidate = json.loads(args.state.read_text(encoding="utf-8"))
        result = publish_state(
            repository=repository, season=args.season,
            candidate=candidate, call=github_api_call(os.environ["GITHUB_TOKEN"]),
            bootstrap=args.bootstrap,
        )
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"odds_state_publish failed: {exc}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
