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
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
TOP = {p.stem for p in TOOLS.glob("*.py")}

# Consumer generators / refreshers: delivery layer, never an input of Shared Derived code.
CONSUMER_EXPLICIT = {"schedule_archive", "player_week_fantasy_refresh", "league_live_derived_refresh"}


# Documented consumer-to-consumer edges (none may be added silently; a stale entry fails the test).
# player_week_fantasy_refresh is the orchestrator that renders the PlayerWeekFantasy App file after its materialization.
CONSUMER_EDGE_ALLOWLIST = {("player_week_fantasy_refresh", "player_week_fantasy_app_publish")}


def is_consumer(module: str) -> bool:
    return module.endswith("_app_publish") or module in CONSUMER_EXPLICIT


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


def derived_closure_files(tools: Path = TOOLS) -> list[Path]:
    """Roots plus every non-consumer top-level module they reach transitively."""
    top = {p.stem for p in tools.glob("*.py")}
    files = {p: None for p in derived_roots(tools)}
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


def consumer_edges(tools: Path = TOOLS) -> set[tuple[str, str]]:
    """Direct imports from one consumer generator into another."""
    top = {p.stem for p in tools.glob("*.py")}
    edges = set()
    for path in tools.glob("*.py"):
        if is_consumer(path.stem):
            for dep in imports_of(path.read_text(encoding="utf-8"), top)[0]:
                if is_consumer(dep) and dep != path.stem:
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
        for module in ("data_roots", "league_metadata", "players_population", "nfl_schedule_games", "app_delivery"):
            self.assertFalse(is_consumer(module))


if __name__ == "__main__":
    unittest.main()
