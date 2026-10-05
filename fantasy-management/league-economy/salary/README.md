# Salary – Überblick und Einstieg

> **Status:** Sammelbereich für offene Konzept- und Analysepapiere. **Keine dieser Regeln ist beschlossen.**
> Das heute geltende System ist in `public/docs/Salary_Explanation.md` beschrieben und bleibt bis zu einer Ligaentscheidung unverändert.
>
> Nachgehalten in Issue #873 (Salary-Bereich mit README-Einstieg anlegen).

## Lesereihenfolge

| # | Papier | Inhalt | Status (laut Dateikopf) |
|---|--------|--------|--------------------------|
| 1 | [`public/docs/Salary_Explanation.md`](../../../public/docs/Salary_Explanation.md) | Heutiges Salary-System (Ist-Zustand) | gültig |
| 2 | [`salary-dead-cap-concept.md`](salary-dead-cap-concept.md) | Rookie-Salary, Mindestgehalt, Dead Cap, feste Rookie-Vertragsstufen | Diskussionsentwurf, nicht beschlossen |
| 3 | [`salary-system-redesign-concept.md`](salary-system-redesign-concept.md) | Redesign des Performance Salary, Positionskritikalität, Cap-Dynamik (Stand 29.09.2026) | offenes Research-/Designpapier |
| 4 | [`../league-economy-redesign-options.md`](../league-economy-redesign-options.md) | Synthese der drei Themen Salary/Dead Cap, Performance Salary, Team-Window | frühes Diskussionspapier, keine Gesamtvariante beschlossen |
| 5 | [`../team-window-strategy-concept.md`](../team-window-strategy-concept.md) | Reload, Rebuild oder Hybrid | Konzeptpapier |

## Quantitative Analysen (bleiben am Ablageort)

Datierte Analysen folgen der Analysis-Ablage unter `fantasy-management/analyses/` und werden deshalb hier nur verlinkt:

- [`2026-07-31-three-year-history-baseline.md`](../../analyses/2026/league-meta/salary-efficiency/2026-07-31-three-year-history-baseline.md): Salary-Effizienz-Baseline mit Drei-Jahres-Historie.
- [`2026-10-02-criticality-normalization-k15.md`](../../analyses/2026/league-meta/salary-efficiency/2026-10-02-criticality-normalization-k15.md): Kritikalitäts-Normalisierung (Centered-25, Top-10%-Referenz, k=1,5), führendes Arbeitsmodell.

## Abgrenzung zur Technik

- Die Punktbasis für `Players.json` (Liga-Scoring statt Tank01-PPR) wurde in Issue #347 (Phase 2 Source-Data-Migration) umgestellt. Die Salary-Formel blieb dabei bewusst unverändert; das Redesign ist nicht Teil davon (siehe ADR-041 in `.ai-context/manual/decisions.yaml`).
- Eine Änderung des Salary-Systems wäre eine eigene, von der Liga zu beschließende Änderung und würde erst danach in Generator und App umgesetzt.

## Arbeitsregeln

- Neue Salary-Überlegungen kommen in diesen Ordner; datierte Berechnungen weiter unter `analyses/`.
- Vor Änderungen `fantasy-management/league-economy/AGENTS.md` lesen (Lesereihenfolge und Synthesegrenze).
- Teilbare Fassung (PDF oder Doc) wird erst erstellt, wenn die Ausarbeitung des Vorschlags abgeschlossen ist.
