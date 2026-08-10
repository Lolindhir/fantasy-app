# FFToday Projection Source Audit

Audit-Datum: 8. August 2026  
Aktivierungs- und Produktions-Update: 10. August 2026

## Ergebnis

Status: `active_public_html_source`

FFToday ist als kostenlose öffentliche Projection-Quelle für Kicker sowie QB, RB, WR und TE aktiv. Der produktive Contract nutzt ausschließlich die öffentlichen Standardseiten ohne Login und speichert positionsspezifische Rohstats getrennt vom provider-eigenen `FPts`-Wert.

## Aktiver Scope

Aktive Ranking IDs:

- `redraft-qb-preseason`
- `redraft-rb-preseason`
- `redraft-wr-preseason`
- `redraft-te-preseason`
- `redraft-kicker-preseason`

DEF und IDP sind öffentlich verfügbar, bleiben aber außerhalb des aktuellen aktiven Liga-Lineup-Scopes.

## Geprüfte Source-Eigenschaften

### Öffentliche Projections

Die öffentlichen Projection-Seiten zeigen für 2026 positionsbezogene Regular-Season-Projections mit einem sichtbaren `Updated`-Datum. Beim produktiven Erstlauf des offensiven Contracts am 10. August 2026 war das Source-Updated-Datum der aktiven QB/RB/WR/TE-Feeds der 6. August 2026.

### Offensive Felder

Der aktive offensive Fetcher behält die von FFToday veröffentlichten positionsspezifischen Rohstats bei, insbesondere:

- QB: Completions, Attempts, Passing Yards/TD/INT sowie Rushing Attempts/Yards/TD
- RB: Rushing Attempts/Yards/TD sowie Receptions/Receiving Yards/TD
- WR: Receptions/Receiving Yards/TD sowie Rushing Attempts/Yards/TD
- TE: Receptions/Receiving Yards/TD

Die Rohstats bleiben unabhängig von `FPts`, damit ein späterer Derived Layer das aktuelle Liga-Scoring anwenden kann.

### Pagination

Die offensiven FFToday-Projections sind im Gegensatz zum Kicker-Feed bereits paginiert.

Der aktive Contract folgt deshalb der öffentlichen `Next Page`-Kette vollständig und prüft:

- keine URL-/Pagination-Schleife
- höchstens eine bewusst begrenzte maximale Seitenzahl
- identische Position und Saison auf allen Seiten
- identisches sichtbares Updated-Datum auf allen Seiten
- keine doppelten Source-Spieler-IDs über Seitengrenzen hinweg
- plausible Mindestpopulation nach Zusammenführung aller Seiten

Beim produktiven Erstlauf am 10. August 2026 wurden materialisiert:

- QB: 2 Seiten
- RB: 2 Seiten
- WR: 3 Seiten
- TE: 2 Seiten

Das aktuelle offensive `raw-latest.html` enthält alle erfolgreich abgerufenen öffentlichen Seiten in einem zusammengesetzten Raw-Artefakt mit expliziten Source-Page-Kommentaren.

Der Kicker-Contract behält seine konservative bisherige Regel: unerwartete Kicker-Pagination ist weiterhin ein fail-closed Review-Trigger statt automatisch freigegeben zu werden.

### Kicker-Projections

Die öffentliche Kicker-Seite zeigt unter anderem:

- `Kicker Projections: 2026`
- `Regular Season, Updated: <date>`
- eine öffentliche Tabelle ohne Login-Zwang
- Kicker-Felder `FGM`, `FGA`, `FG%`, `EPM`, `EPA`, `FPts`

Die Kicker-Liste enthält deutlich mehr als die für einen produktiven Mindestbestand erforderlichen 20 Spieler.

### Scoring

Die öffentliche Seite zeigt einen FFToday-Scoring-Kontext. Custom Fantasy Scoring setzt laut Seite Login und ein League Profile voraus.

Für den automatisierten Source-Contract gilt deshalb:

- kein Login
- keine Session-Cookies
- kein My-FFToday-Profil
- keine Custom-Scoring-Parameter
- Source-`FPts` immer als provider-spezifischen Wert behandeln
- die einzelnen Stat-Projections unabhängig davon speichern

Für QB/RB/WR/TE berechnet der Derived Operations Layer zusätzlich liga-spezifische `core_points`. Dafür werden nur Scoring-Komponenten verwendet, die aus den aktiven Projection-Providern vergleichbar vorliegen. Nicht vergleichbar projizierte Komponenten werden nicht imputiert.

### Spieleridentität

Die öffentlichen Spielerlinks enthalten stabile provider-interne numerische IDs unter dem FFToday-Spielerpfad. Diese IDs werden als `source_player_id` gespeichert und nicht als Sleeper-ID interpretiert.

### Zugriff und Vertrag

FFToday beschreibt Rankings, Projections und Analysen als frei bereitgestellte Inhalte. Es wurde kein dokumentierter öffentlicher Projection-API-Vertrag bestätigt.

Folge:

- der Runner verwendet nur die normalen öffentlichen HTML-Seiten
- Abruf höchstens im regulären täglichen Source-Refresh sowie zur Live-Validierung relevanter Contract-Änderungen
- keine verdeckten internen Browser-Endpunkte
- kein Umgehen von Login- oder Paywall-Grenzen
- Parseränderungen müssen bei Source-Layout-Änderungen bewusst geprüft werden

## Produktions-Gates

Der Fetcher muss fail-closed arbeiten und insbesondere prüfen:

1. richtige Position und Saison im Seitentitel
2. sichtbares Source-Updated-Datum
3. Freshness-Grenze
4. erwartete positionsspezifische Spalten-/Row-Struktur
5. Mindestzeilenzahl
6. eindeutige Source-Spieler-IDs aus offiziellen Spielerlinks
7. numerische Plausibilität
8. für offensive Positionen vollständige und konsistente Pagination
9. keine Cross-Page-Duplikate oder abweichenden Source-Datenstände
10. für Kicker weiterhin keine unerwartete Pagination ohne bewusste Contract-Prüfung

Ein Parserfehler oder unvollständiger Feed darf den letzten guten Source-Stand nicht durch einen Teilbestand ersetzen.

## Aktive Source-Pfade

```text
fantasy-management/sources/external-rankings/projections/fftoday/redraft-qb-preseason/
fantasy-management/sources/external-rankings/projections/fftoday/redraft-rb-preseason/
fantasy-management/sources/external-rankings/projections/fftoday/redraft-wr-preseason/
fantasy-management/sources/external-rankings/projections/fftoday/redraft-te-preseason/
fantasy-management/sources/external-rankings/projections/fftoday/redraft-kicker-preseason/
```

## Produktionsnachweis vom 10. August 2026

Der erste produktive offensive Refresh veröffentlichte QB/RB/WR/TE-Snapshots erfolgreich. Der Source-Commit löste danach die erneute Fantasy-Operations-Materialisierung aus, sodass die neuen Projection-Signale in den Derived Datasets verfügbar wurden.

## Neubewertung erforderlich, wenn

- eine aktive öffentliche Tabelle hinter Login verschoben wird
- die öffentliche Pagination-Struktur wesentlich geändert wird
- die Spielerlinks keine stabil auslesbare Source-ID mehr enthalten
- das sichtbare Updated-Datum verschwindet oder seine Semantik geändert wird
- die Spaltenstruktur wesentlich geändert wird
- ein offizieller stabiler API-/Export-Vertrag verfügbar wird; dieser wäre gegenüber HTML bevorzugt
