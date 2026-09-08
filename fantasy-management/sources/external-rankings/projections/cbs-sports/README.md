# CBS Sports Projections

Dieser Bereich speichert normalisierte CBS-Sports-Projections als `ranking_kind: projections`.

## Aktiver Scope

Aktiv materialisiert werden QB, RB, WR, TE und K als **Rest-of-Season-Projections** für die laufende NFL-Saison.

| Compatibility-Ranking-ID | Position | Aktiver Horizont | Reihenfolge |
|---|---|---|---|
| `redraft-qb-preseason` | QB | Rest of Season | projizierte CBS-Fantasy-Punkte absteigend |
| `redraft-rb-preseason` | RB | Rest of Season | projizierte CBS-Fantasy-Punkte absteigend |
| `redraft-wr-preseason` | WR | Rest of Season | projizierte CBS-Fantasy-Punkte absteigend |
| `redraft-te-preseason` | TE | Rest of Season | projizierte CBS-Fantasy-Punkte absteigend |
| `redraft-kicker-preseason` | K | Rest of Season | projizierte CBS-Fantasy-Punkte absteigend |

Die `*-preseason`-Namen bleiben derzeit als stabile Compatibility-IDs und Repository-Pfade erhalten. Sie beschreiben **nicht** mehr den aktiven Source-Horizont. Der aktive Horizont wird in `latest.json` und Snapshot-Metadaten explizit als `rest_of_season` ausgewiesen.

DST ist auf der öffentlichen CBS-Oberfläche verfügbar, wird aktuell aber nicht materialisiert.

## CBS-Lifecycle und Source-Route

Seit dem Saisonstart 2026 ist die zuvor verwendete Route

`/fantasy/football/stats/<POSITION>/<season>/season/projections/nonppr/`

nicht mehr stabil als Saisonprojektion: Am 8. September 2026 lieferte sie dem produktiven Fetcher eine echte CBS-Seite mit der Source-Identität `Week 1 Proj ... Stats`.

Der aktive Contract verwendet deshalb ausschließlich die explizite Rest-of-Season-Route:

`https://www.cbssports.com/fantasy/football/stats/<POSITION>/<season>/restofseason/projections/nonppr/`

Der Parser verlangt passend dazu die Source-Identität `Rest of Season Proj Fantasy Football <Position> Stats`. Eine Weekly-Seite wie `Week 1 Proj ...` ist semantisch ein anderer Datensatz und muss fail-closed abgewiesen werden; sie darf niemals stillschweigend in die Season-Projection-Contracts geschrieben werden.

## Was die Quelle misst

CBS veröffentlicht positionsbezogene Rest-of-Season-Projections. Für QB/RB/WR/TE werden die positionsspezifischen Offense-Statistiken sowie CBS-`FPTS`/`FPPG` separat erhalten. Die Kicker-Tabelle enthält unter anderem:

- Games Played
- FGM / FGA
- Longest Field Goal, soweit die Projection-Seite einen Wert liefert
- Made/Attempts für 1-19, 20-29, 30-39, 40-49 und 50+ Yards
- XPM / XPA
- FPTS / FPPG

Die Kicker-Distanz-Buckets können Dezimalwerte enthalten und werden deshalb als Source-Projections unverändert numerisch erhalten. Bei Spielern mit einer vollständigen Null-Projektion zeigt CBS die Distanz-Buckets teilweise als `—`; der Fetcher normalisiert diese ausschließlich dann auf 0, wenn auch FGM und FGA 0 sind.

CBS-`FPTS` sind Provider-Werte und keine Mighty-Giants-Ligapunkte. Scoring-relevante Einzelstatistiken bleiben separat erhalten, damit Downstream-Operations bei vergleichbaren Feldern liga-spezifische Core Points ableiten können, ohne CBS-Providerpunkte als League Truth zu behandeln.

## Öffentlicher Zugriff

Der Audit hat keinen dokumentierten öffentlichen Projection-API-Vertrag auf der verwendeten Oberfläche bestätigt. Deshalb lesen die Fetcher die öffentliche HTML-Tabelle konservativ und fail-closed.

CBS zeigt auf der verwendeten Projection-Oberfläche kein belastbares sichtbares Source-Updated-Datum. Der Datensatz speichert deshalb `fetched_at` und HTTP-Provenance, erfindet aber kein `source_updated_date`.

## Ablagestruktur

```text
cbs-sports/
├── README.md
├── SOURCE_AUDIT.md
├── analysis-metadata.json
├── redraft-qb-preseason/
├── redraft-rb-preseason/
├── redraft-wr-preseason/
├── redraft-te-preseason/
└── redraft-kicker-preseason/
```

Jeder aktive Ranking-Ordner verwendet denselben Grundvertrag:

```text
<ranking-id>/
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
- Eine Antwort mit falscher Source-Identität wird nicht als neuer Raw-/Ranking-Stand publiziert.

## Rang- und Identity-Semantik

- `source_rank` ist die sichtbare Reihenfolge der erfolgreich gelesenen CBS-Positionstabelle.
- `Rank` ist der eindeutige normalisierte positionsbezogene Rang.
- `source_player_id` wird aus dem offiziellen CBS-NFL-Spielerlink `/nfl/players/<id>/...` übernommen und ist eine CBS-ID, keine Sleeper-ID.
- Für Kicker erfolgt die deterministische Sortierung nach `projected_fantasy_points`, danach FGM, XPM und `source_player_id`.
- Für QB/RB/WR/TE erfolgt die deterministische Sortierung nach `projected_fantasy_points`, danach `source_player_id`.

## Qualitäts- und Completeness-Gates

Die Fetcher veröffentlichen nur, wenn unter anderem folgende Prüfungen bestehen:

- Source-Identität entspricht explizit `Rest of Season Proj Fantasy Football <Position> Stats`.
- Non-PPR-Projection-Kontext ist vorhanden.
- mindestens 20 Zeilen pro Position werden gefunden.
- jede Zeile hat eine eindeutige CBS-Spieler-ID.
- Games Played liegt im plausiblen NFL-Bereich.
- FPPG stimmt innerhalb der jeweiligen Rundung plausibel mit FPTS / Games Played überein.
- eine unerwartete Pagination blockiert die Veröffentlichung.
- Kicker zusätzlich: FGM <= FGA, XPM <= XPA und in jedem Distanz-Bucket Made <= Attempts.
- Kicker `—`-Distanz-Buckets werden nur für eine echte FGM/FGA-Null-Projektion akzeptiert.

Bei Fehlern wird kein teilweiser neuer Ranking-Snapshot veröffentlicht.

### HTTP-200 mit unerwarteter Source-Identität

Ein erfolgreicher HTTP-Transport ist noch kein erfolgreicher Source-Refresh. Liefert CBS mit HTTP 200 eine Seite, deren Source-Identität nicht dem erwarteten Projection-Contract entspricht, muss der Fetcher weiterhin fail-closed abbrechen und darf die Antwort weder als `raw-latest.html` noch als Ranking-Snapshot publizieren.

Der Kicker-Fetcher liefert für diesen Fall eine **begrenzte, operator-taugliche Diagnose**, die eine legitime Provider-Seitenänderung von einer falschen, umgeleiteten oder Interstitial-/Block-Seite unterscheiden hilft, ohne die komplette Antwort zu loggen. Die Diagnose umfasst:

- den normalisierten HTML-`title`, falls vorhanden;
- die normalisierte erste `h1`, falls vorhanden;
- den HTTP-`Content-Type`;
- die Zeichenlänge der empfangenen HTML-Antwort;
- einen kurzen SHA-256-Fingerprint der Antwort;
- einen kurzen, hart begrenzten normalisierten Textausschnitt.

Diese Diagnose ist ausschließlich Observability. Sie darf nie dazu verwendet werden, Source-Identity-, Schema-, Vollständigkeits- oder Plausibilitätsprüfungen automatisch zu lockern. Eine neue legitime CBS-Seitenidentität muss separat geprüft und explizit in den Parser-Contract übernommen werden.

## Direkter Abruf

Kicker:

```bash
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --skip-unchanged
```

QB/RB/WR/TE:

```bash
python fantasy-management/_ai/scripts/fetch_cbs_sports_offense_projections.py --skip-unchanged
```

Prüfmodi für Kicker:

```bash
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --dry-run
python fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py --input /path/to/page.html --dry-run
```

## Automatische Aktualisierung

Der GitHub-Actions-Workflow `FM • Projection • CBS Sports` aktualisiert den CBS-Projections-Bereich täglich über den zentralen Scheduler und kann zusätzlich manuell über `workflow_dispatch` gestartet werden. Er führt zuerst die CBS-spezifischen Unit-Tests aus, ruft anschließend Kicker- und Offense-Fetcher mit `--skip-unchanged` auf und veröffentlicht ausschließlich den CBS-Source-Bereich plus den erfolgreichen Source-Heartbeat über den bestehenden Generated-Data-Publish-Pfad.

## Interpretation

CBS Sports Projections sind erwartete Produktion, kein Expert Consensus, kein ADP und kein Trade-Marktwert. Der aktive In-Season-Horizont ist **Rest of Season**, nicht die einzelne aktuelle Woche. Weekly-Kontext für Lineup-/Kicker-Entscheidungen bleibt ein separater Layer und darf nicht aus diesem Season-Projection-Datensatz abgeleitet werden, indem eine Weekly-CBS-Seite in denselben Contract geschrieben wird.
