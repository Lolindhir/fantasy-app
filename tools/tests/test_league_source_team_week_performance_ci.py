"""Register TeamWeekPerformance regression and real-source integration tests in existing CI.

The current CI already discovers test_league_source*.py without any Actions
workflow edits. Keep the canonical tests in their focused modules and import
their suites here, including the real PowerShell adapter test.
"""
from __future__ import annotations

import unittest


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    suite = unittest.TestSuite()
    for module in (
        "tools.tests.test_weekly_lineup_optimizer",
        "tools.tests.test_team_week_performance",
        "tools.tests.test_team_week_performance_sources",
        "tools.tests.test_team_week_performance_integration",
        "tools.tests.test_team_week_performance_materialize",
    ):
        suite.addTests(loader.loadTestsFromName(module))
    return suite
