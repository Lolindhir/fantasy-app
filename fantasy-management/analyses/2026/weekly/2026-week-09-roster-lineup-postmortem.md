# Mighty Giants — Week 9 2026: Roster + Lineup Postmortem (externe Pregame-Evidenz zuerst)

**Rekonstruktion:** 10.11.2026, nach NFL-/Sleeper-Matchup-Abschluss.  
**Team:** Mighty Giants / TeamID 1; historischer CanonicalLeagueRosterID clr-a8e576139994570d82e9ea2ed3f42b1b.  
**Gegner:** Flo / Just Bill (TeamID 3); vor dem Spiel Giants 4–4 und Flo 7–1.  
**Endstand:** **200,04 : 231,00**, Niederlage mit **30,96** Punkten; Giants danach rechnerisch 4–5.  
**Format:** sechs Teams, Full PPR, 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX (RB/WR/TE) / 1 K.  
**Dokumenttyp:** Persistierte, retrospektive Analyse auf ausdrückliche Nutzerfreigabe, **kein sealed Decision Record**, kein Rewrite der historischen Ex-ante-Akte. **Keine automatischen Roster-, Waiver-, Watchlist-, Regel- oder Modellsystem-Mutationen.**

## 0. Ergebnis, Verifikation und Outcome-Firewall

- **Bestätigte technische Ausführung:** Die finalen Sleeper- und Canonical-League-Week-9-Datensätze enthalten übereinstimmend **13 Starter** inklusive **Saquon Barkley (4866)**, ohne **George Pickens (8137)**. Der konkret von Robert bestätigte direkte Wechsel **Pickens OUT → Barkley START** wurde somit wirksam. Die Starterpunkte summieren sich exakt auf **200,04**; Gegner Flo auf **231,00**.
- **Periodenstabile Absicht:** Das getrennte Dokument [Week-9-Ex-ante-Entscheidungen](2026-week-09-lineup-ex-ante-decisions.md) hält Roberts letzte Bestätigung vom **08.11.2026, ca. 17:57 MEZ** und die damaligen Argumente fest. Es bleibt **unverändert**. Der damalige Repo-Snapshot enthielt noch Pickens; das spätere finale Sleeper-Matchup enthält Barkley.
- **Finalitätsgrenze:** Canonical NFL Game Finality für REG Week 9 meldet **15/15 Spiele final** und das App-Matchup Week 9 ist **final**. Gleichzeitig stand das App-League-Readmodel noch auf **FinalScoredWeek=8**, der Week-9-Snap-Datensatz meldet **Finalized=false** (nur **14** verschiedene Spielkennungen), und aktuelle App-PlayerWeekFantasy-Actuals sind noch **unavailable**. Deshalb sind **Sleeper/Canonical-League-Week-9-Punkte** die bestätigte Scoring-Wahrheit; der nachgelagerte Modell-/Snap-Finality-Status wird nicht als final umgedeutet.
- **Wichtige Periodengrenze:** Die 37er-Gruppe wird aus historischem Week-9-Player-Pool und zum **08.11.2026** materialisiertem Managed-Roster-Snapshot gegengeprüft; die spätere Reserve-/Taxi-Einstufung ist kein Nachweis der vollständigen minutengenauen Eligibility-Historie. AutoSub-Konfiguration/Prioritäten sind nicht rekonstruierbar und werden nicht erfunden.
- **Methodik:** Decision Quality ≠ Outcome Quality ≠ Modellkalibrierung. Die unabhängige **zeitgenössische Pregame-Evidenz** und die **damals zulässigen Alternativen** stehen vor Punkten aus der abgeschlossenen Woche; ein scorerichtiges Lineup ist nicht automatisch der richtige Pregame-Plan.

### Eingefrorene und abgerufene technische Input-SHA (Git-Blobs, Abruf 10.11.2026)

| Inputpfad | Blob-SHA |
|---|---|
| data-source/leagues/nfl-reise/seasons/2026/matchups/week-9.json | 55b24e99871233cf1e0c0245287be155498080a6 |
| data-source/providers/sleeper/leagues/1354177383984267264/matchups/week-9.json | 44340c1b342d3dd35f623fee81919cb83240127a |
| data-source/nfl/snap-counts/2026/09.json | dd3fba06ec5b5f4e372dc5b1b632fa19f119abac |
| fantasy-management/generated/operations/managed-roster-overview.json | 5dddccf4bce61713020d9f5f184b112b4a526a1e |
| public/data/PlayerWeekFantasy.json | 27e78a42e58f318bf5cea02c43dab3275600de3f |
| public/data/Matchups.json | 3306dc7537ea3081ada91f2d4d6d93c82f5cea26 |
| data-source/nfl/game-finality/2026.json | ed850154edc39e4be760f3da4e0e25704b644f4c |
| public/data/League.json | f689e6de698e2c0226b4b26164d4e6d83a6a3328 |

## 1. Verbindliche Regeln für dieses Review

Anwendung der kanonischen Dateien FANTASY_MANAGEMENT_SOURCES.md, FANTASY_MANAGEMENT_RULES.md, ROSTER_ARCHITECTURE.md, MONITORING_AND_WEEKLY_DECISIONS.md und WORKFLOWS.md; **keine neue Normsetzung** durch dieses Review.

1. Source-first: kanonische Liga-Fakten und aktuelle externe NFL-/Fantasy-Evidenz gegeneinander plausibilisieren.
2. Nutzerperspektive: Mighty Giants, TeamID 1, tatsächliche sechs Teams statt generischer 12-Team-Fantasy.
3. Historische Starter, Besitzstände, Slots und Scoring vom **richtigen Zeitpunkt** lesen.
4. Ex-ante-Entscheidungszustand nicht aufgrund späterer Ergebnisse umschreiben.
5. Bei wesentlichen Grenzfällen mehrere unabhängige **Pregame**-Quellen vor interner Projektion prüfen.
6. Quelle und Revision/Zeitpunkt kennzeichnen; FantasyPros-Rankings/-Grades nicht doppelt als unabhängige Stimmen zählen.
7. Zwei QB, zwei TE und vier gemeinsame RB/WR/TE-FLEX; keine isolierte Positionsrangliste als gesamte Start-Sit-Logik.
8. Incumbency-Bonus für bereits gesetzte Starter verbieten; alle damals legalen Alternativen prüfen.
9. Practice, Questionable, Inactive, tatsächlich spielberechtigt und erwarteter Workload getrennt behandeln.
10. Opportunity-Provenance: Snaps, Routes, Targets, Carries und Touches sowie Konkurrenz/temporäre Ausfälle prüfen.
11. Chronologische Decision-Opportunity-Matrix: Thursday, Early Game, 19-Uhr-Lock, Late Games und AutoSub auseinanderhalten.
12. Kein zeitreisender Vergleich mit Spielern, die zum Entscheidungszeitpunkt nicht erworben oder schon gelockt waren.
13. Gemeinsame FLEX-Portfolio-Risiken (Health, Floor, Ceiling, mehrfach ähnliche Unsicherheit) prüfen.
14. Decision Regret nur bei plausibler besserer Same-Information-Entscheidung; Outcome Regret separat.
15. Best Ball ausschließlich mit damals grundsätzlich verfügbaren/spielberechtigten Spielern und als Ex-post-Diagnose deklarieren.
16. Offizielle League-Istwerte gegen verfügbare Derived-Actuals abgleichen; unvollständige Derived-Actuals nicht scheinfinalisieren.
17. Vollständiges Roster einschl. Reserve/Taxi, aber 0 Punkte bei IR/Bye nicht als schlechte Leistung behandeln.
18. Roster Role und Roster Security getrennt bewerten; unklassifizierte Neueinkäufe nicht automatisch als Churn erklären.
19. Für einen Add immer die konkrete Cut-/Depth-/Insurance-/Liquiditäts-Opportunity-Cost prüfen; aus einem Wochenreview kein automatischer Drop.
20. Dynasty-Talent, NFL-Draftkapital und langfristige Stashes nicht aus einem einzelnen Week-Boxscore neu bewerten.
21. Salary/Cap als Managementfaktor, nicht als Qualitäts-/Startsignal; kein unimplementiertes Grading verwenden.
22. Kicker: standardmäßig nur ein Kicker, Stream erst bei relevantem Vorteil inklusive Slot-Kosten.
23. V4-C nur nachrangig zur getrennten Kalibrierung; künftige Regeländerungen brauchen eigene Validierung und Freigabe.

## 2. Unabhängige externe Quellen und Zeitgrenzen

**Pregame (bevorzugt für Decision Quality):**

- Cory Bonini, *Athlon Week-9 PPR FLEX Rankings*, veröffentlicht **07.11.2026, 18:42 EST**. Enthält tatsächliche gemeinsame RB/WR/TE-Rangplätze. https://athlonsports.com/fantasy/fantasy-football-flex-ppr-rankings-2026-nfl-week9
- *FantasyPros Week-9 Quick Grades*, veröffentlicht **08.11.2026, 08:54 EST**. Positionsbezogene Start/Sit-Grades, erzeugt unter Verwendung eigener Consensus-Rankings/-Projektionen und Derek Browns Primer; **nicht** unabhängig vom FantasyPros-ECR derselben Quelle. https://www.fantasypros.com/2026/11/fantasy-football-week-9-player-grades-start-sit-advice-2026/amp/
- Die Originalrevision jeder dynamischen Ranking-Zeile ist nicht archiviert; heute abgerufene Seiten dürfen **nicht** still als atomares Pregame-Lock-Snapshot gelten. Beide Seiten erschienen **nach JAX–BAL am Donnerstag** und sind daher **keine** zeitgenössische Thursday-Rechtfertigung.

**Postgame (nur Outcome und neue Usage/Role-Evidenz):**

- Mike Krueger, *FFToday Usage Notes – Week 9*, aktualisiert **09.11.2026**: tatsächliche Snap-, Touch- und Target Shares. https://www.fftoday.com/articles/krueger/26-usage-notes-wk9.html
- Jerry Donabedian, *RotoWire NFL Box Scores Week 9*, **09.11.2026**: Snap-, Routes-, Opportunities- und Spielverlaufsanalyse. https://www.rotowire.com/football/article/nfl-box-score-breakdown-week-9-recap-usage-stats-145932
- NFL.com, *Puka Nacua likely to be placed on injured reserve with turf toe, sprained MCL and PCL*, **09.11.2026** (Sean-McVay-Auskunft, kein vor dem Spiel verfügbares Injury-Wissen): https://amp.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl

### Externe Week-9-Grenzkandidaten (PPR Cross-Position vs. Positions-Grades)

| Spieler | Athlon FLEX | FantasyPros | Pregame-Einordnung |
|---|---:|---|---|
| Puka Nacua | 4 | WR A+ | eindeutig |
| Kenneth Walker III | 5 | RB A+ | eindeutig |
| Malik Nabers | 6 | WR A | klarer Start |
| D'Andre Swift | 14 | RB A | stark gestützter FLEX |
| Tetairoa McMillan | 27 | WR A− | stabiler FLEX trotz Matchup |
| Harold Fannin Jr. | 37 | TE C+ | begründete FLEX-Chance, gemischte Expertenlage |
| Tyler Warren | 49 | TE C | echte Alternative; kein klarer Vorrang |
| Colston Loveland | 54 | TE B+ | gute TE2-Präferenz |
| Saquon Barkley | 64 | RB B− | bewusster Grenzstart mit Usage-Risiko |
| Jaylen Waddle | 81 | verletzungsbedingt unsicher | nicht ex ante zwingend |
| Breece Hall | 87 | RB C | Rollensplit und Comeback-Risiko |
| Seth McGowan | nicht in Top-Rangliste | RB D+ | kein evidenzgestützter Week-9-Starter |
| Dylan Sampson | 84 | RB D | Bench trotz Usage-Upside vertretbar |

Die Grades sind **positionsbezogen**, keine numerischen Cross-Position-Projektionen; die beiden Quellen werden nicht einfach gemittelt. Die Rangfolge lässt Raum für einen abweichenden, ligaformat- und risikobasierten Start, muss dann aber begründet werden.

## 3. Chronologische Decision-Opportunity-Matrix

| Zeitpunkt MEZ | Damals zulässige/gesicherte Information | Aktion/Grenze | Ex-post-Evidenz / Urteil |
|---|---|---|---|
| **Fr 06.11., 02:15** | Jaguars-WR-Pool Thomas/Hunter/Meyers vor JAX @ BAL; im damaligen Dialog bewusst nicht gestartet | Thursday-Start danach gelockt; Meyers später **kein** Sunday-Ersatz | Meyers 10,50; Thomas 0,00; Hunter −1,10. Vorsicht plausibel, kein Sunday-Decision-Regret |
| **Sa 07.11.** | Swift neu im Roster; Fannin nach 21 Targets in zwei vorherigen Spielen erneut geprüft | Swift und Fannin in gemeinsamen FLEX-Pool aufgenommen | Swift 3,10/72 % Snaps; Fannin 12,20/84 % – zwei unterschiedliche Outcome-Pfade |
| **So 08.11., 15:30** | CIN @ ATL bereits gestartet | Chase Brown danach gelockt | 10,50, kein später legaler Swap |
| **So 08.11., ca. 17:57** | Pickens offiziell Out. Barkley, Warren, Hall als verfügbare Grenzoptionen; Hall trotz Aktivierung mit Allen-Split unsicher; Warren nach Rückkehr nicht garantiert volle alte Rolle | Erst Warren erwogen, nach Roberts Gegenfrage **Barkley** vor Warren/Hall; Robert bestätigt Aufstellung | Der finale Sleeper-Snapshot enthält Barkley; 8,20 vs. Warren 8,40 vs. Hall 11,70 |
| **So 08.11., 19:00** | Lock der besprochenen Starter und Grenzalternativen | Ab dann keine nachträgliche Ergebnisoptimierung | Ex-post Shough-/McGowan-Punkte sind kein ex ante offensichtlicher Start |
| **Mo 09.11., 02:20** | Bears-Buccaneers mit Swift und Loveland | Späte starterspezifische Entscheidung war bereits fixiert, AutoSub-Paarungen nicht bestätigt | Swift 3,10, Loveland 9,40 |
| **Di 10.11., nach Monday Night** | Final Scoring der Fantasy-Woche | Retrospektive, nicht Rewriting des Ex-ante-Records | 200,04 : 231,00 |

**AutoSub-Provenance:** League-Settings zum Entscheidungs-Cutoff erlaubten drei AutoSub-Slots. Der frühere Vorschlag Pickens → Warren wurde **nicht** als tatsächlich angelegte Paarung bestätigt. Auch nach vollständigem Sleeper-Scoring lässt sich die ursprüngliche Pairing- und Prioritätskonfiguration hier nicht sicher rekonstruieren. Keine behauptete AutoSub-Ausführung.

## 4. Tatsächlich gewertete Starter (13/13)

| Slot | Spieler | PPR-Punkte | Offense-Snaps* | Prozess-/Outcome-Kernaussage |
|---|---|---:|---:|---|
| QB1 | Mahomes | 16,48 | 94 % | Ex-ante klarer Start; danach Ellenbogen überprüfen |
| QB2 | Daniels | 14,56 | 100 % | Gegenüber Shough/Penix von unabhängigen Pregame-Grades bevorzugt |
| RB1 | Walker III | 36,30 | 65 % | Core-Start; effizienter Dreifach-TD-Output |
| RB2 | Chase Brown | 10,50 | 63 % | Korrekt als Early-Start fixiert |
| WR1 | Nacua | 35,00 | 93 % | Alpha-Rolle bestätigt; danach PCL/MCL/Turf-Toe-Ausfallrisiko |
| WR2 | Nabers | 9,30 | 79 % | Pregame hoch gerankt; moderate Punkte trotz relevanter Usage |
| TE1 | McBride | 12,40 | 83 % | Pflichtstart im 2-TE-System |
| TE2 | Loveland | 9,40 | 87 % | Ex-ante gegenüber Warren gestützt; Routes separat prüfen |
| FLEX | Swift | 3,10 | 72 % | Extern sehr hoch gerankt; 3,10 primär Outcome Regret |
| FLEX | McMillan | 15,60 | 80 % | Trotz Denver-Matchup durch Target-/Snap-Rolle gestützt |
| FLEX | Fannin Jr. | 12,20 | 84 % | 21 Targets in vorigen zwei Spielen; Week-9-TD bei geringem Volumen |
| FLEX | Barkley | 8,20 | 59 % | Nach Pickens-Out bestätigt; knappes Grenzurteil gegen Warren/Hall |
| K | Fairbairn | 17,00 | 0 % | Hold statt erneuten Streaming-Wechsels; 17,00 |

**13-Starter-Summe:** exakt **200,04**.  
**Snapshot-Disclaimer:** *Offensive Snap-Rates aus dem noch nicht als final deklarierten Week-9-Snap-Datensatz; keine pauschale Aussage zu Route Participation.*

### 4.1 Auffällig gute Prozesse und Outputs

- **Walker (36,30):** Ex-ante eindeutiger Start, 65 % Snaps trotz hoher drei-TD-Produktivität; seine Receiving-Fähigkeit liefert echten Ceiling-Wert. Der niedrigere Snap-Anteil ist für sich kein Rollenverlust.
- **Nacua (35,00):** Ex-ante Lock. 14 Receptions, 150 Yards, TD und 19 Targets bzw. 46,3 % Team-Target-Share belegen Alpha-Nutzung. Nach **dem letzten Spielzug** der Rams diagnostizierte Sean McVay MCL-/PCL-Verstauchungen und Turf Toe, IR wahrscheinlich (NFL.com 09.11.). **Outcome/Injury-Risiko, niemals rückwirkender Startfehler**.
- **McMillan (15,60):** Pregame trotz Broncos-Matchup eine relevante Target-/Snap-Rolle; 80 % Snaps bestätigen Nutzbarkeit.
- **Fairbairn (17,00):** Hold/kein marginaler erneuter Kicker-Stream war sinnvoll; FantasyPros vor dem Spiel K A−.

### 4.2 Enttäuschende Punkte, aber keine automatische falsche Wahl

- **Swift (3,10, 72 % Snaps):** Athlon FLEX14 und FantasyPros RB A unterstützten den Start. Postgame RotoWire: zwölf Carries für 31 Yards, keine Receptions, 13/18 RB-Opportunities. **Hoher Outcome Regret, wenig belastbarer Decision Regret.** Nach Bears-Bye die Konkurrenz durch Monangai prüfen; nicht als bewiesenen 72-%-Restseason-Workhorse verallgemeinern.
- **Nabers (9,30, 79 % Snaps):** trotz mäßiger Effizienz etablierter WR-Start; Athlon FLEX6 und FP A. Kein erneuter Beweis für einen sicheren Bench-Pfad.
- **Mahomes (16,48) / Daniels (14,56):** zwei sinnvoll gewählte QBs; Mahomes' spätere Ellenbogenverletzung ist ein Week-10-Recheck, kein Week-9-Startfehler. Shough später besser gepunktet, aber FP QB C statt Daniels B−.
- **Brown (10,50):** früher Lock und wertvolle RB-Usage, schwacher Output nicht gleich verfehlte Auswahl.
- **McBride (12,40):** zuverlässig zentraler TE, 83 % Snaps; primäre Pflichtposition weiter abgedeckt.

### 4.3 TE- und FLEX-Spezialprüfung

- **Fannin (12,20, 84 % Snaps):** Gegenüber dem Week-8-Review wurde er vor Kickoff ausdrücklich in den FLEX-Pool aufgenommen; die vorherigen **21 Targets / zwei Spiele** waren das richtige Startargument. Week 9 jedoch nur **zwei Receptions für 42 Yards und einen TD**, darunter der entscheidende lange Overtime-Score. Der Punktwert darf nicht als stabiles neues Target-Floor ausgegeben werden.
- **Loveland (9,40, 87 % Snaps):** RotoWire nennt **68 % Routes**, obwohl hohe Snapquote. Gutes TE2-Profil, aber Snap- und Route-Usage nicht gleichsetzen; Warren kam auf 8,40.
- **Barkley (8,20, 59 % Snaps):** 13 Touches in ineffizienter Eagles-Offense mit Joe Milton. Vor dem Lock bestand eine realistische Upside-These; zugleich war nach Week 8 ein reduzierter Workload bekannt. Grenzentscheidung ausdrücklich **niedrige bis mittlere Konfidenz**.

## 5. Alle weiteren 17 regulären aktiven Spieler (Bench)

| Spieler | Position | Week-9-PPR | Offense-Snaps* | Neue Rolle-/Entscheidungsevidenz |
|---|---|---:|---:|---|
| Michael Penix Jr. | QB | 14,48 | 100 % | 100 % Offense-Snaps; ungefähr Daniels-Niveau, ex ante schwächer gerankt |
| Tyler Shough | QB | 19,70 | 100 % | 100 % Snaps; höhere Punkte als Daniels, dennoch nicht ex ante klar bevorzugt |
| Breece Hall | RB | 11,70 | 43 % | 43 % Snaps, 18 Touches; Allen weiterhin mit mehr Routes |
| Cam Skattebo | RB | 0,00 | – | Nicht eingesetzt; keine Performance-Schlussfolgerung |
| Dylan Sampson | RB | 7,80 | 64 % | 64 % Snaps bei 11 Touches; Receiving-/Entwicklungspfad |
| Jeremiyah Love | RB | 0,00 | – | IR/nicht einsatzfähig; kein Score-Urteil |
| Kyle Monangai | RB | 0,00 | – | Kein Spiel; Swift-Konkurrenz nach Bears-Bye beobachten |
| Seth McGowan | RB | 11,20 | 31 % | 31 % Snaps, sieben RB-Opportunities; Contingent Upside |
| Tyler Warren | TE | 8,40 | 83 % | 83 % Snaps; Barkley-Vergleich ex ante umstritten |
| Brian Thomas Jr. | WR | 0,00 | 34 % | 34 % Snaps, null Targets; klares Rollen-Warnsignal |
| George Pickens | WR | 0,00 | – | Offiziell Out/late scratch; Barkley wurde wirksam eingesetzt |
| Germie Bernard | WR | 0,00 | – | Bye; kein Leistungsurteil |
| Jakobi Meyers | WR | 10,50 | 68 % | Thursday schon abgeschlossen; 10,50 nicht Sunday austauschbar |
| Jaylen Waddle | WR | 3,20 | 19 % | 19 % Snaps; Concussion, medizinischer Recheck |
| Ladd McConkey | WR | 0,00 | – | Back spasms vor dem Spiel, nicht eingesetzt; kein normales Nullpunkte-Spiel |
| Marvin Harrison Jr. | WR | 4,00 | 46 % | 46 % Snaps; Routen-/Rollen-Recheck |
| Travis Hunter | WR | -1,10 | 11 % | 11 % Offense-Snaps; kurzfr. geringe Startbarkeit, Talentthese separat |

### 5.1 Materiale Bench-Entwicklungen

**Hall (11,70):** 18 Touches gegenüber Allen mit zehn; zugleich Allen **58,7 % vs. Hall 42,9 % Snaps** und 15 vs. acht gelaufene Routes (FFToday). Hall erhielt also mehr direkte Arbeit, aber keine sichere Passing-Game-Dominanz. **Barkley vor Hall** ist im Nachhinein −3,50 Punkte, doch die vorsichtigen Pregame-Quellen und der tatsächliche Split stützen die damalige Vorsicht.

**Warren (8,40):** 83 % Snaps signalisieren eine kräftigere Rückkehr als die vorherigen 72 %. Der Pregame-Case war trotzdem nicht eindeutig: Athlon ordnete Warren (49) vor Barkley (64), FantasyPros sah TE C versus RB B−. **Nur +0,20** für Warren ex post, **kein substantieller Fehler**.

**Sampson (7,80):** 64,4 % Browns-Snaps gegenüber Judkins 34,2 %, aber Judkins mehr Touches (16 vs. elf). Value-Signal ist die eigenständige Receiving-/Snap-Rolle, kein gesichertes Lead-Backfield.

**McGowan (11,20):** Taylor mit 18 RB-Opportunities, McGowan mit sieben. Das bestätigt einen **contingent** Backup-Pfad; kein unstrittiger Pregame-Start über Swift, dessen Expertenränge klar höher lagen.

**Brian Thomas Jr. (0,00) / Hunter (−1,10):** Thomas 33,9 % Snaps und null Targets; Hunter 11 % Offense-Snaps. Kurzfristige Startability sehr schwach. Die individuelle Dynasty-Talentthese muss dennoch getrennt bleiben.

**Harrison (4,00):** 46 % Offense-Snaps machen den Einsatz-/Route-Recheck wichtiger als den isolierten Boxscore.

**Waddle (3,20):** Concussion und nur 18,7 % Snaps, kein belastbares 2027-/rest-of-season-Talenturteil. **McConkey (0,00):** Rückenkrämpfe im Warmup, kein Einsatz; FFToday berichtet äußerst späte öffentliche Verfügbarkeitsinformation. Solche späten Ereignisse sind nicht nachträglich als früh erkannter Start/Sit-Fehler zu verbuchen.

**Meyers (10,50):** Thursday-Lock, am Sonntag keine Alternative. **Pickens (0,00):** als Out korrekt ersetzt. **Penix/Shough:** brauchbare QB-Tiefe, aber ihre Ergebnisse machen die Daniels-Wahl nachträglich nicht unvernünftig.

## 6. Reserve und Taxi – restliche sieben kontrollierte Spieler

| Spieler | Bereich lt. 08.11.-Roster-Snapshot | PPR | Offense-Snaps* | Bewertung |
|---|---|---:|---:|---|
| Jaxson Dart | Reserve | 0,00 | – | Quarterback-Coverage nur bei tatsächlicher Verfügbarkeit |
| Jonathon Brooks | Reserve | 0,00 | – | Comeback-/Langfrist-Asset, nicht Week-9-Startoption |
| Alec Pierce | Reserve | 0,00 | – | Gesundheit und Aktivierung abwarten |
| Davante Adams | Reserve | 0,00 | – | Veteran-Asset; Rückkehr und Win-now-Nutzen prüfen |
| De'Zhaun Stribling | Reserve | 0,00 | – | Prospect; keine aktive Churn-Kapazität |
| Antonio Williams | Taxi | 5,50 | 84 % | 84 % Snaps und 17,6 % Target Share, vielversprechende Role-Evidenz |
| Chris Bell | Taxi | 0,00 | 63 % | 63 % Snaps; Einsatz statt Fantasy-Ertrag beobachten |

**Williams:** FFToday dokumentiert 83,9 % Offensive Snaps und 17,6 % Target Share – das ist ein echtes Rollen-/Entwicklungssignal trotz nur 5,50 PPR. **Bell:** 63 % Snaps ohne Fantasy-Produktion; weiterer Usage-Recheck statt automatischer Cut.

**Roster-/Taxi-Regel:** Die Taxi-Plätze sind nach Saisonstart gelockt. Reserve- und Taxi-Spieler zählen nicht als freie aktive Churn-Slots; null Punkte wegen fehlender Spielberechtigung sind kein Qualitätsnachweis. Eine spätere Cut-Bewertung benötigt NFL-Draftkapital, Teamrolle, Trade-/Dynasty-Wert, aktuelle Security-Klassifikation und reale Roster-Opportunity-Cost.

## 7. Grenzfall Barkley – Warren – Hall: Same-Information-Review

| Kandidat | Pregame-Hauptargument | Pregame-Gegenargument | Ex post |
|---|---|---|---:|
| Barkley **gewählt** | bekanntes Talent-/TD-Ceiling, freigegeben, potenziell größere Lead-RB-Nutzung | Week-8-Limit, Reinjury-/Usage-Risiko, Athlon FLEX64 | **8,20** |
| Warren **bencht** | klare TE-Target-Perspektive, Athlon FLEX49 | reduzierte Vorwochen-Snaps nach Rückkehr, FP TE C, Matchup/Route-Fragen | **8,40** |
| Hall **bencht** | PPR-Receiving-/Touch-Upside bei Comeback | Allen-Split, schwacher KC-Run-Gegner, FP RB C, Athlon FLEX87 | **11,70** |

**Re-Decision mit damaligem Wissen:** Barkley knapp vor Hall bleibt **vertretbar**, Warren bleibt eine plausible Alternative. Die Auswahl war bewusst eng und muss nicht künstlich nach Ergebnis neu sortiert werden. **Outcome Regret**: Hall +3,50, Warren +0,20; **kein belegbar hoher Decision Regret**.

**Portfolio statt vier Inselurteile:** Gewählte FLEX-Vierergruppe Swift (3,10), McMillan (15,60), Fannin (12,20), Barkley (8,20) = **39,10 Punkte**. Swift hatte den externen Wochenrückhalt, McMillan stabilere Usage, Fannin vorher hohe Targets und Barkley medizinisch bedingte Workload-Unsicherheit. Diese Risikomischung war nicht ideal abgesichert, aber nicht einfach aus den späteren Punkten als fahrlässig zu bezeichnen.

## 8. Hindsight-Best-Ball – nur Diagnose, nicht angeblich damaliger Entscheidungsraum

Verwendet wurden **2 QB / 2 RB / 2 WR / 2 TE / 4 RB/WR/TE-FLEX / 1 K**, normale aktive Week-9-Spieler nach damaligem Rosterpool; Reserve und Taxi ausgeschlossen; tatsächliche Week-9-Fantasy-Punkte als **Oracle-Information**.

| Vergleich | Summe | Differenz zum gewerteten Lineup |
|---|---:|---:|
| Gewertet | **200,04** | – |
| Nachträgliches **Sunday-Oracle** (Meyers nach Thursday ausgeschlossen) | **216,78** | **+16,74** |
| Nachträgliches **Full-Week-Oracle** (Meyers theoretisch vor Thursday verfügbar) | **217,98** | **+17,94** |
| Gegner Flo | **231,00** | – |

**Sunday-Oracle-Deltas:** Daniels → Shough **+5,14**, Barkley → Hall **+3,50**, Swift → McGowan **+8,10**. Ex post totale +16,74, jedoch kein Beweis, dass alle drei Wechsel vor Kickoff mit den damals bekannten Informationen eine bessere Entscheidung gewesen wären.

**Kritischer Realisierbarkeitsvorbehalt:** Das Sunday-Oracle bildet Start-/Positions- und vorangegangenen Thursday-Lock ab, **nicht** rekonstruierte individuelle AutoSub-Pairings oder minutengenaue Eligibility-Ereignisse; deshalb kein forensisch abschließend zertifiziertes reales Maximum. Das Full-Week-Oracle ist explizit ein rein mathematischer Rückblick mit Wissen über Donnerstag und Sonntag. Schon das Sunday-Oracle hätte **216,78 : 231,00** und damit **−14,22** bedeutet: **Die Niederlage wäre auch bei dieser nachträglich besten Sonntagskombination geblieben.**

## 9. V4-C nur nachrangige Modellkalibrierung

Das im Abruf vorliegende App-PlayerWeekFantasy-Snapshot nennt für die 13 tatsächlichen Starter **205,88** Projektionspunkte gegenüber **200,04** Ist (netto **-5,84**). Die geringe Gesamtfehler-Summe entsteht durch kompensierende große Einzelabweichungen:

| Spieler | Modell | League-Ist | Ist − Modell |
|---|---:|---:|---:|
| D'Andre Swift | 18,14 | 3,10 | -15,04 |
| Kenneth Walker III | 22,13 | 36,30 | 14,17 |
| Puka Nacua | 23,72 | 35,00 | 11,28 |
| Malik Nabers | 16,18 | 9,30 | -6,88 |
| Trey McBride | 18,79 | 12,40 | -6,39 |
| Ka'imi Fairbairn | 10,86 | 17,00 | 6,14 |

Die gegenwärtige Projektionsveröffentlichung ist **kein garantiert vor Kickoff eingefrorener Snapshot** und das Derived-/App-Actual-Finalisierungsflag fehlt noch. Daher wird daraus **keine** abschließende ex-ante Modellgüte- oder Entscheidungsnote abgeleitet; zunächst die Source-/Derived-Actual-Finality und League-Scoring-Identität klären.

## 10. Künftige roster- und entscheidungsbezogene Rechecks

1. **Sofortige Health-Rechecks:** Nacuas erwartete IR-Platzierung, Mahomes' Ellenbogen, Waddles Concussion-Protokoll, McConkeys Rücken. Diese Information betrifft Week 10 und Playoff-Coverage, nicht die Week-9-Decision-Quality.
2. **RB-Werte:** Walker bleibt Kernstarter; Hall-/Allen-Touch-vs.-Routes-Split neu prüfen; Sampsons Snap-vs.-Touch-Verteilung beobachten; McGowan als Taylor-Insurance statt Starterrolle einstufen; Swift nach Bears-Bye und Monangai-Rückkehr neu bewerten; Barkley-Workload und Eagles-QB-Umfeld prüfen.
3. **TE-Werte:** Fannins Target- und Route-Volumen nach Overtime-TD validieren; Lovelands 87 % Snaps vs. 68 % Routes nicht verschmelzen; Warrens Recovery-Snaps und Targets vergleichen; McBride Kernstarter.
4. **WR-Werte:** Thomas/Hunter-Harrison-Role-Rechecks sind dringlicher als reine Punktecharts; Antonio Williams Taxi-Signal positiv; Bell Usage weiter beobachten; Nabers/McMillan nicht wegen moderater Week-Punkte abwerten.
5. **QB-Coverage:** Shough und Penix als reale Absicherung im 2-QB-Format; keine automatische Luxus-Quarterback-Akkumulation ohne realistische Start- und Slot-Nutzenpfade.
6. **Kicker:** Fairbairn als ein gehaltener Kicker ohne Week-9-Reue; nächster Wechsel nur bei verifiziertem materiellen Vorteil/Bye/Jobverlust.
7. **Teamfenster:** 4–5 bedeutet in der sechs Teams / vier Playoff-Plätze-Liga **nicht automatisch Rebuild**; die kurzfristige Verletzungswelle und echte FLEX-Ersatzqualität sind entscheidend.

**Methodische Vorschläge – NICHT umgesetzt:** datierte Snapshots der relevanten externen Pregame-Rankingzeilen, eigenständige Thursday-/Early-/Late-Entscheidungsepochen, Routes/Targets/Touches standardmäßig neben Snaps und eine explizite Quelle-/Derived-/League-Finality-Brücke. Änderungen an kanonischen Regeln, State, Teamrollen oder operativen Workflows bedürfen eigenständiger Prüfung/Freigabe.

## 11. Abschließendes Urteil und Unsicherheiten

| Feld | Ex-ante-Prozessbewertung | Outcome getrennt |
|---|---|---|
| Pickens Out → Barkley wirksam gesetzt | bestätigt, korrekte Injury-Reaktion | Barkley 8,20 |
| Walker/Nacua | klare, extern gestützte Starts | 36,30/35,00; Nacua-Verletzung danach |
| Swift gestartet | ex ante stark gestützt; kaum Decision Regret | 3,10, hoher Outcome Regret |
| Fannin in FLEX aufgenommen | gute Verbesserung ggü. Week 8 | 12,20 mit nur zwei Catches |
| Loveland statt Warren | gut vertretbar, Quellen gemischt | 9,40 vs. 8,40 |
| Barkley vs. Warren vs. Hall | enge, bewusst korrigierte Wahl, niedrige–mittlere Konfidenz | maximal +3,50 entgangener Outcome |
| QB Daniels statt Shough | vernünftig, Pregame-Grade klarer bei Daniels | −5,14 Hindsight |
| Kicker Fairbairn gehalten | sinnvoll | 17,00 |
| AutoSubs | Konfiguration unbestätigt | keine gesicherte Pairing-Aussage |
| Best Ball / Modell | als getrennte Diagnosen, **keine** Pregame-Entscheidungsrichter | Sunday-Oracle +16,74, trotzdem Niederlage |

**Gesamturteil:** Überwiegend **ordentlich bis gute Ex-ante-Entscheidungsqualität** bei entmutigendem Ergebnis gegen ein sehr punktstarkes gegnerisches Team. Die primären aktuellen Risiken sind **Gesundheit und langfristige Stabilität einiger NFL-Rollen**, nicht eine einzelne angeblich offensichtlich falsche Week-9-FLEX-Wahl.

**Nachvollziehbarkeitsgrenzen:** Nicht revisionssicher archivierte Ursprungsversionen aller Expertenränge; nicht rekonstruierte AutoSub-Assignments; Week-9-Snap-Quelle noch Finalized=false/14 statt 15 Spiele; App-League-Final-Scored-Week und App-PlayerWeekFantasy-Actuals noch nicht auf dem gleichen Finalitätsstand wie Sleeper-Matchup. Das Urteil ist **keine** versiegelte Entscheidungsakte und keine Revision des [Ex-ante-Dokuments](2026-week-09-lineup-ex-ante-decisions.md).
