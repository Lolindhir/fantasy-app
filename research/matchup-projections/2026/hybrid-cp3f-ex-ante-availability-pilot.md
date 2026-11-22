# CP3f — historischer Ex-ante-Availability-Pilot (2026 Weeks 5–10)

**Stand:** 22.11.2026. **Owner:** [Issue #1451](https://github.com/Lolindhir/fantasy-app/issues/1451). Nur Research, keine produktive Modell- oder Datenänderung.

## Ziel und entscheidende Grenze

CP3d benutzte nachträglich bekannte Snaps als Teilnahme-Oracle. CP3f prüft stattdessen, welche **vor dem Kickoff tatsächlich archivierte** Statusinformation über den möglichen NFL-Einsatz vorhanden war.

- **Injury:** data-derived/nfl-injuries/2025.json enthält 6.068, 2026.json 3.481 Report-Spielerwochen. Beide Produkte sind **retrospektive Source-Snapshots**, nicht Point-in-Time. Die 2025/26er Reports besitzen keine verlässlichen Spieleränderungszeitpunkte (SourceModifiedRaw null); historische Release-UpdatedAt-Werte sind keine ursprünglichen Pregame-Wissensstände. 2024 hat zwar date_modified, aber auch kein garantiertes damaliges vollständiges Report-Snapshot.
- **Availability:** data-derived/nfl-player-availability/2025.json und 2026.json sind bereits v2, mit 23.964 / 13.798 Records. Der aggregierte State, Played, Snaps und Wochen-Rosterstatus dürfen **nur als retrospektives Ziel**, nicht als damalige Prognoseeingabe verwendet werden.
- **ESPN:** Die Git-Historie enthält echte damals persistierte Source-Status-Snapshots ab dem 6. Oktober 2026, zunächst im alten Verzeichnis source-data, nach Migration unter data-source. Nur diese vorher gespeicherten ESPN-Werte dienen als Pregame-Eingabe. Der heute kanonische ESPN-Spieler-ID-Join ist selbst nicht als damaliger Identitätsgraph nachgewiesen.
- **Fantasy-Kader:** Historische Matchups-Dateien werden zur Auswahl einer Liga-Stichprobe benutzt. Sie beweisen nicht, dass alle damaligen Besitzer-/IR-/Taxi-/Waiver-Zustände schon am gewählten Mittwoch eingefroren waren. Gleiches gilt für die damaligen PWF-Projektionen.

## Reproduktion

Skript: [audit_ex_ante_espn_status.cjs](audit_ex_ante_espn_status.cjs). Voraussetzungen: Node und eine lokale Repo-Kopie mit **vollständiger Git-Historie**. Es verwendet ausschließlich git show zum Lesen; es ruft keinen Anbieter ab und publiziert keine Daten. Fixierter Input-Stand für Identitäten, offizielle nachträgliche Labels, NFL-Spielplan und Fantasy-Wochenkader: Commit **5f9c6feb89441088d3aeb19765420f7563d71780**. So verändert ein späterer Availability-Rebuild nicht still das Sample.

CLI-Selbsttest: node research/matchup-projections/2026/audit_ex_ante_espn_status.cjs --self-test

Voller Reproduktionslauf: node research/matchup-projections/2026/audit_ex_ante_espn_status.cjs

Sechs Git-Snapshots jeweils **vor 00:00 UTC des ersten NFL-Spieltages** der betreffenden Woche; das liegt vor dem ersten Donnerstagabend-Kickoff:

| W | letzte bestätigte vorherige ESPN-Beobachtung (UTC) | Git-Commit | Gelabelte NFL-Spielerwochen |
| --- | --- | --- | ---: |
| 5 | 07.10. 23:47 | bf8ac8d6 | 703 |
| 6 | 14.10. 23:47 | 6318ee44 | 665 |
| 7 | 21.10. 23:37 | c35a439c | 667 |
| 8 | 28.10. 22:52 | 2061fd51 | 655 |
| 9 | 04.11. 23:53 | 245f0fb6 | 710 |
| 10 | 11.11. 23:51 | 3050e8a9 | 673 |

Zeit-/Duplikats-/Identity-Guards sind Bestandteil des Skripts. Bei den 4.073 direkt untersuchten NFL-Joins lag kein StatusSinceUtc nach dem tatsächlichen gespeicherten Commitzeitpunkt.

## A — Breite NFL-Population

Insgesamt **4.073** eindeutig gejointe Spielerwochen mit regulärem Spiel und bekanntem späteren Played-Label:

| Vorheriger ESPN-Status | Gespielt | Nicht gespielt |
| --- | ---: | ---: |
| ACTIVE | 2.190 | 997 |
| QUESTIONABLE | 195 | 122 |
| OUT | 7 | 66 |
| DOUBTFUL | 1 | 14 |
| INJURY_RESERVE | 34 | 434 |
| DAY_TO_DAY | 1 | 2 |
| Ohne Status | 0 | 10 |

Die NFL-Population umfasst viele Reservisten und Spieler ohne Snaps. ACTIVE ist keine Zusage, tatsächlich eingesetzt zu werden. Vor dem individuellen Kickoff können sich Statusmeldungen ändern.

## B — Archivierte sechs Fantasy-Kader

6 Teams × 6 Wochen: **1.230** einmalige Fantasy-Kader-Spielerwochen, alle mit ESPN-Zuordnung; **1.095** mit eindeutigem Played-Label. Weitere **130 Bye-Wochen und 5 Wochen ohne Availability-Record** sind bewusst **nicht** als Nichtteilnahme klassifiziert.

| Mittwoch-Status | Gespielt | Nicht gespielt | Gespielt in % |
| --- | ---: | ---: | ---: |
| ACTIVE | 746 | 35 | 95,5 |
| QUESTIONABLE | 111 | 50 | 68,9 |
| OUT | 1 | 15 | 6,3 |
| DOUBTFUL | 1 | 7 | 12,5 |
| INJURY_RESERVE | 11 | 115 | 8,7 |
| DAY_TO_DAY | 1 | 2 | 33,3 |
| **Summe** | **871** | **224** | **79,5** |

**Nur eine einfache diagnostische Klassifikation**, kein kalibriertes Wahrscheinlichkeitsmodell: OUT, DOUBTFUL und INJURY_RESERVE markieren mögliche Nichtteilnahme; alle übrigen Statuswerte vorläufig Teilnahme.

- Baseline **alle spielen**: **224** falsche Einordnungen (79,5 % korrekt).
- Dreistatusregel: **100** falsche Einordnungen (90,9 % korrekt). Das sind 137 richtig erkannte Nichtteilnahmen, 13 zu Unrecht ausgeschlossene spätere Teilnehmer und 87 unerkannte Nichtteilnahmen.

Die 90,9 % sind **kein nachgewiesener Forecast-Qualitätsgewinn für Expected Team Points oder Siegchancen**: historische Fantasy-Kader sind rückblickend ausgewählt, die sechs Wochen sind korreliert, die PWF-As-of-Revisionen nicht gepaart, und es gibt keinen unabhängigen Holdout.

## Entscheidung / nächste Schranke

1. **Kein weiterer historischer Injury-/Availability-Backfill nötig**, um diese grundsätzliche Frage zu prüfen. Bestehende v2-Produkte sind als Outcome-Labels hilfreich.
2. **Kein Rückgriff auf nachträgliche Injury-Reports als damaliges Wissen.** Die frühere ESPN-Git-Datei ist das belegte Signal; echte Byes sind getrennt, Unknown bleibt Unknown. Kein pauschales OUT = null Punkte im produktiven Modell.
3. Für einen **fairen gepaarten Expected-Points- und WinProb-Backtest** zuerst verifizieren, ob dieselben Cutoffs auch die damaligen Fantasy-Roster-/Lineup-/PWF-Versionen tragen. Nur wenn belegt, mit identischen Slots und historisch verfügbaren Projektionen ein kleines Status-vs.-Baseline-Experiment durchführen. Ansonsten ist die notwendige As-of-Evidenz offen.
4. **Keine** Produktionsänderung an PWF, CP2-HybridExpected, WinProbability, Source/Derived, Injury, Availability, UI oder Workflows. Rücknahme nur der beiden Research-Dateien.

**Validierung:** Die sechs historischen ESPN-Git-Dateien und die retrospektiven v2-Labels wurden über den GitHub-Connector im JS-Harness gegeneinander gerechnet. Ein vollständiger direkter Node-CLI-Lauf der ausgecheckten Repository-Geschichte ist nicht behauptet. Review/CI sind zusätzliche PR-Gates, nicht durch einen erfolgreichen JS-Harness-Lauf ersetzt.

## C — Gepaarter As-of-Roster-/PWF-Check (22.11.2026)

**Resultat:** Für alle sechs 2026er Wochen 5–10 liegen vor deren erstem NFL-Kickoff jeweils gemeinsam ein damals veröffentlichter PlayerWeekFantasy-Stand, DecisionWindows mit 13 Starting-Slots und ein kanonischer Sleeper-Wochenkader im Git-Stand vor. Week 5 liegt noch unter source-data/leagues, Weeks 6–10 unter data-source/leagues. Die späteren tatsächlichen Team-Scores werden getrennt aus Commit 5f9c6feb89441088d3aeb19765420f7563d71780 als **Outcome**, nicht als Prognoseeingabe, geladen. Die historischen public/data-Dateien sind hier *Belege für damals veröffentlichte Daten*, niemals eine neue produktive Consumer-Quelle.

**As-of-Checks:** PWF.Week = DecisionWindows.LineupWeek = Matchup.Week; jeweils sechs Teams und 13 Starting-Slots (2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K). Der Join der kanonischen Wochenkader und der damals veröffentlichten Decision-Windows-Spielerlisten ist für 1.229 Spielerwochen exakt (0 Mitgliedschaftsdifferenzen). Alle as-of verfügbaren ESPN-Statusbeobachtungen lagen vor dem Wochen-Checkpoint. Die damaligen PWF-Actual-Felder waren sämtlich null, ebenso die damaligen Sleeper-Team-Punkte.

| Week | Historische Kader-Spielerwochen | damals mit ESPN-Status | OUT/DOUBTFUL/IR | vollständige Paare |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 204 | 78 | 0 | 6 |
| 6 | 205 | 78 | 0 | 6 |
| 7 | 204 | 77 | 0 | 5 |
| 8 | 206 | 77 | 0 | 5 |
| 9 | 205 | 77 | 1 | 5 |
| 10 | 205 | 78 | 2 | 6 |
| **Summe** | **1.229** | **465** | **3** | **33/36** |

Die drei unvollständigen Team-Wochen hatten keinen projizierbaren Kicker (W7 Team 4, W8 und W9 Team 1). Der ein Spielerwochen-Eintrag größere retrospektive Fantasy-Pool aus Abschnitt B und das später vervollständigte ESPN-Mapping dürfen **nicht** als in diesem As-of-Zeitpunkt verfügbar ausgegeben werden.

### Diagnostischer, paariger Punktetest

Auf denselben aktiv rosterbaren Starter-/Bankspielern mit damaligen verfügbaren, noch **teilnahmebedingten** PWF-Projektionen wird ein regelkonformer globaler 13-Slot-Best-Ball berechnet. IR, Taxi, Bye und unbekanntes NFL-Spiel beziehungsweise fehlende PWF-Projektion werden nie als sichere Null kaschiert. Statusarm B entfernt ausschließlich Kandidaten mit damals tatsächlich publiziertem OUT, DOUBTFUL oder INJURY_RESERVE; QUESTIONABLE und fehlender Status bleiben im Pool. Beide Arme haben sonst denselben Pool, dieselben Projektionen und dieselben Slots.

| Metrik, identische 33 vollständige Team-Wochen | Ohne Statusfilter | Mit Statusfilter |
| --- | ---: | ---: |
| MAE gegen spätere tatsächliche Sleeper-Team-Punkte | **28,0707** | **28,5358** |
| RMSE | **35,6283** | **35,8245** |

In **31/33** vollständigen Paaren änderte sich keine einzige Team-Prognose. Nur in W10 bei Team 1 und Team 4 entfernte der Filter einen relevanten Kandidaten. Beide Spieler starteten später tatsächlich nicht und erzielten null Punkte; trotzdem vergrößerte der Filter bei beiden Teams den Punktfehler gegenüber dem späteren **tatsächlichen Manager-Ergebnis**. Die Teilnahmeprognose-Güte (Abschnitt B, retrospektive 90,9 %) ist eben nicht automatisch Team-Score-Güte. Dieser Test misst **nicht** das vollständig geplante Monte-Carlo-Best-Ball-, Coach-Effizienz- oder Siegchancen-Modell und ist keine unabhängige Holdout-Kalibrierung. Die Stichprobe ist klein und wochenweise korreliert.

### Reproduktion und offene Schranke

Neuer Modus des bestehenden [Forschungsskripts](audit_ex_ante_espn_status.cjs):

    node research/matchup-projections/2026/audit_ex_ante_espn_status.cjs --roster-pwf

Mit vollständiger lokaler Git-Historie liest der Modus nur festgehaltene Commits via git show, prüft die temporale und semantische Konsistenz, optimiert beide Kandidatenpools und misst die Fehler gegen spätere Sleeper-Team-Punkte. Der bestehende --self-test enthält nun auch einen synthetischen Fall für vollständige Slots, OUT-Filter und fehlenden Kicker. Die Zahlen wurden mittels GitHub-Connector mit einem unabhängigen JS-Harness nachgerechnet. **Direkter Full-History-CLI-Durchlauf und CI-Erfolg sind noch nicht belegt**, da der lokale Git-Checkout in dieser Umgebung nicht heruntergeladen werden kann.

**Folgerung:** Die alte PWF- und Kaderbasis ist rekonstruierbar, aber die damals publizierte Statuszuordnung umfasst nur 465 der 1.229 Kader-Spielerwochen und gerade drei hochriskante Statussignale. Vor dem wesentlich komplexeren Walk-forward-Test müssen wir die **damals** verfügbare ESPN-Identitätstabelle gegen die im jeweiligen Commit gespeicherte ESPN-Quelldatei prüfen. Einen **heutigen** erweiterten Identity-Graph rückwirkend als damalige operative Zuordnung zu verwenden wäre Look-ahead-Leakage. Vor einer produktiven Chance- oder Punktmodell-Änderung wären größere Stichprobe, echte Expected-Points-/Siegchancenmetriken und ein zeitlich separater Holdout nötig. Produktive Pipelines bleiben unverändert.
