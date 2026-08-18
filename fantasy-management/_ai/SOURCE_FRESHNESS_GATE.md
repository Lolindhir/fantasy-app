# Fantasy Operations Source Freshness Gate

## Zweck

Das Source Freshness Gate trennt zwei Fragen, die nicht vermischt werden dürfen:

1. **Wurde eine Quelle im aktuellen Morgenzyklus erfolgreich geprüft?**
2. **Hat sich ihr Inhalt gegenüber dem letzten gespeicherten Stand verändert?**

Ein erfolgreicher Abruf mit unverändertem Inhalt ist `fresh`. `--skip-unchanged` oder ein unveränderter App-Datensatz dürfen deshalb niemals als Fehler- oder Stale-Signal interpretiert werden.

## Verträge

Konfiguration:

`fantasy-management/automation/source-freshness-gate.json`

Erfolgs-Heartbeats der überwachten Morgenquellen:

`fantasy-management/sources/refresh-status/*.json`

Deterministischer Output:

`fantasy-management/generated/operations/source-freshness.json`

Builder und Schema:

- `fantasy-management/_ai/scripts/write_source_refresh_heartbeat.py`
- `fantasy-management/_ai/scripts/build_source_freshness_gate.py`
- `fantasy-management/_ai/schemas/source-freshness-gate.schema.json`

## Refresh-Bestätigung

League, Players, FantasyPros, FantasyCalc, Fantasy Football Calculator, FFToday, CBS Sports und Sleeper Trending liefern für den 07:00-Monitoring-Zyklus eine explizite erfolgreiche Refresh-Bestätigung. Der Heartbeat enthält mindestens:

- Source-ID;
- Workflow-ID/Name;
- `status = success`;
- tatsächlichen `checked_at`-Zeitpunkt;
- Europe/Berlin-Datum;
- Triggerart;
- `content_changed`;
- die vom Workflow verantworteten Source-Pfade.

Der Heartbeat wird erst nach erfolgreichem Fetch geschrieben. Scheitert ein Fetch, bleibt der letzte erfolgreiche Heartbeat unverändert. Das Freshness Gate darf daraus nur ableiten, dass der aktuelle Zyklus **nicht erfolgreich bestätigt** ist; ohne expliziten neuen Failure-Heartbeat darf es keinen konkreten technischen Fehlergrund erfinden.

`content_changed = false` bedeutet ausdrücklich nicht `stale`. Es bedeutet: Die Quelle wurde erfolgreich neu geprüft, aber der normalisierte Inhalt war unverändert.

## App-Quellen

`public/data/Timestamps.json` bleibt Source-Provenienz für die jeweiligen App-Datensätze, ist aber **nicht** die Bestätigung dafür, dass ein aktueller Fetch erfolgreich gelaufen ist. Ein Feld kann bei unverändertem Inhalt älter bleiben. Deshalb verwenden auch League und Players eigene Erfolgs-Heartbeats.

- `Players`: Der aktive 05:05-Europe/Berlin-Refresh schreibt nach erfolgreichem `RequestPlayers.ps1` den Morgen-Heartbeat. Die bestehenden zusätzlichen 08:00/12:00/18:00-UTC-Läufe bleiben erhalten, schreiben aber keinen zusätzlichen Morgen-Heartbeat. Ein manueller Players-Refresh schreibt einen Heartbeat.
- `League`: Der bestehende Zehn-Minuten-Refresh bleibt unverändert bestehen. Zusätzlich läuft DST-sicher ein eigener 06:35-Europe/Berlin-Refresh, der nach erfolgreichem `RequestLeague.ps1` den Morgen-Heartbeat schreibt. Dadurch entsteht **nicht alle zehn Minuten** ein reiner Heartbeat-Commit. Ein manueller League-Refresh schreibt ebenfalls einen Heartbeat.

League und Players sind Blocking Inputs, weil veraltete Ownership-/League- oder Player-/Injury-Grundlagen normale Monitoring-Aussagen verfälschen können.

## Morgenzyklus

Für die Quellen gilt im 07:00-Monitoring-Zyklus:

- der erfolgreiche Heartbeat muss zum aktuellen Europe/Berlin-Kalendertag gehören;
- er muss nach dem für die Quelle konfigurierten lokalen Mindestzeitpunkt liegen;
- der Heartbeat darf nicht älter als das konfigurierte Maximalalter sein.

Für die externen Ranking-/Projection-/Activity-Quellen und Players beginnt das relevante Fenster ab 05:00 Europe/Berlin. Der dedicated League-Heartbeat wird ab 06:00 akzeptiert und planmäßig um 06:35 erzeugt.

Damit zählt beispielsweise ein erfolgreicher unveränderter 05:32-FantasyCalc-Refresh als frisch, ein Heartbeat vom Vorabend oder vom Vortag aber nicht.

## Gate-Status

Jede Quelle erhält genau einen Status:

- `fresh`: aktuelle erfolgreiche Refresh-Bestätigung liegt vor;
- `stale`: ein vorhandener bestätigter Stand erfüllt das aktuelle Zeitfenster/Maximalalter nicht;
- `missing`: erforderlicher Heartbeat fehlt;
- `failed`: ein expliziter nicht erfolgreicher Heartbeat liegt vor, falls ein Workflow dies künftig schreibt;
- `invalid`: Heartbeat ist strukturell oder zeitlich nicht vertrauenswürdig.

Der Gesamtstatus ist:

- `ok`: alle erwarteten Quellen sind `fresh`;
- `degraded`: mindestens eine nicht-blockierende Quelle ist nicht frisch;
- `blocked`: mindestens eine als Blocking Input konfigurierte Quelle ist nicht frisch.

## Monitoring-Verhalten

`source-freshness.json -> monitoring` ist vor jeder Interpretation von `free-agent-movement-events.json` zu lesen.

### `decision = proceed`

Normales Monitoring ist zulässig. `event_count = 0` darf als belastbarer No-Event-Befund für die abgedeckten deterministischen Signalfamilien behandelt werden.

### `decision = proceed_degraded`

Monitoring darf nur für die weiterhin frisch unterstützten Bereiche laufen. Die in `affected_signal_families` genannten Bereiche sind ausdrücklich eingeschränkt.

Insbesondere gilt:

> Wenn `no_event_conclusion_allowed = false`, darf `free-agent-movement-events.json -> event_count = 0` nicht als „keine relevante Veränderung“ interpretiert werden.

Der korrekte Befund ist dann: kein Event aus dem aktuell materialisierten Stand, aber die Vollständigkeit des aktuellen Source-Zyklus ist nicht bestätigt.

### `decision = block`

Normales Daily Monitoring ist zu unterlassen. Statt Spielerbewegungen aus möglicherweise veralteten Ownership-/Player-Grundlagen zu interpretieren, soll ausschließlich die blockierende Datenqualitäts-/Freshness-Ursache sichtbar gemacht werden.

## 06:45-Konsolidierung und verspätete Quellen

Source- und Heartbeat-Commits im Morgenfenster werden durch den leichten Materializer-Trigger-Gate gebündelt. Um 06:45 erzeugt der Materializer `source-freshness.json` zusammen mit den übrigen Operations-Contracts.

Kommt ein erfolgreicher externer Source-Heartbeat erst nach 06:45, zählt sein Source-only-Push außerhalb des Batch-Fensters als sofortiger Materialisierungs-Trigger. Dadurch wird ein zuvor degradierter Freshness-Stand automatisch durch einen Catch-up-Build aktualisiert.

Der dedicated League-Heartbeat liegt planmäßig bereits vor der 06:45-Konsolidierung. Reguläre Zehn-Minuten-League-Refreshes erzeugen keinen separaten Heartbeat-Commit und damit keinen zusätzlichen reinen Freshness-Rebuild.

## Sicherheitsprinzipien

- Freshness ist kein Spielerwert und keine Empfehlung.
- Fehlende Frische darf nie als negatives Spielersignal interpretiert werden.
- Letzte gute Source-Daten bleiben erhalten, wenn ein Refresh nicht bestätigt ist.
- Das Gate erfindet keinen konkreten Fehlergrund aus einem fehlenden Heartbeat.
- Ein unveränderter, aber erfolgreich geprüfter Source-Stand bleibt vollständig nutzbar.
- Ein Content-Timestamp ist nicht automatisch ein Fetch-Erfolgsnachweis.
- `event_count = 0` ist nur dann ein belastbarer No-Event-Befund, wenn `no_event_conclusion_allowed = true`.
