import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FantasyProsLayoutTests(unittest.TestCase):
    def test_fetchers_use_expert_consensus_provider_path(self):
        dynasty = load_module(
            "fantasypros_dynasty_layout", "fetch_fantasypros_dynasty_superflex.py"
        )
        redraft = load_module(
            "fantasypros_redraft_layout", "fetch_fantasypros_redraft_ppr_superflex.py"
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            expected_provider = (
                repo_root
                / "fantasy-management"
                / "sources"
                / "external-rankings"
                / "expert-consensus"
                / "fantasypros"
            )
            self.assertEqual(
                expected_provider / dynasty.RANKING_ID, dynasty.ranking_root(repo_root)
            )
            self.assertEqual(
                expected_provider / redraft.RANKING_ID, redraft.ranking_root(repo_root)
            )

        self.assertGreaterEqual(dynasty.SCHEMA_VERSION, 6)
        self.assertGreaterEqual(redraft.SCHEMA_VERSION, 6)
        self.assertIn(
            "/expert-consensus/fantasypros/",
            f"/{redraft.ANALYSIS_METADATA_FILE}",
        )


if __name__ == "__main__":
    unittest.main()
