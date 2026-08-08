# CBS Sports Projection Source Audit

Audit-Datum: 8. August 2026

## Ergebnis

Status: `active_public_html_source_candidate`

CBS Sports eignet sich als öffentliche zweite Projection-Quelle für Kicker. Der erste aktive Scope ist die 2026-Preseason-/Full-Regular-Season-Kicker-Projections-Tabelle.

## Geprüfte Source-Eigenschaften

### Öffentliche Kicker-Projections

Die aktuelle öffentliche CBS-Seite zeigt:

- `2026 Projections Fantasy Football Kicker Stats`
- Position `K`
- `2026 Projections`
- Non-PPR- und PPR-Ansicht
- eine vollständige Kicker-Tabelle ohne Login-Zwang

Die Non-PPR-Tabelle enthält beim Audit 36 Spielerzeilen und damit deutlich mehr als den produktiven Mindestbestand von 20.

### Kicker-Felder

Die Tabelle enthält:

- `gp`
- `fgm`, `fga`
- `lng`
- Made/Attempts für `1-19`, `20-29`, `30-39`, `40-49`, `50+`
- `xpm`, `xpa`
- `fpts`, `fppg`

Die Distanz-Buckets sind Projektionen und können Dezimalwerte enthalten. Sie dürfen deshalb nicht als Ganzzahlen erzwungen werden.

Am Tabellenende existieren echte Null-Projektionen, bei denen die Distanz-Buckets als `—` dargestellt werden. Der Source-Contract akzeptiert diese Form nur, wenn FGM und FGA ebenfalls 0 sind, und normalisiert die fehlenden Bucket-Werte dann auf 0.

### Spieleridentität

Die Spielerzeilen verlinken auf offizielle CBS-NFL-Spielerprofile mit numerischer ID im Pfad:

`/nfl/players/<id>/...`

Diese ID ist als stabile provider-interne `source_player_id` geeignet. Sie ist keine Sleeper-ID und wird nicht als ligaübergreifende kanonische Spieler-ID behandelt.

### Andere Positionen

Der gleiche öffentliche Projection-Bereich verlinkt Projections für:

- QB
- RB
- WR
- TE
- RB-WR-TE
- K
- DST

Damit ist CBS Sports grundsätzlich auch als spätere Projection-Quelle für andere Fantasy-Positionen geeignet. Diese Erweiterung ist noch nicht Bestandteil des aktiven CBS-Kicker-Contracts.

### Scoring

Die Kicker-Seite bietet Non-PPR und PPR. Für den Kicker-Source-Contract wird die explizite Non-PPR-URL verwendet. Kicker-FPTS bleiben provider-spezifisch und werden nicht als Mighty-Giants-Ligapunkte interpretiert.

Die distanzbezogenen Field-Goal-Projections werden getrennt gespeichert, damit ein späterer Analyse-Layer das tatsächliche Liga-Scoring anwenden kann, ohne die Source-Daten zu verändern.

### Freshness

Auf der auditierten CBS-Projections-Seite ist kein belastbares sichtbares Projection-Updated-Datum ausgewiesen.

Folge:

- `fetched_at` ist der verlässliche Abrufzeitpunkt.
- HTTP-Header werden als Provenance gespeichert, soweit vorhanden.
- Es wird kein `source_updated_date` erfunden.
- `source_update_timestamp_available` bleibt `false`.
- Bei wertrelevanten Analysen wird der Source frisch abgerufen.

### Zugriff und Vertrag

Der aktive Contract liest ausschließlich die normale öffentliche CBS-Sports-HTML-Seite. Beim Audit wurde auf der verwendeten Oberfläche kein dokumentierter öffentlicher Projection-API-Vertrag bestätigt.

Folge:

- kein Login
- keine Session-Cookies
- keine versteckten Browser-Endpunkte als Contract
- konservativer HTML-Parser
- höchstens regulärer Source-Refresh
- bewusste Neubewertung bei Layout- oder Zugriffsänderungen

## Produktions-Gates

Der Fetcher muss fail-closed arbeiten und insbesondere prüfen:

1. richtige Position und Saison im Seitentitel
2. expliziter Non-PPR-Kontext
3. erwartete Kicker-Spalten
4. Mindestzeilenzahl
5. eindeutige CBS-Spieler-IDs aus offiziellen Spielerlinks
6. plausibles Games-Played-Feld
7. FGM <= FGA und XPM <= XPA
8. Made <= Attempts in jedem Distanz-Bucket
9. plausible FPPG-Rundung gegenüber FPTS / GP
10. Null-Bucket-Dashes nur bei echter FGM/FGA-Null-Projektion
11. keine unerwartete Pagination

Ein Parserfehler oder unvollständiger Feed darf den letzten guten Source-Stand nicht durch einen Teilbestand ersetzen.

## Aktiver Source-Pfad

```text
fantasy-management/sources/external-rankings/projections/cbs-sports/redraft-kicker-preseason/
```

## Geprüfte öffentliche Seiten

- `https://www.cbssports.com/fantasy/football/stats/`
- `https://www.cbssports.com/fantasy/football/stats/K/2026/season/projections/nonppr/`
- offizielles CBS-NFL-Spielerprofil von Brandon Aubrey zur Prüfung der numerischen Spieler-ID im Linkpfad

## Neubewertung erforderlich, wenn

- die öffentliche Tabelle hinter Login verschoben wird
- CBS Pagination für die Kicker-Projections einführt
- die Spielerlinks keine stabile numerische CBS-ID mehr enthalten
- die Tabellenüberschriften oder Row-Struktur wesentlich geändert werden
- ein dokumentierter stabiler CBS-Projection-API-/Export-Vertrag verfügbar wird; dieser wäre gegenüber HTML zu bevorzugen
