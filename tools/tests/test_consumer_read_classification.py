"""#347 K1: every provider or published-read-model read needs a classification entry.

The registry lives in .ai-context/manual/source-of-truth-matrix.yaml under
consumerReadClassification. The test scans consumer code and fails on an unclassified
read, a stale entry or an unknown category. File and token lists are derived from the
repository (data file names from public/data, Sleeper functions from SleeperUtils.psm1),
nothing about individual players or seasons is hard-wired.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX = REPO_ROOT / ".ai-context/manual/source-of-truth-matrix.yaml"
SLEEPER_CLIENT = "public/requests/utils/invoke/SleeperUtils.psm1"
# The Sleeper HTTP client was retired in #347 (K1 follow-up); its function names stay
# reserved so a reintroduced direct call is reported as an unclassified read.
RETIRED_SLEEPER_CLIENT_FUNCTIONS = (
    "Get-SleeperLeague", "Get-SleeperMembers", "Get-SleeperRosters", "Get-SleeperWinnersBracket",
    "Get-SleeperLosersBracket", "Get-SleeperTransactions", "Get-SleeperMatchups", "Get-SleeperDrafts",
    "Get-SleeperDraft", "Get-SleeperDraftPicks", "Get-SleeperDraftTradedPicks", "Get-SleeperTradedPicks",
)

PROVIDER_HOSTS = (
    "sleeper", "nflverse", "fantasypros", "fantasycalc", "fftoday",
    "cbssports", "fantasyfootballcalculator", "espn", "tank01", "rapidapi",
)
URL_RE = re.compile(r"https?://[^\s'\"`)>]*", re.IGNORECASE)
NETWORK_RE = re.compile(
    r"Invoke-RestMethod|Invoke-WebRequest|urllib\.request|urlopen\(|"
    r"\brequests\.(?:get|post)\(|http\.client|aiohttp|httpx"
)
PY_DATA_DIR_RE = re.compile(r"public[\"']?\s*[,/]\s*[\"']?data|DATA_DIR|PUBLIC_DATA|public/data")
# G6 (#1453): the archives under public/data/past_seasons/** are published read models too. They are
# not top-level *.json files, so read_model_names() never saw them, and consumers build their paths
# dynamically (DATA / "past_seasons" / "Drafts" / f"Drafts_{season}.json"). Any executable mention of the
# archive tree or of its configured directories is therefore one legacy:past_seasons token per file.
PAST_SEASONS_TOKEN = "legacy:past_seasons"
PAST_SEASONS_RE = re.compile(r"past_seasons|\bPast[A-Za-z]*SeasonsDir\b|\$config\.\w+ArchiveDir\b|\bConfig\.\w+ArchiveDir\b")
CONFIG_REF_RE = re.compile(r"(?:\$[Cc]onfig|\(Get-Config\))\.([A-Za-z]+)File\b")

SCAN_GLOBS = (
    "public/requests/**/*.ps1",
    "public/requests/**/*.psm1",
    "tools/**/*.py",
    "fantasy-management/**/*.py",
    "fantasy-management/automation/**/*.json",
    "fantasy-management/_ai/*.json",
)


def read_model_names(repo_root: Path) -> list[str]:
    return sorted((p.stem for p in (repo_root / "public/data").glob("*.json")), key=len, reverse=True)


def sleeper_functions(repo_root: Path) -> list[str]:
    client = repo_root / SLEEPER_CLIENT
    found = set(RETIRED_SLEEPER_CLIENT_FUNCTIONS)
    if client.exists():
        found |= set(re.findall(r"function (Get-Sleeper\w+)", client.read_text(encoding="utf-8")))
    return sorted(found)


def scan_text(
    path: str, text: str, names: list[str], sleeper_fns: list[str], helpers: dict[str, str] | None = None
) -> set[str]:
    tokens: set[str] = set()
    name_alt = "|".join(names)
    path_re = re.compile(rf"public/data/({name_alt})\.json")
    for url in URL_RE.findall(text):
        for host in PROVIDER_HOSTS:
            if host in url.lower():
                tokens.add(f"provider:{host}")
    if path != SLEEPER_CLIENT and sleeper_fns:
        for match in re.finditer(r"\b(" + "|".join(sleeper_fns) + r")\b", text):
            tokens.add(f"sleeper-api:{match.group(1)}")
    if NETWORK_RE.search(text):
        tokens.add("network")
    if path.endswith((".ps1", ".psm1")):
        for match in path_re.finditer(text):
            tokens.add(f"legacy:{match.group(1)}")
        for match in CONFIG_REF_RE.finditer(text):
            if match.group(1) in names or match.group(1) + "s" in names:
                tokens.add(f"legacy:{match.group(1)}")
        # A call of a declared reader helper is a read of the read model it wraps (L7).
        for helper, model in (helpers or {}).items():
            if re.search(rf"(?<!function )(?<![\w-]){re.escape(helper)}\b", text):
                tokens.add(f"legacy:{model}")
    elif path.endswith(".py"):
        if PY_DATA_DIR_RE.search(text):
            for match in re.finditer(rf"[\"'/\s]({name_alt})\.json", text):
                tokens.add(f"legacy:{match.group(1)}")
        for match in path_re.finditer(text):
            tokens.add(f"legacy:{match.group(1)}")
    elif path.endswith(".json"):
        for match in path_re.finditer(text):
            tokens.add(f"legacy:{match.group(1)}")
    if path.endswith((".py", ".ps1", ".psm1", ".json")) and PAST_SEASONS_RE.search(text):
        tokens.add(PAST_SEASONS_TOKEN)
    return tokens


def scan_repository(repo_root: Path) -> dict[str, set[str]]:
    names = read_model_names(repo_root)
    fns = sleeper_functions(repo_root)
    helpers = (load_registry().get("helperReads") or {})
    found: dict[str, set[str]] = {}
    for pattern in SCAN_GLOBS:
        for file in repo_root.glob(pattern):
            rel = file.relative_to(repo_root)
            if "node_modules" in rel.parts or "tests" in rel.parts:
                continue
            if file.name.startswith("test_") or "RegressionTest" in file.name:
                continue
            tokens = scan_text(rel.as_posix(), file.read_text(encoding="utf-8", errors="ignore"), names, fns, helpers)
            if tokens:
                found[rel.as_posix()] = tokens
    return found


def load_registry() -> dict:
    data = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    return data["consumerReadClassification"]


def compare(found: dict[str, set[str]], registry: dict) -> list[str]:
    categories = set(registry["categories"])
    consumers = registry["consumers"]
    problems: list[str] = []
    for path, tokens in sorted(found.items()):
        entry = consumers.get(path)
        if entry is None:
            problems.append(f"unclassified consumer {path}: reads {sorted(tokens)}")
            continue
        declared = entry.get("reads") or {}
        for token in sorted(tokens - set(declared)):
            problems.append(f"unclassified read {token} in {path}")
        for token in sorted(set(declared) - tokens):
            problems.append(f"stale classification {token} in {path}: no such read found")
        for token, category in declared.items():
            if category not in categories:
                problems.append(f"unknown category {category!r} for {token} in {path}")
    for path in sorted(set(consumers) - set(found)):
        problems.append(f"stale consumer entry {path}: no read found")
    return problems



# --- G6 (#1453): narrow Angular guards and the analysis-snapshot protection -----------------------------
# Text rules over src/app, deliberately without an AST: a loader, an archive path, a canonical model ID or a
# cap-limit input. They do not forbid aggregation or display logic in Angular; the documented exceptions live in
# source-of-truth-matrix.yaml under angularDomainGuard / analysisSnapshotPolicy.
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_RE = re.compile(r"(?<![:\"'])//[^\n]*")
HTTP_LOADER_RE = re.compile(r"\bHttpClient\b|\bhttp\.(?:get|post|put|delete)\b")
ARCHIVE_PATH_RE = re.compile(r"past_seasons")
DATA_URL_RE = re.compile(r"[\"'`]data/[^\"'`]*[\"'`]")
CAP_LIMIT_INPUT_RE = re.compile(r"SalaryRelevantTeamSize", re.IGNORECASE)
CENTRAL_MODEL_ID_RE = re.compile(
    r"\b(?:salary|salary-cap|roster-cap|auto-cut|grading|standings|awards|win-prob|season-stats|team-range"
    r"|lifecycle|repairability|rivalry)-v\d+\b"
)
# ADR-083 (#1455): head-to-head counting and consolation classification are generator-owned (Rivalry.json).
RIVALRY_LOGIC_RE = re.compile(
    r"\bisConsolationMatchup\b|\bbuildHeadToHead\b|\bbuildRivalryRecords\b|\bcollectRivalryGames\b|\bisPlayoffsComplete\b"
)
RIVALRY_VIEW_FILES = (
    "src/app/shared/components/team-rivals-tab/team-rivals-tab.ts",
    "src/app/shared/components/league-matchups/league-matchups.ts",
)


def load_guard_registry() -> dict:
    data = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    return data["angularDomainGuard"]


def strip_ts_comments(text: str) -> str:
    return LINE_COMMENT_RE.sub("", BLOCK_COMMENT_RE.sub("", text))


def angular_sources(repo_root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for file in (repo_root / "src/app").rglob("*.ts"):
        if file.name.endswith((".spec.ts", ".d.ts")):
            continue
        found[file.relative_to(repo_root).as_posix()] = strip_ts_comments(file.read_text(encoding="utf-8"))
    return found


def check_angular_guards(sources: dict[str, str], guard: dict) -> list[str]:
    loaders = set(guard["httpLoaderFiles"])
    archives = set(guard["archivePathFiles"])
    cap_inputs = {row["path"] for row in guard["capLimitInputFiles"]}
    problems: list[str] = []
    for path, code in sorted(sources.items()):
        if HTTP_LOADER_RE.search(code) and path not in loaders:
            problems.append(f"new HTTP loader outside DataApiService: {path}")
        if ARCHIVE_PATH_RE.search(code) and path not in archives:
            problems.append(f"past_seasons archive path outside DataApiService: {path}")
        if DATA_URL_RE.search(code) and path not in loaders:
            problems.append(f"generated-data URL literal outside DataApiService: {path}")
        if CAP_LIMIT_INPUT_RE.search(code) and path not in cap_inputs:
            problems.append(f"cap limit input (SalaryRelevantTeamSize) outside documented exceptions: {path}")
        if CENTRAL_MODEL_ID_RE.search(code):
            problems.append(f"central model ID in executable frontend code: {path}")
    for path in sorted((loaders | archives | cap_inputs) - set(sources)):
        problems.append(f"stale angularDomainGuard entry: {path}")
    return problems


def check_rivalry_comes_from_product(sources: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for path, code in sorted(sources.items()):
        if RIVALRY_LOGIC_RE.search(code):
            problems.append(f"{path}: head-to-head counting or consolation classification in Angular (ADR-083)")
    for path in RIVALRY_VIEW_FILES:
        code = sources.get(path)
        if code is None:
            problems.append(f"missing rivalry view file: {path}")
        elif "TeamRivalryService" not in code:
            problems.append(f"{path} no longer reads the rivalry product through TeamRivalryService")
        elif "getPastMatchupsRaw" in code:
            problems.append(f"{path} loads the Matchups history for rivalry instead of Rivalry.json")
    return problems


def check_overview_cap_reads_central_outlook(sources: dict[str, str], files: list[str]) -> list[str]:
    problems: list[str] = []
    for path in files:
        code = sources.get(path)
        if code is None:
            problems.append(f"missing overview cap file: {path}")
            continue
        if CAP_LIMIT_INPUT_RE.search(code):
            problems.append(f"{path}: local cap recomputation from SalaryRelevantTeamSize")
    util = sources.get("src/app/shared/utils/overview-cap.util.ts", "")
    if "CapOutlook" not in util:
        problems.append("overview-cap.util.ts no longer reads the central CapOutlook")
    return problems


def check_analysis_snapshot_policy(registry: dict, policy: dict, root: Path) -> list[str]:
    problems: list[str] = []
    declared = {row["path"]: row for row in policy["files"]}
    classified = {
        path for path, entry in registry["consumers"].items()
        if "analysis-snapshot-input" in (entry.get("reads") or {}).values()
    }
    for path in sorted(classified - set(declared)):
        problems.append(f"analysis-snapshot-input without snapshot policy: {path}")
    for path in sorted(set(declared) - classified):
        problems.append(f"stale snapshot policy: {path}")
    for path, row in declared.items():
        for key in ("path", "output"):
            if not (root / row[key]).is_file():
                problems.append(f"snapshot policy file missing: {row[key]}")
        stem = Path(path).stem
        for pattern in policy["productiveScanGlobs"]:
            for file in root.glob(pattern):
                rel = file.relative_to(root)
                if "tests" in rel.parts or file.name.startswith("test_") or rel.as_posix() == path or not file.is_file():
                    continue
                if stem in file.read_text(encoding="utf-8", errors="ignore"):
                    problems.append(f"productive use of analysis snapshot {stem}: {rel.as_posix()}")
    return problems


# #1263 C2: only pre-existing, explicitly classified transitional reads are
# tolerated while their source-to-derived cutovers remain pending. A registry
# category does not itself authorize a consumer-to-consumer dependency.
TRANSITIONAL_CATEGORIES = frozenset({
    "app-read-model-chain", "intentional-overlay", "legacy-read-model-pending",
})
TRANSITIONAL_BASELINE = frozenset()


def compare_transitional_reads(registry: dict) -> list[str]:
    actual = {
        (path, token, category)
        for path, entry in registry["consumers"].items()
        for token, category in (entry.get("reads") or {}).items()
        if category in TRANSITIONAL_CATEGORIES
    }
    problems = [f"new consumer-to-consumer exception: {entry}" for entry in sorted(actual - TRANSITIONAL_BASELINE)]
    problems.extend(f"obsolete transitional baseline: {entry}" for entry in sorted(TRANSITIONAL_BASELINE - actual))
    return problems

def check_productive_edge_audit(edges: object, root: Path) -> list[str]:
    """Validate G1's bounded declarations; never claim automatic callgraph coverage."""
    errors: list[str] = []
    if not isinstance(edges, list) or not edges:
        return ["empty productive edge audit"]
    seen: set[str] = set()
    types = {"source-fact", "normalized", "shared-derived", "consumer-adapter",
             "display-only", "hypothetical", "state-feedback", "blocked/unknown"}
    for index, row in enumerate(edges):
        if not isinstance(row, dict):
            errors.append(f"invalid edge {index}: must be a mapping")
            continue
        edge_id = row.get("id")
        if not isinstance(edge_id, str) or not edge_id or edge_id in seen:
            errors.append(f"missing/duplicate edge id {index}")
        else:
            seen.add(edge_id)
        if row.get("type") not in types:
            errors.append(f"invalid semantic edge type {index}")
        if row.get("status") not in {"verified", "blocked", "unknown"}:
            errors.append(f"invalid edge status {index}")
        if row.get("status") == "verified" and row.get("owner") in ("unresolved", None, ""):
            errors.append(f"unverified owner for edge {index}")
        for key in ("source", "owner", "product", "unavailable"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"missing edge field {index}: {key}")
        for key in ("consumers", "identity", "evidenceFiles"):
            values = row.get(key)
            if not isinstance(values, list) or not values or any(
                not isinstance(v, str) or not v.strip() for v in values
            ):
                errors.append(f"missing edge list {index}: {key}")
        files = row.get("evidenceFiles")
        if isinstance(files, list):
            for path in files:
                if (not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts
                        or not (root / path).is_file()):
                    errors.append(f"missing/unsafe evidence path {index}: {path}")
    return errors



def check_source_family_coverage_audit(matrix: object, audit: object, root: Path) -> list[str]:
    """Validate all Source-family classifications without claiming full cross-language reachability."""
    issues: list[str] = []
    if not isinstance(matrix, dict) or not isinstance(audit, dict):
        return ["invalid source-family audit or canonical matrix"]
    if audit.get("status") != "partial" or audit.get("issue") != 1263:
        issues.append("source-family audit must stay partial and issue-backed")
    edge_list = (audit.get("_edgeList") or [])
    if not isinstance(edge_list, list):
        return issues + ["invalid audited edge list"]
    edges = {
        row["id"]: row for row in edge_list
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    source_families = audit.get("families")
    if not isinstance(source_families, list):
        return issues + ["missing source-family coverage rows"]
    names: set[str] = set()
    actual_names = set(matrix)
    valid_states = {"linked-partial", "unknown", "blocked", "out-of-runtime"}
    for i, row in enumerate(source_families):
        if not isinstance(row, dict):
            issues.append(f"invalid source family row {i}")
            continue
        name = row.get("family")
        if not isinstance(name, str) or not name or name in names:
            issues.append(f"duplicate/missing source family at {i}")
        else:
            names.add(name)
        state = row.get("status")
        if state not in valid_states:
            issues.append(f"invalid source family status: {name}: {state}")
        refs = row.get("edgeIds")
        if not isinstance(refs, list) or any(not isinstance(v, str) for v in refs):
            issues.append(f"invalid source family edgeIds: {name}")
            refs = []
        for ref in refs:
            if ref not in edges:
                issues.append(f"stale source family edge reference: {name}: {ref}")
        if state == "linked-partial" and not any(
            ref in edges and edges[ref].get("status") == "verified" for ref in refs
        ):
            issues.append(f"unverified linked source family: {name}")
        if state == "out-of-runtime" and refs:
            issues.append(f"retired/non-runtime family cannot claim active edge: {name}")
        for field in ("supported", "remaining"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                issues.append(f"missing source family {field}: {name}")
        evidence = row.get("evidenceFiles")
        if not isinstance(evidence, list) or not evidence:
            issues.append(f"missing source family evidence: {name}")
        else:
            for evidence_file in evidence:
                if (not isinstance(evidence_file, str)
                    or not evidence_file
                    or Path(evidence_file).is_absolute()
                    or ".." in Path(evidence_file).parts
                    or not (root / evidence_file).is_file()):
                    issues.append(f"missing/unsafe source family evidence: {name}: {evidence_file}")
    for missing in sorted(actual_names - names):
        issues.append(f"missing source family: {missing}")
    for extra in sorted(names - actual_names):
        issues.append(f"unrecognized source family: {extra}")
    if len(matrix) != 23:
        issues.append("source family baseline drift: expected 23 canonical families")

    products = audit.get("downstreamProducts")
    if not isinstance(products, list) or not products:
        return issues + ["missing separately audited downstream products"]
    product_names: set[str] = set()
    for i, row in enumerate(products):
        if not isinstance(row, dict):
            issues.append(f"invalid downstream product row {i}")
            continue
        name = row.get("product")
        if not isinstance(name, str) or not name or name in product_names:
            issues.append(f"duplicate/missing downstream product at {i}")
        else:
            product_names.add(name)
        state = row.get("status")
        if state not in {"linked-partial", "unmapped", "blocked"}:
            issues.append(f"invalid downstream product status: {name}")
        refs = row.get("edgeIds")
        if not isinstance(refs, list) or any(not isinstance(v, str) for v in refs):
            issues.append(f"invalid downstream product edgeIds: {name}")
            refs = []
        for ref in refs:
            if ref not in edges:
                issues.append(f"stale downstream product edge reference: {name}: {ref}")
        if state == "linked-partial" and not any(
            ref in edges and edges[ref].get("status") == "verified" for ref in refs
        ):
            issues.append(f"unverified downstream product: {name}")
        if state == "unmapped" and refs:
            issues.append(f"unmapped downstream product claims edges: {name}")
        if not isinstance(row.get("remaining"), str) or not row["remaining"].strip():
            issues.append(f"missing downstream product gap: {name}")
        files = row.get("evidenceFiles")
        if not isinstance(files, list) or not files:
            issues.append(f"missing downstream product evidence: {name}")
        else:
            for evidence_file in files:
                if (not isinstance(evidence_file, str)
                    or not evidence_file
                    or Path(evidence_file).is_absolute()
                    or ".." in Path(evidence_file).parts
                    or not (root / evidence_file).is_file()):
                    issues.append(f"missing/unsafe downstream product evidence: {name}: {evidence_file}")
    return issues


def check_downstream_route_audit(audit: object, root: Path) -> list[str]:
    """Code and workflow trace inventory only; never a live or complete reachability assertion."""
    if not isinstance(audit, dict) or not isinstance(audit.get("downstreamRoutes"), list):
        return ["missing downstream route audit"]
    expected = {
        "nfl-games-to-game-context": "nfl-games",
        "team-week-performance-live-to-recaps": "team-week-performance",
        "team-week-performance-historical-backfill": "team-week-performance",
        "computed-matchup-context-to-app": "fantasy-game-context-and-matchups",
        "team-range-projections-to-app": "matchup-projections",
    }
    products = {p.get("product"): p for p in audit.get("downstreamProducts", []) if isinstance(p, dict)}
    issues: list[str] = []
    seen: set[str] = set()
    cache: dict[str, str] = {}
    for i, route in enumerate(audit["downstreamRoutes"]):
        if not isinstance(route, dict):
            issues.append(f"invalid downstream route {i}")
            continue
        rid = route.get("id")
        if rid not in expected or rid in seen:
            issues.append(f"unknown/duplicate downstream route: {rid}")
        seen.add(rid)
        if rid in expected and route.get("product") != expected[rid]:
            issues.append(f"wrong downstream route product: {rid}")
        if products.get(route.get("product"), {}).get("status") != "linked-partial":
            issues.append(f"nonpartial downstream route product: {rid}")
        if route.get("status") != "linked-partial":
            issues.append(f"false downstream route completion: {rid}")
        if route.get("writeScope") not in {"data-derived/nfl-games", "data-derived/team-week-performance", "public/data"}:
            issues.append(f"invalid downstream route write scope: {rid}")
        for field in ("meaning", "remaining"):
            if not isinstance(route.get(field), str) or not route[field].strip():
                issues.append(f"missing downstream route {field}: {rid}")
        witnesses = route.get("evidence")
        if not isinstance(witnesses, list) or len(witnesses) < 4:
            issues.append(f"missing downstream route evidence: {rid}")
            continue
        path_set: set[str] = set()
        for witness in witnesses:
            if not isinstance(witness, dict):
                issues.append(f"invalid downstream route witness: {rid}")
                continue
            path, needle = witness.get("file"), witness.get("contains")
            if (not isinstance(path, str) or not isinstance(needle, str) or not needle
                    or Path(path).is_absolute() or ".." in Path(path).parts or not (root / path).is_file()):
                issues.append(f"missing/unsafe downstream route witness: {rid}")
                continue
            path_set.add(path)
            if path not in cache:
                cache[path] = (root / path).read_text(encoding="utf-8")
            if needle not in cache[path]:
                issues.append(f"stale downstream route witness: {rid} {path}")
        if route.get("workflow") not in path_set or not str(route.get("workflow", "")).startswith(".github/workflows/"):
            issues.append(f"unwitnessed downstream workflow: {rid}")
    for rid in sorted(set(expected) - seen):
        issues.append(f"missing downstream route: {rid}")
    return issues


class ConsumerReadClassificationTest(unittest.TestCase):

    def test_g1_productive_edge_inventory_has_owner_identity_and_evidence(self) -> None:
        audit = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))["productiveEdgeAudit"]
        self.assertEqual("partial", audit["status"])
        self.assertEqual(1263, audit["issue"])
        self.assertEqual([], check_productive_edge_audit(audit["edges"], REPO_ROOT))
        self.assertTrue(any(row["status"] == "blocked" for row in audit["edges"]))
        self.assertTrue(any(row["status"] == "unknown" for row in audit["edges"]))
        valid = next(row for row in audit["edges"] if row["status"] == "verified")
        for change, token in (
            ({"type": "invalid"}, "invalid semantic edge type"),
            ({"owner": "unresolved"}, "unverified owner"),
            ({"evidenceFiles": ["nonexistent/untrusted.py"]}, "missing/unsafe evidence path"),
            ({"identity": []}, "missing edge list"),
        ):
            self.assertTrue(any(token in reason for reason in check_productive_edge_audit(
                [{**valid, **change}], REPO_ROOT
            )), change)

    def test_g1_expanded_productive_edge_owner_boundaries(self) -> None:
        """Pin code-evidenced G1 additions without claiming exhaustive callgraph coverage."""
        audit = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))["productiveEdgeAudit"]
        by_id = {row["id"]: row for row in audit["edges"]}
        required = {
            "canonical-standings-model",
            "canonical-league-history-model",
            "league-drafts-to-league-home",
            "standings-to-draft-order",
            "player-valuation-to-app-players",
            "player-week-fantasy-app-delivery",
            "fm-canonical-league-ownership",
            "fm-canonical-member-display",
            "fm-age-evaluation-reference",
            "fm-fa-board-lifecycle-evaluation",
            "league-finality-to-standings",
        }
        self.assertTrue(required <= by_id.keys())
        self.assertTrue(all(by_id[key]["status"] == "verified" for key in required))
        self.assertEqual("display-only", by_id["fm-canonical-member-display"]["type"])
        self.assertEqual("partial", audit["status"])

        league = (REPO_ROOT / "public/requests/RequestLeague.ps1").read_text(encoding="utf-8")
        self.assertIn("Get-LeagueDraftsProduct", league)
        self.assertIn("Get-LeagueStandingsProduct", league)
        self.assertNotIn("Get-LeagueDraftsLocal", league)
        history = (REPO_ROOT / "tools/league_history_sources.py").read_text(encoding="utf-8")
        self.assertIn("make_standings_loader", history)
        players = (REPO_ROOT / "tools/players_app_publish.py").read_text(encoding="utf-8")
        self.assertIn("derived_data.materialize_player_valuation(", players)
        ops = (REPO_ROOT / "fantasy-management/_ai/scripts/build_fantasy_operations_inputs.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("age_reference_date(", ops)
        self.assertIn("enrich_from_members(", ops)


    def test_g1_all_23_source_families_have_bounded_evidence_and_separate_products(self) -> None:
        document = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
        audit = document["sourceFamilyCoverageAudit"]
        self.assertEqual("partial", audit["status"])
        self.assertEqual(23, len(audit["families"]))
        self.assertEqual(9, len(audit["downstreamProducts"]))
        self.assertEqual(
            [],
            check_source_family_coverage_audit(
                document["matrix"],
                {**audit, "_edgeList": document["productiveEdgeAudit"]["edges"]},
                REPO_ROOT,
            ),
        )
        statuses = {r["family"]: r["status"] for r in audit["families"]}
        self.assertEqual("out-of-runtime", statuses["nflGameBoxscoreLegacy"])
        self.assertEqual("blocked", statuses["nflContracts"])
        self.assertEqual("unknown", statuses["nflPlayerProfile"])
        self.assertEqual("unknown", statuses["nflDepthChart"])
        self.assertEqual("linked-partial", statuses["byeWeek"])
        self.assertEqual("unresolved", document["matrix"]["nflPlayerProfile"]["durableCanonicalPrimary"])
        self.assertEqual("retired-347-g4", document["matrix"]["nflGameBoxscoreLegacy"]["migrationState"])

    def test_g6_source_family_coverage_negative_cases_fail_closed(self) -> None:
        from copy import deepcopy
        document = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
        baseline = {**document["sourceFamilyCoverageAudit"],
                    "_edgeList": document["productiveEdgeAudit"]["edges"]}
        matrix = document["matrix"]
        alterations = (
            (lambda a: a["families"].pop(), "missing source family"),
            (lambda a: a["families"][0].update(family="not-a-source"), "unrecognized source family"),
            (lambda a: a["families"][2]["edgeIds"].append("no-such-verified-edge"), "stale source family edge reference"),
            (lambda a: a["families"][2].update(status="verified"), "invalid source family status"),
            (lambda a: a["families"][2].update(evidenceFiles=["missing/traversal.py"]), "missing/unsafe source family evidence"),
            (lambda a: a["families"][2].update(remaining=""), "missing source family remaining"),
            (lambda a: a["downstreamProducts"][0].update(status="unmapped", edgeIds=["canonical-standings-model"]), "unmapped downstream product claims edges"),
            (lambda a: a.update(status="complete"), "source-family audit must stay partial"),
        )
        for change, expected in alterations:
            with self.subTest(expected=expected):
                candidate = deepcopy(baseline)
                change(candidate)
                errors = check_source_family_coverage_audit(matrix, candidate, REPO_ROOT)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_g1_derived_product_links_keep_partial_and_code_witnesses(self) -> None:
        document = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
        edges = {r["id"]: r for r in document["productiveEdgeAudit"]["edges"]}
        products = {r["product"]: r for r in document["sourceFamilyCoverageAudit"]["downstreamProducts"]}
        witnesses = {
            "nfl-games": ("nfl-games-canonical-materialization", "tools/nfl_games_materialize.py", "build_nfl_games(*inputs)"),
            "team-week-performance": ("team-week-performance-canonical-materialization", "tools/team_week_performance_materialize.py", "load_verified_week_inputs("),
            "fantasy-game-context-and-matchups": ("matchup-context-canonical-app-delivery", "tools/matchup_context_app_publish.py", "resolve_matchups("),
            "matchup-projections": ("matchup-projections-central-model-delivery", "tools/player_week_fantasy_refresh.py", "publish_matchup_projections("),
        }
        for name, (edge, path, code_witness) in witnesses.items():
            with self.subTest(name=name):
                self.assertEqual("linked-partial", products[name]["status"])
                self.assertIn(edge, products[name]["edgeIds"])
                self.assertEqual("verified", edges[edge]["status"])
                self.assertIn(code_witness, (REPO_ROOT / path).read_text(encoding="utf-8"))
                self.assertIn("remain unverified", products[name]["remaining"])
        self.assertEqual("partial", document["productiveEdgeAudit"]["status"])
        self.assertEqual("partial", document["sourceFamilyCoverageAudit"]["status"])

    def test_g1_downstream_publication_routes_are_witnessed(self) -> None:
        audit = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))["sourceFamilyCoverageAudit"]
        self.assertEqual(5, len(audit["downstreamRoutes"]))
        self.assertEqual([], check_downstream_route_audit(audit, REPO_ROOT))
        self.assertEqual("partial", audit["status"])

    def test_g6_downstream_publication_route_negative_cases_fail_closed(self) -> None:
        from copy import deepcopy
        audit = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))["sourceFamilyCoverageAudit"]
        changes = (
            (lambda a: a["downstreamRoutes"].pop(), "missing downstream route"),
            (lambda a: a["downstreamRoutes"][0].update(status="complete"), "false downstream route completion"),
            (lambda a: a["downstreamRoutes"][0].update(product="league-standings"), "wrong downstream route product"),
            (lambda a: a["downstreamRoutes"][0].update(writeScope="data-source"), "invalid downstream route write scope"),
            (lambda a: a["downstreamRoutes"][0]["evidence"][0].update(contains="not-an-existing-job"), "stale downstream route witness"),
            (lambda a: a["downstreamRoutes"][0].update(evidence=[]), "missing downstream route evidence"),
        )
        for mutate, expected in changes:
            with self.subTest(expected=expected):
                candidate = deepcopy(audit)
                mutate(candidate)
                issues = check_downstream_route_audit(candidate, REPO_ROOT)
                self.assertTrue(any(expected in issue for issue in issues), issues)

    def test_g3_bye_week_source_contract_matches_canonical_runtime(self) -> None:
        matrix = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))["matrix"]
        bye = matrix["byeWeek"]
        source = (REPO_ROOT / "tools/player_valuation_sources.py").read_text(encoding="utf-8")
        reader = (REPO_ROOT / "tools/derived_data_lib/players_read_model.py").read_text(encoding="utf-8")
        self.assertEqual("canonical-schedule-derived-active", bye["migrationState"])
        self.assertEqual("tools/player_valuation_sources.py::team_bye_weeks", bye["derivedOwner"])
        self.assertIn("data-source/nfl/schedules/<season>.json", bye["durableCanonicalPrimary"])
        self.assertNotIn("Tank01", bye["fallback"])
        self.assertIn('DATA_SOURCE_ROOT / "nfl/schedules"', source)
        self.assertIn('schedule.get("SourceDataset") != "nflverse.schedules"', source)
        self.assertIn('bye_weeks=sources.team_bye_weeks(repo_root, season)', reader)
        self.assertNotIn("Tank01", reader)

    def test_g6_angular_standings_uses_shared_weekly_table_not_score_replay(self) -> None:
        # This is a narrowly scoped domain-replay guard. Display matchup ordering
        # stays allowed; sorting any Angular array is NOT categorically prohibited.
        source = (REPO_ROOT / "src/app/shared/utils/overview-weekly-dashboard.util.ts").read_text(encoding="utf-8")
        start = source.index("function buildOverviewStandingsSnapshot(")
        end = source.find("\nfunction ", start + 1)
        routine = source[start:end if end >= 0 else len(source)]
        # Both exact-week selection and a validated earlier-week fallback are
        # presentation-only reads of the canonical League Standings product.
        self.assertIn("const season = league.Standings.find(", routine)
        self.assertIn("const candidates = (season?.Weeks ?? [])", routine)
        self.assertIn("row.Week <= completedWeek", routine)
        self.assertIn("candidate.Teams", routine)
        self.assertIn("counts.reduce((total, count) => total + count, 0) !== candidate.Week", routine)
        self.assertIn("resolveCanonicalPlaceDelta(team, row.Place, candidate.Week, candidate.Week)", routine)
        self.assertNotIn("lastWeek.Matchups", routine)
        self.assertNotIn("standingsWinPercentage(", routine)
        self.assertNotIn("rank_teams(", routine)
        # Negative fixture: a reintroduced Matchups-based ranking is detectable.
        self.assertIn("lastWeek.Matchups", routine + "\nconst ranking = lastWeek.Matchups;")

    def test_transitional_consumer_to_consumer_reads_do_not_expand(self) -> None:
        """Known G2/G3 debt is frozen, not a reusable exemption for future domain reads."""
        self.assertEqual([], compare_transitional_reads(load_registry()))

    def test_new_or_silently_reclassified_transitional_reads_are_detected(self) -> None:
        registry = load_registry()
        extra = {**registry, "consumers": {
            **registry["consumers"],
            "tools/new_consumer.py": {"reads": {"legacy:League": "app-read-model-chain"}},
        }}
        self.assertTrue(any("new consumer-to-consumer exception" in s for s in compare_transitional_reads(extra)))
        # C8j: the real frozen baseline is now empty. Exercise the obsolete-entry
        # branch with a simulated historical baseline rather than indexing an empty set.
        from unittest import mock
        historical = frozenset({
            ("tools/derived_data.py", "legacy:Players", "legacy-read-model-pending"),
        })
        with mock.patch.dict(globals(), {"TRANSITIONAL_BASELINE": historical}):
            self.assertTrue(any("obsolete transitional baseline" in s
                                for s in compare_transitional_reads(registry)))

    def test_every_consumer_read_is_classified(self) -> None:
        problems = compare(scan_repository(REPO_ROOT), load_registry())
        self.assertEqual([], problems, "\n".join(problems))

    def test_canonical_ownership_legacy_league_is_only_an_explicit_shadow(self) -> None:
        """An App League reference in the CLI is not a productive display adapter."""
        path = "fantasy-management/_ai/scripts/canonical_league_ownership.py"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        self.assertNotIn("def enrich_canonical_ownership_with_display(", source)
        self.assertIn("def compare_to_app_league(", source)
        self.assertIn("if args.compare_league:", source)
        self.assertIn("enrich_from_members", (
            REPO_ROOT / "fantasy-management/_ai/scripts/operations_team_display.py"
        ).read_text(encoding="utf-8"))
        registry = load_registry()
        reads = registry["consumers"][path]["reads"]
        self.assertEqual(reads.get("legacy:League"), "validation-shadow")
        self.assertEqual([], compare_transitional_reads(registry))
        mutated = {**registry, "consumers": {**registry["consumers"], path: {
            **registry["consumers"][path],
            "reads": {**reads, "legacy:League": "intentional-overlay"},
        }}}
        self.assertTrue(any("new consumer-to-consumer exception" in problem
                            for problem in compare_transitional_reads(mutated)))

    def test_player_valuation_retired_published_hold_seed_remains_retired(self) -> None:
        """A consumer output is never reintroduced as a Shared Derived input."""
        materializer_path = "tools/derived_data.py"
        audit_path = "tools/derived_clean_root_audit.py"
        materializer = (REPO_ROOT / materializer_path).read_text(encoding="utf-8")
        audit = (REPO_ROOT / audit_path).read_text(encoding="utf-8")
        self.assertNotIn("def load_hold_seed(", materializer)
        self.assertNotIn("def _with_seed(", materializer)
        self.assertNotIn('"--hold-seed-players-file"', materializer)
        self.assertNotIn("hold_seed_file", audit)
        self.assertNotIn("load_hold_seed", audit)
        self.assertNotIn("Players.json", audit)
        registry = load_registry()
        self.assertEqual([], compare_transitional_reads(registry))
        self.assertNotIn(materializer_path, registry["consumers"])
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertEqual(set(), scan_text(materializer_path, materializer, names, functions))
        self.assertNotIn("legacy:Players", scan_text(audit_path, audit, names, functions))
        injected = materializer + '\nplayers = "public/data/Players.json"\n'
        self.assertIn("legacy:Players", scan_text(materializer_path, injected, names, functions))
        self.assertTrue(any("unclassified" in issue for issue in compare(
            {materializer_path: scan_text(materializer_path, injected, names, functions)},
            registry,
        )))
        edited = {**registry, "consumers": {**registry["consumers"], materializer_path: {
            "reads": {"legacy:Players": "legacy-read-model-pending"},
        }}}
        self.assertTrue(any("new consumer-to-consumer exception" in problem
                            for problem in compare_transitional_reads(edited)))

    def test_disabled_weekly_review_declares_only_canonical_lifecycle(self) -> None:
        path = "fantasy-management/automation/jobs/weekly-league-review.json"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        import json
        job = json.loads(source)
        self.assertFalse(job["enabled"])
        self.assertEqual(job["trigger"]["source_type"], "canonical_lifecycle")
        self.assertEqual(job["trigger"]["final_week_field"], "FinalScoredWeek")
        self.assertNotIn("league_source", job["trigger"])
        self.assertNotIn("public/data/League.json", source)
        self.assertNotIn("public/data/Timestamps.json", source)
        self.assertTrue(any("league-refresh-witnesses/" in dep["path"]
                            for dep in job["dependencies"]))
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertEqual(set(), scan_text(path, source, names, functions))
        injected = source.replace('"source_type": "canonical_lifecycle"',
                                  '"league_source": "public/data/League.json"')
        self.assertIn("legacy:League", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:League" in issue for issue in compare(
            {path: scan_text(path, injected, names, functions)}, load_registry()
        )))

    def test_monitoring_control_plane_has_no_app_league_dependency(self) -> None:
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        for path in (
            "fantasy-management/automation/runner-config.json",
            "fantasy-management/automation/jobs/entity-observation.json",
        ):
            source = (REPO_ROOT / path).read_text(encoding="utf-8")
            self.assertNotIn("legacy:League", scan_text(path, source, names, functions))
            injected = source.replace("fantasy-management/generated/operations/managed-roster-signals.json",
                                      "public/data/League.json")
            self.assertIn("legacy:League", scan_text(path, injected, names, functions))
            self.assertTrue(any("legacy:League" in p for p in compare(
                {path: scan_text(path, injected, names, functions)}, load_registry()
            )))
        self.assertEqual([], compare_transitional_reads(load_registry()))

    def test_kicker_streaming_has_no_app_league_dependency(self) -> None:
        path = "fantasy-management/automation/kicker-streaming-input-materialization.json"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        builder = (REPO_ROOT / "fantasy-management/_ai/scripts/build_kicker_streaming_inputs.py").read_text(encoding="utf-8")
        self.assertNotIn('"league": "public/data/League.json"', source)
        self.assertNotIn('sources["league"]', builder)
        self.assertIn("enrich_from_members", builder)
        self.assertIn("resolve_lifecycle_state", builder)
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:League", scan_text(path, source, names, functions))
        injected = source.replace('"sources": {', '"sources": {"league": "public/data/League.json",')
        self.assertIn("legacy:League", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:League" in item for item in compare(
            {path: scan_text(path, injected, names, functions)}, load_registry()
        )))

    def test_fa_board_has_no_app_league_dependency(self) -> None:
        path = "fantasy-management/automation/fa-board-materialization.json"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        builder = (REPO_ROOT / "fantasy-management/_ai/scripts/build_fa_board_readmodel.py").read_text(encoding="utf-8")
        self.assertNotIn('"league_enrichment"', source)
        self.assertNotIn('"league_enrichment"', builder)
        self.assertIn("enrich_from_members", builder)
        self.assertIn("RosterPositions", builder)
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:League", scan_text(path, source, names, functions))
        injected = source.replace('"sources": {', '"sources": {"league_enrichment": "public/data/League.json",')
        self.assertIn("legacy:League", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:League" in item for item in compare(
            {path: scan_text(path, injected, names, functions)}, load_registry()
        )))

    def test_player_signals_display_has_no_app_league_input(self) -> None:
        """#1263 C8c: canonical members own Player Signals team labels."""
        path = "fantasy-management/automation/player-signal-materialization.json"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        builder = (REPO_ROOT / "fantasy-management/_ai/scripts/build_player_signal_dataset.py").read_text(encoding="utf-8")
        self.assertNotIn('"league_display"', source)
        self.assertNotIn('"league_display"', builder)
        self.assertIn("enrich_from_members", builder)
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:League", scan_text(path, source, names, functions))
        injected = source.replace('"sources": {', '"sources": {"league_display": "public/data/League.json",')
        self.assertIn("legacy:League", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:League" in item for item in compare(
            {path: scan_text(path, injected, names, functions)}, load_registry())))

    def test_managed_roster_display_has_no_app_league_input(self) -> None:
        """#1263 C8b: canonical members own Operations display."""
        path = "fantasy-management/automation/input-materialization.json"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        builder = (REPO_ROOT / "fantasy-management/_ai/scripts/build_fantasy_operations_inputs.py").read_text(encoding="utf-8")
        self.assertNotIn('"league_display"', source)
        self.assertNotIn('"league_display"', builder)
        self.assertIn("enrich_from_members", builder)
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:League", scan_text(path, source, names, functions))
        self.assertIn("legacy:League", scan_text(path, source + '\n"public/data/League.json"', names, functions))

    def test_request_league_has_no_published_schedule_input(self) -> None:
        """#1263 G2: the canonical lifecycle/windows own game-time facts, not Schedule.json."""
        path = "public/requests/RequestLeague.ps1"
        source = (REPO_ROOT / path).read_text(encoding="utf-8-sig")
        self.assertIn("Get-LeagueLifecycle", source)
        self.assertIn("Get-LeagueDecisionWindows", source)
        self.assertNotIn("$ScheduleFile", source)
        self.assertNotIn("Schedule.json", source)
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:Schedule", scan_text(path, source, names, functions))
        injected = source + "\n$ScheduleFile = $config.ScheduleFile\n"
        self.assertIn("legacy:Schedule", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:Schedule" in item and ("unclassified consumer" in item or "unclassified read" in item)
                            for item in compare({path: scan_text(path, injected, names, functions)}, load_registry())))

    def test_request_league_drafts_come_from_shared_derived_only(self) -> None:
        """#1263 C7: no second App-consumer input for team DraftPicks."""
        path = "public/requests/RequestLeague.ps1"
        reader_path = "public/requests/utils/league/TeamDraftPickUtils.psm1"
        source = (REPO_ROOT / path).read_text(encoding="utf-8-sig")
        reader = (REPO_ROOT / reader_path).read_text(encoding="utf-8-sig")
        self.assertIn("Get-LeagueDraftsProduct", source)
        self.assertNotIn("Get-LeagueDraftsLocal", source)
        self.assertNotIn("Get-LeagueDraftsLocal", reader)
        self.assertIn("Get-DataDerivedRoot", reader)
        self.assertIn("ContractVersion", reader)
        self.assertNotIn("$config.DraftsFile", reader)
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:Drafts", scan_text(path, source, names, functions))
        self.assertNotIn("legacy:Drafts", scan_text(reader_path, reader, names, functions))
        injected = source + "\n$legacy = $config.DraftsFile\n"
        self.assertIn("legacy:Drafts", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:Drafts" in item and ("unclassified consumer" in item or "unclassified read" in item)
                            for item in compare(
            {path: scan_text(path, injected, names, functions)}, load_registry()
        )))

    def test_external_signals_config_rejects_restored_app_league_input(self) -> None:
        path = "fantasy-management/automation/external-signal-materialization.json"
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        names, functions = read_model_names(REPO_ROOT), sleeper_functions(REPO_ROOT)
        self.assertNotIn("legacy:League", scan_text(path, source, names, functions))
        injected = source.replace('"sources": {', '"sources": {"league_display": "public/data/League.json",')
        self.assertIn("legacy:League", scan_text(path, injected, names, functions))
        self.assertTrue(any("legacy:League" in item for item in compare(
            {path: scan_text(path, injected, names, functions)}, load_registry()
        )))

    def test_every_registered_file_exists(self) -> None:
        missing = [p for p in load_registry()["consumers"] if not (REPO_ROOT / p).is_file()]
        self.assertEqual([], missing)

    def test_app_generators_make_no_direct_provider_requests(self) -> None:
        """#347: provider acquisition lives in the source layer; public/requests only holds the generic HTTP helper."""
        offenders = []
        for path, entry in load_registry()["consumers"].items():
            if not path.startswith("public/requests/"):
                continue
            for token, category in (entry.get("reads") or {}).items():
                if token == "network" and category != "http-helper":
                    offenders.append(f"{path}: {token} is {category}")
                if token.startswith("provider:") and category not in ("display-link-construction", "provider-client"):
                    offenders.append(f"{path}: {token} is {category}")
        self.assertEqual([], offenders, "\n".join(offenders))

    def test_unclassified_reads_are_detected(self) -> None:
        names = read_model_names(REPO_ROOT)
        fns = sleeper_functions(REPO_ROOT)
        registry = load_registry()
        self.assertTrue(names and fns)
        injected = {
            "tools/new_consumer.py": scan_text(
                "tools/new_consumer.py",
                f'import requests\nURL = "https://api.sleeper.app/v1/league"\nPATH = "public/data/{names[0]}.json"\n',
                names, fns,
            ),
            "public/requests/utils/league/NewUtils.psm1": scan_text(
                "public/requests/utils/league/NewUtils.psm1",
                f"$x = Get-{fns[0].split('Get-')[1]} -leagueID 1\n$y = Get-Content public/data/{names[0]}.json\n",
                names, fns,
            ),
        }
        problems = compare(injected, registry)
        for path, tokens in injected.items():
            self.assertTrue(tokens, path)
            self.assertTrue(any(f"unclassified consumer {path}" in p for p in problems), problems)

    def test_new_read_in_classified_file_is_detected(self) -> None:
        names = read_model_names(REPO_ROOT)
        fns = sleeper_functions(REPO_ROOT)
        registry = load_registry()
        found = scan_repository(REPO_ROOT)
        path = "public/requests/RequestTeams.ps1"
        self.assertIn(path, found)
        extra = scan_text(path, "Get-Content https://api.sleeper.app/v1/players/nfl", names, fns)
        found[path] = found[path] | extra
        problems = compare(found, registry)
        self.assertTrue(any("unclassified read provider:sleeper" in p for p in problems), problems)

    def test_helper_reads_are_declared_and_consistent(self) -> None:
        """L7: a reader helper hides the read of a read model from its callers, so it is declared once.

        Each declared helper must be defined exactly once, wrap a known read model, and
        its defining file must itself carry the matching classified read.
        """
        registry = load_registry()
        helpers = registry.get("helperReads") or {}
        names = set(read_model_names(REPO_ROOT))
        self.assertNotIn("Get-LeagueDraftsLocal", helpers)
        problems = []
        for helper, model in helpers.items():
            if model not in names:
                problems.append(f"{helper}: unknown read model {model}")
            definitions = [
                f.relative_to(REPO_ROOT).as_posix()
                for pattern in ("public/requests/**/*.ps1", "public/requests/**/*.psm1")
                for f in REPO_ROOT.glob(pattern)
                if re.search(rf"^function {re.escape(helper)}\b", f.read_text(encoding="utf-8", errors="ignore"), re.M)
            ]
            if len(definitions) != 1:
                problems.append(f"{helper}: expected one definition, found {definitions}")
                continue
            reads = (registry["consumers"].get(definitions[0]) or {}).get("reads") or {}
            if f"legacy:{model}" not in reads:
                problems.append(f"{helper}: defining file {definitions[0]} lacks legacy:{model}")
        self.assertEqual([], problems, "\n".join(problems))

    def test_helper_call_is_detected_as_read(self) -> None:
        names = read_model_names(REPO_ROOT)
        fns = sleeper_functions(REPO_ROOT)
        # Synthetic registration verifies the guard even when all real wrapped
        # App Drafts.json reader helpers have been retired by #1263 C7.
        helpers = {"Get-TestAppReader": "Drafts"}
        helper, model = next(iter(helpers.items()))
        call = scan_text("public/requests/New.ps1", f"$x = {helper}\n", names, fns, helpers)
        definition = scan_text("public/requests/New.ps1", f"function {helper} {{ }}\n", names, fns, helpers)
        self.assertEqual({f"legacy:{model}"}, call)
        self.assertEqual(set(), definition)

    # --- G6 (#1453) ---------------------------------------------------------------------------------
    def test_g6_past_seasons_reads_and_dynamic_paths_are_detected(self) -> None:
        names = read_model_names(REPO_ROOT)
        fns = sleeper_functions(REPO_ROOT)
        cases = {
            "tools/new_a.py": 'x = load(DATA / "past_seasons" / "Drafts" / f"Drafts_{season}.json")\n',
            "tools/new_b.py": 'root = Path("public/data/past_seasons")\nfor f in root.glob("*_*.json"): pass\n',
            "tools/new_c.py": 'p = repo / "public" / "data" / "past_seasons" / folder / name\n',
            "public/requests/New.ps1": '$f = Join-Path $config.DraftsArchiveDir "Drafts_$season.json"\n',
            "public/requests/New.psm1": '$d = Join-Path $Config.PastSeasonsDir "Matchups"\n',
            "fantasy-management/automation/x/new.json": '{"input": "public/data/past_seasons/Drafts/Drafts_2025.json"}',
        }
        for path, text in cases.items():
            self.assertIn(PAST_SEASONS_TOKEN, scan_text(path, text, names, fns), path)
        # Negative control: a file without any archive reference yields no archive token.
        self.assertNotIn(PAST_SEASONS_TOKEN, scan_text("tools/ok.py", 'x = load(DATA / "League.json")\n', names, fns))

    def test_g6_unclassified_past_seasons_read_fails_the_registry_check(self) -> None:
        registry = load_registry()
        found = {"tools/new_a.py": {PAST_SEASONS_TOKEN}}
        problems = compare(found, registry)
        self.assertTrue(any("unclassified consumer tools/new_a.py" in p for p in problems), problems)
        path = "tools/league_history_app_publish.py"
        entry = registry["consumers"][path]
        stale = {**registry, "consumers": {**registry["consumers"], path: {
            **entry, "reads": {k: v for k, v in entry["reads"].items() if k != PAST_SEASONS_TOKEN}}}}
        problems = compare(scan_repository(REPO_ROOT), stale)
        self.assertTrue(any(f"unclassified read {PAST_SEASONS_TOKEN} in {path}" in p for p in problems), problems)

    def test_g6_angular_guards_hold_on_the_repository(self) -> None:
        problems = check_angular_guards(angular_sources(REPO_ROOT), load_guard_registry())
        self.assertEqual([], problems, "\n".join(problems))

    def test_g6_angular_guard_negative_fixtures_fail_closed(self) -> None:
        guard = load_guard_registry()
        base = {p: "" for p in (set(guard["httpLoaderFiles"]) | set(guard["archivePathFiles"])
                                | {r["path"] for r in guard["capLimitInputFiles"]})}
        self.assertEqual([], check_angular_guards(base, guard))
        fixtures = {
            "HTTP loader": 'constructor(private http: HttpClient) {} load() { return this.http.get("data/X.json"); }',
            "archive path": "const url = `data/past_seasons/Drafts/Drafts_${season}.json`;",
            "data URL": "const url = 'data/Extra.json';",
            "cap limit": "const n = Math.min(league.SalaryRelevantTeamSize, roster.length);",
            "model ID": "const MODEL = 'roster-cap-v1';",
        }
        for label, code in fixtures.items():
            problems = check_angular_guards({**base, "src/app/features/new/new.ts": code}, guard)
            self.assertTrue(problems, label)
        # Comments and documentation strings do not trip the guard.
        commented = "// loads past_seasons via HttpClient, win-prob-v1\n/* SalaryRelevantTeamSize */\nconst a = 1;"
        self.assertEqual([], check_angular_guards({**base, "src/app/features/new/new.ts": strip_ts_comments(commented)}, guard))
        # A stale exception entry is reported.
        self.assertTrue(any("stale angularDomainGuard entry" in p for p in check_angular_guards({}, guard)))

    def test_g6_rivalry_comes_from_the_product(self) -> None:
        sources = angular_sources(REPO_ROOT)
        self.assertEqual([], check_rivalry_comes_from_product(sources))
        # Red fixtures: the pre-#1455 counting and the heuristic return in a view or util.
        for code in (
            "export function isConsolationMatchup(season: unknown) { return false; }",
            "const record = buildHeadToHead(a, b, seasons, options);",
            "const done = isPlayoffsComplete(season, current, status);",
        ):
            self.assertTrue(check_rivalry_comes_from_product({**sources, "src/app/shared/utils/new.util.ts": code}), code)
        regressed = dict(sources)
        regressed[RIVALRY_VIEW_FILES[0]] = "export class X { load() { return this.dataService.getPastMatchupsRaw('p'); } }"
        self.assertTrue(check_rivalry_comes_from_product(regressed))

    def test_g6_overview_cap_comes_from_central_outlook(self) -> None:
        guard = load_guard_registry()
        sources = angular_sources(REPO_ROOT)
        self.assertEqual([], check_overview_cap_reads_central_outlook(sources, guard["overviewCapFiles"]))
        # Red fixture: the pre-#1456 local recomputation in the overview (top-N salary sum).
        regressed = dict(sources)
        regressed["src/app/features/overview/overview.ts"] = (
            "const playerCount = Math.min(league.SalaryRelevantTeamSize, t.Roster.length);\n"
            "const topPlayers = sortedSalary.slice(0, playerCount);\n"
            "const total = topPlayers.reduce((sum, p) => sum + p.Salary, 0);\n"
        )
        self.assertTrue(check_overview_cap_reads_central_outlook(regressed, guard["overviewCapFiles"]))
        regressed = dict(sources)
        regressed["src/app/shared/utils/overview-cap.util.ts"] = "export const total = 0;"
        self.assertTrue(check_overview_cap_reads_central_outlook(regressed, guard["overviewCapFiles"]))

    def test_g6_salary_simulation_is_a_protected_analysis_snapshot(self) -> None:
        registry = load_registry()
        policy = (yaml.safe_load(MATRIX.read_text(encoding="utf-8")))["analysisSnapshotPolicy"]
        problems = check_analysis_snapshot_policy(registry, policy, REPO_ROOT)
        self.assertEqual([], problems, "\n".join(problems))
        # Negative: a new analysis-snapshot-input without policy, and a productive reference, are reported.
        extra = {**registry, "consumers": {**registry["consumers"],
                 "fantasy-management/new_analysis.py": {"reads": {"legacy:League": "analysis-snapshot-input"}}}}
        self.assertTrue(any("without snapshot policy" in p for p in check_analysis_snapshot_policy(extra, policy, REPO_ROOT)))
        self.assertTrue(any("stale snapshot policy" in p for p in check_analysis_snapshot_policy(
            {**registry, "consumers": {}}, policy, REPO_ROOT)))
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sim = "fantasy-management/league-economy/salary/simulation/salary_simulation.py"
            out = "fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation.json"
            for rel, text in ((sim, ""), (out, "{}"), ("tools/rogue.py", "import salary_simulation\n")):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
            only = {"consumers": {sim: {"reads": {"legacy:League": "analysis-snapshot-input"}}}}
            found = check_analysis_snapshot_policy(only, policy, root)
            self.assertTrue(any("productive use of analysis snapshot" in p for p in found), found)

    def test_unknown_category_is_detected(self) -> None:
        registry = load_registry()
        path, entry = next(iter(registry["consumers"].items()))
        token = next(iter(entry["reads"]))
        broken = {**registry, "consumers": {**registry["consumers"], path: {**entry, "reads": {**entry["reads"], token: "no-such-category"}}}}
        problems = compare(scan_repository(REPO_ROOT), broken)
        self.assertTrue(any("unknown category" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
