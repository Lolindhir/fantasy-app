# Mighty Giants — NFL Week 10 2026: Roster + Lineup Postmortem

**Rekonstruktion und Persistierung:** 18.11.2026, nach abgeschlossenem Week-10-Liga-Scoring.  
**Team:** Mighty Giants (Robert, TeamID 1; CanonicalLeagueRosterID `clr-a8e576139994570d82e9ea2ed3f42b1b`).  
**Gegner:** Jan / Mammoth Marauders (TeamID 4).  
**Ergebnis:** **221,08 : 204,32**, Sieg um **16,76** Punkte; Bilanz anschließend **5–5**, Tabellenplatz **2** (vorher 5).  
**Format:** 6 Teams, Full PPR, **2 QB / 2 RB / 2 WR / 2 TE / 4 RB-WR-TE-FLEX / 1 K**.  
**Dokumenttyp:** Auf ausdrückliche Nutzerfreigabe gespeicherte retrospektive Fantasy-Management-Analyse. Kein versiegelter generischer Decision Record und keine Modifikation der historischen Ex-ante-Akte. Keine Spielertransaktionen, keine Liga-/Salary-/Modell-/Workflow-Änderungen.

## 0. Evidenzhierarchie, Quellen und zeitliche Trennung

1. **Offizielles Ligaergebnis und kontrollierter Wochenpool:** `data-source/leagues/nfl-reise/seasons/2026/matchups/week-10.json` (Blob `f867c9d0869d0853d230906b3b0bb319b2f7a738`), `public/data/Matchups.json` (`af7c68c9e35f00cd5bd92dcb5f7738bd1164b52b`), `public/data/League.json` (`01dde838e5f9f027d00304e995f9c11908fc76b8`). Canonical-League-Matchup enthält exakt 13 gewertete Starter, **221,08** Team-Punkte und **204,32** für Jan sowie 37 kontrollierte Spieler; die einzelnen Starterpunkte summieren sich exakt auf das Teamresultat.
2. **Pregame-Entscheidungswahrheit:** die unveränderte [Week-10-Ex-ante-Akte](2026-week-10-lineup-ex-ante-decisions.md), Capture **Sonntag, 15.11.2026, 13:39:57 MEZ**. Dort sind Aufstellung, Gründe, damals gelesene Expertenzeilen, Zeitfenster und die offenen AutoSub-Unklarheiten dokumentiert. **Nicht nachträglich aus Week-10-Ergebnissen umdeuten.** Die drei Thursday-Starter waren beim Capture bereits gelockt; für den Zeitpunkt vor Donnerstag liegt keine gleichwertig versiegelte Decision-Akte vor.
3. **Historische Zugehörigkeit und Roster-Buckets:** `data-source/leagues/nfl-reise/seasons/2026/rosters.json` (`166bb5c167f4f9a30bd8983c93819580a1fd894d`) und 37er-Week-10-Matchup-Pool; Quervergleich mit dem Ex-ante-Capture und `fantasy-management/generated/operations/managed-roster-signals.json` (`2392e916c1775b7ad4c66cda0b9be73a2e7c42e9`, erzeugt 17.11.). Die Ex-ante-Akte belegt 30 aktive Plätze, 5 Reserve und 2 Taxi. Ein späterer Readmodel-Bucket allein belegt nicht alle minutengenauen Wochenwechsel.
4. **Best-Ball-Diagnose:** `data-derived/team-week-performance/nfl-reise/2026/10.json` (`0c063db8d7893de1c9d52dae9ba105088b255e76`). **244,78** theoretisches Maximum / **90,3178 %** Effizienz / **23,70** ungenutzte Punkte. Taxi und Reserve/IR gehören zur vollständig kontrollierten Population; Best Ball ist keine Behauptung, dass der reale Manager alle erforderlichen Aktivierungen/Cuts sinnvoll oder rechtzeitig durchgeführt hätte. Maßgeblich ist die [präzisierte Format-Notiz](../../../league-context/league-format-notes.md).
5. **Rollen-/Opportunity-Evidenz:** `data-source/nfl/snap-counts/2026/10.json` (`31bb81acfc40e5c633a85a6cf983ce93ee6e64ee`, **`Finalized=false`**), teils mit Positions-/Spielauszügen aus zeitgenössischen externen Boxscores. Snaps sind keine Routes und keine Targets; unterschiedliche Anbieter können leicht verschiedene Snap-Zähler ausweisen.
6. **Abschluss-/Datenqualitätsgrenze:** Die Week-10-League-Wertung ist **final**, aber NFL-Snap-Finality steht im Materialisierungsstand noch aus. Als Hilfsabgleich werden ausschließlich finale tatsächliche Punkte des abgeleiteten Player-Week-Datensatzes benutzt, nicht Prognosen. Bekannte Ist-Diskrepanz: **Travis Hunter: League 3,90, Derived 5,90** – bei dieser Position bleibt der Liga-Score verbindlich und die abweichende abgeleitete Ist-Zeile ungeklärt. Tatsächliche AutoSub-Paarungen und historische Aktivierungs-Transaktionspfade liegen nicht als vollständiger atomarer Lock-Snapshot vor.

### Externe Quellen und deren Zeitstatus

**Damals vor dem relevanten Sonntag-Lock erfasste Gegenchecks** (Details und Capture-Provenienz im unveränderten Ex-ante-Dokument, nicht als heutige Live-Rankings neu datiert):
- [NFL Week-10-Injury-Report](https://amp.nfl.com/news/nfl-week-10-injury-report-2026-season) und [offizielles NFL-Injury-Board](https://www.nfl.com/injuries/league/2026/REG10): Walker Out; Pickens und Fannin ohne finale Game-Designation.
- [Athlon / Cory Bonini, PPR-FLEX Week 10](https://athlonsports.com/fantasy/fantasy-football-flex-ppr-rankings-2026-nfl-week10): im damaligen **13:40-MEZ-Capture** McMillan #10, Fannin #49, Meyers #55, Bernard #73; Warren #41, Chase Brown #43 und Pickens #48. Die Seite wurde später verändert, daher gilt **nur die archivierte Rangzeile** als damals überprüft.
- [Steelers.com, Matt's Stats vor PIT @ CIN](https://www.steelers.com/news/matt-s-stats-week-10-at-bengals): Bernard vorher vier Target Shares **30/27/18/23 %**.
- [Sharp Football, Rich Hribar: PIT @ CIN](https://www.sharpfootballanalysis.com/fantasy/steelers-bengals-week-10-fantasy-football-preview-nfl-worksheet-rich-hribar-2026/amp/): Bernard-Slot-/YAC-Profil und CIN-Matchup.
- [FantasyPros / Derek Brown, Fannin](https://www.fantasypros.com/nfl/notes/493115/harold-fannin-jr-2026-week-10-outlook.php) (**Sit** wegen Houston-Defense) versus [FantasyPros / Ellis Johnson, Fannin](https://www.fantasypros.com/nfl/notes/493024/harold-fannin-jr-2026-week-10-outlook.php) (Target-gestützter Start unter Watson). Nicht als zwei voneinander unabhängige FantasyPros-Konsense zählen.
- [FantasyPros / Derek Brown, Meyers](https://www.fantasypros.com/nfl/notes/493227/jakobi-meyers-2026-week-10-outlook.php) (**FLEX-tauglich**); Stoned Lack Folge 608 und Aftermath gemäß Nutzermaterial/zeitgenössischer Ex-ante-Akte (Meyers-Game-Script-Sorge, Bernard-Herabstufung und Fannin-Gegenposition). Die ASR-Transkripte werden nicht als unabhängig archivierte Online-Originalquelle ausgegeben.

**Erst nach dem Spiel veröffentlichte Evidenz** – ausschließlich für Outcome und beobachtete Rolle, **nicht** als ursprüngliche Entscheidungsbegründung:
- [NFL Week-10-Learnings](https://www.nfl.com/news/2026-nfl-season-week-10-what-we-learned-from-sunday-s-games), [NFL Pro Pickens-Usage](https://pro.nfl.com/games/game/ab789ac9-4feb-11f1-abca-2c54536568a9), [Cowboys Bericht](https://www.dallascowboys.com/news/updates-november-2026): Pickens 18 Targets, 11 Catches, 145 Yards, 3 TD, 51 Routes.
- [Cleveland Browns zu Fannin](https://www.clevelandbrowns.com/news/harold-fannin-jr-s-30-yard-reception-sets-up-go-ahead-touchdown-in-week-10-players-of-the-game) und [Houston Texans Box Score](https://www.houstontexans.com/gameday/2026/week-10-texans-at-browns/box-score): 7 Receptions, 91 Yards (9 Targets laut NFL-Pro/Rollenbericht).
- [Steelers–Bengals Spielbericht](https://www.steelers.com/news/steelers-fall-at-bengals-38-18), [Bernard CBS-Review](https://www.cbssports.com/fantasy/football/news/steelers-germie-bernard-no-catches-in-blowout-loss/) und [RotoWire Week-10-Usage](https://www.rotowire.com/football/article/nfl-box-score-breakdown-week-10-recap-usage-stats-146792): Bernard 3 Targets, 0 Catches, 1 Rush für 10 Yards; sehr hoher Snap-/Route-Anteil, aber kaum Receiving-Opportunity.
- [NBC Sports Warren](https://www.nbcsports.com/fantasy/football/player-news/2026-11-15/tyler-warren-silent-in-week-10-win-over-dolphins), [NFL Warren Game Log](https://www.nfl.com/players/tyler-warren/stats/logs/2026/): 2/3 für 1 Yard und 1 Rush für 3 Yards.
- [RotoWire Meyers](https://www.rotowire.com/football/headlines/jakobi-meyers-news-three-grabs-in-week-10-win-648051): 3/6 für 34 Yards.
- [NFL McGowan Game Log](https://www.nfl.com/players/seth-mcgowan/stats/logs/), [On3 McGowan Week 10](https://www.on3.com/teams/kentucky-wildcats/news/bbnfl-week-10-another-week-another-touchdown-for-seth-mcgowan/): 12 Carries/77 Yards/1 TD.
- [NFL Chase Brown Game Log](https://www.nfl.com/players/chase-brown/stats/logs/2026/), [Cardinals McBride Game Log](https://www.azcardinals.com/team/players-roster/trey-mcbride/logs/), [NBC McMillan](https://www.nbcsports.com/fantasy/football/player-news/2026-11-15/mcmillan-held-to-35-yards-in-week-10-win): reale Produktion von Brown, McBride und McMillan.

## 1. Ligaergebnis, Kontext und Siegtreiber

Die Mighty Giants gewinnen **221,08 : 204,32**, nach 4–5 vor dem Spiel nun **5–5**, im veröffentlichten Standings-Readmodel von Rang **5 auf 2**. Der Sieg ist sportlich wertvoll im engen Playoff-Rennen; er beweist nicht, dass jede einzelne Pregame-Entscheidung optimal war.

| Week-10-Ligapartie | Offizielles Resultat |
|---|---:|
| FloDHL99 – Marci0231 | 267,94 : 200,84 |
| Lolindhir – JanB94 | 221,08 : 204,32 |
| TimpaBay – DennisLACards | 139,92 : 163,08 |

Gegen Jan kompensierten insbesondere **Pickens (43,50), Mahomes (35,42), Chase Brown (28,30) und Skattebo (27,20)** die schwachen Beiträge von Bernard, Warren und anderen. Jan erhielt von Burrow **33,16**, Purdy **31,66**, Ja'Marr Chase **34,10**, Bhayshul Tuten **20,30**, Jefferson **16,40** und Garrett Wilson **15,60**; auf der Gegenseite blieben u. a. Gesicki **1,90**, Allgeier **1,40** und Wan'Dale Robinson **4,00** zurück. Ein Gegner-Score über 200 war kein Selbstläufer; die eigenen Spitzenleistungen entschieden das Duell.

## 2. Chronologische Decision Opportunities

| Zeitpunkt (MEZ) | Damalige reale Handlungsmöglichkeit | Postmortem-Grenze |
|---|---|---|
| **Vor Fr 13.11., 02:15** (US Thursday: WAS @ NYG) | Daniels/Nabers/Skattebo mussten spätestens bis zum individuellen Kickoff gesetzt sein. Taxi-Spieler **Antonio Williams** gehörte grundsätzlich zum kontrollierten Aktivierungspool, hätte aber **vor seinem Donnerstag-Kickoff** auf einen regelkonformen aktiven Platz befördert werden müssen (ggf. Cut eines aktiven Spielers und sinnvolle Slotbelegung). | Kein gleichwertig dokumentierter Pregame-Decision-Record vor Donnerstag; ein hypothetischer Williams-Start ist **kein** belegter damals unterlassener, offensichtlich sinnvoller Move. Eine Aktivierung am Sonntag wäre zu spät gewesen. |
| **So 15.11., 13:39:57** | Archivierter Ex-ante-Stand: **13/13** tatsächlich gesetzte Starter, 37 kontrollierte Spieler, keine Waiver-Claims. Drei Thursday-Starter bereits fixiert. | Der ex-ante festgehaltene Start/Sit-Grenzpool: Fannin, Bernard, Meyers, Sampson; zusätzlich McGowan/gesundheitsbedingte Alternativen. |
| **So 15.11., 15:30** | Frühes International Game NE–DET; laut Ex-ante keine Mighty-Giants-Startalternative betroffen. | Keine rückwirkende Änderung gelockter Donnerstagspunkte. |
| **So 15.11., vor 19:00** | Fannin, Meyers, Sampson, Hall, Warren, McMillan, Mahomes, Fairbairn und je nach Slot McGowan als noch zu disponierende Optionen. | Die Wahl **Fannin + Bernard statt Meyers** war zu diesem Zeitpunkt bereits diskutiert und bestätigt; Meyers ließ sich nach seinem 19-Uhr-Lock nicht auf den Bernard-Slot am Montag übertragen. |
| **So 15.11., 22:05 / 22:25** | McBride und Pickens bis zu ihren individuellen Late-Kickoffs disponibel. | Pickens war freigegeben, aber die vollständige Rückkehr-Nutzung war nicht garantiert; keine erfundene nachträgliche Injury-Sicherheit. |
| **Mo 16.11., 02:20** | Chase Brown/Bernard in PIT–CIN; nur noch tatsächlich ungeblockte, positionsberechtigte Auswechslungen möglich. | Keine zeitreisenden Meyers- oder Thursday-Williams-Swaps. |
| **Di 17.11., 02:15** | McConkey in LAC–BAL; vor diesem Spiel als unsicher besprochen, später offiziell Out. | Kein vorausgesetzter später Backup-Pfad. |
| **Nach finalem Scoring** | Retrospektive, kein Start/Sit-Eingriff mehr. | Ex-ante-Akte unverändert; Resultat- und Decision-Urteil getrennt. |

**Tatsächliche Ausführung:** Die finalen 13 Starter stimmen exakt mit dem am Sonntag bestätigten Lineup überein; ein Week-10-Waiver-Claim der Mighty Giants wurde nicht ausgeführt. Die Liga erlaubt bis zu drei AutoSubs, aber konkrete Paarungen/Prioritäten sind aus dem historischen Datensatz **nicht nachgewiesen**. Es wird weder eine AutoSub-Ausführung noch eine Absicherungswirkung erfunden.

## 3. Die 13 tatsächlich gewerteten Starter

| Slot | Spieler | Full-PPR-Punkte | Offense-Snap-Anteil* |
|---|---|---:|---:|
| QB1 | Patrick Mahomes | 35,42 | 95 % |
| QB2 | Jayden Daniels | 22,76 | 100 % |
| RB1 | Cam Skattebo | 27,20 | 89 % |
| RB2 | Breece Hall | 14,80 | 58 % |
| WR1 | George Pickens | 43,50 | 89 % |
| WR2 | Malik Nabers | 7,40 | 80 % |
| TE1 | Tyler Warren | 2,40 | 86 % |
| TE2 | Trey McBride | 8,70 | 83 % |
| FLEX1 | Chase Brown | 28,30 | 73 % |
| FLEX2 | Tetairoa McMillan | 6,50 | 80 % |
| FLEX3 | Harold Fannin Jr. | 16,10 | 87 % |
| FLEX4 | Germie Bernard | 1,00 | 95 % |
| K | Ka'imi Fairbairn | 7,00 | – |
| **Gesamt** | | **221,08** | |

\* Snap-Daten aus Week-10-nflverse, **nicht vollständig finalisiert**; Kicker ohne offensive Snap-Basis.

### QB: klare Rollen- und Qualitätsentscheidung

**Patrick Mahomes (35,42):** Der stark besetzte und verfügbare QB1 rechtfertigte den Start vor Penix (13,34) und Shough (10,98). Der Prozess war auch ohne Kenntnis der 35,42 Punkte durch Startrolle, etablierte Nutzung und damalige externe QB-Signale gestützt. **Jayden Daniels (22,76)** war beim Sonntag-Capture bereits fixiert; seine Leistung darf den ursprünglichen Thursday-Start nicht rückwirkend begründen.

### RB und FLEX mit substantieller Rolle

**Cam Skattebo (27,20):** 18 Carries, 78 Rush-Yards und 2 Rush-TDs, dazu 3 Catches für 44 Yards; sehr hohe Offense-Beteiligung. Echte Wochen-Rollenbestätigung, allerdings bereits Thursday-gelockt. **Breece Hall (14,80):** 11 Carries/41 Yards und 4 Catches/67 Yards; 58 % statt 43 % Offense-Snaps in Week 9. Der Start war insbesondere als Ersatz für den offiziell ausgefallenen Walker begründet, nicht durch eine garantierte neue Lead-Rolle. **Chase Brown (28,30):** 10 Carries/44 Yards, 9 Targets/8 Receptions/39 Yards und 2 Receiving-TDs; hohe Full-PPR-Wirkung über tatsächliche Receiving-Nutzung und TD-Varianz.

### WR: strukturelle Signale nicht mit Boxscores verwechseln

**George Pickens (43,50):** 18 Targets, 11 Receptions, 145 Yards, drei TDs, **51 Routes** und 89 % Offense-Snaps. Die Sorge einer tatsächlichen gesundheitlichen Einschränkung nach Hamstring-Rückkehr bestätigte sich nicht. Hohe Targets/Routes sind das tragende Week-11-Rollensignal; drei TDs dürfen nicht als verlässlicher Normalfall fortgeschrieben werden. Der Wechsel für den IR-Spieler Puka war schon *vorher* korrekt begründet.

**Malik Nabers (7,40):** 7 Targets/5 Catches/44 Yards, 80 % Snaps; ein verlorener Fumble belastete den Score. Der bloße Fantasy-Wert beweist keinen Rollenverlust. Bereits Thursday fixiert. **Tetairoa McMillan (6,50):** 7 Targets/3 Catches/35 Yards und 80 % Snaps; schwache Conversion bei weiter erkennbarer Receiving-Rolle. Keine ausreichende Basis, aus einem Spiel eine dauerhafte Herabstufung abzuleiten.

### TE: Zielvolumen und Snap-Anteil trennen

**Trey McBride (8,70):** 5 Catches auf 5 Targets, 37 Yards, 83 % Offense-Snaps bei begrenzter Cardinals-Produktion gegen die Rams. Weiterhin nachvollziehbarer Pflicht-TE-Start. **Tyler Warren (2,40):** 2/3 für 1 Yard und 1 Rush für 3 Yards, trotz ca. 86 % Snaps. Das ist ein echter Target-/Opportunity-Ausfall, nicht einfach Nichterscheinen auf dem Feld. Seine starke externe Pregame-Startbewertung macht einen schlechten Boxscore allein noch nicht zum Beleg eines Fehlstarts.

**Harold Fannin Jr. (16,10 FLEX):** 9 Targets/7 Catches/91 Yards, 39 Routes laut Postgame-Usage und 87 % Offense-Snaps im internen Snap-Slice. Der vor dem Spiel angesprochene schwere Houston-TE-Defensivkontext war echt, doch das Watson-gestützte Receiving-Volumen trug. Der Erfolg beruhte nicht auf einem zufälligen Touchdown. **Gute ex-ante Risikoentscheidung mit bestätigter Opportunity-These.**

### Kicker

**Ka'imi Fairbairn (7,00):** Solider, aber kein außergewöhnlicher Ertrag. Kein belegter, damals tatsächlicher Free-Agent-Kicker einschließlich Drop-/Roster-Kosten mit materiellem Zusatznutzen; daher **kein nachgewiesener Streaming-Prozessfehler**. Die vollständige historische Kicker-Marktalternative bleibt nicht auditiert.

## 4. Kern-Grenzentscheidung Fannin / Bernard / Meyers

| Kandidat | Pregame-Signal (15.11.-Capture) | Tatsächlich | Same-Information-Urteil |
|---|---|---|---|
| **Fannin – START** | Watson-abhängige 9/12-Target-Spiele; Houston-Defense stark gegen TE; FantasyPros Derek Brown skeptisch, Johnson und Stoned Lack positiv unter Role-Annahme; Athlon FLEX49. | **16,10**; 9 Targets, 7 Catches, 91 Yards | **Gut begründet.** Die zuvor formulierte Receiving-Opportunity bestätigte sich. |
| **Bernard – START** | Hohe vorangegangene Snap-Anteile (94/91/85 %), Target Shares 30/27/18/23 %, gutes CIN-Slot-/YAC-Matchup; aber kurze aDOT, Target-Floor-Kritik, Stoned-Lack-Abwertung, Athlon FLEX73. | **1,00**; 95 % Snaps, 33 Routes laut RotoWire, **3 Targets/0 Catches**, 1 Rush für 10 Yards | **Kritisch.** Tatsächliche Beteiligung blieb hoch, aber Pass-Opportunity brach ein; Snap-Floor war kein sicherer Target-Floor. |
| **Jakobi Meyers – BENCH** | Athlon FLEX55 (**18 Plätze vor Bernard**), FantasyPros FLEX-tauglich, gutes TEN-Perimeter-Matchup; hingegen JAX-Run-Game-Script und zuvor wechselnde Snaps. | **6,40**; 6 Targets/3 Catches/34 Yards; 81 % Snaps (W9: 68 %) | **Ernsthafte Same-Information-Gegenoption.** Der Vergleich durfte vor dem 19-Uhr-Lock entschieden werden. |

**Direkter ex-post Tausch:** Meyers statt Bernard ergäbe **+5,40** Punkte bzw. **226,48** statt 221,08; der Sieg gegen Jan wäre unverändert geblieben. **Nicht** als zwingender Beweis behandeln, dass Meyers vorher eindeutig starten musste.

**Entscheidungsurteil:** Leicht plausibler **Decision Regret** zugunsten Meyers, aber niedrige bis mittlere Sicherheit: Die externe Pregame-Evidenz favorisierte ihn teilweise klar, während Bernards jüngster echter Target-Trend und das Cincinnati-Profil eine seriöse Gegenposition waren. Der eigentliche Verbesserungsansatz ist, **Snaps, Routes, Targets pro Route, Team-Passvolumen und Game-Script-Downside** in gemeinsamen FLEX-Grenzfällen konsequent auseinanderzuhalten. Ein Sit ausschließlich wegen späterer 1,00 Punkte wäre Outcome-Hindsight.

**Portfolio:** Chase Brown/McMillan/Fannin/Bernard hatten unterschiedliche Receiving-Risiken; ein garantierter Floor aus vier gleichzeitig startenden Passfangprofilen wäre falsch gewesen. Fannin war kein imaginärer dritter TE-Pflichtslot, sondern legitimer FLEX.

## 5. Übriger 24er-Kader: aktive Bank, Reserve und Taxi

Alle unten aufgeführten Spieler gehören zum kontrollierten Week-10-Player-Pool. Die Bereichszuordnung wird mit dem Ex-ante-Capture abgeglichen; **Reserve und Taxi schließen theoretisches Best Ball nicht aus**, jedoch erfordern echte Starts rechtzeitige, regelkonforme Aktivierung. **0,00** bei Bye, Out oder IR ist keine negative Spielerbewertung.

| Bereich | Spieler | Week-10-Punkte | Offense-Snaps* | Management-Einordnung |
|---|---|---:|---:|---|
| Aktive Bank | Michael Penix Jr. | 13,34 | 100 % | QB-Tiefe; keine überzeugende Alternative zu Mahomes. |
| Aktive Bank | Tyler Shough | 10,98 | 100 % | QB-Tiefe; kein klarer Ex-ante-Vorrang vor Mahomes. |
| Aktive Bank | D'Andre Swift | 0,00 | – | Bye; nicht startbar. |
| Aktive Bank | Dylan Sampson | 7,70 | 51 % | 51 % Offense-Snaps nach 64 % in W9; RB-Rotation. |
| Aktive Bank | Jeremiyah Love | 0,00 | – | IR; kein spielender Week-10-Kandidat. |
| Aktive Bank | Kenneth Walker III | 0,00 | – | Offiziell Out (Leiste); Hall-Pflichtwechsel. |
| Aktive Bank | Kyle Monangai | 0,00 | – | Bye; nicht startbar. |
| Aktive Bank | Saquon Barkley | 0,00 | – | Bye; Nullpunkte sind kein Leistungsurteil. |
| Aktive Bank | Seth McGowan | 13,70 | 29 % | 12 Carries/77 Rush-Yards/1 TD, aber 29 % Snaps; interessanter RB2-/Contingency-Pfad. |
| Aktive Bank | Brian Thomas Jr. | 5,90 | 48 % | 48 % Snaps nach 34 % in W9; weitere Rollenprüfung nötig. |
| Aktive Bank | Jakobi Meyers | 6,40 | 81 % | 6 Targets/3 Catches/34 Yards; engste Bernard-Alternative. |
| Aktive Bank | Jaylen Waddle | 0,00 | – | Kein belegter weiterer Week-10-Startpfad. |
| Aktive Bank | Ladd McConkey | 0,00 | – | Später offiziell Out; keine gesicherte Late-Swap-Absicherung. |
| Aktive Bank | Marvin Harrison Jr. | 0,00 | – | Offiziell Out. |
| Aktive Bank | Puka Nacua | 0,00 | – | IR; Pickens kam ins Lineup. |
| Aktive Bank | Travis Hunter | 3,90 | 8 % | Nur 8 % Offense-Snaps; Offensiveinsatz bleibt begrenzt. |
| Aktive Bank | Colston Loveland | 0,00 | – | Bye; nicht startbar. |
| Reserve | Alec Pierce | 0,00 | – | Reserve; kein Spielbeitrag. |
| Reserve | Davante Adams | 0,00 | – | Reserve; Injury/Availability vor weiterer Aktivierung prüfen. |
| Reserve | De'Zhaun Stribling | 0,00 | – | Reserve; Entwicklungsstash. |
| Reserve | Jaxson Dart | 0,00 | – | Reserve; nicht mit aktiver QB-Absicherung verwechseln. |
| Reserve | Jonathon Brooks | 0,00 | – | Reserve; kein Week-10-Einsatz. |
| Taxi | Antonio Williams | 12,20 | 86 % | Taxi; am Donnerstag 2 Catches/42 Yards/1 TD, hätte vor seinem Kickoff aktiviert werden müssen. |
| Taxi | Chris Bell | 0,00 | – | Taxi; kein Week-10-Score. |

**Wichtige Roster-Signale:**
- **Seth McGowan (13,70):** 12 Rushes/77 Yards/TD bei 29 % Snaps (W9: 31 %). Hoher Output bei noch beschränktem Anteil; der eigenständige RB2-/Contingency-Pfad ist für Dynasty interessant, nicht mit einer gesicherten Lead-Back-Rolle verwechseln. Der Pregame-Start statt Warren/Bernard war **nicht eindeutig besser begründbar**.
- **Dylan Sampson (7,70):** 51 % Snaps nach 64 %; Beteiligung vorhanden, aber kein belegter Sprung in die primäre Touch-Rolle. Kein klares ex-ante Argument, ihn allein wegen des etwas besseren Scores über Bernard zu stellen.
- **Jakobi Meyers (6,40):** Bei nur sechs Targets nicht der automatische zweistellige Floor, vor dem er teilweise beworben wurde. Trotzdem begründete Gegenoption zu Bernard; NFL-Rolle/Routes vor Week 11 revalidieren.
- **Brian Thomas Jr. (5,90):** Snaps 34 % → 48 %; eine leichte Nutzungsverbesserung, aber noch kein Beweis für frühere Premium-Rolle. **Travis Hunter (3,90 Liga-Wertung)** blieb mit 8 % Offense-Snaps kurzfristig kaum startbar, unabhängig von allgemeiner Dynasty-Fantasie.
- **Antonio Williams (12,20, Taxi):** 2 Receptions/42 Yards/TD am Donnerstag und 86 % Offense-Snaps. Sichtbarer Entwicklungs-/Nutzungsimpuls, aber der Taxi-Status hätte **vor seinem Thursday-Kickoff** mit aktivem Kaderplatz und potenziell echtem Cut-Opfer verändert werden müssen. Nicht als gratis oder nach Sonntag verfügbar darstellen. **Chris Bell** blieb Taxi-Stash ohne Week-10-Ertrag.
- **Ladd McConkey:** Der spätere tatsächliche Ausfall darf nicht als vor Sunday garantiert bekannt oder als sicherer Monday-Backup modelliert werden.
- **Bye/Out/IR/Reserve-Spieler:** Nicht aus einer Null im Score eine Cut-/Drop-Empfehlung ableiten; Coverage, Salary, Retention und künftige Opportunity sind eigenständige Betrachtungen.

## 6. Theoretisches Best Ball vs. Managementqualität

**Offizielle diagnostische Wochenkennzahlen** (`team-week-performance`):
- Gewertetes Lineup: **221,08**.
- **Best-Ball-Potential: 244,78** aus dem vollständigen kontrollierten 37er-Pool, inklusive des potenziell vor Thursday aktivierbaren Taxi-WR **Antonio Williams**.
- **Outcome-/Points-Regret: 23,70**; Effizienz **90,32 %**.

Das Best-Ball-Optimum (ex post, keine ex-ante Empfehlung) wäre:

| Slot im Best-Ball-Readmodel | Spieler | Ist-Punkte |
|---|---|---:|
| QB-1 | Patrick Mahomes | 35,42 |
| QB-2 | Jayden Daniels | 22,76 |
| RB-1 | Chase Brown | 28,30 |
| RB-2 | Cam Skattebo | 27,20 |
| WR-1 | George Pickens | 43,50 |
| WR-2 | Antonio Williams | 12,20 |
| TE-1 | Harold Fannin Jr. | 16,10 |
| TE-2 | Trey McBride | 8,70 |
| FLEX-1 | Breece Hall | 14,80 |
| FLEX-2 | Seth McGowan | 13,70 |
| FLEX-3 | Dylan Sampson | 7,70 |
| FLEX-4 | Malik Nabers | 7,40 |
| K-1 | Ka'imi Fairbairn | 7,00 |
| **Gesamt** | | **244,78** |

**Keine Korrektur auf 239,08 vornehmen.** Dieser niedrigere Wert wäre nur ein zusätzliches Szenario mit nachträglich **eingeschränktem Kandidatenpool** (z. B. ohne Taxi-Aktivierung). Er ersetzt nicht den kanonischen Best-Ball-Standard. Sleeper erlaubt nach der Taxi-Deadline eine **einseitige Aktivierung** aus Taxi, jedoch kein erneutes Zurückverschieben; Reserve/IR ist je nach aktueller Eligibility ebenfalls aktivierbar. Ein voller aktiver 30er-Kader kann dafür einen Drop oder andere legale Kapazitätsaktion erfordern. Das 244,78-Potential bildet den hypothetisch besten Wochenoutput ab, **nicht** den sicheren Nutzen nach verlorenem Dynasty-/Rosterwert.

**Zwei unterschiedliche Gegenfakten getrennt halten:**
1. **Williams-Option:** Vor Thursday potenziell möglich, aber nicht am Sonntag noch nachholbar; keine dokumentierte ursprüngliche Vor-Thursday-Entscheidung, keine beweisbare damalige Weitsicht und kein nachgewiesener optimaler Cut.
2. **Sonntag-Grenzentscheidungen:** Fannin/Meyers/Bernard/Warren sowie McGowan/Sampson konnten innerhalb ihrer echten Kickoff-/Slotgrenzen verglichen werden, jedoch **ohne** Ergebnisse aus der Zukunft. Dass McGowan nachträglich Warren übertraf, begründet nicht automatisch einen fehlerhaften damaligen TE2-Start.

Eine vollständige sequenzielle Optimierung mit **konkreten** frühen Cuts, unvollständig archivierten AutoSub-Einstellungen, Minutensperren und dem Dynasty-Preis der aktivierten Spieler ist nicht belegt und wird nicht als Teil dieses theoretischen Maximums ausgegeben.

## 7. Prozessbewertung (nicht aus Endergebnis allein)

| Entscheidung | Prozessurteil | Begründung / Grenze |
|---|---|---|
| **Mahomes statt Penix/Shough** | **Gut gestützt** | Starterrolle und zeitgenössische externe QB-Evidenz, nicht bloß stärkere spätere Punkte. |
| **Hall für Walker** | **Korrekte Pflichtanpassung** | Walker offiziell Out; Hall als verfügbarer RB-Ersatz, Rollensplit nicht zu 100 % garantiert. |
| **Pickens für Puka** | **Gut gestützt** | Puka IR; Pickens freigegeben, bei weiterhin erwähnter Hamstring-Restunsicherheit. |
| **Warren TE2** | **Ex ante vertretbar** | Günstiges Pregame-TE-Matchup/positive externe Einschätzungen; tatsächliches Target-Volumen enttäuschte. |
| **Fannin FLEX** | **Gut trotz Risiko** | Der stark konträre Houston-Matchup-Befund wurde offen diskutiert; die Target-These war seriös. |
| **Bernard vor Meyers** | **Leicht kritischer Decision-Grenzfall** | Meyers hatte bereits zeitgenössische externe Argumente; Gegenargumente zu Bernard wurden vielleicht zu gering gewichtet. Keine eindeutige Fehlentscheidung. |
| **McGowan/Sampson Bank** | **Kein nachgewiesener Prozessfehler** | Unklare Rolle/kleiner bzw. wechselnder Anteil zum Lock; hohe beobachtete McGowan-Effizienz erst postgame sicher. |
| **Fairbairn halten, kein Waiver** | **Nicht widerlegt; Markt-Audit offen** | Keine belegte materielle Verbesserung bei Einbezug realer Drop-Kosten und Eligibility. |
| **Williams Taxi lassen** | **Nicht nachträglich als bewiesener Fehler einstufen** | Theoretisch vorher aktivierbar, aber kein zeitgenössischer Thursday-Entscheidungsrecord und echte Cut-/Slot-Opportunitätskosten. |

**Gesamtbewertung:** Gute, nicht perfekte Fantasy-Management-Woche. Der Sieg ist real; die klaren Verletzungsersatz-Entscheidungen und Fannins FLEX-Risikowahl waren gut begründet. Der aussagekräftigste mögliche Verbesserungsbereich ist der **Bernard/Meyers-Target-Floor-Stresstest** – nicht die bloße Ex-post-Suche nach dem punktbesten Bench-Spieler.

## 8. Nächste fachliche Rechecks (keine automatischen Aktionen)

1. **Bernard vs. Meyers und vollständige FLEX-Grenze vor Week 11 neu aufbauen:** frisches Team-Passvolumen, Targets/Route, konkurrierende Empfänger, Snap-/Route-Trend, Verletzungen und unabhängige Pregame-Rankings heranziehen. Ein einzelnes schlechtes Bernard-Spiel erzeugt keinen automatischen Dynasty-Cut.
2. **Pickens und Fannin:** hohe beobachtete Targets/Routes und volle Gesundheit bei nächstem Injury-Report bestätigen; den außergewöhnlichen Pickens-Drei-TD-Tag nicht fortschreiben.
3. **Warren/McBride/McMillan:** Opportunity-Entwicklung statt reinen Boxscore prüfen; besonders Warrens wenige Targets trotz hoher Snaps und McMillans niedrige Reception-Conversion.
4. **McGowan/Sampson:** eigenständige Touch-Rolle, Konkurrenz- und Dynasty-Upside beobachten; McGowan nicht von 29 % Snaps zum sicheren Lead-Back hochrechnen.
5. **Antonio Williams:** Taxi-Promotion bleibt eine *reale künftige Option* mit Zeit- und Cut-Preis. Vor einem Move den verdrängten aktiven Spieler, irreversible Taxi-Rückkehr und mittelfristige Retention explizit beurteilen.
6. **Daten-/Nachweisgrenzen:** Snap-Finality und die einzelne Hunter-Scoring-Ist-Divergenz getrennt prüfen; keine daraus erfundenen Spielerpunkte oder automatisch veränderten Ligaergebnisse.

**Scope-Abschluss:** Diese Retrospektive verwendet externe Pregame- und Postgame-Evidenz, trennt Decision von Outcome und enthält den vollständigen 37er-Pool. Sie führt **keine** Prognoseintervall-, Projection-Modell- oder Modellverbesserungsdiskussion und verändert keine entsprechenden Artefakte. Die [historische Ex-ante-Datei](2026-week-10-lineup-ex-ante-decisions.md) bleibt unverändert.
