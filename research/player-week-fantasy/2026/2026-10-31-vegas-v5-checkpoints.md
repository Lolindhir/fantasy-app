# PlayerWeekFantasy – Original-Checkpoints aus Issue #978

Dies ist die **wortgetreue historische Audit-Evidenz** der Forschungs- und Reproduktionsschritte 3–9 aus [Issue #978](https://github.com/Lolindhir/fantasy-app/issues/978), Stand 31.10.2026. Frühere Zwischenstände bleiben bewusst enthalten und können durch spätere Checkpoints korrigiert werden. Aktuellen Ergebnisstatus ausschließlich dem [konsolidierten Research-Audit](2026-10-31-vegas-v5-research-audit.md) entnehmen.

---

## Research-Checkpoint 3 – RB-V5-Ablation 28.10.2026

**Freigabe 28.10.2026:** begrenzter explorativer Read-only-Ablationstest V4-C vs Relative Vegas vs rollenabhängiges Vegas vs rollenabhängiges Vegas + Defense, nur RB; kein produktiver Modell-/Generator-/Workflow-Write.

### Rechenstand / Daten
- **2024:** 964 vergleichbare RB-Spieler-Spiele (W4–17; 470 Entwicklung W4–10 / 494 Parameterauswahl W11–17). Kalibrierte Gewichte anschließend aus allen 964 2024-Fällen neu geschätzt. **2025:** 951 vergleichbare RB-Spieler-Spiele (W4–17) mit fixierten 2024-Gewichten.
- Gleiche Stichprobe für alle Varianten; nur RB mit tatsächlichen Carries+Targets > 0, mindestens zwei früheren aktiven Saisongames und drei abgeschlossenen früheren Teamgames, V4-C-Projection.Status=available und finalen liga-spezifischen PWF-Actuals.
- Quellen: `data-source/providers/nflverse/player-stats/raw-2024.csv` / `raw-2025.csv` für Pregame-Historie/Opportunity, GSIS→CanonicalPlayerID über `data-source/nfl/rosters/<season>.json`; `data-derived/player-week-fantasy/nfl-reise/<season>/<week>.json` für V4-C-Basis und Liga-Actual; `data-derived/nfl-games/<season>.json` für ImpliedTeamPoints, Spread und Total. Nur vorherige Spielwochen bei der Featurebildung; **historische Odds nicht mit zertifizierter Pre-Kickoff-Timestamp**.
- Spot-Parität Raw→canonical `data-source/nfl/player-stats/**`: W05/2024 75/75 RB-Zeilen, W05/2025 86/86 RB-Zeilen stimmen für Team/Carries/Targets/Rushing- und Receiving-Yards. Noch **kein** Vollparitäts-Audit über 34 Wochen.
- Features B: relative ImpliedTeamPoints gegenüber letzten 3 Teamspielen, implied Team-Punktedifferenz, Total. C: Carries-/Targets-Trends, historisch geglättete Receiving-Opportunity-Quote und deren Interaktionen mit Delta/Spread. D: zusätzlich per gegnerischem Team und früheren Spielen opponent-normalisierte RB-Target-Rate, Rush-YPC und Rec-YPT (Shrinkage n/(n+4), 6 frühere Defense-Games). Position-only Baseline bleibt unverändert. Ridge-Raster 8/32/128/512 und Clip ±1/2/3 Punkte, Auswahl nur 2024 W11–17.

### Ergebnisse 2025 (N=951, MAE / RMSE)
| Variante | MAE | RMSE | Delta MAE vs V4-C | Woche-Cluster-Bootstrap 95 %-Intervall Delta |
|---|---:|---:|---:|---:|
| A V4-C | 5,0649 | 7,0116 | – | – |
| B Relative Vegas | **5,0301** | 6,9602 | **−0,0348** (−0,69 %) | [−0,0701; +0,0042] |
| C Rollen+Vegas | 5,0496 | 6,9507 | −0,0153 (−0,30 %) | [−0,0557; +0,0209] |
| D Rollen+Vegas+Defense | 5,0542 | 6,9474 | −0,0107 (−0,21 %) | [−0,0652; +0,0363] |

**Sekundäre, nicht unabhängige Rangpaar-Proxy:** 7.612 wochengleiche RB-Paare verschiedener NFL-Teams mit V4-C-Basisabstand 0,5–3,0 Punkten, beide tatsächlich eingesetzt, ohne Gleichstand im Outcome: Treffer A 57,74 %, B 58,17 %, C 58,33 %, D 58,15 %. Keine echten Fantasy-Lineup-/Waiver-Entscheidungen; Paare überlappen stark und eignen sich nicht für unabhängige Signifikanztests.

**Interpretation:** B ist im 2025-MAE der beste getestete Kandidat; Rollen und opponent-normalisierte Defense verbessern den MAE gegenüber B **nicht**. Zusätzliche Features senken teilweise RMSE und verbessern Paar-Ranking geringfügig, aber keine belastbare Start/Sit-Relevanz bewiesen. Wochen-Bootstrap-Intervalle enthalten Null. 2025 wurde in vorheriger Forschung bereits inspiziert und ist kein wirklich neuer untouched Holdout. Ergebnis bleibt **inconclusive**, nicht produktionsreif.

**Reproduzierbarkeit:** Auswertung in diesem Chat mit read-only Connector und separatem lokalem Python-Forschungsskript `rb_v5_ablation.py` (Chat-Artefakt, **nicht** im Repository); das Skript rechnet aus denselben Source- und PWF-Dateien und schreibt nichts. Der Lauf des Python-Skripts gegen eine vollständige lokale Repo-Kopie sowie die vollständige Canonical-Raw-Parität sind noch als separate Audit-Gates offen; direkte Zahlen wurden mit dem interaktiven JS-Forschungsdurchlauf berechnet. Keine produktiven Modellparameter, Repo-Skripte, Quell-/Derived-Daten oder Workflows verändert.

**Nächster Handoff:** Vor jeder Modellentscheidung (1) Forschungs-Skript gegen vollständigen Repo-Checkout unabhängig ausführen und Ergebnisse abgleichen, (2) Vollparität Raw↔Canonical W1–17 prüfen, (3) echte Pregame-Odds-Snapshots mit Zeitstempel über neuere Prospektivwochen sammeln, (4) Start/Sit anhand zeitlich korrekt verfügbarer Roster-Alternativen statt überlappender hypothetischer Paare validieren. #978 bleibt `status:analysis`; #697-Produktionsmodell unverändert.


## Handoff 29.10.2026 – Freigabe unabhängige Audit-Gates

**Nutzerfreigabe:** „ok, Freigabe für dies“ im Anschluss an den Vorschlag eines read-only RB-V5-Tests. Der bereits am 28.10. dokumentierte Ablationslauf (2025 N=951; B bester MAE; insgesamt inconclusive) wird **nicht** als neu durchgeführter Test ausgegeben. Diese Freigabe erlaubt die ausstehenden reproduzierbaren Research-/Audit-Schritte, **keine** Aktivierung eines Produktivmodells oder Änderung an produktiven Pipelines.

**Aktuelle Überprüfung (29.10.):** Der gespeicherte Research-Checkpoint vom 28.10. enthält 2024-Entwicklung/Validierung, 2025-Testwerte, einen JS-Explorationslauf, und den Hinweis auf ein ausschließlich als Chat-Artefakt vorhandenes Python-Skript. Eine unabhängig ausgeführte Reproduktion des Skripts gegen einen vollständigen Checkout ist weiterhin **nicht nachgewiesen**. Die GitHub-Connector-Lesung umfangreicher kanonischer wöchentlicher player-stats / weekly-rosters liefert keinen nutzbaren vollständigen Body; der Chat-Container besitzt keinen Repository-Checkout und kann Github.com nicht per Git/HTTP erreichen. Ein unabhängiger Vollparitäts-/Replay-Lauf lässt sich aus dieser Ausführungsumgebung nicht seriös bestätigen.

**Offene konkrete Audit-Gates:**
- [ ] Vorhandenes read-only rb_v5_ablation.py aus dem früheren Chat-Artefakt wiederherstellen bzw. gleichwertiges Reproduktionsskript versionieren und gegen einen **vollständigen lokalen Checkout** laufen lassen.
- [ ] Exakte Gleichheit der 2024/2025-Populationen, MAE/RMSE und Variantenkoeffizienten mit dem 28.10.-Checkpoint verifizieren; Abweichungen dokumentieren, nicht glattziehen.
- [ ] Vollständige Raw→Canonical-Parität der verwendeten Spieler-/Defense-Statistiken prüfen, nicht nur W05-Spotchecks.
- [ ] Pregame-Line-Provenance und historisches Odds-Leakage sichtbar markieren; echte zeitgestempelte Prospektiv-Snapshots separat sammeln.
- [ ] Ex-ante realistische Start/Sit-Alternativen für einen späteren Entscheidungsbacktest definieren und 2025 nicht wieder als untouched Holdout deklarieren.

**Status:** Research/Audit nicht abgeschlossen. Kein neuer V5-Ergebniswert berechnet, kein Produktiv-Write, kein Scheduler-/Modelländerung. Issue bleibt status:analysis.


## Audit-Checkpoint 4 – unabhängige Datenprüfung und B-Nachrechnung (29.10.2026)

**Technischer Zugang gelöst:** Große Source-Dateien lassen sich über GitHub-Blob-SHA mit dem verbundenen GitHub-Connector vollständig lesen. Die vorherige Aussage, Raw/Canonical-Daten seien hier unzugänglich, ist überholt. Eine lokale Repository-Kopie liegt weiterhin nicht vor.

**Vollständiger RB/FB-Raw↔Canonical-Feldvergleich 2024/25, REG W01–W17 (Read-only):**
- 2024: 1.515 Raw-Zeilen, 1.515 Canonical-Zeilen, 1.515 1:1 zugeordnet; 0 fehlende Zeilen, 0 Abweichungen in den geprüften Merkmalen.
- 2025: 1.548 Raw-Zeilen, 1.548 Canonical-Zeilen, 1.548 1:1 zugeordnet; 0 fehlende Zeilen, 0 Abweichungen.
- Join per (Week, GSIS PlayerID, game_id); Felder: Team, OpponentTeam, carries, targets, receptions, rushing_yards, receiving_yards, rushing_tds, receiving_tds. Kontrolliert wurden die **für die RB-Research-Frage wesentlichen Felder**, nicht sämtliche NFL-Statistiken.
- 2024/25 enthalten über diese 34 Wochen insgesamt 3.063 passende RB/FB-Spieler-Spiel-Zeilen ohne Abweichung bei den genannten Feldern.

**Unabhängige Baseline-Reproduktion mit Raw, saisonalem Canonical-Roster-GSIS, nfl-games und PWF:**
- Gleiche Eligibility-Gates wie im 28.10.-Checkpoint: nur RB, W4–17, carries+targets > 0, ≥2 frühere aktive Player-Games, ≥3 frühere Team-Games, V4-C verfügbare Projection und league-scored finale Actuals.
- 2024 erneut exakt **N=964**; V4-C MAE **4,97607946**, RMSE **6,46981059**; 2024 W4–10 N=470, W11–17 N=494.
- 2025 erneut exakt **N=951**; V4-C MAE **5,06488297**, RMSE **7,01159491**. Dies reproduziert die zuvor im Issue berichteten Ausgangswerte.

**Zweite, explizit eigenständig definierte Variante B (NICHT die alten B-Koeffizienten):**
- Residuelle additive Ridge-Regression mit Intercept, z-standardisierten drei Eingängen (Team-ImpliedPoints minus last-three team actual PPG; eigener implied margin; NFL market total), Ridge-Raster 8/32/128/512, Korrektur-Caps ±1/2/3. Hyperparameter auf 2024 W4–10 trainiert und W11–17 gewählt, dann nur 2024 W4–17 refit, **2025 vollständig ohne Gewichtsänderung** evaluiert.
- Gewählt: Ridge=512, Clip=±2 Fantasy-Punkte. 2025 **MAE 5,00200997**, RMSE **6,98354033**, Bias **−0,70367533**. Gegen V4-C 2025: ΔMAE **−0,062873** bzw. −1,24 %. Frühere Variante B vom 28.10. hatte MAE 5,0301/RMSE 6,9602 – **nicht als exakte Reproduktion dieser früheren Variante interpretieren**.
- Aus 10.000 deterministischen Week-Cluster-Bootstrap-Samples der 14 Wochen 2025: nominales 95%-Intervall für ΔMAE **[−0,1002; −0,0258]** (JS-Lauf). Dies ist nur Binnenstichproben-Unsicherheit unter den zugrunde gelegten historischen Features; **keine** zertifizierte prospektive Vorhersagegüte und 2025 ist nach wiederholter Modellinspektion **kein untouched Holdout**. Historische nflverse-Odds verfügen weiterhin über keinen belegten ursprünglichen Pregame-Beobachtungszeitpunkt.
- Überlappende RB-Rangpaare anderer Teams, Basisabstand 0,5–3,0 Punkte: 7.612 Paare; Treffer V4-C 4.395/7.612=57,74 %, unabhängiges B 4.429/7.612=58,18 %. Kein echter Manager-Start/Sit-Test; Paare nicht unabhängig.

**Reproduktionsartefakt:** Eigenständiges Python-3-Standardbibliothek-Skript `rb_v5_replay_audit.py` als Chat-Datei erstellt (read-only; prüft die geprüften RB/FB-Felder, Population, V4-C und neue B-Korrektur). Python-Syntaxprüfung erfolgreich; **End-to-End-Lauf dieses Python-Skripts gegen einen vollständigen Checkout ist noch ausstehend**. Die o.g. Zahlen stammen aus tatsächlich ausgeführter unabhängiger JS-Berechnung direkt auf Connector-Git-Blobs.

**Weiterhin offen:** exakter Replay der alten B/C/D-Koeffizienten aus dem 28.10.-Skript, unabhängige komplette Rollen- und Defense-Ablation, echtes historisch bezeugtes Pregame-Odds-Archiv, prospektive und reale Start/Sit-Entscheidungsprüfung. V4-C Produktion, Source, Workflows, CI und Angular unverändert; Issue `status:analysis`.


## Audit-Checkpoint 5 – Originalskript wiedergefunden, vollständige B/C/D-Reproduktion (29.10.2026)

**Wesentliche Korrektur zu den Hand-offs 3/4:** Die ursprüngliche Chat-Datei `rb_v5_ablation.py` vom 28.10. wurde in der persönlichen ChatGPT-Dateibibliothek unter genau diesem Dateinamen wiedergefunden und der vollständige **336-zeilige Python-Quelltext** gelesen. Raw-Dateimaterialisierung dieses Library-Files in den lokalen Container wurde abgelehnt; der Quelltext konnte jedoch vollständig inspiziert werden. Über den GitHub-Connector lassen sich sämtliche benötigten großen Source-Git-Blobs auslesen.

**Unabhängige Reproduktion der ORIGINALEN Modellform (aus dem wiedergefundenen Quelltext, in JS neu umgesetzt):**
- Original 2024: N=964, Entwicklung W4–10 N=470, Validierung W11–17 N=494; V4-C MAE=4,9760794606, RMSE=6,4698105920. Gewichte mit exakt den Funktionen/Features/Clips/Ridge-Tie-Breaks des Original-Python-Skripts anhand der Original-Quellen neu geschätzt. Gewählte Parameter: B Ridge 32/Cap ±1; C Ridge 128/Cap ±1; D Ridge 128/Cap ±2.
- Original 2025: N=951. A V4-C MAE=5,0648829653, RMSE=7,0115949146. B Relative Vegas MAE=5,0300933373, RMSE=6,9601658950. C Roles+Vegas MAE=5,0496252431, RMSE=6,9506997049. D Roles+Vegas+Defense MAE=5,0542253164, RMSE=6,9473823897.
- Die Werte stimmen **in allen ausgewiesenen vier Dezimalstellen** exakt mit dem datierten Research-Checkpoint vom 28.10. überein, nicht nur die Stichprobengrößen. Der ursprüngliche Report wurde also unabhängig auf demselben Datenstand und derselben Modellform nachvollzogen.
- Hypothetische RB-Paare mit Basisabstand 0,5–3 Punkte, unterschiedliche NFL-Teams: 7.612 Paare. Treffer: A=57,7378 %, B=58,1713 %, C=58,32895 %, D=58,1450 %. Auch die ursprünglich berichteten Paar-Trefferquoten stimmen exakt.
- Aus dem Original-Pythoncode geprüft: D berechnet defensive Features als bis zur Zielwoche bekannte **opponent-normalisierte Residuen** (Allowed minus historische gegnerische Offense-Baseline), dann bis zu sechs frühere Defensive-Games und Shrinkage; kein Import von W-Actual in W-Features. Rollenmerkmale nutzen frühere Carries/Targets, glattes Target-Share (t+2)/(c+t+4) und Vegas-Interaktionen. Keine zusätzlichen Features still eingeführt.

**Wichtig zur Einordnung:** Der ursprüngliche Python-Code wurde **nicht** selbst in einer vollständigen lokalen Repository-Kopie ausgeführt; stattdessen wurde seine Mathematik unabhängig im verbundenen JS-Ausführungsweg reproduziert. Aufgrund exakter Übereinstimmung bei Kohorten, Parameterauswahl, A/B/C/D-MAE/RMSE und Paarmaßen ist der fachliche B/C/D-Replay-Check mit belastbarer Rechenparität abgeschlossen. Es bleibt eine optionale buchstäbliche Python-End-to-End-Runner-Verifikation (Environment/Runtime), nicht mehr der vorherige fehlende Zahlenabgleich.

**Ergebnis:** Das ursprüngliche D-Modell gewinnt keinen MAE gegenüber B; die Hypothese, dass mehr Rollen-/Defense-Merkmale nachweisbar bessere Fantasy-Punktprognosen liefern, ist derzeit **inconclusive**. Die separate neu definierte B-Variante aus Checkpoint 4 ist ein zusätzlicher explorativer Kandidat und **nicht** stiller Ersatz für die Originalmodellformen. 2025 kein echter unangetasteter Holdout; Odds-Provenance ohne garantierten historischen pre-kickoff-Zeitpunkt; überlappende Rangpaare sind keine realen Start/Sit-Entscheidungen. Kein produktiver V4-C/V4-C-PI1- oder Workflow-Change.

**Offene Forschungsfragen nach diesem Audit:** (1) neuere zeitgestempelte Pregame-Odds-Observationen für prospektive, strikt leakagesichere Validierung, (2) echter Fantasy-Start/Sit-Paarvergleich mit zu dieser Zeit zulässigen Roster-/Lineup-Alternativen, (3) optional reine Python-Runner-Parität auf einem vollständigen Checkout, ohne dafür neue Workflows einzuführen. Status weiterhin `status:analysis`.


## Research-Checkpoint 6 – entscheidungsorientierter Modellbenchmark (29.10.2026)

**Nutzerauftrag / Scope:** Nach dem reproduzierten RB-V5-Audit wurde explizit die Neuausrichtung der Evaluation auf *Start/Sit* (primär) und *Waiver-/Roster-Entscheidungen* (sekundär) freigegeben. Dieser Checkpoint ist **read-only Research und Machbarkeitsprüfung**. Kein V5-Cutover, keine produktive Modell-/Source-/Derived-/App-/CI-/Workflowänderung. Modellowner bleibt #697, Weekly Decision Owner #206, menschliche Postmortems #208. Keine parallele Projektions- oder Scoring-Wahrheit aufbauen.

### Evaluationsziel / vorab festgelegte Maße

- **Primär: tatsächlich erzielte Lineup-Punkte bei gleicher ex-ante legaler Entscheidungsmenge.** Für V4-C und einen Challenger dieselben Fantasy-Team-/Wochen-/Decision-Time-Kandidaten, Slots, Locks, Scoring-, Availability- und Ersatzregeln verwenden. Verglichen wird *Challenger-Actual minus V4-C-Actual* in PPR je Team-Woche (paired); nach Saison/Woche und Entscheidungstyp ausweisen. Mehr tatsächliche Lineup-Punkte sind das direkte Nutzensignal.
- **Outcome-/Points-Regret (sekundär):** `best_hindsight_points(gleicher ex-ante legaler Pool) - actual_points(des Modells)`. Das ist **hindsight Outcome-Regret**, nicht retrospektiv bewiesener *Decision Regret* im Sinn der bestehenden Weekly-Reviews. Dass der gleiche Oracle-Term beim gepaarten Modellvergleich wegfällt, ausdrücklich sichtbar halten. Nicht einen unbeschränkten All-Roster-Best-Ball-Oracle als real einsetzbare Aufstellung deklarieren.
- **Boundary Decision Accuracy (sekundär):** nur echte, zum Entscheidungszeitpunkt austauschbare Start-/Sit-Alternativen an einer Starter/FLEX-Grenze; Gewinner nach finalen Liga-Punkten, Gleichstände separat, keine willkürlichen paarweisen Cross-Team-RB-Kombinationen oder pseudo-unabhängigen 7.612 Paare.
- **Diagnostik:** Spieler-MAE/RMSE/Bias, Coverage (Anteil vollständiger, korrekt rekonstruierter Team-Wochen / Kandidaten), fehlende Historie, DNP/Bye/Inactive, Positions- und Playoff-Splits; diese Werte sind nicht alleinige Ship-Kriterien.
- **Spätere getrennte Waiver-/Roster-Evaluation:** nur vor dem Waiver verfügbare Spieler, tatsächliche Transaktions-/Roster-/Cap-/Slot-Kosten, marginale startbare Mehrwochenpunkte und echte Replacement-Alternative; Dynasty-/Markt-/Upside-Wert nicht fälschlich mit kurzfristigem PPR gleichsetzen.
- **Unsicherheit/Überoptimierung:** gepaarte Auswertung pro Fantasy-Team-Woche, Week-Cluster-Bootstrap und Stabilität über Seasons. 2025 ist nach mehrfacher Inspektion **kein unangetasteter Holdout**; keine neue Variante an 2025 selektieren und anschließend als prospektiv validiert ausgeben.

### Vollständiger Daten-Join-Audit, 2024 und 2025 W04–W17, tatsächlich ausgeführt (GitHub-Dateien/Blobs, JS; read-only)

Basis: `data-source/leagues/nfl-reise/seasons/{season}/league.json`, `matchups/week-{w}.json`, `data-derived/player-week-fantasy/nfl-reise/{season}/{w:02d}.json`. 2025/W04 zusätzlich vollständige `data-source/nfl/weekly-rosters/2025/04.json` und Position-Join geprüft. Es wurden **nicht** die Berechnungen eines vollständigen lineupspezifischen Ex-ante-Backtests ausgeführt.

| Prüfkriterium | 2024 W04–17 | 2025 W04–17 |
|---|---:|---:|
| Fantasy-Team-Wochen | 84 | 84 |
| Historische feste Starter pro Team | 12 | 13 |
| Tatsächliche Starter-Zeilen | 1.008 | 1.092 |
| Starter mit V4-C-Projektion | 1.008 | 1.091 |
| Wochen-Roster-Player-Zeilen | 2.270 | 2.683 |
| Player-Zeilen mit verfügbarer V4-C-Projektion | 2.096 | 2.484 |
| Matchup-Player ohne PWF-Record | 162 | 182 |
| Davon mit >0 offiziellen Matchup-Punkten | 0 | 0 |
| Final-Scoring-Differenzen bei vorhandenem PWF-Record | 0 | 1 |

Die einzige 2025-Differenz ist **W06, +0,50 PWF zu League-Points** für CanonicalPlayerID `NFLP-3c5ddc5072f6fe8f9b77`; der bereits dokumentierte, eng akzeptierte W06-Scoring-Fall ist vor einem Lineup-Lauf explizit mit der bestehenden Ausnahme-Policy abzugleichen, nicht still auszugleichen. Alle fehlenden PWF-Player-Records betreffen **0-Punkt-Spieler, keine Starter**. Der eine Starter ohne verfügbare V4-C-Projektion liegt in **2025 W10**. Coverage/fehlende Prognosen niemals als tatsächliche Null-Projektionen auffüllen.

**Explorativer Ansatz abgebrochen / nicht als Modellresultat freigegeben:** Ein erster Versuch, aus dem gesamten finalen Matchup-`Players`-Wochenpool die auf V4-C basierte optimale Aufstellung zu berechnen, wurde explizit verworfen. Der Pool enthält laut bestehendem TWP-Vertrag auch **Fantasy-IR/Reserve und Taxi** und ist ein *retrospektives All-Roster-Potential*, kein nachweislich zum Kickoff legaler Start/Sit-Pool. Ein Vergleich dieses Oracles mit wirklichen Managerstarts wäre unfair; die resultierenden Zahlen sind daher **keine validen Start/Sit- oder V4-C-Qualitätskennzahlen**. W05/06 fehlende PWF-Records waren überwiegend finale 0-Punkte-Fälle; nur der separat verifizierte W06-Fall war eine echte PWF-vs-League-Differenz.

### Verbindliche Ex-ante-Eligibility-Gates vor einem echten Decision-Backtest

- **Historical provenance:** pro Entscheidungszeitpunkt dokumentierte Fantasy-Ownership, Starter/Bench, Reserve/IR, Taxi, verfügbare Lineup-Slots sowie Kickoff-/Player-Locks. Finale Matchup-Players allein reichen ausdrücklich nicht. Ohne attestierbare Pre-Lock-Daten nur *retrospective week-pool proxy* mit eigenem Status, kein echter Start/Sit-Backtest.
- **Lineup-Legalität:** Saison-`RosterPositions` aus kanonischer League, FLEX-Eligibility aus bestehender `FantasyRelevanceV2Utils.psm1` / `ExportWeeklyPerformanceSlots.ps1`, globaler Assignment-Optimizer `tools/weekly_lineup_optimizer.py`; IR/Taxi nicht als freie Bench interpretieren; AutoSub und Late-Swap zeitpunktgetreu behandeln. Kein neues paralleles Eligibility-/Scoring-System.
- **Ex-ante Modellzustand:** V4-C-Felder und Challenger-Korrekturen nur soweit die Inputfakten zum Entscheidungszeitpunkt verfügbar waren. Das PWF-Modell ist *conditional-on-participation*; separate Availability-/Inactive-Policy muss ausgewiesen werden. Retrospektiv materialisierte NFL-Wochen-Roster sind kein Beweis damaliger Verfügbarkeit.
- **Scoring/Finality:** nur finale liga-spezifische Actuals, fail-closed bei ungeklärter Differenz; bekannte explizite Ausnahmen sichtbar. Kein Outcome-Leakage in Candidate-Filter, Gewichte, Entscheidungszeitpunkte oder Week-Wahl.
- **Vegas-Provenance:** B/C/D vor produktiver Empfehlung mit belegten Pre-Kickoff-Odds testen; historische Odds ohne zeitlichen Snapshot genügen nicht.
- **Vergleichseinheit:** gleiche rekonstruierte Team-/Week-/Decision-Window-Population für A/B/C/D, und nur vollständig auflösbare Cases in den gepaarten Hauptvergleich; fehlende Fälle/Selektionsbias gesondert ausweisen.

### Handoff / offener Ablauf

- [x] Primäre/sekundäre Zielmetriken mit Outcome-vs.-Decision-Regret-Abgrenzung definiert.
- [x] Bereits vorhandenen PWF-/TWP-/Lineup-Optimizer-/FLEX-Contract geprüft; keine neue Berechnungshoheit nötig.
- [x] Beide historischen 14-Wochen-Kohorten auf Starter-/Prognoseabdeckung und finales Scoring gegengeprüft.
- [x] Unzulässigen All-Roster-Week-Pool-Shortcut erkannt und als **nicht valide** ausgeschlossen.
- [ ] Nachweisbar zeitlich korrekten Fantasy-Bench-/IR-/Taxi-/Lock-Kandidatenpool für repräsentative historische Team-Wochen rekonstruieren; dokumentieren, welche Team-Wochen *genuinely evaluable* sind.
- [ ] Erst danach echten paired Lineup-Entscheidungsbacktest V4-C vs. historische B/C/D auf derselben legalen Population ausführen; Validierungsbefunde von Optimierungs-/Kandidatenwahl trennen.
- [ ] Für 2026+ zeitgestempelte Prospektivdaten (Roster-, Lineup-, Availability-, Projection- und Vegas-As-of) spezifizieren; etwaige neue persistierende Snapshot-Automation ist **nicht** durch diesen Audit freigegeben.
- [ ] Mehrwochen-Waiver-/Roster-Nutzen als getrennte spätere Auswertung implementieren.

**Aktueller Befund:** Hohe Starter-Projektionsabdeckung, aber **kein valides empirisches Start/Sit-V4-C-vs.-Vegas-Ergebnis**. V4-C bleibt produktiv. Issue bleibt `status:analysis`; weder Modellfreigabe noch neue Scheduler-/Writer-Freigabe.


## Research-Checkpoint 7 – tatsächlicher 2025-RB-Lineup-Proxy A/B (30.10.2026)

**Autorisierter Auftrag:** Nach Checkpoint 6 ausdrücklich „mach das jetzt“ zur tatsächlichen Evaluation von V4-C vs. Vegas für Fantasy-Start/Sit. Durchführung im Chat als read-only Berechnung über die vollständigen GitHub-Connector-Dateien/Blobs; keine App-/Generator-/Workflow-/Modell-/Source-Änderung. Der historisch *tatsächlich* legale Pre-Lock-Roster lässt sich aus den vorhandenen Wochen-Matchups **nicht belegen**. Deshalb wurde kein solcher Test behauptet; stattdessen ein vollständig berechneter, strikt beschrifteter **retrospektiver RB-Same-Team-Week-Pool-Proxy** mit Sensitivitätsfilter ausgeführt.

### Kontrolllauf: Original-Vegas-B exakt reproduziert

- Originalskript `rb_v5_ablation.py` aus dem ChatGPT-Library-Text erneut vollständig gelesen (336 Zeilen). Modell B: nur `delta`, `spread`, `total - 43`, Ridge-Regression ohne Intercept, z-artige Feature-Skalierung mit mindestens 0,3, transformierte Features auf ±5 begrenzt, additive Korrektur auf ±1 PPR begrenzt.
- 2024 aus Canonical NFL/roster, nflverse-Raw-Player-Stats, Derived `nfl-games` und allen PWF W04–17: **N=964**, Train W04–10 **470**, Validation W11–17 **494**, gewählte Hyperparameter **Ridge=32, Cap ±1** (exakt ursprüngliche Wahl).
- Fit auf 2024 W04–17: `scales=[5.383053446953886,5.822561066872184,3.7963963158615357]`, `beta=[0.6276102919511259,0.38397058670518025,0.2160081772927129]`.
- Exakte unabhängige 2025-Reproduktion auf ursprünglicher aktiver RB-Population **N=951**: V4-C **MAE=5.0648829653, RMSE=7.0115949146**; B **MAE=5.0300933373, RMSE=6.9601658950**. Keine Variante neu anhand von 2025 selektiert. Historische Odds-As-of weiterhin *nicht* belegt.

### Neu tatsächlich ausgeführter RB-Same-Team-Week-Pool-Proxy

**Rechenregel:** 2025 W04–W17, sechs historische Fantasy-Teams pro Woche. Zum festgestellten Week-Final-Pool `matchups.Players` die nach Wochendaten positionierten RBs mit verfügbarer PWF-V4-C-Prognose bestimmen; Anzahl der als `Starters` tatsächlich eingesetzten RBs je Team beibehalten, Nicht-RBs unverändert lassen. Dieselben RB-Kandidaten einmal nach V4-C und einmal nach V4-C+B ordnen, jeweils oberste `k` nehmen; die ausgewählten RBs anhand der **offiziellen League-`PlayerPoints`** auswerten. Für B: NFL-Team/Position aus dem historischen **aber erst nachträglich finalisierten** NFL `weekly-rosters` der Zielwoche, Vorwochen-Spielerusage aus Raw, Team-Punkte nur vor der Zielwoche, Original-Vegas-Signal aus Derived `nfl-games`. Bei fehlender vorheriger RB-Historie oder Vegas-Basis keine Korrektur. Nie aus Zielwochen-Carries/Targets selektieren. Keine Parallel-Neuberechnung von offiziellen Ist-Punkten oder gesamten Lineup-Regeln.

**Nicht rekonstruierte Aspekte:** Der Finale `matchups.Players`-Pool enthält IR/Reserve/Taxi und kann spät hinzugefügte oder bereits gelockte Spieler umfassen. `weekly-rosters` ist kein Pregame-Snapshot; `Status=ACT` dort ist NFL-Kaderstatus, nicht Fantasy-Startberechtigung. Es fehlen per Decision-Time belegte Fantasy-IR-/Taxi-/Lock- und Availability-Snapshots, verlässlich historische Odds-As-of-Observations und ggf. AutoSub-/Late-Swap-Intentionen. Deshalb **kein echter Pre-Lock-Start/Sit-Backtest, kein belegter ex-ante erzielbarer Vorteil**. Die konstante Zahl RB-Starter ist nur ein begrenzter RB-Teilentscheid, nicht ein kompletter positionsübergreifender Lineup-Optimizer.

| RB-Proxy-Kennzahl | Gesamter finaler Week-Pool | Sensitivität: NFL-Status ACT |
|---|---:|---:|
| Team-Wochen vorhanden | 84 | 84 |
| Evaluierbare Team-Wochen | **83** | **83** |
| Geänderte RB-Auswahlen V4-C → B | **12** | **14** |
| Davon B mit mehr tatsächlichen PPR | **8** | **9** |
| Davon B mit weniger tatsächlichen PPR | **4** | **5** |
| Paired RB-Punktedelta B − A, gesamt | **+50,2** | **+37,4** |
| Mittelwert gesamt über 83 Team-Wochen | **+0,605 PPR/Team-Woche** | **+0,451 PPR/Team-Woche** |

- Die eine ausgeschlossene Team-Woche: **2025 W10**, `clr-5c3b56e348de5d1697e556f62c439c2d`, Starter `NFLP-cece7b470136fb434cf9` fehlt im finalen NFL-Wochen-Roster und hat keine verfügbare PWF-Prognose; 0 tatsächliche League-Punkte. Fail-closed, nicht als Prognose=0 ergänzen.
- Week-Pool-Paired-Deltas W04–W17 (PPR über evaluierbare Team-Wochen pro Woche): `+5,4; +8,2; 0; +7,2; 0; 0; 0; 0; 0; −2,0; −5,6; +30,0; −6,4; +13,4` = `+50,2`.
- Explorativ 10.000 deterministische resampling-Durchläufe über Wochencluster (14 Wochen, jeweils Team-Wochen gewichtet), nominales 95%-Perzentilintervall für **gemitteltes Delta je Team-Woche**: ungefähr **[−0,083; +1,445] PPR**. Umfasst Null. Bereits mehrfach inspiziertes 2025 ist kein untouched Holdout; Intervall kein prospektiver Qualitätssicherungsbeleg.
- Dass im restriktiven NFL-ACT-Proxy mehr als im vollständigen Pool gewechselt wird und der Gesamtvorteil von 50,2 auf 37,4 sinkt, ist ein konkretes Zeichen für die **hohe Sensitivität auf Kandidaten-/Availability-Filter**, nicht für exakte Robustheit von B.

### Handoff

- [x] Gleiche originale A/B-Rechenform und 2025-Modellmaße unabhängig reproduziert.
- [x] Retrospektive Same-Fantasy-Team-RB-Auswahlen vollständig W04–W17 gegeneinander gerechnet.
- [x] 2025/W10-Datenlücke fail-closed ausgeschlossen; offizielle League-Istpunkte statt unbestätigter PWF-Differenz gewählt.
- [x] Sensitivität auf bekannten finalen NFL-Rosterstatus ACT getestet; uncertainty / Bias / Outcome-vs.-Decision-Regret transparent dokumentiert.
- [ ] Pre-Lock-legaler Entscheidungspool bleibt **offen**; nur mit tatsächlich zeitgestempelten historischen/fortlaufenden Fantasy-Ownership, aktiver Bench/IR/Taxi, Spieler-/Slot-Locks, Availability und Odds sinnvoll. Keine unbelegte Legalität aus `matchups.Players` oder NFL-`Status=ACT` annehmen.
- [ ] Mit solchen Daten später **vollen legalen Paired-Lineup-Backtest** und separat Mehrwochen-Waiver-/Roster-Backtest entwickeln; nicht aus +50,2 Proxy-PPR einen produktiven Vegas-Rollout begründen.
- [ ] Eine neue automatische persistente Pre-Lock-Snapshot-Sammlung hätte eigenständige Data-/Writer-/Publication-Auswirkungen und erfordert entsprechende gezielte Freigabe/Architekturprüfung vor Implementierung.

**Status:** Forschung liefert ein vorläufiges positives, aber statistisch und historisch nicht gesichertes RB-Entscheidungssignal. Original-V4-C und V4-C-PI1 bleiben produktiv unverändert. Issue #978 `status:analysis`; kein neues produktives Modell, kein GitHub-Actions-Workflow, keine Änderungen an Shared-Derived/Canonical Source.


## Research-Checkpoint 7 – echte Pregame-App-Snapshots, RB-Vegas-Entscheidungsproxy (30.10.2026)

**Auftrag:** Nutzer hat die sofortige Prüfung historisch tatsächlich verfügbarer Start/Sit-Alternativen und den Vergleich V4-C vs. ursprüngliche Vegas-B-Korrektur explizit freigegeben („OK verstehe, mach das jetzt“). **Ausführung:** direkte, read-only GitHub-Connector-/Git-Blob- und JS-Rechnung, keine Produktions-/Workflow-/Quelldatenänderungen. Das Ergebnis ist ein **Pregame-Roster/Projection-Snapshot-basierter Research-Proxy, keine zeitlich vollständig zertifizierte Vegas-Performance**.

### Originale B-Modellform unabhängig aus 2024 rekonstruiert

Das ursprüngliche archivierte Python-Skript `rb_v5_ablation.py` wurde erneut gelesen. Mit `data-source/providers/nflverse/player-stats/raw-2024.csv`, `data-source/nfl/rosters/2024.json`, `data-derived/nfl-games/2024.json` und allen `data-derived/player-week-fantasy/nfl-reise/2024/04..17.json` wurde die originale Vegas-Featurelogik in JS umgesetzt. Korrekte CSV-Quote-Behandlung nötig (headshot-URLs enthalten Kommas). **Exakt reproduziert:** 964 eligible 2024 RB-Spiele; 470 W4–10 / 494 W11–17; V4-C-Baseline-MAE 4,9760794606. Originale B-Wahl: Ridge 32, Cap ±1 PPR. Refit auf 2024 W4–17 mit identischer Feature-Reihenfolge `[delta, spread, total-43]` und ohne Intercept:
- Feature-Scales = `[5.383053446953886, 5.822561066872184, 3.7963963158615357]`.
- Ridge-Betas = `[0.6276102919511259, 0.38397058670518025, 0.2160081772927129]`.
- `delta` = Team-Markt-ImpliedPoints minus letzte 3 tatsächliche Team-Scoring-Werte vor der Woche; `spread` = eigener ImpliedPoints-Vorsprung; `total-43`; jeweils skaliert, auf ±5 gekappt, Gesamtkorrektur ±1 PPR. Keine Zeile im 2024-Fit war tatsächlich vom ±5-Featurecap betroffen. 2024-Re-Fit B MAE 4,9556762137 (Train-Sample, **kein unabhängiger Evaluationswert**).
- Beim 2026-Entscheidungsproxy wurde B auf Spieler mit vorhandener V4-C-Projektion ausgedehnt, ohne anhand späterer Zielwochen-Carries/Targets zu selektieren. **Achtung:** Das originale 2024-B-Training war auf tatsächlich aktive RB-Spieler beschränkt; die Anwendung auf den vollen Entscheidungspool ist Extrapolation, keine bereits separat validierte Availability- oder Rookie-Regel.

### Historisch belegte Pregame-App-Snapshots (vor dem ersten Sunday-Kickoff der jeweiligen Woche)

| 2026-Woche | Commit mit zu dem Zeitpunkt archiviertem `public/data/League.json`, `Players.json`, `PlayerWeekFantasy.json` | Git Commitzeit UTC |
|---|---|---|
| W04 | `674ed95ed1825b678b704171240dea31432341c8` | 2026-10-04 10:06 |
| W05 | `07be8e1a7c6200557b2ee768ec31973108641a84` | 2026-10-11 10:03 |
| W06 | `60811de44329c020a2f449f51ee58d1b0882817e` | 2026-10-18 10:17 |
| W07 | `3aae21a7c53505270ed26d8603a93a5c65bac883` | 2026-10-25 10:03 |

W07 ist 11:03 CET; das Mighty-Giants-Starterset entspricht dem separat archivierten Ex-ante-Entscheidungsdokument vom 25.10. ca. 14:12 CET. Modelle und Fantasy-Roster werden **jeweils am gleichen belegten Pregame-Commit** gelesen. Final-Punkte entstammen nachträglich kanonischen Matchup-`PlayerPoints`, nicht aus dem Pregame-Snapshot. Die 2026-Markt-Features stammen aus dem aktuell materialisierten `data-derived/nfl-games/2026.json` (**retrospektiv**); `nflverse.schedule-odds` enthält keinen zertifizierten ursprünglichen Pregame-Observation-Timestamp. Die am 30.10. erneut gelesene Odds-Source-Metadata belegt nur einen aktuellen Abruf, **nicht** den Zustand vor den vier Kickoffs.

### Kandidaten- und Lock-Policy der read-only Simulation

- Historischer Fantasy-Team-`Roster` minus `Reserve`/IR und `Taxi`; Position/Team/Out-Designation aus dem jeweiligen **Pregame-`Players.json`**. 2026er `Players.ByeWeek` ist als pauschaler Week-4-Filter ungeeignet und wurde nach einem offensichtlichen Fehllauf verworfen; stattdessen tatsächlich Woche zugeordneten NFL-Spielplan verwenden. Auflösung von NFL-Team-Abbr/Matchup und tatsächlichen Punktwerten strikt; unbekannte Kandidaten bleiben als Coverage-Lücke kenntlich.
- Bereits vor dem Snapshot gespielte Donnerstagsspieler: damalige Starter **zwingend fixieren**, damalige Bankspieler **unwählbar**. Sonntag-/Montagsspiele bleiben offen (der jeweilige Snapshot lag vor dem ersten Sunday-Kickoff). Der gleiche Positions-Slotpool pro Team und Saison (2026: 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX, 1 K) und derselbe globale Assignment-Algorithmus wie `tools/weekly_lineup_optimizer.py` (Hungarian matching), FLEX nur RB/WR/TE. **Leere Starter-Slots sind zulässig** (bereits im bestehenden Optimizer-Contract vorgesehen), etwa Mammoth W07 ohne startbaren Kicker: beide Modelle hatten dort 12 statt 13 belegte Slots.
- Nur bekannte pregame Out-/IR-Designation oder NFL-Roster-/Spielplan-Fakten filtern; **keine nach dem Spiel bekannt gewordenen Inactive-Flags** aus finalen NFL-Rosters als vermeintliche Pregame-Information verwenden. Sonstige Injury-/AutoSub-/Last-Minute-News bleiben wegen unvollständiger Archivlage eine Einschränkung.
- Originale 2024-B-Vegas-Korrektur ausschließlich für RBs; gleiche verbleibende Kandidaten und Locked-Starter für A und B, finale offizielle `PlayerPoints` als Outcome. Nur gleiche Team/Woche und vollständig rekonstruierbare Outcomes als Hauptstichprobe; kein altes All-Roster-Best-Ball einschließlich IR/Taxi.

### Tatsächlich berechnete Resultate (Research-Proxy, kein Produktionsentscheid)

| 2026 | Nachgebildete Team-Wochen | A→B-Aufstellungswechsel | Finaler Ergebnis-Delta B−A |
|---|---:|---:|---:|
| W04 | 6 | 1 (Mammoth: Luther Burden III → RJ Harvey) | **+7,90 PPR** (11,4 → 19,3) |
| W05 | 6 | 0 | 0,00 |
| W06 | 6 | 0 (ein Team mit unvollständig beobachtetem Kandidatenscoring) | 0,00 im auswertbaren Teil |
| W07 | 6 | 1 (Mammoth: Dallas Goedert → RJ Harvey) | **+4,20 PPR** (9,8 → 14,0) |
| **Summe, explorativ** | **24** | **2** | **+12,10 PPR** |

**Strenger Coverage-Filter:** Nur **16/24 Team-Wochen** hatten im modellierten Kandidatenraum keine fehlende veröffentlichte Projektion und keine ungeklärten offiziellen Spieler-Outcomes; darin **2 Wechsel / 2 positive Outcomes / 0 negative Outcomes / 14 unveränderte Lineups**, **+12,10 PPR**. Die restlichen acht Team-Wochen bleiben **partial/unresolved**, auch wenn im beschränkten, verfügbaren Kandidatenraum kein Modellwechsel sichtbar war. Keine fehlende Projektion/kein unbekannter Punktewert wurde still zu Null gesetzt. Das ist **kein signifikanter Vorteil**, keine reine Prospektivstichprobe und keine echte 2024-/2025-Historie; Stichprobe klein, ein RB (RJ Harvey) trägt beide positiven Wechselfälle, nicht unabhängig.

**Korrekturtransparenz (mehrstufige Exploration):** Erste W07-Rechnung mit *postgame*-PWF und *postgame*-NFL-Active-Status war unzulässig und wurde verworfen. Die nachfolgende striktere Variante blockierte W07 Mammoth fälschlich aufgrund leerem Kicker-Slot; nach Prüfung bestätigte sich, dass der bestehende Lineup-Optimizer explizit ein leeres Starter-Slot zulässt. **Maßgeblich sind nur die oben ausgewiesenen vier Pregame-Commit-basierten Berechnungen** und der ausgewiesene Abdeckungsfilter.

### Bewertung, offene Gates / Handoff

- **Vorläufige Hypothese:** Vegas-B kann einzelne marginale RB↔FLEX-Entscheidungen verbessern. Der Zusatznutzen ist in W04–07 klein und auf zwei Fälle konzentriert; für Mighty Giants im betrachteten Proxy kein A→B-Aufstellungswechsel.
- **Kein Modellcutover:** Trotz belegter Pregame-Roster und Pregame-V4-C-Projektionen kann das B-Signal wegen fehlender **zeitlich belegter Pregame-Marktquote** nachträglich veränderte Odds enthalten. Deshalb darf `+12,10` **nicht** als live-prognostische Kausalverbesserung oder validierte Win-/Lineup-Quality verkauft werden. 2024/25 besitzen keine vergleichbaren vollständigen Pregame-Fantasy-Roster-Snapshots aus der Git-Historie.
- [x] Original-B-Koeffizienten aus 2024 mit realen Source-Git-Blobs rekonstruiert.
- [x] Vier historische 2026-Pregame-Commit-Snapshots mit Roster+V4-C-Projektionen identifiziert und gegen finale offizielle Week-PlayerPoints read-only verglichen.
- [x] IR/Taxi-, Bye, inaktive Pregame-Designation, Locked-Bench, Forced-Locked-Starts, FLEX, optionale leere Slots und fehlende Score/Projection-Gates explizit behandelt.
- [x] Gepaarte RB-Vegas-Ablation als **diagnostischen Proxy** für 16 vollständige Team-Wochen gerechnet; 8 Partial Cases markiert.
- [ ] Unveränderliche **vor Kickoff beobachtete** Odds-/Availability-/Modelleingabe-Snapshots sowie belastbare später eintretende Lineup-Wechsel/AutoSub/late waivers für prospektive Auswertung verfügbar machen; hierfür bestehende Odds-Source-/Buffer-Architektur von #471 prüfen, keine zweite Writer-Pipeline oder manuelle Mutation ohne gesonderte konkrete Freigabe.
- [ ] Zusätzlich über mehrere Wochen/Seasons echte disjunkte Start/Sit-Entscheidungen, lineupspezifischen Net-Points-Regret und gekoppelte Team-Week-Unsicherheit bewerten; erst danach einen V5-Produktionsentscheid diskutieren.

**Status bleibt `status:analysis`, V4-C-Produktion unverändert.** Dieser Schritt änderte nur den Research-Issue-Body; keine Modellgewichte, PWF-/League-/Odds-Source-Files, Scheduler, Tests, PR oder Deploy.

## Research-Checkpoint 8 – positionsübergreifender Vegas-B-Test (30.10.2026)

**Auftrag:** Nutzer hat nach Abschluss des reinen RB-Vergleichs ausdrücklich die Erweiterung auf QB, WR und TE freigegeben („ja, mach das“). Durchführung ausschließlich als read-only Forschungsrechnung im verbundenen GitHub-Connector; diese Issue-Fortschreibung ist die einzige Repository-Mutation. **Kein produktiver Modell-, Workflow-, Scheduler-, Daten- oder App-Write.**

### 2024-Fit → 2025-Positionsevaluation

- **Kanonische Baseline:** bestehende V4-C `data-derived/player-week-fantasy/nfl-reise/{2024,2025}/04..17.json` inklusive liga-spezifischer `Actual.Points`, `Projection.Points` und `Status`.
- **NFL-/Vegas-Inputs:** `data-source/providers/nflverse/player-stats/raw-{2024,2025}.csv`, `data-source/nfl/rosters/{2024,2025}.json` (GSIS↔Canonical), `data-derived/nfl-games/{2024,2025}.json`. Historische Marktquoten **nicht** als damals beobachtete Pre-Kickoff-Preise zertifiziert.
- **Fairer Vergleich:** gleiche positionseigene Spieler-Spiel-Population für A und B; REG W04–17, aktuelle offensive Beteiligung >0 (QB: pass attempts + carries; RB/WR/TE: carries + targets), ≥2 vorherige aktive Saisongames, ≥3 frühere abgeschlossene NFL-Teamspiele, verfügbare V4-C-Projektion und finale offizielle Liga-Actuals. Dieses `conditional-on-participation`-Evaluationssample beweist **keine** Pre-Lock-Verfügbarkeit.
- **Modell B positionsweise trainiert:** exakt ursprüngliche drei Features `[ImpliedTeamPoints - prior3TeamScoreMean, ownImplied - opponentImplied, GameTotal - 43]`. Positionseigene z-Skalen aus 2024; Featurecap ±5, Ridge ohne Intercept λ=32, additive Prognosekorrekturcap ±1 PPR. Dieselben auf RB-2024-Validation gewählten Hyperparameter für **alle Positionen fixiert**, keine 2025-Hyperparameterauswahl. Positionseigene Gewichte aus **allen** 2024-Fällen, 2025 Test.
- **Kontrollreproduktion:** RB 2024 **N=964** mit exakten originalen Skalen `[5.383053446953886,5.822561066872184,3.7963963158615357]`, Betas `[0.6276102919511259,0.38397058670518025,0.2160081772927129]`; RB 2025 **N=951** und MAE 5.0648829653→5.0300933373, exakt wie Checkpoint 7.

| Position | 2024-Fit N | 2025-Test N | MAE V4-C | MAE + B | Delta (B−A) | Delta relativ | Wochencluster-Bootstrap 95%-Perzentilintervall Delta |
|---|---:|---:|---:|---:|---:|---:|---|
| RB | 964 | 951 | 5.064883 | 5.030093 | -0.034790 | -0.69 % | [-0.07045; +0.00316] |
| QB | 451 | 441 | 6.687356 | 6.676145 | -0.011211 | -0.17 % | [-0.08729; +0.05889] |
| WR | 1491 | 1484 | 4.873208 | 4.877971 | +0.004763 | +0.10 % | [-0.00523; +0.01493] |
| TE | 761 | 785 | 3.952198 | 3.988486 | +0.036289 | +0.92 % | [+0.01349; +0.05724] |

Positionseigene 2024-Fit-Parameter (Feature-Reihenfolge wie oben; λ=32):
- QB: Skalen `[5.345872234795185,5.8559956783648355,3.773084153667748]`; Betas `[0.8984729928959626,-0.05585465294531694,0.3563368837633101]`.
- WR: Skalen `[5.322206730360297,5.837243515135259,3.863933469731433]`; Betas `[0.08582512795767175,-0.18435660209636415,0.10387546890559309]`.
- TE: Skalen `[5.364980080109947,5.822680131182152,3.7080894062316285]`; Betas `[0.14322631690984677,-0.04109200679997162,0.47792140880350037]`.

2024 interne Prüfung W04–10 Fit → W11–17 Validation mit λ=32, Cap ±1: QB MAE **6.506807→6.458288**; WR **4.886686→4.902467**; TE **3.861639→3.917831**. WR/TE also bereits im Vorjahres-Validierungsschnitt nicht überzeugend. Bootstraps 2025 sind deterministisch über 14 Wochencluster (10.000 Resamples), **nicht** unabhängig prospektiv und bei bereits inspiziertem 2025 nicht als unangetasteter Holdout darstellbar. Einzelpositionen auf Basis des MAE: QB schwach/unsicher positiv, WR indifferent, TE bei dieser Korrektur negativ.

### Fantasy-Lineup-Proxy 2026 W04–07 – alle Positionen

- Die bereits in Checkpoint 7 belegten **vier Sunday-Pregame-Commit-Snapshots** von `public/data/League.json`, `Players.json` und `PlayerWeekFantasy.json` erneut eingelesen; W04 `674ed95...`, W05 `07be8e1...`, W06 `60811de...`, W07 `3aae21a...`. Offizielle nachträglich finale League-Punkte aus `data-source/leagues/nfl-reise/seasons/2026/matchups/week-{4..7}.json::PlayerPoints`.
- Gleicher Team-Roster minus IR/Reserve/Taxi, Pregame Out-Designation, tatsächlicher NFL-Wochenspielplan, vor Commit gespielte Starter-Slots fixiert/Bench blockiert, 2 QB + 2 RB + 2 WR + 2 TE + 4 FLEX + 1 K, FLEX RB/WR/TE, leere Slots erlaubt; globale gewichtete Zuordnung (Hungarian).
- Bei allen Varianten identischer Kandidatenpool, identische legale Locks und Baseline V4-C. Modelle einzeln (nur RB, QB, WR oder TE) und gemeinsam (alle vier) korrigiert; cap ±1 pro Spieler. Die 2026-Markt- und Team-Scoring-Features sind **retrospektiv materialisiert**, nicht zeitlich als Pre-Kickoff attestiert.
- **Strenge Coverage:** **16/24** Team-Wochen ohne fehlende Kandidatenprojektion/ungeklärte offizielle Punkte; **8 partial** mit fehlenden/ungeklärten Modell-Kandidaten ausgeschlossen. Keine stillschweigende Prognose=0-Setzung. RB-Only-Ergebnis aus Checkpoint 7 **exakt reproduziert**.

| Variante | Geänderte Aufstellungen in 16 vollständigen Team-Wochen | Summe offizielle PPR-Differenz zur V4-C-Lineup-Baseline |
|---|---:|---:|
| Nur RB-B | 2 | +12.1 |
| Nur QB-B | 1 | +12.2 |
| Nur WR-B | 2 | -1.5 |
| Nur TE-B | 1 | +0.8 |
| **RB+QB+WR+TE gemeinsam** | **3** | **+25.1** |

**Konkrete vollständig erfasste Entscheidungen:**
- 2026 W04 Mammoth Marauders: nur QB-B **Joe Burrow statt Jalen Hurts**, +12.2; nur RB-B **RJ Harvey statt Luther Burden III**, +7.9; gemeinsames B **beide Wechsel**, +20.1.
- 2026 W04 Team TimpaBay: nur TE-B und gemeinsames B **Jake Ferguson statt Emeka Egbuka**, +0.8.
- 2026 W07 Mammoth: nur RB-B und gemeinsames B **RJ Harvey statt Dallas Goedert**, +4.2.
- WR-isoliert: 2026 W04 Mammoth **Wan'Dale Robinson statt Luther Burden III**, -0.4; 2026 W06 TimpaBay **Woody Marks statt Romeo Doubs**, -1.1. Der W06-WR-Wechsel tritt **im gemeinsamen Modell nicht auf**; Einzelpositionsdeltas daher **nicht additiv**.
- Mighty Giants: W04, W05, W06 vollständig und unverändert. W07 Kandidaten-Outcome-Coverage partial; kein beobachteter Wechsel im eingeschränkten Pool.

**Gates / Interpretation:** Entscheidungsproxy zeigt zusätzlich zu RB ein konkretes QB- und ein kleines TE-Positivbeispiel, aber **keinen nachgewiesenen generalisierbaren Nutzen**. Bei TE widerspricht die 2025-Gesamt-MAE dem kleinen 2026-Lineup-Plus; bei WR verschlechterte der isolierte Eingriff zwei reale Startentscheidungen. Die **+25.1** sind keine garantierte/ex-ante erzielbare Verbesserung, keine schlüssige Kausalwirkung von Vegas und keine statistisch belastbare Modellfreigabe. 2024/25-Teamspiele sind nicht Pre-Kickoff-odds-zertifiziert; 2026 hat nur vier Wochen und drei vollständige gemeinsame Lineup-Wechsel; auch 2026 sind Odds-As-of und Availability-/AutoSub-Spätereignisse offen.

**Empfehlung:** V4-C und V4-C-PI1 **unverändert lassen**. Prospektive, zeitgestempelte Odds-/Roster-/Projection-/Availability-Observations und weitere vollständige Wochen sammeln, auf **gepaartem ganzen Lineup** gegen RB-only sowie alle-Positionen B evaluieren. QB als sekundäre Testhypothese offenhalten; **keine pauschale WR-/TE-Korrektur produktiv ausrollen**. #978 bleibt `status:analysis`.


## Research-Checkpoint 9 – Vegas bei extremen Matchups / PI1-Range (31.10.2026)

**Scope:** Vom Nutzer freigegebene, read-only Auswertung: 2025-Extreme nach erwarteten Vegas-Team-Punkten, Spread und Game Total; Primärziel sind **Spieler-Punktprognosen**, nicht Start/Sit. Zusätzlich bestehendes V4-C-PI1-Prediction-Range-Modell überprüfen. Einzige Änderung ist die administrative Dokumentation im Issue; keine Produktions-/Daten-/Code-/Workflowänderung.

### Reproduzierbarkeit und Einschränkungen

- Quellen unverändert aus vollständigen GitHub-Blobs gelesen: 2025 nflverse raw player-stats, canonical roster GSIS-IDs, nfl-games Marktquoten, finale liga-spezifische player-week-fantasy JSON Weeks 04–17 mit V4-C Projection.Points, Actual.Points und PredictionRanges. Same Eligibility wie Checkpoint 8, historische Team-Score-Features bis vor der jeweiligen Woche.
- Vegas-Modell B exakt aus Checkpoint 8: drei Features (Team-Implied minus Mittel der drei letzten Team-Actual-Scores, eigener Implied-Margin, GameTotal minus 43), positionsspezifische 2024-Koeffizienten/-Skalen, Ridge λ=32, Cap ±1 PPR. **Kein** 2025-Retraining.
- Kontrollwerte reproduziert: RB N951 MAE 5.0649→5.0301; QB N441 6.6874→6.6761; WR N1484 4.8732→4.8780; TE N785 3.9522→3.9885.
- **Explorative, überlappende Subgruppen, keine unabhängige Validierung:** Team implied ≤18 / ≥28; Spread ≤−7 / ≥+7; Total <40 / ≥50. Schwellen wurden im laufenden Forschungsdesign gewählt, 2025 ist mehrfach inspiziert. Historische Odds-As-of-Beobachtungszeit vor Kickoff **nicht nachgewiesen**. Conditional-on-actual-participation ist kein vollständiger Pregame-Availability-Test.
- 95%-Intervalle mit 10.000 deterministischen Week-Cluster-Bootstrap-Resamples der 14 Wochen (gepaarte B−V4-C-MAE-Deltas); Untergruppenbefunde wegen mehrfacher Tests **nicht prospektiv signifikant**.

### RB-Extrem-Segmente 2025 – Punkt-MAE

| RB-Gruppe | N | MAE V4-C | MAE B | Delta MAE | Relativ | Bootstrap 95% Delta |
|---|---:|---:|---:|---:|---:|---|
| Gesamt | 951 | 5.0649 | 5.0301 | -0.0348 | -0.69% | [-0.0693; +0.0035] |
| Team-Implied ≤18 | 129 | 5.0685 | 4.8740 | **-0.1945** | **-3.84%** | [-0.2694; -0.1068] |
| Team-Implied ≥28 | 81 | 5.5726 | 5.6337 | +0.0610 | +1.10% | [-0.1415; +0.2306] |
| Underdog, Spread ≤−7 | 153 | 5.0503 | 4.9473 | -0.1030 | -2.04% | [-0.1788; -0.0355] |
| Favorit, Spread ≥+7 | 161 | 5.3945 | 5.4564 | +0.0619 | +1.15% | [-0.0529; +0.1718] |
| Total ≥50 | 111 | 5.2396 | 5.1683 | -0.0713 | -1.36% | [-0.1956; +0.0237] |
| Total <40 | 116 | 4.6777 | 4.5613 | -0.1164 | -2.49% | [-0.2531; +0.0272] |
| abs(Spread) ≥7 | 314 | 5.2268 | 5.2083 | -0.0185 | -0.35% | [-0.0815; +0.0439] |

Low-Implied-RB: 129 Spieler-Spiele über 56 NFL-Team-Wochen, in 13/14 Wochen bessere gepaarte absolute Fehlerbilanz. **Gegenprobe:** RMSE 6.8777→6.8912 verschlechtert sich trotz MAE-Gewinn. Die starke Segmentverbesserung kann durch nachträgliche Teilgruppenauswahl und die unsichere Marktquoten-Provenance überzeichnet sein. Kein automatischer Cutoff bei ≤18 ableitbar.

Ein weiterer überlappender Feature-Schnitt (Implied Team Score minus letzte drei Team-Scores ≤−5): RB N204 MAE 5.3397→5.1739, Delta −0.1658, 95%-Bootstrap [-0.2475; -0.0713]. Da genau dieses Delta im B-Modell enthalten ist, keine unabhängige Bestätigung eines besonderen Mechanismus.

### Bereits bestehende V4-C-PI1-Intervalle

**Korrektur zur Diskussion:** Für V4-C sind bereits PredictionRanges von 50%, 80%, 90% vorhanden (Modell V4-C-PI1); kein neues Range-Modell erforderlich. Test: unveränderte PI1-Intervalle versus hypothetische Verschiebung des Intervallmittelpunkts um Vegas-B bei gleicher Breite, **keine** eigenständige Varianz-/Quantil-Kalibrierung.

| Beobachtung | PI1 V4-C | PI1 + B-Shift |
|---|---:|---:|
| RB alle, 50%-Abdeckung | 50.5% | 52.1% |
| RB alle, 80%-Abdeckung | 78.5% | 78.3% |
| RB alle, 90%-Abdeckung | 89.3% | 89.4% |
| RB alle, 80%-Intervallscore | 23.785 | 23.666 |
| RB alle, 90%-Intervallscore | 28.477 | 28.326 |
| RB Team-Implied ≤18, 80%-Abdeckung | 78.3% | 81.4% |
| RB Team-Implied ≤18, 80%-Intervallscore | **23.225** | **23.968** |
| RB Team-Implied ≤18, 90%-Abdeckung | 92.2% | 91.5% |
| RB Team-Implied ≤18, 90%-Intervallscore | **27.361** | **28.030** |
| RB Total ≥50, 80%-Abdeckung | 73.9% | 75.7% |

Intervallscore = (obere−untere Grenze) + 2/(1−Nominalniveau) × Distanz außerhalb des Intervalls; niedriger besser. Die ursprünglichen RB-Intervalle sind gesamt ungefähr nominal kalibriert. **Low-Implied-RBs** zeigen trotz gesunkenem Point-MAE sogar **schlechtere** Intervallscores nach dem reinen B-Shift. Keine belastbare Evidenz für engere oder bessere Prediction-Ranges durch Vegas. 90%-PI1-Gesamtabdeckung andere Positionen: QB 89.3%, WR 91.5%, TE 91.6%.

### Ergebnis und Handoff

- **Vegas für V5 vorerst zurückstellen**; kein pauschaler oder durch Exploration nachträglich auf Low-Implied-RBs eingeschränkter Vegas-Rollout. V4-C und V4-C-PI1 bleiben unverändert produktiv.
- Primärziel **Punktvorhersage-Qualität** (MAE, RMSE, Bias), Range separat (empirische Coverage, Intervallscore/Schärfe). Start/Sit-Effekt nicht als Proxy für Modellgüte einsetzen.
- Nur falls später ohnehin echte vor-Kickoff-Zeitstempel für Odds/Roster/Projection vorliegen: vorher fixierte Low-Implied-RB-Hypothese auf neuen Wochen/Seasons testen, ohne weitere 2025-Threshold-Suche. Keine eigenständige neue Pipeline allein dafür.
- Research bleibt **inconclusive**, Issue weiter status:analysis.
