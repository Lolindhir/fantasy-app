# Fantasy Management Automation

Dieser Ordner ist die deklarative Steuerungsebene für wiederkehrende Fantasy-Management-Automationen.

Geplante ChatGPT-Tasks oder spätere technische Runner wecken das System nur auf. Welche Jobs fällig sind, welche Daten sie benötigen, was sie schreiben dürfen und wann Robert benachrichtigt wird, wird im Repository definiert.

## Neutraler Teambezug

Der maschinenlesbare Begriff für das Team, auf dessen Interessen die Automation optimiert, lautet `managed_team`.

- Das Team wird über die stabile ID aus `public/data/League.json` aufgelöst.
- Der aktuelle Franchise-Name ist nur ein dynamischer Anzeigename.
- Eine Umbenennung verändert keine Job-IDs, Pfade, States, Profile oder Analysen.
- `own_team` wäre aus Agent-Sicht mehrdeutig; `master_team` ist semantisch unklar.

## Zielbild

```text
Geplanter Task / Runner-Wakeup
  -> Repo-Regeln und runner-config.json lesen
  -> managed_team stabil auflösen
  -> aktivierte Jobs entdecken
  -> Trigger, Datenbereitschaft und Idempotenz prüfen
  -> Target Sets und Observation Profiles anwenden
  -> nur fällige Jobs ausführen
  -> materielle Bundles atomar veröffentlichen
  -> nach Job-Regel benachrichtigen
```

## Dateien und Verantwortlichkeiten

- `AGENTS.md` enthält verbindliche Runner-Regeln.
- `runner-config.json` enthält globale Runner-Regeln und `managed_team`.
- `jobs/*.json` enthält deklarative Jobdefinitionen.
- `target-sets/*.json` enthält manuelle Targets und dynamische Selektoren.
- `profiles/*.json` enthält Signale, Quellenregeln und Kriterien.
- `workflows/*.md` beschreibt die fachliche Ausführung und Veröffentlichung.
- `state/{job-id}.json` enthält den veränderlichen Zustand eines Jobs.
- `fantasy-management/analyses/` enthält fertige Analyse-Outputs.
- `public/data/` bleibt Source of Truth für aktuelle Liga- und App-Daten.

Ein laufender Runner darf State und freigegebene Outputs verändern, aber nicht seine Jobs, Target Sets, Profile, Workflows oder generierte App-Daten.

## Generisches Observation Framework

Der Job `entity-observation` trennt:

1. **Job** – Trigger, Abhängigkeiten, Schreib- und Benachrichtigungsregeln.
2. **Target Set** – manuelle Listen und dynamische Selektoren.
3. **Observation Profile** – wiederverwendbare Signale und Quellenanforderungen.
4. **Criterion** – strukturierte Regeln für Materialität und Klassifikation.
5. **Observation Event** – Beobachtung, Interpretation und Handlungseffekt.

Der erste Target Set ist `player-role-watch`. Die ersten Profile sind:

- `role-opportunity`
- `market-movement`

Tank Bigsby ist der erste produktiv vorbereitete Target. Seine geprüfte Baseline ist im State gespeichert.

## Erweiterbarkeit

Weitere Target Sets können denselben Runner verwenden:

```text
managed-roster-health
rookie-stashes
waiver-candidates
trade-targets
sell-high-candidates
team-backfields
```

Weitere Profile können unabhängig ergänzt werden:

```text
injury-status
roster-security
contract-situation
ownership-availability
lineup-usage
source-disagreement
```

Target Sets unterstützen manuelle Targets, Selektoren, Mischformen, mehrere Profile, Kriterien-Overrides, Aktivitätsfenster und unterschiedliche Entscheidungskontexte.

## Externer Zeitplan und Repo-Trigger

Der externe Task legt nur die Wakeup-Zeit fest. Die fachliche Fälligkeit bleibt im Repository.

Unterstützte Triggerklassen:

- `interval`
- `calendar`
- `league_week_finalized`
- `source_changed`
- `deadline_offset`
- `manual`

Ein Task kann täglich oder häufiger aufwachen, ohne jeden Job auszuführen.

## Runner-Modi

- `read_only`: nur lesen und bewerten.
- `proposal`: konkrete Änderungen vorschlagen.
- `write_enabled`: ausschließlich innerhalb des freigegebenen Write Scopes schreiben.

Der kontrollierte Read-only-Lauf, die Baseline und der atomare Schreibtest wurden erfolgreich abgeschlossen. Der Produktionsrunner ist deshalb für den ersten Observation Job in `write_enabled` vorbereitet.

## Baseline, Materialität und Idempotenz

Die erste erfolgreiche Prüfung erstellt eine stille Baseline.

Weitere Läufe vergleichen:

```text
Target + Profil + Material-State-Hash
```

Nur ein nach Profilkriterien materieller Unterschied erzeugt ein Observation Event. Zeitstempel, Formulierungsänderungen oder erneut gefundene identische Quellen erzeugen keinen Event.

Jeder Event trennt:

```text
Observation
Interpretation
Decision Effect
```

## Atomare Veröffentlichung

Für ein materielles Observation Event gehören drei Artefakte zusammen:

```text
aktualisierter State
+ JSON-Event
+ Markdown-Event
```

Sie werden in einem gemeinsamen Git-Tree und einem einzigen Commit veröffentlicht. Der Commit muss direkt auf dem zuvor gelesenen `main`-Stand aufbauen.

Vor der Veröffentlichung werden festgehalten:

- erwartete Parent-Commit-SHA;
- erwartete Blob-SHA der State-Datei.

Hat sich Branch oder State zwischen Lesen und Schreiben verändert, wird nicht überschrieben und nicht erzwungen. Der vorbereitete Write wird verworfen und auf aktuellem Stand neu bewertet.

Keine materielle Änderung bedeutet:

- kein Event;
- kein State-Heartbeat;
- kein Commit;
- keine Benachrichtigung.

Details stehen in `workflows/atomic-publication.md`.

## State-Regeln

- Genau eine State-Datei pro Job.
- Zustand pro Target und Profil.
- Profile dürfen unabhängig erfolgreich sein oder fehlschlagen.
- Revision nur bei echter State-Änderung erhöhen.
- Keine Heartbeat-Commits.
- Fachlich relevante Historie gehört in Observation Events.
- Letzten guten Material-State bei Quellenfehlern behalten.

## Benachrichtigungen

Der erste produktive Job nutzt `material_changes_only` mit Mindestschwere `medium`.

Eine Meldung erfolgt erst nach erfolgreicher Repo-Veröffentlichung und nennt Evidenz, vorherigen Zustand, Interpretation, Auswirkungen, Empfehlung, Konfidenz und ungelöste Konflikte.

## Schreibgrenzen

- nur Pfade aus `execution.write_scope`;
- keine Änderungen unter `public/data/`;
- keine Laufzeitänderungen an Jobs, Target Sets, Profilen oder Workflows;
- keine GitHub-Actions-Dateien ohne ausdrückliche Zustimmung;
- keine No-op-Commits;
- kein Force-Push durch den Runner.

## Validierung

```bash
python fantasy-management/_ai/scripts/validate_automation.py

python -m unittest discover \
  -s fantasy-management/_ai/scripts/tests \
  -p "test_validate_automation.py" \
  -v
```

Zusätzlich werden Observation Profiles über den profilspezifischen Validator geprüft.

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
