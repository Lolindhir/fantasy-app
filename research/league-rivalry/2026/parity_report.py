#!/usr/bin/env python3
"""Parity of the league-rivalry product against the golden dump of the former Angular util (Issue #1455).

Usage: parity_report.py <golden.json> <product.json>
Compares every (TeamID, OpponentID, Filter) record exactly (no tolerance) and lists every differing game individually.
Allowed differences: E1 (winners-bracket placement games count) and the last-playoff-week consolation games the old heuristic counted.
"""
import json
import sys

golden = {(r["TeamID"], r["OpponentID"], r["Filter"]): r for r in json.load(open(sys.argv[1]))}
product = {(r["TeamID"], r["OpponentID"], r["Filter"]): r for r in json.load(open(sys.argv[2]))["Records"]}


def key(g, camel):
    if camel:
        return (g["season"], g["week"], g["stage"], g["outcome"], g["teamPoints"], g["opponentPoints"], g["margin"])
    return (g["Season"], g["Week"], g["Stage"], g["Outcome"], g["TeamPoints"], g["OpponentPoints"], g["Margin"])


exact = 0
missing_in_product, extra_in_product, game_diffs = [], [], []
for ident in sorted(set(golden) | set(product)):
    g, p = golden.get(ident), product.get(ident)
    gg = [key(x, True) for x in g["Games"]] if g else []
    pg = [key(x, False) for x in p["Games"]] if p else []
    if gg == pg and (not g or (g["Wins"], g["Losses"], g["Ties"], g["PointsFor"], g["PointsAgainst"]) == (p["Wins"], p["Losses"], p["Ties"], p["PointsFor"], p["PointsAgainst"])):
        exact += 1
        continue
    for game in gg:
        if game not in pg:
            game_diffs.append(("only-old", ident, game))
    for game in pg:
        if game not in gg:
            game_diffs.append(("only-new", ident, game))
print(f"records compared: {len(set(golden) | set(product))}, exact equal: {exact}")
seen = set()
for kind, ident, game in game_diffs:
    # each game appears for both directions and several filters; report it once per season/week/pair
    pair = tuple(sorted(ident[:2]))
    marker = (kind, pair, game[:3])
    if marker in seen:
        continue
    seen.add(marker)
    print(kind, "pair", pair, "season", game[0], "week", game[1], "stage", game[2])
print("differing games:", len(seen))
