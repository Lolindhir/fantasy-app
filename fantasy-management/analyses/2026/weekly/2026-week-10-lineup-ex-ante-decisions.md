# Mighty Giants — NFL Week 10 (2026): Ex-ante-Lineup-Entscheidungen gegen Jan

**Entscheidungs-/Capture-Cutoff:** Sonntag, **15.11.2026, 13:39:57 MEZ** (Europe/Berlin; die technische Datenprüfung erfolgte ca. 13:24–13:40 MEZ).  
**Partie:** Mighty Giants (Robert, TeamID 1; 4–5) gegen Mammoth Marauders (Jan, TeamID 4; 4–5).  
**Format:** sechs Teams, Full PPR, zwei feste QB-, RB-, WR- und TE-Plätze, **vier gemeinsame RB/WR/TE-FLEX**, ein Kicker; maximal drei AutoSubs laut League-Settings.  
**Status:** zeitgenössischer, ausdrücklich vom Nutzer zur Speicherung freigegebener **Ex-ante-Lineup-Record**, kein versiegelter generischer Decision Record, kein Postmortem und keine neue produktive Decision-Pipeline.  
**Ausführung:** Sleeper/League-Readmodel zeigt **genau die 13 unten genannten Starter**. Der Nutzer bestätigte die Aufstellung im Gespräch und verzichtete am 15.11. ausdrücklich auf Waiver-Claims. Diese Analyse nimmt selbst **keine** Sleeper-Transaktion vor.  
**Outcome-Firewall:** WAS @ NYG vom Donnerstag ist bereits abgeschlossen; seine Spieler sind zum hier dokumentierten Zeitpunkt gelockt. Die damalige *Thursday-Entscheidungsrationale* wird **nicht** aus dem bekannten Spielergebnis konstruiert. Alle Angaben zu ungespielten Partien sind als Pregame-Evidenz oder Prognosen zu verstehen.

## 1. Technischer Entscheidungsstand und Source-Linie

| Input, gelesen am 15.11.2026 vor dem nächsten relevanten Kickoff | Git-Blob-SHA / Stand |
|---|---|
| public/data/League.json | 519b51077c96133862455eae915851189ab9e165 |
| public/data/Matchups.json | 5143a9c22ca4f5d8ad0661bde1e28b1b299d25be |
| public/data/DecisionWindows.json | 51e29d5afe7521ed21f48df1a22c506aad39beaf |
| public/data/Schedule.json | 043af770446f85596a386e09bb470b3720548cd8 |
| public/data/PlayerWeekFantasy.json | b99a542fc9ae72c1175576574aad60066728bce4 |
| fantasy-management/generated/operations/managed-roster-signals.json | c70647af2c7d99592a85f46f3e14d9a68eb6baf6; generiert 15.11., 04:22:00 UTC |
| data-source/nfl/snap-counts/2026/06.json | e4f411286de5aae9a43dc827d9d9660b925e1257 |
| data-source/nfl/snap-counts/2026/07.json | 69c4ddd375f8756a1da7c06b8882b39613a725bf |
| data-source/nfl/snap-counts/2026/08.json | 4508434fba3de3c786d4e2bdfbc0148674e9e336 |
| data-source/nfl/snap-counts/2026/09.json | d1b9a68155966735084ab466be8a8a8773f8a476 |

**Liga-Status am Cutoff:** Week 10 offen; TeamID 1 mit **13/13 Starterplätzen** und identischer Starterliste in League.json und DecisionWindows; Roster 37 kontrollierte Spieler, 30/30 aktive Plätze, 5/5 Reserve und 2/2 Taxi (Taxi-Lock bindend). Das App-Matchup zeigt **57,36 : 0,00** nach dem Thursday-Spiel bei noch nicht vergleichbarer Zahl abgeschlossener Starter. Diese Rohpunktzahl ist **kein** unabhängig kalibrierter Vorhersagevorsprung oder Grund für automatisches „Floor-Only“-Spiel.

**Zeitgrenzen:** Bereits am 13.11. um 02:15 MEZ (Thursday US) liefen Daniels, Nabers und Skattebo auf. NE @ DET beginnt am Sonntag **15:30 MEZ**, betrifft aber keinen startbaren Mighty-Giants-Spieler. Die erste für uns noch offene Entscheidung ist der **19:00-MEZ-Lock** am Sonntag (Mahomes, Hall, McMillan, Warren, Fannin, Fairbairn und Bench-Alternativen wie Meyers/Sampson). Später folgen McBride **22:05**, Pickens **22:25** und Chase Brown/Bernard **Montag 02:20 MEZ**. Der späte Bernard-Lock schafft **keine** automatische Rückgriffsmöglichkeit auf Meyers, sobald Meyers am Sonntag um 19:00 Uhr gelockt ist.

## 2. Aktuell tatsächlich gespeicherte Startaufstellung

| Slot | Spieler | Sleeper-ID | Matchup / Status am Capture |
|---|---|---:|---|
| QB1 | Patrick Mahomes | 4046 | KC @ ATL; Sonntag 19:00; verfügbar |
| QB2 | Jayden Daniels | 11566 | WAS @ NYG; Donnerstag bereits gespielt, gelockt |
| RB1 | Cam Skattebo | 12481 | NYG vs WAS; Donnerstag bereits gespielt, gelockt |
| RB2 | Breece Hall | 8155 | NYJ vs BUF; Sonntag 19:00; verfügbar |
| WR1 | George Pickens | 8137 | DAL vs SF; Sonntag 22:25; Final Practice Full, keine Game-Designation |
| WR2 | Malik Nabers | 11632 | NYG vs WAS; Donnerstag bereits gespielt, gelockt |
| TE1 | Tyler Warren | 12518 | IND vs MIA; Sonntag 19:00 |
| TE2 | Trey McBride | 8130 | ARI vs LAR; Sonntag 22:05 |
| FLEX1 | Chase Brown | 9224 | CIN vs PIT; Montag 02:20 |
| FLEX2 | Tetairoa McMillan | 12526 | CAR @ NO; Sonntag 19:00 |
| FLEX3 | Harold Fannin Jr. | 12506 | CLE vs HOU; Sonntag 19:00; Full Practice, keine Game-Designation |
| FLEX4 | Germie Bernard | 13274 | PIT @ CIN; Montag 02:20 |
| K | Ka'imi Fairbairn | 3451 | HOU @ CLE; Sonntag 19:00 |

Die Sleeper-Slotreihenfolge folgt dem tatsächlichen **League.json → Teams[TeamID=1].Starter**. Es sind zwei QB + zwei RB + zwei WR + zwei TE + vier FLEX + ein K. **Kein Waiver-Move** wurde ausgeführt oder als Bedingung des Lineups angenommen.

**Begründete Änderungen seit dem vorherigen Set:** George Pickens für Puka Nacua (NFL-IR); Breece Hall für Kenneth Walker III (für KC @ ATL offiziell **Out**, Leiste); Germie Bernard für den durch die Slot-Umstellung frei gewordenen vierten FLEX. Hall wurde **nicht** als Recovery- oder Role-Lock zu 100 % angenommen; entscheidend ist der verfügbare Ersatz gegenüber dem sicheren Walker-Ausfall. Pickens' gesundheitliche Freigabe ist eine **Verfügbarkeitsinformation**, keine Garantie für vollständige frühere Produktion.

## 3. Tatsächlich konsultierte externe Pregame-Evidenz

**Capture-Zeit:** öffentlich abrufbare Zeilen am **15.11.2026, ca. 13:34–13:40 MEZ**, vor dem 19:00-Uhr-Lock und vor PIT @ CIN. Alle nachfolgenden Quellen zu noch ungespielten Spielen haben Evidenzstatus **pre_lock_captured**, sofern nicht ausdrücklich anders angegeben. Veröffentlichungs-/Update-Zeit unbekannt, falls nicht direkt auf der jeweiligen Quelle angegeben. Dynamische Seiten können sich nach dem Capture ändern; es wird **keine** unveränderliche Webversion/HTML-Kopie im Repo behauptet.

| Quelle (Typ) | Angezeigte Veröffentlichung / Status | Konkret gelesene Zeilen und Bedeutung |
|---|---|---|
| [NFL.com Week-10-Injury-Report](https://amp.nfl.com/news/nfl-week-10-injury-report-2026-season), offiziell | veröffentlicht im Week-10-Vorfeld; konkrete Quellenrevision nicht ausgewiesen | **Kenneth Walker III: OUT** (groin); **Marvin Harrison Jr.: OUT**; Sonntag noch finalen Inactive-Status revalidieren. |
| [NFL.com offizieller Injury-Report (REG10)](https://www.nfl.com/injuries/league/2026/REG10), offiziell | dynamische Woche-10-Seite, Updatezeit nicht sicher bestimmt | **George Pickens: Full Participation, keine Game-Designation**; **Harold Fannin Jr.: Full Participation, keine Game-Designation**. |
| [NBC Sports / Nic Bodiford, Pickens cleared](https://www.nbcsports.com/fantasy/football/player-news/2026-11-13/george-pickens-hamstring-cleared-to-face-49ers), Injury-/Rollenbericht | 13.11.2026 | Pickens nach Hamstring-Woche erneut startbar, Einordnung ungefähr WR2, aber Rückkehr nach Ausfall birgt Restunsicherheit. |
| [Cory Bonini, Athlon Week-10 PPR FLEX Rankings](https://athlonsports.com/fantasy/fantasy-football-flex-ppr-rankings-2026-nfl-week10), **gemeinsame RB/WR/TE-PPR-FLEX-Liste** | **14.11., 20:52 EST** (15.11., 02:52 MEZ) | **McMillan 10**, **Warren 41**, **Chase Brown 43**, **Pickens 48**, **Fannin 49**, **Meyers 55**, **Hall 72**, **Bernard 73**, **Sampson 117**. Diese unabhängige Liste sieht ausdrücklich **Meyers vor Bernard** und ist ein ernstzunehmender Widerspruch zum gewählten FLEX4. |
| [Steelers.com / Matt's Stats: Week 10 at Bengals](https://www.steelers.com/news/matt-s-stats-week-10-at-bengals), offizieller Team-/Usage-Bericht | circa 12.11.2026; genaue Updatezeit unbekannt | Bernard zuletzt Target Shares von **30/27/18/23 %** in vier Spielen, durchschnittlich **7,5 Targets**, circa **51,5 % Slot-Anteil**; viel YAC; gegenüber früher deutlich gewachsene Rolle. |
| [Rich Hribar, Sharp Football: PIT @ CIN Week 10](https://www.sharpfootballanalysis.com/fantasy/steelers-bengals-week-10-fantasy-football-preview-nfl-worksheet-rich-hribar-2026/amp/), unabhängige Usage-/Matchup-Analyse | circa 11.11.2026; genaue Updatezeit unbekannt | Bernard **21 % Targets pro Slot-Route**, **1,76 Yards/Slot-Route**, **4,8 Air Yards/Target**, **21,4 % Screens**; Bengals lassen **10,6 Yards/Slot-Target** zu, viel Passing über Mitte. Positiver Floor-WR3-Case, aber Tiefenprofil limitiert Upside. |
| [Derek Brown, FantasyPros Fannin Week-10 Outlook](https://www.fantasypros.com/nfl/notes/493115/harold-fannin-jr-2026-week-10-outlook.php), individuelle Expertenanalyse | **12.11., 13:35 EST** | **Sit** trotz 17,7 % Target Share und 1,68 YPRR: Houston erlaubte TEs zuletzt extrem wenig Yards/Target und Punkte/Opportunity. Explizit **kritischer Gegenbeleg** zu Fannin-FLEX. |
| [Ellis Johnson, FantasyPros Fannin Week-10 Outlook](https://www.fantasypros.com/nfl/notes/493024/harold-fannin-jr-2026-week-10-outlook.php), andere individuelle Expertenanalyse | **11.11., 18:36 EST** | Fannin in zwei Watson-Spielen mit **9 bzw. 12 Targets**; bei ähnlicher Nutzung trotz Houston startbarer TE, aber letzte Partie nur zwei Catches. **Nicht** als unabhängige FantasyPros-Konsensstimme doppelt zählen. |
| [Derek Brown, FantasyPros Meyers Week-10 Outlook](https://www.fantasypros.com/nfl/notes/493227/jakobi-meyers-2026-week-10-outlook.php), individuelle Expertenanalyse | **13.11., 20:35 EST** | **Meyers FLEX-tauglich**, 15,9 % Target Share, 2,02 YPRR, 19 % First-Read-Share; Tennessee zuletzt sehr großzügig gegen Perimeter-WR. Matchup-Faktor **pro Meyers**. |
| [FantasyPros Week-10 Primer](https://www.fantasypros.com/2026/11/the-primer-week-10-edition-2026-fantasy-football/), Start/Sit-Analyse | circa 14.11.; Updatezeit nicht genau belegt | Behandelt Fannin wegen Houston zurückhaltend; ist nicht unabhängig von Derek Browns FantasyPros-Analyse. |
| Stoned Lack Folge 608 „Überdosis Woche 10“ (vom Nutzer bereitgestelltes Transkript **Eingefügter Text(2).txt**, Projektdatei ohne verifizierten GitHub-Quellpfad), Nutzermaterial als Podcast-Perspektive | Transkript vom Nutzer bereitgestellt, Zeitmarken unten; exakt datierter Publikationsstand nicht belegt | **Meyers eher Sit** wegen erwartetem JAX-Führungsspiel/Run-Game-Script gegen TEN; **Fannin FLEX** trotz schwerem Houston-TE-Matchup und Watson-Checkdowns; **Bernard** kontrovers: Matchup-freundlicher Host vs. Host mit deutlichem Targetvolumen-Floor-Einwand. Das ist keine unfallfreie, verifizierte vollständige Ranking-Tabelle. |
| Stoned Lack „Aftermath Woche 10“, Nutzermaterial **Eingefügter Text(4).txt** | vom Nutzer am 14.11.2026 bereitgestellt | Pickens vom Podcast-Host auf **WR19** verbessert; Bernard **herabgestuft**, exakter neuer Rang im ASR-Transkript unbekannt. Das macht Bernard zum bewussten Grenzfall. |

**Stoned-Lack-Primärstellen aus den bereitgestellten Transkripten (ASR-verrauscht, wortlautkonservative Interpretation):** Folge 608 circa **17:34–20:15** (JAX-Game-Script/Meyers), **49:51–50:20** (Fannin), **1:34:27–1:37:15** (Bernard-Dissens); „Aftermath“ **26:30–27:20** (Pickens) und **29:23–29:43** (Bernard nach unten). Stoned Lack dient als **identifizierte Expertenmeinung**, nicht als unabhängige Spiel- oder Resultatstatistik.

**Quellenabhängigkeit:** FantasyPros-Derek-Brown-Fannin-Note und FantasyPros Primer dürfen nicht als zwei unabhängige Stimmen gezählt werden. Athlon (Bonini), Steelers.com (Team-Usage), Sharp (Hribar), NFL.com (Injury) und die individuellen Podcast-Hosts sind getrennte Publikationsperspektiven; die gleichen ursprünglichen NFL-Ereignisse können trotzdem dieselbe Datenbasis haben.

## 4. Vergleichbare Usage-Evidenz, offene Datenfelder und Grenzpool

**Historisch im Repository enthaltene Offense-Snapanteile (nflverse; Werte sind ausdrücklich **keine** Routes oder Targets):**

| Spieler | W6 | W7 | W8 | W9 | Ex-ante-Folgerung |
|---|---:|---:|---:|---:|---|
| **Germie Bernard (PIT WR)** | 74 / **94 %** | 58 / **91 %** | 50 / **85 %** | kein Beleg im abgefragten Snap-Slice | Hohe, recht gleichmäßige Beteiligung; alleine kein garantierter Target-Floor. |
| **Jakobi Meyers (JAX WR)** | 53 / **75 %** | kein Beleg im abgefragten Snap-Slice | 29 / **54 %** | 38 / **68 %** | Geringere/volatilere Einsatzzeit; Matchup gegen TEN kann dies nicht automatisch kompensieren. |
| **Dylan Sampson (CLE RB)** | nicht erhoben | 32 / **46 %** | 39 / **56 %** | 47 / **64 %** | Deutlich wachsender Einsatz, aber nicht nachgewiesener Lead-Back-Einsatz. |
| **Tetairoa McMillan (CAR WR)** | 60 / **76 %** | 38 / **68 %** | 65 / **89 %** | 53 / **80 %** | Mehrwöchige hohe Participation im Starterpool. |

Ein „kein Beleg“ in einem abgefragten Snap-Slice ist **keine nachgewiesene Null, Verletzung oder Bye**. Für Fannin sind exakte gleiche-Wochen-Offense-Snaps/Routes in dieser Erhebung **nicht sauber belegt**; stattdessen liegen explizite Targets/Share/YPRR aus den genannten externen Analysen vor. Kein Einsetzen von erfundenen Routes, Targetzahlen oder Waiver-Status. Alle berechneten PPR-Werte unten sind **Projektionen**, keine gemessenen Oppor­tunities.

**Dreiergrenze für zwei FLEX-Starts, nach gemeinsamer Bewertungslogik:**

| Kriterium | Harold Fannin Jr. (CLE vs HOU) | Germie Bernard (PIT @ CIN) | Jakobi Meyers (JAX @ TEN) |
|---|---|---|---|
| Letztes belegtes Rollenbild | 17,7 % Target Share; Watson-Spiele mit 9/12 Targets; letzte Partie mit nur 2 Targets/Catches | Sehr viel Snap-Beteiligung, 7,5 Targets/Spiel im aktuellen Vier-Spiele-Fenster; Slot-/YAC-Rolle | 15,9 % Target Share, 2,02 YPRR; zuletzt 54 und 68 % Snapanteil |
| Matchup | **Schwer:** HOU stark gegen TE-Targets/TE-Fantasy-Opportunity | **Gut:** CIN anfällig gegen Slot-/In-Breaker-/YAC-Profile | **Gut:** TEN schwach gegen Perimeter-WR |
| Gegenargument / Downside | Watson-Role-Abhängigkeit; Texans reduzieren TE-Effizienz, 2-Target-Ausreißer möglich | Kurze Targettiefe 4,8 ADOT; hoher PPR-Floor **nur**, wenn ausreichend Targets wirklich kommen; Hosts gespalten | Jaguars können bei erwarteter klarer Führung Passvolumen senken; schwankende jüngste Snaps; zuletzt Knöchel im Practice Report, aber keine Game-Designation |
| Expertenkonflikt | Athlon FLEX49; FantasyPros Brown „Sit“, Johnson positiv unter Bedingung höherer Targets; Stoned Lack FLEX | Athlon FLEX73, nach Stoned Lack „Aftermath“ abgewertet; Sharp positiv wegen Slot-Matchup | Athlon FLEX55, **vor Bernard**; FantasyPros „FLEX-tauglich“; Stoned Lack eher Sit wegen Game Script |
| Entscheidung | **START** (moderate Konfidenz) | **START** (niedrig–moderat; knapper Grenzfall) | **BENCH** (plausible Reversal-Alternative) |

**Erwartungswert-Kontext aus aktueller App-V4-C-Quelle (nutzerspezifische Scoringbasis, Week10):** Fannin **11,51**, Bernard **9,58**, Meyers **9,33**, Sampson **10,29** Punkte; Pickens **13,24**, McMillan **14,92**, Hall **12,83**. Der PWF-Record ist im Status „conditional on participation“, **ohne** zuverlässige Injury-Verfügbarkeitskorrektur. Daraus folgt keine automatisierte Startentscheidung, insbesondere keine Cross-Position-Dominanz durch 0,25 Punkte Bernard-vs.-Meyers. Für die **bereits absolvierten** Thursday-Starter ist die gegenwärtige PWF-Projektion **keine zeitkonforme alte Pregame-Prognose**.

### 4.1 Warum trotz Kontroverse Fannin + Bernard?

- **Fannin:** Attraktive belegte Rolle in Cleveland, Watson nutzt ihn als Kurzpass-/Outlet-Option, eigenes TD-/YAC-Ceiling. Die schwierige Houston-Defense ist ein **echter** Contra-Punkt und wird weder mit seinem TE-Ranking noch mit einem Stone-Luck-Score wegdefiniert.
- **Bernard:** Gegen Cincinnati passen Slots, kurze Receptions und YAC zum Matchup; die Spielzeit war zuletzt hoch. Es wäre aber **falsch**, die Snaps als Garantie von sechs bis sieben Catches zu deklarieren. Stoned Lack mahnt zu Recht einen schwachen Floor bei weniger als vielen Targets an; seine spätere Podcast-Herabstufung wird im Entscheidungsstand festgehalten.
- **Meyers:** Sehr gute Tennesse-Schwäche gegen Outside-WR; bei regulärer Passing-Volume ist er eine ernsthafte Alternative mit glaubwürdigem zweistelligem PPR-Ergebnis. Seine zuletzt wechselnde Einsatzquote und das von Stoned Lack skizzierte mögliche dominante JAX-Game-Script sprechen gegen die Behauptung „sicherster Floor“.
- **Entscheidungsmarge:** **Knapp**, nicht robust. Athlon bevorzugt Meyers klar vor Bernard; die gewählte Bernard-Präferenz beruht auf anderer Gewichtung von *jüngster Opportunity und Slot-Fit*. Bei neuem, belastbarem Injury-/Role-/Target-Kontext vor den relevanten Locks neu bewerten. Das ursprüngliche Urteil dabei als Zeitstand erhalten, nicht umschreiben.

**Nutzerpräferenz/Bestätigung:** Robert hinterfragte mehrfach, ob Meyers nicht sicherer sei, verlangte den Stoned-Lack-Gegencheck und bestätigte nach der ausführlichen Abwägung die gespeicherte Fannin/Bernard-Variante. **Ein persönlicher numerischer Confidence-Score oder expliziter alternativer Risikogrenzwert wurde nicht abgefragt oder behauptet.** Die textliche Konfidenz ist die fachliche Assistentenbewertung, keine nachträglich erfundene Nutzerzahl.

### 4.2 Die vier FLEX zusammen und übrige Bank

**FLEX-Portfolio:** Chase Brown + Tetairoa McMillan + Harold Fannin Jr. + Germie Bernard. Brown/McMillan besitzen klare Startargumente, Fannin/Bernard tragen unterschiedliche receiving-abhängige Risikoquellen. In einer 6-Team-/4-FLEX-Liga ist **Beteiligung/Expected Opportunity plus Matchup** wichtiger als ein schematisches „RB immer vor TE“. Hohe gemeinsame Catchabhängigkeit ist eine **qualitative** Risikoüberlegung, keine geschätzte Korrelation.

**Reale aktive Bench-Konkurrenz:** Meyers (engster Start/Sit-Grenzkandidat); Dylan Sampson (wachsende CLE-Snaps, Receiving-/Game-Script-Chance, aber noch keine bestätigte Premium-Touchrolle); Michael Penix Jr. und Tyler Shough (2QB, aber Mahomes+gelockter Daniels bevorzugt); Ladd McConkey (Questionable, später Monday-Lock, unsichere aktuelle Rolle); Brian Thomas Jr. (starker Rolleinbruch), Travis Hunter (überwiegend Defense-Einsatz), Seth McGowan (Colts-RB2/Contingency). **Bye:** Saquon Barkley, D'Andre Swift, Colston Loveland, Jaylen Waddle/Kyle Monangai. **Out:** Kenneth Walker III, Marvin Harrison Jr.; **IR:** Puka Nacua, Jeremiyah Love. Weitere Reserve-Spieler (Dart, Brooks, Stribling, Adams, Pierce) und gelockte Taxi-Spieler (Antonio Williams, Chris Bell) sind nicht als sofort startbare Alternativen behauptet.

**QB:** Mahomes bleibt über Shough/Penix aufgrund plausibler Start-/Passrollen-Evidenz und mehreren besprochenen externen QB-Rankings; Daniels bereits gelockt. **TE-Pflicht:** McBride und Warren klarer als die externen mittleren verfügbaren Alternativen; Fannin nutzt einen FLEX, nicht einen erfundenen dritten TE-Pflichtslot. **Kicker:** Fairbairn halten; ein Streaming-Wechsel ist weder durchgeführt noch durch einen nachweisbaren materiellen Vorteil inklusive Drop-Kosten begründet.

## 5. Decision-Opportunity-Matrix und Handlungsschranken

| Zeit (MEZ) | Zustand / rechtlich mögliche Anpassung | Geplante Handlung |
|---|---|---|
| Freitag, **13.11. 02:15** | WAS @ NYG bereits final: Daniels, Nabers und Skattebo gelockt | **Kein** nachträglicher Thursday-Start/Sit; Resultate nur getrennt als bereits bekanntes Matchup-Signal |
| Sonntag, **15.11. 13:39:57** | 13 Starter korrekt in League.json/DecisionWindows, keine Waiver-Änderung | **Diesen Ex-ante-Record archivieren** |
| Sonntag **15:30** | NE @ DET München; keine für Mighty Giants gelockten aktiven Starter | Keine Spieler aus diesem Kickoff als aktuelle Optionen konstruiert |
| Sonntag **ca. 17:30–19:00** | Offizielle Inactives und unerwartete Practice-/Role-Ereignisse für 19-Uhr-Spiele | **Letzter Recheck** zu Fannin, Meyers, Hall, Warren, McMillan, Mahomes, Fairbairn, Sampson. Falls materielles Delta: neuer datierter Ex-ante-Zusatz, nicht heimliches Rewrite |
| Sonntag **19:00** | Fannin, Meyers, Sampson und mehrere feste Starter/Alternativen werden gelockt | Fannin starten; Meyers/Sampson bleiben auf der Bank; Bernard-Entscheidung durch Wegfall von Meyers als späterer Ersatz faktisch präjudiziert |
| Sonntag **22:05/22:25** | McBride und Pickens eigene, spätere Locks | Spätere Inactives prüfen; Pickens nach Hamstring-Rückkehr kein garantiert voller Workload |
| Montag **02:20** | Chase Brown und Bernard; verbleibende Start/Sit-/AutoSub-Fragen nur mit legalen, noch nicht gelockten Spielern | Vorerst beide Start; keinen nicht verifizierten Late-Swap-Ersatz behaupten |
| Dienstag **02:15** | LAC @ BAL; McConkey Questionable, aktueller Bench | Nicht rückwirkend als sichere Bernard-Ausfallversicherung behaupten |

**AutoSubs:** Liga erlaubt maximal drei, aber **konkrete Paarungen/Prioritäten/Trigger sind in der abgerufenen Starterliste nicht bestätigt**. Status ausdrücklich **unconfirmed**; keine fiktive Sicherung oder AutoSub-Ausführung. Auch ein **active-but-limited**-Spieler wird nicht allein wegen geringer Snaps durch Inactive-Only-Logik ersetzt.

## 6. Ex-ante-Testthesen und spätere Review-Fragen

1. **Fannin-Hypothese:** Browns-Passing mit Watson gibt ihm trotz schwieriger Texans-TE-Defense eine relevante Receiving-Opportunity. Prüfung: tatsächliche Routes/Targets, QB-Verteilung, Fannin-Points; Entscheidung nicht allein an TD-/Endscore messen.
2. **Bernard-Hypothese:** regelmäßige Routes/Slot-Targets plus Bengals' Innen-/YAC-Anfälligkeit machen ihn knapp besser als Meyers. Prüfung: Target-Share, Receptions, Slot-Aufteilung, Spielverlauf, Steelers-Team-Passvolumen und Vergleich zur Same-Information-Alternative.
3. **Meyers-Gegenhypothese:** Titans-Matchup könnte trotz niedrigerer jüngerer Snaps ein höheres Zielvolumen/mehr PPR-Punkte erzeugen; Jaguars könnten aber durch frühen Vorsprung passen reduzieren. Prüfung: Routes, Targets, Jacksonville-Passrate *nach Spielständen*, nicht bloß Ergebnis.
4. **Pickens-Verfügbarkeitsrisiko:** medizinisch freigegeben ≠ garantierter voller Snap-/Route-Anteil. Prüfen gegen mögliche Comeback-Beschränkung und späteren Lock.
5. **Walker/Puka-Pflichtwechsel:** tatsächliche offiziellen Ausfälle rechtfertigen vor dem Spiel den Positionswechsel; Scores des Ersatzes sind **Outcome**, kein Beleg für fehlerfreie ursprüngliche Risikoannahmen.
6. **Portfolio-Review:** Gegen Jan die tatsächlich wirksam gewerteten 13 Starter, etwaige AutoSubs, rechtlich verfügbare Alternativen und den Status der vier Datenfinalitäts-Ebenen getrennt ausweisen. Keine Best-Ball-Oracle-Auswahl als angeblich offensichtliche Ex-ante-Entscheidung.
7. **Externe Rangdivergenz:** Athlon sah Meyers 18 FLEX-Ränge vor Bernard; unsere begründete Abweichung wird bei der Same-Information-Prozessprüfung explizit erneut geprüft, ohne nachträglich den späteren Sieger zur Originalpräferenz zu machen.

**Bedingungen für eine spätere Revision:** neue offizielle Inactive-/Injury-Nachrichten, verifizierte Rolle, Starting-QB-Änderungen, tatsächliche AutoSub-Legalität. Ein **neues, datiertes Addendum** mit Delta und Bestätigungsstatus ist erforderlich; dieses eingefrorene Ex-ante-Dokument bleibt ein zeitgebundener Snapshot.

**Keine Änderungen** an Starterbelegung, Waiver, Salary, V4-C, Stone Luck Score, League-Regeln oder Actions. Spätere Outcomes ausschließlich in eine getrennte Week-10-Postmortem-Datei. **Tracking:** vorhandenes GitHub-Issue #206 (manuelle Weekly-Ex-ante-Dokumentation; spätere Workflow-Operationalisierung bleibt separat offen).
