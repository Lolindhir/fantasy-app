# Fantasy Management Automation

Dieser Ordner ist die deklarative Steuerungsebene für wiederkehrende Fantasy-Management-Automationen.

Die geplanten ChatGPT-Tasks oder spätere technische Runner wecken das System nur auf. Welche Jobs bei einem Lauf fällig sind, welche Daten sie benötigen, was sie schreiben dürfen und wann Robert benachrichtigt wird, wird im Repository definiert.

## Zielbild

```text
Geplanter Task / Runner-Wakeup
  -> Root-AGENTS.md und Fantasy-Management-Regeln lesen
  -> runner-config.json laden
  -> aktivierte Jobs entdecken
  -> fachliche Trigger und Datenbereitschaft prüfen
  -> nur fällige Jobs ausführen
  -> Ergebnis und Job-State getrennt speichern
  -> nach Job-Regel benachrichtigen
```

## Dateien und Verantwortlichkeiten

- `runner-config.json` enthält globale Runner-Regeln, aber keinen externen Zeitplan.
- `jobs/*.json` enthält deklarative Jobdefinitionen.
- `state/{job-id}.json` enthält ausschließlich den veränderlichen Zustand eines einzelnen Jobs.
- Fertige Analysen werden unter `fantasy-management/analyses/` gespeichert.
- Aktuelle Liga-, Roster-, Draft-, Transaktions- und Spieler-Daten bleiben unter `public/data/`.

Jobdefinition und State dürfen nicht vermischt werden:

- Eine Jobdefinition beschreibt dauerhaft, was geprüft und erzeugt werden soll.
- Ein State beschreibt, was bereits geprüft oder verarbeitet wurde.
- Ein Runner darf den State verändern, aber keine Jobdefinition eigenmächtig umschreiben.

## Externer Zeitplan und Repo-Trigger

Die Ausführungszeit eines geplanten Tasks liegt außerhalb des Repositories. Die Repo-Konfiguration kann einen Task nicht selbst starten.

Das Repository steuert stattdessen die fachliche Fälligkeit. Unterstützte Triggerklassen sind:

- `interval`: frühestens nach einem Mindestabstand erneut prüfen.
- `calendar`: nur an definierten Wochentagen und nach einer lokalen Uhrzeit prüfen.
- `league_week_finalized`: ausführen, wenn ein neuer vollständig aktualisierter Spieltag vorliegt.
- `source_changed`: ausführen, wenn sich definierte Eingaben verändert haben.
- `deadline_offset`: zu festgelegten Abständen vor oder nach einer Deadline ausführen.
- `manual`: nur nach ausdrücklichem Aufruf ausführen.

Ein Task kann daher täglich oder häufiger aufwachen, ohne jeden Job bei jedem Lauf auszuführen.

## Runner-Modi

- `read_only`: Repo und externe Quellen lesen; keine State- oder Analyse-Dateien verändern.
- `proposal`: Änderungen strukturiert vorschlagen, aber nicht selbst schreiben.
- `write_enabled`: nur innerhalb der in Job und Runner freigegebenen Pfade schreiben.

Das Grundmodell startet in `read_only`. Schreibrechte werden erst nach einem bewussten, erfolgreichen Test aktiviert.

## Datenbereitschaft und Idempotenz

Vor jeder Ausführung müssen alle erforderlichen Abhängigkeiten geprüft werden. Fehlende oder veraltete Daten führen nicht zu einer Teilanalyse, sondern abhängig von der Jobregel zu `pending`, `skipped` oder einem Fehlerzustand.

Jeder Job muss einen fachlichen Idempotenzschlüssel erzeugen, zum Beispiel:

```text
2026-week-01
2026-07-22-tank-bigsby
2026-trade-deadline-minus-14-days
```

Ein bereits erfolgreich verarbeiteter Schlüssel darf nicht noch einmal dieselbe Analyse erzeugen.

## State-Regeln

- Genau eine State-Datei pro Job.
- Keine globale Datei mit allen Jobzuständen.
- Keine täglichen Heartbeat-Commits ohne Zustandsänderung.
- State nur bei Statuswechsel, materieller Änderung, erfolgreichem Output oder verändertem Fehlerzustand schreiben.
- `recent_events` ist ein kurzer technischer Verlauf und kein dauerhaftes Analysearchiv.
- Fachlich relevante Ergebnisse gehören in datierte Analysen, nicht in den State.

## Benachrichtigungsmodi

- `always_on_completion`: nach jedem erfolgreichen fachlichen Abschluss melden.
- `material_changes_only`: nur bei relevanter Veränderung melden.
- `critical_only`: nur kritische Ereignisse melden.
- `silent_repo_output`: Ergebnis nur ins Repo schreiben.
- `summary_only`: mehrere kleine Ereignisse gebündelt melden.

Jede Meldung soll die Veränderung, Evidenz, vorherigen Zustand, Mighty-Giants-Auswirkung, Handlungsempfehlung und Konfidenz enthalten, soweit diese Punkte für den Job relevant sind.

## Schreibgrenzen

Ein Job darf nur in den unter `execution.write_scope` angegebenen Bereichen schreiben. Zusätzlich gelten die globalen Repository-Regeln:

- Keine Änderung an `public/data/` durch Fantasy-Management-Analysen.
- Keine Änderung an Jobdefinitionen durch einen laufenden Runner.
- Keine GitHub-Actions-Workflow-Datei ohne ausdrückliche Zustimmung.
- Dynamische externe Werte nicht als dauerhafte Wahrheit speichern.
- Gespeicherte Analysen sind historischer Kontext und müssen bei neuen Entscheidungen mit aktuellen Daten abgeglichen werden.

## Startkonfiguration

`jobs/weekly-league-review.json` ist als vollständiges, aber deaktiviertes Referenzbeispiel enthalten. Es zeigt:

- einen fachlichen Ereignistrigger,
- Datenabhängigkeiten,
- einen Idempotenzschlüssel,
- getrennte Markdown-/JSON-Ausgaben,
- einen eigenen State,
- eine Benachrichtigung nach erfolgreichem Abschluss.

Der Job bleibt deaktiviert, bis der konkrete Spieltagsanalyse-Workflow und die Ausgabestruktur umgesetzt und geprüft sind.

## Lesereihenfolge für einen Runner

1. `/AGENTS.md`
2. `fantasy-management/AGENTS.md`
3. relevante Dateien unter `fantasy-management/_ai/`
4. diese README
5. `runner-config.json`
6. aktivierte Jobdefinitionen
7. jeweilige Job-States
8. benötigte aktuelle Repo-Daten und externe Quellen

Die Schemata liegen unter `fantasy-management/_ai/schemas/` und sind in `_ai/schema-list.json` registriert.
