#!/usr/bin/env python3
"""Read-only restore probe for the Shared Derived products of every league (#471).

Each product is rebuilt in two isolated temporary roots and compared with the published files:

* empty:  only data-source, data-meta and public/requests are visible; the product is built twice.
* normal: published data-derived plus historical Standings are visible, as in a
          productive run; the product is built once. The published Players hold
          seed was retired by ADR-076 and is never copied or loaded.
* published: the files in the repository.

Per product (and league) the three-way comparison gives one status:

* ready:             empty == normal == published, the second empty pass is a no-op.
* stale-published:   empty == normal, only the published files are behind (hint, not an error).
* latent-blocker:    the product only builds with the transitional Standings input (Issue #987, hint).
* restore-defect:    empty != normal, the product silently depends on previously generated output (error).
* nondeterministic:  the second empty pass changed output (error).
* blocked:           a source is not ready or a build failed (error).

This is NOT a publisher; nothing in the repository is written. An explicit
--schedule-outlook-candidate mode audits the proposed Outlook product entirely
in memory after shadow-only PWF/TWP/SeasonStatistics rebuilds. It is not a
production model selection or publication approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_META_ROOT, DATA_SOURCE_ROOT
from derived_data import (
    LEAGUE_DRAFTS, LEAGUE_RIVALRY, LEAGUE_STANDINGS, LEAGUE_TRANSACTIONS, SEASON_STATISTICS,
    materialize_league_history, materialize_league_rivalry, materialize_league_standings, materialize_player_valuation, materialize_season_statistics, serialize,
)
from historical_pwf_batch import materialize_historical
from league_metadata import list_league_ids, load_league_metadata
from league_schedule_outlook_preview import preview_all
from derived_data_lib.league_schedule_outlook import assemble
from derived_data_lib.models.registry import get_model
from league_standings_sources import current_season, manifest
from matchup_context_materialize import EXPECTED_ERRORS as MATCHUP_CONTEXT_ERRORS, PRODUCT as MATCHUP_CONTEXT, materialize as materialize_matchup_context
from datetime import datetime, timezone
from weekly_recaps_materialize import EXPECTED_ERRORS as WEEKLY_RECAPS_ERRORS, PRODUCT as WEEKLY_RECAPS, materialize as materialize_weekly_recaps
from nfl_games_materialize import discover_seasons, materialize as materialize_nfl_games
from nfl_injuries_phase import plan_injury_phase
from team_week_performance_materialize import materialize_all_finalized

PLAYER_VALUATION = "player-valuation"
PLAYER_WEEK_FANTASY = "player-week-fantasy"
TEAM_WEEK_PERFORMANCE = "team-week-performance"
NFL_GAMES = "nfl-games"
NFL_INJURIES = "nfl-injuries"

# Stable build and report order, upstream before downstream; official TeamWeekPerformance is independent of PWF score
# parity. The clean-root variant starts empty, so a product that reads another persisted product (awards-v2/v3 of
# league-standings read season-statistics, which reads PlayerWeekFantasy) must be built after it, exactly like the
# productive-like variant where the published products are already visible.
PRODUCTS = (
    PLAYER_VALUATION, LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS,
    PLAYER_WEEK_FANTASY, TEAM_WEEK_PERFORMANCE, NFL_GAMES, NFL_INJURIES, SEASON_STATISTICS,
    LEAGUE_STANDINGS, LEAGUE_RIVALRY, MATCHUP_CONTEXT, WEEKLY_RECAPS,
)
GLOBAL_PRODUCTS = frozenset({NFL_GAMES, NFL_INJURIES})

FAILING = frozenset({"blocked", "nondeterministic", "restore-defect"})
HINTS = frozenset({"stale-published", "latent-blocker"})
LATENT_STANDINGS_ISSUE = "#987"
STANDINGS_MARKER = "transitional Standings"
# Only the historical Standings shadow is copied; the retired player seed is excluded.
PUBLISHED_APP_FILES = ("Standings.json",)
EXAMPLE_LIMIT = 12

Unit = tuple[str, str | None]


def unit_key(unit: Unit) -> str:
    product, league = unit
    return product if league is None else f"{product}/{league}"


def _files(root: Path, unit: Unit) -> dict[str, str]:
    """Relative path -> sha256 of every product file (of one league for league products)."""
    product, league = unit
    directory = root / DATA_DERIVED_ROOT / product
    if league is not None:
        single = directory / f"{league}.json"
        if single.is_file():  # one file per league (league-rivalry), no league directory
            return {single.name: hashlib.sha256(single.read_bytes()).hexdigest()}
        directory = directory / league
    if not directory.is_dir():
        return {}
    skip: Path | None = None
    if product == MATCHUP_CONTEXT:
        # The running season's documents depend on the clock through the Decision Windows (ADR-089): a current snapshot,
        # not byte-reproducible from a clean root. Every completed season is covered.
        skip = directory / str(current_season(manifest(root, league)))
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*.json"))
        if skip is None or skip not in p.parents
    }


def _written(summary: dict[str, Any]) -> int:
    return sum(int(season["Written"]) for season in summary["Seasons"])


def _held(summary: dict[str, Any]) -> int:
    return sum(int(x.get("HeldRowsAcrossSnapshots", 0)) for x in summary["Seasons"])


def _blocked_reason(report: dict[str, Any]) -> str:
    reasons = [str(w.get("Reason")) for w in report.get("Weeks", []) if w.get("Status") == "blocked"]
    return f"{report['BlockedCount']} blocked weeks, first: {reasons[:2]}"


def discover_injury_seasons(root: Path) -> list[int]:
    """Use canonical Source season directories, never published Derived output, for coverage."""
    folder = root / DATA_SOURCE_ROOT / "nfl" / "injuries"
    if not folder.is_dir():
        raise ValueError("Canonical NFL injuries Source directory is missing")
    seasons = sorted(
        int(p.name) for p in folder.iterdir()
        if p.is_dir() and len(p.name) == 4 and p.name.isdigit()
    )
    if not seasons:
        raise ValueError("No canonical NFL injuries seasons to restore")
    return seasons


def _build_nfl_injuries(root: Path) -> int:
    """Build into the isolated shadow from the *real* canonical Source root.

    The shadow intentionally symlinks its read-only data-source directory to the
    real repository. The Injury production reader prohibits symlinked ancestors,
    so resolve that existing audit-owned Source link before reading; Derived
    output always stays inside the shadow, never in the real repository.
    """
    source_root = (root / DATA_SOURCE_ROOT).resolve().parent
    written = 0
    for season in discover_injury_seasons(root):
        relative = f"{DATA_DERIVED_ROOT}/{NFL_INJURIES}/{season}.json"
        artifacts = plan_injury_phase(source_root, season, "derived")
        if set(artifacts) != {relative} or not isinstance(artifacts[relative], bytes):
            raise ValueError(f"Unexpected NFL injuries Derived output for {season}")
        target = root / relative
        candidate = artifacts[relative]
        if target.is_file() and target.read_bytes() == candidate:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(candidate)
        written += 1
    return written


def _build(unit: Unit, root: Path) -> tuple[int, int]:
    """Run the productive generator of one unit in `root`; return (writes, held rows)."""
    product, league = unit
    output = root / DATA_DERIVED_ROOT
    if product == PLAYER_VALUATION:
        summary = materialize_player_valuation(root, output, league, None, False)
        return _written(summary), _held(summary)
    if product in (LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS):
        return _written(materialize_league_history(root, output, league, product, None, False)), 0
    if product == LEAGUE_STANDINGS:
        return _written(materialize_league_standings(root, output, league, None, False)), 0
    if product == LEAGUE_RIVALRY:
        return _written(materialize_league_rivalry(root, output, league, None, False)), 0
    if product == SEASON_STATISTICS:
        return _written(materialize_season_statistics(root, output, league, None, False)), 0
    if product == PLAYER_WEEK_FANTASY:
        report = materialize_historical(root, league_id=league, write=True)
        if report["BlockedCount"]:
            raise ValueError(_blocked_reason(report))
        return int(report.get("ChangedCount", 0)), 0
    if product == TEAM_WEEK_PERFORMANCE:
        report = materialize_all_finalized(root, league_id=league, write=True, require_pwf=False)
        if report["BlockedCount"]:
            raise ValueError(_blocked_reason(report))
        return int(report["ChangedCount"]), 0
    if product == NFL_GAMES:
        return sum(
            int(materialize_nfl_games(root, season, write=True)["Written"])
            for season in discover_seasons(root)
        ), 0
    if product == NFL_INJURIES:
        return _build_nfl_injuries(root), 0
    if product == MATCHUP_CONTEXT:
        try:
            summaries = materialize_matchup_context(root, output, league, "history", datetime.now(timezone.utc))
        except MATCHUP_CONTEXT_ERRORS as error:
            raise ValueError(f"{type(error).__name__}: {error}") from error
        return sum(int(x["Written"]) for x in summaries), 0
    if product == WEEKLY_RECAPS:
        # Pure function of canonical facts and the products built before it (team-week-performance, league-standings): every season is covered.
        try:
            summaries = materialize_weekly_recaps(root, output, league, "all")
        except WEEKLY_RECAPS_ERRORS as error:
            raise ValueError(f"{type(error).__name__}: {error}") from error
        return sum(int(x["Written"]) for x in summaries), 0
    raise ValueError(f"Unknown product: {product}")


def _run_variant(
    shadow: Path, units: list[Unit], *, passes: int,
) -> dict[Unit, dict[str, Any]]:
    results: dict[Unit, dict[str, Any]] = {}
    for unit in units:
        product, league = unit
        entry: dict[str, Any] = {"error": None, "writes": [], "files": [], "held": 0}
        results[unit] = entry
        try:
            for index in range(passes):
                writes, held = _build(unit, shadow)
                if index == 0:
                    entry["held"] = held
                entry["writes"].append(writes)
                entry["files"].append(_files(shadow, unit))
            if not entry["files"][0]:
                raise ValueError("Materializer produced no product snapshots")
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            entry["error"] = str(exc) or type(exc).__name__
    return results


def _diff(left: dict[str, str], right: dict[str, str]) -> dict[str, list[str]]:
    return {
        "Differing": sorted(k for k in left.keys() & right.keys() if left[k] != right[k]),
        "OnlyLeft": sorted(left.keys() - right.keys()),
        "OnlyRight": sorted(right.keys() - left.keys()),
    }


def _classify(empty: dict[str, Any], normal: dict[str, Any], published: dict[str, str]) -> dict[str, Any]:
    """Three-way comparison of one unit; see the module docstring for the statuses."""
    latent = bool(empty["error"]) and STANDINGS_MARKER in empty["error"] and not normal["error"]
    result: dict[str, Any] = {"PreviouslyPublishedCount": len(published)}
    if normal["error"] or (empty["error"] and not latent):
        result["Status"] = "blocked"
        result["Reason"] = (
            f"Productive-like build failed: {normal['error']}" if normal["error"]
            else f"Clean-root build failed: {empty['error']}"
        )
        return result
    normal_files = normal["files"][0]
    result["HeldRowsAcrossSnapshots"] = normal["held"]
    against_published = _diff(normal_files, published)
    result["ChangedVsPublishedCount"] = len(against_published["Differing"])
    result["MissingInPublishedCount"] = len(against_published["OnlyLeft"])
    result["StalePublishedExamples"] = (against_published["Differing"] + against_published["OnlyLeft"])[:EXAMPLE_LIMIT]
    stale = bool(against_published["Differing"] or against_published["OnlyLeft"])
    if latent:
        result["Status"] = "latent-blocker"
        result["LatentBlocker"] = LATENT_STANDINGS_ISSUE
        result["Reason"] = (
            f"Builds only with the transitional Standings input ({LATENT_STANDINGS_ISSUE}): {empty['error']}"
        )
        return result
    first, second = empty["files"]
    result["RebuiltCount"] = len(first)
    result["SecondPassWrites"] = empty["writes"][1]
    result["SecondPassByteIdentical"] = first == second
    if empty["writes"][1] != 0 or first != second:
        result["Status"] = "nondeterministic"
        result["Reason"] = "Second clean-root pass changed reconstructed output"
        return result
    # A published file that the normal run left untouched and the empty run cannot build is an orphan,
    # not a hidden dependency: it is reported as stale instead of a defect.
    versus = _diff(first, normal_files)
    orphans = [k for k in versus["OnlyRight"] if normal_files[k] == published.get(k)]
    defects = {
        "Differing": versus["Differing"],
        "OnlyEmpty": versus["OnlyLeft"],
        "OnlyNormal": [k for k in versus["OnlyRight"] if k not in orphans],
    }
    result["RestoreDefectCount"] = sum(len(v) for v in defects.values())
    if result["RestoreDefectCount"]:
        result["Status"] = "restore-defect"
        result["RestoreDefectExamples"] = {k: v[:EXAMPLE_LIMIT] for k, v in defects.items() if v}
        result["Reason"] = "Clean-root output differs from the productive-like run"
        return result
    result["OrphanedPublishedCount"] = len(orphans)
    if stale or orphans:
        result["Status"] = "stale-published"
        result["Reason"] = "Published files are behind; clean-root and productive-like output agree"
    else:
        result["Status"] = "ready"
    return result


def _prepare(shadow: Path, source: Path, *, published: bool) -> None:
    for name in (DATA_SOURCE_ROOT, DATA_META_ROOT):
        (shadow / name).symlink_to(source / name, target_is_directory=True)
    (shadow / "public/data").mkdir(parents=True)
    # PowerShell bridge of TeamWeekPerformance (existing FantasyRelevance slot rules).
    if (source / "public/requests").is_dir():
        (shadow / "public/requests").symlink_to(source / "public/requests", target_is_directory=True)
    derived = source / DATA_DERIVED_ROOT
    if published and derived.is_dir():
        shutil.copytree(derived, shadow / DATA_DERIVED_ROOT)
    else:
        (shadow / DATA_DERIVED_ROOT).mkdir()
    if published:
        for name in PUBLISHED_APP_FILES:
            if (source / "public/data" / name).is_file():
                shutil.copy2(source / "public/data" / name, shadow / "public/data" / name)


def audit(
    repo_root: Path, *, leagues: list[str] | None = None, candidate_model_id: str | None = None,
) -> dict[str, Any]:
    """Rebuild every product with and without existing Derived/App files and compare with the published ones.

    Live repository data-derived, public/data and workflow state remain untouched.
    """
    source = repo_root.resolve()
    for name in (DATA_SOURCE_ROOT, DATA_META_ROOT):
        if not (source / name).is_dir():
            raise ValueError(f"Missing required canonical root: {name}")
    league_ids = leagues or list_league_ids(source / DATA_META_ROOT)
    if not league_ids:
        raise ValueError("No league found in data-meta")
    if candidate_model_id is not None:
        get_model(candidate_model_id, kind="schedule-outlook")
    source_before = _schedule_outlook_source_witness(source) if candidate_model_id is not None else None
    advisory: dict[str, dict[str, Any]] = {}
    units: list[Unit] = [
        (product, None if product in GLOBAL_PRODUCTS else league)
        for product in PRODUCTS
        for league in ([None] if product in GLOBAL_PRODUCTS else league_ids)
    ]
    with tempfile.TemporaryDirectory(prefix="derived-clean-root-audit-") as empty_dir, \
         tempfile.TemporaryDirectory(prefix="derived-normal-root-audit-") as normal_dir:
        empty_root, normal_root = Path(empty_dir), Path(normal_dir)
        _prepare(empty_root, source, published=False)
        _prepare(normal_root, source, published=True)
        empty = _run_variant(empty_root, units, passes=2)
        normal = _run_variant(normal_root, units, passes=1)
        if candidate_model_id is not None:
            # Reuse the already rebuilt roots: no second PWF/TWP/Stats pass.
            for league_id in league_ids:
                try:
                    upstream = [(product, league_id) for product in (
                        PLAYER_WEEK_FANTASY, TEAM_WEEK_PERFORMANCE, SEASON_STATISTICS)]
                    for unit in upstream:
                        first, other = empty[unit], normal[unit]
                        if first["error"] or other["error"]:
                            raise ValueError(f"Upstream {unit_key(unit)} blocked: "
                                             f"{first['error'] or other['error']}")
                        if (len(first["files"]) != 2 or first["writes"][1] != 0
                                or first["files"][0] != first["files"][1]):
                            raise ValueError(f"Upstream {unit_key(unit)} second-pass no-op failed")
                    metadata = load_league_metadata(league_id, source / DATA_META_ROOT)
                    seasons = sorted(int(year) for year in metadata["Seasons"])
                    empty_digests = _schedule_outlook_candidate_digests(
                        empty_root, league_id, seasons, candidate_model_id)
                    normal_digests = _schedule_outlook_candidate_digests(
                        normal_root, league_id, seasons, candidate_model_id)
                    equal = empty_digests == normal_digests
                    advisory[league_id] = {
                        "Status": "candidate-pass" if equal else "restore-defect",
                        "CandidatePass": equal,
                        "SnapshotCount": len(empty_digests),
                        "Seasons": seasons,
                        "DigestDifferences": _diff(empty_digests, normal_digests) if not equal else {},
                        "ProviderFreshnessVerified": False,
                        "ReadyForPublication": False,
                    }
                except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
                    advisory[league_id] = {
                        "Status": "blocked-candidate", "CandidatePass": False,
                        "VerifiedCandidatePass": False, "Reason": str(exc),
                        "ProviderFreshnessVerified": False, "ReadyForPublication": False,
                    }
            # Verify the source trees only after all candidate preview reads,
            # not just after the upstream materializers.
            source_after = _schedule_outlook_source_witness(source)
            source_verified = source_before is not None and source_before == source_after
            for candidate in advisory.values():
                candidate["SourceRevisionVerified"] = source_verified
                candidate["SourceRevisionWitness"] = source_before if source_verified else None
                candidate["VerifiedCandidatePass"] = bool(candidate["CandidatePass"] and source_verified)
                if candidate["CandidatePass"]:
                    candidate["Status"] = ("verified-candidate" if source_verified
                                           else "unverified-candidate")
    results: dict[str, dict[str, Any]] = {}
    for unit in units:
        product, league = unit
        results[unit_key(unit)] = {
            "Product": product, "League": league,
            **_classify(empty[unit], normal[unit], _files(source, unit)),
        }
    failed = sorted(k for k, v in results.items() if v["Status"] in FAILING)
    report = {
        "Mode": "three-way-clean-root-probe",
        "Leagues": league_ids,
        "ReadOnly": True,
        "Published": False,
        "Scope": [unit_key(u) for u in units],
        "Products": results,
        "FailedProducts": failed,
        "HintProducts": {k: v["Status"] for k, v in sorted(results.items()) if v["Status"] in HINTS},
        "ReadyForFullRestore": not failed,
    }
    if candidate_model_id is not None:
        report["AdvisoryScheduleOutlookCandidate"] = advisory
        report["CandidateModelID"] = candidate_model_id
    return report


def _schedule_outlook_source_witness(root: Path) -> dict[str, str] | None:
    """Best-effort exact Git revision witness for canonical input roots.

    A revision witness proves the accepted committed input trees used in this
    checkout; it does NOT prove real-time provider freshness, observed historical
    snapshots or the future writer's ability to rebuild on a publication race.
    Missing Git context and any tracked/untracked changes fail closed.
    """
    def git(*args: str) -> str | None:
        try:
            process = subprocess.run(
                ["git", "-C", str(root), *args], capture_output=True, text=True,
                check=False, timeout=25,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return process.stdout.strip() if process.returncode == 0 else None

    commit = git("rev-parse", "--verify", "HEAD")
    source_tree = git("rev-parse", "--verify", "HEAD:data-source")
    metadata_tree = git("rev-parse", "--verify", "HEAD:data-meta")
    status = git("status", "--porcelain", "--untracked-files=all", "--", "data-source", "data-meta")
    if not all(isinstance(x, str) and len(x) == 40 and
               all(ch in "0123456789abcdef" for ch in x)
               for x in (commit, source_tree, metadata_tree)):
        return None
    if status is None or status:
        return None
    return {
        "RepositoryCommit": commit,
        "SourceTree": source_tree,
        "MetadataTree": metadata_tree,
    }


def _build_schedule_outlook_candidate_upstream(root: Path, league_id: str, seasons: list[int]) -> int:
    """Rebuild only selected seasons, in a temporary Derived root, in dependency order."""
    pwf = materialize_historical(root, league_id=league_id, seasons=seasons, write=True)
    if pwf["BlockedCount"]:
        raise ValueError(f"PlayerWeekFantasy upstream blocked: {_blocked_reason(pwf)}")
    twp = materialize_all_finalized(root, league_id=league_id, seasons=seasons,
                                  write=True, require_pwf=False)
    if twp["BlockedCount"]:
        raise ValueError(f"TeamWeekPerformance upstream blocked: {_blocked_reason(twp)}")
    stats = materialize_season_statistics(root, root / DATA_DERIVED_ROOT, league_id, seasons, False)
    return int(pwf["ChangedCount"]) + int(twp["ChangedCount"]) + _written(stats)


def _schedule_outlook_candidate_digests(
    shadow: Path, league_id: str, seasons: list[int], selected_model_id: str,
) -> dict[str, str]:
    """All final cutoffs, in memory only, from existing reconstructed upstream."""
    digests: dict[str, str] = {}
    for year in seasons:
        replay = preview_all(shadow, league_id, year)
        last = replay.get("LastLeagueScoredWeek")
        snapshots = replay.get("Snapshots")
        if type(last) is not int or last < 0 or not isinstance(snapshots, list) or len(snapshots) != last + 1:
            raise ValueError(f"Incomplete Schedule Outlook replay for {year}")
        for week, observation in enumerate(snapshots):
            document = assemble(observation, selected_model_id=selected_model_id)
            if document["AsOf"]["AfterWeek"] != week or document["Season"] != year:
                raise ValueError(f"Out-of-order Schedule Outlook cutoff {year}/{week}")
            name = f"{year}/after-week-{week:02d}.json"
            digests[name] = hashlib.sha256(serialize(document).encode("utf-8")).hexdigest()
    if not digests:
        raise ValueError("Schedule Outlook candidate replay produced no snapshots")
    return digests


def audit_schedule_outlook_candidate(
    repo_root: Path, league_id: str, *, seasons: list[int] | None = None, selected_model_id: str,
) -> dict[str, Any]:
    """Probe I5b's *candidate* product in memory, never in a persisted output path.

    Restores the existing PWF -> TWP -> season-statistics upstream in isolated
    empty/normal shadows, then assembles every final as-of outlook. The second
    empty pass checks upstream no-op and exact output digest stability. No
    ScheduleOutlook metadata selection, production writer or file is introduced.
    This is an explicit opt-in audit, not part of the routine restore gate.
    """
    source = repo_root.resolve()
    if not isinstance(league_id, str) or not league_id.strip():
        raise ValueError("Explicit canonical --league is required")
    for name in (DATA_SOURCE_ROOT, DATA_META_ROOT):
        if not (source / name).is_dir():
            raise ValueError(f"Missing required canonical root: {name}")
    if not isinstance(selected_model_id, str) or not selected_model_id:
        raise ValueError("An explicit candidate --model-id is required (not a metadata selection)")
    get_model(selected_model_id, kind="schedule-outlook")

    metadata = load_league_metadata(league_id, source / DATA_META_ROOT)
    configured = sorted(int(s) for s in metadata["Seasons"])
    selected = sorted(set(configured if seasons is None else seasons))
    if not selected or any(type(y) is not int or y not in configured for y in selected):
        raise ValueError(f"Requested season is not configured for {league_id}: {selected}")

    def build_once(shadow: Path) -> tuple[int, dict[str, str]]:
        writes = _build_schedule_outlook_candidate_upstream(shadow, league_id, selected)
        return writes, _schedule_outlook_candidate_digests(
            shadow, league_id, selected, selected_model_id)

    source_before = _schedule_outlook_source_witness(source)
    with tempfile.TemporaryDirectory(prefix="outlook-source-only-") as empty_dir, tempfile.TemporaryDirectory(prefix="outlook-normal-") as normal_dir:
        empty_root, normal_root = Path(empty_dir), Path(normal_dir)
        _prepare(empty_root, source, published=False)
        _prepare(normal_root, source, published=True)
        first_writes, first = build_once(empty_root)
        second_writes, second = build_once(empty_root)
        normal_writes, normal = build_once(normal_root)

    source_after = _schedule_outlook_source_witness(source)
    source_verified = source_before is not None and source_before == source_after
    second_identical = first == second and second_writes == 0
    roots_identical = first == normal
    return {
        "Mode": "schedule-outlook-candidate-source-only-restore",
        "ReadOnly": True,
        "Published": False,
        "CandidateModelID": selected_model_id,
        "ModelSelectedInDataMeta": False,
        "CanonicalLeagueID": league_id,
        "Seasons": selected,
        "SnapshotCount": len(first),
        "FirstPassUpstreamWrites": first_writes,
        "SecondPassUpstreamWrites": second_writes,
        "NormalPassUpstreamWrites": normal_writes,
        "SecondPassByteIdentical": second_identical,
        "EmptyAndNormalIdentical": roots_identical,
        "DigestDifferences": _diff(first, normal) if not roots_identical else {},
        "CandidatePass": second_identical and roots_identical,
        "CompleteConfiguredSeasonCoverage": selected == configured,
        "SourceRevisionVerified": source_verified,
        "VerifiedCandidatePass": second_identical and roots_identical and source_verified,
        "SourceRevisionWitness": source_before if source_verified else None,
        "ProviderFreshnessVerified": False,
        "ReadyForPublication": False,
    }


def render_summary(result: dict[str, Any]) -> str:
    """Markdown for the GitHub Job Summary: one row per unit, errors first, hints named."""
    failed = set(result["FailedProducts"])
    lines = [
        "### Shared Derived restore gate",
        "",
        f"Result: **{'FAIL' if failed else 'PASS'}** ({len(result['Products'])} units, leagues: "
        f"{', '.join(result['Leagues']) or 'none'}). Read-only; nothing was written.",
        "",
        "| Unit | Status | Detail |",
        "|---|---|---|",
    ]
    for key, item in sorted(result["Products"].items(), key=lambda kv: (kv[0] not in failed, kv[0])):
        detail = str(item.get("Reason") or "").replace("|", "/").replace("\n", " ")
        lines.append(f"| {key} | {item['Status']} | {detail} |")
    if result["HintProducts"]:
        lines += ["", "Hints (no failure): " + ", ".join(
            f"{k} = {v}" for k, v in result["HintProducts"].items())]
    if "AdvisoryScheduleOutlookCandidate" in result:
        lines += ["", "### League Schedule Outlook (read-only candidate; advisory)",
                  "", "| League | Candidate status | Cutoffs | Evidence |",
                  "|---|---|---:|---|"]
        for league, candidate in sorted(result["AdvisoryScheduleOutlookCandidate"].items()):
            reason = str(candidate.get("Reason") or
                         ("clean committed Source roots" if candidate.get("SourceRevisionVerified")
                          else "source revision not verified")).replace("|", "/").replace("\n", " ")
            lines.append(f"| {league} | {candidate['Status']} | "
                         f"{candidate.get('SnapshotCount', 0)} | {reason} |")
        lines += ["", "Candidate findings do not alter the existing product restore gate. "
                  "No Outlook snapshot has been published."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", action="append", help="CanonicalLeagueID (repeatable); default: every league in data-meta")
    parser.add_argument("--github-summary", action="store_true",
                        help="append a Markdown table to $GITHUB_STEP_SUMMARY (CI restore gate)")
    parser.add_argument("--schedule-outlook-candidate", action="store_true",
                        help="opt-in source-only, in-memory Schedule Outlook restore/replay (not a publisher)")
    parser.add_argument("--include-schedule-outlook-candidate", action="store_true",
                        help="advisory Outlook replay inside the existing full restore, reusing built shadows")
    parser.add_argument("--season", action="append", type=int,
                        help="candidate-only season selection; default all configured seasons")
    parser.add_argument("--model-id",
                        help="candidate-only explicit schedule-outlook model ID (no metadata default)")
    args = parser.parse_args()
    if args.schedule_outlook_candidate:
        if args.include_schedule_outlook_candidate:
            parser.exit(2, "Choose standalone or integrated candidate mode, not both\n")
        if not args.league or len(args.league) != 1 or not args.model_id:
            parser.exit(2, "Candidate replay requires exactly one --league and explicit --model-id\n")
        if args.github_summary:
            parser.exit(2, "--github-summary is not supported in candidate mode\n")
        try:
            result = audit_schedule_outlook_candidate(
                args.repo_root, args.league[0], seasons=args.season, selected_model_id=args.model_id,
            )
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            parser.exit(2, f"Schedule Outlook candidate restore blocked: {exc}\n")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["VerifiedCandidatePass"] else 2
    if args.season is not None or (args.model_id is not None and not args.include_schedule_outlook_candidate):
        parser.exit(2, "--season and --model-id require a candidate mode\n")
    if args.include_schedule_outlook_candidate and not args.model_id:
        parser.exit(2, "Integrated candidate audit requires an explicit --model-id\n")
    try:
        result = audit(
            args.repo_root, leagues=args.league,
            candidate_model_id=args.model_id if args.include_schedule_outlook_candidate else None,
        )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Clean-root probe could not start: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.github_summary and summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write(render_summary(result))
    return 0 if result["ReadyForFullRestore"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
