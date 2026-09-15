from __future__ import annotations

import csv
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.historical_crosswalk import (  # noqa: E402
    _select_boundary_commits,
    sync_historical_crosswalk_evidence,
)
from nfl_source_data_lib.mapping_history import (  # noqa: E402
    build_historical_app_mapping_claims,
    extend_provider_mapping_payload,
)


def _config(start_season: int = 2024, *, minimum_rows: int | None = 1) -> dict:
    config = json.loads(
        (TOOLS.parent / "source-data/historical-identity-backfill.json").read_text(
            encoding="utf-8"
        )
    )
    config["startSeason"] = start_season
    if minimum_rows is not None:
        config["source"]["minimumRows"] = minimum_rows
    return config


def _write_config(
    root: Path, start_season: int = 2024, *, minimum_rows: int | None = 1
) -> None:
    path = root / "source-data/historical-identity-backfill.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_config(start_season, minimum_rows=minimum_rows)), encoding="utf-8"
    )


def _write_crosswalk(root: Path, season: int, rows: list[dict[str, str]]) -> None:
    relative = f"providers/dynastyprocess/ff-player-ids-history/{season}/opening.csv"
    path = root / "source-data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "mfl_id",
        "gsis_id",
        "sleeper_id",
        "espn_id",
        "pfr_id",
        "pff_id",
        "name",
        "draft_year",
        "draft_round",
        "draft_pick",
        "draft_ovr",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})

    metadata = {
        "schemaVersion": 1,
        "source": "dynastyprocess.ff-player-ids-history",
        "provider": "dynastyprocess",
        "upstream": "dynastyprocess/data",
        "repository": "dynastyprocess/data",
        "path": "files/db_playerids.csv",
        "season": season,
        "availabilityStatus": "available",
        "snapshots": [
            {
                "role": "opening",
                "commitSha": "abc123abc123abc123abc123abc123abc123abcd",
                "rawPath": relative,
            }
        ],
    }
    (path.parent / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")


class HistoricalCrosswalkTests(unittest.TestCase):
    def test_legacy_schema_acquisition_preserves_raw_and_replays_offline(self) -> None:
        # The actual 2020 opening snapshot has 2,072 rows and no draft_ovr.
        raw = b"gsis_id,sleeper_id,espn_id,pfr_id,name\n" + (
            b"00-0019596,167,2330,BradTo00,Tom Brady\n" * 2072
        )
        commit = {"sha": "a" * 40, "committedAtUtc": "2020-08-01T00:00:00Z"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_config(root, 2020, minimum_rows=None)
            with patch(
                "nfl_source_data_lib.historical_crosswalk._history_commits",
                return_value=[commit],
            ), patch(
                "nfl_source_data_lib.historical_crosswalk.urllib.request.urlopen",
                return_value=io.BytesIO(raw),
            ):
                result = sync_historical_crosswalk_evidence(root, current_season=2020)

            directory = root / "source-data/providers/dynastyprocess/ff-player-ids-history/2020"
            metadata_path = directory / "metadata.json"
            metadata_bytes = metadata_path.read_bytes()
            metadata = json.loads(metadata_bytes)
            self.assertEqual(1, result["snapshotCount"])
            self.assertEqual(raw, (directory / "opening.csv").read_bytes())
            self.assertEqual(commit["sha"], metadata["snapshots"][0]["commitSha"])
            self.assertEqual(2072, metadata["snapshots"][0]["rowCount"])
            self.assertEqual(
                hashlib.sha256(raw).hexdigest(),
                metadata["snapshots"][0]["contentHashSha256"],
            )
            self.assertEqual(
                ["gsis_id", "sleeper_id", "espn_id", "pfr_id", "name"],
                metadata["snapshots"][0]["columns"],
            )
            with patch(
                "nfl_source_data_lib.historical_crosswalk.urllib.request.urlopen",
                side_effect=AssertionError("Offline replay must not fetch"),
            ):
                replay = sync_historical_crosswalk_evidence(
                    root, current_season=2020, offline=True
                )
                frozen = sync_historical_crosswalk_evidence(
                    root, current_season=2021, offline=True
                )
            self.assertEqual("offline-existing", replay["results"][0]["status"])
            self.assertEqual("frozen-available", frozen["results"][0]["status"])
            self.assertEqual(metadata_bytes, metadata_path.read_bytes())
            self.assertEqual(raw, (directory / "opening.csv").read_bytes())

    def test_legacy_schema_still_requires_provider_columns_and_plausible_size(self) -> None:
        fields = ["gsis_id", "sleeper_id", "espn_id", "pfr_id"]
        commit = {"sha": "a" * 40, "committedAtUtc": "2020-08-01T00:00:00Z"}
        for missing in [*fields, None]:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _write_config(root, 2020, minimum_rows=None)
                retained = [field for field in fields if field != missing]
                raw = (",".join(retained) + "\n").encode()
                # Missing columns fail even with enough rows; a schema-valid
                # truncated snapshot must still fail the production size floor.
                raw += (",".join("id" for _ in retained) + "\n").encode() * (
                    2072 if missing else 1999
                )
                with patch(
                    "nfl_source_data_lib.historical_crosswalk._history_commits",
                    return_value=[commit],
                ), patch(
                    "nfl_source_data_lib.historical_crosswalk.urllib.request.urlopen",
                    return_value=io.BytesIO(raw),
                ):
                    with self.assertRaisesRegex(
                        ValueError, f"missing required columns: {missing}" if missing else "implausibly few rows"
                    ):
                        sync_historical_crosswalk_evidence(root, current_season=2020)
                directory = root / "source-data/providers/dynastyprocess/ff-player-ids-history/2020"
                self.assertFalse((directory / "opening.csv").exists())
                self.assertFalse((directory / "metadata.json").exists())

    def test_boundary_commit_selection_uses_first_and_last(self) -> None:
        commits = [
            {"sha": "b", "committedAtUtc": "2024-09-20T00:00:00Z"},
            {"sha": "a", "committedAtUtc": "2024-09-01T00:00:00Z"},
            {"sha": "c", "committedAtUtc": "2025-02-01T00:00:00Z"},
        ]
        commits.sort(key=lambda item: (item["committedAtUtc"], item["sha"]))

        selected = _select_boundary_commits(commits)

        self.assertEqual(
            [("opening", "a"), ("closing", "c")],
            [(item["role"], item["sha"]) for item in selected],
        )

    def test_no_history_metadata_is_semantic_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_config(root, 2024)

            with patch(
                "nfl_source_data_lib.historical_crosswalk._history_commits",
                return_value=[],
            ):
                first = sync_historical_crosswalk_evidence(
                    root,
                    current_season=2024,
                )
                metadata_path = (
                    root
                    / "source-data/providers/dynastyprocess/ff-player-ids-history/2024/metadata.json"
                )
                rendered = metadata_path.read_text(encoding="utf-8")
                second = sync_historical_crosswalk_evidence(
                    root,
                    current_season=2024,
                )

            self.assertEqual(1, first["noHistorySeasonCount"])
            self.assertEqual(1, second["noHistorySeasonCount"])
            self.assertEqual(rendered, metadata_path.read_text(encoding="utf-8"))
            self.assertNotIn("retrievedAtUtc", rendered)

    def test_historical_crosswalk_backfills_sleeper_from_two_non_sleeper_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_config(root, 2024)
            _write_crosswalk(
                root,
                2024,
                [
                    {
                        "gsis_id": "00-0019596",
                        "sleeper_id": "167",
                        "espn_id": "2330",
                        "pfr_id": "BradTo00",
                        "name": "Tom Brady",
                    }
                ],
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-brady",
                    "IDs": {
                        "GSIS": "00-0019596",
                        "ESPN": "2330",
                        "PFR": "BradTo00",
                    },
                    "IDAliases": {},
                }
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)

            self.assertEqual([], conflicts)
            sleeper = [
                claim
                for claim in claims
                if claim["Provider"] == "Sleeper" and claim["ExternalID"] == "167"
            ]
            self.assertEqual(1, len(sleeper))
            self.assertEqual("NFLP-brady", sleeper[0]["CanonicalPlayerID"])
            self.assertEqual(2024, sleeper[0]["ObservedSeason"])
            self.assertEqual(1, stats["externalSleeperClaimCount"])

    def test_sleeper_does_not_corroborate_itself(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_config(root, 2024)
            _write_crosswalk(
                root,
                2024,
                [
                    {
                        "gsis_id": "00-A",
                        "sleeper_id": "S1",
                        "name": "One Anchor",
                    }
                ],
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-a",
                    "IDs": {"GSIS": "00-A", "Sleeper": "S1"},
                    "IDAliases": {},
                }
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)

            self.assertEqual([], conflicts)
            self.assertFalse(
                any(
                    claim["Provider"] == "Sleeper"
                    and claim["ExternalID"] == "S1"
                    and claim["ObservedSeason"] == 2024
                    for claim in claims
                )
            )
            self.assertGreater(stats["externalInsufficientCorroborationCount"], 0)

    def test_historical_crosswalk_provider_disagreement_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_config(root, 2024)
            _write_crosswalk(
                root,
                2024,
                [
                    {
                        "gsis_id": "00-A",
                        "sleeper_id": "S1",
                        "espn_id": "2",
                        "pfr_id": "A00",
                        "name": "Ambiguous",
                    }
                ],
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-a",
                    "IDs": {"GSIS": "00-A", "PFR": "A00"},
                    "IDAliases": {},
                },
                {
                    "CanonicalPlayerID": "NFLP-b",
                    "IDs": {"ESPN": "2"},
                    "IDAliases": {},
                },
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)

            self.assertFalse(
                any(
                    claim["Provider"] == "Sleeper"
                    and claim["ExternalID"] == "S1"
                    for claim in claims
                )
            )
            self.assertEqual(1, stats["externalConflictingPlayerCount"])
            self.assertEqual("historical_crosswalk_provider_disagreement", conflicts[0]["Reason"])

    def test_historical_mapping_can_coexist_with_later_reused_sleeper_id(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-new",
                    "FirstObservedSeason": 2026,
                    "LastObservedSeason": 2026,
                    "Sources": ["current"],
                }
            ],
            "Conflicts": [],
        }
        claim = {
            "Provider": "Sleeper",
            "ExternalID": "S1",
            "CanonicalPlayerID": "NFLP-old",
            "ObservedSeason": 2024,
            "Sources": ["historical"],
        }

        once = extend_provider_mapping_payload(payload, [claim], [])
        twice = extend_provider_mapping_payload(once, [claim], [])

        mappings = [
            item for item in once["Mappings"]
            if item["Provider"] == "Sleeper" and item["ExternalID"] == "S1"
        ]
        self.assertEqual(2, len(mappings))
        self.assertEqual(once, twice)


    def test_historical_mapping_does_not_bridge_unobserved_gap(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2026,
                    "LastObservedSeason": 2026,
                    "Sources": ["current"],
                }
            ],
            "Conflicts": [],
        }
        claim = {
            "Provider": "Sleeper",
            "ExternalID": "S1",
            "CanonicalPlayerID": "NFLP-a",
            "ObservedSeason": 2024,
            "Sources": ["historical"],
        }

        result = extend_provider_mapping_payload(payload, [claim], [])

        mappings = [
            item for item in result["Mappings"]
            if item["Provider"] == "Sleeper" and item["ExternalID"] == "S1"
        ]
        self.assertEqual(2, len(mappings))
        self.assertEqual(
            [(2024, 2024), (2026, 2026)],
            sorted(
                (item["FirstObservedSeason"], item["LastObservedSeason"])
                for item in mappings
            ),
        )

    def test_contiguous_historical_observations_merge_into_interval(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2026,
                    "LastObservedSeason": 2026,
                    "Sources": ["current"],
                }
            ],
            "Conflicts": [],
        }
        claims = [
            {
                "Provider": "Sleeper",
                "ExternalID": "S1",
                "CanonicalPlayerID": "NFLP-a",
                "ObservedSeason": season,
                "Sources": [f"history-{season}"],
            }
            for season in (2024, 2025)
        ]

        result = extend_provider_mapping_payload(payload, claims, [])

        mappings = [
            item for item in result["Mappings"]
            if item["Provider"] == "Sleeper" and item["ExternalID"] == "S1"
        ]
        self.assertEqual(1, len(mappings))
        self.assertEqual(2024, mappings[0]["FirstObservedSeason"])
        self.assertEqual(2026, mappings[0]["LastObservedSeason"])

    def test_token_replay_preserves_provider_isolation_and_new_conflicts(self) -> None:
        payload = {
            "Mappings": [
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "CanonicalPlayerID": player,
                    "FirstObservedSeason": 2024,
                    "LastObservedSeason": 2024,
                    "Sources": ["existing"],
                }
                for provider, external_id, player in (
                    ("Sleeper", 7, "NFLP-a"),
                    ("ESPN", "7", "NFLP-b"),
                )
            ],
            "Conflicts": [],
        }
        original = copy.deepcopy(payload)
        claims = [
            {
                "Provider": "Sleeper",
                "ExternalID": "7",
                "CanonicalPlayerID": player,
                "ObservedSeason": season,
                "Sources": ["historical"],
            }
            for player, season in (("NFLP-c", 2024), ("NFLP-d", 2024), ("NFLP-a", 2025))
        ]

        once = extend_provider_mapping_payload(payload, claims, [])
        twice = extend_provider_mapping_payload(once, claims, [])

        self.assertEqual(original, payload)
        self.assertEqual(once, twice)
        self.assertEqual(2, len(once["Mappings"]))
        self.assertEqual(original["Mappings"][1], once["Mappings"][0])
        self.assertEqual(2025, once["Mappings"][1]["LastObservedSeason"])
        self.assertEqual(["existing", "historical"], once["Mappings"][1]["Sources"])
        self.assertEqual(1, len(once["Conflicts"]))
        self.assertEqual(["NFLP-a", "NFLP-c"], once["Conflicts"][0]["CanonicalPlayerIDs"])



if __name__ == "__main__":
    unittest.main()
