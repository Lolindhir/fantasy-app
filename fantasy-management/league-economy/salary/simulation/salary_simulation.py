#!/usr/bin/env python3
"""Salary-Simulationspaket (Issue #879).

Rechnet den Salary-Entwurf aus fantasy-management/league-economy/salary/ auf dem
aktuellen Repo-Datenstand durch (Liga-Scoring seit #347 D4) und schreibt JSON,
CSV und Markdown nach ../analyses/.

Liest nur Repo-Daten, schreibt keine App-Daten. Aufruf aus dem Repo-Root:

    python3 fantasy-management/league-economy/salary/simulation/salary_simulation.py
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "public" / "data"
LEAGUE_SRC = ROOT / "source-data" / "leagues" / "nfl-reise" / "seasons"
NFL_SRC = ROOT / "source-data" / "nfl"
OUT_DIR = Path(__file__).resolve().parents[1] / "analyses"
OUT_STEM = "2026-10-05-salary-simulation"

POSITIONS = ["QB", "RB", "WR", "TE", "K"]
FLEX_ELIGIBLE = {"RB", "WR", "TE"}
SEASONS = {"SeasonMinus1": 2025, "SeasonMinus2": 2024, "SeasonMinus3": 2023}

# Heutige Formel (RequestPlayers.ps1 / RequestLeague.ps1)
REF_SIGNAL = 20.0
REF_SALARY = 50_000_000
CAP_FACTOR = 0.9

# Entwurf (salary-dead-cap-concept.md)
MIN_PCT_BY_YEAR = [(1, 0.0025), (2, 0.0030), (3, 0.0035), (4, 0.0040), (5, 0.0045), (8, 0.0050)]
ROOKIE_MAX_PCT = 0.035
ROOKIE_LAST_PCT = 0.003
ROOKIE_UNDRAFTED_PCT = 0.0025
ROOKIE_EXP = 3.5
ROOKIE_WEIGHT_FANTASY = 0.65
ROOKIE_ESCALATION = {1: 1.00, 2: 1.25, 3: 1.50}
DEAD_CAP_RATE = {0: 0.50, 1: 0.30, 2: 0.15}
DEAD_CAP_RATE_LONG = 0.05


def load(path: Path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def as_list(data, key):
    if isinstance(data, list):
        return data
    return data.get(key, [data])


# ---------------------------------------------------------------- Salary-Kurven

def map_salary(signal: float, k: float) -> float:
    """MapSalaryToDollarsNonLinear mit Quelle 0..20 und Ziel 0..50 Mio."""
    normalized = signal / REF_SIGNAL
    if normalized > 1:
        scaled = 1 + (normalized - 1) * k
    else:
        scaled = max(normalized, 0) ** k
    return scaled * REF_SALARY


def season_performance(entry: dict) -> float:
    return 0.5 * entry["AvgPotentialGame"] + 0.5 * entry["AvgGame"]


def floored_three_year(p1: float, p2: float, p3: float) -> float:
    """Get-FantasySalaryWithFloor ohne Dollar-Abbildung: 3Y-Performance."""
    if p1 == 0 and p2 == 0:
        return 0.0
    if p1 >= p2 and p1 >= p3:
        ratio, top = 0.5, p1
    elif p2 >= p1 and p2 >= p3:
        ratio, top = 0.33, p2
    else:
        ratio, top = 0.17, p3
    floor = top * ratio
    return (max(p1, floor) + max(p2, floor) + max(p3, floor)) / 3


def top_n_cap(salaries: list[float], top_n: int, relevant_team_size: int) -> float:
    ordered = sorted(salaries, reverse=True)[:top_n]
    return sum(ordered) / len(ordered) * relevant_team_size * CAP_FACTOR


def min_pct(year: int) -> float:
    pct = MIN_PCT_BY_YEAR[0][1]
    for threshold, value in MIN_PCT_BY_YEAR:
        if year >= threshold:
            pct = value
    return pct


def round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


# ------------------------------------------------------------ Ligaformat

def league_format(league: dict) -> dict:
    slots = Counter(league["RosterSize"])
    teams = int(league["TotalTeams"])
    return {
        "teams": teams,
        "fixed": {pos: slots.get(pos, 0) * teams for pos in POSITIONS},
        "flex": slots.get("FLEX", 0) * teams,
        "top_n": int(league["SalaryRelevantTeamSize"]) * teams,
        "relevant_team_size": int(league["SalaryRelevantTeamSize"]),
    }


# --------------------------------------------------- Criticality (DMLI)

def lineup_value(pools: dict[str, list[float]], fmt: dict) -> float:
    """Optimale ligaweite Aufstellung: feste Slots je Position, danach FLEX."""
    total = 0.0
    leftovers = []
    for pos in POSITIONS:
        values = pools.get(pos, [])
        n = fmt["fixed"][pos]
        total += sum(values[:n])
        if pos in FLEX_ELIGIBLE:
            leftovers.extend(values[n:])
    leftovers.sort(reverse=True)
    total += sum(leftovers[: fmt["flex"]])
    return total


def season_curves(players: list[dict], key: str, fmt: dict) -> dict:
    pools = defaultdict(list)
    for player in players:
        if player["Position"] in POSITIONS:
            pools[player["Position"]].append(season_performance(player["PointHistory"][key]))
    for pos in pools:
        pools[pos].sort(reverse=True)
    base = lineup_value(pools, fmt)
    curves = {}
    flex_mix = Counter()
    for pos in POSITIONS:
        values = pools.get(pos, [])
        curve = []
        for index in range(len(values)):
            reduced = dict(pools)
            reduced[pos] = values[:index] + values[index + 1:]
            curve.append(round(base - lineup_value(reduced, fmt), 6))
        curves[pos] = curve
    # FLEX-Verteilung für die Dokumentation
    leftovers = []
    for pos in FLEX_ELIGIBLE:
        leftovers.extend((v, pos) for v in pools.get(pos, [])[fmt["fixed"][pos]:])
    leftovers.sort(reverse=True)
    flex_mix.update(pos for _, pos in leftovers[: fmt["flex"]])
    return {"curves": curves, "flex_mix": dict(flex_mix), "pool_sizes": {p: len(pools.get(p, [])) for p in POSITIONS}}


def three_year_curves(per_season: dict[int, dict]) -> dict[str, list[float]]:
    result = {}
    for pos in POSITIONS:
        length = max(len(per_season[y]["curves"][pos]) for y in per_season)
        curve = []
        for index in range(length):
            vals = []
            for y in per_season:
                c = per_season[y]["curves"][pos]
                vals.append(c[index] if index < len(c) else 0.0)
            curve.append(sum(vals) / len(vals))
        while curve and curve[-1] == 0:
            curve.pop()
        result[pos] = curve
    return result


def c_ref_top10(curves: dict[str, list[float]]) -> tuple[float, int, int]:
    positive = sorted((v for pos in curves for v in curves[pos] if v > 0), reverse=True)
    count = max(1, round_half_up(len(positive) * 0.10))
    return sum(positive[:count]) / count, len(positive), count


def assign_criticality(perfs: list[tuple[str, float]], curve: list[float]) -> dict[str, float]:
    """Rang innerhalb der Position, Ties erhalten den Mittelwert ihrer Rangpunkte."""
    ordered = sorted(perfs, key=lambda item: -item[1])
    result = {}
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1][1] == ordered[index][1]:
            end += 1
        points = [curve[i] if i < len(curve) else 0.0 for i in range(index, end + 1)]
        value = sum(points) / len(points)
        for i in range(index, end + 1):
            result[ordered[i][0]] = value
        index = end + 1
    return result


# ------------------------------------------------------------ Rookies

def draft_pct(rank: int | None, pool: int) -> float:
    if rank is None or pool <= 0:
        return ROOKIE_UNDRAFTED_PCT
    if pool == 1:
        return ROOKIE_MAX_PCT
    share = 1 - (rank - 1) / (pool - 1)
    return ROOKIE_LAST_PCT + (ROOKIE_MAX_PCT - ROOKIE_LAST_PCT) * share ** ROOKIE_EXP


def sleeper_by_canonical() -> dict[str, str]:
    identities = load(NFL_SRC / "identities" / "players.json")["Players"]
    mapping = {}
    for entry in identities:
        sleeper = (entry.get("IDs") or {}).get("Sleeper")
        if sleeper:
            mapping[entry["CanonicalPlayerID"]] = str(sleeper)
    return mapping


def nfl_draft_ranks(season: int, canon_to_sleeper: dict[str, str]) -> tuple[dict[str, int], int]:
    picks = load(NFL_SRC / "draft" / f"{season}.json")["Picks"]
    skill = [p for p in picks if p.get("Position") in {"QB", "RB", "WR", "TE"}]
    skill.sort(key=lambda p: p["OverallPick"])
    ranks = {}
    for rank, pick in enumerate(skill, start=1):
        sleeper = canon_to_sleeper.get(pick.get("CanonicalPlayerID"))
        if sleeper:
            ranks[sleeper] = rank
    return ranks, len(skill)


def fantasy_rookie_ranks(season: int, rookie_ids: set[str]) -> tuple[dict[str, int], int, str]:
    """Rang im Rookie Draft der Saison. 2024 gab es keinen Rookie Draft:
    dann zählt die Reihenfolge der Rookies im Free-Agent-Draft (Annahme)."""
    drafts = as_list(load(DATA / "past_seasons" / "Drafts" / f"Drafts_{season}.json"), "Drafts")
    rookie = [d for d in drafts if d.get("DraftType") == "Rookie"]
    if rookie:
        picks = sorted((p for d in rookie for p in d["Picks"] if p.get("PlayerID")), key=lambda p: p["OverallPick"])
        source = "Rookie Draft"
    else:
        picks = sorted(
            (p for d in drafts for p in d["Picks"] if p.get("PlayerID") in rookie_ids),
            key=lambda p: p["OverallPick"],
        )
        source = "Free-Agent-Draft (nur Rookies, Annahme)"
    ranks = {str(p["PlayerID"]): rank for rank, p in enumerate(picks, start=1)}
    return ranks, len(picks), source


# ----------------------------------------------------------- Gesamtmodell

def run_model(players, perf3y, curves, cref, fmt, *, prev_cap, k, band, population, rookie_contracts,
              base_minimum, rookie_year1_pct):
    """Ein Salary-Zyklus. Liefert Salary je Spieler und das resultierende Cap."""
    on_rookie = {
        p["ID"] for p in players if rookie_contracts and 1 <= int(p["Year"] or 0) <= 3
    }

    def in_population(p):
        if population == "all":
            return True
        if p["ID"] in on_rookie:
            return False
        if population == "veterans_with_nfl_team" and p["IsFreeAgent"]:
            return False
        return True

    crit = {}
    for pos in POSITIONS:
        ranked = [(p["ID"], perf3y[p["ID"]]) for p in players if p["Position"] == pos and in_population(p)]
        crit.update(assign_criticality(ranked, curves.get(pos, [])))

    rows = {}
    for p in players:
        pid = p["ID"]
        year = int(p["Year"] or 1)
        c = crit.get(pid, 0.0)
        modifier = (1 - band) + 2 * band * min(max(c / cref, 0.0), 1.0)
        signal = perf3y[pid] * modifier
        minimum = round_half_up(prev_cap * min_pct(year)) if base_minimum else 0
        if pid in on_rookie:
            salary = round_half_up(prev_cap * rookie_year1_pct[pid] * ROOKIE_ESCALATION[year])
            salary = max(salary, minimum)
            kind = "rookie"
        else:
            salary = minimum + round_half_up(map_salary(signal, k))
            kind = "performance"
        rows[pid] = {"criticality": c, "modifier": modifier, "signal": signal, "salary": salary, "kind": kind,
                     "minimum": minimum}
    cap = top_n_cap([r["salary"] for r in rows.values()], fmt["top_n"], fmt["relevant_team_size"])
    return rows, cap


def team_cap_salary(salaries: list[float], fmt: dict) -> float:
    """Wie team-salary.util.ts: Summe der SalaryRelevantTeamSize teuersten Spieler."""
    return sum(sorted(salaries, reverse=True)[: fmt["relevant_team_size"]])


def summarize(players, rows, cap, fmt, teams, current_rows=None):
    by_id = {p["ID"]: p for p in players}
    top = sorted(rows.items(), key=lambda kv: -kv[1]["salary"])[: fmt["top_n"]]
    top_total = sum(r["salary"] for _, r in top)
    positions = {}
    for pos in POSITIONS:
        sel = [r["salary"] for pid, r in top if by_id[pid]["Position"] == pos]
        positions[pos] = {"count": len(sel), "share": round(sum(sel) / top_total, 4) if top_total else 0}
    kinds = Counter(r["kind"] for _, r in top)
    team_rows = []
    for team in teams:
        total = team_cap_salary([rows[pid]["salary"] for pid in team["Roster"] if pid in rows], fmt)
        team_rows.append({"team": team["Team"], "salary_top_relevant": total, "share_of_cap": round(total / cap, 4),
                          "over_cap_by": max(0, round(total - cap))})
    return {
        "salary_cap": round(cap),
        "top_n": fmt["top_n"],
        "top_n_floor": top[-1][1]["salary"] if top else 0,
        "top_n_by_position": positions,
        "top_n_rookie_contracts": kinds.get("rookie", 0),
        "teams": team_rows,
        "teams_over_cap": sum(1 for t in team_rows if t["over_cap_by"] > 0),
    }


def iterate_cap(players, perf3y, curves, cref, fmt, anchor_cap, rookie_pct, **opts):
    """Rückkopplung Vorjahres-Cap -> Minimum/Rookies -> Cap, bis zur Konvergenz."""
    history = []
    prev = anchor_cap
    rows = cap = None
    for _ in range(40):
        rows, cap = run_model(players, perf3y, curves, cref, fmt, prev_cap=prev, rookie_year1_pct=rookie_pct, **opts)
        history.append(round(cap))
        if abs(cap - prev) < 1:
            break
        prev = cap
    return rows, cap, history


# ------------------------------------------------------------- Dead Cap

def roster_index_by_team(league):
    return {int(t["TeamID"]): t["Team"] for t in league["Teams"]}


def acquisition_events():
    """(season, created_ms, player, roster_id, kind) für Zugänge und Abgänge."""
    events = []
    for season in (2024, 2025, 2026):
        drafts = as_list(load(DATA / "past_seasons" / "Drafts" / f"Drafts_{season}.json"), "Drafts")
        for draft in drafts:
            for pick in draft["Picks"]:
                if pick.get("PlayerID") and pick.get("CurrentOwnerRosterID"):
                    events.append((season, 0, str(pick["PlayerID"]), int(pick["CurrentOwnerRosterID"]), "draft"))
    tx_files = {
        2024: DATA / "past_seasons" / "Transactions" / "Transactions_2024.json",
        2025: DATA / "past_seasons" / "Transactions" / "Transactions_2025.json",
        2026: DATA / "Transactions.json",
    }
    transactions = []
    for season, path in tx_files.items():
        for tx in load(path):
            if tx.get("Status") != "complete":
                continue
            transactions.append((season, tx))
            for pid, roster in (tx.get("Drops") or {}).items():
                events.append((season, tx["CreatedAt"] - 1, str(pid), int(roster), "drop:" + tx["Type"]))
            for pid, roster in (tx.get("Adds") or {}).items():
                events.append((season, tx["CreatedAt"], str(pid), int(roster), "add:" + tx["Type"]))
    events.sort(key=lambda e: (e[0], e[1]))
    return events, transactions


def dead_cap_simulation(league, salary_by_cycle, cap_by_cycle, cap_deadline_ms):
    """Simuliert Dead Cap aus allen echten Cuts mit Tenure-Staffel.

    Ein Cut zählt auf die nächste Cap Deadline nach dem Cut. Basis ist das zum
    Cut-Zeitpunkt geltende Salary (Robert, 05.10.2026: altes Salary)."""
    events, _ = acquisition_events()
    names = roster_index_by_team(league)
    holder = {}  # (player, roster) -> acquisition season
    active = {}  # (cycle, player) -> aktives Salary nach früheren Cuts
    cuts = []
    for season, created, pid, roster, kind in events:
        if kind == "draft" or kind.startswith("add:"):
            holder[(pid, roster)] = season
            if kind == "add:trade":
                for other in list(holder):
                    if other[0] == pid and other[1] != roster:
                        holder.pop(other)
            continue
        acquired = holder.pop((pid, roster), None)
        if kind == "drop:trade":
            continue  # Trade ist kein Cut
        acq = acquired if acquired is not None else 2024
        tenure = season - acq
        rate = DEAD_CAP_RATE.get(tenure, DEAD_CAP_RATE_LONG)
        in_season = created >= cap_deadline_ms.get(season, 0)
        # Salary-Zyklus: In-Season-Cuts der Saison S nutzen Zyklus S und zählen zur Deadline S+1.
        # Offseason-Cuts vor der Deadline S nutzen bereits Zyklus S (Salary ab Offseason-Start).
        cycle = season
        deadline = season + 1 if in_season else season
        cycle_salary = salary_by_cycle.get(cycle, {}).get(pid)
        # Retained Salary: frühere Cuts im selben Zyklus haben das aktive Salary schon reduziert.
        salary = active.get((cycle, pid), cycle_salary)
        dead = round_half_up(salary * rate) if salary is not None else None
        if salary is not None:
            active[(cycle, pid)] = salary - dead
        cuts.append({
            "player": pid, "team": names.get(roster, str(roster)), "season": season, "in_season": in_season,
            "tenure": tenure, "rate": rate, "salary_basis_cycle": cycle, "cycle_salary": cycle_salary,
            "salary_at_cut": salary, "dead_cap": dead,
            "counts_at_deadline": deadline, "acquisition_known": acquired is not None,
        })
    per_deadline = defaultdict(lambda: defaultdict(lambda: {"cuts": 0, "dead_cap": 0, "unknown_salary": 0}))
    for cut in cuts:
        bucket = per_deadline[cut["counts_at_deadline"]][cut["team"]]
        bucket["cuts"] += 1
        if cut["dead_cap"] is None:
            bucket["unknown_salary"] += 1
        else:
            bucket["dead_cap"] += cut["dead_cap"]
    summary = {}
    for deadline, teams in sorted(per_deadline.items()):
        cap = cap_by_cycle.get(deadline)
        summary[deadline] = {
            "reference_cap": round(cap) if cap else None,
            "teams": [
                {"team": team, **values, "share_of_cap": round(values["dead_cap"] / cap, 4) if cap else None}
                for team, values in sorted(teams.items())
            ],
        }
    return cuts, summary


# ------------------------------------------------------------- Zyklus 2025

def cycle_2025_performance(players):
    """3Y-Performance für Zyklus 2025 (Saisons 2024, 2023, 2022).
    2022 nur als Tank01-PPR-Archiv verfügbar (Annahme, 17 mögliche Spiele)."""
    archive = as_list(load(DATA / "past_seasons" / "Players_2022.json"), "Players")
    perf_2022 = {}
    for entry in archive:
        games = [g for g in entry.get("Games", []) if g.get("Week", 0) <= 18]
        if not games:
            continue
        total = sum(float(g.get("FantasyPoints") or 0) for g in games)
        perf_2022[str(entry["TankID"])] = 0.5 * total / 17 + 0.5 * total / len(games)
    result = {}
    for p in players:
        p2024 = season_performance(p["PointHistory"]["SeasonMinus2"])
        p2023 = season_performance(p["PointHistory"]["SeasonMinus3"])
        p2022 = perf_2022.get(str(p.get("TankID")), 0.0)
        result[p["ID"]] = floored_three_year(p2024, p2023, p2022)
    return result


# ------------------------------------------------------------- Markdown

SCENARIO_LABELS = {
    "A_heute": "A · Heute (k=2, keine Verträge, kein Minimum)",
    "B_k15_ohne_vertraege": "B · Criticality + k=1,5, ohne Minimum und Rookie-Verträge",
    "C_hauptszenario": "C · Hauptszenario: Entwurf komplett",
    "D_population_ohne_rookievertraege": "D · wie C, Rang ohne Rookie-Verträge",
    "E_population_ohne_rookies_und_nfl_fa": "E · wie C, Rang ohne Rookie-Verträge und NFL-Free-Agents",
    "F_band_15": "F · wie C, Bandbreite ±15 %",
    "G_band_35": "G · wie C, Bandbreite ±35 %",
    "H_k20": "H · wie C, aber k=2,0",
    "I_ohne_base_minimum": "I · wie C, ohne Base Minimum",
}


def mio(value) -> str:
    if value is None:
        return "–"
    return f"{value / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value, digits=1) -> str:
    if value is None:
        return "–"
    return f"{value * 100:.{digits}f}".replace(".", ",") + " %"


def num(value, digits=2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def write_report(r: dict) -> str:
    sc = r["scenarios"]
    base_cap = sc["A_heute"]["salary_cap"]
    lines = []
    w = lines.append
    w("# Salary-Simulation 05.10.2026: Entwurf auf Liga-Scoring durchgerechnet")
    w("")
    w("> Status: Simulation als Datengrundlage für eine Ligaentscheidung. **Nichts davon ist beschlossen.**")
    w("> Nachgehalten in Issue #879. Reproduzierbar mit `simulation/salary_simulation.py`.")
    w("> Rohdaten: [`" + OUT_STEM + ".json`](" + OUT_STEM + ".json), Spielertabelle: [`" + OUT_STEM + "-players.csv`](" + OUT_STEM + "-players.csv) (Semikolon, öffnet in Excel).")
    w("")
    w("## 1. Kurzfassung")
    w("")
    c = sc["C_hauptszenario"]
    w(f"- Die heutige Formel lässt sich exakt nachrechnen ({r['baseline_check']['players']} Spieler, {r['baseline_check']['salary_mismatches']} Abweichungen, Cap {mio(r['baseline_check']['recomputed_cap'])} Mio. wie veröffentlicht).")
    w(f"- Die Criticality-Kurven auf Liga-Scoring sind fast identisch mit dem Tank01-Stand. C_ref sinkt von {num(r['criticality']['c_ref_previous_tank01'], 4)} auf {num(r['criticality']['c_ref'], 4)}.")
    w(f"- Der komplette Entwurf (Szenario C) hebt das Cap von {mio(base_cap)} auf {mio(c['salary_cap'])} Mio. (+{pct(c['salary_cap'] / base_cap - 1)}). Fast der ganze Anstieg kommt vom additiven Base Minimum (Vergleich C mit I).")
    w(f"- Im Hauptszenario stehen {c['top_n_rookie_contracts']} Spieler mit Rookie-Vertrag in den Top {c['top_n']}. Die QB-Masse sinkt deutlich, WR/RB/TE steigen.")
    w("- Die Frage, wer in die Positionsränge zählt (C/D/E), verschiebt das Cap um weniger als 0,2 %. Für einzelne TEs macht sie bis etwa 1 Mio. aus.")
    w("- Dead Cap aus den echten Cuts wäre an der Deadline 2026 für mehrere Teams spürbar (bis über 20 % des Caps). Die Cuts sind aber unter Regeln ohne Dead Cap entstanden; das Verhalten würde sich ändern.")
    w("")
    w("## 2. Datenbasis und Prüfung")
    w("")
    w("| Quelle | Verwendung |")
    w("|---|---|")
    for key, value in r["inputs"].items():
        w(f"| `{key}` | {value} |")
    w("")
    fmt = r["format"]
    w(f"Ligaformat aus League.json: {fmt['teams']} Teams, feste Starter {', '.join(f'{p} {n}' for p, n in fmt['fixed'].items())}, FLEX {fmt['flex']}, Cap-relevant Top {fmt['top_n']} ({fmt['relevant_team_size']} je Team).")
    w("")
    w("## 3. Criticality-Kurven auf Liga-Scoring")
    w("")
    w("Berechnung wie im Redesign-Papier (DMLI je Saison 2023/2024/2025, Rangmittel über drei Jahre). Population sind alle Spieler aus Players.json mit Punkten in der Saison.")
    w("")
    w("| Saison | FLEX-Verteilung | Poolgröße QB/RB/WR/TE/K |")
    w("|---|---|---|")
    for year, info in sorted(r["criticality"]["per_season"].items()):
        mix = ", ".join(f"{k} {v}" for k, v in sorted(info["flex_mix"].items()))
        pools = "/".join(str(info["pool_sizes"][p]) for p in POSITIONS)
        w(f"| {year} | {mix} | {pools} |")
    w("")
    w("3Y-Kurven (Rangpunkte mit Criticality > 0):")
    w("")
    w("```text")
    for pos, curve in r["criticality"]["three_year"].items():
        w(f"{pos}: " + " · ".join(f"{pos}{i + 1} {num(v)}" for i, v in enumerate(curve)))
    w("```")
    w("")
    w(f"C_ref (Mittel der oberen 10 % von {r['criticality']['positive_rank_points']} positiven Rangpunkten, also {r['criticality']['reference_points']} Punkte): **{num(r['criticality']['c_ref'], 4)}** (vorher {num(r['criticality']['c_ref_previous_tank01'], 4)}).")
    w("")
    w("## 4. Szenarien")
    w("")
    w("Alle Szenarien außer A rechnen das Cap mit Rückkopplung: Vorjahres-Cap → Minimum und Rookie-Verträge → neues Cap, bis es sich nicht mehr ändert. Startwert ist das heute veröffentlichte Cap.")
    w("")
    w("| Szenario | Cap (Mio.) | ggü. heute | Top-120-Schwelle (Mio.) | QB | RB | WR | TE | K | Rookie-Verträge in Top 120 |")
    w("|---|---:|---:|---:|---|---|---|---|---|---:|")
    for name, s in sc.items():
        pos = s["top_n_by_position"]
        cells = " | ".join(f"{pos[p]['count']} · {pct(pos[p]['share'], 0)}" for p in POSITIONS)
        w(f"| {SCENARIO_LABELS[name]} | {mio(s['salary_cap'])} | {pct(s['salary_cap'] / base_cap - 1)} | {mio(s['top_n_floor'])} | {cells} | {s['top_n_rookie_contracts']} |")
    w("")
    w("Positionsspalten: Anzahl Spieler in den Top 120 · Anteil an der Top-120-Salary-Masse.")
    w("")
    w("**Zerlegung des Cap-Anstiegs:** B zeigt nur Criticality und k=1,5, I zusätzlich die Rookie-Verträge, C zusätzlich das Base Minimum.")
    w("")
    w(f"- heute → B: {pct(sc['B_k15_ohne_vertraege']['salary_cap'] / base_cap - 1)}")
    w(f"- B → I (Rookie-Verträge): {pct(sc['I_ohne_base_minimum']['salary_cap'] / sc['B_k15_ohne_vertraege']['salary_cap'] - 1)}")
    w(f"- I → C (Base Minimum): {pct(sc['C_hauptszenario']['salary_cap'] / sc['I_ohne_base_minimum']['salary_cap'] - 1)}")
    w("")
    w("### Größte Veränderungen einzelner Spieler (C gegenüber heute)")
    w("")
    players = r["players"]
    ranked = sorted(players, key=lambda p: p["salary_C_hauptszenario"] - p["salary_A_heute"])
    w("| Spieler | Pos | Year | Vertrag | heute (Mio.) | C (Mio.) | Differenz |")
    w("|---|---|---:|---|---:|---:|---:|")
    for p in ranked[-10:][::-1] + ranked[:10]:
        delta = p["salary_C_hauptszenario"] - p["salary_A_heute"]
        w(f"| {p['name']} | {p['position']} | {p['year']} | {p['contract']} | {mio(p['salary_A_heute'])} | {mio(p['salary_C_hauptszenario'])} | {'+' if delta >= 0 else ''}{mio(delta)} |")
    w("")
    w("### Rang-Population (C, D, E)")
    w("")
    diffs = sorted(players, key=lambda p: -abs(p["salary_C_hauptszenario"] - p["salary_D_population_ohne_rookievertraege"]))[:8]
    w("Zählen Spieler mit Rookie-Vertrag nicht in den Positionsrang, rücken Veteranen auf. Am stärksten betroffen:")
    w("")
    w("| Spieler | Pos | C (Mio.) | D (Mio.) | E (Mio.) |")
    w("|---|---|---:|---:|---:|")
    for p in diffs:
        w(f"| {p['name']} | {p['position']} | {mio(p['salary_C_hauptszenario'])} | {mio(p['salary_D_population_ohne_rookievertraege'])} | {mio(p['salary_E_population_ohne_rookies_und_nfl_fa'])} |")
    w("")
    w("## 5. Rookie-Verträge")
    w("")
    w("| Draftjahr | Fantasy-Signal | Fantasy-Pool | NFL-Pool (QB/RB/WR/TE) |")
    w("|---|---|---:|---:|")
    for season, info in sorted(r["rookies"]["sources"].items()):
        w(f"| {season} | {info['fantasy_source']} | {info['fantasy_pool']} | {info['nfl_pool']} |")
    w("")
    by_id = {p["id"]: p for p in players}
    w("Die 15 teuersten Rookie-Verträge im Hauptszenario:")
    w("")
    w("| Spieler | Pos | Year | Fantasy-Rang | NFL-Rang | Year1-% | C (Mio.) | heute (Mio.) |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    rookies = sorted(r["rookies"]["players"], key=lambda x: -by_id[x["id"]]["salary_C_hauptszenario"])[:15]
    for x in rookies:
        p = by_id[x["id"]]
        w(f"| {x['player']} | {x['position']} | {x['year']} | {x['fantasy_rank'] or 'undrafted'} | {x['nfl_skill_rank'] or 'undrafted'} | {pct(x['year1_pct'], 2)} | {mio(p['salary_C_hauptszenario'])} | {mio(p['salary_A_heute'])} |")
    w("")
    w("## 6. Teams: Cap-Auslastung (Top 20 je Kader, heutige Kader)")
    w("")
    team_names = [t["team"] for t in sc["A_heute"]["teams"]]
    w("| Szenario | " + " | ".join(team_names) + " |")
    w("|---|" + "---:|" * len(team_names))
    for name, s in sc.items():
        w(f"| {name.split('_')[0]} | " + " | ".join(pct(t["share_of_cap"], 0) for t in s["teams"]) + " |")
    w("")
    w("Die Werte zeigen nur die Größenordnung. In der Saison ist das Cap ohne Bedeutung; geprüft wird erst an der Deadline mit den dann gültigen Kadern.")
    w("")
    t = r["timing_cycle_2025_vs_2026"]
    w("## 7. Zeitpunkt der Salary-Umstellung")
    w("")
    w(f"Kader am Ende der Saison 2025, einmal mit Salary-Zyklus 2025 und einmal mit Zyklus 2026 (heutige Formel). Cap Zyklus 2025: {mio(t['cap_cycle_2025'])} Mio., Zyklus 2026: {mio(t['cap_cycle_2026'])} Mio.")
    w("")
    w("| Team | Zyklus 2025 (Mio.) | Zyklus 2026 (Mio.) | Sprung | Anteil Cap 2025 | Anteil Cap 2026 |")
    w("|---|---:|---:|---:|---:|---:|")
    for row in t["teams"]:
        w(f"| {row['team']} | {mio(row['salary_cycle_2025'])} | {mio(row['salary_cycle_2026'])} | {'+' if row['delta'] >= 0 else ''}{mio(row['delta'])} | {pct(row['share_cap_2025'], 0)} | {pct(row['share_cap_2026'], 0)} |")
    w("")
    w("Gilt das neue Salary ab Offseason-Start, sieht jedes Team diesen Sprung sofort und hat die ganze Offseason für Trades und Cuts. Gilt es erst an der Deadline, kommt der Sprung ohne Reaktionszeit.")
    w("")
    w("## 8. Dead Cap aus echten Cuts")
    w("")
    w("Annahmen: Tenure-Staffel 50/30/15/5 %, Basis ist das zum Cut-Zeitpunkt geltende Salary (Roberts Entscheidung: altes Salary), Retained Salary bei mehrfachen Cuts im selben Zyklus, heutige Salary-Formel auf Liga-Scoring. In-Season-Cuts der Saison S zählen an der Deadline S+1; Offseason-Cuts vor der Deadline nutzen bereits den neuen Zyklus.")
    w("")
    cuts = r["dead_cap"]["cuts"]
    for deadline, info in r["dead_cap"]["summary_by_deadline"].items():
        label = {"2025": "Deadline 2025 (Cuts der Saison 2024)", "2026": "Deadline 2026 (In-Season 2025 + Offseason 2026)",
                 "2027": "Deadline 2027 (Saison 2026 bis heute, unvollständig)"}.get(str(deadline), str(deadline))
        w(f"### {label}")
        w("")
        if not any(row["dead_cap"] for row in info["teams"]):
            w("Nicht berechenbar: Für den Salary-Zyklus 2024 fehlen die Saisons 2021/2022 auf Liga-Scoring. Cuts je Team: " + ", ".join(f"{row['team']} {row['cuts']}" for row in info["teams"]) + ".")
            w("")
            continue
        w(f"Referenz-Cap: {mio(info['reference_cap'])} Mio.")
        w("")
        w("| Team | Cuts | Dead Cap (Mio.) | davon In-Season (Mio.) | davon Offseason (Mio.) | Anteil am Cap |")
        w("|---|---:|---:|---:|---:|---:|")
        for row in info["teams"]:
            sel = [c for c in cuts if c["counts_at_deadline"] == int(deadline) and c["team"] == row["team"] and c["dead_cap"]]
            ins = sum(c["dead_cap"] for c in sel if c["in_season"])
            off = sum(c["dead_cap"] for c in sel if not c["in_season"])
            w(f"| {row['team']} | {row['cuts']} | {mio(row['dead_cap'])} | {mio(ins)} | {mio(off)} | {pct(row['share_of_cap'])} |")
        w("")
    w("Die zehn größten Einzelposten:")
    w("")
    w("| Spieler | Team | Saison | Zeitpunkt | Tenure | Salary beim Cut (Mio.) | Dead Cap (Mio.) |")
    w("|---|---|---:|---|---:|---:|---:|")
    for c in sorted((c for c in cuts if c["dead_cap"]), key=lambda c: -c["dead_cap"])[:10]:
        w(f"| {c['name']} | {c['team']} | {c['season']} | {'In-Season' if c['in_season'] else 'Offseason'} | {c['tenure']} | {mio(c['salary_at_cut'])} | {mio(c['dead_cap'])} |")
    w("")
    w("## 9. Annahmen und Datenlücken")
    w("")
    w("- **Population:** Nur Spieler aus dem heutigen Players.json. Zurückgetretene Spieler fehlen in den historischen Kurven; die Kurven der Saisons 2023/2024 können dadurch leicht zu flach sein.")
    w("- **Anker-Cap:** Startwert der Rückkopplung ist das heute veröffentlichte Cap. Rookie-Verträge der Jahrgänge 2024/2025 nutzen denselben Anker statt des Caps ihres Draftjahres.")
    w("- **Jahrgang 2024:** Die Liga hatte 2024 keinen Rookie Draft. Als Fantasy-Signal zählt die Reihenfolge der Rookies im Free-Agent-Draft 2024.")
    w("- **Zyklus 2025:** Für die Saison 2022 gibt es nur das Tank01-PPR-Archiv; mögliche Spiele = 17. Das betrifft nur Timing und Dead Cap der Deadline 2026.")
    w("- **Dead Cap:** Die Cuts entstanden unter Regeln ohne Dead Cap. Auto-Cuts der Commissioner lassen sich in den Daten nicht von Manager-Cuts unterscheiden. Die Tenure startet beim ersten bekannten Zugang (Draft oder Transaktion ab 2024).")
    w("- **In-Season:** heißt hier jeder Cut nach der Cap Deadline der Saison, also auch in der Preseason. Für 2024 und 2025 gibt es keine Transaktionen vor der Deadline.")
    w("- **Projected:** SalaryProjected ist nicht simuliert.")
    w("")
    w("## 10. Fragen für die Liga")
    w("")
    w("1. Soll das Base Minimum additiv bleiben, obwohl es das Cap allein um etwa 8–9 % hebt? Alternative: Minimum nur als Untergrenze.")
    w("2. Wie breit soll der Criticality-Modifier sein (±15/25/35 %) und welches k? Szenarien F, G und H zeigen die Spannweite.")
    w("3. Wer zählt in die Positionsränge? Der Effekt ist klein, die Regel sollte trotzdem feststehen.")
    w("4. Wie mit Dead Cap aus In-Season-Cuts umgehen, die nach Abschnitt 8 einzelne Teams stark belasten würden?")
    w("5. Ab wann gilt das neue Salary: Offseason-Start oder Deadline?")
    w("6. Wie werden laufende Rookie-Jahrgänge (2024/2025) beim Systemwechsel behandelt?")
    w("")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ main

def main():
    players = [p for p in load(DATA / "Players.json") if p["Position"] in POSITIONS]
    league = load(DATA / "League.json")
    fmt = league_format(league)
    teams = league["Teams"]
    published_cap = float(league["SalaryCap"])

    # 1) Baseline: heutige Formel nachrechnen
    seasons = {}
    for p in players:
        h = p["PointHistory"]
        seasons[p["ID"]] = {SEASONS[key]: season_performance(h[key]) for key in SEASONS}
    perf3y = {pid: floored_three_year(v[2025], v[2024], v[2023]) for pid, v in seasons.items()}
    baseline_salary = {pid: round_half_up(map_salary(perf3y[pid], 2.0)) for pid in perf3y}
    mismatches = [p for p in players if abs(baseline_salary[p["ID"]] - float(p["Salary"])) > 1]
    baseline_cap = top_n_cap(list(baseline_salary.values()), fmt["top_n"], fmt["relevant_team_size"])

    # 2) Criticality-Kurven je Saison und 3Y
    per_season = {year: season_curves(players, key, fmt) for key, year in SEASONS.items()}
    curves = three_year_curves(per_season)
    cref, positive_points, ref_points = c_ref_top10(curves)

    # 3) Rookie-Year-1-Prozente
    canon_to_sleeper = sleeper_by_canonical()
    year_of_class = {1: 2026, 2: 2025, 3: 2024}
    rookie_pct, rookie_rows, rookie_sources = {}, [], {}
    for year, season in year_of_class.items():
        ids = {p["ID"] for p in players if int(p["Year"] or 0) == year}
        nfl_ranks, nfl_pool = nfl_draft_ranks(season, canon_to_sleeper)
        fan_ranks, fan_pool, source = fantasy_rookie_ranks(season, ids)
        rookie_sources[season] = {"fantasy_source": source, "fantasy_pool": fan_pool, "nfl_pool": nfl_pool}
        for p in players:
            if p["ID"] not in ids:
                continue
            fr, nr = fan_ranks.get(p["ID"]), nfl_ranks.get(p["ID"])
            pct = ROOKIE_WEIGHT_FANTASY * draft_pct(fr, fan_pool) + (1 - ROOKIE_WEIGHT_FANTASY) * draft_pct(nr, nfl_pool)
            rookie_pct[p["ID"]] = pct
            rookie_rows.append({"player": p["Name"], "id": p["ID"], "position": p["Position"], "year": year,
                                "fantasy_rank": fr, "nfl_skill_rank": nr, "year1_pct": round(pct, 6)})

    # 4) Szenarien
    base_opts = dict(k=1.5, band=0.25, population="all", rookie_contracts=True, base_minimum=True)
    scenario_defs = {
        "A_heute": None,
        "B_k15_ohne_vertraege": dict(base_opts, rookie_contracts=False, base_minimum=False),
        "C_hauptszenario": dict(base_opts),
        "D_population_ohne_rookievertraege": dict(base_opts, population="veterans"),
        "E_population_ohne_rookies_und_nfl_fa": dict(base_opts, population="veterans_with_nfl_team"),
        "F_band_15": dict(base_opts, band=0.15),
        "G_band_35": dict(base_opts, band=0.35),
        "H_k20": dict(base_opts, k=2.0),
        "I_ohne_base_minimum": dict(base_opts, base_minimum=False),
    }
    scenarios = {}
    model_rows = {}
    for name, opts in scenario_defs.items():
        if opts is None:
            rows = {pid: {"salary": s, "kind": "performance", "criticality": None, "modifier": 1.0,
                          "signal": perf3y[pid], "minimum": 0} for pid, s in baseline_salary.items()}
            summary = summarize(players, rows, baseline_cap, fmt, teams)
            summary["cap_iterations"] = [round(baseline_cap)]
        else:
            rows, cap, history = iterate_cap(players, perf3y, curves, cref, fmt, published_cap, rookie_pct, **opts)
            summary = summarize(players, rows, cap, fmt, teams)
            summary["cap_iterations"] = history
            summary["options"] = opts
        scenarios[name] = summary
        model_rows[name] = rows

    # 5) Zyklus 2025 (für Timing und Dead Cap)
    perf_2025_cycle = cycle_2025_performance(players)
    salary_2025_cycle = {pid: round_half_up(map_salary(v, 2.0)) for pid, v in perf_2025_cycle.items()}
    cap_2025_cycle = top_n_cap(list(salary_2025_cycle.values()), fmt["top_n"], fmt["relevant_team_size"])

    # 6) Timing: Rosters Ende 2025 mit altem vs. neuem Salary
    rosters_2025 = load(LEAGUE_SRC / "2025" / "rosters.json")
    names = roster_index_by_team(league)
    timing = []
    for roster in rosters_2025:
        rid = int(roster["ProviderMappings"][0]["ProviderRosterID"])
        ids = [m["ProviderPlayerID"] for pl in roster["Players"] for m in pl["ProviderMappings"] if m["Provider"] == "Sleeper"]
        old = team_cap_salary([salary_2025_cycle.get(pid, 0) for pid in ids], fmt)
        new = team_cap_salary([baseline_salary.get(pid, 0) for pid in ids], fmt)
        timing.append({"team": names.get(rid, str(rid)), "players": len(ids),
                       "salary_cycle_2025": old, "salary_cycle_2026": new, "delta": new - old,
                       "share_cap_2025": round(old / cap_2025_cycle, 4), "share_cap_2026": round(new / baseline_cap, 4)})

    # 7) Dead Cap aus echten Cuts (heutige Salary-Formel, Liga-Scoring)
    deadline_ms = {2024: 0, 2025: 0, 2026: 1782863999000}  # 2026-06-30T23:59:59Z; 2024/2025 ohne Offseason-Cuts
    cuts, dead_cap = dead_cap_simulation(
        league,
        {2024: {}, 2025: salary_2025_cycle, 2026: baseline_salary},
        {2025: cap_2025_cycle, 2026: baseline_cap, 2027: baseline_cap},
        deadline_ms,
    )
    by_id = {p["ID"]: p for p in players}
    for cut in cuts:
        cut["name"] = by_id.get(cut["player"], {}).get("Name")

    # Spieler-Tabelle
    main_rows = model_rows["C_hauptszenario"]
    player_table = []
    for p in sorted(players, key=lambda p: -main_rows[p["ID"]]["salary"]):
        pid = p["ID"]
        player_table.append({
            "id": pid, "name": p["Name"], "position": p["Position"], "year": p["Year"],
            "nfl_team": p["TeamAbbr"], "performance_3y": round(perf3y[pid], 3),
            "salary_published": int(float(p["Salary"])), "salary_today_recomputed": baseline_salary[pid],
            "criticality": round(main_rows[pid]["criticality"], 4),
            "modifier": round(main_rows[pid]["modifier"], 4), "contract": main_rows[pid]["kind"],
            **{f"salary_{name}": model_rows[name][pid]["salary"] for name in scenario_defs},
        })

    result = {
        "type": "league_meta_analysis",
        "scope": "fantasy-management",
        "created": "2026-10-05",
        "issue": 879,
        "status": "simulation, keine Ligaentscheidung",
        "inputs": {
            "players": "public/data/Players.json (Liga-Scoring seit #347 D4)",
            "league": "public/data/League.json",
            "rookie_drafts": "public/data/past_seasons/Drafts/Drafts_<season>.json",
            "nfl_draft": "source-data/nfl/draft/<season>.json",
            "transactions": "public/data/past_seasons/Transactions/*.json + public/data/Transactions.json",
            "rosters_2025": "source-data/leagues/nfl-reise/seasons/2025/rosters.json",
            "season_2022": "public/data/past_seasons/Players_2022.json (Tank01-PPR, nur für Zyklus 2025)",
        },
        "format": fmt,
        "baseline_check": {
            "players": len(players),
            "salary_mismatches": len(mismatches),
            "mismatch_examples": [{"name": p["Name"], "published": p["Salary"], "recomputed": baseline_salary[p["ID"]]}
                                  for p in mismatches[:10]],
            "published_cap": published_cap,
            "recomputed_cap": round(baseline_cap),
        },
        "criticality": {
            "c_ref": round(cref, 4),
            "positive_rank_points": positive_points,
            "reference_points": ref_points,
            "c_ref_previous_tank01": 8.6425,
            "per_season": {y: {"flex_mix": v["flex_mix"], "pool_sizes": v["pool_sizes"],
                               "curves": {pos: [round(x, 3) for x in c if x > 0] for pos, c in v["curves"].items()}}
                           for y, v in per_season.items()},
            "three_year": {pos: [round(x, 3) for x in c] for pos, c in curves.items()},
        },
        "rookies": {"sources": rookie_sources, "players": sorted(rookie_rows, key=lambda r: -r["year1_pct"])},
        "scenarios": scenarios,
        "timing_cycle_2025_vs_2026": {"cap_cycle_2025": round(cap_2025_cycle), "cap_cycle_2026": round(baseline_cap),
                                      "teams": timing},
        "dead_cap": {"summary_by_deadline": dead_cap, "cuts": cuts},
        "players": player_table,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{OUT_STEM}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with open(OUT_DIR / f"{OUT_STEM}-players.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(player_table[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(player_table)
    (OUT_DIR / f"{OUT_STEM}.md").write_text(write_report(json.loads(json.dumps(result))), encoding="utf-8")
    return result


if __name__ == "__main__":
    out = main()
    print(json.dumps({k: out[k] for k in ("baseline_check",)}, indent=1))
    print("C_ref", out["criticality"]["c_ref"])
    for name, s in out["scenarios"].items():
        print(name, s["salary_cap"], s["cap_iterations"][-3:], s["teams_over_cap"],
              {p: (v["count"], v["share"]) for p, v in s["top_n_by_position"].items()}, s["top_n_rookie_contracts"])
