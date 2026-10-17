"""Full real-source replay gate for #1061. Never writes into the live checkout."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from nfl_source_data_lib.common import load_registry  # noqa: E402
from nfl_source_data_lib.materialize import materialize  # noqa: E402

SOURCE = TOOLS.parent
TARGETS = ((2024, 1), (2024, 2), (2025, 1))
POSITIONS = {"QB", "RB", "WR", "TE", "FB", "K"}


def snapshot(root: Path) -> dict[str, str]:
    """Hash all canonical NFL and source-audit outputs; raw evidence is input."""
    result = {}
    for directory in ("data-source/nfl", "data-source/audits"):
        for path in sorted((root / directory).rglob("*.json")):
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            result[str(path.relative_to(root))] = digest.hexdigest()
    return result


def safe_frozen_enrichment(old: dict, new: dict) -> tuple[bool, int]:
    """Non-ID payloads, record ordering, and all existing IDs must be equal."""
    before = json.loads(json.dumps(old))
    after = json.loads(json.dumps(new))
    old_rows, new_rows = before.get("Records"), after.get("Records")
    if not isinstance(old_rows, list) or not isinstance(new_rows, list):
        return False, 0
    if len(old_rows) != len(new_rows):
        return False, 0
    filled = 0
    for old_row, new_row in zip(old_rows, new_rows, strict=True):
        old_id = old_row.pop("CanonicalPlayerID", None)
        new_id = new_row.pop("CanonicalPlayerID", None)
        if old_id not in (None, "") and old_id != new_id:
            return False, filled
        if old_id in (None, "") and new_id not in (None, ""):
            filled += 1
    return before == after, filled


class HistoricalIdentityIsolatedFullReplay(unittest.TestCase):
    @unittest.skipUnless(
        (SOURCE / "data-source/nfl/identities/players.json").is_file(),
        "Requires persisted canonical NFL sources",
    )
    def test_real_source_materialization_and_second_no_op(self):
        with tempfile.TemporaryDirectory(prefix="nfl-1061-source-replay-") as scratch:
            root = Path(scratch)
            # Real copies, NEVER hardlinks or symlinks for writable canonical data.
            shutil.copytree(SOURCE / "data-source", root / "data-source")
            app = root / "public/data"
            app.mkdir(parents=True)
            players = SOURCE / "public/data/Players.json"
            if players.is_file():
                shutil.copy2(players, app / "Players.json")
            past = SOURCE / "public/data/past_seasons"
            if past.is_dir():
                (app / "past_seasons").mkdir()
                for file in sorted(past.glob("Players_*.json")):
                    shutil.copy2(file, app / "past_seasons" / file.name)

            baseline = snapshot(root)
            old_rosters = {
                (year, week): json.loads((root /
                    f"data-source/nfl/weekly-rosters/{year}/{week:02d}.json").read_text(encoding="utf-8"))
                for year, week in TARGETS
            }
            datasets = {d.id: d for d in load_registry(root) if d.materialize}
            first = materialize(root, datasets, force=False)
            once = snapshot(root)
            paths = sorted(set(baseline) | set(once))
            changed = [p for p in paths if baseline.get(p) != once.get(p)]
            fixed = {
                "data-source/nfl/identities/players.json",
                "data-source/nfl/identities/provider-mappings.json",
                "data-source/audits/nfl-source-data-audit.json",
            }
            prefixes = ("data-source/nfl/weekly-rosters/", "data-source/nfl/player-stats/")
            # Current-season roster output is not frozen, but identity-only
            # enrichment must still preserve all other fields and existing owners.
            current_roster = "data-source/nfl/rosters/2026.json"
            if current_roster in changed:
                old_current = json.loads((SOURCE / current_roster).read_text(encoding="utf-8"))
                new_current = json.loads((root / current_roster).read_text(encoding="utf-8"))
                current_safe, current_filled = safe_frozen_enrichment(old_current, new_current)
                print(
                    f"#1061 current roster 2026: identity_only={current_safe}, "
                    f"newly_filled={current_filled}",
                    flush=True,
                )
                self.assertTrue(current_safe, "Current roster 2026 changed non-identity facts")
                self.assertGreater(current_filled, 0, "Current roster changed without identity enrichment")
                fixed.add(current_roster)

            weekly_changed = [p for p in changed if p.startswith("data-source/nfl/weekly-rosters/")]
            weekly_filled = 0
            for relative_path in weekly_changed:
                old_week = json.loads((SOURCE / relative_path).read_text(encoding="utf-8"))
                new_week = json.loads((root / relative_path).read_text(encoding="utf-8"))
                safe, filled = safe_frozen_enrichment(old_week, new_week)
                self.assertTrue(safe, f"Unexpected factual/identity drift in {relative_path}")
                weekly_filled += filled
            print(
                f"#1061 all changed weekly rosters: "
                f"partitions={len(weekly_changed)}, newly_filled={weekly_filled}, "
                "non_identity_drift=0",
                flush=True,
            )
            unexpected = [p for p in changed if p not in fixed and not p.startswith(prefixes)]
            print(
                "#1061 real isolated materialization: "
                f"canonical_players={first['identityCount']}, "
                f"changed_outputs={len(changed)}, unexpected={len(unexpected)}, "
                f"changed_paths={changed[:90]}, unexpected_paths={unexpected[:30]}",
                flush=True,
            )

            prior_ids = {
                row["CanonicalPlayerID"]
                for row in json.loads((SOURCE / "data-source/nfl/identities/players.json")
                                      .read_text(encoding="utf-8"))["Players"]
            }
            replay_ids = {
                row["CanonicalPlayerID"]
                for row in json.loads((root / "data-source/nfl/identities/players.json")
                                      .read_text(encoding="utf-8"))["Players"]
            }
            self.assertFalse(prior_ids - replay_ids, "Previously issued identities disappeared")
            print(f"#1061 newly added canonical identities={len(replay_ids - prior_ids)}", flush=True)

            for year, week in TARGETS:
                path = root / f"data-source/nfl/weekly-rosters/{year}/{week:02d}.json"
                result = json.loads(path.read_text(encoding="utf-8"))
                safe, filled = safe_frozen_enrichment(old_rosters[(year, week)], result)
                unresolved = [
                    row for row in result["Records"]
                    if row.get("Position") in POSITIONS
                    and row.get("Status") != "RET"
                    and not row.get("CanonicalPlayerID")
                ]
                print(
                    f"#1061 {year}/W{week:02d}: "
                    f"frozen_non_id_equal={safe}, newly_filled={filled}, "
                    f"relevant_unresolved={len(unresolved)}",
                    flush=True,
                )
                self.assertTrue(safe, f"Frozen facts or existing identities changed: {path}")
                self.assertFalse(unresolved, f"Unresolved PWF-relevant rows: {path}")
                old_relevant_unresolved = [
                    row for row in old_rosters[(year, week)]["Records"]
                    if row.get("Position") in POSITIONS
                    and row.get("Status") != "RET"
                    and not row.get("CanonicalPlayerID")
                ]
                if old_relevant_unresolved:
                    self.assertGreater(filled, 0, f"No identity enrichment: {path}")

            second = materialize(root, datasets, force=False)
            twice = snapshot(root)
            drift = sorted(p for p in set(once) | set(twice) if once.get(p) != twice.get(p))
            print(
                f"#1061 second isolated materialization: changed={len(drift)}, "
                f"identityChanged={second['identityChanged']}, "
                f"mappingsChanged={second['providerMappingsChanged']}, "
                f"drift_paths={drift[:30]}",
                flush=True,
            )
            self.assertFalse(drift, f"Second run not a no-op: {drift[:30]}")
            self.assertFalse(unexpected, f"Unexpected canonical outputs: {unexpected[:30]}")


if __name__ == "__main__":
    unittest.main()
