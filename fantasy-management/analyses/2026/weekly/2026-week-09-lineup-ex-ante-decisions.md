# Mighty Giants — Week 9 2026: Ex-ante-Lineup-Entscheidungen gegen Flo

**Entscheidungs-Cutoff:** Sonntag, 08.11.2026, ca. **17:57 MEZ** (Europe/Berlin; nach Browns frühem Kickoff, vor den 19-Uhr-Spielen).  
**Team / Gegner:** Robert (Mighty Giants, TeamID 1, 4–4) gegen Flo (Just Bill, TeamID 3, 7–1).  
**Format:** 6 Teams, Full PPR; 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K; drei AutoSub-Slots laut zum Cutoff abgerufenen League-Settings.  
**Typ:** Vom Nutzer ausdrücklich zur Aufbewahrung freigegebene, zeitgenössische **Ex-ante-Lineup-Entscheidungsanalyse**. **Kein** formell versiegelter Decision Record, **kein** Postmortem, **keine** neue Decision-Set-Architektur.  
**Outcome-Firewall:** Die Donnerstagspartie JAX @ BAL war zum Cutoff abgeschlossen; der frühe Sonntag-Kickoff CIN @ ATL hatte bereits begonnen. Ihre Resultate und spätere Punkte dürfen die hier dokumentierten Prä-Kickoff-Begründungen der noch offenen Spiele nicht rückwirkend ändern. Für die Thursday-Benchentscheidung werden die bereits bekannten Resultate getrennt von der ursprünglichen Begründung dokumentiert.

## 1. Evidenz, technischer Snapshot und Ausführungsgrenze

### 1.1 Tatsächlich bestätigte Nutzerentscheidungen

- Robert bestätigte am 08.11. zunächst, dass die zuvor gemeinsam empfohlene **13-Spieler-Aufstellung** in Sleeper gesetzt wurde.
- Nach Roberts Meldung **„pickens ist out“** wurde ein neuer FLEX-Ersatz erforderlich.
- Robert hinterfragte ausdrücklich die vorschnelle Warren-Empfehlung und das daraus folgende Vier-TE-Lineup. Es folgte ein neuer Vergleich **Warren vs. Hall vs. Barkley**. Die finale Empfehlung wechselte nach Korrektur der Warren-Opportunity-/Matchup-Einschätzung zu **Saquon Barkley**.
- Robert bestätigte anschließend ausdrücklich: **„ok, habe Barkley aufgestellt.“**
- Damit ist **Barkley statt Pickens** die letzte bestätigte **Nutzer-Ausführungsentscheidung**. Keine eigenständige Sleeper-Mutation durch den Assistenten.
- **AutoSubs:** Im Gespräch wurde Pickens → Warren als Absicherung empfohlen. **Eine tatsächlich eingerichtete AutoSub-Paarung wurde für Week 9 nicht vom Nutzer bestätigt**. Aus dem Starter-Readmodel ist AutoSub-Konfiguration nicht belastbar rekonstruierbar.

### 1.2 Repo-Belege, getrennt von der Nutzerbestätigung

Zum Erstellungszeitpunkt abrufbare GitHub-Readmodels:

- `public/data/League.json`, Blob **`a5225cf19b03882b73919cf7cbfa42f1a231506f`**: Week 9, 13 Starter, **George Pickens / 8137** noch als FLEX, **Saquon Barkley / 4866** noch nicht als Starter; vollständiger 37er-Pool mit Reserve und Taxi.
- `data-source/providers/sleeper/leagues/1354177383984267264/matchups/week-9.json`, Blob **`cd2b4e8325c86785f0e42ac9cfe7230a5d140e8e`**: ebenfalls Pickens als Starter und Barkley als Bench zu diesem Abruf; beide Teams mit 13 Starter-Slots.
- `fantasy-management/generated/operations/managed-roster-overview.json`, zum 08.11.2026 materialisiert: Spielerpool und technische Injury-Flags; diese Flags können gegenüber neueren offiziellen Injury Reports hinterherhinken.
- `public/data/MatchupProjections.json`: **nur sekundärer, modellabhängiger Plausibilitäts-/Szenariohinweis**; nicht Hauptbeleg für Favoritenlage oder Start/Sit.

**Wichtige Provenance-Grenze:** Der sichtbare Repo-/Sleeper-Lesestand enthält **noch Pickens**, die spätere, konkrete **Nutzerbestätigung enthält Barkley**. Die nachfolgende 13er-Liste ist daher die **vom Nutzer bestätigte beabsichtigte Aufstellung**, **nicht** eine behauptete zweite technische Synchronisationsbestätigung. Ein späterer Review muss den tatsächlich wirksam gelockten Starter separat aus historischen Matchup-/Sleeper-Fakten ermitteln.

**Externe Evidenz:** Die am 05.–08.11. im Chat diskutierten und dort mit Web-Belegen versehenen Week-Rankings, Start/Sit-Analysen und Injury-/Usage-Berichte von FantasyPros, NBC/Rotoworld, Footballguys, 4for4, CBS, NFL-/Teamberichten, DraftSharks sowie Stoned Lack sind **datierte Gesprächsevidenz**. Die konkrete Originalversion jeder dynamischen Ranking-Seite ist in diesem Artefakt **nicht als Snapshot archiviert**. Rankings werden deshalb nicht als unveränderliche dauerhafte Quellenwahrheit ausgegeben. Die Stoned-Lack-Einschätzung zu Hall basiert hier auf Roberts mündlicher Wiedergabe, nicht auf einem separat auditierten Podcast-Take.

## 2. Letzter bestätigter Start-Plan (13 Spieler)

| Slot | Spieler | Sleeper-ID | Ex-ante-Entscheidung |
| --- | --- | --- | --- |
| QB1 | Patrick Mahomes | 4046 | Start; etablierte QB-Rolle und günstiger Jets-Gegner |
| QB2 | Jayden Daniels | 11566 | Start; gegenüber Penix/Shough bevorzugt |
| RB1 | Kenneth Walker III | 8151 | Klarer Start; Qualität und Opportunity, Kansas City gegen Jets |
| RB2 | Chase Brown | 9224 | Start; Receiving-Fit und externe Week-Rankings; früher Kickoff bereits erfolgt |
| WR1 | Puka Nacua | 9493 | Klarer Start |
| WR2 | Malik Nabers | 11632 | Start; gegen Ende der Woche Volltraining / keine finale Game-Designation laut damaliger Berichtslage |
| TE1 | Trey McBride | 8130 | Klarer Start |
| TE2 | Colston Loveland | 12517 | Start; mehrere aktuelle Week-Rankings im oberen TE-Bereich |
| FLEX1 | D'Andre Swift | 6790 | Start; belegte Carries/Workload, auch bei möglichem Monangai-Return |
| FLEX2 | Tetairoa McMillan | 12526 | Start; trotz schwierigem Denver-Matchup hohe Target-/Routenbeteiligung |
| FLEX3 | Harold Fannin Jr. | 12506 | Start; aktuelle Receiving-Opportunity, gutes Matchup gegen New Orleans |
| FLEX4 | **Saquon Barkley** | **4866** | **Nach Pickens-Out bewusst vom Nutzer eingesetzt**, vor Warren/Hall |
| K | Ka'imi Fairbairn | 3451 | Halten; kein ausreichender Kicker-Streaming-Vorteil identifiziert |

**Gesamtstruktur:** 2 QB + 2 RB + 2 WR + 2 TE + 4 FLEX (Swift, McMillan, Fannin, Barkley) + 1 K = **13**, darunter **drei** Tight Ends (McBride, Loveland, Fannin), **nicht vier**. Die physische FLEX-Reihenfolge in Sleeper kann hiervon abweichen; relevant ist der bestätigte Spielerpool.

**Bewusst nicht gestartet:** George Pickens (Out), Tyler Warren, Breece Hall, weitere Alternative Jaylen Waddle; dazu der bereits am Donnerstag nicht eingesetzte Jaguars-WR-Pool (Brian Thomas Jr., Travis Hunter, Jakobi Meyers). Ein späterer Postmortem-Vergleich muss die tatsächlichen Lock-/Verfügbarkeitszeitpunkte respektieren.

## 3. Entscheidungsverlauf und Reversal-Begründungen

### 3.1 Thursday: keine Jaguars-Receiver starten

- Ursprüngliche Entscheidung vor JAX @ BAL: **Brian Thomas Jr., Travis Hunter und Jakobi Meyers benchen**. Maßgeblich waren die damals schwache/unklare offensive Rolle und die besseren Alternativen im tiefen Mighty-Giants-Roster.
- Nach dem Spiel war Meyers' 10,5-PPR-Ergebnis bekannt. Dies ist **Outcome**, keine nachträgliche Begründung der ursprünglichen Start/Sit-Auswahl. Thomas und Hunter waren ebenfalls nicht gestartet.

### 3.2 Samstag: Swift aufgerückt, Fannin ernsthaft auf Startniveau

- Im inzwischen aktualisierten Mighty-Giants-Roster wurde **D'Andre Swift** als sofort relevante RB-/FLEX-Option berücksichtigt. Die Diskussion stellte auf hohe jüngste Carries/Opportunity und Monangais Verfügbarkeit ab.
- **Harold Fannin Jr.** wurde nach eigener gezielter Prüfung nicht mehr als per se vierter TE abqualifiziert: Im Gespräch standen **21 Targets, 16 Receptions und 245 Yards über die zwei vorherigen Spiele**, das günstige Saints-Matchup und eine letztlich fehlende finale Game-Designation trotz Leistenbeschwerden.
- **Trey McBride und Colston Loveland** blieben die gesetzten TE-Starter. **Fannin** erhielt einen FLEX-Platz. **Tyler Warren** und **Barkley** verblieben zu diesem Zeitpunkt auf der Bank.
- **Korrigierter Analysefehler:** Die erste Bewertung hatte das interne V4-C-/Matchup-Modell zu stark gewichtet. Robert verlangte ausdrücklich die Anwendung der Repository-Regeln: unabhängige aktuelle Redraft-Quellen, Usage, Injury, Floor/Median/Ceiling, gemeinsamer FLEX-Pool, nachvollziehbares Reversal Gate. Diese Hierarchie ist **bindend**; ein kleiner Modellprojektionsvorsprung begründet keinen automatischen Start.

### 3.3 Hall-Debatte: gesund, aber Rolle gegenüber Braelon Allen ungeklärt

- Roberts Wiedergabe des Stoned-Lack-Podcasts: **Breece Hall ungefähr RB21**, weiterhin als RB1 bezeichnet, mit möglicher Receiving-/Passing-Game-Rolle, während Braelon Allen mehr physische Carries übernehmen könnte.
- Besprochen wurde, dass Hall wieder voll trainiert und ohne finale Game-Designation spielbereit war; daraus folgt **nicht automatisch** normaler Snap-/Touch-Anteil.
- Plausibler Full-PPR-Case: Hall kann bei negativem Game Script gegen Kansas City und mehr Checkdowns punkten; zusätzlich wurde der mögliche Ausfall anderer Jets-Passempfänger als Kontext diskutiert.
- Plausible Gegenhypothese: Allen hat in Halls Abwesenheit echte, teils auch im Passspiel relevante Opportunity aufgebaut. Die Rollenaufteilung nach Halls Comeback ist nicht sicher vorherzusagen; schwieriges KC-Run-Matchup.
- **Entscheidung:** Hall bleibt **Bench**, zunächst knapp hinter Fannin; auch nach Pickens' Ausfall wurde er nicht der bevorzugte Ersatz. Das ist eine Week-9-Rollenunsicherheit, **kein langfristiges Dynasty-Urteil**.

### 3.4 Pickens fällt aus: zunächst Warren vorgeschlagen, danach bewusst revidiert

- Pickens war zunächst trotz Hamstring-/Schulterproblemen mit Rückhalt der Week-WR-Rankings als FLEX geplant. Roberts spätere **Out-Meldung** ist das materielle neue Ereignis, das den Starterwechsel auslöst.
- **Zwischenempfehlung:** `Pickens → Tyler Warren`. Der erste Impuls stützte sich auf Warrens Target-Volumen, externe TE-Rankings und die Möglichkeit eines inaktiven Pickens. Das hätte **vier TEs insgesamt** (McBride, Loveland, Fannin, Warren) bedeutet.
- Robert hinterfragte zu Recht die Reihung gegenüber Hall/Barkley sowie die konkrete Qualität von Warrens Matchup und Gesundheits-/Rückkehrstatus.
- **Korrigierte externe Gegenprüfung:** Warren spielt **IND vs. DAL**, eine nicht klar vorteilhafte TE-Defensivkonstellation; nach verpassten Wochen kehrte er in Week 8 mit reduzierter Snap-Beteiligung zurück (im Chat ungefähr **72 %** statt zuvor häufig >85 %), erhielt aber **10 Targets** und nur **4 Catches/18 Yards**. Volle Spielberechtigung ist **keine** Garantie für volle alte Rolle. Die damaligen Expertenrankings zu Warren schwankten merklich. Seine Situation war zuvor zu optimistisch dargestellt worden.
- **Barkley-Gegenhypothese:** Trotz reduzierter Week-8-Nutzung (im Chat ungefähr **32 % Snaps, 14 Touches**) und anhaltendem Active-but-limited-Risiko ist Barkley für Week 9 freigegeben und kann bei einer Erholung seiner Lead-RB-Rolle gegen die Giants deutlich mehr Touches/TD-Chancen erhalten. Auch dieser Upside-Case ist **nicht gesichert**.
- **Finale Reversal-Entscheidung:** **Barkley leicht vor Warren**, Hall dahinter. Der Wechsel von der Warren-Zwischenempfehlung beruht **nicht** allein auf Roberts Hinweis „vier TEs“, sondern auf der nachgeholten Prüfung von **Dallas-TE-Matchup, Warrens Rückkehr-/Snap-Sicherheit und Barkleys vergleichbarer Upside-These**. Die Entscheidungskonfidenz wurde im Gespräch als **niedrig bis mittel** beschrieben.
- **Nutzerbestätigung:** Robert teilte ausdrücklich mit, dass **Barkley aufgestellt** wurde. Damit ist `Pickens OUT → Barkley START` die letzte maßgebliche bestätigte Entscheidung.

## 4. Gemeinsame FLEX-Portfolio- und Gegnerbetrachtung

**Gewählte FLEX-Vierergruppe:** **Swift + McMillan + Fannin + Barkley**.

| Spieler | Tragender Ex-ante-Case | Materielles verbleibendes Risiko |
| --- | --- | --- |
| Swift | Stabiles jüngstes Carry-Volumen; Monangai noch nicht gesichert; externe Rankings deutlich positiv | Später Kickoff, Monangai-Rückkehr, mögliches Nutzungs-Splitting |
| McMillan | Weiterhin relevanter Target Share und Routes; individueller Nutzungs-Floor | Schwierige Denver-Defense, QB-/Team-Effizienz |
| Fannin | 21 Targets in zwei Spielen, im Vergleich günstiges Saints-TE-Matchup | Einzelsample/Variabilität, Leistenrestrisiko trotz fehlender Game-Designation |
| Barkley | Hohe bekannte Talent-/Touchdown-Upside bei wieder größerem Workload | Verletzungs-/Comeback-Folgen, Week-8-Snaplimit, möglicher aktiver aber reduzierter Einsatz |

**Portfolio-Entscheidung:** Der Pickens-Ausfall beseitigt eine Hamstring-/Inaktivitätsquelle, dafür wird mit Barkley **bewusst** ein Workload-/Reinjury-Risiko akzeptiert. Mit Swift/McMillan gibt es zwei besser durch jüngste Opportunity gestützte FLEX-Optionen; Fannin trägt eine receiving-basierte kurzfristige Upside-These. Die vier Risiken sind **nicht identisch** und dürfen nicht ohne Evidenz zu einer statistisch korrelierten Gesamtwahrscheinlichkeit verrechnet werden. Kein pauschales „RB schlägt TE“ oder „drei TEs sind zu viel“.

**Gegner Flo (Just Bill):** 7–1 vor Week 9 und Tabellenführer, starke aktuell gesetzte Starter; am Donnerstag keine gewerteten Starter in diesem direkten Matchup. Gegen diese real starke Mannschaft ist Ceiling wichtig, aber ein über die Repo-Matchup-Projektion behaupteter fixer Außenseiterstatus reicht **nicht**, um zwanghaft maximale Varianz zu wählen. Die im Chat erörterte mögliche Verletzungsunsicherheit bei Flos Amon-Ra St. Brown wurde **nicht als bestätigter Ausfall** eingeplant.

**Modellgrenze:** `public/data/MatchupProjections.json` darf ex ante lediglich eine nachrangige Szenariokontrolle sein. Der vom Modell angezeigte Punkteabstand ist keine unabhängig kalibrierte Matchup-Win-Probability und kein autonomer Grund, Hall/Warren/Barkley zu wählen.

## 5. Zeitpunkte, Locks und AutoSubs

| Zeitpunkt MEZ | Relevanz |
| --- | --- |
| Freitag 06.11., 02:15 | JAX @ BAL, alle drei Jaguars-WR bewusst gebenchtt |
| Sonntag 08.11., 15:30 | CIN @ ATL mit Chase Brown: beim hier dokumentierten Cutoff bereits gestartet; kein ex-post Wechsel möglich |
| Sonntag 08.11., ca. 17:30–18:00 | Finale Injury-/Inactive-Informationen für 19-Uhr-Spiele. Roberts Pickens-Out-Meldung, Diskussion der drei FLEX-Ersatzkandidaten und bestätigte Barkley-Umstellung erfolgten vor dem 19-Uhr-Lock |
| Sonntag 08.11., 19:00 | Pickens/Warren/Barkley/Fannin/Hall (und weitere relevante Starter) im 19-Uhr-Fenster; nach Lock keine nachträgliche Auswahl |
| Montag 09.11., 02:20 | CHI vs. TB mit Swift und Loveland; Monangai-Rolle als möglicher Volumenfaktor |
| Dienstag 10.11., 02:15 | BUF @ MIN als verbleibendes Monday-Night-Spiel der NFL-Week 9 |

**AutoSub:** Die Liga-Settings nennen `max_subs=3`, `sub_start_time_eligibility=0`, `sub_lock_if_starter_active=0`; konkrete Sleeper-Trigger-/Lock-Semantik darf nur mit aktueller offizieller Dokumentation behauptet werden. **Keine konkrete Week-9-Paarung ist durch Robert bestätigt.** Durch den direkten Wechsel zu Barkley soll kein bereits als Out bekannter Pickens als notwendiger aktiver Starter zurückbleiben. Ob die technische Starterbelegung rechtzeitig bei Sleeper synchronisiert wurde, ist aus dem später abrufbaren Historienrecord zu überprüfen.

## 6. Konfidenz, Gegenhypothesen und spätere Review-Fragen

- **Hohes Vertrauen:** Mahomes, Daniels, Walker, Puka, McBride, Swift; in den besprochenen Quellen auch Loveland und Chase Brown gut gestützt.
- **Mittleres Vertrauen:** Nabers (offizieller Freigabekontext), McMillan (schwieriger Gegner, gute Usage), Fannin (jüngste Targets + Matchup vs. kurze Sample-Historie).
- **Niedrig bis mittleres Vertrauen am Grenzslot:** **Barkley vor Warren/Hall**. Das ist eine bewusst akzeptierte Unsicherheit, kein nachträglich als zwangsläufig dargestellter Start.
- **Korrekturen aus dem Entscheidungsprozess:** (1) V4-C nie Hauptquelle; (2) vollständigen FLEX-Pool statt isolierter Spielernamen betrachten; (3) beim Pickens-Ausfall nicht automatisch den ersten früher genannten Backup aufstellen; (4) Warren-Rückkehr nicht mit vollem alten Snapvolumen gleichsetzen; (5) Nutzerbestätigung sauber von Repo-Synchronisierung unterscheiden.

**Im eigenständigen Week-9-Postmortem zu prüfen, ohne dieses Artefakt umzuschreiben:**

1. Welche **13 Starter** wurden tatsächlich gewertet? Wurde Barkley vor seinem Lock in Sleeper wirksam statt Pickens gesetzt, und gab es AutoSubs?
2. Waren die zum Decision-Cutoff bekannten Injury-/Workload-Fakten zu Pickens, Fannin, Hall, Warren, Barkley, Nabers und Monangai korrekt?
3. Welche Snap-/Route-/Carry-/Target-Zahlen und welche Opportunity-Provenance ergaben sich tatsächlich; besonders **Barkley vs. Warren vs. Hall** und **Fannin**?
4. Was wäre die beste **Same-Information-Entscheidung** gewesen und was ist lediglich **Outcome Regret** aufgrund späterer Scores?
5. Haben externe Expertenargumente, Rolle und Matchup die Entscheidung besser getragen als das nachrangige interne Modell?
6. Wie wirkte die Kombination der vier FLEX-Spieler tatsächlich, statt nur den punktstärksten Bench-Spieler nachträglich zum „offensichtlichen“ Starter zu erklären?

**Geltende Regelquellen:** `fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md`, `fantasy-management/_ai/FANTASY_MANAGEMENT_RULES.md`, `fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md`, `fantasy-management/_ai/ROSTER_ARCHITECTURE.md`. Zukunftige Week-Ergebnisse und Bewertungen gehören in `fantasy-management/analyses/2026/weekly/2026-week-09-roster-lineup-postmortem.md` (nur wenn später tatsächlich erstellt), **nicht** in eine Überschreibung dieses Ex-ante-Entscheidungsstands.
