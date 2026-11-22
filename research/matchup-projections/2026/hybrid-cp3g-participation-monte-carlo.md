# CP3g — Ex-ante-Teilnahmewahrscheinlichkeiten im Best-Ball-Monte-Carlo

**Stand:** 22.11.2026 · **Issue:** [#1451](https://github.com/Lolindhir/fantasy-app/issues/1451) · **Status:** Research-only, kein produktiver Modellwechsel.

## Fragestellung

Der empirische Best-Ball-Uplift ist innerhalb einer Prognose ein fester, aus früheren Wochen berechneter Multiplikator. Er bildet keine aktuelle Unsicherheit auf Spielerebene ab. CP3b simuliert dagegen PI1-Punktverteilungen für jeden Kandidaten, unterstellt dabei aber faktisch die Teilnahme aller projizierbaren Spieler. CP3d zeigte, dass nachträglich bekannte Teilnahme einen erheblichen Teil dieser Überoptimierung erklären kann. CP3g ersetzt **kein** rückblickendes Oracle durch ein zukünftiges Wissen, sondern simuliert eine explizite, unsichere Teilnahmeentscheidung.

## Methode und Provenienz

Reproduktionsskript: [simulate_best_ball_ex_ante_participation.cjs](simulate_best_ball_ex_ante_participation.cjs).

- **Vor dem ersten Kickoff:** Dieselben sechs historisch tatsächlich gespeicherten Git-Commits 2026 W5–10 wie CP3f. Daraus nur damalige *public/data/DecisionWindows.json* und *public/data/PlayerWeekFantasy.json* als **Beleg für die frühere Veröffentlichung** (nicht als neuer produktiver Consumer-Eingang). Positionskonforme 13-Slot-Optimierung: 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K; nur Starter/Bank mit freigeschaltetem NFL-Spiel, GameID und PWF 90-%-Range. IR/Taxi und Bye ausgeschlossen. Beobachtete Status-Zeitpunkte müssen vor dem eingefrorenen Mittwochabend-Checkpoint liegen. CP3f hat die damalige DW-Kaderpopulation gegenüber dem zeitgleichen kanonischen Sleeper-Matchup-Roster separat für alle sechs Wochen paritätsgeprüft.
- **Späteres Ergebnis:** Fixierter Ergebnis-Commit **5f9c6feb89441088d3aeb19765420f7563d71780**, finale **PlayerWeekFantasy.Actual** und NFL-Snap-Counts nur als rückblickende Scores/Labels und als Training **für spätere Wochen**. Target ist der mit tatsächlichen PWF-Punkten optimal erreichbare Best Ball **auf dem damals bekannten Kandidatenpool**, **nicht** der tatsächliche Sleeper-Manager-Score oder die offizielle retrospektive TWP-Kaderpopulation. Nicht vorhandene positive Positions-Snap-Evidenz gilt im Versuch als Nonparticipation-Proxy, nicht als Diagnose; diese Abgrenzung ist noch eine Fehlerquelle.
- **Drei Simulationsarme auf exakt denselben Spielern:** (A) alle Kandidaten werden als spielend behandelt, (B) für jeden Kandidaten vor dem Punktedraw ein Bernoulli-Ziehung mit p(Teilnahme) nach damaligem Status und **nur den vorigen** Wochen, (C) nur diagnostisch die später tatsächlich Snap-positiven Kandidaten (Oracle). Alle ziehen dieselben bedingten Punkte aus PI1 mit Sigma=(P90 oben−unten)/(2·1,64485), symmetrische unabhängige Normal-Surrogate; globaler CP3b-Hungarian-Solver mit virtuellen 0-Slots. Durch gemeinsame Punkteziehungen darf B nie über A liegen. Ein fehlender Pflichtslot im Teilnahme-Zufallsdraw wird als 0 gewertet, **nicht** als verdeckter Sample-Drop. Kein Korrelationsmodell.
- **Vorwochen-Uplift-Kontrolle:** Unsimulierter PWF-Projektions-BB und ein *gepoolter*, ausschließlich auf bereits gespielten untersuchten Wochen beruhender Ist-BB/Proj-BB-Faktor. Dieser gepoolte Faktor hat **dieselbe Zielgröße** wie die drei Simulationsarme, ist aber **nicht** identisch mit CP3a (dort Team-spezifisch und im Manager-Expected-Score mit Coach-Effizienz kombiniert).
- **Wahrscheinlichkeitskategorien:** ACTIVE, QUESTIONABLE, OUT, DOUBTFUL, INJURY_RESERVE, DAY_TO_DAY, UNKNOWN. Als explizit **illustrative, nicht extern kalibrierte** Startwerte jeweils p=0,95/0,70/0,05/0,05/0,05/0,70/0,85; je Kategorie acht Beta-Pseudobeobachtungen. Danach p=(8·prior + Anzahl vorheriger Snap-positiver Wochen)/(8 + Anzahl vorheriger Kandidaten-Wochen). W5 ist Warm-up, der vorläufige sequenzielle Vergleich gilt W6–10. Dieselbe Woche kann ihre eigene p **nicht** verändern. Identitätslücken bleiben UNKNOWN und werden nicht als ACTIVE umetikettiert.

**Reproduzierbar mit einem lokalen vollständigen Git-History-Checkout:**

    node research/matchup-projections/2026/simulate_best_ball_ex_ante_participation.cjs --self-test
    node research/matchup-projections/2026/simulate_best_ball_ex_ante_participation.cjs --draws=240 --rows
    node research/matchup-projections/2026/simulate_best_ball_ex_ante_participation.cjs --draws=800

Die gesamte Normal-/Teilnahmeziehung ist seed-fixiert (20261122), die Quellen sind commit-fixiert. Alle Dateneingaben sind read-only via git show. Die 240er Probe dient der schnellen Hypothesenprüfung; sie beansprucht noch keine Konvergenz der Monte-Carlo-Schätzung.

## Ergebnis der überprüften 240-Draws-Probe

Sechs Teams × sechs Wochen = 36 Team-Wochen. **33/36** haben am betreffenden As-of-Checkpoint vollständige projizierbare 13-Slot-Kader; W7 einmal und W8/W9 je einmal fehlt ein projizierbarer Kicker. 928 projizierbare Spielerwochen über alle sechs Wochen, davon nur **429 mit damaligem ESPN-ProviderStatus**, **499 mit UNKNOWN**. Die vollen damaligen Kader hatten 1.229 Spielerwochen und 465 Status-Zuordnungen (CP3f), ein anderer Nenner. Im hier relevanten Kandidatenpool sind 499/928 (53,8 %) ohne gemappten Status.

Die sechs Wochen wurden im **echten eingecheckten Research-Code**, mit separat über den GitHub-Connector geladenen, identischen Git-JSON-Bytes und JavaScript-Node-API-Stubs, in zwei Gruppen ausgeführt: W5–7 direkt; W8–10 nach Übergabe der **aus W5–7 berechneten** trainierten Status-Zähler und kumulierten BB-Werte. Der Fortschreibungsmechanismus ist dadurch auch für den W8–10-Teil auf die Vergangenheit beschränkt. Die 2026er W5–7-Stände für das zweite Segment waren:
- UNKNOWN n=253, played=196; ACTIVE n=191, played=190; QUESTIONABLE n=30, played=23; DAY_TO_DAY n=1, played=1.
- Gültige vorherige BB-Paare 17, Istsumme 3798,80 Punkte, Projektionssumme 3511,6792.

**Primäre Auswertung: 27 vollständige Team-Wochen W6–10 (W5 nur Warm-up), gepaart:**

| Verfahren | MAE gegen späteren As-of-Kader-Best-Ball | Bias (Forecast−Target) | Nominelle 80-%-Abdeckung |
| --- | ---: | ---: | ---: |
| Bedingter PWF-Projektions-BB, ohne Ziehungen | 31,32 | −14,10 | – |
| Gepoolter früherer Ist-/Proj-BB-Uplift | 31,14 | +7,31 | – |
| Unkorrigierter PI1-Monte-Carlo-BB | **33,90** | **+23,22** | 15/27 = 55,6 % |
| **Teilnahmebewusster PI1-Monte-Carlo-BB** | **30,13** | **+11,20** | **18/27 = 66,7 %** |
| Retrospektives Teilnahme-Oracle (nicht einsetzbar) | 29,31 | +14,44 | 18/27 = 66,7 % |

Der Teilnahmearm reduziert den MAE gegenüber Raw um **3,78 Punkte (~11,1 %)** und den positiven Bias um ca. 12 Punkte. Der gepoolte Uplift bleibt im Bias besser, während die Teilnahmesimulation im MAE rund 1,01 Punkte vorn liegt. **Kein deutlicher Sieger**, kleine Stichprobe, nicht unabhängig kalibrierte Priors. Die nominalen 80-%-Intervalle sind auch nach dem Schritt unterdeckend.

**Teilnahme-Klassifikationsdiagnostik**, auf allen 762 projizierbaren Kandidaten in W6–10, nach Abschluss jeder Woche gelabelt: vorläufiger Wahrscheinlichkeits-Brier ca. **0,0953**, naive „alle spielen“-Wahrscheinlichkeit **0,1194** (niedriger besser). Die ausgewerteten Labels beruhen auf positiven positionskonformen Snaps; bei W5–10 insgesamt 112 Kandidaten-Wochen fehlt ein Snap-Record (24/24/17/14/15/18). Sie werden hier als nicht teilgenommen gezählt, nicht als Verletzung; echte fehlende Snap-Erfassung könnte das Resultat verzerren. Kein p(play)-Kalibrierungszertifikat.

**Diagnostische Teilgruppen:**
- W5–7: 17 vollständig, Raw MAE 29,1311 / Teilnahme 25,4384. Für den primären W6–7-Walkforward: 11 vollständig, Raw MAE 36,1872 / Teilnahme 29,1763.
- W8–10: 16 vollständig, Raw MAE 32,3359 / Teilnahme 30,7833, gepoolter Uplift MAE 29,3152. Der zweite Abschnitt wurde mit exakt den W5–7-Trainer-Zählern gestartet.
- W10: nur zwei stark negativen ESPN-Status zugeordnete projizierbare Kandidaten (ein OUT, ein IR); die meisten p-Korrekturen kommen aktuell von UNKNOWN und QUESTIONABLE, **nicht** aus einem umfangreichen offiziellen Ausfall-Feed.

## Grenzen, CI, Architektur und Entscheidung

1. **Noch keine belastbare produktive Modellkalibrierung.** Nur 2026 W5–10, davon 27 vergleichbare Folgewoche-Team-Ergebnisse. Die Priors wurden heuristisch im Rahmen dieser Untersuchung gewählt und sind kein unabhängig validierter historischer Fit. Die Analyse ist explorativ, nicht blindem Holdout gleichzustellen.
2. **Kein echter Dienstag-/Sonntag-Lock-Replay.** Die sechs as-of-Commits liegen am Mittwoch vor dem ersten Spiel der Woche. Die damaligen späteren Roster-, Waiver- und Verletzungsänderungen bis zum individuellen Kickoff werden nicht modelliert. Die späteren finalisierten Snap- und PWF-Daten sind revisionierte Outcomes, keine punkt-in-zeit bestätigte vorherige Trainingspublikation. DNP≠Injury.
3. **PWF-Rangeform und Auswahl bleiben unkalibriert.** Die asymmetrischen PI1-Ranges werden als symmetrische Normalverteilung approximiert, keine Spieler-/NFL-Team-Korrelationen; CP3c und CP3d haben hier noch weitere Fehlerquellen identifiziert. Die simulierte Best-Ball-Verteilung ist kein Manager-Expected-Score ohne separates Coach-/Lock-Modell.
4. **Exakte Identität/Snapposition:** Für die Snap-Ziele werden nur Kandidaten-IDs und deren damalige Fantasy-Positionen genutzt (RB/HB-Alias in diesem Audit). Fremde NFL-Identitäts-/Positionskonflikte fließen nicht als DNP ein; widersprechende Snap-Positionen werden gezählt. Ein fehlender relevanter Snap bleibt mangels zusätzlichem Beglaubigungsnachweis ein Nonparticipation-Proxy.
5. **Validierung:** JS-Syntaxcheck, synthetischer Self-Test und sechs echte Wochen via Connector-gestützten Stub-Harness ausgeführt; im Split 17+16 vollständige Wochen. **Kein vollständiger echter Node-CLI-Lauf gegen lokalen Full-History-Git-Checkout** und kein Nachweis bereits abgeschlossener PR-CI für den neuen HEAD. Forschungscode in bestehendem Draft-PR #1623, nicht produktiv aktiviert. CI-Impact: keine neue Testfamilie, kein produktiver Fast-/Deep-Router oder Publisher; Research-Self-Test allein beweist keinen historischen End-to-End-CLI-Lauf.
6. **Architektur:** Die existierenden CP3b-Optimierer/Normal-RNG und CP3c-Snap-Helfer werden wiederverwendet. Keine neue Source-/Derived-/Consumer-Read-Kante, keine PWF-/Hybrid-/WinProb-/App-/Doku-/Writer-/Workflow-Änderung, keine Änderung an data-meta oder Handbuch. Revert des neuen Research-Files und dieses Berichts genügt.
7. **Nächster fachlicher Schritt:** Wahrscheinlichkeiten mit robustem as-of-Identity-/Statusfeed und größeren zeitlich separierten Daten/mehreren Trainingsfenstern prüfen, dann beste Kandidaten gegen dieselben echten As-of-Best-Ball-Targets und separat Manager-Scores/WinProbability evaluieren. Vorher **keine** produktive Aktivierung und kein Claim, das Monte-Carlo-Modell sei nun gut kalibriert.
