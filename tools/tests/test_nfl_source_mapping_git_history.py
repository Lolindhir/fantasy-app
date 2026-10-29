from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.mapping_history import build_historical_app_mapping_claims  # noqa: E402


class NflSourceMappingGitHistoryRetiredTests(unittest.TestCase):
    def _repo(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        return temporary, root

    def _write_archive_marker(self, root: Path, season: int) -> None:
        archive = root / "public/data/past_seasons"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f"Players_{season}.json").write_text("[]", encoding="utf-8")

    def _commit_players(self, root: Path, when: str, rows: list[dict]) -> str:
        path = root / "public/data/Players.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows), encoding="utf-8")
        subprocess.run(["git", "add", str(path.relative_to(root))], cwd=root, check=True)
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        subprocess.run(
            ["git", "commit", "-m", "Players Update"],
            cwd=root,
            check=True,
            capture_output=True,
            env=env,
        )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_players_json_git_history_is_no_longer_identity_evidence(self) -> None:
        # #347 H1a: the generated Players.json is a consumer output. Its git
        # history must not produce historical provider claims or git statistics.
        temporary, root = self._repo()
        try:
            self._write_archive_marker(root, 2025)
            self._commit_players(
                root,
                "2025-10-15T12:00:00Z",
                [{"ID": "S1", "TankID": "T1", "Name": "Player A", "Position": "WR"}],
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-a",
                    "IDs": {"Sleeper": "S1", "Tank01": "T1"},
                    "IDAliases": {},
                }
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)

            self.assertEqual([], claims)
            self.assertEqual([], conflicts)
            self.assertFalse([key for key in stats if key.startswith("git")])
            self.assertEqual(0, stats["historicalClaimCount"])
        finally:
            temporary.cleanup()

if __name__ == "__main__":
    unittest.main()
