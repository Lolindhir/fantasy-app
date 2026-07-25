# TESTFIXTURE – Tank Bigsby Opportunity Change

> **Nicht mergen.** Diese Datei wurde ausschließlich für den kontrollierten atomaren Schreibtest der Fantasy-Automation erzeugt. Sie beschreibt keine reale Rollenänderung.

- **Erstellt:** 2026-07-25T07:04:01+02:00
- **Job:** `entity-observation`
- **Target:** `tank-bigsby-2026`
- **Profil:** `role-opportunity`
- **Klassifikation:** `opportunity_change`
- **Schweregrad:** `medium`
- **Perspektive:** `managed_team`

## Observation

**[SIMULATION]** Zwei unabhängige Test-Fundstellen stufen Tank Bigsby als klaren primären Backup mit überwiegender First-Team-Nutzung ein.

| Signal | Vorher | Simulierter Zustand |
|---|---|---|
| Rollenklasse | `listed_rb3_open_backup_competition` | `simulated_clear_primary_backup` |
| First-Team-Nutzung | `unknown` | `majority` |
| Goal-Line-Nutzung | `unknown` | `rotational` |

## Interpretation

**[SIMULATION]** Das würde eine belastbare Separation von Will Shipley und einen relevanten Opportunity-Anstieg bedeuten.

Konfidenz: `medium`

## Decision Effect

**[SIMULATION]** Als Barkley-Handcuff würde Bigsby vom späten Value-Target zum priorisierten FA-Draft-Ziel aufsteigen.

- Vorherige Aktion: Nur als spätes Value- oder Handcuff-Target einplanen.
- Simulierte neue Aktion: Ab FA-Runde 4 aktiv einplanen und nicht bis Runde 5 warten.
- Dringlichkeit: `next_window`

## Evidenz

1. `Controlled practice report A` – künstliche Test-Fundstelle
2. `Controlled practice report B` – unabhängige künstliche Test-Fundstelle

## Write-Test-Erwartung

Dieser Branch muss genau drei fachliche Änderungen enthalten:

1. aktualisierter Observation-State;
2. dieses Markdown-Event;
3. das passende JSON-Event.

Runner-Konfiguration, Jobdefinition, Profile, Target Sets und `public/data` dürfen nicht verändert sein.
