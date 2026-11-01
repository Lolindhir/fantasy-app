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



# #1263 C2: only pre-existing, explicitly classified transitional reads are
# tolerated while their source-to-derived cutovers remain pending. A registry
# category does not itself authorize a consumer-to-consumer dependency.
TRANSITIONAL_CATEGORIES = frozenset({
    "app-read-model-chain", "intentional-overlay", "legacy-read-model-pending",
})
TRANSITIONAL_BASELINE = frozenset({
    ("fantasy-management/_ai/scripts/canonical_league_ownership.py", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/external-signal-materialization.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/fa-board-materialization.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/input-materialization.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/jobs/entity-observation.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/jobs/weekly-league-review.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/kicker-streaming-input-materialization.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/managed-roster-overview.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/player-signal-materialization.json", "legacy:League", "intentional-overlay"),
    ("fantasy-management/automation/runner-config.json", "legacy:League", "intentional-overlay"),
    ("public/requests/RequestLeague.ps1", "legacy:Drafts", "app-read-model-chain"),
    ("public/requests/RequestLeague.ps1", "legacy:Schedule", "app-read-model-chain"),
    ("public/requests/utils/league/TeamDraftPickUtils.psm1", "legacy:Drafts", "app-read-model-chain"),
    ("tools/derived_data.py", "legacy:Players", "legacy-read-model-pending"),
})


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

class ConsumerReadClassificationTest(unittest.TestCase):

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
        path, token, _ = next(iter(TRANSITIONAL_BASELINE))
        edited_entry = {**registry["consumers"][path], "reads": {
            **registry["consumers"][path]["reads"], token: "validation-shadow",
        }}
        edited = {**registry, "consumers": {**registry["consumers"], path: edited_entry}}
        self.assertTrue(any("obsolete transitional baseline" in s for s in compare_transitional_reads(edited)))

    def test_every_consumer_read_is_classified(self) -> None:
        problems = compare(scan_repository(REPO_ROOT), load_registry())
        self.assertEqual([], problems, "\n".join(problems))

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
        self.assertTrue(helpers)
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
        helpers = load_registry()["helperReads"]
        helper, model = next(iter(helpers.items()))
        call = scan_text("public/requests/New.ps1", f"$x = {helper}\n", names, fns, helpers)
        definition = scan_text("public/requests/New.ps1", f"function {helper} {{ }}\n", names, fns, helpers)
        self.assertEqual({f"legacy:{model}"}, call)
        self.assertEqual(set(), definition)

    def test_unknown_category_is_detected(self) -> None:
        registry = load_registry()
        path, entry = next(iter(registry["consumers"].items()))
        token = next(iter(entry["reads"]))
        broken = {**registry, "consumers": {**registry["consumers"], path: {**entry, "reads": {**entry["reads"], token: "no-such-category"}}}}
        problems = compare(scan_repository(REPO_ROOT), broken)
        self.assertTrue(any("unknown category" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
