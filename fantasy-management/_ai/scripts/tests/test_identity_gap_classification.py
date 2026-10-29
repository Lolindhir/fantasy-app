#!/usr/bin/env python3
"""Tests for the structural identity-gap classifier (Issue #347, B3)."""

from __future__ import annotations

import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import identity_gap_classification as gap  # noqa: E402


def record(**ids: str) -> dict:
    return {"IDs": ids}


class IdentityGapClassificationTests(unittest.TestCase):
    def test_placeholder_gsis_upgrade_needs_shared_esb_on_exactly_two_records(self) -> None:
        provisional = record(GSIS="PRY456541", ESB="PRY456541", Sleeper="13261")
        durable = record(GSIS="00-0040792", ESB="PRY456541", PFF="148184")
        self.assertEqual(
            gap.PLACEHOLDER_GSIS_UPGRADE,
            gap.classify_identity_gap(
                provisional, durable, esb_occurrences=Counter({"PRY456541": 2})
            ),
        )
        # A third record with the same ESB keeps the pair out of the automatic class.
        self.assertIsNone(
            gap.classify_identity_gap(
                provisional, durable, esb_occurrences=Counter({"PRY456541": 3})
            )
        )

    def test_placeholder_rule_rejects_other_disagreeing_shared_provider(self) -> None:
        provisional = record(GSIS="X1", ESB="E1", PFR="A")
        durable = record(GSIS="00-0000001", ESB="E1", PFR="B")
        self.assertIsNone(
            gap.classify_identity_gap(
                provisional, durable, esb_occurrences=Counter({"E1": 2})
            )
        )

    def test_two_valid_gsis_values_are_not_a_placeholder_pair(self) -> None:
        a = record(GSIS="00-0000001", ESB="E1")
        b = record(GSIS="00-0000002", ESB="E1")
        self.assertIsNone(
            gap.classify_identity_gap(a, b, esb_occurrences=Counter({"E1": 2}))
        )

    def test_split_identity_has_no_shared_provider(self) -> None:
        self.assertEqual(
            gap.SPLIT_IDENTITY,
            gap.classify_identity_gap(
                record(Sleeper="14071", Tank01="5393270"),
                record(GSIS="00-0041585", PFR="FinlGr00", ESB="FIN386337"),
            ),
        )

    def test_hartman_is_a_wrong_upstream_claim(self) -> None:
        provisional = record(Sleeper="11558", Tank01="4361994")
        durable = record(GSIS="00-0039677", Sleeper="11376", ESPN="4361994", ESB="HAR733165")
        self.assertEqual(
            gap.WRONG_UPSTREAM_CLAIM, gap.classify_identity_gap(provisional, durable)
        )

    def test_same_provider_disagreement_without_cross_anchor_stays_unclassified(self) -> None:
        # Two unrelated same-name players must not be held as one person.
        self.assertIsNone(
            gap.classify_identity_gap(
                record(Sleeper="1", Tank01="10"),
                record(GSIS="00-0000009", Sleeper="2", ESPN="99"),
            )
        )

    def test_age_counts_days_since_contract_and_never_goes_negative(self) -> None:
        self.assertEqual(0, gap.age_in_days(date(2026, 10, 4)))
        self.assertEqual(10, gap.age_in_days(date(2026, 10, 14)))
        self.assertEqual(0, gap.age_in_days(date(2026, 9, 1)))


if __name__ == "__main__":
    unittest.main()
