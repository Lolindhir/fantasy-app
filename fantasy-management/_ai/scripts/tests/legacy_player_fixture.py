"""Test helper: feed the builders the legacy-shaped fixture players.

The builders read players through canonical_player_inputs.load_players, which
needs the full canonical repository (Sleeper snapshot, NFL rosters, profiles,
PlayerValuation). The builder tests use a minimal fake world, so they stub that
one function with the fixture file public/data/Players.json. The real function
is covered by test_canonical_player_inputs.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import canonical_player_inputs


def patch_player_inputs(testcase) -> None:
    def load_players(root, league_id, season, reference_date):
        return json.loads((Path(root) / "public/data/Players.json").read_text(encoding="utf-8"))

    def source_files(root, league_id, season):
        return [("players", Path(root) / "public/data/Players.json")]

    for name, replacement in (("load_players", load_players), ("source_files", source_files)):
        patcher = mock.patch.object(canonical_player_inputs, name, replacement)
        patcher.start()
        testcase.addCleanup(patcher.stop)
