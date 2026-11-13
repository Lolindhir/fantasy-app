# Salary – Überblick und Einstieg

> **Status:** Sammelbereich für offene Konzept- und Analysepapiere. **Keine dieser Regeln ist beschlossen.**
> Das heute geltende System ist in `public/docs/Salary_Explanation.md` beschrieben und bleibt bis zu einer Ligaentscheidung unverändert.
>
> Nachgehalten in Issue #873 (Salary-Bereich mit README-Einstieg anlegen).

## Aktuell bestätigter Konzeptstand zum Minimum (11.10.2026)

Robert hat die **gleitende 50-%-Regel** als bevorzugte *Konzeptentscheidung* bestätigt ([Issue #956](https://github.com/Lolindhir/fantasy-app/issues/956)). Sie ersetzt die früher im Detailpapier verwendete **voll additive** Minimum-Salary-Formel; sie ist **keine** bereits beschlossene Ligaregel und wird nicht in der App angewendet.

Für normale Performance-Verträge ab Year 4 gilt:

```text
P = Performance-Salary vor Minimum
M = erfahrungsabhängiges Minimum (0,40–0,50 % ab Year 4)
Salary = max(P, M + 0,50 × P)
```

Die **unveränderten** Rookie Contracts gelten für Year 1–3 (Year 1 Draft-basiert, Year 2 = 125 % und Year 3 = 150 % des festen Year-1-Salarys). Ein in beiden Draft-Signalen undrafted Rookie kostet in Year 1 genau **0,25 %** des Vorjahres-Caps; im Vergleich bei gleicher Cap-Basis folgen **0,3125 %** und **0,375 %**, jeweils weniger als das Minimum eines Year-4-Veteranen ohne Performance (**0,40 %**).

Die Simulation vom **05.10.2026** bleibt als **historischer Vergleich** bestehen: Das vollständig additive Szenario C mit 478,9 Mio. Cap ist **nicht** mehr das bevorzugte Minimum-Modell. Der anschließend geprüfte 50-%-Ansatz ergab in diesem Snapshot **440,9 Mio. Cap**, genauso viel wie das Gesamtmodell ohne Base Minimum. Einzelheiten, Grenzen und Berechnungsdefinition stehen im kanonischen [Salary-/Dead-Cap-Konzept](salary-dead-cap-concept.md).



> **Hinweis Simulation (Issue #1453):** `simulation/salary_simulation.py` ist ein datierter Analyse-Snapshot (05.10.2026, Ergebnis `analyses/2026-10-05-salary-simulation.json`) und liest bewusst veröffentlichte Read Models. Er ist kein Pipeline-Consumer und darf von keinem Workflow, Generator oder Frontend aufgerufen werden; die Umstellung auf Shared Derived erfolgt erst beim nächsten notwendigen Update der Analyse. Der Scanner-Test schützt das (`analysisSnapshotPolicy` in `.ai-context/manual/source-of-truth-matrix.yaml`).

## Lesereihenfolge

| # | Papier | Inhalt | Status (laut Dateikopf) |
|---|--------|--------|--------------------------|
| 1 | [`public/docs/Salary_Explanation.md`](../../../public/docs/Salary_Explanation.md) | Heutiges Salary-System (Ist-Zustand) | gültig |
| 2 | [`salary-dead-cap-concept.md`](salary-dead-cap-concept.md) | Rookie-Salary, gleitendes 50-%-Minimum, Dead Cap, feste Rookie-Vertragsstufen | Gleitendes Minimum als Konzeptentscheidung bestätigt; keine Ligaregel |
| 3 | [`salary-system-redesign-concept.md`](salary-system-redesign-concept.md) | Redesign des Performance Salary, Positionskritikalität, Cap-Dynamik (Stand 29.09.2026) | offenes Research-/Designpapier |
| 4 | [`../league-economy-redesign-options.md`](../league-economy-redesign-options.md) | Synthese der drei Themen Salary/Dead Cap, Performance Salary, Team-Window | frühes Diskussionspapier, keine Gesamtvariante beschlossen |
| 5 | [`../team-window-strategy-concept.md`](../team-window-strategy-concept.md) | Reload, Rebuild oder Hybrid | Konzeptpapier |

## Quantitative Analysen (`analyses/`)

- [CP1 – Salary-/League-Economy-Baseline (05.11.2026)](analyses/2026-11-05-salary-cap-cp1-baseline.md) – fixierte historische Roster-/Cap-Zeitreihe, 2024–2026er Transaktions-/Draft-Inventar und methodische Grenzen für [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344); keine Ligaregel.
- [CP2a – A/B/C-Stresstest (05.11.2026)](analyses/2026-11-05-salary-cap-cp2-abc-stress-test.md) – kontrollierte Vergleichspreise, permanenter Cap-Vollzug als kontrafaktischer Transaktions-Stresstest und Grenzen; CP2-Fachentscheidung noch offen, [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344).
- [CP2b – Historische Salaries, Compliance und Starter-/Trade-Kosten (06.11.2026)](analyses/2026-11-06-salary-cap-cp2b-historical-compliance.md) – sechs tatsächlich archivierte Salary-/Cap-Versionen, hypothetische legale Cut-only-Kader, FA-Draft-/Trade-Buyer-Checks und offene Testsemantik; keine neue Regel ([Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344)).


Datierte Salary-Berechnungen liegen unter derselben Root (jeweils `.md` und `.json`):

- [`2026-07-31-three-year-history-baseline.md`](analyses/2026-07-31-three-year-history-baseline.md): Salary-Effizienz-Baseline mit Drei-Jahres-Historie.
- [`2026-10-02-criticality-normalization-k15.md`](analyses/2026-10-02-criticality-normalization-k15.md): Kritikalitäts-Normalisierung (Centered-25, Top-10%-Referenz, k=1,5), führendes Arbeitsmodell.
- [`2026-10-05-salary-simulation.md`](analyses/2026-10-05-salary-simulation.md): Historisches Simulationspaket auf Liga-Scoring (Issue #879): Criticality-Kurven neu, Szenarien für Bandbreite, k, Rang-Population, **damals voll additives** Base Minimum und Rookie-Verträge, Cap-Rückkopplung, Zeitpunkt der Salary-Umstellung, Dead Cap aus echten Cuts. Dazu JSON und Spielertabelle als CSV.
- [`2026-11-05-flo-cap-impact-case-study.md`](analyses/2026-11-05-flo-cap-impact-case-study.md): **Fallstudie Flo / Just Bill 2026** – acht Juni-Cap-Cuts, nachfolgende Free-Agent-Draft-Umverteilung, Kader- und Salary-Rekonstruktion, Ergebnisse und offene Fragen zur gewünschten Wirkung des Salary Caps. Datierter empirischer Befund, keine neue Regel.
- [`2026-11-05-salary-cap-design-goals-handoff.md`](analyses/2026-11-05-salary-cap-design-goals-handoff.md): **Gesprächsübergabe Salary-Cap-Ziele** – Nutzerziel gegen dauerhaft kostenlos konservierte Dynasty-Dominanz, Flo-Interpretation, Trade-/Dead-Cap-Abwägungen, permanente Durchsetzung vs. Criticality, kompakte A/B/C-Backtests; **kein Beschluss**, Input für ein separates zentrales Design-Issue.


## Simulation (`simulation/`)

- [`salary_simulation.py`](simulation/salary_simulation.py) rechnet die Simulation reproduzierbar aus Repo-Daten nach und schreibt JSON, CSV und Markdown nach `analyses/`. Aufruf aus dem Repo-Root: `python3 fantasy-management/league-economy/salary/simulation/salary_simulation.py`. Kurve, Floor, Saisonpunkte-Gewichte und Cap der heutigen Formel kommen aus den zentralen Modellen `salary-v1` und `salary-cap-v1` (`tools/derived_data_lib/models`, Issue #919 Schritt 7); die Entwurfsparameter des Redesigns (Mindestprozente, Rookie-Skala, Dead Cap) stehen weiter im Skript.

## Abgrenzung zur Technik

- Die Punktbasis für `Players.json` (Liga-Scoring statt Tank01-PPR) wurde in Issue #347 (Phase 2 Source-Data-Migration) umgestellt. Die Salary-Formel blieb dabei bewusst unverändert; das Redesign ist nicht Teil davon (siehe ADR-041 in `.ai-context/manual/decisions.yaml`).
- Eine Änderung des Salary-Systems wäre eine eigene, von der Liga zu beschließende Änderung und würde erst danach in Generator und App umgesetzt.

## Arbeitsregeln

- Neue Salary-Überlegungen und datierte Salary-Analysen kommen in diesen Ordner (Analysen nach `analyses/`).
- Vor Änderungen `fantasy-management/league-economy/AGENTS.md` lesen (Lesereihenfolge und Synthesegrenze).
- Teilbare Fassung (PDF oder Doc) wird erst erstellt, wenn die Ausarbeitung des Vorschlags abgeschlossen ist.
