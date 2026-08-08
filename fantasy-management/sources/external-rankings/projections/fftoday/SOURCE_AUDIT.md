# FFToday Projection Source Audit

Audit-Datum: 8. August 2026

## Ergebnis

Status: `active_public_html_source`

FFToday eignet sich als kostenlose Projection-Quelle für einen konservativen täglichen Abruf der öffentlichen Standardseiten. Der erste aktive Scope ist Kicker.

## Geprüfte Source-Eigenschaften

### Öffentliche Projections

Die öffentliche Projection-Seite zeigt für 2026:

- `Kicker Projections: 2026`
- `Regular Season, Updated: <date>`
- eine öffentliche Tabelle ohne Login-Zwang
- Kicker-Felder `FGM`, `FGA`, `FG%`, `EPM`, `EPA`, `FPts`

Die Kicker-Liste enthält beim Audit deutlich mehr als die für einen produktiven Mindestbestand erforderlichen 20 Spieler.

### Andere Positionen

Der gleiche öffentliche Projection-Bereich verlinkt und veröffentlicht Projections für:

- QB
- RB
- WR
- TE
- K
- DEF
- DL
- LB
- DB

Damit ist FFToday grundsätzlich auch als spätere Projection-Quelle für die übrigen Fantasy-Positionen geeignet. Diese Erweiterung ist noch nicht Bestandteil des aktiven Contracts.

### Scoring

Die öffentliche Seite zeigt einen FFToday-Scoring-Kontext. Custom Fantasy Scoring setzt laut Seite Login und ein League Profile voraus.

Für den automatisierten Source-Contract gilt deshalb:

- kein Login
- keine Session-Cookies
- kein My-FFToday-Profil
- keine Custom-Scoring-Parameter
- Source-`FPts` immer als provider-spezifischen Wert behandeln
- die einzelnen Stat-Projections unabhängig davon speichern

### Zugriff und Vertrag

FFToday beschreibt Rankings, Projections und Analysen als frei bereitgestellte Inhalte. Beim Audit wurde jedoch keine dokumentierte öffentliche Projection-API gefunden.

Folge:

- der Runner verwendet nur die normale öffentliche HTML-Seite
- Abruf höchstens im täglichen Source-Refresh
- keine verdeckten internen Browser-Endpunkte
- kein Umgehen von Login- oder Paywall-Grenzen
- Parseränderungen müssen bei Source-Layout-Änderungen bewusst geprüft werden

## Produktions-Gates

Der Fetcher muss fail-closed arbeiten und insbesondere prüfen:

1. richtige Position und Saison im Seitentitel
2. sichtbares Source-Updated-Datum
3. Freshness-Grenze
4. erwartete Kicker-Spalten
5. Mindestzeilenzahl
6. eindeutige Source-Spieler-IDs aus offiziellen Spielerlinks
7. numerische Plausibilität von FGM/FGA, FG%, EPM/EPA und FPts
8. keine unerwartete Pagination

Ein Parserfehler oder unvollständiger Feed darf den letzten guten Source-Stand nicht durch einen Teilbestand ersetzen.

## Aktiver Source-Pfad

```text
fantasy-management/sources/external-rankings/projections/fftoday/redraft-kicker-preseason/
```

## Geprüfte öffentliche Seiten

- `https://www.fftoday.com/rankings/`
- `https://www.fftoday.com/rankings/playerproj.php?LeagueID=&PosID=80&Season=2026&order_by=FFPts&sort_order=DESC`
- `https://www.fftoday.com/rankings/playerproj.php?LeagueID=&PosID=10&Season=2026`
- `https://www.fftoday.com/about/`

## Neubewertung erforderlich, wenn

- die öffentliche Tabelle hinter Login verschoben wird
- die Seite Pagination für Kicker einführt
- die Spielerlinks keine stabil auslesbare Source-ID mehr enthalten
- die Spaltenstruktur wesentlich geändert wird
- ein offizieller stabiler API-/Export-Vertrag verfügbar wird; dieser wäre gegenüber HTML bevorzugt
