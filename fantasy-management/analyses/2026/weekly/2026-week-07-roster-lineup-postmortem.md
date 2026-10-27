# Mighty Giants — Week 7 2026 Roster + Lineup Postmortem

## 0. Status, Quellen und Outcome-Firewall

- **Rekonstruktion:** 27.10.2026; NFL Week 7 (22.–26.10.); Mighty Giants, TeamID 1.
- **Gegner:** Dennis / Team DennisLACards (TeamID 5). **Final:** 177,42 : 210,66; Niederlage um 33,24 Punkte. Bilanz 4–3, weiterhin Platz 3.
- **Typ:** abgeschlossenes retrospektives Wochenreview, kein versiegelter Decision Record. Die vor Spielbeginn gespeicherte [Week-7-Ex-ante-Analyse](2026-week-07-lineup-ex-ante-decisions.md) (25.10., ca. 14:12 MEZ) wird **nicht** überschrieben oder aus dem Ergebnis neu begründet.
- **Format:** 6 Teams, Full PPR; 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K.

### Evidenzhierarchie und Grenzen

1. **Finale Punkte und Starter:** `data-source/leagues/nfl-reise/seasons/2026/matchups/week-7.json` (Mighty-Giants-Roster `clr-a8e576139994570d82e9ea2ed3f42b1b`, 37 Spieler, 13 Starter); `public/data/Matchups.json` mit Week-7-`CompletionState=final`. Die 13 StarterPoints summieren sich auf exakt 177,42.
2. **Ex ante, primär:** `2026-week-07-lineup-ex-ante-decisions.md`, damalige Nutzer-Entscheidungen und Verletzungs-/Lock-Abwägungen. Es existiert kein vollständiger, vor *allen* Spielen eingefrorener Decision-Set-Snapshot.
3. **Historische Transaktionen:** `data-source/leagues/nfl-reise/seasons/2026/transactions/week-7.json`, mit Erfolgsstatus, CreatedAt/StatusUpdatedAt und Spieler-IDs; ein fehlgeschlagener Claim zählt nicht als tatsächlich verfügbarer Zugang.
4. **Roster-Eligibility-Rekonstruktion:** aktuelles `data-source/leagues/nfl-reise/seasons/2026/rosters.json`, in Kombination mit Week-7-Transaktionen, Week-7-Matchup-Pool und Ex-ante-Starter-Snapshot. Weder das historische Matchup noch das spätere Roster-Readmodel archiviert sämtliche **ursprünglichen Week-7-Reserve-/Taxi-Belegungen mit separatem Lock-Zeitstempel**. Daher ist das Hindsight-Maximum weiter unten ein **unter den explizit angegebenen Eligibility-Annahmen rekonstruiertes**, kein zweifelsfrei separat eingefrorenes Slot-Archiv.
5. **Nutzung:** `data-source/nfl/snap-counts/2026/06.json` und `07.json`; beide melden `Finalized=false`. Betroffene vorhandene Game-Zeilen sind als vorläufige Usage-Indikatoren verwendbar; für nicht enthaltene Spiele (insbesondere Monday Night) werden keine Snap-Zahlen behauptet. Snap Share ist **nicht** Route Participation, Target Share oder ein Ersatz für Touches.
6. **Modell, getrennt von Entscheidungsgüte:** `data-derived/player-week-fantasy/nfl-reise/2026/07.json` (V4-C), mit historisierten Projektionswerten. `ActualScoringEvidenceFinalized=true`, aber `TargetWeeklyRosterFinalized=false`; bei einzelnen Spielern weichen die enthaltenen Istpunkte vom finalen League-Matchup ab (siehe Abschnitt 8).
7. **Externe Pregame-Stimmen:** CBS/Jamey Eisenberg (21.10.), NFL Fantasy (21./22.10.), UPI (22.10.), Spike Week (Stand 22.10., 10:20 ET), Harris Football (Stand 24.10., 16:00 ET), FantasyPros/Derek Brown (24.10.) und offizielle Team-Injury-Reports. Sie sind qualitative bzw. quellenformatabhängige externe Prüfmaßstäbe; aktualisierte Webseiten sind **nicht automatisch archivierte Originalrevisionen**.

**Präzise Zeitgrenze:** Lovelands 19,90 Punkte waren am Sonntag-Cutoff schon vom Donnerstag bekannt. Spätere Spieler-/Verletzungsresultate gelten nur als Ex-post-Evidenz. Für das lokale Timing gilt die Umstellung auf MEZ am Sonntag 25.10.2026.

## 1. Ergebnis und Liga-/Saisonkontext

| Week-7-Matchup | Final |
| --- | ---: |
| **Mighty Giants – DennisLACards** | **177,42 : 210,66** |
| Ruhr Valley Packers (Marcel) – Mammoth Marauders (Jan) | 140,60 : 172,40 |
| Just Bill (Flo) – TimpaBay (Tim) | 214,08 : 186,70 |

Dennis erzielt den zweithöchsten Score der sechsköpfigen Liga; Mighty Giants liegen mit 177,42 auf Wochenrang 4. Der gegnerische 0–6-Record war vorab ein valides, aber **nicht hinreichendes** Indiz für eine Favoritenrolle. Sein konkreter Starterpool hätte das Risiko-Budget begrenzen müssen. Das Wochenresultat beruht sowohl auf eigener Unterproduktion als auch einem starken Gegner, nicht allein auf Start/Sit-Fehlern.

Nach Week 7: **4–3, Platz 3**, 1.367,66 Points For und 1.289,76 Against; Marcel ist ebenfalls 4–3, mit 1.306,14 Points For. Der Playoff-Platz ist nicht gesichert. Der Week-7-Teamwert liegt 8,14 Punkte über Week 6 (169,28), aber deutlich unter Week 4/5 (221,84/232,10). Die letzte Vier-Wochen-Folge 221,84 / 232,10 / 169,28 / 177,42 ist kein Beweis für einen permanenten Trend ohne Rollen-/Schedule-Analyse.

## 2. Gewertete 13 Starter — finaler League-Score, Modell nur als Diagnose

| Slot | Starter | Week-7-Ist | V4-C-Projektion |
| --- | --- | ---: | ---: |
| QB | Patrick Mahomes | 7,00 | 19,55 |
| QB | Tyler Shough | 14,82 | 19,22 |
| RB | Chase Brown | 9,80 | 13,89 |
| RB | Kenneth Walker III | 9,70 | 25,58 |
| WR | Germie Bernard | 5,70 | 10,02 |
| WR | Malik Nabers | 18,10 | 16,18 |
| TE | Colston Loveland | 19,90 | 7,90 |
| TE | Trey McBride | 27,10 | 17,34 |
| FLEX | George Pickens | 15,70 | 13,97 |
| FLEX | Tetairoa McMillan | 8,00 | 16,39 |
| FLEX | Jaylen Waddle | 8,80 | 9,26 |
| FLEX | Puka Nacua | 21,80 | 22,67 |
| K | Ka'imi Fairbairn | 11,00 | 10,35 |
| **Summe (unrundete Modellwerte)** | | **177,42** | **202,32** |

**Große Ergebnisabweichungen:** Walker −15,88; Mahomes −12,55; McMillan −8,39 gegenüber V4-C; Loveland +12,00, McBride +9,76. Das sind **Modell-/Outcome-Residuen, keine automatischen Coaching-Fehler**. Positive TE-Ergebnisse haben die schwachen QB/RB/WR-Scores nur teilweise kompensiert. Der Final-Score stammt immer aus dem League-Matchup, nicht aus der unvollständig synchronisierten Derived-Actual-Spalte.

## 3. Historische Bank, Waivers, Taxi-/Reserve-Boundary

**Punktende Spieler im 37er-Matchup-Pool, die nicht gewertet wurden:**

| Spieler | Week-7-Punkte | Einordnung zum letzten bekannten Pregame-Cutoff |
| --- | ---: | --- |
| Tre Tucker | 21,30 | Aktive Bank; ausdrücklich **AutoSub für Puka**, nicht unabhängiger Zusatzstarter |
| Michael Penix Jr. | 20,42 | Aktive QB-Alternative zu Shough und Mahomes |
| Cam Skattebo | 19,10 | Aktiver RB; nach Week-6-Rollenverlust ex ante stark risikobehaftet |
| Saquon Barkley | 15,10 | Aktive Bank; Hamstring / Questionable, später Monday-Start |
| Harold Fannin Jr. | 13,10 | Aktiver TE, hinter McBride/Loveland |
| Dylan Sampson | 10,70 | Aktiver RB im rekonstruierten Slotstatus; produktiver Week-7-Output |
| Marvin Harrison Jr. | 7,60 | Aktiver WR, keine begründete ex-ante Priorität gegenüber Core-Startern |
| Seth McGowan | 5,80 | Erst Sonntag 25.10. per erfolgreichem Waiver hinzugekommen; RB-Backup/Stash, kein belegter Grenzstarter |

**Besondere Ausschlüsse:** Im nachgelagerten Canonical-Roster liegen **Antonio Williams und Chris Bell auf Taxi**; **Jaxson Dart, Jonathon Brooks, Davante Adams, Alec Pierce und De'Zhaun Stribling auf Reserve**. Die Taxi-/Reserve-Verteilung ist für die Week-7-Eligibility eine explizite Rekonstruktionsannahme, **kein datierter Week-7-Locknachweis**. Ihre Punkte gehören nicht zur aktiven Best-Ball-Kandidatenmenge. Mehrere weitere Null-Spieler haben Bye, Inactive-/Out-Status oder fehlende Spielnutzung; Nullpunkte beweisen nicht per se Verfügbarkeit.

**Week-7-Transaktionen der Mighty Giants (UTC in MEZ/MESZ umgerechnet):**
- **21.10., 12:05 MESZ:** Brian Thomas Jr. (Sleeper 11631) statt Wicks (9486), erfolgreich. Tre Tucker (10213) statt Pearsall (11638), ebenfalls erfolgreich. Ein früherer zusätzlicher Tucker-Claim ohne Drop wurde wegen zu vieler Spieler abgewiesen und erzeugte keinen zweiten Besitzpfad.
- **25.10., 11:04 MEZ:** Seth McGowan (13424) und Travis Hunter (12530) durch erfolgreiche Claims mit Drops hinzugekommen. Ein früherer Hunter-Claim ohne Drop scheiterte an der Rostergröße.
- **25.10., ca. 14:12 MEZ:** dokumentierter Ex-ante-Starterstand wurde **nach** den Sonntag-Waivers festgehalten. Hunter hatte Bye; McGowan blieb ein Colts-Backup hinter Jonathan Taylor. Beide kamen rechtzeitig für ihren möglichen Sonntag-Vergleich hinzu, waren aber nicht auf Basis eines nachgewiesenen Weekly-Starterprofils vorzuziehen.

Spätere Besitzstände dürfen die historische Startberechtigung nicht ersetzen. Vollständige originale Screenshots/Paarungsreihenfolgen aus Sleeper sind nicht im Canonical-Matchup abgelegt.

## 4. Verbindliche Decision-Opportunity-Matrix

| Entscheidungsfenster (Berlin) | Ex ante bekannt / legal | Ex-post-Ausgang; Bewertungsgrenze |
| --- | --- | --- |
| **Do 22.10. vor Bears–Patriots / Loveland-Lock** | McBride gesetzt; Loveland gegen Fannin als TE2 geprüft, Loveland bewusst bevorzugt. | Loveland 19,90 vs. Fannin 13,10. Keine rückwirkende Begründung mit seinem Donnerstagsscore. |
| **Sa 24.10.** | Barkley nach zwei limitierten Einheiten **Full Practice**, aber offiziell Questionable; Full Practice steigert Startchance, garantiert keinen normalen Workload. Waddle ohne vergleichbares Comeback-Risiko. | Das Barkley→Waddle-AutoSub-Szenario wurde diskutiert, wegen *active-but-limited*-Risiko aber bewusst **nicht** final gewählt. |
| **So 25.10., 11:04 MEZ Waivers** | Hunter/McGowan erfolgreich hinzugekommen; beide keine belegten Week-7-Starter-Upgrades. | Kein punktorientierter nachträglicher Swap mit Stashes. |
| **So 25.10., ca. 14:12 MEZ Cutoff** | Waddle direkt starten; Barkley und Hall benchen. Shough vor Penix, Mahomes gesetzt; Bernard WR; Puka mit Tucker-AutoSub laut Robert technisch eingerichtet. Bereits 19,90 Loveland-Punkte bekannt. | Entscheidungswille und tatsächlich gewertetes 13er-Starter-Set stimmen überein. Die originale AutoSub-Konfiguration ist im Repo nicht separat materialisiert. |
| **So 25.10., 14:30 MEZ Paris-Lock** | Shough und Bernard fest gelockt; gegen nachfolgende Starts nur noch zulässige Änderungen anderer Positionen. | Shough 14,82; Bernard 5,70. Nicht wegen späterer Bench-Ergebnisse als nachträglich austauschbar behandeln. |
| **So 25.10., 18:00 MEZ frühe NFL-Spiele** | Hall letztlich offiziell inactive, Skattebo/andere frühe RB-Optionen sperren zu ihrem Kickoff. Inactive-Wissen erst nach der dokumentierten 14:12-Entscheidung als neues Signal behandeln. | Hall 0; Skattebo 19,10. Skattebos Breakout war nicht als 19,10-Punkte-Ergebnis vorhersehbar. |
| **So 25.10., 21:05 MEZ Waddle-Lock** | Entscheidende Frist für theoretisches Barkley-Starter/Waddle-als-früherer-Sub-Pairing; final war **Waddle direkt Starter**. | Waddle 8,80; Barkley 15,10. Kein automatischer +6,30 Decision Regret. |
| **So 25.10., 21:25 MEZ Rams–Raiders** | Puka trotz Wade-Frage Starter, Tre Tucker laut Nutzer als AutoSub; nur beim zulässigen Inactive-Fall greift die Versicherung. | Puka aktiv, 21,80; Tucker auf Bank, 21,30. Keine AutoSub-Auslösung nachgewiesen/erforderlich; Tucker-Punkte waren keine unversicherte verlorene Zusatzposition. |
| **Di 27.10., 01:15 MEZ MNF** | Barkley kam tatsächlich aktiv zurück; Pickens später regulärer Starter. Die Barkley-News nach Waddle-Lock waren für dessen Slot nicht mehr frei disponibel. | Barkley 15,10; Pickens 15,70. Monday-Snap-Zeilen liegen im nicht finalen NFL-Snap-Bestand noch nicht belastbar vor. |

**Zeit-/Wissenshygiene:** Der am 24.10. datierte offizielle Eagles-Injury-Report belegt Barkleys Saturday-Full und Questionable. Die finale Monday-Inactive-Liste der Eagles vom 26.10. bestätigt seine Aktivität erst **nach** Waddles Lock. Die Jets bestätigten Halls Inactive am Sonntag, also nicht als ursprüngliches Samstag-Faktum. Einzelne frühere Experten-Webseiten wurden später aktualisiert; ihre aktuelle Rangnummer ist kein garantierter exakter Stand zu jedem Lock.

## 5. Externe Pregame-Prognosen — unabhängig vom eigenen Modell

Bei Wocheneinordnungen haben verifizierte *vor dem betroffenen Lock datierte* Reports/Rankings Vorrang; Rankings mit späterer Revision nur qualifiziert zitieren.

| Externe Quelle und datierter Stand | Entscheidungsrelevanter Befund | Konsequenz |
| --- | --- | --- |
| **NFL Fantasy, Week-7-QB Start/Sit** (vor Week-7-Spielen) | **Mahomes als Sit of the Week** wegen Seattle-Passverteidigung und jüngstem Fantasy-Rückgang; **Shough** ebenfalls Sit-Vorsicht wegen schwächerer jüngster Passing-Produktion/Pittsburgh | Es gab eigenständige negative QB-Argumente, die der etablierte Name nicht neutralisiert. |
| **UPI, 22.10.** | Mahomes QB15, Shough QB18; Penix in der veröffentlichten Top-20 **nicht** aufgeführt | Kein eindeutiger externer Penix-Vorrang. |
| **Spike Week, Snapshot 22.10. 10:20 ET** | Shough QB14, Mahomes QB18, Penix QB19 | Mahomes war nicht überall automatisch QB1; Penix blieb knapp dahinter. |
| **Harris Football, 24.10., 16:00 ET** | Mahomes QB8, Penix QB13, Shough QB16 | Gegenmeinung: Mahomes trotz Seattle hoch und Penix **vor** Shough. Die Quellen widersprechen sich real. |
| **CBS / Jamey Eisenberg, 21.10.** | Waddle **Borderline Start** gegen Arizonas WR-anfällige Defense, trotz schwachem bisherigen Output/Bo Nix | Valider positiver Week-7-Case, keine Garantie für stabilen Floor. |
| **NFL Fantasy, Week-7-RB** | Skattebo **Sit of the Week** nach Week-6-Fumble-/Rollendegradierung | Seine späteren 19,10 Punkte sind primär neue Usage-Evidenz, kein bewiesenes Pregame-Versäumnis. |
| **Philadelphia Eagles, 24.10.** | Barkley Full Practice, offiziell Questionable | Stark verbessertes Aktivierungs-Argument; ungelöste Workload-/Reinjury-Downside. |
| **FantasyPros / Derek Brown, 24.10. 19:35 ET** | Barkley nach Comeback mit möglichem Workload, aber zu erwartender Laufblock-/Dallas-Defense-Gegenwind | Barkley ist ein legitimer Waddle-Konkurrent, nicht klar risikofreier Must-Start. |
| **New York Jets, 23.10. und 25.10.** | Hall zuvor Questionable nach DNP/LP/LP; Sonntag offiziell inactive | Bench-Entscheidung trotz attraktivem Miami-Matchup sinnvoll. |

**Wichtige Revisionseinschränkung:** Die am 25.10. um 10:30 ET aktualisierte NBC-QB-/WR-Rangliste lag **nach** dem 14:12-MEZ-Cutoff für das frühe Paris-Spiel. Solche revisionsabhängigen Endstände werden hier nicht als damals zu jedem Zeitpunkt verfügbare ursprüngliche Rangposition zitiert. Allgemeine One-QB-/One-TE-Rangplätze müssen auf unsere 2-QB-/2-TE-Liga übertragen werden.

**Belegte externe Links, getrennt vom Repo-Modell:**
- NFL QB: https://www.nfl.com/news/nfl-fantasy-2026-start-em-sit-em-quarterbacks-for-week-7
- NFL RB/Skattebo: https://www.nfl.com/news/nfl-fantasy-2026-start-em-sit-em-running-backs-for-week-7
- UPI QB, 22.10.: https://www.upi.com/Sports_News/NFL/2026/10/22/fantasy-football-quarterback-rankings-Week7/5301792670015/
- Spike Week, 22.10.: https://spikeweek.com/week-7-fantasy-football-rankings/
- Harris, Snapshot 24.10.: https://christopher-harris-mgg4.squarespace.com/ranks
- CBS/Waddle, 21.10.: https://sportsfly.cbsistatic.com/fantasy/football/news/fantasy-football-start-em-sit-em-wr-in-week-7-jaylen-waddle-finally-finds-a-soft-matchup-to-exploit/
- Eagles Injury, 24.10.: https://www.philadelphiaeagles.com/news/cowboys-vs-eagles-injury-report-2026-nfl-week-7-saquon-barkley-jalyx-hunt
- Eagles Inactives, 26.10. (nur Ex-post): https://www.philadelphiaeagles.com/news/cowboys-vs-eagles-inactives-saquon-barkley-jalyx-hunt-2026-week-7-monday-night-football
- FantasyPros/Barkley, 24.10.: https://www.fantasypros.com/nfl/notes/475134/saquon-barkley-2026-week-7-outlook.php
- Jets Injury, 23.10.: https://www.newyorkjets.com/news/jets-injury-report-week-7-vs-dolphins-friday-10-23-2026
- Jets Inactives, 25.10. (nur Ex-post): https://www.newyorkjets.com/news/jets-vs-dolphins-nfl-game-inactives-10-25-2026

## 6. Legales Hindsight-Best-Ball — rekonstruiertes bedingtes Maximum

Der rechenbasierte Pool besteht aus den 37 Week-7-Spielern minus der **für Week 7 als unverändert angenommenen** aktuellen Reserve-/Taxi-Belegung, ausschließlich mit Spielpunkten aus dem finalen Canonical-League-Matchup. Pflichtslots 2 QB / 2 RB / 2 WR / 2 TE / 1 K, danach vier FLEX RB/WR/TE.

| Slot | Hindsight-Spieler | Ist |
| --- | --- | ---: |
| QB | Michael Penix Jr. | 20,42 |
| QB | Tyler Shough | 14,82 |
| RB | Cam Skattebo | 19,10 |
| RB | Saquon Barkley | 15,10 |
| WR | Puka Nacua | 21,80 |
| WR | Tre Tucker | 21,30 |
| TE | Trey McBride | 27,10 |
| TE | Colston Loveland | 19,90 |
| FLEX | Malik Nabers | 18,10 |
| FLEX | George Pickens | 15,70 |
| FLEX | Harold Fannin Jr. | 13,10 |
| FLEX | Dylan Sampson | 10,70 |
| K | Ka'imi Fairbairn | 11,00 |
| **Bedingtes Hindsight-Maximum** | | **228,14** |

- **Realisiert 177,42; rechnerischer Best-Ball-Gap 50,72; 77,8 % Hindsight-Effizienz.**
- Der perfekte hindsight-Score hätte Dennis um **17,48** übertroffen. Das macht den Gap nicht zu **50,72 vermeidbaren Entscheidungsfehler-Punkten**.
- Der hypothetische Tucker-Start hätte die tatsächlich von Tucker bereitgestellte Puka-AutoSub-Versicherung verändert. Das optimale Punkteroster ist **kein** identischer Risikomanagementplan mit denselben Versicherungen.
- Für eine uneingeschränkt als *periodenstabil legal* deklarierte Zahl wäre ein datierter Week-7-Reserve-/Taxi-Snapshot zusätzlich nötig. Ohne den bleibt die explizite Bedingung bestehen; spätere Reserve-/Taxi-Stände dürfen nicht unmarkiert zu historischen Fakten werden.

## 7. Same-Information-Re-Decision: Entscheidung statt Punktjagd

| Zeitkonformer Entscheidungskonflikt | Ex-post-Vergleich | Same-Information-Urteil |
| --- | ---: | --- |
| **Mahomes statt Penix** | Penix +13,42 | **Prüfenswerter enger Decision-Regret-Kandidat**, aber kein klarer Beweis: NFL-/Spike-Week-Warnung zu Mahomes, dennoch UPI/Harris Mahomes vor Penix. Warnungen für schwieriges Matchup zu wenig prominent gegen Talentstatus geprüft; Re-Decision ohne neues Wissen bleibt umstritten. |
| **Shough statt Penix** | Penix +5,60 | **Eher Outcome Regret:** Spike Week und UPI sprechen gegen eindeutigen Penix-Pregame-Vorsprung; Harris favorisiert Penix. Kein sauberes Analysten-Einstimmigkeitssignal. |
| **Waddle statt Barkley** | Barkley +6,30 | **Enge Boundary, möglicher leichter Risiko-Gewichtungs-Regret:** Full Practice, dünnes Eagles-Backfield und mögliches Volumen stützten Barkley; Hamstring/Questionable/Monday-Lock und active-but-limited-Risiko stützten Waddle. Bewusste konservative Nutzerpräferenz bleibt legitim. Kein sicherer +6,30-Prozessfehler. |
| **Hall nicht starten** | Hall 0 | **Richtiger Risikoentscheid**. Spätere Inactive-Bestätigung darf aber nicht als vor dem ursprünglichen Cutoff bekannt angenommen werden. |
| **Skattebo benchen** | 19,10 auf Bank | **Outcome Regret:** massive Week-6-Degradierung und externes NFL-Sit-Signal rechtfertigten Vorsicht. Week 7 liefert neue Rolleninformation, kein Beweis für vorhersehbare Punkte. |
| **Bernard statt Tucker** | Tucker +15,60 | **Eher Outcome Regret + Portfolio-Prüfung:** vorliegende Bernard-Opportunity und CBS-Support; Tucker als Puka-Inactive-Versicherung. Direkter Punktetausch ist **kein** äquivalenter AutoSub-Plan. |
| **Loveland statt Fannin** | Loveland +6,80 | **Positiver Decision-Prozess:** vor Donnerstag anhand Opportunity/TE2-Gruppe begründet, nicht nur weil Loveland nachträglich gewann. |
| **Puka starten, Tucker als AutoSub** | Puka 21,80, Tucker 21,30 | **Gute Absicherung/Execution:** Puka aktiv; keine verpasste AutoSub-Auslösung. Die Paarung ist nur durch Nutzeraussage, nicht durch eigene Sleeper-AutoSub-Archivierung belegt. |
| **Walker, Brown, McMillan starten** | 9,70 / 9,80 / 8,00 | **Eher Outcome Regret mit Rollen-Recheck:** produktive Pregame-Rollen und starke externe Startereinstufungen; neue Week-7-Nutzung differenziert überprüfen. |

**Kern-Firewall:** Keine nachträgliche ex-ante-Uminterpretation nur weil ein RB/WR plötzlich effizient wurde. Ein möglicher Verbesserungshebel ist **frühere ernsthafte Einbeziehung divergierender externer QB-Sits und Barkleys tatsächlicher Practice-Verbesserung**, nicht pauschaler Best-Ball-Chase.

## 8. Tatsächliche Usage, Nachhaltigkeit und Datenqualität

Offense-Snaps, soweit in den **nicht global finalisierten** Week-6-/Week-7-NFL-Snap-Partitionen enthalten:

| Spieler | Week 6 | Week 7 | Interpretation für nächstes Spiel |
| --- | ---: | ---: | --- |
| Cam Skattebo | 6 / 8 % | **37 / 56 %** | Deutlicher Rollen-Rebound **plus** 19,10 Fantasy; Touch-/Fumble-/Early-Down-Arbeit und Harbaugh-Berichte neu prüfen. |
| Tre Tucker | 46 / 70 % | **56 / 82 %** | Positiver Einsatztrend passend zu 21,30; Targets/Routes vs. einmalige Effizienz prüfen. |
| Jaylen Waddle | 39 / 65 % | **34 / 56 %** | Sinkender Offense-Anteil; vereinbar mit hoher Route-Participation auf gespielten Passplays, aber kein Beweis für stabilen Volumen-Floor. Genaues Target-/Route-Volumen erforderlich. |
| Germie Bernard | 74 / 94 % | **58 / 91 %** | 5,70 Punkte bei weiterhin sehr hoher Nutzung; kein reflexartiger Role-Downgrade. |
| Kenneth Walker III | 45 / 74 % | **39 / 74 %** | 9,70 Punkte trotz stabiler Anteilsrolle; Rush/Receiving, Touch-Qualität und Gegnerkontext prüfen. |
| Tetairoa McMillan | 60 / 76 % | **38 / 68 %** | Niedrigerer Anteil und 8,00; Teamvolumen, Routes und mögliche Game-Script-Ursachen prüfen. |
| Puka Nacua | 52 / 90 % | **61 / 85 %** | Trotz Calf-Kontext hohe Participation und 21,80. |
| Malik Nabers | 66 / 86 % | **48 / 73 %** | Weiter produktiv (18,10), aber sinkender Anteil beobachten. |
| Colston Loveland | 68 / 88 % | **58 / 84 %** | Starke Doppel-TE-Leistung nicht automatisch als wachsende Snap-Share verkaufen. |
| Trey McBride | 70 / 97 % | **75 / 93 %** | Elite-Einbindung, 27,10 ist zusätzlicher Output, nicht die alleinige These. |
| Harold Fannin Jr. | 56 / 89 % | **58 / 83 %** | 13,10 Bankpunkte + weiterhin relevante Rolle; TE-Rotation real. |
| Dylan Sampson | keine Week-6-Zeile | **32 / 46 %** | 10,70-Punkte-Game mit substantieller Einsatzzeit; RB-Depth/Role-Context prüfen. |

**Nicht interpretierbar:** Penix/Barkley/Pickens ohne belastbare Week-7-Snap-Zeile in dieser Partition; kein Erfinden von Routes/Targets/Carries. Die enthaltenen aktuellen Angaben sind noch kein endgültiges NFL-Snap-Audit.

**Konkret erkannter Scoring-Inkonsistenzfall:** Im Week-7-Canonical-League-Matchup stehen für **George Pickens 15,70** und **Saquon Barkley 15,10**, während `data-derived/player-week-fantasy/nfl-reise/2026/07.json -> Records[].Actual.Points` für dieselben CanonicalPlayerIDs jeweils **0,00** liefert, obwohl der globale Actual-Scoring-State als `final` gemeldet ist. Mögliche Ursachen (z. B. zeitliche Materialisierung oder abweichende Provenienz) sind **noch nicht verifiziert**. Deshalb nicht still Model-Actual 0 als finales League-Fantasy-Resultat übernehmen, keine Pipeline verändern und diesen Konflikt als separaten Datenqualitäts-Recheck behandeln.

**V4-C (separat):** 202,3159 prognostizierte Starterpunkte gegen finale 177,42 (−24,8959). Browns/Walkers und Mahomes' Residuen zeigen Schwächen in dieser Woche, die starken TEs kompensieren teils. Die Modellwerte werden **nicht** als Entscheidungsrichter für den damaligen Cutoff gewertet, zudem ist das Derived-Actual-Material nicht in allen Montagsspielen konsistent. Ein echter Kalibrierungsbericht braucht vergleichbare, finalisierte und zeitlich gültige Samples, nicht nur diese 13 Spieler.

## 9. Roster-/Dynasty-Interpretation — Week 8 ohne Boxscore-Chase

### Quarterback

Mahomes bleibt ein wertvoller Dynasty-Core und potenzieller Weekly-Starter; sein Seattle-Ausreißer zwingt **nicht** zum Cut/Trade. Allerdings ist eine automatische QB1-Startergarantie unabhängig vom Matchup in einer echten 2-QB-Rotation nicht sinnvoll. Shough und Penix müssen auf derselben datierten Boundary neu verglichen werden, sobald Week-8-Opponent, Protection, Injury und unabhängige Rankings verfügbar sind; Jayden Daniels nach Bye auf Availability prüfen. Jaxson Dart nur nach tatsächlicher Reserve-/Gesundheitslage als aktiv startbare QB-Option behandeln.

### Running Back

Walker bleibt bei 74 % Snaps ein klarer Wochenkandidat; Brown hat 75 % im Week-7-Game und muss nach Touches/Passdowns, nicht nach 9,80, bewertet werden. Skattebo gewinnt durch 56 % Week-7-Snaps den Status **erneut ernsthafter Start-/FLEX-Kandidat** (noch keine Garantie für dauerhaften Lead-Back). Barkleys Hamstring-Comeback und verfügbare Workload-Signale neu prüfen; Hall erst bei bestätigter Gesundheit und Umfang. Dylan Sampsons 46-%-Woche erhöht die Priorität zur Analyse der Browns-RB-Verteilung. Seth McGowan bleibt zunächst Handcuff-/Entwicklungs-Asset, nicht plötzlich Weekly-Starter aus 5,80 Punkten. Keine automatische Roster- oder Salary-Entscheidung aus diesen Einzelresultaten.

### Wide Receiver / FLEX

Waddles sinkender Snap-Anteil und die noch nicht erhärtete Effizienz-/Playcalling-These erfordern den dringendsten echten Recheck; 8,80 Punkte allein wären kein ausreichender Grund. Tucker gewinnt durch **82 %** und 21,30 Punkte eine ernsthafte Möglichkeit auf einen direkten Starter-Boundary-Platz, jedoch nicht ohne Routen/Targets und Matchup. Bernard fällt trotz 5,70 nicht automatisch heraus (91 % Snaps). Nabers, Puka, Pickens und McMillan weiter nach Rolle, Gegner und gegebenenfalls Injury betrachten. Nach den Week-7-Waivern auch Hunter als langfristiges Upside-Asset und BTJ als gehaltenen WR neu bewerten, nicht als historische Week-7-Starter.

### Tight End / Kicker

McBride (27,10) und Loveland (19,90) waren sehr gute zwei Pflicht-TE-Starts; Fannin (13,10) und der noch nicht verfügbare Warren bleiben echte Tiefe, nicht automatische Cuts oder rein rechnerische FLEX-Sieger. Keine pauschale Third-TE-Startregel ohne expliziten FLEX-Vergleich. Fairbairn 11,00: keine neue Streaming-Pflicht; grundsätzlich ein Kicker.

### Waiver-/Dynasty-Portfolio

Das Pre-Week-7-Stash-Motiv bei Hunter/McGowan war langfristige Optionswert-Abwägung, keine 2026-W7-Punktewette. Bewertung bleibt an aktuelle Opportunity, Draft Capital, Market Value, Relevanz für die 6er-Liga, geschützte Churn-Slots und realistische Trade-Nachfrage gebunden. Da Trades, Drops und Reserve-Plätze die längerfristige Struktur betreffen, ist kein einzelnes Week-7-Resultat eine selbstständige Transaktionsfreigabe.

## 10. Konkrete Week-8-Rechecks und wiederkehrende Prozesslehren

1. **Waddle/Tucker/Bernard/Skattebo:** Routes, Targets, Carries/High-Value-Usage und Week-8-Gegner prüfen; die gesamte letzte 2–3-Starter-/erste 2–3-Bank-Boundary gemeinsam neu sortieren, ohne Incumbency-Bonus.
2. **Mahomes/Shough/Penix/Daniels:** datierte externe Week-Rankings *einschließlich begründeter Sit-Takes* neben aktuellem Einsatz, Matchup und Eigenmodell dokumentieren. Unterschiedliche Expertenmeinungen nicht nach Ergebnis vereinheitlichen.
3. **Barkley/Hall/Puka/Pickens:** injury/Practice, Game-Time-Decision, glaubwürdiges Workload-Limit, tatsächlicher Kickoff und AutoSub-Versicherung separat abbilden. Waddle/Barkley verdeutlicht, warum früher Substitute-Lock und *active-but-limited* verschiedene Risiken sind.
4. **Walker/Brown/Sampson/Skattebo:** bei hoher Snap Share niedrige Fantasy-Punkte nicht direkt in Positionsverlust übersetzen; nachhaltiges Volumen, Passdown-/Goal-Line-Rolle und Gegnerspielstil prüfen.
5. **TE-Rotation:** McBride/Loveland/Warren/Fannin im 2-TE-Format mit Health, Routes/Targets und Week-8-Matchups prüfen; letzter TE/FLEX-Kandidat gegen WR/RB-Grenze statt isolierter TE-Rangliste.
6. **Data-quality / Scoring:** Pickens/Barkley-Derived-Istwert 0 gegen finale Matchup-Punkte verifizieren, Ursache und Freshness der NFL-/Derived-Monday-Daten diagnostizieren. Nicht die finalen League-Punkte überschreiben. TargetWeeklyRosterFinalized und Snap-Finalität separat nachziehen.
7. **Matchup-Risikobudget:** Dennis' 0–6-Vorbilanz als Warnung behandeln: Gegnerstarter, Byes, Verletzungen und realistische Ceiling-Optionen konkret abgleichen statt einen vermeintlich ungefährdeten Floor-Sieg vorauszusetzen.
8. **Weekly-History-Lerntransfer:** Week-5/6-Waddle-Snapstabilität (65 %) war eine wiederholte Warnung für ein angebliches Usage-Comeback; Skattebos Week-6-Demotion war reale Pregame-Rollenevidenz und wurde Week 7 durch neue Nutzung teilweise revidiert. Beides zeigt: alte Rollenannahmen aktualisieren, ohne kurzfristiges Ergebnis als Ursache auszugeben.

## 11. Gesamturteil und noch offene Beweislücken

**Sportlich:** vierter Wochen-Score der Liga, Niederlage trotz ordentlicher TE-/Puka-Produktion, 4–3 auf Platz 3. Dennis erzielte starke 210,66 statt eines vom Record abgeleiteten schwachen Scores.

**Prozess:** gute Loveland/TE-Auswahl und Puka-Tucker-Absicherung; nachvollziehbares Skattebo-/Hall-Risikomanagement. Engster potenzieller echter Lernpunkt ist die eigenständige Gewichtung des Mahomes-Seattle-Matchups gegenüber Penix sowie Barkleys verbesserter Full-Practice-Status im Waddle-Vergleich. Der Waddle-Start war ausdrücklich eine bewusste konservative Portfoliowahl, **kein** gedankenloser Projektionsentscheid.

**Hindsight:** bedingtes Best Ball 228,14 (Gap 50,72; 77,8 %), ohne diese 50,72 als Coaching-Verlust auszugeben.

**Offene Beweisgrenzen:** keine periodenfest materialisierte 13-Start-/AutoSub-Konfiguration für jedes einzelne Lock-Fenster; Reserve-/Taxi-Slotstatus nur rekonstruiert; nicht global finale Week-7-Snaps; fehlende vollständige Routes/Targets/Touches; mehrere dynamische externe Rankings ohne gesicherte Ursprungsrevision; Derived-Istwerte für Pickens/Barkley nicht synchron mit finalem League-Matchup. Daher keine erfundenen punktgenauen *Decision-Regret-Kosten* und keine nachträgliche Überschreibung früherer Entscheidungen.

**Governance:** persistierte rückblickende Analyse unter `fantasy-management/analyses/2026/weekly/` im bestehenden [Issue #208](https://github.com/Lolindhir/fantasy-app/issues/208). Ex-ante-W7-Dokument, historische Decision-Seals, Liga-Scoring, technische Materialisierung und Rosterzustand bleiben unverändert.
