# Mighty Giants — Week 5 2026 Roster + Lineup Postmortem

## 0. Status, Rekonstruktion und Quellen

- **Saison/Woche:** NFL 2026, Week 5.
- **Team:** Mighty Giants, Robert, TeamID 1.
- **Gegner:** Jan / Mammoth Marauders, TeamID 4.
- **Ergebnis:** **232,10 : 200,12**, Sieg mit **31,98 Punkten Vorsprung**.
- **Finalisierung / Rekonstruktion:** **13.10.2026**, nach Fantasy-Scoring-Finality; Persistierung von Robert freigegeben.
- **Dokumenttyp:** abgeschlossenes retrospektives Postmortem, **kein** sealed Decision Record. Der Ex-ante-Entscheidungszustand wird nicht mit Ex-post-Wissen überschrieben.

### Beleglage und Quellenhierarchie

1. Finale historische Team-/Spieler-Punkte und 13 gewertete Starter aus source-data/leagues/nfl-reise/seasons/2026/matchups/week-5.json. Der Mighty-Giants-Datensatz enthält 37 Spieler.
2. Finalität, Liga-Matchups, Standings und Wochenkontext aus public/data/Matchups.json, public/data/WeeklyRecaps.json und public/data/League.json; League: CurrentWeek 6, FinalScoredWeek 5.
3. Spieler-Punkte und Modellprojektionen aus derived-data/player-week-fantasy/nfl-reise/2026/05.json (784 Records, ActualScoringEvidenceFinalized = true). **Einschränkung:** ein archivierter Wochen-Modellwert ist keine Garantie, dass genau diese Projektion im finalen persönlichen Start/Sit-Entscheidungszeitpunkt sichtbar oder ausschlaggebend war.
4. NFL-Offense-Snaps und Snap-Share-Vergleiche aus source-data/nfl/snap-counts/2026/04.json und source-data/nfl/snap-counts/2026/05.json.
5. Aktuelle Taxi-/Reserve-Sektion aus public/data/League.json und fantasy-management/generated/operations/managed-roster-overview.json **nur als Rekonstruktionshilfe** gegen den historischen Week-5-Spielerpool; source-data/leagues/nfl-reise/seasons/2026/transactions/week-5.json dokumentiert in Week 5 keine Mighty-Giants-Transaktion. Die Canonical-Matchup-Datei enthält keinen separaten periodenstabilen Taxi-/Reserve-Status.
6. Ex-ante-Prozesskontext aus den Week-1-bis-Week-4-Reviews und damaligen Chatüberlegungen zu Shough/Cousins sowie Waddle/WR-Alternativen; kein vollständig archiviertes finales Week-5-Decision-Set.
7. Bewertungsstandard: fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md, „Post-Week Roster + Lineup Retrospective“.

**Offene Evidenzlücken:** Week-5-Snap-Counts melden Finalized = false und umfassen derzeit **14 Spiele**; insbesondere **BUF@LA** fehlt, somit kein interner Week-5-Snap-Anteil von Puka Nacua oder Davante Adams. Der Week-5-Derived-Fantasy-Datensatz meldet außerdem TargetWeeklyRosterFinalized = false. Originale AutoSub-Paarungen, Reihenfolgen und konkrete Late-Swap-Execution fehlen in der historischen Matchup-Datei. **Gewertete Starter sind beweisbar; ursprünglicher Start-Intent und alle Absicherungspfade nicht vollständig.** Nicht belegte Targets, Routes und Injury-Details werden nicht ergänzt oder geraten.

## 1. Matchup-Resultat und Ligaentwicklung

| Week-5-Matchup | Final |
| --- | ---: |
| **Robert gegen Jan** | **232,10 : 200,12** |
| Flo gegen Marcel | 229,60 : 209,20 |
| Tim gegen Dennis | 197,76 : 185,62 |

Mighty Giants erzielen **den höchsten Team-Score von Week 5**. Nach 221,84 Punkten und +29,96 gegen Flo in Week 4 folgt der zweite Sieg mit nochmals höherem Score. Der Positiveffekt ist real, die Nachhaltigkeit des Weekly-Floors damit noch nicht belegt.

| Platz nach Week 5 | Manager | Bilanz | Points For |
| ---: | --- | ---: | ---: |
| 1 | Tim | 4–1 | 1.087,14 |
| 2 | Flo | 4–1 | 1.077,48 |
| **3** | **Robert** | **3–2** | **1.020,96** |
| 4 | Marcel | 3–2 | 988,90 |
| 5 | Jan | 1–4 | 969,50 |
| 6 | Dennis | 0–5 | 785,72 |

Robert steigt von Rang 4 auf Rang 3. Seine Scores in Weeks 1–5: **205,36 / 188,02 / 173,64 / 221,84 / 232,10**; Durchschnitt **204,19**. Gesamtpunktdifferenz: **+81,14** (1.020,96 For, 939,82 Against). In einer Liga mit sechs Teams und vier Playoffplätzen ist Rang 3 eine starke Position, aber kein mathematischer Playoff- oder Titelgarant.

Die archivierte Week-5-Modellsumme der 13 finalen Starter ist **189,82**, der tatsächliche Team-Score liegt **42,28 darüber**. Dies beschreibt positive Ergebnisabweichung, **nicht** automatisch gute Entscheidungsqualität.

## 2. Finale Starter — einzeln validiert

Slot-Struktur: **2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K**. Die Slot-Reihenfolge wird aus den 13 historischen Startern und dem aktiven Ligamuster rekonstruiert.

| Slot | Spieler | Punkte | Week-5-Modell |
| --- | --- | ---: | ---: |
| QB | Tyler Shough | 1,84 | 21,11 |
| QB | Jayden Daniels | 32,26 | 16,66 |
| RB | Jeremiyah Love | 2,20 | 11,49 |
| RB | Chase Brown | 7,00 | 15,11 |
| WR | George Pickens | 28,00 | 11,50 |
| WR | Davante Adams | 22,10 | 17,58 |
| TE | Trey McBride | 21,60 | 17,37 |
| TE | Tyler Warren | 21,40 | 11,99 |
| FLEX | Puka Nacua | 37,70 | 21,21 |
| FLEX | Jaylen Waddle | 4,80 | 10,56 |
| FLEX | Malik Nabers | 29,10 | 12,77 |
| FLEX | Cam Skattebo | 7,10 | 12,41 |
| K | Ka'imi Fairbairn | 17,00 | 10,07 |
| **Gesamt** | | **232,10** | **189,82** |

**Checksummenprüfung:** Die 13 StarterPoints aus dem historischen Matchup addieren sich zu **232,10**.

### Warum ein starker Sieg trotz erheblicher Ausfälle?

- Fünf startende WR: **121,70 Punkte**.
- Zwei TE: **43,00 Punkte**.
- Zwei QB: **34,10 Punkte** — fast alles dank Daniels.
- Drei RB: **nur 16,30 Punkte**.
- Kicker: **17,00 Punkte**.

Die **acht punktbesten Starter** Nacua, Daniels, Nabers, Pickens, Adams, McBride, Warren und Fairbairn produzieren gemeinsam **209,16** Punkte. Die übrigen **fünf** Starter nur **22,94**. Das Team wurde von der Spitzenproduktion kompensatorisch getragen. Daraus folgt gerade **kein** belastbarer hoher Floor sämtlicher Starterplätze.

## 3. Bank und tatsächliche Vergleichsoptionen

| Aktiver Bankspieler | Position | Punkte | Modell |
| --- | --- | ---: | ---: |
| Michael Penix Jr. | QB | 14,40 | 13,78 |
| Dontayvion Wicks | WR | 11,30 | 9,27 |
| Jakobi Meyers | WR | 5,70 | 11,15 |
| Malachi Fields | WR | 4,00 | 6,79 |
| Colston Loveland | TE | 3,90 | 6,54 |
| Harold Fannin Jr. | TE | 1,40 | 12,64 |

**Taxi:** Antonio Williams 6,10 und Chris Bell 2,60. Beide sind ohne entsprechende vorherige Rosteränderung **keine** normalen Bank-Alternativen. **Reserve:** Jonathon Brooks, Jaxson Dart, Ricky Pearsall, Dylan Sampson und De'Zhaun Stribling; im historischen Week-5-Matchup je 0 Punkte. Weitere aktive Spieler im 37-Spieler-Pool produzierten ebenfalls 0 Punkte. Deren tatsächliche Spielbereitschaft darf nicht allein aus einem Null-Score erschlossen werden.

Die Trennung zwischen Taxi/Reserve/aktiv ist aus dem späteren unveränderten Roster unter Einbezug der Week-5-Transaktionsdaten **rekonstruiert**, nicht aus einem separat datierten historischen Statusobjekt bewiesen. Das ändert die positiven Best-Ball-Alternativen nicht, ist aber methodisch zu dokumentieren.

## 4. Legales Hindsight-Best-Ball

Mit tatsächlich erzielten Punkten und der rekonstruierten Week-5-Lineup-Eligibility:

| Slot | Optimierter Spieler | Punkte |
| --- | --- | ---: |
| QB | Jayden Daniels | 32,26 |
| QB | Michael Penix Jr. | 14,40 |
| RB | Cam Skattebo | 7,10 |
| RB | Chase Brown | 7,00 |
| WR | Puka Nacua | 37,70 |
| WR | Malik Nabers | 29,10 |
| TE | Trey McBride | 21,60 |
| TE | Tyler Warren | 21,40 |
| FLEX | George Pickens | 28,00 |
| FLEX | Davante Adams | 22,10 |
| FLEX | Dontayvion Wicks | 11,30 |
| FLEX | Jakobi Meyers | 5,70 |
| K | Ka'imi Fairbairn | 17,00 |
| **Best-Ball-Maximum** | | **254,66** |

- **Realisiert:** 232,10.
- **Hindsight-Lücke:** **22,56**.
- **Best-Ball-Effizienz:** **91,1 %**.
- **Week-4-Vergleich:** 221,84 von 274,14 = 80,9 %.

Die Differenz besteht rechnerisch aus **Penix statt Shough (+12,56)**, **Wicks statt Waddle (+6,50)** und **Meyers statt Love (+3,50)**, bei letzterem mit dem nötigen Umbau Skattebo von FLEX zu RB. Das ist eine **Ex-post-Aufstellung**. Es wäre methodisch falsch, den gesamten Abstand als vermeidbaren Decision Regret zu markieren.

## 5. Start/Sit- und Prozessreviews

### 5.1 Tyler Shough / Michael Penix Jr. / Kirk Cousins

**Resultat:** Shough 1,84, Penix 14,40, Differenz **+12,56** zugunsten des Bank-QB. Shough spielte **100 % der Offensive Snaps** seines Teams in Week 4 und Week 5; Week 5 waren es 45, Week 4 noch 74. Der verringerte absolute Playcount allein erklärt die katastrophale Fantasy-Ausbeute nicht; Ursachen müssen mit Game-/Passing-Kontext untersucht werden.

**Ex ante:** Das archivierte Modell erwartete **21,11 für Shough** und **13,78 für Penix**. Shough hatte damit auf den vorhandenen modellierten Fakten einen deutlichen Startvorsprung. Die vor Week 5 geführte Diskussion über in Rankings teils höher platzierten **Kirk Cousins** ist ein valider Anlass zur Zweitprüfung, aber kein Nachweis, dass Cousins im eigenen Roster war, ein Trade stattfand oder Penix zwangsläufig hätte starten müssen.

**Same-Information-Re-Decision:** Unter den belegten Modellwerten wäre Shough weiter vertretbar. Eine konträre zeitgenössische Injury-/Matchup-/Analystenevidenz hätte geprüft werden müssen, ist hier aber nicht ausreichend archiviert, um einen klaren Prozessfehler zu behaupten.

**Urteil:** **großer Outcome Regret, kein nachgewiesener Decision Regret.** Week-6-Recheck dringend, aber keine reflexhafte Cut-/Bench-Dauerregel aus 1,84 Punkten.

### 5.2 Jeremiyah Love — Gefahr der vorschnellen Workhorse-Projektion

**Week 5:** 2,20 Punkte, **36 Snaps / 49 % Offense-Snap-Share**; **Week 4:** 30 / 45 %. Der Snap-Anteil hat sich damit leicht erhöht, bleibt aber **unter 50 %**. Das stützt keine exklusive Backfield-Rolle und relativiert den früheren hohen Touch-Workload als sicheren neuen Floor.

**Ex ante:** Modell 11,49 für Love, 11,15 für Meyers, 9,27 für Wicks. Love war nach damaliger Projektion eine legitime knappe FLEX-/RB-Wahl und durfte nicht allein wegen Week-4-Scores automatisch fallen gelassen werden.

**Same-Information-Re-Decision:** Start weiter begründbar, aber Rollenunsicherheit ausdrücklich preisen. In unserer Vier-FLEX-Liga Love nicht wegen des Namens fest einbauen, sondern den letzten Starterplatz gegen **alle** WR-Optionen vergleichen.

**Urteil:** **Outcome Regret plus neuer Rollen-Risiko-Befund**, kein klarer 3,50-Punkte-Prozessfehler.

### 5.3 Chase Brown — Scoringrückgang und realer Usage-Trigger

- Week 4: **19,10 Punkte** dank starkem Receiving-Output, **60 Snaps / 79 %**.
- Week 5: **7,00 Punkte**, **39 Snaps / 60 %**; **-19 Prozentpunkte Snap Share**.
- Archiviertes Week-5-Modell: **15,11**.

Der Start war auf den vorliegenden Daten **klar vertretbar**: beste RB-Modellprojektion und nachgewiesene Week-4-Passing-Game-Rolle. Der tatsächliche Rückgang des Snap-Anteils ist **neue relevante Information**. Seine Ursache (Game Script, Backfield-Rotation, Einsatzform) wird aus den Snaps allein nicht bestimmt.

**Same-Information-Re-Decision:** Brown starten. **Urteil:** Outcome Regret; für Week 6 Ursache des Usage-Rückgangs prüfen, nicht bloß auf 7,00 Punkte reagieren.

### 5.4 Cam Skattebo — Volumen ohne Fantasy-Floor

- Week 4: **7,60 Punkte**, **43 Snaps / 64 %**.
- Week 5: **7,10 Punkte**, **56 Snaps / 63 %**.
- Modell Week 5: **12,41**.

Die grundlegende Einsatzrolle ist **stabil**, und absolute Snaps stiegen sogar. Der sehr ähnliche schwache Score zeigt, dass Präsenz nicht automatisch Receiving-, Red-Zone- oder Effizienzpunkte erzeugt. Die vorab angenommene Volume-Chance war trotzdem nicht grundlos.

**Same-Information-Re-Decision:** weiter legitimer FLEX-/RB-Pool-Kandidat, aber kein unantastbarer Floor-Spieler gegenüber zusätzlichen WRs. **Urteil:** Outcome Regret; High-Value-Touches gesondert prüfen.

### 5.5 Jaylen Waddle / Wicks / Meyers — die engste Boundary

| Vergleich | Week 4 | Week 5 | Modell Week 5 |
| --- | --- | --- | ---: |
| Waddle | 45 Snaps / 68 % | **40 / 65 %**, 4,80 Punkte | 10,56 |
| Wicks | 56 / 92 % | **52 / 84 %**, 11,30 Punkte | 9,27 |
| Meyers | 50 / 82 % | **61 / 85 %**, 5,70 Punkte | 11,15 |

Waddles vor Week 5 diskutierte positive Coaching-/Playcalling-Erzählung war ein **mögliches** Nutzungsargument; ein neuer Offensive Playcaller erzeugt aber nicht automatisch zusätzliche Routen, Targets und Snaps. Die Week-5-Daten zeigen **keinen Snap-Share-Anstieg** (65 % statt 68 %). Wicks hatte bereits in beiden Wochen eine wesentlich höhere Offense-Präsenz. Meyers lag im archivierten Modell sogar **knapp über Waddle**.

Das ist nicht dasselbe wie „Wicks hätte vorhersehbar 11,30 erzielt“: Ohne vollständige Targets/Routes/High-Value-Usage kann ein Spieler mit niedrigerem Snap Share trotzdem das bessere WR-Ceiling sein. Der Modellvorsprung Waddles zu Wicks war außerdem nur **1,30 Punkte**.

**Same-Information-Re-Decision:** Vor dem Lock Waddle **explizit** gegen Wicks und Meyers mit Rolle, Prognose und Risiko neu sortieren, statt die Playcalling-Story ungeprüft als Startvorsprung festzuschreiben. Bei Nachweis tatsächlicher Target-/Route-Verbesserung wäre Waddle legitim; ohne diesen Nachweis ist die Grenze knapp.

**Urteil:** **potenziell leichter Decision Regret / Review-Lücke**, nicht der sichere Prozessfehler über exakt 6,50 Punkte. Diese +6,50 sind die Ex-post-Differenz zu Wicks.

### 5.6 Malik Nabers — guter Lerntransfer aus dem Week-4-Grenzfall

- Week 4: **23,20 auf der Bank**, **51 / 76 % Snaps**.
- Week 5: **29,10 als Starter**, **80 / 90 % Snaps**.
- Week-5-Modell: **12,77**.

Der Week-4-Sit war nach späterer Gegenprüfung **nur ein Grenzfall**, weil Davante Adams auch mit Puka weiterhin sehr hohe Snaps spielte. Week 5 löste den engen Fall pragmatisch: **Nabers starten, ohne Adams automatisch zu verdrängen.** Week 5 brachte zusätzlich höhere Nabers-Nutzung, nicht bloß Glück über einen einzelnen Fantasy-Play.

**Same-Information-Re-Decision:** starten. **Urteil:** **starke Prozessaktualisierung**, positives Rollen- und Ergebnissignal; daraus nicht exakt 29,10 als neuen Median prognostizieren.

### 5.7 Pickens, Puka Nacua und Davante Adams

**George Pickens:** **28,00**, **53 Snaps / 88 % Week 5** gegenüber 67 / 86 % Week 4. Starkes Ceiling bei weiterhin hohem Usage-Anteil; klar begründeter Start.

**Puka Nacua:** **37,70** und somit höchster Mighty-Giants-Spieler. In Week 4 bereits **76 / 90 % Snaps**; die Week-5-BUF@LA-Snaps fehlen in der internen Datei. Der Score steht fest, **sein konkreter Week-5-Snap-/Routenanteil nicht**. Kein belegbarer Grund für den Sit.

**Davante Adams:** **22,10**; in Week 4 trotz Pukas Rückkehr **80 / 95 % Snaps** bei nur 7,20 Punkten. Diese damalige Usage machte einen automatischen Puka-bedingten Adams-Downgrade falsch; genau das wurde im Week-4-Review nachträglich korrigiert. Der Week-5-Score ist stark, die Monday-Week-5-Snaps sind aber noch offen.

**Same-Information-Re-Decision:** alle drei starten. **Urteil:** gut begründete Starts; zwischen gesichertem Score und noch ungesicherter Monday-Usage strikt unterscheiden.

### 5.8 Trey McBride, Tyler Warren und die feste 2-TE-Nachfrage

| TE | Week 4 Snaps | Week 5 Snaps | Week 5 Fantasy |
| --- | --- | --- | ---: |
| Trey McBride | 64 / 97 % | **66 / 90 %** | **21,60** |
| Tyler Warren | 56 / 85 % | **67 / 94 %** | **21,40** |

**43,00 gemeinsame Punkte** und zwei sehr hohe Offense-Anteile. Das ist mehr als TD-Varianz: beide sind im beobachteten Spielkontext stark eingebunden. Da **zwei TE fest** starten müssen, ist eine verlässliche Doppelbesetzung strukturell wichtiger als in generischen 1-TE-Ligen.

**Same-Information-Re-Decision:** beide starten. **Urteil:** klare Startqualität plus echte Usage-Bestätigung. Bei den Bank-TE Fannin (1,40) und Loveland (3,90) folgt daraus **kein** automatischer Cut oder Trade.

### 5.9 Fairbairn

**17,00 Punkte** gegenüber Week-5-Modell **10,07**; Week 4 ebenfalls stark mit 16,00. Der Start ist unstrittig. Zwei Kicker-Spikes ändern keine strukturelle Ein-Kicker-/Replacement-Level-Regel.

## 6. Trennung Decision Regret und Outcome Regret

| Fall | Ex-post-Punktegap | Urteil | Begründung |
| --- | ---: | --- | --- |
| Penix statt Shough | **+12,56** | **Outcome Regret** | Modell vor Vergleich klar pro Shough; fehlender Nachweis einer ex-ante besseren Penix-These |
| Wicks statt Waddle | **+6,50** | **Boundary; leichter potenzieller Decision Regret** | Enger Pool, deutlich höherer Wicks-Snap-Anteil, nicht belegter Waddle-Rollenanstieg |
| Meyers statt Love bei RB/FLEX-Umbau | **+3,50** | **Eher Outcome Regret** | Modellwerte Love/Meyers sehr ähnlich; spätere Snap-Daten klären Rollenrisiko besser |
| Brown niedrig | – | **Outcome Regret + Usage-Recheck** | Start ex ante klar tragfähig, Rückgang 79 % → 60 % neu |
| Skattebo niedrig | – | **Outcome Regret** | Rund 63–64 % Snaps, aber schlechte Ausbeute |
| Nabers ins Lineup | **29,10 erzielt** | **starke Prozessanpassung** | Week-4-Grenzfall neu bewertet; Week-5-Share 90 % |
| Beide TE fix | **43,00 erzielt** | **klarer guter Prozess** | Hohe bestätigte Week-5-Nutzung |

**Methodische Warnung:** Ein 91,1-%-Best-Ball-Wert misst die rückblickende Resultatnähe zum Optimum; er ist **keine isolierte Coach-Gütezahl**. Ohne den damaligen versiegelten Final-Lineup-Snapshot bleibt die feinste Ex-ante-Zuordnung teilweise unsicher. Die 22,56 sind daher **nicht** 22,56 erwiesen vermeidbare Fehlerpunkte.

## 7. Positions-/Usage-Befunde und Roster-Folgen

### Quarterback

Daniels (32,26) kompensierte Shough (1,84) fast vollständig. 100 % der Offensive Snaps garantieren keine gute QB-Produktion. Penix war als aktiver Bench-QB verfügbar und lieferte 14,40, rechtfertigt rückblickend aber keinen automatischen Rankingtausch. Vor künftigen Matchups **QB2-Floor, Pass-Offense-Kontext und tatsächliche externe Alternativen** gemeinsam bewerten.

### Running Back

Alle drei startenden RB zusammen **16,30**. Love 49 % Snap Share, Brown 60 %, Skattebo 63 %. Diese Kombination relativiert das Gefühl, der RB-Raum müsse jede Woche mehrere FLEX-Plätze besetzen. Bei **vier FLEX** ist die Competition für den letzten RB-Slot breit. Gleichzeitig beweisen zwei schwache Wochen nicht, dass Dynasty-Asset-Wert, Salary-/Cap-Profil oder Roster Security beschädigt sind. **Keine automatischen Trade-/Cut-Entscheidungen** aus den Ergebnissen.

### Wide Receiver

Fünf aktive WR lieferten **121,70**. Puka, Nabers, Pickens und Adams trugen das Ceiling. Waddle war der eigentliche inkrementelle FLEX-Grenzfall. Die wichtigste Week-6-Aufgabe ist **nicht** ein neues pauschales WR-Ranking, sondern ein vollständiger Vergleich aller startberechtigten WR/FLEX-Kandidaten nach Opportunity, Health und Matchup.

### Tight End

McBride und Warren: **43,00** mit 90 %/94 % Week-5-Snap-Anteilen. Das ist ein Formatvorteil im festen 2-TE-System. Keine automatische Folgerung, dass Fannin/Loveland abgegeben werden sollten: echte Rollen-/Security- und Angebotsbewertung folgt getrennt den Roster-Regeln.

## 8. Konkrete Week-6-Rechecks

1. **Shough/Penix/QB2:** Passing-Effizienz, Protection, Injury-/Matchup-News und verfügbaren Alternativenmarkt prüfen; Kirk Cousins nur als damals diskutierten Target-Impuls behandeln, nicht als tatsächlich im Roster befindlichen Spieler.
2. **Waddle/Wicks/Meyers/FLEX:** Playcalling-Hypothese anhand tatsächlicher Routes/Targets/High-Value-Usage verifizieren, 65 % Waddle-Snap-Share gegen 84 % Wicks und 85 % Meyers gewichten; final die komplette WR-/RB-FLEX-Boundary auswerten.
3. **Love/Brown/Skattebo:** Touch- und Snap-Verteilung sowie Third-Down-/Receiving-/Goal-Line-Arbeit ergänzen. Insbesondere Brown von 79 % auf 60 % untersuchen und Loves wiederholte 45–49 % korrekt in das Floor-Risiko übersetzen.
4. **Nabers/Pickens/McBride/Warren:** beobachtete hohe Usage in die nächsten Schätzungen aufnehmen, aber die Week-5-Ceiling-Punkte nicht mechanisch extrapolieren.
5. **Puka/Adams:** fehlende BUF@LA-Snap-/Target-/Route-Daten nachtragen, sobald verlässlich verfügbar; erst danach Week-5-Rollenvergleiche behaupten.
6. **AutoSub-Prozess:** Original-Startaufstellung, AutoSub-Zuordnungen/Prioritäten und Late-Swap-Timing künftig als periodenfesten Final-Lineup-Snapshot archivieren. **Verbesserungsvorschlag, noch keine freigegebene Regel-/Pipelineänderung.**

## 9. Lernentwicklung und Abschluss

- **Week 3:** 173,64 Punkte. Fokus auf McMillan/Skattebo-Startgrenze und erwartete Gegnerstärke statt nachträglichen Matchup-State.
- **Week 4:** 221,84 Punkte. Nabers-Sit nach Gegenprüfung nur noch als Grenzfall, nicht als eindeutiger Fehler; Adams' hoher Snap-Anteil trotz Puka verhindert vorschnellen Downgrade.
- **Week 5:** **232,10 Punkte**, Nabers startet **und** Adams bleibt; beide produzieren stark. Shough erlebt extrem negatives Outcome trotz modelliertem Startvorsprung, Waddle bleibt eine überprüfbare knappe WR-Boundary.

**Sportliches Gesamturteil:** **sehr stark** — zweiter Sieg in Folge, Week-5-Ligatopscore, Rang 3 bei 3–2, +31,98 gegen Jan.

**Prozessurteil:** **überwiegend gut mit konkreten Rechecks**. Das Einstellen von Nabers bei gleichzeitigem Behalten von Adams und der Einsatz von Puka/Pickens/McBride/Warren waren gut begründete Entscheidungen. Der QB2-Ausfall und die RB-Ergebnisse zeigen erhebliche Outcome-Varianz. Bei Waddle ist ein kritischerer Vorabvergleich gegen Wicks/Meyers angezeigt; aus einem Coaching-Narrativ folgt keine automatisch höhere reale Usage.

**Transparenz:** Das finale Scoring und 13 gewertete Starter sind gesichert. Best Ball ist legal anhand des rekonstruierten aktiven Rosters, aber streng **ex post**. Unvollständige Monday-NFL-Snaps, nicht archivierte AutoSubs und fehlendes gesiegeltes Pregame-Decision-Set bleiben gekennzeichnet. Dieses Review ersetzt keine historischen Entscheidungen und erzeugt **keine** automatische dauerhafte Roster- oder Regeländerung.
