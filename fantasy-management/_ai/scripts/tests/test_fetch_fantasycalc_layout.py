import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_fantasycalc_rankings.py"
spec = importlib.util.spec_from_file_location("fantasycalc_layout", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FantasyCalcLayoutTests(unittest.TestCase):
    def test_fetcher_uses_market_value_provider_path(self):
        config = module.FORMAT_CONFIGS["dynasty"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            self.assertEqual(
                repo_root
                / "fantasy-management"
                / "sources"
                / "external-rankings"
                / "market-value"
                / "fantasycalc"
                / config["ranking_id"],
                module.ranking_root(repo_root, config),
            )

        self.assertGreaterEqual(module.SCHEMA_VERSION, 3)
        self.assertIn(
            "/market-value/fantasycalc/",
            f"/{module.ANALYSIS_METADATA_FILE}",
        )


if __name__ == "__main__":
    unittest.main()
