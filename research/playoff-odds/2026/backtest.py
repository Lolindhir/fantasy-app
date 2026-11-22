#!/usr/bin/env python3
"""Walk-forward backtest playoff-odds-v1 (50/50) against playoff-odds-v2 (strength, points tiebreak) - Issue #1607.

Every after-week cutoff of every season of the league is replayed from accepted canonical facts only (no future leak: the models
see results up to the cutoff). Two questions:
  1. Playoff entry: Brier score and log loss of PlayoffProbability against the real final playoff field (completed seasons only).
  2. Single games: Brier score and log loss of the next week's win probabilities (v1 = 0.5 by construction).
Usage: python research/playoff-odds/2026/backtest.py [--league nfl-reise] [--out result.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import league_schedule_outlook_preview as src  # noqa: E402
import league_standings_sources as standings  # noqa: E402


def clip(p):
    return min(max(p, 1e-4), 1 - 1e-4)


def score(pairs):
    if not pairs:
        return None
    n = len(pairs)
    return {"N": n, "Brier": round(sum((p - y) ** 2 for p, y in pairs) / n, 4),
            "LogLoss": round(-sum(y * math.log(clip(p)) + (1 - y) * math.log(1 - clip(p)) for p, y in pairs) / n, 4)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    seasons = standings.manifest_seasons(standings.manifest(ROOT, args.league))
    VARIANTS = {"v1": ("playoff-odds-v1", "schedule-outlook-v2"), "v2": ("playoff-odds-v2", "schedule-outlook-v2"),
                "v2-fade": ("playoff-odds-v2", "schedule-outlook-v3")}
    entry = {m: [] for m in VARIANTS}
    entry_by_cut = {}
    games = {m: [] for m in VARIANTS}
    for season in seasons:
        try:
            inputs = src.load_season_inputs(ROOT, args.league, season)
            inputs.stats()
        except src.ScheduleOutlookSourceError:
            continue
        end = inputs.regular_end
        final_field = None
        if inputs.scored >= end:
            final = src.snapshot(inputs, end, "playoff-odds-v2", model_id="schedule-outlook-v2")["PlayoffOdds"]
            final_field = {t["CanonicalLeagueRosterID"]: t["PlayoffProbability"] for t in final["Teams"]}
        for week in range(0, min(inputs.scored, end - 1) + 1):
            snaps = {m: src.snapshot(inputs, week, o, model_id=k)["PlayoffOdds"] for m, (o, k) in VARIANTS.items()}
            for m, block in snaps.items():
                if final_field is not None and block["Available"]:
                    for t in block["Teams"]:
                        pair = (t["PlayoffProbability"], final_field[t["CanonicalLeagueRosterID"]])
                        entry[m].append(pair)
                        entry_by_cut.setdefault((m, week), []).append(pair)
            if week + 1 <= inputs.scored:
                actual = inputs.results(week + 1)
                for m in ("v2", "v2-fade"):
                    for t in snaps[m]["Teams"]:
                        for g in t["Upcoming"]:
                            if g["Week"] != week + 1:
                                continue
                            own, opp = actual[t["CanonicalLeagueRosterID"]][1], actual[g["OpponentCanonicalLeagueRosterID"]][1]
                            y = 1.0 if own > opp else 0.0 if own < opp else 0.5
                            games[m].append((g["WinProbability"], y))
                            if m == "v2":
                                games["v1"].append((0.5, y))
    result = {"Seasons": seasons, "PlayoffEntry": {m: score(v) for m, v in entry.items()},
              "PlayoffEntryByCutoffWeek": {str(w): {m: score(entry_by_cut.get((m, w), [])) for m in VARIANTS}
                                           for w in sorted({k[1] for k in entry_by_cut})},
              "SingleGames": {m: score(v) for m, v in games.items()}}
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
