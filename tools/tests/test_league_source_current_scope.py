"""Parity of the combined `current` League source scope with the three single scopes (#945)."""

from __future__ import annotations

import json
import re
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



class SourceValidationSparseCheckoutContracts(unittest.TestCase):
    """G5 fail-closed profile checks for the existing shared Source workflow."""

    def _workflow(self) -> str:
        return (REPO / ".github/workflows/sync-league-source-data.yml").read_text(
            encoding="utf-8"
        )

    def test_current_pr_and_live_use_the_same_blobless_sparse_profile(self) -> None:
        workflow = self._workflow()
        profiles = re.findall(
            r"^          sparse-checkout: \|\n((?:^            [^\n]+\n)+)",
            workflow, flags=re.MULTILINE,
        )
        # the third profile is the non-cone write-capable sync checkout (G5 E1), tested separately
        self.assertEqual(3, len(profiles), "PR proof must use the exact production profile")
        profiles = profiles[:2]
        self.assertEqual(profiles[0], profiles[1])
        directories = set(profiles[0].strip().splitlines())
        selected = {entry.strip() for entry in directories}
        self.assertEqual(
            {
                "tools", ".github/workflows", "data-meta",
                "data-source/leagues", "data-source/providers/sleeper",
                "data-source/nfl/schedules", "data-source/nfl/identities",
            }, selected,
        )
        self.assertNotIn("data-source", selected)  # would pull multi-GB historical sources
        self.assertNotIn("data-source/nfl/player-stats", selected)
        self.assertNotIn("data-source/nfl/weekly-rosters", selected)
        self.assertNotIn("filter: blob:none", workflow)  # checkout filter overrides sparse input
        self.assertEqual(4, workflow.count("remote.origin.partialclonefilter"))  # + sync verify (G5 E1)

    def test_full_noncurrent_source_modes_and_publisher_remain_unchanged(self) -> None:
        workflow = self._workflow()
        validate = workflow.split("\n  validate:\n", 1)[1].split(
            "\n  validate_current_sparse_pr:\n", 1
        )[0]
        self.assertIn("if: env.MATERIALIZATION_SCOPE == 'current'", validate)
        self.assertIn("if: env.MATERIALIZATION_SCOPE != 'current'", validate)
        self.assertEqual(2, validate.count("uses: actions/checkout@v7"))
        self.assertIn('full)\n              python -m unittest discover -s tools/tests', validate)
        self.assertIn("python tools/league_source_data.py validate", validate)

        pr = workflow.split("\n  validate_current_sparse_pr:\n", 1)[1].split(
            "\n  sync:\n", 1
        )[0]
        self.assertIn("if: github.event_name == 'pull_request'", pr)
        self.assertIn("contents: read", pr)
        self.assertIn("tools.tests.test_league_source_current_scope -v", pr)
        self.assertIn("tools.tests.test_league_source_transaction_window", pr)
        self.assertIn("python tools/league_source_data.py validate", pr)
        sync = workflow.split("\n  sync:\n", 1)[1]
        self.assertIn("needs: validate", sync)
        self.assertIn("name: Checkout main", sync)
        self.assertIn("token: $" + "{{ secrets.PAT_PUSH }}", sync)
        self.assertIn("name: Sync, materialize and publish League source data", sync)
        self.assertEqual(1, sync.count("sparse-checkout:"))  # G5 E1: current scope only
        self.assertIn("if: env.MATERIALIZATION_SCOPE != 'current'", sync)
        self.assertIn("git sparse-checkout disable", sync)

    def test_sparse_input_guard_checks_parity_and_rejects_oversized_sources(self) -> None:
        workflow = self._workflow()
        guard_lines = re.findall(
            r"^          for path in (.+); do$", workflow, flags=re.MULTILINE,
        )
        guard_lines = [line for line in guard_lines if '"tools/league_source_data.py"' in line]  # sync fallback verify is unquoted
        self.assertEqual(2, len(guard_lines), "Both scoped guards must verify real inputs")
        self.assertEqual(guard_lines[0], guard_lines[1])
        for path in (
            "tools/tests/test_league_source_current_scope.py",
            "data-source/league-registry.json",
            "data-meta/nfl-reise/metadata.json",
            "data-source/leagues/nfl-reise/manifest.json",
            "data-source/nfl/schedules/2026.json",
            "data-source/nfl/identities/provider-mappings.json",
            "data-source/providers/sleeper",
        ):
            self.assertIn(f'"{path}"', guard_lines[0], path)
        self.assertEqual(2, workflow.count("Historical player stats unexpectedly checked out"))
        self.assertEqual(2, workflow.count("Historical rosters unexpectedly checked out"))
        self.assertEqual(2, workflow.count("Missing required current-scope input"))
        self.assertEqual(3, workflow.count("core.sparseCheckout"))  # + sync fallback verify (G5 E1)
        self.assertEqual(3, workflow.count("Blobless Git filter missing"))  # + sync verify (G5 E1)


class SyncSparseGitMechanicsTest(unittest.TestCase):
    """G5 E1: the publish loop's git mechanics (reset, clean, add, push, race rebuild) work in the sparse clone."""

    @staticmethod
    def _profile() -> list[str]:
        workflow = (REPO / ".github/workflows/sync-league-source-data.yml").read_text(encoding="utf-8")
        block = re.findall(
            r"^          sparse-checkout: \|\n((?:^            [^\n]+\n)+)", workflow, flags=re.MULTILINE
        )[2]
        return [line.strip() for line in block.splitlines() if line.strip()]

    def test_profile_covers_inputs_and_writes_and_excludes_history(self) -> None:
        profile = self._profile()
        for required in (
            "/tools/", "/data-meta/", "/data-source/leagues/", "/data-source/providers/sleeper/",
            "/data-source/nfl/schedules/", "/data-source/nfl/identities/", "/data-source/_sync/",
            "/data-source/*.json",
        ):
            self.assertIn(required, profile)
        self.assertFalse([p for p in profile if "player-stats" in p or "weekly-rosters" in p])

    def _git(self, cwd, *args, check=True):
        import subprocess
        return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True,
                              env={**__import__("os").environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})

    def test_loop_mechanics_and_race_recovery_in_sparse_blobless_clone(self) -> None:
        import subprocess
        import sys
        import tempfile
        from pathlib import Path as P

        with tempfile.TemporaryDirectory() as tmp:
            base = P(tmp)
            seed = base / "seed"
            seed.mkdir()
            self._git(seed, "init", "-q", "-b", "main")
            for rel, body in {
                "tools/a.py": "x", "data-meta/m.json": "{}", "data-source/league-registry.json": "{}",
                "data-source/leagues/l/seasons/2026/league.json": "{}",
                "data-source/providers/sleeper/leagues/1/league.json": "{}",
                "data-source/_sync/keep.json": "{}",
                "data-source/nfl/player-stats/2001.json": "history",
                "data-source/nfl/weekly-rosters/2001/1.json": "history",
            }.items():
                (seed / rel).parent.mkdir(parents=True, exist_ok=True)
                (seed / rel).write_text(body)
            self._git(seed, "add", "-A")
            self._git(seed, "commit", "-q", "-m", "seed")
            origin = base / "origin.git"
            subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(origin)], check=True)
            self._git(origin, "config", "uploadpack.allowFilter", "true")
            self._git(origin, "config", "uploadpack.allowAnySHA1InWant", "true")
            self._git(origin, "config", "receive.denyCurrentBranch", "ignore")
            url = f"file://{origin}"

            def sparse_clone(name):
                c = base / name
                subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", "--depth", "1",
                                "--branch", "main", url, str(c)], check=True)
                self._git(c, "sparse-checkout", "init", "--no-cone")
                (c / ".git" / "info" / "sparse-checkout").write_text("\n".join(self._profile()) + "\n")
                self._git(c, "checkout", "-q", "main")
                return c

            a, b = sparse_clone("a"), sparse_clone("b")
            self.assertTrue((a / "tools/a.py").exists())
            self.assertFalse((a / "data-source/nfl/player-stats").exists())
            helper = [sys.executable, str(REPO / "tools" / "git_transient.py")]

            # competing writer pushes first
            (b / "data-source/leagues/l/seasons/2026/league.json").write_text('{"b":1}')
            self._git(b, "add", "-A", "--", "data-source/leagues", "data-source/_sync")
            self._git(b, "commit", "-q", "-m", "b")
            self._git(b, "push", "-q", url, "HEAD:main")

            # writer a: stale base -> race -> reset_to_main -> rebuild -> push
            def write_and_commit():
                (a / "data-source/providers/sleeper/leagues/1/league.json").write_text('{"a":1}')
                self._git(a, "add", "-A", "--", "data-source/providers/sleeper/leagues", "data-source/leagues")
                self._git(a, "commit", "-q", "-m", "a")

            write_and_commit()
            race = subprocess.run(helper + ["push", url, "HEAD:main"], cwd=a, capture_output=True, text=True)
            self.assertEqual(10, race.returncode, race.stderr)
            self._git(a, "reset", "-q", "--hard", "HEAD~1")
            fetch = subprocess.run(helper + ["fetch", url, "main"], cwd=a, capture_output=True, text=True)
            self.assertEqual(0, fetch.returncode, fetch.stderr)
            self._git(a, "reset", "-q", "--hard", "FETCH_HEAD")
            self._git(a, "clean", "-fdq", "--", "data-source/providers/sleeper/leagues",
                      "data-source/leagues", "data-source/_sync")
            self.assertEqual('{"b":1}', (a / "data-source/leagues/l/seasons/2026/league.json").read_text())
            self.assertFalse((a / "data-source/nfl/player-stats").exists())
            write_and_commit()
            ok = subprocess.run(helper + ["push", url, "HEAD:main"], cwd=a, capture_output=True, text=True)
            self.assertEqual(0, ok.returncode, ok.stderr)
            # a path outside the profile cannot be staged silently
            (a / "data-source/nfl/player-stats").mkdir(parents=True, exist_ok=True)
            (a / "data-source/nfl/player-stats/new.json").write_text("x")
            status = self._git(a, "status", "--porcelain=v1", "--untracked-files=all").stdout
            self.assertIn("data-source/nfl/player-stats/new.json", status)  # visible to assert_league_source_only


if __name__ == "__main__":
    unittest.main()
