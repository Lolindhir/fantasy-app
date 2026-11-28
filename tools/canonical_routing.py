"""Dormant Combine routing and accepted Git-tree preflight (#1618 M2b).

This module does not publish or create partitions. Production activation and
verified new-season admission are separate gates; no environment override.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Mapping

if __package__:
    from .data_roots import DATA_CANONICAL_ROOT, DATA_SOURCE_ROOT
else:
    from data_roots import DATA_CANONICAL_ROOT, DATA_SOURCE_ROOT

COMBINE_DATASET = "nfl/combine"
_SEASON_FILE = re.compile(r"([1-9][0-9]{3})\.json")
_COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class RouteMode(Enum):
    LEGACY = "legacy"
    TRANSITION = "transition"
    CANONICAL = "canonical"


def _season(season: int) -> None:
    if type(season) is not int or not 1000 <= season <= 9999:
        raise ValueError(f"Invalid canonical season: {season!r}")


@dataclass(frozen=True)
class FamilyRouting:
    mode: RouteMode = RouteMode.LEGACY
    legacy_exceptions: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.mode, RouteMode):
            raise ValueError("Invalid family route mode")
        if type(self.legacy_exceptions) is not frozenset:
            raise ValueError("Legacy exceptions must be immutable")
        for season in self.legacy_exceptions:
            _season(season)
        if self.mode is not RouteMode.TRANSITION and self.legacy_exceptions:
            raise ValueError("Legacy exceptions require transition mode")

    def relative_path(self, dataset: str, season: int) -> Path:
        if dataset != COMBINE_DATASET:
            raise ValueError(f"Unsupported canonical dataset: {dataset!r}")
        _season(season)
        legacy = self.mode is RouteMode.LEGACY or season in self.legacy_exceptions
        root = DATA_SOURCE_ROOT if legacy else DATA_CANONICAL_ROOT
        return Path(root, *COMBINE_DATASET.split("/"), f"{season}.json")


# Remains legacy until the separately approved cutover.
COMBINE_ROUTING = FamilyRouting()


def _git(root: Path, *args: str) -> bytes:
    # Disable replacement objects: accepted bytes must come from the pinned tree.
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "-C", str(root), *args],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("Cannot verify accepted Git tree: " + " ".join(args)) from exc


def _real_route(root: Path, relative: Path) -> Path:
    path = root
    for index, part in enumerate(relative.parts):
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Symlink in canonical partition route: {path}")
        if index < len(relative.parts) - 1 and path.exists() and not path.is_dir():
            raise ValueError(f"Non-directory parent in canonical partition route: {path}")
    return path


@dataclass(frozen=True)
class AcceptedPartition:
    path: Path
    blob: str


@dataclass(frozen=True)
class AcceptedSnapshot:
    commit: str
    partitions: Mapping[int, AcceptedPartition]

    def path_for(self, season: int) -> Path:
        _season(season)
        if season not in self.partitions:
            raise ValueError(f"Unadmitted Combine season: {season}")
        return self.partitions[season].path

    def require_existing_candidates(self, seasons: set[int]) -> None:
        """For the existing-only checkpoint, require complete accepted coverage.

        Future verified admissions must be handled explicitly, not by this method.
        """
        for season in seasons:
            _season(season)
        if seasons != set(self.partitions):
            raise ValueError("Candidate seasons differ from accepted inventory")


def preflight_accepted_combine(
    repo_root: Path, base_commit: str, routing: FamilyRouting = COMBINE_ROUTING,
) -> AcceptedSnapshot:
    """Read-only preflight of a pinned checked-out commit and its actual bytes.

    Never use the index or the working tree to decide which seasons are accepted.
    Run only in isolated complete worktrees for M2b; sparse/scoped production
    materializers must not call this until an explicit cutover.
    """
    if not isinstance(base_commit, str) or not _COMMIT.fullmatch(base_commit):
        raise ValueError("A full pinned commit object ID is required")
    root = repo_root.absolute()
    if root.resolve() != root or not root.is_dir():
        raise ValueError("A real repository root is required")
    if Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()) != root:
        raise ValueError("Preflight must use the repository root")
    if _git(root, "rev-parse", "--verify", "HEAD").decode().strip() != base_commit:
        raise ValueError("Checkout does not match pinned commit")
    if _git(root, "cat-file", "-t", base_commit).strip() != b"commit":
        raise ValueError("Pinned object is not a commit")

    directories = [Path(name, *COMBINE_DATASET.split("/"))
                   for name in (DATA_SOURCE_ROOT, DATA_CANONICAL_ROOT)]
    accepted: dict[int, AcceptedPartition] = {}
    # Use recursive tree entries to detect unexpected nested paths as well.
    listing = _git(root, "ls-tree", "-r", "-z", base_commit, "--",
                   *(path.as_posix() for path in directories))
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        header, raw_name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode("ascii").split()
        relative = Path(raw_name.decode("utf-8"))
        match = _SEASON_FILE.fullmatch(relative.name)
        if (mode != "100644" or kind != "blob" or not match
                or relative.parent not in directories):
            raise ValueError(f"Invalid tracked Combine entry: {relative}")
        season = int(match.group(1))
        if season in accepted or relative != routing.relative_path(COMBINE_DATASET, season):
            raise ValueError(f"Duplicate or wrong tracked Combine route: {relative}")
        path = _real_route(root, relative)
        if not path.is_file():
            raise FileNotFoundError(f"Expected Combine partition absent: {path}")
        payload_bytes = path.read_bytes()
        if payload_bytes != _git(root, "cat-file", "blob", blob):
            raise ValueError(f"Combine partition differs from accepted Git blob: {path}")
        payload = json.loads(payload_bytes)
        if (not isinstance(payload, dict) or type(payload.get("Season")) is not int
                or payload["Season"] != season or type(payload.get("Finalized")) is not bool
                or not isinstance(payload.get("Records"), list)):
            raise ValueError(f"Invalid accepted Combine payload: {path}")
        accepted[season] = AcceptedPartition(path, blob)

    if routing.mode is RouteMode.TRANSITION and not routing.legacy_exceptions <= accepted.keys():
        raise ValueError("Legacy exception is not in the accepted inventory")
    # Inspect both physical directories, including untracked/broken symlinks.
    expected_paths = {partition.path for partition in accepted.values()}
    for relative in directories:
        directory = _real_route(root, relative)
        if directory.exists():
            if not directory.is_dir():
                raise ValueError(f"Combine route is not a directory: {directory}")
            for path in directory.iterdir():
                if path not in expected_paths:
                    raise ValueError(f"Unexpected Combine route entry: {path}")
    # The index is not the authority, but staged changes in this family are
    # not a valid input to a read-before-write transaction. In particular,
    # git rm --cached can leave the working bytes intact after staging a delete.
    staged = _git(root, "diff", "--cached", "--name-only", "-z", base_commit, "--",
                  *(path.as_posix() for path in directories))
    if staged:
        raise ValueError("Staged Combine changes differ from the accepted Git tree")
    return AcceptedSnapshot(base_commit, MappingProxyType(accepted))
