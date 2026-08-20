# Fantasy Operations Source Freshness Gate

## Zweck

Das Source Freshness Gate trennt zwei Fragen, die nicht vermischt werden dürfen:

1. **Wurde eine überwachte Fantasy-Operations-Quelle im aktuellen Morgenzyklus erfolgreich geprüft?**
2. **Hat sich ihr Inhalt gegenüber dem letzten gespeicherten Stand verändert?**

Ein erfolgreicher Abruf mit unverändertem Inhalt ist `fresh`. `--skip-unchanged` darf deshalb niemals als Fehler- oder Stale-Signal interpretiert werden.

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

FantasyPros, FantasyCalc, Fantasy Football Calculator, FFToday, CBS Sports und Sleeper Trending liefern für den 07:00-Monitoring-Zyklus eine explizite erfolgreiche Refresh-Bestätigung. Der Heartbeat enthält mindestens:

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

## App-Quellen und Cross-Context-Grenze

`public/data/Players.json`, `public/data/League.json` und die weiteren unter `public/data/` veröffentlichten App-Datensätze sind kanonische App-Inputs. Fantasy Management konsumiert sie read-only und darf auf veröffentlichte Änderungen reagieren. **Players und League sind bewusst keine Quellen im Fantasy-Operations-Freshness-Gate.**

Die Workflows `APP • Data • Players` und `APP • Data • League` schreiben keine Fantasy-Management-Heartbeats. Ihre Generierung, Schedules und Veröffentlichung dürfen nicht von Fantasy-Management-Skripten, -Dateien oder -Runtime-State abhängen. Der League-App-Workflow behält ausschließlich seinen regulären Zehn-Minuten-Refresh und den manuellen App-Start; ein zusätzlicher Fantasy-Management-spezifischer 06:35-Refresh existiert nicht.

`public/data/Timestamps.json` bleibt App-Provenienz dafür, wann sich einzelne generierte App-Datensätze zuletzt inhaltlich verändert haben. Diese Zeitstempel sind kein Fantasy-Operations-Freshness-Gate und dürfen das Monitoring nicht als paralleler App-Health-Vertrag blockieren. Fantasy Operations verwendet den jeweils aktuell auf `main` veröffentlichten App-Stand als Input.

Falls künftig eine zusätzliche Fetch-Erfolgs- oder Freshness-Prüfung für App-Daten im Fantasy-Management-Kontext gewünscht wird, muss sie auf der Consumer-Seite unabhängig von der App-Produktionspipeline umgesetzt werden. Änderungen an App-Generatoren, App-Workflows, deren Scheduling oder Veröffentlichung benötigen eine ausdrückliche Freigabe der konkreten Cross-Context-Änderung.

## Morgenzyklus

Für die im Gate konfigurierten Heartbeat-Quellen gilt im 07:00-Monitoring-Zyklus:

- der erfolgreiche Heartbeat muss zum aktuellen Europe/Berlin-Kalendertag gehören;
- er muss nach dem für die Quelle konfigurierten lokalen Mindestzeitpunkt liegen;
- der Heartbeat darf nicht älter als das konfigurierte Maximalalter sein.

Für die externen Ranking-/Projection-/Activity-Quellen beginnt das relevante Fenster ab 05:00 Europe/Berlin.

Damit zählt beispielsweise ein erfolgreicher unveränderter 05:32-FantasyCalc-Refresh als frisch, ein Heartbeat vom Vorabend oder vom Vortag aber nicht.

## Gate-Status

Jede konfigurierte Quelle erhält genau einen Status:

- `fresh`: aktuelle erfolgreiche Refresh-Bestätigung liegt vor;
- `stale`: ein vorhandener bestätigter Stand erfüllt das aktuelle Zeitfenster/Maximalalter nicht;
- `missing`: erforderlicher Heartbeat fehlt;
- `failed`: ein expliziter nicht erfolgreicher Heartbeat liegt vor, falls ein Workflow dies künftig schreibt;
- `invalid`: Heartbeat ist strukturell oder zeitlich nicht vertrauenswürdig.

Der Gesamtstatus ist:

- `ok`: alle erwarteten Quellen sind `fresh`;
- `degraded`: mindestens eine nicht-blockierende Quelle ist nicht frisch;
- `blocked`: mindestens eine als Blocking Input konfigurierte Quelle ist nicht frisch.

Im aktuellen Produktionsvertrag sind alle sechs überwachten Fantasy-Operations-Quellen nicht-blockierend. Ein fehlender oder veralteter externer Source-Heartbeat führt deshalb zu `degraded`, kann aber weiterhin `no_event_conclusion_allowed = false` setzen. App-Daten wie League und Players werden nicht über diesen Mechanismus zu Blocking Inputs erklärt.

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

Der Builder unterstützt weiterhin Blocking Inputs für zukünftige ausdrücklich konfigurierte Quellen. Existiert ein solcher nicht frischer Blocking Input, ist normales Daily Monitoring zu unterlassen und ausschließlich die blockierende Datenqualitäts-/Freshness-Ursache sichtbar zu machen.

League und Players gehören nicht zu diesen blockierenden Freshness-Grundlagen; ihre veröffentlichten App-Datensätze bleiben read-only konsumierte Inputs.

## Unabhängige Morgen-Materialisierung und 06:45-Catch-up

Jeder erfolgreiche relevante Source- oder Success-Heartbeat-Commit auf `main` darf unmittelbar eine vollständige Fantasy-Operations-Materialisierung anstoßen. Zusätzlich bleiben relevante Änderungen an kanonischen App-Daten wie `League.json`, `Players.json` und `Timestamps.json` normale read-only Input-Trigger für die Materialisierung, ohne dass Fantasy Management deren Erzeugungsworkflow verändert. Für diese Entscheidung gibt es keinen Unterschied zwischen dem Morgenfenster und anderen Tageszeiten.

Der DST-sichere 06:45-Europe/Berlin-Lauf bleibt ausschließlich als zusätzlicher Catch-up bestehen. Er ist weder die einzige reguläre Morgen-Materialisierung noch ein Readiness-Beweis für das 07:00-Monitoring. Korrektheit darf nicht davon abhängen, dass GitHub Actions diesen Schedule pünktlich startet oder vor 07:00 beendet. Entsprechend heißt der Konfigurationswert im Freshness-Vertrag `morning_cycle.catch_up_time`; die frühere Bezeichnung `consolidation_time` ist entfernt.

Kommt ein erfolgreicher externer Source- oder Heartbeat-Commit verspätet, löst auch er unmittelbar eine neue Materialisierung aus. Ebenso können echte relevante App-Datenänderungen unmittelbar materialisieren. Ein zuvor degradierter Freshness-Stand kann dadurch automatisch auf dem aktuellen `main` neu aufgebaut werden.

Für den 07:00-Consumer gilt ausschließlich der tatsächlich veröffentlichte kanonische Operations-State. Der Consumer liest `source-freshness.json` und beachtet `decision`, `no_event_conclusion_allowed`, `blocking_source_ids`, nicht frische Quellen und `affected_signal_families`; aus der Uhrzeit oder dem 06:45-Schedule darf keine Readiness abgeleitet werden.

## Materialisierungs-Observability

`FM • Materialize • Operations Inputs` schreibt bei jedem ausgeführten Materializer-Lauf eine kompakte Laufzeitübersicht in das GitHub-Actions-Run-Summary. Für Push-Trigger werden dabei getrennt ausgewiesen:

- Trigger-/Source-Commit-Zeitpunkt → Start des Materializer-Jobs;
- Start des Materializer-Jobs → erfolgreicher Publish des kanonischen Operations-State;
- Trigger-/Source-Commit-Zeitpunkt → erfolgreicher Publish insgesamt.

Zusätzlich werden Trigger-Grund, Trigger-Commit, veröffentlichter Materializer-Commit und die absoluten Zeitpunkte ausgewiesen. Bei Schedule- oder Manual-Runs ist eine Source-Commit-Latenz nicht definiert und bleibt ausdrücklich `n/a`.

Diese Werte sind **nur Observability**. Sie werden nicht in `source-freshness.json` persistiert, verändern weder `decision` noch `no_event_conclusion_allowed` und dürfen niemals als Ersatz für Success-Heartbeats oder das Freshness Gate verwendet werden.

## Sicherheitsprinzipien

- Freshness ist kein Spielerwert und keine Empfehlung.
- Fehlende Frische darf nie als negatives Spielersignal interpretiert werden.
- Letzte gute Source-Daten bleiben erhalten, wenn ein Refresh nicht bestätigt ist.
- Das Gate erfindet keinen konkreten Fehlergrund aus einem fehlenden Heartbeat.
- Ein unveränderter, aber erfolgreich geprüfter Source-Stand bleibt vollständig nutzbar.
- Ein Content-Timestamp ist nicht automatisch ein Fetch-Erfolgsnachweis.
- Fantasy Management darf für eigene Freshness-Zwecke keine App-Produktionspipeline zur Laufzeitabhängigkeit machen.
- `event_count = 0` ist nur dann ein belastbarer No-Event-Befund, wenn `no_event_conclusion_allowed = true`.
