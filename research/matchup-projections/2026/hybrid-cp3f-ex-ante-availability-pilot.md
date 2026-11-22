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
