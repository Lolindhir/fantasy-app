# CP3d — Oracle-Availability-Ablation des Monte-Carlo-Best-Ball

- **Datum:** 2026-11-19
- **Issue:** [#1451](https://github.com/Lolindhir/fantasy-app/issues/1451)
- **Vorarbeiten:** [CP3b](hybrid-selection-range-monte-carlo.md), [CP3c](hybrid-pwf-range-participation-audit.md)
- **Status:** Reiner Forschungscheckpoint. Keine Änderung an produktiver PWF, CP2-HybridExpected, WinProbability, App, Source/Derived oder Workflows.

## Forschungsfrage und Testentscheidung

Die CP3b-Simulation behandelte alle Spieler mit PWF-Projektion wie sichere Teilnehmer. CP3c zeigte, dass die **marginalen** 90-%-PWF-Intervalle für tatsächlich eingesetzte Spieler nahe am Soll liegen, das bedingte Modell aber die tatsächliche Teilnahme nicht modelliert. CP3d isoliert im exakt selben historischen Kaderpool/League-Slot-Setup den Effekt, Kandidaten **mit nachträglich bekannter Nichtteilnahme/fehlendem positivem Snap-Nachweis** aus der Simulation zu entfernen.

**Das ist ausdrücklich ein Oracle-/Lookahead-Gegenfaktum und keine zulässige ex-ante-Verfügbarkeitsprognose.** Ein fehlender positiver Snap-Record beweist weder medizinische Verletzung noch OUT; Bye, Bench und Quellenabdeckung können Ursachen sein. Deshalb sprechen wir von einem *Snap-Oracle-Filter*, nicht einem Injury-Modell.

## Implementierung und echte Quellen

- **Reproduzierbares Skript:** [ablate_best_ball_oracle_availability.cjs](ablate_best_ball_oracle_availability.cjs). Reuses `simulate_best_ball_ranges.cjs::optimize/randomNormal` und `audit_pwf_range_coverage.cjs::snapsByPlayer/playedFromSnap`. Keine eigene Produktionslogik, neue Writer oder Schedules.
- **Saisons/Wochen:** 2024/2025/2026, jeweils Weeks 5–10; 6 Teams × 6 Wochen × 3 Saisons = **108 Team-Wochen**.
- **Daten:** PWF-V4-C-PI1-Projektionen und finale Actuals unter `data-derived/player-week-fantasy/nfl-reise`; historische Fantasy-Wochenkader `data-source/leagues/nfl-reise/seasons/<season>/matchups/week-<week>.json`; NFL-Wochenpositionen `data-source/nfl/weekly-rosters`; NFL-Snaps `data-source/nfl/snap-counts`; TWP-PotentialPoints und OptimalLineup `data-derived/team-week-performance`; exakte RosterPositions aus jeweiligem `league.json`.
- **Saisonale Formation:** 2024 12 Slots (1QB, 2RB, 2WR, 2TE, 2FLEX, 1WRRB_FLEX, 1REC_FLEX, 1K); 2025/26 13 (2QB, 2RB, 2WR, 2TE, 4FLEX, 1K). Die realen `league.json`-Slots wurden aus GitHub gegen die Analyseaufstellung geprüft.
- **Gleiche Verteilungen und Zufallsziehungen:** Beide Arme erhalten für jeden Kandidaten in jedem Draw **denselben** `mean + sigma × standardnormal`-Score. Arm A maximiert alle PWF-projizierbaren Kandidaten, Arm B nur die Teilmenge mit positivem relevantem Snap-Nachweis (OffenseSnaps>0 bzw. K SpecialTeamsSnaps>0). Null-/Fehlslots werden nicht stillschweigend als komplette Aufstellung akzeptiert. Jeder Draw des Oracle-Solvers ist zwangsläufig kleiner/gleich dem Raw-Solver; diese Invariante prüft das Skript.
- **Simulation:** 2024 800 Draws pro Team-Woche, 2025/26 1.200, Seed 20261119, 3-Wochen-Blöcke; identische CP3b-Normal-/Assignment-Annahmen. Intervalle aus 10-/90-%-Sample-Quantilen.
- **Faires Scoring:** Prognosen beider Arme gegen dieselben TWP.PotentialPoints, paarweiser MAE/Bias/Coverage. Zusätzlich werden PWF-Actual-optimierte Ergebnisse als Nachweis der Target-Reproduktion gegen TWP geprüft.

Run im Repository:

```bash
node research/matchup-projections/2026/ablate_best_ball_oracle_availability.cjs --self-test
node research/matchup-projections/2026/ablate_best_ball_oracle_availability.cjs --seasons=2024,2025,2026 --weeks=5-10 --draws=1200 --draws-2024=800 --block=3 --seed=20261119
```

## Ergebnisse – 107 paarweise vollständige Team-Wochen

| Kennzahl | Alle PWF-Kandidaten | Snap-Oracle-Pool | Differenz |
| --- | ---: | ---: | ---: |
| MAE zum tatsächlichen TWP Best Ball | 28,61 Pkt. | **23,75 Pkt.** | **−4,86 Pkt. (−17,0 %)** |
| Bias (Prognose − tatsächlicher TWP Best Ball) | **+19,67 Pkt.** | **+6,17 Pkt.** | **−13,50 Pkt.** |
| Abdeckung nominelles 80-%-Intervall | 56,1 % (60/107) | **70,1 % (75/107)** | +14,0 Prozentpunkte |
| Simulierter Aufschlag gegenüber eigenem projiziertem Best Ball | +21,29 % | +18,01 % | −3,28 Prozentpunkte |

**Aufschlüsselung der 13,50 Punkte:** Durch Ausschluss der Oracle-nicht-eingesetzten Kandidaten sinkt der *deterministische* projizierte Best Ball durchschnittlich um **5,96 Punkte**, darüber hinaus sinkt der in der Monte-Carlo-Selektion entstehende Aufschlag um **7,54 Punkte**. Der Gesamtunterschied ist also **nicht** ausschließlich ein Effekt der simulierten Highs.

**Unveränderte CP3b-Rohkontrolle auf allen 108 Team-Wochen:** MAE **28,35 Punkte**, Bias **+19,49 Punkte**, nominelle 80-%-Abdeckung **61/108 = 56,5 %**. Das stimmt bis auf kleine Monte-Carlo-/Rundungsabweichungen mit CP3b (28,33 / +19,43 / 56,5 %) überein.

### Je Saison – paarweise vollständige Wochen

| Saison | N | Raw MAE | Oracle MAE | Raw Bias | Oracle Bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 35 | 24,70 | **20,23** | +19,48 | +6,65 |
| 2025 | 36 | 30,32 | **25,60** | +17,76 | +2,34 |
| 2026 | 36 | 30,70 | **25,32** | +21,77 | +9,54 |

Alle drei Saisons zeigen eine niedrigere absolute Abweichung und einen kleineren positiven Bias. Trotzdem bleibt die Oracle-Simulation im Mittel optimistisch und deckt mit 70,1 % deutlich weniger als die nominellen 80 % ab.

## Pool, Vollständigkeit und auffällige Fälle

- **2.960** PWF-projizierbare Kader-Kandidaten über alle Team-Wochen; **2.496** mit positivem Snap-Nachweis; **464** beim Oracle-Filter nicht zugelassen (**15,7 %**). Davon **460** ohne passenden Snap-Record und vier mit Snap-Record, aber ohne positive, nach CP3c relevante Snaps. Nicht als bestätigte Injury-OUT-Zahlen ausgeben.
- 10 Positionen stimmten zwischen Wochenroster und Snap-Record nicht überein; der Audit nutzt für Fantasy-Slot-Eignung die kanonische Wochenrosterposition (CP3b) und für Teilnahme den CP3c-Snap-Proxy. Positionen nicht stillschweigend überschreiben.
- **Raw 108/108 vollständig**, Oracle **107/108 vollständig**. **2024 Week 5, RosterID clr-91d6bcbb12ba53e296f3066988d7c1cd:** Nach Filter bleibt ein Pflichtslot unbesetzt. Oracle-Punkte/Intervall werden fail-closed **nicht** als volle Prognose gewertet.
- **TWP-Target-Reproduktion:** Raw-PWF-Actual optimiert reproduziert in **107/108** Fällen den retrospektiven TWP-PotentialPoints-Wert innerhalb 0,05 Punkten; Oracle in **106/108** (inkl. unvollständigem Oracle-Fall). **2025 Week 7** enthält ein TWP-OptimalLineup-Mitglied ohne verwertbare Projektion und einen um **16,60 Punkte** kleineren PWF-Kandidaten-Potentialwert. Der gepoolte Paarvergleich enthält diesen transparenterweise und ein separates `aligned`-Subset von **106** Fällen ist im Skript ausgewiesen.
- **Identität/Zeit:** Historischer gesamter archivierter Wochenkader inklusive IR/Taxi, nicht aktuell aktivierbarer Live-Pool. Keine echte Dienstag-As-of- oder Lock-Rekonstruktion. Bei historischen PWF-Revisionen kann Lookahead nicht vollständig ausgeschlossen werden.

## Interpretation und Grenzen

1. **Bedeutender Verfügbarkeits-Mechanismus belegt:** Ein ex-post-Einsatzfilter reduziert bei ansonsten gleichem Zufallsmodell die Überschätzung um rund 13,5 Punkte und den MAE um 17 %. Das misst den Filtereffekt **in dieser Stichprobe und Modellannahme**, nicht die ex-ante erzielbare Verbesserung durch ein künftiges Injury- oder Participation-Modell.
2. **Modell bleibt trotz Oracle zu optimistisch:** +6,17 Punkte Bias und 70,1 % statt 80 % Coverage. Andere Ursachen bleiben möglich: normale symmetrische Ziehungen aus asymmetrischen PI1-Grenzen, unabhängige Spieler trotz realer Korrelationen, Extremwert-Auswahl, unterschiedliche Kader-/Slot-Konstruktionen und historische Snap-/PWF-Provenienz.
3. **Kein direkter Vergleich mit Manager-Punkten/Chance:** Zielgröße hier TWP ex-post PotentialPoints, *nicht* ActualStarterPoints oder Siegchance. CP3a Manager-Score-Benchmarks bleiben getrennt.
4. **Statistik:** Die 107 Team-Wochen sind innerhalb gemeinsamer NFL-Spiele und Manager-Saisonverläufe korreliert. Keine formale Überlegenheits-/Konfidenzbehauptung, keine optimierte Parameterkalibrierung an denselben Testdaten.

## Nächster Forschungscheckpoint

**CP3e – Residuen und gemeinsame Spielergebnisverteilung:** Bei tatsächlich eingesetzten Spielern reale standardisierte Residuen/Tails nach Position und Projektionsbucket gegen die unabhängige Normalannahme testen; danach NFL-Team-/Spiel-Korrelationen als getrennte Ablation einführen. Eine **ex-ante-Verfügbarkeitsschätzung** ist ein eigener evidenzbasierter Teil der späteren Hybrid-Manager-Prognose (inklusive Injury, Bye und unbekannten Zuständen); das Oracle niemals als Produktionsfeature benutzen. Erst nach gültigem historischem Zeit-Split Manager-Punkte, Intervallkalibrierung und Matchup-Brier/LogLoss gegen einfache CP3a-Baselines vergleichen.

**CI-/Architektur-Impact:** Nur neues read-only Research-Skript und Forschungsdokument unter bestehendem Research-Owner. Bestehende CP3b-/CP3c-Funktionen wiederverwendet; keine neuen Testmodule unter `tools/tests`, keine Testinventory-/CI-Router-/Workflow-/Source-/Derived-/App-Änderungen; keine produktive Deep-Kategorie nötig. Script und historischer Auswertungslauf wurden im GitHub-gestützten JS-Harness (dreiwöchige Quellpartitionen, strukturell gleiche Assignment-/Snap-Helper) validiert; CP3d Self-Test mit geladenen Original-Imports ausgeführt. Kein direkter vollständiger Node-CLI-Durchlauf in einer lokalen Repo-Kopie behauptet. Forschung wieder rückgängig zu machen durch Revert dieser beiden Research-Dateien.
