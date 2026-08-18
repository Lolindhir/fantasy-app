# Fantasy Operations Source Freshness Gate

## Zweck

Das Source Freshness Gate trennt zwei Fragen, die nicht vermischt werden dürfen:

1. **Wurde eine Quelle im aktuellen Morgenzyklus erfolgreich geprüft?**
2. **Hat sich ihr Inhalt gegenüber dem letzten gespeicherten Stand verändert?**

Ein erfolgreicher Abruf mit unverändertem Inhalt ist `fresh`. `--skip-unchanged` darf deshalb niemals als Fehler- oder Stale-Signal interpretiert werden.

## Verträge

Konfiguration:

`fantasy-management/automation/source-freshness-gate.json`

Erfolgs-Heartbeats der externen Quellen:

`fantasy-management/sources/refresh-status/*.json`

Deterministischer Output:

`fantasy-management/generated/operations/source-freshness.json`

Builder und Schema:

- `fantasy-management/_ai/scripts/write_source_refresh_heartbeat.py`
- `fantasy-management/_ai/scripts/build_source_freshness_gate.py`
- `fantasy-management/_ai/schemas/source-freshness-gate.schema.json`

## Refresh-Bestätigung

FantasyPros, FantasyCalc, Fantasy Football Calculator, FFToday, CBS Sports und Sleeper Trending schreiben nach einem vollständig erfolgreichen Fetch/Validate einen kleinen Heartbeat. Der Heartbeat enthält mindestens:

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

## Interne App-Quellen

Für `League` und `Players` werden keine parallelen Heartbeats erzeugt. Hier nutzt das Gate die bestehenden kanonischen Zeitstempel in `public/data/Timestamps.json`:

- `League`: maximal 30 Minuten alt;
- `Players`: maximal 180 Minuten alt.

Diese beiden Quellen sind Blocking Inputs, weil veraltete Ownership-/League- oder Player-/Injury-Grundlagen normale Monitoring-Aussagen verfälschen können.

## Morgenzyklus

Für externe Quellen gilt im 07:00-Monitoring-Zyklus:

- der erfolgreiche Heartbeat muss zum aktuellen Europe/Berlin-Kalendertag gehören;
- er muss aus dem Morgenfenster ab 05:00 Europe/Berlin stammen;
- der Heartbeat darf nicht älter als das konfigurierte Maximalalter sein.

Damit zählt ein erfolgreicher unveränderter 05:32-FantasyCalc-Refresh als frisch, ein Heartbeat vom Vorabend oder vom Vortag aber nicht.

## Gate-Status

Jede Quelle erhält genau einen Status:

- `fresh`: aktuelle erfolgreiche Refresh-Bestätigung liegt vor;
- `stale`: ein vorhandener bestätigter Stand erfüllt das aktuelle Zeitfenster/Maximalalter nicht;
- `missing`: erforderlicher Zeitstempel oder Heartbeat fehlt;
- `failed`: ein expliziter nicht erfolgreicher Heartbeat liegt vor, falls ein Workflow dies künftig schreibt;
- `invalid`: Heartbeat oder Zeitstempel ist strukturell oder zeitlich nicht vertrauenswürdig.

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

Die externen Source- und Heartbeat-Commits werden zwischen 05:00 und 06:45 Europe/Berlin durch den leichten Materializer-Trigger-Gate gebündelt. Um 06:45 erzeugt der Materializer `source-freshness.json` zusammen mit den übrigen Operations-Contracts.

Kommt ein erfolgreicher Source-Heartbeat erst nach 06:45, zählt sein Source-only-Push außerhalb des Batch-Fensters als sofortiger Materialisierungs-Trigger. Dadurch wird der zuvor degradierte Freshness-Stand automatisch durch einen Catch-up-Build aktualisiert.

## Sicherheitsprinzipien

- Freshness ist kein Spielerwert und keine Empfehlung.
- Fehlende Frische darf nie als negatives Spielersignal interpretiert werden.
- Letzte gute Source-Daten bleiben erhalten, wenn ein Refresh nicht bestätigt ist.
- Das Gate erfindet keinen konkreten Fehlergrund aus einem fehlenden Heartbeat.
- Ein unveränderter, aber erfolgreich geprüfter Source-Stand bleibt vollständig nutzbar.
- `event_count = 0` ist nur dann ein belastbarer No-Event-Befund, wenn `no_event_conclusion_allowed = true`.
