# CBS Sports Projection Source Audit

Audit-Datum: 8. August 2026  
Aktivierungs- und Live-Validierungs-Update: 10. August 2026

## Ergebnis

Status: `active_public_html_source`

CBS Sports ist als öffentliche Projection-Quelle für Kicker sowie QB, RB, WR und TE aktiv. Der produktive Contract nutzt die öffentlichen 2026-Preseason-/Full-Regular-Season-Projections-Seiten ohne Login und speichert provider-spezifische Rohstats getrennt von der späteren liga-spezifischen Auswertung.

## Aktiver Scope

Aktive Ranking IDs:

- `redraft-qb-preseason`
- `redraft-rb-preseason`
- `redraft-wr-preseason`
- `redraft-te-preseason`
- `redraft-kicker-preseason`

DST ist auf der öffentlichen Projection-Oberfläche vorhanden, bleibt aber außerhalb des aktuellen aktiven Liga-Lineup-Scopes.

## Geprüfte Source-Eigenschaften

### Öffentliche Projections

Die öffentlichen CBS-Seiten stellen für 2026 positionsbezogene Projection-Tabellen bereit. Der aktive Contract verwendet explizit die Non-PPR-Ansicht. Provider-FPTS/FPPG bleiben Source-Werte und werden nicht als Mighty-Giants-Ligapunkte interpretiert.

### Offensive Felder

Der aktive offensive Fetcher behält die für die jeweilige Position veröffentlichten Rohstats bei, insbesondere:

- QB: Passing Attempts/Completions/Yards/TD/INT sowie Rushing Attempts/Yards/TD
- RB: Rushing sowie Targets/Receptions/Receiving und Fumbles Lost
- WR: Targets/Receptions/Receiving sowie Rushing und Fumbles Lost
- TE: Targets/Receptions/Receiving und Fumbles Lost

Diese Rohstats ermöglichen im Derived Operations Layer eine liga-spezifische `core_points`-Berechnung. Dabei werden nur Scoring-Komponenten verwendet, die aus den aktiven Projection-Providern vergleichbar vorliegen. Nicht vergleichbar projizierte Komponenten werden nicht imputiert.

### Source-Position vs. Ranking-Position

Die öffentliche CBS-Tabelle kann auf einer Fantasy-Positionsseite Spieler mit einer abweichenden football-spezifischen Source-Position führen.

Live bestätigt am 10. August 2026:

- die RB-Projections-Seite enthält Fullbacks, zum Beispiel `FB`
- die TE-Projections-Seite kann ebenfalls einen `FB`-Eintrag enthalten

Der Contract behandelt das source-treu:

- `position` bleibt die Fantasy-/Seitenposition des Rankings (`RB` bzw. `TE`)
- `source_position` speichert den von CBS tatsächlich angezeigten Wert, zum Beispiel `FB`
- unerwartete Source-Positionen außerhalb der positionsspezifisch erlaubten Menge führen weiterhin fail-closed zu einem Fehler

### Signed Yardage

CBS kann bei kleinen Nebenrollen negative Yardage-Projections veröffentlichen. Im Live-Check wurde beispielsweise eine negative Rushing-Yard-Projektion auf der WR-Seite beobachtet.

Deshalb gilt:

- Yardage- und zugehörige Average-Felder dürfen negative Werte erhalten
- echte Counting Stats wie Attempts, Targets, Receptions und Touchdowns müssen weiterhin nichtnegativ sein
- negative Werte werden nicht auf null gekappt oder anderweitig bereinigt

### Kicker-Felder

Die Kicker-Tabelle enthält:

- `gp`
- `fgm`, `fga`
- `lng`
- Made/Attempts für `1-19`, `20-29`, `30-39`, `40-49`, `50+`
- `xpm`, `xpa`
- `fpts`, `fppg`

Die Distanz-Buckets sind Projektionen und können Dezimalwerte enthalten. Sie dürfen deshalb nicht als Ganzzahlen erzwungen werden.

Am Tabellenende können echte Null-Projektionen vorkommen, bei denen Distanz-Buckets als `—` dargestellt werden. Der Kicker-Contract akzeptiert diese Form nur, wenn FGM und FGA ebenfalls 0 sind, und normalisiert die fehlenden Bucket-Werte dann auf 0.

### Spieleridentität

Die Spielerzeilen verlinken auf offizielle CBS-NFL-Spielerprofile mit numerischer ID im Pfad:

`/nfl/players/<id>/...`

Diese ID ist als stabile provider-interne `source_player_id` geeignet. Sie ist keine Sleeper-ID und wird nicht als ligaübergreifende kanonische Spieler-ID behandelt.

### Scoring

Für den Source-Contract werden die veröffentlichten Provider-Werte und Rohstats unverändert getrennt gehalten.

Für QB/RB/WR/TE gilt im Downstream:

- CBS-`FPTS` sind keine Liga-Projektion
- das aktuelle `League.json -> ScoringType` wird nur im Derived Operations Layer angewendet
- `core_points` werden nur aus vergleichbar projizierten Komponenten berechnet
- nicht verfügbare 2-Point-/sonstige Scoring-Komponenten werden nicht erfunden

Für Kicker werden die distanzbezogenen Field-Goal-Projections getrennt gespeichert, damit der positionsspezifische Kicker-Layer das tatsächliche Liga-Scoring anwenden kann.

### Freshness

Auf den auditierten CBS-Projections-Seiten ist kein belastbares sichtbares Projection-Updated-Datum ausgewiesen.

Folge:

- `fetched_at` ist der verlässliche Abrufzeitpunkt
- HTTP-Header werden als Provenance gespeichert, soweit vorhanden
- es wird kein `source_updated_date` erfunden
- `source_update_timestamp_available` bleibt `false`
- bei wertrelevanten Analysen wird der Source frisch abgerufen

### Zugriff und Vertrag

Der aktive Contract liest ausschließlich die normalen öffentlichen CBS-Sports-HTML-Seiten. Es wurde kein dokumentierter öffentlicher Projection-API-Vertrag bestätigt.

Folge:

- kein Login
- keine Session-Cookies
- keine versteckten Browser-Endpunkte als Contract
- konservativer HTML-Parser
- regulärer täglicher Source-Refresh
- Live-Source-Validierung bei relevanten Pull-Request-Änderungen
- bewusste Neubewertung bei Layout- oder Zugriffsänderungen

## Produktions-Gates

Der Fetcher muss fail-closed arbeiten und insbesondere prüfen:

1. richtige Position und Saison im Seitentitel
2. expliziter Non-PPR-Kontext
3. erwartete positionsspezifische Row-Struktur
4. Mindestzeilenzahl
5. eindeutige CBS-Spieler-IDs aus offiziellen Spielerlinks
6. plausible Games-Played-Werte
7. plausible FPPG-Rundung gegenüber FPTS / GP
8. nur positionsspezifisch erlaubte Source-Positionen
9. negative Werte nur in explizit signed-fähigen Yardage-/Average-Feldern
10. keine unerwartete Pagination
11. für Kicker zusätzlich Makes <= Attempts und die positionsspezifischen Distanz-Bucket-Regeln

Ein Parserfehler oder unvollständiger Feed darf den letzten guten Source-Stand nicht durch einen Teilbestand ersetzen.

## Aktive Source-Pfade

```text
fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-qb-preseason/
fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-rb-preseason/
fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-wr-preseason/
fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-te-preseason/
fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-kicker-preseason/
```

## Produktionsnachweis vom 10. August 2026

Nach erfolgreicher Live-Validierung wurden QB/RB/WR/TE im regulären CBS-Workflow materialisiert. Die neuen `latest.json`-Pointer und normalisierten Snapshots wurden veröffentlicht und lösten anschließend die erneute Fantasy-Operations-Materialisierung aus.

## Neubewertung erforderlich, wenn

- die öffentliche Tabelle hinter Login verschoben wird
- CBS Pagination für einen aktiven Positionsfeed einführt
- die Spielerlinks keine stabile numerische CBS-ID mehr enthalten
- neue bislang nicht erlaubte Source-Positionen auf einer aktiven Fantasy-Positionsseite erscheinen
- die Tabellenüberschriften oder Row-Struktur wesentlich geändert werden
- ein dokumentierter stabiler CBS-Projection-API-/Export-Vertrag verfügbar wird; dieser wäre gegenüber HTML zu bevorzugen
