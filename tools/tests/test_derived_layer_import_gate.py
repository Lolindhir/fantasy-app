"""Architecture gate (Issue #1263 CP5): Shared-Derived code must not reach Consumer code.

Statically scans every Python module of the Shared-Derived layer (tools/derived_data_lib/**, the
*_materialize.py entry points and derived_data.py) including function-local and literal dynamic
imports, and follows top-level tools modules transitively. A forbidden consumer module anywhere in
that closure is a layer violation. Limits: non-literal dynamic imports are flagged, PowerShell/Node/
Angular layers are not covered here (see test_consumer_read_classification for file reads).

Hardening (architecture cleanup before #1618): the closure of non-consumer modules reached from the roots is also
scanned for public/data literals, and consumer generators must not import each other (shared helpers belong in the
neutral tools/app_delivery.py). Remaining limits: consumer detection is name based (*_app_publish plus the explicit
list), paths built from parts are not seen, Python only; there is no whole-repository graph. This is the logical layer
check; the physical Canonical cutover is Issue #1618 and not part of it.

Second hardening (final review): the closure is additionally scanned with the same public/data path rule as the K1 read
classification (PY_DATA_DIR_RE: literals, DATA_DIR/PUBLIC_DATA names and paths built from parts such as
`root / "public" / "data"`). The only known hit is the reviewed validation-shadow path in transaction_canonical_shadow.py
(allowlist with stale check). tools/app_delivery.py is an explicit consumer helper: Derived code must not import it, and
consumer generators may. Third hardening: the orchestrators league_live_derived_refresh and
player_week_fantasy_refresh write Derived products, so their own code and non-consumer import closure are scanned with
the same public/data rule (consumer generators they call on purpose, see the allowlist below, are not followed). A
dedicated producer-orchestrator category is a separate follow-up.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
TOP = {p.stem for p in TOOLS.glob("*.py")}

# Consumer generators / refreshers: delivery layer, never an input of Shared Derived code.
CONSUMER_EXPLICIT = {"schedule_archive", "player_week_fantasy_refresh", "league_live_derived_refresh"}
# Shared helper of the consumer generators (writer, load helpers): consumer layer, forbidden for Derived code.
# Consumer generators importing it is the intended direction and is not a consumer-to-consumer edge.
CONSUMER_HELPERS = {"app_delivery"}

# Same rule as PY_DATA_DIR_RE of test_consumer_read_classification.py (checked for equality below).
PY_DATA_DIR_RE = re.compile(r"public[\"']?\s*[,/]\s*[\"']?data|DATA_DIR|PUBLIC_DATA|public/data")
# Reviewed exceptions: pure validation-shadow read classified as validation-shadow in the K1 registry.
PUBLIC_DATA_PATH_ALLOWLIST = {"transaction_canonical_shadow.py"}


# Documented consumer-to-consumer edges (none may be added silently; a stale entry fails the test).
# player_week_fantasy_refresh is the orchestrator that renders the PlayerWeekFantasy App file after its materialization.
CONSUMER_EDGE_ALLOWLIST = {("player_week_fantasy_refresh", "player_week_fantasy_app_publish")}


def is_consumer(module: str) -> bool:
    return module.endswith("_app_publish") or module in CONSUMER_EXPLICIT or module in CONSUMER_HELPERS


def derived_roots(tools: Path = TOOLS) -> list[Path]:
    roots = sorted((tools / "derived_data_lib").rglob("*.py"))
    roots += sorted(tools.glob("*_materialize.py"))
    roots.append(tools / "derived_data.py")
    return roots


def _strip_tools(name: str) -> str:
    parts = name.split(".")
    return ".".join(parts[1:]) if parts[0] == "tools" and len(parts) > 1 else name


def imports_of(source: str, top: set[str]) -> tuple[set[str], list[int]]:
    """Return (imported top-level tools modules, line numbers of non-literal dynamic imports).

    Also counts the literal script names of subprocess/runpy calls (x.py) and the `tools.` package prefix.
    """
    found: set[str] = set()
    dynamic: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for a in node.names:
                head = _strip_tools(a.name).split(".")[0]
                if head in top:
                    found.add(head)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            head = _strip_tools(node.module).split(".")[0]
            if head in top:
                found.add(head)
            if node.module == "tools":
                found.update(a.name for a in node.names if a.name in top)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(".py"):
            stem = Path(node.value.replace("\\", "/")).stem
            if stem in top and is_consumer(stem):
                found.add(stem)
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in {"import_module", "__import__"}:
                arg = node.args[0] if node.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    head = _strip_tools(arg.value).split(".")[0]
                    if head in top:
                        found.add(head)
                else:
                    dynamic.append(node.lineno)
    return found, dynamic


def public_data_literals(tools: Path = TOOLS) -> list[str]:
    """Runtime string literals naming public/data in the Shared-Derived roots (docstrings excluded)."""
    hits: list[str] = []
    for path in derived_roots(tools):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    docstrings.add(id(body[0].value))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings and "public/data" in node.value.replace("\\", "/")):
                hits.append(f"{path.relative_to(tools).as_posix()}:{node.lineno}")
    return sorted(hits)


def _literals_in(path: Path, tools: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    return [
        f"{path.relative_to(tools).as_posix()}:{node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings and "public/data" in node.value.replace("\\", "/")
    ]


def derived_closure_files(tools: Path = TOOLS, roots: list[Path] | None = None) -> list[Path]:
    """Roots plus every non-consumer top-level module they reach transitively."""
    top = {p.stem for p in tools.glob("*.py")}
    files = {p: None for p in (derived_roots(tools) if roots is None else roots)}
    stack = []
    for path in list(files):
        stack += sorted(imports_of(path.read_text(encoding="utf-8"), top)[0])
    seen: set[str] = set()
    while stack:
        module = stack.pop()
        if module in seen or is_consumer(module):
            continue
        seen.add(module)
        path = tools / f"{module}.py"
        files[path] = None
        stack += sorted(imports_of(path.read_text(encoding="utf-8"), top)[0])
    return sorted(files)


def public_data_literals_transitive(tools: Path = TOOLS) -> list[str]:
    hits: list[str] = []
    for path in derived_closure_files(tools):
        hits += _literals_in(path, tools)
    return sorted(set(hits))


def _flatten_div(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _flatten_div(node.left) + _flatten_div(node.right)
    return [node]


def _adjacent_public_data(parts: list[ast.AST]) -> bool:
    values = [p.value if isinstance(p, ast.Constant) and isinstance(p.value, str) else None for p in parts]
    return any(a == "public" and b == "data" for a, b in zip(values, values[1:]))


def public_data_path_hits(path: Path, tools: Path) -> list[str]:
    """Executable public/data path uses by the K1 rule: literals, DATA_DIR-like names, paths built from parts."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    rel = path.relative_to(tools).as_posix()
    hits = []
    for node in ast.walk(tree):
        text = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            text = node.value.replace("\\", "/")
        elif isinstance(node, ast.Name):
            text = node.id
        elif isinstance(node, ast.Attribute):
            text = node.attr
        if text is not None and PY_DATA_DIR_RE.search(text):
            hits.append(f"{rel}:{node.lineno}")
        elif isinstance(node, ast.BinOp) and _adjacent_public_data(_flatten_div(node)):
            hits.append(f"{rel}:{node.lineno}")
        elif isinstance(node, ast.Call) and _adjacent_public_data(list(node.args)):
            hits.append(f"{rel}:{node.lineno}")
    return sorted(set(hits))


def public_data_path_hits_transitive(tools: Path = TOOLS) -> list[str]:
    hits: list[str] = []
    for path in derived_closure_files(tools):
        hits += public_data_path_hits(path, tools)
    return sorted(set(hits))


ORCHESTRATORS = ("league_live_derived_refresh", "player_week_fantasy_refresh")
# Reviewed public/data path uses inside the orchestrator closure: the same reviewed shadow path as for Derived.
ORCHESTRATOR_PATH_ALLOWLIST: set[str] = set(PUBLIC_DATA_PATH_ALLOWLIST)


def orchestrator_roots(tools: Path = TOOLS) -> list[Path]:
    return [tools / f"{name}.py" for name in ORCHESTRATORS if (tools / f"{name}.py").exists()]


def public_data_path_hits_orchestrators(tools: Path = TOOLS) -> list[str]:
    """Orchestrators write Derived products; their own code and non-consumer closure must not read public/data.
    Consumer generators they call on purpose (CONSUMER_EDGE_ALLOWLIST) are not followed."""
    hits: list[str] = []
    for path in derived_closure_files(tools, orchestrator_roots(tools)):
        hits += public_data_path_hits(path, tools)
    return sorted(set(hits))


def consumer_edges(tools: Path = TOOLS) -> set[tuple[str, str]]:
    """Direct imports from one consumer generator into another."""
    top = {p.stem for p in tools.glob("*.py")}
    edges = set()
    for path in tools.glob("*.py"):
        if is_consumer(path.stem):
            for dep in imports_of(path.read_text(encoding="utf-8"), top)[0]:
                if is_consumer(dep) and dep != path.stem and dep not in CONSUMER_HELPERS:
                    edges.add((path.stem, dep))
    return edges


def violations(tools: Path = TOOLS) -> tuple[list[str], list[str]]:
    top = {p.stem for p in tools.glob("*.py")}
    closure_cache: dict[str, set[str]] = {}

    def direct(module: str) -> set[str]:
        if module not in closure_cache:
            found, _ = imports_of((tools / f"{module}.py").read_text(encoding="utf-8"), top)
            closure_cache[module] = found
        return closure_cache[module]

    bad: list[str] = []
    dyn: list[str] = []
    for path in derived_roots(tools):
        found, dynamic = imports_of(path.read_text(encoding="utf-8"), top)
        rel = path.relative_to(tools).as_posix()
        dyn += [f"{rel}:{line}" for line in dynamic]
        seen: set[str] = set()
        stack = [(m, [rel, m]) for m in sorted(found)]
        while stack:
            module, chain = stack.pop()
            if module in seen:
                continue
            seen.add(module)
            if is_consumer(module):
                bad.append(" -> ".join(chain))
                continue
            for nxt in sorted(direct(module)):
                stack.append((nxt, chain + [nxt]))
    return sorted(set(bad)), sorted(set(dyn))


class DerivedLayerImportGateTests(unittest.TestCase):
    def test_derived_layer_never_reaches_consumer_modules(self):
        bad, _ = violations()
        self.assertEqual(bad, [], "Shared-Derived code must not import consumer generators: " + "; ".join(bad))

    def test_no_non_literal_dynamic_imports_in_derived_layer(self):
        _, dynamic = violations()
        self.assertEqual(dynamic, [])

    def test_gate_is_red_for_direct_transitive_lazy_and_dynamic_violations(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "derived_data_lib").mkdir()
            (tools / "x_app_publish.py").write_text("")
            (tools / "helper.py").write_text("def f():\n    import x_app_publish\n")
            (tools / "derived_data.py").write_text("")
            (tools / "a_materialize.py").write_text("import helper\n")
            (tools / "derived_data_lib" / "lazy.py").write_text("def g():\n    from schedule_archive import build\n")
            (tools / "schedule_archive.py").write_text("")
            (tools / "derived_data_lib" / "dyn.py").write_text("import importlib\nimportlib.import_module(name)\n")
            (tools / "derived_data_lib" / "lit.py").write_text("import importlib\nimportlib.import_module('x_app_publish')\n")
            bad, dynamic = violations(tools)
        self.assertIn("a_materialize.py -> helper -> x_app_publish", bad)
        self.assertIn("derived_data_lib/lazy.py -> schedule_archive", bad)
        self.assertIn("derived_data_lib/lit.py -> x_app_publish", bad)
        self.assertEqual(dynamic, ["derived_data_lib/dyn.py:2"])

    def test_derived_layer_has_no_public_data_path_literals(self):
        self.assertEqual(public_data_literals(), [])

    def test_gate_is_red_for_tools_prefix_subprocess_and_public_data_literals(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "derived_data_lib").mkdir()
            (tools / "derived_data.py").write_text("")
            (tools / "x_app_publish.py").write_text("")
            (tools / "derived_data_lib" / "pre.py").write_text("from tools.x_app_publish import f\n")
            (tools / "derived_data_lib" / "sub.py").write_text("import subprocess\nsubprocess.run(['python', 'tools/x_app_publish.py'])\n")
            (tools / "derived_data_lib" / "doc.py").write_text('"""reads public/data/X.json"""\nPATH = "public/data/Players.json"\n')
            bad, _ = violations(tools)
            literals = public_data_literals(tools)
        self.assertIn("derived_data_lib/pre.py -> x_app_publish", bad)
        self.assertIn("derived_data_lib/sub.py -> x_app_publish", bad)
        self.assertEqual(literals, ["derived_data_lib/doc.py:2"])

    def test_derived_closure_has_no_public_data_path_literals(self):
        self.assertEqual(public_data_literals_transitive(), [])

    def test_consumer_generators_do_not_import_each_other(self):
        self.assertEqual(sorted(consumer_edges() - CONSUMER_EDGE_ALLOWLIST), [])
        self.assertEqual(sorted(CONSUMER_EDGE_ALLOWLIST - consumer_edges()), [], "stale allowlist entry")

    def test_gate_is_red_for_transitive_literals_and_consumer_edges(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "derived_data_lib").mkdir()
            (tools / "derived_data.py").write_text("")
            (tools / "helper.py").write_text("import inner\n")
            (tools / "inner.py").write_text('P = "public/data/Players.json"\n')
            (tools / "a_materialize.py").write_text("import helper\n")
            (tools / "a_app_publish.py").write_text("")
            (tools / "b_app_publish.py").write_text("from a_app_publish import Writer\n")
            (tools / "c_app_publish.py").write_text("import subprocess\nsubprocess.run(['python', 'a_app_publish.py'])\n")
            literals = public_data_literals_transitive(tools)
            edges = consumer_edges(tools)
        self.assertEqual(literals, ["inner.py:1"])
        self.assertEqual(edges, {("b_app_publish", "a_app_publish"), ("c_app_publish", "a_app_publish")})

    def test_known_neutral_helpers_are_not_consumers(self):
        for module in ("data_roots", "league_metadata", "players_population", "nfl_schedule_games"):
            self.assertFalse(is_consumer(module))

    def test_app_delivery_is_an_explicit_consumer_helper(self):
        self.assertTrue(is_consumer("app_delivery"))
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "derived_data_lib").mkdir()
            (tools / "derived_data.py").write_text("")
            (tools / "app_delivery.py").write_text("")
            (tools / "a_app_publish.py").write_text("from app_delivery import Writer\n")
            (tools / "derived_data_lib" / "bad.py").write_text("import app_delivery\n")
            bad, _ = violations(tools)
            edges = consumer_edges(tools)
        self.assertEqual(bad, ["derived_data_lib/bad.py -> app_delivery"])
        self.assertEqual(edges, set())

    def test_public_data_regex_matches_k1_rule(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import test_consumer_read_classification as k1

        self.assertEqual(PY_DATA_DIR_RE.pattern, k1.PY_DATA_DIR_RE.pattern)

    def test_derived_closure_has_no_unreviewed_public_data_paths(self):
        hits = public_data_path_hits_transitive()
        unreviewed = [h for h in hits if h.split(":")[0] not in PUBLIC_DATA_PATH_ALLOWLIST]
        self.assertEqual(unreviewed, [], "public/data path in the Derived closure: " + "; ".join(unreviewed))
        stale = PUBLIC_DATA_PATH_ALLOWLIST - {h.split(":")[0] for h in hits}
        self.assertEqual(sorted(stale), [], "stale allowlist entry")

    def test_orchestrators_do_not_read_public_data(self):
        hits = public_data_path_hits_orchestrators()
        unreviewed = [h for h in hits if h.split(":")[0] not in ORCHESTRATOR_PATH_ALLOWLIST]
        self.assertEqual(unreviewed, [], "public/data path in an orchestrator closure: " + "; ".join(unreviewed))
        stale = ORCHESTRATOR_PATH_ALLOWLIST - {h.split(":")[0] for h in hits}
        self.assertEqual(sorted(stale), [], "stale allowlist entry")
        self.assertEqual(len(orchestrator_roots()), len(ORCHESTRATORS), "orchestrator renamed or removed")

    def test_gate_is_red_for_orchestrator_public_data_paths_but_not_followed_consumers(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "league_live_derived_refresh.py").write_text("import lib, thing_app_publish\n")
            (tools / "lib.py").write_text('def f(root):\n    return root / "public" / "data"\n')
            (tools / "thing_app_publish.py").write_text('X = "public/data/A.json"\n')
            hits = public_data_path_hits_orchestrators(tools)
        self.assertEqual([h.split(":")[0] for h in hits], ["lib.py"])

    def test_gate_is_red_for_paths_built_from_parts_and_data_dir_names(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "derived_data_lib").mkdir()
            (tools / "derived_data.py").write_text("")
            (tools / "helper.py").write_text('def f(root):\n    return root / "public" / "data" / "X.json"\n')
            (tools / "joined.py").write_text('def f(root):\n    return root.joinpath("public", "data")\n')
            (tools / "named.py").write_text("from cfg import DATA_DIR\nX = DATA_DIR\n")
            (tools / "clean.py").write_text('"""public/data in a docstring"""\nX = 1\n')
            (tools / "a_materialize.py").write_text("import helper, joined, named, clean\n")
            hits = public_data_path_hits_transitive(tools)
        self.assertEqual(sorted(h.split(":")[0] for h in hits), ["helper.py", "joined.py", "named.py"])


if __name__ == "__main__":
    unittest.main()
