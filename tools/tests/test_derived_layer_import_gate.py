"""Architecture gate (Issue #1263 CP5): Shared-Derived code must not reach Consumer code.

Statically scans every Python module of the Shared-Derived layer (tools/derived_data_lib/**, the
*_materialize.py entry points and derived_data.py) including function-local and literal dynamic
imports, and follows top-level tools modules transitively. A forbidden consumer module anywhere in
that closure is a layer violation. Limits: non-literal dynamic imports are flagged, PowerShell/Node/
Angular layers are not covered here (see test_consumer_read_classification for file reads).
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
TOP = {p.stem for p in TOOLS.glob("*.py")}

# Consumer generators / refreshers: delivery layer, never an input of Shared Derived code.
CONSUMER_EXPLICIT = {"schedule_archive", "player_week_fantasy_refresh", "league_live_derived_refresh"}


def is_consumer(module: str) -> bool:
    return module.endswith("_app_publish") or module in CONSUMER_EXPLICIT


def derived_roots(tools: Path = TOOLS) -> list[Path]:
    roots = sorted((tools / "derived_data_lib").rglob("*.py"))
    roots += sorted(tools.glob("*_materialize.py"))
    roots.append(tools / "derived_data.py")
    return roots


def imports_of(source: str, top: set[str]) -> tuple[set[str], list[int]]:
    """Return (imported top-level tools modules, line numbers of non-literal dynamic imports)."""
    found: set[str] = set()
    dynamic: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names if a.name.split(".")[0] in top)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            head = node.module.split(".")[0]
            if head in top:
                found.add(head)
            if head == "derived_data_lib":
                continue
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in {"import_module", "__import__"}:
                arg = node.args[0] if node.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    head = arg.value.split(".")[0]
                    if head in top:
                        found.add(head)
                else:
                    dynamic.append(node.lineno)
    return found, dynamic


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

    def test_known_neutral_helpers_are_not_consumers(self):
        for module in ("data_roots", "league_metadata", "players_population", "matchup_projection", "nfl_schedule_games"):
            self.assertFalse(is_consumer(module))


if __name__ == "__main__":
    unittest.main()
