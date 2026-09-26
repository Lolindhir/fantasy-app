from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.nfl_source_data_lib.identity import (
    _app_player_espn_bridge,
    _build_components,
    app_player_candidates,
)
from tools.nfl_source_data_lib.identity_model import IdentityCandidate


def external_candidate(ids: dict[str, str]) -> IdentityCandidate:
    return IdentityCandidate(
        ids=ids,
        name="External Player",
        first_name="External",
        last_name="Player",
        birth_date="2001-01-01",
        position="WR",
        latest_team="NYG",
        source="nflverse.ff-player-ids",
        priority=10,
    )


class AppEspnIdentityBridgeTests(unittest.TestCase):
    def test_tank01_espn_link_bridges_only_to_independently_observed_external_anchor(self) -> None:
        row = {
            "ID": "S1",
            "TankID": "T1",
            "ESPNID": None,
            "ESPN": "https://www.espn.com/nfl/player/_/id/4566158/ben-sauls",
        }
        anchor_candidates = {
            ("ESPN", "4566158"): [external_candidate({"ESPN": "4566158"})]
        }
        self.assertEqual(
            "4566158",
            _app_player_espn_bridge(row, anchor_candidates),
        )
        self.assertIsNone(_app_player_espn_bridge(row, {}))

    def test_sleeper_and_tank01_espn_disagreement_fails_closed(self) -> None:
        row = {
            "ID": "S1",
            "TankID": "T1",
            "ESPNID": "14870",
            "ESPN": "https://www.espn.com/nfl/player/_/id/4685408/will-johnson",
        }
        anchor_candidates = {
            ("ESPN", "14870"): [external_candidate({"ESPN": "14870"})],
            ("ESPN", "4685408"): [external_candidate({"ESPN": "4685408"})],
        }
        self.assertIsNone(_app_player_espn_bridge(row, anchor_candidates))

    def test_conflicting_current_sleeper_claim_blocks_espn_bridge(self) -> None:
        row = {
            "ID": "11558",
            "TankID": "4361994",
            "ESPNID": None,
            "ESPN": "https://www.espn.com/nfl/player/_/id/4361994/sam-hartman",
        }
        anchor_candidates = {
            ("ESPN", "4361994"): [
                external_candidate(
                    {
                        "ESPN": "4361994",
                        "Sleeper": "11376",
                    }
                )
            ]
        }
        self.assertIsNone(_app_player_espn_bridge(row, anchor_candidates))

    def test_matching_current_sleeper_claim_does_not_block_espn_bridge(self) -> None:
        row = {
            "ID": "S1",
            "TankID": "T1",
            "ESPNID": "1234",
            "ESPN": None,
        }
        anchor_candidates = {
            ("ESPN", "1234"): [
                external_candidate(
                    {
                        "ESPN": "1234",
                        "Sleeper": "S1",
                    }
                )
            ]
        }
        self.assertEqual("1234", _app_player_espn_bridge(row, anchor_candidates))

    def test_app_candidate_does_not_seed_unobserved_espn_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public/data").mkdir(parents=True)
            (root / "public/data/Players.json").write_text(
                json.dumps(
                    [
                        {
                            "ID": "S1",
                            "TankID": "T1",
                            "ESPNID": None,
                            "ESPN": "https://www.espn.com/nfl/player/_/id/1234/test-player",
                            "Name": "Test Player",
                            "Position": "WR",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            candidates, _ = app_player_candidates(
                root,
                external_anchor_candidates={},
            )

        self.assertEqual(1, len(candidates))
        self.assertEqual({"Sleeper": "S1", "Tank01": "T1"}, candidates[0].ids)

    def test_correlated_espn_anchor_attaches_app_candidate_to_durable_identity_not_provisional(self) -> None:
        durable_existing = IdentityCandidate(
            ids={"GSIS": "00-1", "ESPN": "1234"},
            name="Test Player",
            first_name="Test",
            last_name="Player",
            birth_date="2001-01-01",
            position="WR",
            latest_team="NYG",
            source="canonical-existing",
            priority=0,
            existing_internal_id="NFLP-durable",
        )
        durable_current = IdentityCandidate(
            ids={"GSIS": "00-1", "ESPN": "1234"},
            name="Test Player",
            first_name="Test",
            last_name="Player",
            birth_date="2001-01-01",
            position="WR",
            latest_team="NYG",
            source="nflverse.players",
            priority=10,
        )
        provisional_existing = IdentityCandidate(
            ids={"Sleeper": "S1", "Tank01": "T1"},
            name="Test Player",
            first_name=None,
            last_name=None,
            birth_date=None,
            position="WR",
            latest_team="NYG",
            source="canonical-existing",
            priority=0,
            existing_internal_id="NFLP-provisional",
        )
        app_current = IdentityCandidate(
            ids={"Sleeper": "S1", "Tank01": "T1", "ESPN": "1234"},
            name="Test Player",
            first_name=None,
            last_name=None,
            birth_date=None,
            position="WR",
            latest_team="NYG",
            source="app.Players",
            priority=30,
        )

        candidates = [
            durable_existing,
            durable_current,
            provisional_existing,
            app_current,
        ]
        union_find = _build_components(candidates)

        self.assertEqual(union_find.find(0), union_find.find(1))
        self.assertEqual(union_find.find(0), union_find.find(3))
        self.assertNotEqual(union_find.find(0), union_find.find(2))


if __name__ == "__main__":
    unittest.main()
