from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from validate_episode_package import RegistryIndex, Report as PackageReport, validate_episode_package  # noqa: E402
from validate_episode_coverage import Report as CoverageReport, validate_package  # noqa: E402


class SplitEpisodeValidatorTests(unittest.TestCase):
    def test_valid_split_package_passes_both_validators(self) -> None:
        source_root = Path(__file__).resolve().parents[4]
        source_package = source_root / "fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0571"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0571"
            package.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_package, package)
            schema_source = source_root / "fantasy-management/_ai/schemas"
            schema_target = root / "fantasy-management/_ai/schemas"
            schema_target.mkdir(parents=True, exist_ok=True)
            for name in [
                "episode-index.schema.json",
                "episode-takes.schema.json",
                "episode-takes-part.schema.json",
                "episode-mentions.schema.json",
                "episode-mentions-part.schema.json",
            ]:
                shutil.copy2(schema_source / name, schema_target / name)

            package_report = PackageReport()
            validate_episode_package(
                package,
                root,
                schema_target / "episode-takes.schema.json",
                RegistryIndex(),
                package_report,
                skip_schema=False,
                skip_registry=True,
            )
            self.assertEqual([], package_report.errors)

            coverage_report = CoverageReport()
            validate_package(
                package,
                root,
                schema_target / "episode-index.schema.json",
                schema_target / "episode-mentions.schema.json",
                coverage_report,
                warnings_for_legacy=True,
            )
            self.assertEqual([], coverage_report.errors)

    def test_invalid_occurrence_inside_split_part_is_rejected(self) -> None:
        source_root = Path(__file__).resolve().parents[4]
        source_package = source_root / "fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0571"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0571"
            package.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_package, package)
            schema_source = source_root / "fantasy-management/_ai/schemas"
            schema_target = root / "fantasy-management/_ai/schemas"
            schema_target.mkdir(parents=True, exist_ok=True)
            for name in [
                "episode-index.schema.json",
                "episode-takes.schema.json",
                "episode-takes-part.schema.json",
                "episode-mentions.schema.json",
                "episode-mentions-part.schema.json",
            ]:
                shutil.copy2(schema_source / name, schema_target / name)

            part_path = package / "mentions/part01.json"
            part = json.loads(part_path.read_text(encoding="utf-8"))
            del part["mentions"][0]["occurrences"][0]["timestamp_start"]
            part_path.write_text(json.dumps(part, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            coverage_report = CoverageReport()
            validate_package(
                package,
                root,
                schema_target / "episode-index.schema.json",
                schema_target / "episode-mentions.schema.json",
                coverage_report,
                warnings_for_legacy=True,
            )
            self.assertTrue(
                any(
                    "aggregated mentions schema violation" in issue.message
                    and "timestamp_start" in issue.message
                    for issue in coverage_report.errors
                )
            )

    def test_duplicate_take_id_across_parts_is_rejected(self) -> None:
        source_root = Path(__file__).resolve().parents[4]
        source_package = source_root / "fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0571"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0571"
            package.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_package, package)
            teams_path = package / "takes/teams.json"
            teams = json.loads(teams_path.read_text(encoding="utf-8"))
            players = json.loads((package / "takes/players-part01.json").read_text(encoding="utf-8"))
            teams["takes"][0]["id"] = players["takes"][0]["id"]
            teams_path.write_text(json.dumps(teams, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            report = PackageReport()
            validate_episode_package(
                package,
                root,
                source_root / "fantasy-management/_ai/schemas/episode-takes.schema.json",
                RegistryIndex(),
                report,
                skip_schema=False,
                skip_registry=True,
            )
            self.assertTrue(any("Duplicate take id" in issue.message for issue in report.errors))


if __name__ == "__main__":
    unittest.main()
