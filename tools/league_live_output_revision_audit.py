#!/usr/bin/env python3
"""G5 GET-only immutable Git-tree output inventory for a named commit (#1263).

This is NOT a successful-run receipt, independently verified consumer parity,
provider freshness, complete future-draft coverage or safe-to-skip proof.
No production workflow imports this module.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import PurePosixPath
from typing import Any, Callable

ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from tools import audit_workflow_job_costs as github
from tools import league_live_shadow_gate as shadow

SHA = re.compile(r"^[0-9a-f]{40}$")
LEAGUE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
YEAR_FILE = re.compile(r"^(20\d\d|21\d\d)\.json$")
WEEK_FILE = re.compile(r"^(\d\d)\.json$")
OUTPUT_PREFIXES = (
    "data-derived/league-drafts", "data-derived/league-transactions",
    "data-derived/player-week-fantasy", "data-derived/team-week-performance",
)
APP_FILES = tuple(p for p in shadow.STAGE_OUTPUTS["league"] if p.endswith(".json"))


class SnapshotError(ValueError):
    """Missing, inconsistent, ambiguous or malformed immutable Git evidence."""


class Snapshot:
    """Resolve actual tree entries and selected small JSON blobs at one Git commit."""

    def __init__(self, fetch: github.Fetcher, commit_sha: str):
        if not isinstance(commit_sha, str) or SHA.fullmatch(commit_sha) is None:
            raise SnapshotError("invalid-immutable-commit-sha")
        self.fetch = fetch
        self.commit_sha = commit_sha
        commit = fetch(f"commits/{commit_sha}", {})
        details = commit.get("commit") if isinstance(commit, dict) else None
        tree = details.get("tree") if isinstance(details, dict) else None
        root = tree.get("sha") if isinstance(tree, dict) else None
        if commit.get("sha") != commit_sha or not isinstance(root, str) or not SHA.fullmatch(root):
            raise SnapshotError("commit-tree-not-independently-resolved")
        self.root_sha = root
        self.trees: dict[str, dict[str, dict[str, Any]]] = {}

    def tree(self, sha: str) -> dict[str, dict[str, Any]]:
        if sha in self.trees:
            return self.trees[sha]
        data = self.fetch(f"git/trees/{sha}", {})
        if (not isinstance(data, dict) or data.get("sha") != sha
                or data.get("truncated") is True or not isinstance(data.get("tree"), list)):
            raise SnapshotError("incomplete-or-wrong-git-tree")
        rows: dict[str, dict[str, Any]] = {}
        for item in data["tree"]:
            if not isinstance(item, dict):
                raise SnapshotError("malformed-git-tree-entry")
            name, obj_sha, typ = item.get("path"), item.get("sha"), item.get("type")
            if (not isinstance(name, str) or not name or "/" in name or
                    name in {".", ".."} or name in rows or
                    not isinstance(obj_sha, str) or not SHA.fullmatch(obj_sha) or
                    typ not in {"tree", "blob"}):
                raise SnapshotError("invalid-or-duplicate-git-tree-entry")
            rows[name] = item
        self.trees[sha] = rows
        return rows

    def entry(self, path: str) -> dict[str, Any]:
        if (not isinstance(path, str) or not path or
                PurePosixPath(path).is_absolute() or
                any(part in {".", "..", ""} for part in path.split("/"))):
            raise SnapshotError("unsafe-repository-path")
        current = self.root_sha
        for index, part in enumerate(path.split("/")):
            row = self.tree(current).get(part)
            if row is None:
                raise SnapshotError("required-git-entry-missing:" + path)
            if index < len(path.split("/")) - 1:
                if row["type"] != "tree":
                    raise SnapshotError("expected-git-tree:" + path)
                current = row["sha"]
        return row

    def directory(self, path: str) -> dict[str, dict[str, Any]]:
        row = self.entry(path)
        if row["type"] != "tree":
            raise SnapshotError("expected-git-directory:" + path)
        return self.tree(row["sha"])

    def blob_id(self, path: str) -> str:
        row = self.entry(path)
        if row["type"] != "blob":
            raise SnapshotError("expected-git-blob:" + path)
        return row["sha"]

    def json(self, path: str) -> dict[str, Any]:
        sha = self.blob_id(path)
        blob = self.fetch(f"git/blobs/{sha}", {})
        if (not isinstance(blob, dict) or blob.get("sha") != sha or
                blob.get("encoding") != "base64" or
                not isinstance(blob.get("content"), str) or
                type(blob.get("size")) is not int or
                not 1 <= blob["size"] <= 262144):
            raise SnapshotError("missing-or-invalid-canonical-blob:" + path)
        try:
            # GitHub's Git Blobs API legitimately line-wraps base64 content.
            # Normalize only CRLF/LF separators; strict base64 validation and
            # the independently recomputed Git blob SHA-1 remain mandatory.
            encoded = blob["content"].replace("\r\n", "\n").replace("\n", "")
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise SnapshotError("canonical-blob-unreadable:" + path) from exc
        if len(data) != blob["size"] or hashlib.sha1(
            b"blob " + str(len(data)).encode() + b"\0" + data
        ).hexdigest() != sha:
            raise SnapshotError("canonical-blob-digest-mismatch:" + path)
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError) as exc:
            raise SnapshotError("canonical-json-unreadable:" + path) from exc
        if not isinstance(value, dict):
            raise SnapshotError("canonical-json-not-object:" + path)
        return value


def _years(rows: dict[str, dict[str, Any]], base: str, output: dict[str, str],
           *, weekly: bool = False) -> list[int]:
    observed: list[int] = []
    for name, entry in sorted(rows.items()):
        match = YEAR_FILE.fullmatch(name) if not weekly else re.fullmatch(r"(20\d\d|21\d\d)", name)
        if match is None:
            raise SnapshotError("unexpected-derived-partition:" + base + "/" + name)
        year = int(match.group(1))
        if weekly and entry["type"] != "tree" or not weekly and entry["type"] != "blob":
            raise SnapshotError("invalid-derived-partition-type:" + name)
        observed.append(year)
        if not weekly:
            output[base + "/" + name] = entry["sha"]
    return observed


def audit_immutable_outputs(fetch: github.Fetcher, commit_sha: str) -> dict[str, Any]:
    """Prove Git objects for selected output surfaces under one immutable commit.

    Only canonical metadata and manifest are independently decoded and
    content-digest verified. Dynamic Draft coverage below is a conservative
    minimum; provider-specific future partitions and historical recovery
    cannot be certified by directory presence. Never return safeToSkip=true.
    """
    result: dict[str, Any] = {
        "schemaVersion": 1, "mode": "offline-git-blob-output-inventory",
        "revision": commit_sha, "status": "blocked", "reasonCodes": [],
        "selectedGitOutputBlobIdsVerified": False,
        "metadataMinimumDraftYearsVerified": False,
        "completeOutputInventoryVerified": False,
        "providerDraftHorizonVerified": False,
        "outputSemanticParityVerified": False,
        "successfulProducerRunVerified": False,
        "independentProviderFreshnessVerified": False,
        "independentNflFinalityVerified": False,
        "recoveryClean": False, "raceFree": False,
        "safeToSkip": False, "enforced": False,
    }
    try:
        snapshot = Snapshot(fetch, commit_sha)
        meta_rows = snapshot.directory("data-meta")
        league_ids = sorted(meta_rows)
        if (not league_ids or any(not LEAGUE.fullmatch(name)
               or row["type"] != "tree" for name, row in meta_rows.items())):
            raise SnapshotError("canonical-league-collection-unknown")
        source_leagues = snapshot.directory("data-source/leagues")
        if set(source_leagues) != set(league_ids) or any(
            row["type"] != "tree" for row in source_leagues.values()
        ):
            raise SnapshotError("source-metadata-league-scope-mismatch")
        for prefix in OUTPUT_PREFIXES:
            rows = snapshot.directory(prefix)
            if set(rows) != set(league_ids) or any(
                row["type"] != "tree" for row in rows.values()
            ):
                raise SnapshotError("missing-or-extra-derived-league:" + prefix)

        output: dict[str, str] = {}
        coverage: list[dict[str, Any]] = []
        for league in league_ids:
            metadata = snapshot.json(f"data-meta/{league}/metadata.json")
            manifest = snapshot.json(f"data-source/leagues/{league}/manifest.json")
            season_id = manifest.get("CurrentCanonicalLeagueSeasonID")
            current = (int(season_id.rsplit("-", 1)[1])
                       if isinstance(season_id, str)
                       and re.fullmatch(re.escape(league) + r"-(20\d\d|21\d\d)", season_id)
                       else None)
            if (metadata.get("CanonicalLeagueID") != league or
                    metadata.get("SchemaVersion") != 1 or
                    manifest.get("CanonicalLeagueID") != league or
                    type(current) is not int or
                    metadata.get("CurrentProviderLeagueID") != manifest.get("CurrentProviderLeagueID")):
                raise SnapshotError("metadata-manifest-season-identity-mismatch:" + league)
            draft = metadata.get("Drafts")
            if not isinstance(draft, dict):
                raise SnapshotError("missing-draft-configuration:" + league)
            count = draft.get("UpcomingDraftCount")
            if (type(count) is not int or not 1 <= count <= 30 or
                    draft.get("UpcomingDraftCountMode") != "PerDraftType" or
                    not isinstance(draft.get("Types"), list) or not draft["Types"]):
                raise SnapshotError("unsupported-draft-season-horizon:" + league)
            seasons = manifest.get("Seasons")
            if (not isinstance(seasons, list) or
                    sum(isinstance(item, dict) and item.get("Season") == current for item in seasons) != 1):
                raise SnapshotError("current-season-not-in-canonical-manifest:" + league)

            years_by_product: dict[str, list[int]] = {}
            for prefix in OUTPUT_PREFIXES:
                directory = f"{prefix}/{league}"
                rows = snapshot.directory(directory)
                weekly = prefix.endswith(("/team-week-performance", "/player-week-fantasy"))
                years = _years(rows, directory, output, weekly=weekly)
                years_by_product[prefix.rsplit("/", 1)[-1]] = years
                if current not in years:
                    raise SnapshotError("current-product-season-missing:" + directory)
                if weekly:
                    for year in years:
                        week_dir = f"{directory}/{year}"
                        week_rows = snapshot.directory(week_dir)
                        if not week_rows:
                            raise SnapshotError("empty-week-partitions:" + week_dir)
                        for name, row in week_rows.items():
                            match = WEEK_FILE.fullmatch(name)
                            if (match is None or not 1 <= int(match.group(1)) <= 23
                                    or row["type"] != "blob"):
                                raise SnapshotError("invalid-week-partition:" + week_dir + "/" + name)
                            output[week_dir + "/" + name] = row["sha"]
            expected_drafts = set(range(current, current + count + 1))
            if not expected_drafts.issubset(years_by_product["league-drafts"]):
                raise SnapshotError("metadata-minimum-future-drafts-missing:" + league)
            coverage.append({
                "league": league, "currentSeason": current,
                "minimumConfiguredDraftYears": sorted(expected_drafts),
                "observedDraftYears": years_by_product["league-drafts"],
                "observedTransactionYears": years_by_product["league-transactions"],
                "observedTwpYears": years_by_product["team-week-performance"],
                "observedPwfYears": years_by_product["player-week-fantasy"],
            })
        for path in APP_FILES:
            output[path] = snapshot.blob_id(path)
        if len(output) != len(set(output)) or not output:
            raise SnapshotError("duplicate-or-missing-output-identity")
        digest = hashlib.sha256(
            json.dumps(sorted(output.items()), separators=(",", ":")).encode()
        ).hexdigest()
        result.update(
            status="immutable-selected-output-blobs-observed",
            selectedGitOutputBlobIdsVerified=True,
            metadataMinimumDraftYearsVerified=True,
            gitTreeSha=snapshot.root_sha,
            canonicalLeagueIDs=league_ids,
            leagueCoverage=coverage,
            selectedOutputCount=len(output),
            selectedOutputFingerprint=digest,
            selectedOutputBlobs=output,
        )
    except (github.AuditError, SnapshotError, KeyError, ValueError, TypeError,
            AttributeError, OSError) as exc:
        result["reasonCodes"] = [type(exc).__name__ + ": " + str(exc)]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args(argv)
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo)
            or not SHA.fullmatch(args.commit_sha)):
        parser.error("valid --repo and 40-character --commit-sha required")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Missing read-only GitHub API token", file=sys.stderr)
        return 2
    try:
        result = audit_immutable_outputs(github.api_fetch(args.repo, token), args.commit_sha)
    except (github.AuditError, ValueError) as exc:
        print("Offline output audit unavailable: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["selectedGitOutputBlobIdsVerified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
