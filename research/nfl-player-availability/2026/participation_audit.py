#!/usr/bin/env python3
"""Read-only audit of nflverse pbp_participation against persisted snap counts, player stats and the
nfl-player-availability product (Issue 1612, CP2). Writes JSON to stdout, changes nothing.

Inputs (downloaded by hand, never committed):
  PARTDIR/p<season>.csv        https://github.com/nflverse/nflverse-data/releases/download/pbp_participation/pbp_participation_<season>.csv
  PBPDIR/pbp<season>.csv.gz    https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_<season>.csv.gz
Usage: python3 -I participation_audit.py REPO PARTDIR SEASON [PBPDIR]
Positive evidence is the union of offense_players and defense_players (GSIS, all seasons); players_on_play is
numeric (gsis_it_id) before 2023 and is not used."""
import csv, gzip, io, json, re, sys, collections, hashlib, os
csv.field_size_limit(10**9)
repo, pdir, season = sys.argv[1], sys.argv[2], int(sys.argv[3])
pbpdir = sys.argv[4] if len(sys.argv) > 4 else pdir
NFL = f"{repo}/data-source/nfl"
GSIS = re.compile(r"^00-\d{7}$")
out = {"season": season}

sched = json.load(open(f"{NFL}/schedules/{season}.json"))["Games"]
fin = {g["GameID"]: g["Final"] for g in json.load(open(f"{NFL}/game-finality/{season}.json"))["Games"]}
games = {g["GameID"]: g for g in sched}
out["schedule_games"] = {t: sum(1 for g in sched if g["GameType"] == t) for t in sorted({g["GameType"] for g in sched})}

raw = open(f"{pdir}/p{season}.csv", "rb").read()
out["participation_sha256"] = hashlib.sha256(raw).hexdigest()
out["participation_bytes"] = len(raw)
rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
out["part_rows"] = len(rows)
out["part_columns"] = list(rows[0].keys())

# game level
pg = collections.defaultdict(list)
for r in rows:
    pg[r["nflverse_game_id"]].append(r)
out["part_games"] = len(pg)
out["part_games_not_in_schedule"] = sorted(g for g in pg if g not in games)
out["schedule_games_without_part"] = sorted(g for g in games if g not in pg)
out["schedule_games_without_part_final"] = sum(1 for g in games if g not in pg and fin.get(g))
dupkey = collections.Counter((r["nflverse_game_id"], r["play_id"]) for r in rows)
out["duplicate_game_play_rows"] = sum(v - 1 for v in dupkey.values() if v > 1)

# GSIS list integrity
bad = collections.Counter()
for r in rows:
    lists = {}
    for k in ("players_on_play", "offense_players", "defense_players"):
        v = r[k]
        lists[k] = v.split(";") if v else []
    if not lists["offense_players"] and not lists["defense_players"]:
        bad["empty_offense_and_defense"] += 1
    if not lists["players_on_play"]:
        bad["empty_players_on_play"] += 1
    for k, l in lists.items():
        if k != "players_on_play" and any(not GSIS.match(x) for x in l):
            bad["malformed_gsis_" + k] += 1
        if len(l) != len(set(l)):
            bad["dup_in_" + k] += 1
    if season >= 2023 and set(lists["players_on_play"]) != set(lists["offense_players"]) | set(lists["defense_players"]):
        bad["union_mismatch"] += 1
    if set(lists["offense_players"]) & set(lists["defense_players"]):
        bad["on_both_sides"] += 1
    if r["n_offense"] != "" and int(float(r["n_offense"])) != len(lists["offense_players"]):
        bad["n_offense_mismatch"] += 1
    if r["n_defense"] != "" and int(float(r["n_defense"])) != len(lists["defense_players"]):
        bad["n_defense_mismatch"] += 1
out["integrity"] = dict(bad)
sizes = collections.Counter(len(r["players_on_play"].split(";")) if r["players_on_play"] else 0 for r in rows)
out["players_on_play_size_hist_top"] = dict(sizes.most_common(8))

# PBP comparison
pbp = {}
pbp_path = f"{pbpdir}/pbp{season}.csv.gz"
if os.path.exists(pbp_path):
    pb = collections.defaultdict(dict)
    with gzip.open(pbp_path, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pb[r["game_id"]][r["play_id"]] = r["play_type"]
    pbp = pb
    out["pbp_games"] = len(pb)
    out["pbp_plays"] = sum(len(v) for v in pb.values())
    orphan = [(g, p) for g, p in dupkey if g not in pb or p not in pb[g]]
    out["part_plays_orphan_vs_pbp"] = len(orphan)
    out["part_plays_distinct"] = len(dupkey)
    out["pbp_plays_without_part"] = sum(1 for g, v in pb.items() for p in v if (g, p) not in dupkey)
    out["pbp_plays_without_part_by_type"] = dict(collections.Counter(
        t for g, v in pb.items() for p, t in v.items() if (g, p) not in dupkey).most_common(8))
    out["pbp_games_not_in_part"] = sorted(g for g in pb if g not in pg)[:10]
    ptypes = collections.Counter(pb[g].get(p, "ORPHAN") for g, p in dupkey)
    out["part_plays_by_pbp_type"] = dict(ptypes.most_common(12))
    # ST detection: plays whose type is kickoff/punt/field_goal/extra_point
    ST = {"kickoff", "punt", "field_goal", "extra_point"}
    out["st_plays_in_part"] = sum(v for k, v in ptypes.items() if k in ST)
    out["st_plays_in_pbp"] = sum(1 for v in pb.values() for t in v.values() if t in ST)

# identities
ids = json.load(open(f"{NFL}/identities/players.json"))["Players"]
g2c = collections.defaultdict(set)
for p in ids:
    for gid in [p["IDs"].get("GSIS")] + list(p["IDAliases"].get("GSIS", [])):
        if gid:
            g2c[gid].add(p["CanonicalPlayerID"])
out["gsis_multi_owner"] = sum(1 for v in g2c.values() if len(v) > 1)
itmap = {}
rp = f"{repo}/data-source/providers/nflverse/weekly-rosters/raw-{season}.csv"
it2g = collections.defaultdict(set)
if os.path.exists(rp):
    for r in csv.DictReader(open(rp, encoding="utf-8")):
        if r.get("gsis_it_id") and r.get("gsis_id"):
            it2g[r["gsis_it_id"]].add(r["gsis_id"])
out["it_id_ambiguous"] = sum(1 for v in it2g.values() if len(v) > 1)
numeric_season = False
out["id_format"] = "gsis_it_id-numeric" if numeric_season else "gsis"

# positives per game
pos = collections.defaultdict(lambda: collections.defaultdict(lambda: {"plays": 0, "st": 0, "scrim": 0, "types": collections.Counter()}))
ST = {"kickoff", "punt", "field_goal", "extra_point"}
for r in rows:
    gid = r["nflverse_game_id"]
    t = pbp.get(gid, {}).get(r["play_id"]) if pbp else None
    xs = set()
    for k in ("offense_players", "defense_players"):
        if r[k]:
            xs.update(r[k].split(";"))
    for x in xs:
        d = pos[gid][x]
        d["plays"] += 1
        d["types"][t or ("ORPHAN" if pbp else "unknown")] += 1
        if t in ST:
            d["st"] += 1
        elif t is not None:
            d["scrim"] += 1
unres = collections.Counter(); posc = set(); multi = 0
part_pos = {}  # (game, canonical) -> info
for gid, d in pos.items():
    for x, v in d.items():
        if numeric_season:
            gs = it2g.get(x)
            if not gs or len(gs) > 1:
                unres["gsis_unresolved"] += 1; continue
            x = next(iter(gs))
        c = g2c.get(x)
        if not c:
            unres["gsis_unresolved"] += 1; unres["unres_pg_sample"] = unres["unres_pg_sample"]
            continue
        if len(c) > 1:
            multi += 1; continue
        part_pos[(gid, next(iter(c)))] = v
out["player_games_gsis_total"] = sum(len(d) for d in pos.values())
out["player_games_gsis_unresolved"] = unres["gsis_unresolved"]
out["player_games_gsis_ambiguous"] = multi
out["player_games_positive_resolved"] = len(part_pos)
out["player_games_st_only"] = sum(1 for v in part_pos.values() if v["plays"] == v["st"] and pbp)

# existing evidence
snap = {}; snap_noid = collections.defaultdict(int)
stats = set()
for w in sorted(os.listdir(f"{NFL}/snap-counts/{season}")):
    for r in json.load(open(f"{NFL}/snap-counts/{season}/{w}"))["Records"]:
        if r["CanonicalPlayerID"]:
            snap[(r["GameID"], r["CanonicalPlayerID"])] = r
        else:
            snap_noid[r["GameID"]] += 1
if os.path.isdir(f"{NFL}/player-stats/{season}"):
    for w in sorted(os.listdir(f"{NFL}/player-stats/{season}")):
        for r in json.load(open(f"{NFL}/player-stats/{season}/{w}"))["Records"]:
            if r["CanonicalPlayerID"]:
                stats.add((r["Stats"]["game_id"], r["CanonicalPlayerID"]))
out["snap_rows_with_identity"] = len(snap)
out["snap_rows_without_identity"] = sum(snap_noid.values())

def snapped(k):
    r = snap.get(k)
    return bool(r) and (r["OffenseSnaps"] + r["DefenseSnaps"] + r["SpecialTeamsSnaps"]) > 0

cur_played = {k for k in snap if snapped(k)} | stats
out["currently_played_player_games"] = len(cur_played)
agree = cur_played & set(part_pos)
out["currently_played_also_in_part"] = len(agree)
out["currently_played_not_in_part"] = len(cur_played - set(part_pos))
only = set(part_pos) - cur_played
out["part_positive_not_in_current_played"] = len(only)

REAL = {"pass", "run", "qb_kneel", "qb_spike", "kickoff", "punt", "field_goal", "extra_point"}
out["player_games_positive_with_real_play"] = sum(1 for v in part_pos.values() if set(v["types"]) & REAL) if pbp else None
# join to availability product
prod = {}
pf = f"{repo}/data-derived/nfl-player-availability/{season}.json"
if os.path.exists(pf):
    for r in json.load(open(pf))["Records"]:
        if r["GameID"]:
            prod[(r["GameID"], r["CanonicalPlayerID"])] = r
cat = collections.Counter(); ev = collections.Counter(); samples = collections.defaultdict(list)
for k in only:
    r = prod.get(k)
    if r is None:
        # a game-final check
        cat["not_in_product_population"] += 1
        continue
    s = r["Participation"]["State"]; e = r["Participation"]["Evidence"]
    cat[f"product_{s}"] += 1
    ev[f"{s}/{e}"] += 1
    if len(samples[f"{s}/{e}"]) < 3:
        samples[f"{s}/{e}"].append({"game": k[0], "week": r["Week"], "state": r["State"], "available": r["Available"], "plays": part_pos[k]["plays"], "st": part_pos[k]["st"], "snap_row": (snap.get(k) or {}).get("OffenseSnaps"),})
out["only_part_categories"] = dict(cat)
out["only_part_evidence"] = dict(ev)
out["only_part_samples_no_ids"] = None
# NEW confirmed played = product unknown -> positive
out["new_confirmed_played_vs_unknown"] = cat.get("product_unknown", 0)
out["contradictions_product_not_played_vs_part_positive"] = cat.get("product_not-played", 0)
# contradiction detail by snap row presence/plays
cd = collections.Counter()
mins = []
for k in only:
    r = prod.get(k)
    if r and r["Participation"]["State"] == "not-played":
        v = part_pos[k]
        cd["snap_row_zero" if k in snap else "no_snap_row"] += 1
        cd["plays_le_2" if v["plays"] <= 2 else "plays_gt_2"] += 1
        cd["st_only" if v["plays"] == v["st"] and pbp else "has_scrimmage_or_unknown"] += 1
out["contradiction_detail"] = dict(cd)
out["contradictions"] = sorted(
    ({"game": k[0], "canonical": k[1], "plays": part_pos[k]["plays"], "types": dict(part_pos[k]["types"]),
      "has_real_play": bool(set(part_pos[k]["types"]) & REAL), "product_state": prod[k]["State"],
      "evidence": prod[k]["Participation"]["Evidence"], "snap_row": k in snap}
     for k in only if prod.get(k) and prod[k]["Participation"]["State"] == "not-played"),
    key=lambda x: (x["game"], x["canonical"]))
out["new_confirmed_with_real_play"] = sum(1 for k in only if prod.get(k) and prod[k]["Participation"]["State"] == "unknown" and set(part_pos[k]["types"]) & REAL)
# players in product played but absent in part, by position (misses of participation)
miss = collections.Counter()
for k, r in prod.items():
    if r["Participation"]["State"] == "played" and k not in part_pos:
        miss["played_not_in_part"] += 1
out.update(miss)
# ST-only per PFR
st_only = {k for k, r in snap.items() if r["OffenseSnaps"] + r["DefenseSnaps"] == 0 and r["SpecialTeamsSnaps"] > 0}
out["pfr_st_only_player_games"] = len(st_only)
out["pfr_st_only_also_in_part"] = len(st_only & set(part_pos))
out["pfr_st_only_in_part_with_st_plays"] = sum(1 for k in st_only if k in part_pos and part_pos[k]["st"] > 0)
# OAK regression (games with OAK as a team)
oak_games = {g for g in games if "OAK" in g.split("_")[2:]}
out["oak_games"] = len(oak_games)
if oak_games:
    out["oak_part_positive"] = sum(1 for (g, c) in part_pos if g in oak_games)
    out["oak_currently_played"] = sum(1 for (g, c) in cur_played if g in oak_games)
    out["oak_both"] = sum(1 for k in cur_played if k[0] in oak_games and k in part_pos)
# orphan plays: do they carry player lists?
orph_nonempty = 0
if pbp:
    for r in rows:
        if r["play_id"] not in pbp.get(r["nflverse_game_id"], {}) and (r["offense_players"] or r["defense_players"]):
            orph_nonempty += 1
    out["orphan_plays_with_players"] = orph_nonempty
out["empty_player_plays_by_type"] = dict(collections.Counter(pbp.get(r["nflverse_game_id"], {}).get(r["play_id"], "ORPHAN") for r in rows if not (r["offense_players"] or r["defense_players"])).most_common(6)) if pbp else None
out["unknown_product_records"] = sum(1 for r in prod.values() if r["Participation"]["State"] == "unknown")
out["unknown_product_with_part_positive"] = sum(1 for k, r in prod.items() if r["Participation"]["State"] == "unknown" and k in part_pos)
print(json.dumps(out, indent=1, default=str))
