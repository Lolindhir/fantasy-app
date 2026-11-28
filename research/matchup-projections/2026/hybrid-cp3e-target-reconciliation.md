# CP3e – Target-Reconciliation der Best-Ball-Studie (2026 W5–10)

- **Stand:** 2026-11-22
- **Owner:** [Issue #1451](https://github.com/Lolindhir/fantasy-app/issues/1451)
- **Scope:** Nur read-only Research; weder produktive Source-/Derived-Daten noch Modelle, UI, Workflows oder Writer verändern.
- **Vorarbeiten:** [CP3d](hybrid-oracle-availability-ablation.md), CP3e-simple-Ergebnisse im Issue #1451.

## Frage

In der empirischen CP3e-simple-Auswertung reproduzierte der Snap-Oracle-Pool bei vier der 36 Team-Wochen die offiziellen TWP-Best-Ball-Punkte nicht. Sind vier Zielwerte falsch oder filtert die Research-Simulation echte Teilnehmer heraus?

## Abgleich mit aktuellen Repository-Originaldaten

Verglichen wurden für jede Woche die archivierten PWF-Projektionen und finalen PWF-Actuals, Wochenkader aus dem League-Layer, NFL Weekly-Rosters-Positionen, NFL Snap-Counts sowie TWP.PotentialPoints und TWP.OptimalLineup. Der vorhandene globale CP3b-Best-Ball-Optimizer wurde für das tatsächliche Punkte-Optimum genutzt; Slotformation: 2026 mit 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K.

**Alle vier Fehlfälle sind dasselbe Team** `clr-a8e576139994570d82e9ea2ed3f42b1b` und derselbe Spieler `NFLP-47281a0fdddeb30277b6`: `weekly-rosters.Position=RB`, aber `snap-counts.Position=HB`. Positive Offensive-Snaps belegen in den vier Wochen dessen tatsächlichen Einsatz. Seine finalen PWF-Punkte stimmen jeweils mit dem TWP-OptimalLineup-Eintrag überein.

| Week | Offensive Snaps | Spielerpunkte | Original-Oracle-Optimum | Alias-Oracle-Optimum | TWP PotentialPoints |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 | 39 | 7,00 | 250,26 | **255,06** | 255,06 |
| 8 | 51 | 16,10 | 203,52 | **208,12** | 208,12 |
| 9 | 36 | 10,50 | 216,78 | **217,98** | 217,98 |
| 10 | 48 | 28,30 | 222,98 | **244,78** | 244,78 |

**Sechs Wochen, sechs Teams:** Der ursprüngliche Research-Snap-Filter stimmt in **32/36** Fällen mit TWP bis auf 0,05 Punkte überein. Eine einzig für den Research-Abgleich verwendete, streng evidenzbasierte Regel `weeklyPosition === 'RB' && snap.position === 'HB' && offenseSnaps > 0` führt zu **36/36** Übereinstimmungen. Alle anderen Kandidaten, Slotregeln und finalen Punkte bleiben gleich. Der freie Raw-PWF-Actual-Pool reproduziert ebenfalls alle 36 Zielwerte.

Damit ist keine Modifikation von produktiven NFL-Quelldaten, kanonischen Rosterpositionen oder offiziellen TWP-Best-Ball-Punkten gerechtfertigt. Das Problem liegt in der Research-Teilnahmetaxonomie; das Alias ist **kein** Beleg einer vor dem Spiel bekannten Teilnahme.

## Reproduzierbarkeit

Read-only-Skript: [audit_cp3e_target_reconciliation.cjs](audit_cp3e_target_reconciliation.cjs).

```bash
node research/matchup-projections/2026/audit_cp3e_target_reconciliation.cjs --self-test
node research/matchup-projections/2026/audit_cp3e_target_reconciliation.cjs --season=2026 --weeks=5-10
```

Das Skript importiert den vorhandenen CP3b-Assignment-Solver, die CP3c-Snap-Auswertung und die CP3d-Slotfunktion. Es vergleicht originalen Oracle-Filter, eng alias-ergänzten Oracle-Filter und ungefilterte PWF-Actuals gegen dieselben TWP-Targets, berichtet Restabweichungen und prüft Pool-Monotonie. Nicht-Teilnahme wird nicht aus null Fantasy-Punkten abgeleitet. Eine TWP-OptimalLineup-Zeile mit null Punkten kann auch einen Spieler ohne positive Snap-Evidenz enthalten; deshalb ist der **Punkte-Optimum-Abgleich** entscheidend, nicht bloß die Gleichheit aller OptimalLineup-Spieler-IDs.

**Validierungsstatus:** Node-Syntaxcheck des neuen Skripts und isolierter Self-Test mit lokalen Hilfsstubs erfolgreich; aktueller Echtquellenabgleich per GitHub-Connector und äquivalentem JS-Optimizer in drei Zweier-Wochenblöcken, 36/36 nach enger Alias-Regel. Ein vollständiger direkter CLI-Datenlauf aus einer lokalen vollständigen Repository-Kopie ist hier **nicht** erfolgt. Keine CI-/Deep-Ausführung als erledigt behaupten.

## Bedeutung für CP3e und die nächsten Forschungsfragen

Diese Reconciliation beseitigt den konkreten Zielwertvergleichsfehler; sie **ändert keine** Monte-Carlo-Prognosen und ist **keine** neue Intervall- oder Punktkalibrierung. Der bisherige CP3e-simple-Vergleich auf denselben 36 offiziellen Targets bleibt als explorativer Befund erhalten: Normal vs. empirische Residuen, MAE 25,38 vs. 25,41 und nominelle 80-%-Coverage 61,1 % vs. 77,8 %. Die Verteilungskorrektur hat keinen belegten Punktprognose-Vorteil; eine neue Produktionsmethode ist nicht gerechtfertigt.

Die separate CP3d-Abweichung **2025 W7** (fehlender projizierbarer OptimalLineup-Kandidat) ist von dieser 2026er Alias-Reconciliation **nicht** gelöst. Ebenso fehlen nachweislich vor dem Kickoff beobachtete Teilnahmeprognosen, echte historische As-of-Kader sowie echte Managerentscheidungen/Locks. Deshalb bleibt CP3/CP4 offen. Nächste sinnvolle unabhängige Untersuchung: **kleines ex-ante-Availability-Baseline-Experiment** auf ausschließlich vor Kickoff verfügbaren Zuständen, mit Unknown- und Coverage-Ausweis und unveränderter Oracle-Referenz nur als nachträglichem Diagnostikziel. Erst danach Expected Manager Score und Siegchancen.

**Rollback:** Revert ausschließlich der zwei neuen Research-Dateien. Keine Runner-, Testinventar-, Workflow-, Produkt-, UI- oder Source-Änderung.
