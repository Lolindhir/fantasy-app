# FFToday Projections

Dieser Bereich speichert normalisierte Spieler-Projections von FFToday als eigene Ranking-Art `projections`.

## Aktiver Scope

Aktuell wird ausschließlich das Kicker-Ranking materialisiert:

| Ranking-ID | Position | Horizont | Reihenfolge |
|---|---|---|---|
| `redraft-kicker-preseason` | K | vollständige 2026 Regular Season, Preseason-Projections | projizierte FFToday-Fantasy-Punkte absteigend |

Der Source-Audit vom 8. August 2026 bestätigt, dass derselbe öffentliche Projection-Bereich auch QB, RB, WR, TE, DEF sowie IDP-Positionen anbietet. Diese Positionen sind bewusst noch nicht aktiv materialisiert.

## Was die Quelle misst

FFToday veröffentlicht statistische Regular-Season-Projections. Für Kicker enthält die öffentliche Tabelle mindestens:

- FGM
- FGA
- FG%
- EPM
- EPA
- FPts

`FPts` ist ein von FFToday berechneter Source-Wert. Er ist kein liga-spezifischer Mighty-Giants-Punktwert. Die normalisierte Liste behält deshalb sowohl die einzelnen Kicking-Projections als auch den Source-Fantasy-Points-Wert.

## Öffentlicher Zugriff

Der aktive Fetcher liest die öffentliche Standardseite ohne Login und ohne My-FFToday-League-Profil. Custom Scoring wird nicht verwendet, weil FFToday dafür einen eingeloggten League-Profile-Kontext verlangt.

Es gibt keinen dokumentierten öffentlichen FFToday-Projection-API-Vertrag. Die Integration liest deshalb die öffentliche HTML-Tabelle konservativ und fail-closed.

## Ablagestruktur

```text
fftoday/
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
- `latest.json` verweist auf den neuesten normalisierten Snapshot und enthält Source-/Raw-Freshness.
- Historisiert werden nur geänderte `ranking.csv`- und `metadata.json`-Snapshots.
- Bleibt die normalisierte Rankingliste identisch, wird kein neuer Snapshot erzeugt; der letzte erfolgreiche Raw-Stand wird trotzdem aktualisiert.

## Normalisierte Kicker-Liste

`ranking.csv` enthält:

```text
name,Rank,source_rank,position,team,source_player_id,bye,fgm,fga,fg_pct,epm,epa,projected_fantasy_points,source_updated_date,season
```

Rangsemantik:

- `source_rank` ist die Reihenfolge der Spielerzeile auf der erfolgreich gelesenen FFToday-Seite.
- `Rank` ist der eindeutige normalisierte Kicker-Rang.
- Sortierung: `projected_fantasy_points` absteigend, danach FGM absteigend, EPM absteigend und `source_player_id`.
- `source_player_id` wird aus dem offiziellen FFToday-Spielerlink `/stats/players/<id>/...` übernommen.

## Qualitäts- und Completeness-Gates

Der Fetcher veröffentlicht nur, wenn unter anderem folgende Prüfungen bestehen:

- Seitentitel entspricht `Kicker Projections: <season>`.
- sichtbares `Regular Season, Updated: M/D/YYYY` ist vorhanden und nicht älter als standardmäßig 45 Tage.
- mindestens 20 Kicker-Zeilen werden gefunden.
- jede Zeile hat eine eindeutige FFToday-Spieler-ID.
- Bye Week liegt im plausiblen NFL-Bereich.
- FGM <= FGA und EPM <= EPA.
- FG% liegt zwischen 0 und 100 und stimmt plausibel mit FGM/FGA überein.
- eine unerwartete Pagination blockiert die Veröffentlichung, bis die Completeness-Logik bewusst erweitert wurde.

Bei Fehlern wird kein teilweiser neuer Ranking-Snapshot veröffentlicht.

## Direkter Abruf

```bash
python fantasy-management/_ai/scripts/fetch_fftoday_kicker_projections.py --skip-unchanged
```

Prüfmodi:

```bash
python fantasy-management/_ai/scripts/fetch_fftoday_kicker_projections.py --dry-run
python fantasy-management/_ai/scripts/fetch_fftoday_kicker_projections.py --input /path/to/page.html --dry-run
```

## Automatische Aktualisierung

Der GitHub-Actions-Workflow `Update FFToday Projections` aktualisiert den aktiven Projection-Bereich täglich und kann manuell gestartet werden. Er führt zuerst die Source-spezifischen Unit-Tests aus und committed ausschließlich `fantasy-management/sources/external-rankings/projections/fftoday/`.

## Interpretation

FFToday Projections sind kein Expert Consensus, kein ADP und kein Trade-Marktwert. Sie beantworten primär die Frage, welche Regular-Season-Produktion der Provider erwartet.

Für Kicker ist das besonders nützlich, weil FGM/FGA und EPM/EPA die erwartete Scoring-Gelegenheit getrennt vom beobachteten Draftmarkt zeigen. Das spätere Mighty-Giants-Ranking darf FFToday-Projections mit Kicker-ADP und aktuellen Job-/Competition-Signalen vergleichen, die Source-Werte aber nicht still in liga-spezifische Wahrheit umdeuten.
