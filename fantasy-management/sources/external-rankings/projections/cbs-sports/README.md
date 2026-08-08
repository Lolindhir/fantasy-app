# CBS Sports Projections

Dieser Bereich speichert normalisierte CBS-Sports-Projections als `ranking_kind: projections`.

## Aktiver Scope

Aktuell wird ausschließlich das Kicker-Ranking materialisiert:

| Ranking-ID | Position | Horizont | Reihenfolge |
|---|---|---|---|
| `redraft-kicker-preseason` | K | vollständige 2026 Regular Season, Preseason-Projections | projizierte CBS-Fantasy-Punkte absteigend |

Der Source-Audit vom 8. August 2026 bestätigt, dass derselbe öffentliche CBS-Projections-Bereich auch QB, RB, WR, TE, kombinierte RB-WR-TE-Ansichten und DST anbietet. Diese Positionen sind noch nicht aktiv materialisiert.

## Was die Quelle misst

CBS veröffentlicht Regular-Season-Projections. Die Kicker-Tabelle enthält:

- Games Played
- FGM / FGA
- Longest Field Goal, soweit die Projection-Seite einen Wert liefert
- Made/Attempts für 1-19, 20-29, 30-39, 40-49 und 50+ Yards
- XPM / XPA
- FPTS / FPPG

Die Distanz-Buckets können Dezimalwerte enthalten und werden deshalb als Source-Projections unverändert numerisch erhalten. Bei Spielern mit einer vollständigen Null-Projektion zeigt CBS die Distanz-Buckets teilweise als `—`; der Fetcher normalisiert diese ausschließlich dann auf 0, wenn auch FGM und FGA 0 sind.

CBS-`FPTS` sind Provider-Werte und keine Mighty-Giants-Ligapunkte. Die einzelnen Kicking-Projections bleiben deshalb separat erhalten.

## Öffentlicher Zugriff

Der aktive Source-Contract verwendet die öffentliche CBS-Sports-Seite:

`https://www.cbssports.com/fantasy/football/stats/K/<season>/season/projections/nonppr/`

Der Audit hat keinen dokumentierten öffentlichen Projection-API-Vertrag auf der verwendeten Oberfläche bestätigt. Deshalb liest der Fetcher die öffentliche HTML-Tabelle konservativ und fail-closed.

CBS zeigt auf dieser Projection-Seite kein belastbares sichtbares Source-Updated-Datum. Der Datensatz speichert deshalb `fetched_at` und HTTP-Provenance, erfindet aber kein `source_updated_date`.

## Ablagestruktur

```text
cbs-sports/
├── README.md
├── SOURCE_AUDIT.md
├── analysis-metadata.json
└── redraft-kicker-preseason/
    ├── raw-latest.html
    ├── latest.json
    └── snapshots/
        └── YYYY-MM-DD/
            ├── ranking.csv
            └── metadata.json
```

## Speicherregeln

- `raw-latest.html` enthält nur die neueste erfolgreich validierte öffentliche Source-Seite.
- Historische Raw-HTML-Dateien werden nicht archiviert.
- `latest.json` verweist auf den neuesten normalisierten Snapshot.
- Historisiert werden nur geänderte `ranking.csv`- und `metadata.json`-Snapshots.
- Bleibt das normalisierte Ranking identisch, wird kein neuer Snapshot erzeugt; Raw und Fetch-Provenance werden trotzdem aktualisiert.

## Normalisierte Kicker-Liste

`ranking.csv` enthält Player-/Team-Identität, `Rank`, `source_rank`, Games Played, FGM/FGA, alle fünf Distanz-Buckets, XPM/XPA, CBS-FPTS/FPPG und Saison.

Rangsemantik:

- `source_rank` ist die sichtbare Reihenfolge der erfolgreich gelesenen CBS-Tabelle.
- `Rank` ist der eindeutige normalisierte Kicker-Rang.
- Sortierung: `projected_fantasy_points` absteigend, danach FGM, XPM und `source_player_id`.
- `source_player_id` wird aus dem offiziellen CBS-NFL-Spielerlink `/nfl/players/<id>/...` übernommen und ist eine CBS-ID, keine Sleeper-ID.

## Qualitäts- und Completeness-Gates

Der Fetcher veröffentlicht nur, wenn unter anderem folgende Prüfungen bestehen:

- Seitentitel entspricht `<season> Projections Fantasy Football Kicker Stats`.
- Non-PPR-Projection-Kontext und erwartete Kicker-Spalten sind vorhanden.
- mindestens 20 Kicker-Zeilen werden gefunden.
- jede Zeile hat eine eindeutige CBS-Spieler-ID.
- Games Played liegt im plausiblen NFL-Bereich.
- FGM <= FGA und XPM <= XPA.
- in jedem Distanz-Bucket gilt Made <= Attempts.
- CBS-FPPG stimmt innerhalb der Rundung plausibel mit FPTS / Games Played überein.
- `—` in Distanz-Buckets wird nur für eine echte FGM/FGA-Null-Projektion akzeptiert.
- eine unerwartete Pagination blockiert die Veröffentlichung.

Bei Fehlern wird kein teilweiser neuer Ranking-Snapshot veröffentlicht.

## Direkter Abruf

```bash
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --skip-unchanged
```

Prüfmodi:

```bash
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --dry-run
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --input /path/to/page.html --dry-run
```

## Automatische Aktualisierung

Der GitHub-Actions-Workflow `FM • Projection • CBS Sports` aktualisiert den CBS-Kicker-Projections-Bereich täglich um 06:08 Europe/Berlin und kann zusätzlich manuell über `workflow_dispatch` gestartet werden. Er führt zuerst die CBS-spezifischen Unit-Tests aus, ruft anschließend den Fetcher mit `--skip-unchanged` auf und committed ausschließlich `fantasy-management/sources/external-rankings/projections/cbs-sports/` über den Generated-Data-Scope `cbs-projections`.

## Interpretation

CBS Sports Projections sind erwartete Produktion, kein Expert Consensus, kein ADP und kein Trade-Marktwert. Für Kicker liefert CBS zusätzlich zu Gesamtpunkten distanzbezogene Field-Goal-Projections. Diese Rohwerte können später für eine liga-spezifische Scoring-Reconciliation genutzt werden, ohne die Source-Werte selbst umzuschreiben.
