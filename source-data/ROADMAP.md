# NFL Source-Data Roadmap

Diese Roadmap hält den aktuell beschlossenen Ausbau der persistenten NFL-Source-Data-Schicht fest, bevor bestehende App-Generatoren auf neue Quellen umgestellt werden.

## Leitplanke

- Zuerst wird die vollständige `source-data`-Schicht aufgebaut, validiert und idempotent gemacht.
- Bis diese Schicht vollständig und stabil ist, bleiben `public/requests/**`, die bestehenden App-Read-Model-Verträge unter `public/data/**` und deren heutige Provider-Nutzung unverändert.
- Die spätere Generator-Migration erfolgt erst danach als eigener Schritt und feldweise gegen die dann vorhandenen kanonischen Source-Verträge.
- Eine neue Source-Quelle wird nicht allein durch Registrierung automatisch zum App-Provider.

## Bereits aktive Source-Datasets

- `nflverse.players`
- `nflverse.ff-player-ids`
- `nflverse.draft-picks`
- `nflverse.combine`

## Noch aufzubauende Source-Datasets

### NFLverse

- `nflverse.schedules`
  - Schedule, Season, Week, Game Type, Teams, Kickoff und Scores.
  - Kanonische Game-ID: nflverse `game_id`.

- `nflverse.game-finality`
  - Finality-Evidenz über nflverse `released_games.csv`.
  - Ein Score allein darf niemals als Final-Nachweis gelten.
  - Spätere kanonische Regel: Ein Spiel gilt als final, wenn seine `game_id` in der validierten nflverse-Release-Evidenz enthalten ist.
  - `weekFinal` wird später erst dann abgeleitet, wenn alle für die jeweilige Woche relevanten Spiele kanonisch final sind.

- `nflverse.player-stats`
  - Saisonweise Weekly Player Stats.
  - Vollständige relevante NFL-Rohstatistik persistieren, nicht nur einen Provider-Fantasy-Point-Wert.
  - Dazu gehören insbesondere Passing, Rushing, Receiving, Kicking, Fumbles sowie `punt_return_yards`, `kickoff_return_yards` und Return-TDs.

- `nflverse.snap-counts`
  - Saisonweise Snap Counts über nflverse/PFR.
  - Fehlend, noch nicht veröffentlicht und echter numerischer Wert `0` müssen unterscheidbar bleiben.

- `nflverse.weekly-rosters`
  - Wöchentliche NFL-Teamzugehörigkeit und In-Season-Teamwechsel.

- `nflverse.rosters`
  - Saisonale Roster-/Profil-Evidenz.

### Sleeper

- `sleeper.players`
  - Persistierter `/players/nfl`-Snapshot als aktuelle Plattform-/Player-Quelle.
  - Temporär vorgesehene Injury-Felder: `injury_status`, `injury_start_date`, `practice_participation` sowie weitere verfügbare Sleeper-Statusfelder.
  - Sleeper kann damit Tank01 für den aktuellen Injury-Status voraussichtlich weitgehend ersetzen; ausführliche Tank01-Felder wie Return-Date oder Beschreibung gelten nicht als Pflicht, wenn keine gleichwertige Quelle vorhanden ist.
  - Sleeper-spezifische Player-, Status- und Depth-Chart-Felder bleiben als Plattformdaten getrennt von kanonischer NFL-Historie.

## Registry- und Sync-Ausbau

Die aktuelle Registry unterstützt primär eine feste URL pro Dataset. Für die saisonweise ausgelieferten nflverse-Quellen wird eine echte Partitionierungsunterstützung benötigt.

Geplanter Vertrag:

- Fixed Source
  - eine feste URL
  - ein validierter Raw-Snapshot
  - geeignet z. B. für Players, Schedule, Game-Finality und Sleeper Players

- Season-partitioned Source
  - URL-Template mit `{season}`
  - Raw-Dateien pro Saison
  - geeignet für Player Stats, Snap Counts, Rosters und Weekly Rosters

Der Sync soll mindestens unterstützen:

- aktuelle Saison im normalen Lauf;
- explizite Season-Auswahl für Backfills/Repair;
- prior-season freeze gemäß Lifecycle-Vertrag;
- `not-yet-available` als legitimen Zustand, wenn ein aktuelles saisonales Dataset upstream noch nicht veröffentlicht wurde;
- klare Trennung von `not-yet-available`, Fetch-Fehler, unerwartet leer/unvollständig und erfolgreich verfügbar.

## Zielstruktur der kanonischen Source-Daten

Richtungsweisend, noch kein App-Vertrag:

```text
source-data/
  providers/
    nflverse/
      schedules/
      game-finality/
      player-stats/
      snap-counts/
      rosters/
      weekly-rosters/
    sleeper/
      players/

  nfl/
    schedules/<season>.json
    game-finality/<season>.json
    player-stats/<season>/<week>.json
    snap-counts/<season>/<week>.json
    rosters/<season>.json
    weekly-rosters/<season>/<week>.json
    injuries/current.json
```

Alle Player-Verknüpfungen in der kanonischen NFL-Schicht laufen über `CanonicalPlayerID` und validierte Provider-Mappings. Display-Namen sind keine autoritativen Join-Keys.

## Fantasy-Scoring-Ziel

Fantasy Points sollen langfristig nicht als Provider-Wert kanonisch übernommen werden.

Zielregel:

1. Kanonische NFL Player Stats liefern die Rohfakten.
2. Sleeper League `scoring_settings` liefern die Liga-Regeln.
3. Fantasy Points werden daraus deterministisch innerhalb der eigenen Pipeline berechnet.
4. Provider-Fantasy-Point-Werte dürfen später als Validierungs-/Kontrollwerte dienen, aber nicht als kanonische Punktequelle.

Damit bleiben spätere Scoring-Änderungen wie Punkte für Return Yards ohne Wechsel der NFL-Statistikquelle möglich.

## Rolle von Tank01 nach der Migration

Tank01 soll wegen des begrenzten Requestbudgets möglichst nicht dauerhaft im normalen Datenpfad benötigt werden.

Zielbild nach erfolgreicher Source- und späterer Generator-Migration:

- kein primärer Schedule-/Finality-Provider;
- kein primärer Weekly-Stats-/Snap-Provider;
- kein primärer Fantasy-Point-Provider;
- möglichst kein primärer Injury-Provider, sofern Sleeper für den benötigten aktuellen Injury-Vertrag ausreicht;
- stattdessen optionaler Kontrollprovider/Failsafe, z. B. ein begrenzter periodischer Vergleich gegen kanonische Daten;
- ein Kontrollabgleich darf Abweichungen melden/auditieren, aber kanonische Daten nicht automatisch überschreiben.

## Abnahmekriterien vor Generator-Migration

Die App-Generatoren werden erst umgestellt, wenn für die benötigten Source-Datasets folgende Punkte erfüllt sind:

- Registry-/Lifecycle-Verträge sind vollständig und maschinenvalidiert.
- Raw-Provider-Daten werden persistent und fail-closed synchronisiert.
- Kanonische Materialisierung ist für die benötigten Datasets implementiert.
- Provider-/Game-/Season-/Week-Join-Invarianten sind getestet.
- Source-Availability-Zustände sind explizit modelliert.
- Audit-Ausgabe zeigt Coverage und Konflikte nachvollziehbar.
- Ein kompletter produktiver Source-Sync läuft erfolgreich.
- Ein unmittelbar folgender unveränderter Lauf ist semantisch ein No-op.
- Erst danach beginnt die separate Migration von `RequestGames.ps1`, `RequestPlayers.ps1` und weiteren App-Generatoren.
