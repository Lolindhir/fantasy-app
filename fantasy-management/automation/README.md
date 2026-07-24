# Fantasy Management Automation

Dieser Ordner ist die deklarative Steuerungsebene für wiederkehrende Fantasy-Management-Automationen.

Geplante ChatGPT-Tasks oder spätere technische Runner wecken das System nur auf. Welche Jobs bei einem Lauf fällig sind, welche Daten sie benötigen, was sie schreiben dürfen und wann Robert benachrichtigt wird, wird im Repository definiert.

## Neutraler Teambezug

Der maschinenlesbare Begriff für das Team, auf dessen Interessen die Automation optimiert, lautet `managed_team`.

Warum dieser Begriff:

- `managed_team` beschreibt eindeutig die operative Beziehung.
- `own_team` wäre aus Sicht verschiedener Agents oder Nutzer mehrdeutig.
- `master_team` ist kein üblicher Fantasy-Begriff und semantisch unklar.
- Der aktuelle Franchise-Name ist nur ein dynamischer Anzeigename.

Das verwaltete Team wird in `runner-config.json` über die stabile Team-ID aus `public/data/League.json` aufgelöst. Eine spätere Umbenennung der Franchise verändert deshalb keine Job-IDs, Pfade, States, Profile oder Analysen.

## Zielbild

```text
Geplanter Task / Runner-Wakeup
  -> Root-AGENTS.md und Fantasy-Management-Regeln lesen
  -> runner-config.json und managed_team laden
  -> aktivierte Jobs entdecken
  -> fachliche Trigger und Datenbereitschaft prüfen
  -> Target Sets auflösen
  -> Observation Profiles anwenden
  -> Kriterien und Materialität bewerten
  -> nur fällige Jobs ausführen
  -> Ergebnis und Job-State getrennt speichern
  -> nach Job-Regel benachrichtigen
```

## Dateien und Verantwortlichkeiten

- `AGENTS.md` enthält die verbindlichen Runner-Regeln für Agents und geplante Tasks.
- `runner-config.json` enthält globale Runner-Regeln und die stabile Referenz auf `managed_team`, aber keinen externen Zeitplan.
- `jobs/*.json` enthält deklarative Jobdefinitionen.
- `target-sets/*.json` enthält manuelle Zielobjekte und später dynamische Selektoren.
- `profiles/*.json` enthält wiederverwendbare Beobachtungssignale, Quellenregeln und Kriterien.
- `workflows/*.md` beschreibt die fachliche Ausführung.
- `state/{job-id}.json` enthält ausschließlich den veränderlichen Zustand eines einzelnen Jobs.
- Fertige Analysen werden unter `fantasy-management/analyses/` gespeichert.
- Aktuelle Liga-, Roster-, Draft-, Transaktions- und Spieler-Daten bleiben unter `public/data/`.

Jobdefinition, Konfiguration und State dürfen nicht vermischt werden:

- Eine Jobdefinition beschreibt dauerhaft, wann und wie geprüft wird.
- Ein Target Set beschreibt, was beobachtet wird.
- Ein Profil beschreibt, welche Signale und Kriterien gelten.
- Ein State beschreibt, was bereits geprüft oder verarbeitet wurde.
- Ein Runner darf State und freigegebene Outputs verändern, aber nicht Jobdefinitionen, Target Sets oder Profile.

## Generisches Observation Framework

Der erste echte Automationsbaustein ist kein fest verdrahteter Player Watch, sondern ein generischer Job `entity-observation`.

Er trennt fünf Ebenen:

1. **Job** – Trigger, Abhängigkeiten, Schreib- und Benachrichtigungsregeln.
2. **Target Set** – manuelle Listen und spätere dynamische Selektoren.
3. **Observation Profile** – wiederverwendbare Signale und Quellenanforderungen.
4. **Criterion** – strukturierte Regeln für Materialität und Klassifikation.
5. **Observation Event** – Beobachtung, Interpretation und Handlungseffekt.

Der erste Target Set ist `player-role-watch`. Die ersten Profile sind:

- `role-opportunity`
- `market-movement`

Tank Bigsby dient als erster konfigurierter Testfall. Der generische Job bleibt deaktiviert und der Runner bleibt `read_only`, bis ein manueller Test erfolgreich war.

## Erweiterbarkeit

Weitere Listen können ohne neuen Runner entstehen, zum Beispiel:

```text
target-sets/
  player-role-watch.json
  managed-roster-health.json
  rookie-stashes.json
  waiver-candidates.json
  trade-targets.json
  sell-high-candidates.json
  team-backfields.json
```

Weitere Profile können unabhängig ergänzt werden:

```text
profiles/
  injury-status.json
  roster-security.json
  contract-situation.json
  ownership-availability.json
  lineup-usage.json
  source-disagreement.json
```

Target Sets unterstützen:

- manuelle Targets;
- dynamische Selektoren;
- Mischformen;
- mehrere Profile pro Target;
- Kriterien-Overrides pro Target;
- zeitliche Aktivitätsfenster;
- unterschiedliche Entscheidungskontexte.

Entity-Typen sind nicht auf Spieler begrenzt. Später möglich sind unter anderem `nfl_team`, `position_group`, `backfield`, `fantasy_team`, `draft_pick`, `ranking_source`, `deadline` oder `league_rule`.

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

Das Grundmodell bleibt in `read_only`. Schreibrechte werden erst nach einem bewussten, erfolgreichen Test aktiviert.

## Baseline, Materialität und Idempotenz

Die erste erfolgreiche Prüfung eines Targets erstellt eine Baseline. Sie löst standardmäßig keine Nachricht aus.

Weitere Läufe vergleichen normalisierte materielle Zustände:

```text
Target + Profil + Material-State-Hash
```

Nur ein nach Profilkriterien materieller Unterschied erzeugt ein Observation Event. Zeitstempel, Formulierungsänderungen oder erneut gefundene identische Quellen dürfen keinen neuen Event auslösen.

Jeder Event trennt:

```text
Observation = Was hat sich in Daten und Evidenz verändert?
Interpretation = Was bedeutet diese Veränderung wahrscheinlich?
Decision Effect = Was ändert sich für managed_team, Liga oder einen anderen Kontext?
```

## State-Regeln

- Genau eine State-Datei pro Job.
- Zielzustand wird beim Observation Job pro Target und Profil gespeichert.
- Unterschiedliche Profile dürfen unabhängig erfolgreich sein oder fehlschlagen.
- Keine täglichen Heartbeat-Commits ohne Zustandsänderung.
- State nur bei Statuswechsel, materieller Änderung, erfolgreichem Output oder verändertem Fehlerzustand schreiben.
- Fachlich relevante Historie gehört in datierte Observation Events, nicht in den State.

## Benachrichtigungsmodi

- `always_on_completion`: nach jedem erfolgreichen fachlichen Abschluss melden.
- `material_changes_only`: nur bei relevanter Veränderung melden.
- `critical_only`: nur kritische Ereignisse melden.
- `silent_repo_output`: Ergebnis nur ins Repo schreiben.
- `summary_only`: mehrere kleine Ereignisse gebündelt melden.

Eine materielle Meldung nennt Evidenz, vorherigen Zustand, Interpretation, Auswirkungen, Empfehlung, Konfidenz und ungelöste Quellenkonflikte.

## Schreibgrenzen

Ein Job darf nur in den unter `execution.write_scope` angegebenen Bereichen schreiben. Zusätzlich gelten:

- keine Änderung an `public/data/` durch Fantasy-Management-Analysen;
- keine Änderung an Jobdefinitionen, Target Sets oder Profilen durch einen laufenden Runner;
- keine GitHub-Actions-Workflow-Datei ohne ausdrückliche Zustimmung;
- keine tägliche Commit-Flut ohne fachliche Änderung;
- dynamische externe Werte bleiben datierter Kontext und keine dauerhafte Wahrheit.

## Validierung

```bash
python fantasy-management/_ai/scripts/validate_automation.py

python -m unittest discover \
  -s fantasy-management/_ai/scripts/tests \
  -p "test_validate_automation.py" \
  -v
```

Der Validator prüft unter anderem:

- JSON-Schemas;
- Job-/State-Paare;
- Konfigurationsreferenzen;
- eindeutige Profile und Target Sets;
- Profilanwendbarkeit auf Entity-Typen;
- Target-ID-Kollisionen;
- erlaubte Schreibpfade;
- stabile `managed_team`-Konfiguration;
- fehlende oder unbekannte Profilverweise;
- unerwünschte Franchise-Namen in der Automation.

## Lesereihenfolge für einen Runner

1. `/AGENTS.md`
2. `fantasy-management/AGENTS.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
4. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
5. `fantasy-management/automation/AGENTS.md`
6. diese README
7. `runner-config.json`
8. aktivierte Jobdefinitionen
9. deren Konfigurationsreferenzen
10. jeweilige Job-States
11. benötigte aktuelle Repo-Daten und externe Quellen

Die Schemata liegen unter `fantasy-management/_ai/schemas/` und sind in `_ai/schema-list.json` registriert.
