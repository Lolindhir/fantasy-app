# Fantasy Management Automation

Dieser Ordner enthält die deklarativen Verträge und den historischen Runner-Unterbau für wiederkehrende Fantasy-Management-Automationen.

Für den aktuellen produktiven Fantasy-Operations-Betrieb ist `fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md` die übergeordnete Architekturregel. Bei Widersprüchen zwischen älteren Runner-Dokumenten und dieser Architektur gilt die aktuelle Architecture.

## Aktueller Produktionsmodus

Seit der provider-neutralen Migration läuft das geplante Fantasy-Operations-Monitoring **read-only**:

```text
Source-Refreshes
→ deterministische Materialisierung
→ geplantes read-only Monitoring
→ frische qualitative Recherche
→ Vergleich mit bestätigten Baselines
→ nur bei materieller Änderung Benachrichtigung / Write-Vorschlag
→ nach ausdrücklicher Freigabe interaktiver persistenter Write
```

Der aktuelle `runner-config.json` steht auf `read_only`. Der frühere autonome Observation-Bootstrap ist deaktiviert.

Damit gilt:

- Ein geplanter Monitoring-Lauf schreibt keinen State und keine Analyse-Events.
- Fehlende Baselines lösen keinen autonomen Bootstrap oder Backfill aus.
- Dauerhafte Observation-Baselines werden erst nach ausdrücklicher Freigabe interaktiv gespeichert.
- Für qualitative Entity-Observation-Baselines ist `state/entity-observation.json` der kanonische persistente State.
- Die alten Runner-, Bootstrap- und Publication-Dokumente bleiben als historische und technische Verträge erhalten, soweit die aktuelle Architecture sie nicht ausdrücklich ersetzt.

## Neutraler Teambezug

Der maschinenlesbare Begriff für das Team, auf dessen Interessen die Automation optimiert, lautet `managed_team`.

- Das Team wird über die stabile ID aus `public/data/League.json` aufgelöst.
- Der aktuelle Franchise-Name ist nur ein dynamischer Anzeigename.
- Eine Umbenennung verändert keine Job-IDs, Pfade, States, Profile oder Analysen.
- `own_team` wäre aus Agent-Sicht mehrdeutig; `master_team` ist semantisch unklar.

## Dateien und Verantwortlichkeiten

- `AGENTS.md` enthält verbindliche Agent- und Runner-Regeln.
- `runner-config.json` enthält globale Runner-Regeln und `managed_team`.
- `jobs/*.json` enthält deklarative Jobdefinitionen des generischen Automation-Frameworks.
- `target-sets/*.json` enthält manuelle Targets und dynamische Selektoren.
- `profiles/*.json` enthält Signale, Quellenregeln und Materialitätskriterien.
- `workflows/*.md` dokumentiert fachliche Ausführung, Normalisierung und historische Publication-Mechaniken.
- `state/{job-id}.json` enthält veränderlichen persistenten Zustand eines Jobs.
- `fantasy-management/generated/operations/` enthält ausschließlich reproduzierbare, deterministische Operations-Read-Models.
- `fantasy-management/analyses/` enthält gespeicherte Analyse-Outputs.
- `public/data/` bleibt Source of Truth für aktuelle Liga- und App-Daten.

## Generisches Observation-Modell

Der bestehende `entity-observation`-Vertrag trennt weiterhin fünf Ebenen:

1. **Job** – Trigger, Abhängigkeiten, erlaubte Outputs und Benachrichtigungsregeln.
2. **Target Set** – welche Entitäten beobachtet werden.
3. **Observation Profile** – welche Signale, Normalisierung und Quellenstandards gelten.
4. **Criterion** – wann eine Veränderung materiell ist und wie sie klassifiziert wird.
5. **Observation State / Event** – gespeicherter Vergleichszustand beziehungsweise historischer Event-Vertrag.

Diese Trennung bleibt sinnvoll und wird für bestätigte Baselines weiterverwendet. Was nicht mehr produktiv verwendet wird, ist der **autonome schreibende Runner-Pfad**.

## Runner-Modi

Die historischen Runner-Modi bleiben im Schema definiert:

- `read_only`: nur lesen und bewerten;
- `proposal`: konkrete Änderungen vorschlagen;
- `write_enabled`: innerhalb des konfigurierten Write Scopes schreiben.

Der aktuelle produktive Operations-Betrieb verwendet `read_only`. Eine frühere erfolgreiche Aktivierung von `write_enabled` im Juli 2026 wurde mit der provider-neutralen Migration im August bewusst zurückgenommen.

## Baseline, Materialität und Idempotenz

Eine persistierte qualitative Baseline wird pro Target und Profil als normalisierter `material_state` mit deterministischem SHA-256-Hash gespeichert.

Für neue oder aktualisierte bestätigte Baselines gelten insbesondere:

- nur Profil-`output_fields` und ausdrücklich erlaubte strukturierte Support-Felder verwenden;
- Zeitstempel, URLs und reine Formulierungsunterschiede nicht in den Material-State-Hash aufnehmen;
- vorherige gute Zustände bei Quellenfehlern erhalten;
- keine No-op- oder Heartbeat-Writes;
- `revision` genau einmal pro vollständiger realer State-Änderung erhöhen;
- vollständigen Replacement-State gegen Schema und Cross-File-Regeln validieren.

Die erste Beobachtung allein ist keine materielle Benachrichtigung. Das geplante Monitoring kann für seinen Lauf intern einen ersten Vergleichszustand bilden; dauerhafte Speicherung benötigt weiterhin eine Freigabe.

## Human-approved State-Persistenz

Der kanonische qualitative Observation-State ist:

```text
fantasy-management/automation/state/entity-observation.json
```

Nach ausdrücklicher Freigabe wird ein Write interaktiv vorbereitet und veröffentlicht. Dabei gelten die Sicherheitsprinzipien des früheren atomaren Publication-Designs weiter:

- aktuellen Branch-Parent pinnen;
- aktuellen State-Blob pinnen;
- vollständigen State erzeugen;
- Schema und Cross-File-Regeln validieren;
- nur non-forced fast-forward publizieren;
- bei Konflikt verwerfen und auf aktuellem Stand neu berechnen.

Ein genehmigter Baseline-Write ist kein erfolgreicher autonomer Runner-Lauf und darf `last_successful_run` nicht entsprechend vortäuschen.

## Legacy Observation Runner und Bootstrap

Der frühere autonome State-writing Observation Runner bleibt nur als historische Konfiguration und technischer Vertrag im Repository.

Nicht Teil des aktuellen scheduled Monitoring sind:

- autonomes Schreiben nach `state/entity-observation.json`;
- autonomer Observation Bootstrap;
- automatischer vollständiger Baseline-Backfill;
- autonomer Replacement-State-Writer;
- automatische Observation-Event-Publikation als Voraussetzung für die Benachrichtigung.

Die Bootstrap-Konfiguration ist deshalb ausdrücklich deaktiviert. Historische Workflow-Dateien dürfen zur Rekonstruktion von Normalisierungs-, Hash-, Validierungs- und Concurrency-Regeln gelesen werden, aber ihre alte Aktivierungslogik darf die aktuelle Architecture nicht überschreiben.

## Schreibgrenzen

Bei scheduled Monitoring:

- keine Repository-Writes;
- keine Änderung an State, Knowledge, Decisions, Boards oder Analysen;
- keine Änderung an Jobs, Target Sets, Profilen oder Workflows;
- keine Änderung an `public/data/`;
- keine GitHub-Actions-Änderung ohne separate ausdrückliche Freigabe.

Bei einem ausdrücklich freigegebenen interaktiven Write:

- nur den konkret genehmigten Persistenzumfang schreiben;
- vorhandene gute und nicht betroffene Zustände erhalten;
- normale Repository-Validierung und sichere Publication anwenden.

## Validierung

Für die bestehende Automation-Konfiguration:

```bash
python fantasy-management/_ai/scripts/validate_automation.py

python -m unittest discover \
  -s fantasy-management/_ai/scripts/tests \
  -p "test_validate_automation.py" \
  -v
```

Observation-State-Replacements müssen zusätzlich gegen `automation-observation-state.schema.json` und die Cross-File-Regeln validiert werden.

## Lesereihenfolge

Für aktuelle Fantasy-Operations-Arbeit:

1. `/AGENTS.md`
2. `fantasy-management/AGENTS.md`
3. `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`
4. `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`
5. `fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md`
6. `fantasy-management/automation/AGENTS.md`, wenn Automation-Verträge oder State betroffen sind
7. diese README
8. `runner-config.json`
9. relevante Job-, Target-Set-, Profil-, Workflow- und State-Dateien
10. aktuelle Repo-Daten und erforderliche externe Quellen

Die Schemata liegen unter `fantasy-management/_ai/schemas/` und sind in `_ai/schema-list.json` registriert.
