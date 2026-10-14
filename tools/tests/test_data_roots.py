"""#788 step 0: data root directory names are defined once per language and not spelled out elsewhere.

Python production code under tools/ takes the names from tools/data_roots.py, PowerShell production
code under public/requests/ from ConfigUtils.psm1. The scan only looks at path-like string literals
(the root name followed by a path separator or ending the literal); prose in comments, docstrings and
log messages is allowed. Workflow files, documentation and tests are out of scope by design.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import data_roots  # noqa: E402

CONFIG_UTILS = REPO_ROOT / "public/requests/utils/ConfigUtils.psm1"
PY_PATH_LITERAL = re.compile(r"(?<![\w-])(data-source|data-derived)(?=$|[/\\])")
PS_PATH_LITERAL = re.compile(r"(?<![\w-])(data-source|data-derived)(?=[\"'/\\])")


def python_production_files() -> list[Path]:
    return sorted(
        p for p in TOOLS.rglob("*.py")
        if "tests" not in p.relative_to(TOOLS).parts and p.name != "data_roots.py"
    )


def powershell_production_files() -> list[Path]:
    root = REPO_ROOT / "public/requests"
    return sorted(
        p for p in [*root.rglob("*.ps1"), *root.rglob("*.psm1")]
        if "RegressionTest" not in p.name and p != CONFIG_UTILS
    )


def python_literal_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [
        f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno}: {node.value!r}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and PY_PATH_LITERAL.search(node.value)
    ]


def powershell_literal_violations(path: Path) -> list[str]:
    text = re.sub(r"<#.*?#>", lambda m: "\n" * m.group(0).count("\n"), path.read_text(encoding="utf-8"), flags=re.S)
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        if PS_PATH_LITERAL.search(line):
            found.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{number}: {line.strip()[:120]}")
    return found


class DataRootsTests(unittest.TestCase):
    def test_python_production_code_has_no_spelled_out_roots(self) -> None:
        violations = [v for path in python_production_files() for v in python_literal_violations(path)]
        self.assertEqual([], violations, "use tools/data_roots.py instead of spelling out data roots")

    def test_powershell_production_code_has_no_spelled_out_roots(self) -> None:
        violations = [v for path in powershell_production_files() for v in powershell_literal_violations(path)]
        self.assertEqual([], violations, "use Get-DataSourceRoot/Get-DataDerivedRoot/Get-DataMetaRoot from ConfigUtils.psm1")

    def test_detectors_flag_path_literals_but_not_prose(self) -> None:
        self.assertTrue(PY_PATH_LITERAL.search("data-source/nfl"))
        self.assertTrue(PY_PATH_LITERAL.search("data-derived"))
        self.assertFalse(PY_PATH_LITERAL.search("fantasy-app-source-data/1"))
        self.assertFalse(PY_PATH_LITERAL.search("canonical data-source layer"))
        self.assertTrue(PS_PATH_LITERAL.search('Join-Path $r "data-source\\nfl"'))
        self.assertFalse(PS_PATH_LITERAL.search('Write-Host "canonical data-source..."'))

    def test_powershell_roots_match_python_constants(self) -> None:
        text = CONFIG_UTILS.read_text(encoding="utf-8")
        expected = {
            "DataSourceRootName": data_roots.DATA_SOURCE_ROOT,
            "DataDerivedRootName": data_roots.DATA_DERIVED_ROOT,
            "DataMetaRootName": data_roots.DATA_META_ROOT,
        }
        for variable, value in expected.items():
            match = re.search(rf"\$script:{variable}\s*=\s*'([^']+)'", text)
            self.assertIsNotNone(match, variable)
            self.assertEqual(value, match.group(1), variable)
        for function in ("Get-DataSourceRoot", "Get-DataDerivedRoot", "Get-DataMetaRoot"):
            self.assertIn(f"function {function}", text)
        for key in ("DataSourceDir", "DataDerivedDir", "DataMetaDir"):
            self.assertIn(f"{key} ", text)

    def test_python_helpers_resolve_below_repo_root(self) -> None:
        root = Path("/repo")
        self.assertEqual(root / data_roots.DATA_SOURCE_ROOT, data_roots.data_source_dir(root))
        self.assertEqual(root / data_roots.DATA_DERIVED_ROOT, data_roots.data_derived_dir(root))
        self.assertEqual(root / data_roots.DATA_META_ROOT, data_roots.data_meta_dir(root))


if __name__ == "__main__":
    unittest.main()
