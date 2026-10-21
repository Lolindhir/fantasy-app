# Mighty Giants — Week 6 2026 Roster + Lineup Postmortem (chronologisch korrigiert)

**Rekonstruktion:** 21.10.2026 (nach Scoring-Finality und Nutzerkorrektur zur tatsächlichen Zeitachse)  
**Team:** Robert / Mighty Giants (TeamID 1)  
**Gegner:** Tim / TimpaBay (TeamID 6)  
**Ergebnis:** **169,28 : 139,28**, Sieg mit **30,00 Punkten** Vorsprung  
**Dokumenttyp:** abgeschlossene retrospektive Analyse, **kein** versiegelter Decision Record und keine Änderung historischer Start/Sit-Entscheidungen  
**Persistierungsfreigabe:** 21.10.2026, inklusive expliziter methodischer Regelergänzung

> **Zentraler Korrekturpunkt gegenüber der ersten Chat-Fassung:** Der direkte Ex-post-Vergleich Waddle ↔ Germie Bernard darf **nicht** als Donnerstag-Decision-Regret gewertet werden. Waddle spielte am Donnerstag (NFL-Ortsdatum 15.10.), während Bernard erst am Sonntag per Waiver zu den Mighty Giants kam. Die Donnerstagentscheidung war ein bewusster, zeitkritischer FLEX-/Injury-Absicherungspfad im Umfeld von Barkley und Jeremiyah Love. Gleichzeitig sind die eigenen experimentellen Modellprojektionen keine verlässliche Ex-ante-Entscheidungsautorität. Externe Pregame-Einschätzungen werden gesondert rekonstruiert.

## 0. Quellen, Rekonstruktionsgrad und Outcome-Firewall

**Periodenstabile Matchup-Fakten:**
1. \`data-source/leagues/nfl-reise/seasons/2026/matchups/week-6.json\`: historische 37 Mighty-Giants-Spieler, finale 13 gewertete Starter und 169,28 Punkte (CanonicalLeagueRosterID \`clr-a8e576139994570d82e9ea2ed3f42b1b\`).
2. \`public/data/Matchups.json\`: Week 6 \`CompletionState = final\`; sämtliche drei Liga-Matchups.
3. \`public/data/League.json\`: Saison 2026, \`CurrentWeek = 7\`, \`FinalScoredWeek = 6\`, 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K.
4. \`data-source/leagues/nfl-reise/seasons/2026/transactions/week-6.json\` und \`week-7.json\`: datierte Waiver-Zugänge und Abgänge; Week-7-Zugänge sind aus allen Week-6-Entscheidungsvergleichen ausgeschlossen.
5. Roster-/Reserve-/Taxi-Rekonstruktion aus dem historischen Spielerpool, Week-6-/Week-7-Transaktionen und der vor den Week-7-Waivern gesicherten App-Snapshot-Datei \`public/data/backup/League_20261020_204147.json\`. Kein formal eingefrorener periodenstabiler Taxi-Status pro Spieler im Matchup-Record.

**Nachträgliche Diagnose, nicht Pregame-Wahrheit:**
6. \`data-derived/player-week-fantasy/nfl-reise/2026/06.json\`: finale Fantasy-Istpunkte und eigene V4-C-Week-Projektionen, \`ActualScoringEvidenceFinalized = true\`, \`TargetWeeklyRosterFinalized = false\`.
7. \`data-source/nfl/snap-counts/2026/05.json\` und \`06.json\`: Nutzungsvergleich; Week 6 \`Finalized = false\`. Snap-Fakten einzelner vorhandener Spiele nicht als vollständige finale Abdeckung ausgeben.
8. Benutzerpräzisierung am 21.10. und zeitgenössische Chat-Entscheidung vom 15.10.: Waddle vs. Fannin; bewusste Absicherung wegen unklarer Barkley-/Love-Verfügbarkeit. Sonntag 18.10. weitere Start-/AutoSub-/Waiver-Diskussion zu Warren, Fannin, Bernard sowie Mahomes/Daniels vs. Shough/Penix. Chat-Erinnerung/Entscheidungskontext ist nicht mit einem technisch versiegelten vollständigen Start-Snapshot gleichzusetzen.

**Externe Pregame-Evidenz** mit Datumsangabe wird in Abschnitt 6 separat aufgeführt. Eine Website-Rangliste, die nach Veröffentlichung aktualisiert wurde, ist **keine** revisionssichere Momentaufnahme. Fehlende exakte Änderungszeitpunkte/ursprüngliche Rankings werden nicht erfunden.

**Outcome-Firewall:** Spätere Punkte, Snap Shares, Ausfälle und Ranglistenrevisionen dürfen die damals verfügbaren Alternativen nicht verändern. „Hindsight-/Best-Ball-Punkte“ und „begründbarer Decision Regret“ sind unterschiedliche Kategorien.

## 1. Ergebnis und Ligaentwicklung

| Week-6-Matchup | Final |
| --- | ---: |
| **Robert – Tim** | **169,28 : 139,28** |
| Marcel – Dennis | 176,64 : 174,10 |
| Flo – Jan | 181,34 : 179,00 |

Robert gewinnt zum dritten Mal in Folge und steht **4–2** auf **Platz 3**, mit **1.190,24 Points For** und **1.079,10 Points Against** (**+111,14**). Flo führt mit 5–1 und 1.258,82 Punkten, Tim steht bei 4–2 und 1.226,42, Marcel bei 4–2 und 1.165,54.

Wochenscores Robert Weeks 1–6: **205,36 / 188,02 / 173,64 / 221,84 / 232,10 / 169,28**. Durchschnitt **198,37**. Gegenüber Week 5 sinkt der Score um **62,82**, rund **27,1 %**. Mit **169,28** erzielt Robert den **fünfthöchsten** Week-6-Score der Liga; gegen jeden der anderen vier möglichen Gegner hätte dieser Score nicht gereicht. Der sportliche Sieg ist real, aber der Wochenscore bestätigt keinen stabilen 220-Punkte-Floor.

## 2. Tatsächlich gewertete Starter und retrospektiver Modellvergleich

| Slot | Starter | Ist Week 6 | Eigenes Modell V4-C |
| --- | --- | ---: | ---: |
| QB | Patrick Mahomes | 11,48 | 21,22 |
| QB | Jayden Daniels | 21,00 | 20,65 |
| RB | Cam Skattebo | 0,00 | 11,65 |
| RB | Kenneth Walker III | 27,90 | 24,75 |
| WR | Jaylen Waddle | 6,40 | 9,85 |
| WR | Malik Nabers | 28,50 | 14,74 |
| TE | Trey McBride | 12,30 | 18,08 |
| TE | Harold Fannin Jr. | 1,90 | 10,91 |
| FLEX | George Pickens | 13,30 | 14,07 |
| FLEX | Tetairoa McMillan | 14,60 | 16,82 |
| FLEX | Davante Adams | 6,90 | 18,55 |
| FLEX | Puka Nacua | 14,00 | 24,60 |
| K | Ka'imi Fairbairn | 11,00 | 10,81 |
| **Gesamt** | | **169,28** | **216,71** |

Die finalen Starter summieren sich exakt auf **169,28**. Die eigene archivierte Projektion für dieselben 13 Spieler ergibt **216,7059** (**216,71**), also einen Ist-Abstand von **−47,43**. **Das ist ein Kalibrierungs- und Diagnosebefund, kein Beweis für 47,43 vermeidbare Coaching-Punkte**: Das Modell ist noch in Entwicklung, es ist nicht alleinige Pregame-Autorität und seine archivierte Version garantiert keinen identischen Informationsstand zum Lock.

Startende Positionsgruppen: QB **32,48**, RB **27,90**, WR/FLEX-WR **83,70**, TE **14,20**, K **11,00**. Malik Nabers (28,50) und Kenneth Walker III (27,90) liefern zusammen **56,40**, also ein Drittel des Wochenoutputs.

## 3. Historischer Spielerpool: Bank, Taxi, Reserve

**Positive tatsächlich nicht gewertete Punkte im historischen Pool:**

| Spieler | Position | Ist Week 6 | V4-C | Zulässige normale Bankalternative? |
| --- | --- | ---: | ---: | --- |
| Tyler Shough | QB | 26,96 | 17,91 | Ja |
| Germie Bernard | WR | 25,70 | 6,96 | Ja, **erst nach Sunday-Waiver** |
| Michael Penix Jr. | QB | 23,10 | 13,97 | Ja |
| Colston Loveland | TE | 18,50 | 6,08 | Ja |
| Jakobi Meyers | WR | 13,30 | 10,16 | Ja |
| Antonio Williams | WR | 8,00 | 7,40 | **Nein: Taxi** |
| Marvin Harrison Jr. | WR | 6,40 | 6,59 | Ja |
| Dontayvion Wicks | WR | 4,40 | 9,76 | Ja, in Week 6 noch gehalten |
| Malachi Fields | WR | 3,90 | 6,58 | Ja |
| Ladd McConkey | WR | 2,70 | 9,76 | Ja |

**Taxi Week 6:** Antonio Williams und Chris Bell (0,00). **Reserve:** Jaxson Dart, Jonathon Brooks, Dylan Sampson, Ricky Pearsall und De'Zhaun Stribling. Alle dürfen ohne dokumentierte zeitgerechte Aktivierung **nicht** in ein reguläres Wochen-Best-Ball aufgenommen werden.

Zusätzlich im historischen Spielerpool mit 0,00 Punkten u. a.: Breece Hall, Saquon Barkley, Jeremiyah Love, Chase Brown, Kyle Monangai, Tyler Warren und Adonai Mitchell. Null Punkte allein belegen **keine** vorherige Spielbereitschaft; Bye-/Inactive-/Injury-/Rollenstatus getrennt prüfen.

**Zeitachse der Änderungen:** Bernard kam Sonntag 18.10. über einen **erfolgreichen** Week-6-Waiver, gleichzeitig wurde Caleb Douglas (Sleeper 13296) abgegeben; der eigene parallele Claim auf einen anderen Spieler scheiterte. Brian Thomas Jr. (für Wicks) und Tre Tucker (für Pearsall) kamen **erst durch Week-7-Transaktionen am 20./21.10.** und sind keine historischen Week-6-Optionen.

## 4. Decision-Opportunity-Matrix: Donnerstag, Sonntag und spätere Locks

| Phase | Belegter Entscheidungsraum | Bedeutung für das Postmortem |
| --- | --- | --- |
| **Donnerstag 15.10., vor DEN–SEA** | Waddle als frühe FLEX-Option; damals diskutierte Alternative insbesondere **Harold Fannin Jr.**; Barkley/Love nicht sicher verfügbar. Im damaligen Chat wurde Sleeper Waddle ca. 11,34 und Fannin ca. 10,91 gegenübergestellt. | Robert entschied **bewusst für Waddle**, um bei möglichen Ausfällen beider RB spätere Pflicht- und FLEX-Plätze abzusichern. Der Plan muss als Risiko-/Portfolioentscheidung und nicht als rückblickende reine Punktwette bewertet werden. |
| **Thursday Night / Lock** | Waddle spielt gegen Seattle, liefert 6,40 und ist anschließend gesperrt. | Kein späterer Sonntagsspieler kann rückwirkend gegen Waddle eingewechselt werden. Insbesondere **Bernard vs. Waddle war nie eine reale Entscheidung**. |
| **Sonntag 18.10., vor Waiver und Spielen** | Barkley und Love fehlen; Warren unsicher; Mahomes/Daniels als QB-Starter; Shough/Penix als Alternativen; Skattebo als RB2. Bernard ist zunächst Free Agent. | RB-Pflichtslot-Verfügbarkeit und TE-Backup sind die zentralen Lock-Checks. Späte Rollennachrichten dürfen nur auf Slots wirken, die noch legal umstellbar sind. |
| **Sonntag 18.10., Waiver ca. 12 Uhr Berlin** | Erfolgreicher Bernard-Claim (CreatedAt 09:57:17 UTC = 11:57 CEST). Er wird erst jetzt held/aktiv; seine bereits vorhandene Steelers-Opportunity war relevant, aber nicht rückwirkend für Waddle. | **Bernard vs. zu diesem Zeitpunkt noch ungesperrte WR/FLEX** ist eine eigenständige potenzielle Sonntagsentscheidung; die konkrete originale Slot-/Lock-Verteilung ist nicht vollständig archiviert. |
| **Sonntag, Pregame Inactives / Kickoffs** | Tyler Warren fällt mit Leistenverletzung aus. Ursprünglicher Chat-Plan: Warren starten und **Fannin als AutoSub-Absicherung**; final gewertet wird Fannin. | Bewusster Injury-Backup-Pfad ist belegt, **exakter AutoSub-Mechanismus und konkrete technische Ausführung nicht**. Darum kein frei erfundener manueller Swap oder pauschaler „vergessener Warren“-Fehler. |
| **Nach Week 6** | Finale Punkte, Snaps, neue Injury- und Depth-Chart-Informationen. | Nur für Outcome, Modellkalibrierung und Week-7-Rechecks; nicht als rückwirkend bereits bekannte Grundlage. |

**Wesentliche Nutzerpräzisierung:** Die Waddle-Auswahl entstand nicht aus einem simplen „Waddle > Bernard“ oder aus blindem Vertrauen ins eigene Modell. Sie priorisierte eine verlässlich früh spielende Option gegenüber späteren Unsicherheiten um Barkley/Love und der Fannin-Alternative. Die beiden RB-Ausfälle traten tatsächlich ein. Dieses Risikomotiv bleibt auch bei nur 6,40 realisierten Waddle-Punkten legitim.

## 5. Legales Hindsight-Best-Ball — ausschließlich Ex-post-Diagnose

| Slot | Optimum | Punkte |
| --- | --- | ---: |
| QB | Tyler Shough | 26,96 |
| QB | Michael Penix Jr. | 23,10 |
| RB | Kenneth Walker III | 27,90 |
| RB | Cam Skattebo* | 0,00 |
| WR | Malik Nabers | 28,50 |
| WR | Germie Bernard | 25,70 |
| TE | Colston Loveland | 18,50 |
| TE | Trey McBride | 12,30 |
| FLEX | Tetairoa McMillan | 14,60 |
| FLEX | Puka Nacua | 14,00 |
| FLEX | George Pickens | 13,30 |
| FLEX | Jakobi Meyers | 13,30 |
| K | Ka'imi Fairbairn | 11,00 |
| **Maximaler historischer Score** | | **229,16** |

*Skattebo ist nur einer von mehreren mit 0,00 bewerteten legalen RB2-Kandidaten; kein anderer aktiver RB außer Walker erzielt positive Punkte.*

- **Realisiert: 169,28**
- **Best-Ball-Gap: 59,88**
- **Hindsight-Effizienz: 73,9 %**
- Austauschrechnung rein ex post: Shough für Mahomes **+15,48**; Penix für Daniels **+2,10**; Loveland für Fannin **+16,60**; Bernard für Waddle **+19,30**; Meyers für Adams **+6,40**.

**Explizite Warnung:** Der +19,30-Austausch Bernard/Waddle ist rechnerisch gültig im **nach vollständiger Week-6-Rostergestaltung erlaubten Ergebnis-Best-Ball**, aber **keine** im Thursday-Entscheidungsfenster mögliche Aktion. Ebenso sind andere einzelne Hindsight-Tausche nicht automatisch ex ante besser. Nicht 59,88 Punkte „Coaching-Fehler“ melden.

## 6. Externe Pregame-Einschätzungen: QB und TE, getrennt vom eigenen Modell

Externe Quellen sind in diesem Review die primäre **Plausibilitäts- und Marktfolie für die damalige Entscheidung**, keine unfehlbare Wahrheit. Alle allgemeinen Rankings müssen auf das konkrete 2-QB-/2-TE-/4-FLEX-Format und echte Locks übertragen werden.

### 6.1 QB-Pregame

**Sports Illustrated, Michael Fabiano, Week 6 QB Rankings**, ursprünglich 13.10.2026 veröffentlicht, **zuletzt 17.10. geändert** (vor Sonntag, aber kein archivierter Thu-/Fr-Snapshot): **Mahomes QB4**, **Daniels QB7**, **Shough QB12**, **Penix QB19**. Quelle: https://www.si.com/fantasy/week-6-quarterback-rankings

**UPI, 15.10.2026**, ebenfalls vor Sonntag: **Mahomes QB11**, **Daniels QB17**, **Penix QB19**; die verfügbare Ergebnisdarstellung erlaubt keine sicher datierte Shough-Platzierung, daher keine ergänzt. Quelle: https://www.upi.com/Sports_News/NFL/2026/10/15/fantasy-football-quarterback-rankings-Week6/4991792070413

**Pro Football Network, 12.10.2026:** frühe Week-6-Einordnung Mahomes vor Daniels/Shough, aber die Quelle ist eine vorläufige frühe Wochenrangliste; nicht als finale Injury-bereinigte Sunday-Rangliste lesen. Quelle: https://www.profootballnetwork.com/fantasy-football/early-qb-rankings-week-6-2026-katz/

**Ex-ante-Befund:** Trotz unterschiedlicher Ranghöhe stützten unabhängige vor dem Sonntag verfügbare Expertenbewertungen die Wahl **Mahomes + Daniels**. Der interne Modellvorsprung war daher **nicht allein** ausschlaggebend und ist auch nicht erforderlich, um den Prozess als gut begründet zu bewerten. Nachträglich hatten Shough (26,96) und Penix (23,10) höhere Ergebnisse. **Outcome Regret, kein nachgewiesener QB-Decision-Regret.** Bei Shough ist die besonders starke Reaktion auf den Week-5-Flop kritisch; zugleich war er in der genannten SI-Rangliste zumindest QB12 und damit echte QB2-Kontextoption in einer 2-QB-Liga.

### 6.2 TE-Pregame

**FantasyPros, Pat Fitzmaurice, PPR Week-6-Ranking vom 15.10.2026** (vor Sonntag): **McBride TE2**, **Warren TE5**, **Fannin TE8**, **Loveland TE10**; veröffentlichte damalige ECR-Referenzen Fannin 10, Loveland 14. Quelle: https://www.fantasypros.com/nfl/rankings/pat-fitzmaurice.php?position=TE&scoring=PPR&week=6

**Sports Illustrated, Michael Fabiano:** Week-6-TE-Rangliste, erstmals 13.10., **zuletzt am 18.10. geändert** (exakter Revision-Zeitpunkt zum Sunday Lock offen): McBride 1, Warren 4, Fannin 10, Loveland 12 im recherchierten Stand. Wegen der möglichen späteren Update-Information **nicht** als revisionssicheren Ursprungsstand behandeln. Quelle: https://www.si.com/fantasy/week-6-tight-end-rankings

**NBC-Rangliste:** Ein Suchindex meldet für einen 18.10. aktualisierten Stand Loveland 10, Fannin 11 nach dem Entfernen Warrens. Da dieser Stand bereits Sunday-Inactive-Verarbeitung enthält, ist er **nicht** als vor dem ursprünglichen Waddle-Donnerstagsentscheid unverändert vorhanden anzunehmen. Außerdem ergab sich beim direkten Öffnen einer NBC-QB-URL ein historisch abweichender Seiteninhalt (2023), daher **keine Abstützung zentraler Schlussfolgerungen auf NBC-URLs aus gemischten Indizes**.

**Ex-ante-Befund:** Warren war als gesunder TE klar oben, Fannin lag nach einer zeitgenössischen konkreten FantasyPros-Experteneinschätzung **knapp vor Loveland**. Loveland wurde dennoch teils bereits relativ positiv gesehen, unter anderem wegen der erwarteten Rückkehr Caleb Williams'. Nach Warren-Out blieben zwei echte startbare TE-Alternativen. Fannin als Absicherung hatte einen fachlich vertretbaren Pregame-Fall; Loveland erzielte tatsächlich **+16,60** mehr. Dies ist **überwiegend Outcome Regret** mit einer sinnvollen gesonderten Kalibrierungsfrage zur Offense-/QB-Rückkehr und zu Opportunity-Signalen; ohne revisionsfesten Sunday-Snapshot und vollständige damalige Targets/Routes kein Beweis für einen eindeutigen Loveland-Start.

### 6.3 Waddle-Pregame

FantasyPros Derek Brown, **15.10.2026 13:35 EDT** (19:35 CEST), bewertete Waddle trotz Payton/Webb-Playcalling-Wechsel als mittelmäßige FLEX-Option wegen des schwachen QB-Spiels und des Seattle-Matchups. **Diese Bewertung ist zwar vor dem Thursday-Kickoff, liegt aber nach der dokumentierten Nutzerentscheidung am Donnerstagmittag/-nachmittag und darf nicht still als für diese frühe Entscheidung bereits gelesen gelten.** Quelle: https://www.fantasypros.com/nfl/notes/466329/jaylen-waddle-2026-week-6-outlook.php

Für die **reale Donnerstagabwägung** sind absichernde FLEX-Punkte, Barkley/Love-Ausfallrisiko, spätere Lock-Flexibilität und Fannin als besprochene Alternative entscheidend. Schlechte spätere Waddle-Punkte oder der Sonntagserfolg Bernards erlauben keine rückwirkende automatische Abwertung.

## 7. Spieler- und Positionsreview mit Same-Information-Re-Decision

### 7.1 QB: Mahomes/Daniels vs. Shough/Penix

Ergebnis: Mahomes **11,48**, Daniels **21,00**, Shough **26,96**, Penix **23,10**. Das Modell bevorzugte Mahomes/Daniels; wichtiger: die verfügbare externe Expertenlandschaft bevorzugte überwiegend ebenfalls beide. **Same-information:** voraussichtlich erneut Mahomes/Daniels starten; Week-5-Recency-Bias gegen Shough vermeiden und seine damalige QB12-Sichtbarkeit beachten. **Urteil:** Outcome Regret, kein bewiesener Prozessfehler.

### 7.2 RB: erkannte Verletzungslage und dennoch ungesicherter RB2-Floor

Walker **27,90** bei 45 Snaps / 74 %. Skattebo **0,00** bei nur **6 / 8 %** (Week 5 **56 / 63 %**). Chase Brown: Bye. Barkley (Hamstring), Love (Ankle), Breece Hall und Kyle Monangai waren in Week 6 nicht startfähig. Waddles frühzeitiger FLEX-Start war bereits **eine bewusste Reaktion** auf Barkley/Love-Unsicherheit.

Am **Sonntag vor Kickoff** wurde zusätzlich berichtet, dass Najee Harris statt Skattebo starten sollte; die Rolle Skattebos sei nach Fumbles reduziert. Dieser Vorgang war Pregame-Rolleninformation, **das Ausmaß bis auf null Touches** war erst später bekannt. Quelle Pregame (18.10. um 13:22 UTC): https://www.nbcsports.com/fantasy/football/player-news/2026-10-18/fowler-najee-harris-is-set-to-start-in-week-6 ; nachträgliche Ergebnis-/Erklärungssicht: https://www.nfl.com/news/why-didn-t-giants-rb-cam-skattebo-tally-a-carry-vs-saints-i-got-punished-for-what-i-did

**Same-information:** Walker starten; Skattebo nach Pregame-Demotion klar abwerten, aber im tatsächlich gehaltenen spielberechtigten RB-Pool erzielte kein anderer RB positive Week-6-Punkte. Ein möglicher früher RB-Waiver wäre als **Roster-/Coverage-Entscheidung** nur mit wirklich damaliger FA-Availability, Dropkosten und Zeitpunkt zu bewerten; diese Evidenz wurde nicht vollständig rekonstruiert. **Urteil:** Risiko wurde teilweise antizipiert; materieller RB-Coverage-Recheck, kein bewiesener falscher interner RB2-Punktetausch.

### 7.3 TE: Warren-Out, Fannin und Loveland

Warren fiel nach einer Leistenverletzung als Game-Day-Inactive aus. Warren war zuvor als einer der stärksten verfügbaren TE angesehen worden. Contemporaneous Plan: **Warren starten, Fannin als AutoSub**; historisch wurde **Fannin mit 1,90** gewertet. Vollständige originale AutoSub-Paarungs-/Ausführungsevidenz liegt nicht vor. Quelle Inactive: https://www.stampedeblue.com/indianapolis-colts-news/128860/colts-tight-end-tyler-warren-announced-among-inactives-against-titans-for-week-6

Fannin: **1,90**, **56 Snaps / 89 %**, aber wenig Passing-Output. Loveland: **18,50**, **68 / 88 %**; McBride: **12,30**, **70 / 97 %**. Pregame-Rankings gaben Fannin einen knappen Vorsprung vor Loveland. **Same-information:** Fannin war ein vertretbarer Absicherungspfad; besondere Verbesserungschance bei QB-/Passing-Game-Kontext (Caleb Williams' Rückkehr), nicht durch blindes Nachsetzen der 18,50. **Urteil:** Outcome Regret mit relevantem Quellen-/Opportunity-Recheck, kein sicherer Decision Regret.

### 7.4 WR/FLEX: Waddle ist kein Bernard-Fehler; Bernard vs. späte Flexoptionen separat

Waddle **6,40**, **39 Snaps / 65 %**, nach Week 5 ebenfalls **65 %**. Seine erhoffte positive Playcalling-Rollenentwicklung hat sich anhand der reinen Feldpräsenz noch nicht sichtbar bestätigt. Die Donnerstagentscheidung war jedoch eine **bewusste Injury-Portfolio-Absicherung**, keine Entscheidung gegen Bernard. **Same-information Donnerstag:** Waddle bleibt eine legitime, knappe Wahl gegen Fannin, sofern das Barkley/Love-Ausfallrisiko und die Flex-Absicherungspriorität so eingeschätzt werden wie damals. **Kein nachgewiesener Waddle-Decision-Regret.**

Bernard **25,70**, **74 Snaps / 94 %** gegenüber bereits **55 / 92 %** und 14,40 Punkten in Week 5. Er hatte einen belegten Sunday-Startcase dank großer aktueller Steelers-Rolle und personeller Ausfälle, aber erst nach dem eigenen Waiver-Zugang. **Same-information Sonntag:** Bernard hätte gegen **noch nicht gelockte** Starter/FLEX (z. B. Adams/Pickens/McMillan abhängig vom konkreten Kickoff-/Slot-Status) erneut direkt geprüft werden sollen. Ohne vollständige ursprüngliche Sunday-Entscheidungsnotizen kann aus dieser plausiblen Review-Lücke noch kein sicherer Fehler von +19,30 abgeleitet werden. **Potenzielle Sunday-Opportunity-Review-Lücke**, getrennt vom Thursday-Waddle-Start.

Davante Adams **6,90**, **43 / 74 %**; Puka Nacua **14,00**, **52 / 90 %**. Beide hatten vorab etablierte Rollen und gute externe Reputation; schwächere Istpunkte allein rechtfertigen keinen rückwirkenden Sit. Meyers **13,30** auf der Bank, ein Hindsight-Gap von **+6,40** zu Adams, ohne erwiesene bessere frühere Wahl. Nabers **28,50** mit **86 % Snaps** bestätigt seine stabile Core-Startrolle; Pickens **13,30 / 88 %**, McMillan **14,60 / 76 %** bleiben grundsätzlich begründete Starts.

### 7.5 Kicker

Fairbairn **11,00** gegen eigenes Modell **10,81**. Solider Start; kein durch Week 6 ausgelöster automatischer Streaming-Bedarf.

## 8. Decision-Regret-Klassifikation — revidiert

| Entscheidungsfall | Ex-post-Gap | Tatsächlich zeitkonforme Bewertung |
| --- | ---: | --- |
| Mahomes → Shough | +15,48 | **Outcome Regret**; externe Sunday-Pregame-Rankings stützen den ursprünglichen Mahomes-Start |
| Daniels → Penix | +2,10 | **Outcome Regret**, keine bewiesene bessere Pregame-Alternative |
| Fannin → Loveland | +16,60 | **Eher Outcome Regret**, mit Pflicht-Recheck QB-Rückkehr / TE-Opportunity; Warren-Absicherung bewusst angelegt |
| Waddle → Bernard | +19,30 | **Kein realer Thursday-Vergleich, deshalb kein Waddle-Decision-Regret.** Nur mathematisches Full-Week-Best-Ball |
| Bernard ↔ Sunday noch freie FLEX-Spieler | situationsabhängig | **Potenzieller Review-Gap**, konkrete damalige Slots/Locks und Pregame-Rankings nicht voll dokumentiert |
| Adams → Meyers | +6,40 | **Eher Outcome Regret**, interne/reale Rolle nicht ex ante widerlegt |
| Skattebo als RB2 | intern 0,00 Verbesserung | **Risk-/Coverage-Recheck:** Sonntag-Demotion relevant, aber keine gehaltene punktende RB-Alternative; hypothetischer Waiver unbewiesen |

**Gesamt-Prozessurteil:** gemischter, aber deutlich besser begründeter Entscheidungsprozess als eine reine 73,9-%-Best-Ball-Betrachtung nahelegt. Reale Risikoplanung (Waddle/Thursday, Warren/Fannin-Absicherung) wurde in der ersten Bewertung unterschätzt. Zu verbessern: Sunday-RB-Coverage, zeitnahe Behandlung von Skattebo-Rollennews, Nach-Add-Neubewertung der noch offenen Bernard-Slots, externer TE-QB-/Usage-Crosscheck.

## 9. Roster-/Dynasty-Interpretation und Week-7-Rechecks

1. **RB-Pflichtdeckung:** Nicht die nominelle Tiefe, sondern die zum Lock gesichert verfügbare Starter-Coverage bewerten; Bye/Out/Rollenverlust getrennt führen. Vor allem Skattebos Fumble-/Rollenthema, Love/Barkley/Hall/Monangai Availability, Brown nach Bye und Walker-Rolle neu prüfen. Ein RB-Add benötigt tatsächliche FA-Availability plus Drop-/Churn-Opportunity-Cost.
2. **WR/FLEX:** Bernards 92→94 % Snap Share und Week-6-Targets als relevanten Rollen-Trigger prüfen, ohne einen 25,70-Punkte-Median anzunehmen. Waddle weiter kritisch nach Targets, Routes, Quarterback-Umfeld und Playcalling-Effekt bewerten; nicht wegen des fiktiven Bernard-Thursday-Vergleichs abstrafen.
3. **TE:** McBride halten; Warrens Groin-/Inactive-Status verfolgen; Fannin vs. Loveland anhand externer Wochenranglisten, tatsächlicher Routes/Targets und QB-/Offense-Kontext statt allein eigener Modellwerte entscheiden. Vier gehaltene TE sind bei zwei festen Starterspots ein struktureller Vorteil, keine automatische Cut-Empfehlung.
4. **QB:** Alle vier tatsächlich startenden QB-Assets (Mahomes, Daniels, Shough, Penix) wieder gleichwertig in den Sunday-Pregame-Abgleich nehmen; keinen Boxscore-Chase aus Week 5 oder 6.
5. **Prozessqualität / Quellen:** Für jeden kritischen Start eine kleine datierte Decision-Opportunity-Timeline dokumentieren: Zeitpunkt, erlaubte Spieler, Injury-Lage, offener Lock, externe Quelle samt Stand und optional eigenes Modell. Die externe Markteinschätzung bleibt unabhängig vom Modell-Kalibrierungsbericht.

## 10. Bewertungsfazit und Grenzen

**Sportliches Urteil:** Dritter Sieg in Folge, 4–2 und Platz 3, aber nur Rang 5 nach Week-6-Wochenpunkten.  
**Lineup-Ergebnis:** 169,28 von legalen 229,16 = **73,9 %** Hindsight-Effizienz, **59,88** Ex-post-Punkte Abstand.  
**Entscheidungsurteil:** Das große Waddle-vs.-Bernard-Versäumnis der ersten Chatversion wird ausdrücklich **zurückgenommen**. Die damalige Waddle/Fannin-Absicherung war bewusst und bei Barkley/Love-Risiko legitim. Externe Pregame-QB-/TE-Einschätzungen geben wichtige zusätzliche Evidenz, die nicht durch die eigene noch unreife Projektion ersetzt werden darf. RB-Coverage und Sunday-Neusortierung bleiben prüfwürdig.

**Offene Evidenzlücken:** Kein vollständiger versiegelter finaler Pregame-Decision-Set-Snapshot; konkrete originale AutoSub-Konfiguration und jeder Late-Swap nicht archiviert; Week-6-Snap-Datei global nicht final; externe Websites mit teils nachträglich aktualisierten Rankings und ohne rückholbare historische Revision; keine vollständige historisch zeitgestempelte Week-6-FA-Verfügbarkeitsliste. Deshalb kein sicherer weiterer Decision-Regret-Betrag behauptet.

**Governance:** Die User-Freigabe vom 21.10. betrifft die Persistierung dieser neuen Rückschau sowie die separate kanonische Methodenregel in \`fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md\`. Weder frühere abgeschlossene Wochenreviews noch historische Startentscheidungen/Seals noch das Projektionsmodell werden verändert.
