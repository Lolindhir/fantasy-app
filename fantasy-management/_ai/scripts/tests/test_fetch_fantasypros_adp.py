import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_fantasypros_adp.py"
spec = importlib.util.spec_from_file_location("fantasypros_adp_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def source_table(labels):
    rows = "".join(
        f"<tr><td></td><td>ADP</td><td>{label}</td><td>8/{1 + index:02d}</td></tr>"
        for index, label in enumerate(labels)
    )
    return (
        '<table id="sources"><tr><th></th><th>Expert</th><th>Site</th>'
        f"<th>Date</th></tr>{rows}</table>"
    )


def page_identity(config_key="ppr-overall", season=2026, wrong_identity=False):
    if config_key == "ppr-overall":
        title = (
            f"Average Draft Position (ADP) - PPR Leagues {season} | FantasyPros"
            if not wrong_identity
            else f"Average Draft Position (ADP) - Standard Leagues {season} | FantasyPros"
        )
        identity = f"<h1>Average Draft Position (ADP)</h1><div>{season} PPR Scoring</div>"
        labels = ["ESPN", "Sleeper", "CBS", "NFL", "RTSports", "Fantrax"]
    else:
        title = f"{season} Average Draft Position (ADP): Half PPR OP | FantasyPros"
        if wrong_identity:
            title = f"{season} Average Draft Position (ADP): Standard OP | FantasyPros"
        identity = (
            f"<h1>Average Draft Position (ADP)</h1><div>{season} Half PPR Scoring Superflex</div>"
        )
        labels = ["Sleeper", "FFPC"]
    return title, identity, labels


def make_html(
    config_key="ppr-overall",
    *,
    season=2026,
    change=0,
    raw_note="a",
    bad_average=False,
    wrong_identity=False,
):
    title, identity, source_labels = page_identity(config_key, season, wrong_identity)
    if config_key == "ppr-overall":
        headers = [
            "Rank", "Player (Bye)", "POS", "ESPN", "Sleeper", "CBS",
            "NFL", "RTSports", "Fantrax", "AVG", "Real-Time",
        ]
    else:
        headers = ["OP", "Overall", "Player (Bye)", "POS", "Sleeper", "FFPC", "AVG"]

    header_html = "".join(f"<th>{value}</th>" for value in headers)
    row_html = []
    positions = ["QB", "RB", "WR", "TE"]
    for index in range(1, 121):
        position = positions[(index - 1) % 4]
        player_id = 1000 + index
        name = f"Player {index}"
        player_cell = (
            f'<td><div data-player="{player_id}">'
            f'<a href="https://www.fantasypros.com/nfl/players/player-{index}.php">{name}</a>'
            f'<span class="short-name">P. {index}</span> FA ({1 + index % 14})'
            f'<a class="fp-id-{player_id}" data-fp-id="{player_id}" href="javascript:;"></a>'
            "</div></td>"
        )
        if config_key == "ppr-overall":
            espn = index + change if index == 1 else index
            sleeper = index + 1
            cbs = index
            nfl = "—"
            rtsports = index + 2
            fantrax = "—"
            values = [espn, sleeper, cbs, rtsports]
            average = sum(values) / len(values)
            if bad_average and index == 1:
                average += 5
            cells = [
                index, player_cell, f"{position}{1 + (index - 1) // 4}",
                espn, sleeper, cbs, nfl, rtsports, fantrax,
                f"{average:.1f}", index,
            ]
        else:
            sleeper = index + change if index == 1 else index
            ffpc = index + 1
            average = (sleeper + ffpc) / 2
            if bad_average and index == 1:
                average += 5
            cells = [
                index, index * 2, player_cell,
                f"{position}{1 + (index - 1) // 4}", sleeper, ffpc,
                f"{average:.1f}",
            ]
        rendered = []
        for value in cells:
            rendered.append(
                value if isinstance(value, str) and value.startswith("<td>")
                else f"<td>{value}</td>"
            )
        row_html.append("<tr>" + "".join(rendered) + "</tr>")

    return f"""
    <html><head><title>{title}</title></head><body>
    {identity}<div data-note="{raw_note}">{raw_note}</div>
    <table id="adp"><thead><tr>{header_html}</tr></thead><tbody>{''.join(row_html)}</tbody></table>
    {source_table(source_labels)}
    </body></html>
    """


def make_shell(config_key="ppr-overall", *, season=2026):
    title, identity, labels = page_identity(config_key, season)
    return f"<html><head><title>{title}</title></head><body>{identity}{source_table(labels)}</body></html>"


def make_export_tsv(config_key="ppr-overall", *, change=0, bad_average=False):
    if config_key == "ppr-overall":
        headers = [
            "Rank", "Player Name", "Team", "Bye", "POS", "ESPN", "Sleeper",
            "CBS", "NFL", "RTSports", "Fantrax", "AVG", "Real-Time",
        ]
    else:
        headers = [
            "OP", "Overall", "Player Name", "Team", "Bye", "POS",
            "Sleeper", "FFPC", "AVG",
        ]
    rows = ["FantasyPros ADP Export", "Generated for testing", "\t".join(headers)]
    positions = ["QB", "RB", "WR", "TE"]
    for index in range(1, 121):
        position = positions[(index - 1) % 4]
        if config_key == "ppr-overall":
            espn = index + change if index == 1 else index
            sleeper = index + 1
            cbs = index
            rtsports = index + 2
            values = [espn, sleeper, cbs, rtsports]
            average = sum(values) / len(values)
            if bad_average and index == 1:
                average += 5
            values_out = [
                index, f"Player {index}", "FA", 1 + index % 14,
                f"{position}{1 + (index - 1) // 4}", espn, sleeper, cbs,
                "—", rtsports, "—", f"{average:.1f}", index,
            ]
        else:
            sleeper = index + change if index == 1 else index
            ffpc = index + 1
            average = (sleeper + ffpc) / 2
            if bad_average and index == 1:
                average += 5
            values_out = [
                index, index * 2, f"Player {index}", "FA", 1 + index % 14,
                f"{position}{1 + (index - 1) // 4}", sleeper, ffpc,
                f"{average:.1f}",
            ]
        rows.append("\t".join(str(value) for value in values_out))
    return "\n".join(rows) + "\n"


class FantasyProsAdpTests(unittest.TestCase):
    def parse(self, config_key="ppr-overall", **kwargs):
        config = module.FORMAT_CONFIGS[config_key]
        html = make_html(config_key, **kwargs)
        return module.parse_adp_page(
            html,
            config,
            season=2026,
            source_url=module.build_source_url(config, 2026),
        )

    def test_active_season_uses_canonical_url_and_historical_keeps_year(self):
        config = module.FORMAT_CONFIGS["ppr-overall"]
        self.assertEqual(
            config["url"],
            module.build_source_url(config, 2026, current_season=2026),
        )
        self.assertIn(
            "year=2025",
            module.build_source_url(config, 2025, current_season=2026),
        )
        self.assertIn(
            "export=xls",
            module.build_export_url(config, 2026, current_season=2026),
        )

    def test_parses_ppr_dynamic_sources_and_player_identity(self):
        rows, diagnostics, raw = self.parse()
        self.assertEqual(120, len(rows))
        self.assertEqual(list(range(1, 121)), [row["Rank"] for row in rows])
        self.assertEqual("Player 1", rows[0]["name"])
        self.assertEqual("1001", rows[0]["source_player_id"])
        self.assertEqual("player-1", rows[0]["player_slug"])
        self.assertEqual("FA", rows[0]["team"])
        self.assertEqual("QB1", rows[0]["position_rank"])
        ranks = json.loads(rows[0]["source_ranks_json"])
        self.assertEqual(1, ranks["espn"])
        self.assertIsNone(ranks["nfl"])
        self.assertEqual(4, rows[0]["contributing_source_count"])
        self.assertEqual(
            ["cbs-sports", "espn", "rtsports", "sleeper"],
            diagnostics["active_source_ids"],
        )
        self.assertEqual(120, len(raw["ranking_rows"]))

    def test_parses_superflex_format_and_overall_rank(self):
        rows, diagnostics, _ = self.parse("half-ppr-superflex")
        self.assertEqual(120, len(rows))
        self.assertEqual(1, rows[0]["source_format_rank"])
        self.assertEqual(2, rows[0]["source_overall_rank"])
        self.assertEqual(["ffpc", "sleeper"], diagnostics["active_source_ids"])

    def test_official_export_fallback_uses_canonical_identity_and_source_dates(self):
        config = module.FORMAT_CONFIGS["ppr-overall"]
        calls = []
        responses = [
            (make_shell(), {"content_type": "text/html"}, config["url"]),
            (
                make_export_tsv(),
                {"content_type": "application/vnd.ms-excel"},
                module.build_export_url(config, 2026, current_season=2026),
            ),
        ]

        def request(url, referer=""):
            calls.append((url, referer))
            return responses[len(calls) - 1]

        item = module._prepare_live_format(
            config=config,
            season=2026,
            request=request,
        )
        self.assertEqual(2, len(calls))
        self.assertEqual(config["url"], calls[0][0])
        self.assertEqual(config["url"], calls[1][1])
        self.assertEqual("official_export_fallback", item["raw_payload"]["extraction_method"])
        self.assertEqual("delimited_export", item["raw_payload"]["ranking_document_format"])
        self.assertEqual(120, len(item["rows"]))
        self.assertEqual("Player 1", item["rows"][0]["name"])
        self.assertEqual("FA", item["rows"][0]["team"])
        self.assertEqual("", item["rows"][0]["source_player_id"])
        self.assertEqual(6, len(item["diagnostics"]["source_dates"]))

    def test_export_fallback_remains_fail_closed(self):
        config = module.FORMAT_CONFIGS["ppr-overall"]
        responses = [
            (make_shell(), {}, config["url"]),
            (make_export_tsv(bad_average=True), {}, module.build_export_url(config, 2026)),
        ]
        index = 0

        def request(url, referer=""):
            nonlocal index
            result = responses[index]
            index += 1
            return result

        with self.assertRaisesRegex(module.FantasyProsAdpError, "export fallback failed"):
            module._prepare_live_format(config=config, season=2026, request=request)

    def test_rejects_wrong_identity_and_average_mismatch(self):
        with self.assertRaisesRegex(module.FantasyProsAdpError, "not PPR"):
            self.parse(wrong_identity=True)
        with self.assertRaisesRegex(module.FantasyProsAdpError, "AVG mismatch"):
            self.parse(bad_average=True)

    def test_unchanged_ranking_updates_raw_without_new_snapshot(self):
        config = module.FORMAT_CONFIGS["ppr-overall"]
        rows, diagnostics, raw = self.parse(raw_note="first")
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            fetched_at = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
            paths, created, removed = module.write_format(
                repo_root=repo_root,
                rows=rows,
                config=config,
                diagnostics=diagnostics,
                raw_payload=raw,
                fetched_at=fetched_at,
                source_url=module.build_source_url(config, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
                retention_count=4,
            )
            self.assertTrue(created)
            self.assertEqual([], removed)
            self.assertEqual(4, len(paths))

            rows2, diagnostics2, raw2 = self.parse(raw_note="second")
            raw2["volatile_note"] = "second"
            paths2, created2, _ = module.write_format(
                repo_root=repo_root,
                rows=rows2,
                config=config,
                diagnostics=diagnostics2,
                raw_payload=raw2,
                fetched_at=datetime(2026, 7, 21, 8, tzinfo=timezone.utc),
                source_url=module.build_source_url(config, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
                retention_count=4,
            )
            self.assertFalse(created2)
            self.assertEqual(2, len(paths2))
            root = module.ranking_root(repo_root, config)
            self.assertFalse((root / "snapshots" / "2026-07-21").exists())
            latest = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual("2026-07-20", latest["snapshot_date"])
            self.assertEqual("2026-07-21T08:00:00+00:00", latest["raw_fetched_at"])

    def test_retains_latest_four_changed_snapshots(self):
        config = module.FORMAT_CONFIGS["ppr-overall"]
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            for offset in range(5):
                rows, diagnostics, raw = self.parse(change=offset)
                _, created, _ = module.write_format(
                    repo_root=repo_root,
                    rows=rows,
                    config=config,
                    diagnostics=diagnostics,
                    raw_payload=raw,
                    fetched_at=datetime(2026, 7, 20 + offset, 8, tzinfo=timezone.utc),
                    source_url=module.build_source_url(config, 2026),
                    response_headers={},
                    season=2026,
                    skip_unchanged=True,
                    retention_count=4,
                )
                self.assertTrue(created)
            root = module.ranking_root(repo_root, config)
            self.assertEqual(
                ["2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24"],
                module.snapshot_dates(root),
            )
            with (root / "snapshots" / "2026-07-24" / "ranking.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(module.CSV_FIELDS, list(csv_rows[0].keys()))

    def test_main_validates_both_formats_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ppr = root / "ppr.html"
            sf = root / "sf.html"
            ppr.write_text(make_html("ppr-overall"), encoding="utf-8")
            sf.write_text(make_html("half-ppr-superflex", bad_average=True), encoding="utf-8")
            result = module.main(
                [
                    "--season", "2026", "--repo-root", str(root),
                    "--fetched-at", "2026-07-31T06:00:00Z",
                    "--input", f"ppr-overall={ppr}",
                    "--input", f"half-ppr-superflex={sf}",
                    "--skip-unchanged",
                ]
            )
            self.assertEqual(1, result)
            self.assertFalse((root / module.SOURCE_ROOT).exists())


if __name__ == "__main__":
    unittest.main()
