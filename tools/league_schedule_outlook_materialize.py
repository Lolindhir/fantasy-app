#!/usr/bin/env python3
"""Bounded, deterministic materializer of the league-schedule-outlook Shared Derived product (Issue #1519, I6).

Productive since the approved activation of Issue #1519 (Robert, 2026-11-19): league-live (current season,
incremental) and update-transactions (all seasons, full) call it inside their existing rebuild-and-retry
publications. The model per season comes from data-meta ``Models.ScheduleOutlook`` (no default or fallback);
``--model-id`` is an optional assertion that must equal the selection.

Layout (per league and season; one file per fully scored after-week cutoff plus a completeness index):
  <out-root>/league-schedule-outlook/<CanonicalLeagueID>/<Season>/after-week-NN.json
  <out-root>/league-schedule-outlook/<CanonicalLeagueID>/<Season>/index.json   (written LAST)

Modes:
  incremental  recompute only cutoffs whose input fingerprint differs from the persisted document
               (or whose file is missing/unreadable). The persisted file only decides *whether* to
               recompute; content never depends on it. Bounded current-season mode for League Live.
  full         recompute every cutoff and compare bytes (weekly history pass / drift detection).

Consistency: all documents of a season are built in memory, the season inputs are re-read and their
fingerprints re-computed (a change during the run aborts the season), then files are replaced atomically
and the index is written last. Any error leaves the season untouched. Orphan snapshot files are reported
and never deleted automatically.

Usage:
  league_schedule_outlook_materialize.py --league ID [--out-root DIR] [--scope current|all] [--season YYYY ...]
      [--mode incremental|full] [--check] [--fail-on-error] [--model-id ASSERTED]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids, data_meta_root, load_league_metadata, model_for  # noqa: E402
from derived_data_lib.league_schedule_outlook import PRODUCT, SCHEMA_VERSION, assemble  # noqa: E402
from derived_data_lib.models.registry import get_model  # noqa: E402
from derived_data_lib.playoff_brackets import round_windows  # noqa: E402
import league_schedule_outlook_preview as source  # noqa: E402
from league_schedule_outlook_preview import ScheduleOutlookSourceError, SeasonInputs  # noqa: E402

FINGERPRINT_VERSION = 2
INDEX_PRODUCT = "league-schedule-outlook-index"
INDEX_NAME = "index.json"
MODES = ("incremental", "full")


class ScheduleOutlookMaterializeError(ValueError):
    """Unsafe, inconsistent or unauthorized materialization; nothing was written for the season."""


def snapshot_name(after_week: int) -> str:
    return f"after-week-{after_week:02d}.json"


def product_dir(out_root: Path, league_id: str, season: int) -> Path:
    return out_root / PRODUCT / league_id / str(season)


def serialize(document: dict[str, Any]) -> str:
    """Deterministic compact JSON; the same bytes the restore candidate digests."""
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"


def _digest(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bracket_projection(rows: Any, windows: list[tuple[int, ...]] | None, *, after_week: int, regular_end: int) -> Any:
    """Exactly the bracket facts schedule-outlook-v1 can read at this cutoff.

    Direct seeds count only from the regular-season end; Winner/Loser only once the whole round is
    scored. Everything the model masks is excluded so a later playoff result does not invalidate the
    earlier cutoffs. If the format or rows are malformed the raw payload is used (the model fails closed).
    """
    if windows is None or not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return rows
    projected = []
    for row in sorted(rows, key=lambda r: (str(r.get("Match")), str(r.get("Round")))):
        round_no = row.get("Round")
        item: dict[str, Any] = {k: row.get(k) for k in ("Match", "Round", "Placement", "Team1Source", "Team2Source")}
        if after_week >= regular_end:
            for slot in (1, 2):
                if row.get(f"Team{slot}Source") is None:
                    item[f"Team{slot}CanonicalLeagueRosterID"] = row.get(f"Team{slot}CanonicalLeagueRosterID")
        if type(round_no) is int and 1 <= round_no <= len(windows) and after_week >= windows[round_no - 1][-1]:
            item["WinnerCanonicalLeagueRosterID"] = row.get("WinnerCanonicalLeagueRosterID")
            item["LoserCanonicalLeagueRosterID"] = row.get("LoserCanonicalLeagueRosterID")
        projected.append(item)
    return projected


def input_fingerprint(inputs: SeasonInputs, after_week: int, model_id: str, odds_model_id: str) -> str:
    """SHA-256 over exactly the accepted facts and versions this cutoff depends on.

    Included: schema/fingerprint/model versions, identities, week structure, team identity, the future
    regular-season pairings, the ratings of the cutoff's rating week only, and the cutoff-visible
    bracket facts, the played win/loss/tie records (points only once the regular season is complete,
    for the official tiebreak) and the playoff-odds model. Excluded (by design): scores, lineups, later ratings, masked bracket results.
    """
    rating_week = source.rating_week_for(inputs, after_week)
    stats = inputs.stats() if rating_week else {}
    ratings = source.ratings_for_week(stats, inputs.teams, rating_week=rating_week)
    winners, losers = inputs.brackets()
    windows = round_windows(inputs.week_structure)
    kwargs = {"after_week": after_week, "regular_end": inputs.regular_end}
    return _digest({
        "FingerprintVersion": FINGERPRINT_VERSION,
        "SchemaVersion": SCHEMA_VERSION,
        "ModelID": model_id,
        "PlayoffOddsModelID": odds_model_id,
        "Records": [(r["CanonicalLeagueRosterID"], r["Wins"], r["Losses"], r["Ties"],
                     r["Points"] if after_week >= inputs.regular_end else None,
                     r["PointsAgainst"] if after_week >= inputs.regular_end else None)
                    for r in sorted(inputs.records(after_week), key=lambda r: r["CanonicalLeagueRosterID"])],
        "League": [inputs.league_id, inputs.season_id, inputs.season],
        "AfterWeek": after_week,
        "RatingWeek": rating_week or None,
        "WeekStructure": inputs.week_structure,
        "Teams": sorted((t["TeamID"], t["CanonicalLeagueRosterID"]) for t in inputs.teams),
        "Pairings": {str(w): inputs.pairings(w) for w in range(max(1, after_week + 1), inputs.regular_end + 1)},
        "SeasonStatsModel": stats.get("Models", {}).get("SeasonStats") if stats else None,
        "Ratings": {k: ratings[k] for k in sorted(ratings)},
        "Winners": _bracket_projection(winners, windows, **kwargs),
        "Losers": _bracket_projection(losers, windows, **kwargs),
    })


def build_document(inputs: SeasonInputs, after_week: int, model_id: str, fingerprint: str, odds_model_id: str) -> dict[str, Any]:
    return assemble(source.snapshot(inputs, after_week, odds_model_id), selected_model_id=model_id, input_fingerprint=fingerprint)


def _read_existing(path: Path) -> tuple[str, dict[str, Any] | None]:
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError):
        return "", None
    return text, data if isinstance(data, dict) else None


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def selected_model_id(repo_root: Path, league_id: str, season: int, asserted: str | None = None) -> str:
    """The data-meta model choice of one season; missing or unknown selections fail closed."""
    try:
        metadata = load_league_metadata(league_id, data_meta_root(repo_root))
        model_id = model_for(metadata, season, "ScheduleOutlook")
    except LeagueMetadataError as exc:
        raise ScheduleOutlookMaterializeError(f"No usable ScheduleOutlook model selection for {season}: {exc}") from exc
    if asserted is not None and asserted != model_id:
        raise ScheduleOutlookMaterializeError(
            f"Season {season}: data-meta selects {model_id}, not the asserted {asserted}")
    return model_id


def selected_odds_model_id(repo_root: Path, league_id: str, season: int) -> str:
    """The data-meta PlayoffOdds choice of one season; missing or unknown selections fail closed."""
    try:
        return model_for(load_league_metadata(league_id, data_meta_root(repo_root)), season, "PlayoffOdds")
    except LeagueMetadataError as exc:
        raise ScheduleOutlookMaterializeError(f"No usable PlayoffOdds model selection for {season}: {exc}") from exc


def materialize_season(
    repo_root: Path, out_root: Path, league_id: str, season: int, model_id: str,
    *, odds_model_id: str | None = None, mode: str = "incremental", check_only: bool = False,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ScheduleOutlookMaterializeError(f"Unknown mode {mode!r}")
    get_model(model_id, kind="schedule-outlook")
    if odds_model_id is None:
        odds_model_id = selected_odds_model_id(repo_root, league_id, season)
    get_model(odds_model_id, kind="playoff-odds")
    folder = product_dir(out_root, league_id, season)

    inputs = source.load_season_inputs(repo_root, league_id, season)
    scored = inputs.scored
    if type(scored) is not int or scored < 0:
        raise ScheduleOutlookMaterializeError("Unknown LeagueScoredWeek")
    weeks = list(range(scored + 1))
    fingerprints = {w: input_fingerprint(inputs, w, model_id, odds_model_id) for w in weeks}

    texts: dict[int, str] = {}
    unchanged = recomputed = 0
    writes: list[int] = []
    for week in weeks:
        existing_text, existing = _read_existing(folder / snapshot_name(week))
        current = (existing is not None and mode == "incremental"
                   and existing.get("Provenance", {}).get("InputFingerprint") == fingerprints[week]
                   and existing.get("AsOf", {}).get("AfterWeek") == week
                   and existing.get("Models", {}).get("ScheduleOutlook") == model_id
                   and existing.get("Models", {}).get("PlayoffOdds") == odds_model_id
                   and existing.get("SchemaVersion") == SCHEMA_VERSION)
        if current:
            texts[week] = existing_text
            unchanged += 1
            continue
        text = serialize(build_document(inputs, week, model_id, fingerprints[week], odds_model_id))
        recomputed += 1
        texts[week] = text
        if text != existing_text:
            writes.append(week)

    # Source-change guard: re-read everything; any fingerprint movement aborts the season untouched.
    fresh = source.load_season_inputs(repo_root, league_id, season)
    if fresh.scored != scored or any(input_fingerprint(fresh, w, model_id, odds_model_id) != fingerprints[w] for w in weeks):
        raise ScheduleOutlookMaterializeError(f"Season {season}: inputs changed during the run; nothing written")

    index = {
        "SchemaVersion": SCHEMA_VERSION, "Product": INDEX_PRODUCT, "CanonicalLeagueID": league_id,
        "CanonicalLeagueSeasonID": inputs.season_id, "Season": season,
        "Models": {"ScheduleOutlook": model_id, "PlayoffOdds": odds_model_id}, "LeagueScoredWeek": scored,
        "Snapshots": [{"AfterWeek": w, "File": snapshot_name(w), "InputFingerprint": fingerprints[w],
                       "Sha256": hashlib.sha256(texts[w].encode("utf-8")).hexdigest()} for w in weeks],
    }
    index_text = serialize(index)
    index_changed = _read_existing(folder / INDEX_NAME)[0] != index_text
    expected = {snapshot_name(w) for w in weeks} | {INDEX_NAME}
    orphans = sorted(p.name for p in folder.glob("after-week-*.json") if p.name not in expected) if folder.is_dir() else []

    if not check_only:
        for week in writes:
            _atomic_write(folder / snapshot_name(week), texts[week])
        if index_changed or writes:
            _atomic_write(folder / INDEX_NAME, index_text)  # last: a present index implies a complete set
    return {
        "Season": season, "CanonicalLeagueID": league_id, "Mode": mode, "LeagueScoredWeek": scored,
        "Snapshots": len(weeks), "Unchanged": unchanged, "Recomputed": recomputed,
        "Written" if not check_only else "WouldWrite": len(writes) + (1 if index_changed else 0),
        "Orphans": orphans,
    }


def seasons_for_scope(repo_root: Path, league_id: str, scope: str, explicit: list[int] | None) -> list[int]:
    import league_standings_sources as standings
    manifest = standings.manifest(repo_root, league_id)
    available = standings.manifest_seasons(manifest)
    if explicit:
        unknown = [s for s in explicit if s not in available]
        if unknown:
            raise ScheduleOutlookMaterializeError(f"Seasons not in the league manifest: {unknown}; available: {available}")
        return sorted(set(explicit))
    return [standings.current_season(manifest)] if scope == "current" else available


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default=None, help="default: every configured league (data-meta)")
    parser.add_argument("--model-id", help="optional assertion; the model always comes from data-meta Models.ScheduleOutlook")
    parser.add_argument("--out-root", type=Path, default=None, help="default: the repository data-derived root")
    parser.add_argument("--scope", choices=("current", "all"), default="current")
    parser.add_argument("--season", type=int, action="append")
    parser.add_argument("--mode", choices=MODES, default="incremental")
    parser.add_argument("--check", action="store_true", help="dry run; exit 1 when a write or orphan would remain")
    parser.add_argument("--fail-on-error", action="store_true",
                        help="exit 1 when a season cannot be materialized (default: warn and keep the last good set)")
    args = parser.parse_args()
    out_root = args.out_root if args.out_root is not None else data_derived_dir(args.repo_root)
    failures = 0
    pending = 0
    try:
        league_ids = [args.league] if args.league else list(list_league_ids())
    except (LeagueMetadataError, OSError) as exc:
        print(f"schedule outlook materialization failed: {exc}", file=sys.stderr)
        return 1
    for league_id in league_ids:
        try:
            seasons = seasons_for_scope(args.repo_root, league_id, args.scope, args.season)
        except (ScheduleOutlookMaterializeError, ScheduleOutlookSourceError, ValueError, OSError, KeyError) as exc:
            print(f"schedule outlook materialization failed: {exc}", file=sys.stderr)
            return 1
        for season in seasons:
            try:
                summary = materialize_season(args.repo_root, out_root, league_id, season,
                                             selected_model_id(args.repo_root, league_id, season, args.model_id),
                                             mode=args.mode, check_only=args.check)
            except (ScheduleOutlookMaterializeError, ScheduleOutlookSourceError, ValueError, OSError, KeyError) as exc:
                failures += 1
                print(f"::warning::schedule outlook {league_id} season {season} not materialized: {exc}", file=sys.stderr)
                continue
            pending += summary.get("WouldWrite", 0) + len(summary["Orphans"])
            print(json.dumps(summary, sort_keys=True))
    return 1 if (failures and (args.fail_on_error or args.check)) or (args.check and pending) else 0


if __name__ == "__main__":
    raise SystemExit(main())
