"""Parity of the combined `current` League source scope with the three single scopes (#945)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import league_source_data  # noqa: E402

CLI = TOOLS / "league_source_data.py"
SINGLE_SCOPES = (
    ("league-core", "--current-league-core-scope"),
    ("transactions", "--current-transaction-window"),
    ("drafts", "--current-draft-scope"),
)
REQUIRED_INPUTS = (
    "data-source/league-registry.json",
    "data-meta",
    "data-source/leagues",
    "data-source/providers/sleeper",
    "data-source/nfl/schedules",
    "data-source/nfl/identities/provider-mappings.json",
)


def _copy_inputs(target: Path) -> None:
    for relative in REQUIRED_INPUTS:
        source = REPO / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def _remove_current_canonical_outputs(root: Path) -> None:
    """Delete the canonical current-season outputs so the run has to rewrite them."""
    for league_dir in (root / "data-source" / "leagues").glob("*/seasons"):
        seasons = sorted(p for p in league_dir.iterdir() if p.is_dir() and p.name.isdigit())
        if not seasons:
            continue
        current = seasons[-1]
        # league.json carries the persisted WeekStructure that materialization reads back.
        for name in ("members.json", "rosters.json", "drafts.json",
                     "winners-bracket.json", "losers-bracket.json"):
            (current / name).unlink(missing_ok=True)
        for directory in ("transactions", "matchups"):
            shutil.rmtree(current / directory, ignore_errors=True)


def _tree(root: Path) -> dict[str, bytes]:
    base = root / "data-source" / "leagues"
    return {
        str(path.relative_to(base)): path.read_bytes()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _run(root: Path, *extra: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(CLI), "materialize", "--repo-root", str(root), *extra],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(f"League source CLI failed:\n{completed.stderr[-2000:]}")
    return json.loads(completed.stdout)


@unittest.skipUnless(
    all((REPO / relative).exists() for relative in REQUIRED_INPUTS),
    "persisted League data-source is not available",
)
class CurrentScopeParityTests(unittest.TestCase):
    def test_combined_scope_matches_three_single_scopes_and_is_noop_on_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as combined_dir, tempfile.TemporaryDirectory() as single_dir:
            combined, single = Path(combined_dir), Path(single_dir)
            for root in (combined, single):
                _copy_inputs(root)
                _remove_current_canonical_outputs(root)

            combined_result = _run(
                combined, "--materialization-scope", "current", "--current-scope"
            )
            single_changed = 0
            for scope, flag in SINGLE_SCOPES:
                result = _run(single, "--materialization-scope", scope, flag)
                single_changed += sum(item["CanonicalFilesChanged"] for item in result["Leagues"])

            self.assertEqual(_tree(combined), _tree(single))
            self.assertGreater(single_changed, 0, "fixture must exercise real writes")
            self.assertEqual(
                sum(item["CanonicalFilesChanged"] for item in combined_result["Leagues"]),
                single_changed,
            )

            rerun = _run(combined, "--materialization-scope", "current", "--current-scope")
            self.assertEqual(
                {item["CanonicalLeagueID"]: item["CanonicalFilesChanged"] for item in rerun["Leagues"]},
                {item["CanonicalLeagueID"]: 0 for item in rerun["Leagues"]},
            )


class CurrentScopeArgumentTests(unittest.TestCase):
    def _args(self, **overrides):
        values = dict(
            command="materialize",
            seasons=None,
            weeks=None,
            dataset_ids=None,
            materialization_scope="current",
            current_league_core_scope=False,
            current_transaction_window=False,
            current_draft_scope=False,
            current_matchup_scope=False,
            current_scope=True,
        )
        values.update(overrides)
        return league_source_data.argparse.Namespace(**values)

    def test_valid_combination(self) -> None:
        league_source_data._validate_current_scope_args(self._args())

    def test_rejects_mixing_with_single_scope(self) -> None:
        with self.assertRaises(ValueError):
            league_source_data._validate_current_scope_args(
                self._args(current_draft_scope=True)
            )

    def test_scope_and_flag_must_be_paired(self) -> None:
        with self.assertRaises(ValueError):
            league_source_data._validate_current_scope_args(
                self._args(materialization_scope="drafts")
            )
        with self.assertRaises(ValueError):
            league_source_data._validate_current_scope_args(
                self._args(current_scope=False)
            )

    def test_parts_run_in_order_and_merge_per_league(self) -> None:
        seen: list[str] = []

        def fake_execute(args):
            part = next(
                name for name, flag in league_source_data.CURRENT_SCOPE_PARTS if getattr(args, flag)
            )
            seen.append(part)
            return {"Leagues": [{
                "CanonicalLeagueID": "x",
                "Dependencies": [part, "shared"],
                "CanonicalFilesChanged": 1,
                "Current" + part: {"p": part},
            }]}

        with mock.patch.object(league_source_data, "execute", fake_execute):
            result = league_source_data.execute_current_scope(self._args())
        self.assertEqual(seen, ["league-core", "transactions", "drafts"])
        (item,) = result["Leagues"]
        self.assertEqual(item["CanonicalFilesChanged"], 3)
        self.assertEqual(item["Dependencies"], ["league-core", "shared", "transactions", "drafts"])
        self.assertEqual(item["MaterializationScope"], "current")


if __name__ == "__main__":
    unittest.main()
