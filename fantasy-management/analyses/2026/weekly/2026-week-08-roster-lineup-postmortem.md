# Mighty Giants — Week 8 2026: Roster + Lineup Postmortem (Ex-ante-Expertenabgleich)

**Rekonstruktion:** 03.11.2026 nach Finalisierung der Fantasy-Istwerte; NFL Week 8 vom 29.10.–02.11.2026.  
**Team:** Mighty Giants / Robert (TeamID 1; CanonicalLeagueRosterID `clr-a8e576139994570d82e9ea2ed3f42b1b`).  
**Gegner:** Marcel / Ruhr Valley Packers (TeamID 2).  
**Ergebnis:** **164,92 : 177,06** — Niederlage mit **12,14 Punkten**; danach 4–4, Tabellenplatz 4/6.  
**Format:** 6 Teams, Full PPR; 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K.  
**Typ:** retrospektive Analyse unter ausdrücklicher Nutzerfreigabe; **kein versiegelter Decision Record**. Die vor dem Spiel dokumentierte Ex-ante-Entscheidungsakte wird **nicht** überschrieben.  

> **Methodische Korrektur gegenüber der vorläufigen Chat-Auswertung:** Ein hoher Bench-Score oder ein Fehlbetrag gegenüber unserem V4-C-Modell ist kein Ex-ante-Prozessfehler. Für die entscheidenden FLEX-/TE-Grenzen wird zuerst die *damals erkennbare* Experten-, Rollen- und Verletzungsevidenz verglichen. Erst danach folgen Same-Information-Re-Decision, Resultat, Modellkalibrierung und neue Usage-Erkenntnisse. Insbesondere lässt sich aus Fannins 23,40 Punkten **kein offensichtlicher Startanspruch** ableiten.

## 0. Evidenzhierarchie, Zeitstabilität und Grenzen

1. **League/Scoring (primär):** `data-source/leagues/nfl-reise/seasons/2026/matchups/week-8.json`, `public/data/Matchups.json` (`CompletionState=final`) und `public/data/League.json` (`FinalScoredWeek=8`). 13 gewertete Mighty-Giants-Starter ergeben exakt **164,92** Punkte, Gegner **177,06**.
2. **Ex ante (primär für Entscheidungsgüte):** die auf dem separaten, noch **offenen PR #1276** gesicherte Datei `fantasy-management/analyses/2026/weekly/2026-week-08-lineup-ex-ante-decisions.md` (Branch `docs/week-08-ex-ante-lineup-2026`); sie konserviert die tatsächliche Dialog- und Entscheidungskette vom 29.10.–01.11., aber **keinen vor allen Week-8-Spielen atomar eingefrorenen Snapshot**. Ex-ante-Felder werden nicht retrospektiv ergänzt oder verändert. Referenz: https://github.com/Lolindhir/fantasy-app/pull/1276
3. **Transaktionen/Eligibility:** `data-source/leagues/nfl-reise/seasons/2026/transactions/week-8.json` und historischer Matchup-Spielerpool. Der tatsächlich erfolgreiche Kicker-Waiver Little für Fairbairn wurde am 29.10. eingereicht und am **01.11. um 12:05 MEZ** abgeschlossen; weitere Mighty-Giants-Claims ohne Drop scheiterten an der Rostergröße. Historische Taxi-/Reserve-Zuweisungen und AutoSub-Paarungen sind nicht vollständig als separate Lock-Snapshots archiviert; spätere aktuelle Roster-Readmodels dienen **nicht** als rückwirkend beweiskräftige Eligibility.
4. **Externe zeitgenössische Expertensignale:** vor dem relevanten Sonntag-Lock veröffentlichte Quellen, einzeln dokumentiert unter Abschnitt 4. Veröffentlichungsdatum ist nicht gleich revisionssicherem Zeitpunkt jeder sichtbaren Ranglistenzeile. Rankings ohne nachweisbare Pregame-Revision werden nur eingeschränkt als historisches Indiz genutzt; nach Kickoff aktualisierte Rankings sind keine damalige Entscheidungsbasis.
5. **Outcome und Modell (nicht primär für Start/Sit):** `data-derived/team-week-performance/nfl-reise/2026/08.json` bestätigt das rekonstruierte Hindsight-Optimum **208,12** (79,2427 % Effizienz, 43,20 Punkte Abstand); `data-derived/player-week-fantasy/nfl-reise/2026/08.json` V4-C, 726/726 `Actual.State=final`, `ActualScoringEvidenceFinalized=true`, aber `TargetWeeklyRosterFinalized=false`. Die internen Wochenprojektionen sind **experimentelle Diagnosedaten**, kein nachgewiesener damaliger vollständiger Pregame-Expertenkonsens.
6. **Usage:** `data-source/nfl/snap-counts/2026/07.json` und `08.json`. In Week 8 sind 14 NFL-Spiele und 1.311 Spielerrecords enthalten, aber `Finalized=false`. Die Wochen-Spiel-Finality ist 14/14. Snap Share belegt nicht automatisch Route Participation/Target Share; diese Größen dürfen nicht vermischt werden.
7. **Cross-Source-Test:** Alle 78 gewerteten Starter der sechs Liga-Teams besitzen identische finale League-Matchup- und V4-C-Actual-Punkte. Für die Mighty Giants stimmen sämtliche 13 Starter und die wesentlichen punktenden Bankalternativen überein; inaktive/Taxi-/Bye-Nullspieler ohne Derived-Zeile sind nicht als Scoring-Widerspruch zu zählen.

**Outcome-Firewall:** Sofern unten nicht als nachweisliche Information zu einem früheren Kickoff markiert, sind neue Verletzungen, Week-8-Scores, Week-8-Targets/Snaps und Hindsight-Optimum *erst nach den Entscheidungen bekannt* und werden nur für Ergebnisse, Kalibrierung und spätere Weekly-Rechecks verwendet. Ein Online-Artikel, der vor dem Spiel erschien, aber später verändert worden sein könnte, gilt ohne Archiv nicht als unangreifbar eingefrorene damalige Einzelrankings.

## 1. Finaler Spieltag und Starter

| Slot | Spieler | Final Ist | Archiviertes V4-C | Differenz Ist − V4-C |
| --- | --- | ---: | ---: | ---: |
| QB1 | Patrick Mahomes | 25,44 | 17,79 | +7,65 |
| QB2 | Jayden Daniels | 14,98 | 20,70 | −5,72 |
| RB1 | Chase Brown | 16,10 | 13,39 | +2,71 |
| RB2 | Kenneth Walker III | 12,40 | 23,44 | −11,04 |
| WR1 | Tetairoa McMillan | 11,80 | 14,82 | −3,02 |
| WR2 | Puka Nacua | 25,00 | 22,57 | +2,43 |
| TE1 | Trey McBride | 20,20 | 18,51 | +1,69 |
| TE2 | Colston Loveland | 11,50 | 9,31 | +2,19 |
| FLEX | George Pickens | 6,80 | 13,78 | −6,98 |
| FLEX | Jeremiyah Love | 2,30 | 9,98 | −7,68 |
| FLEX | Saquon Barkley | 12,40 | 8,01 | +4,39 |
| FLEX | Tre Tucker | 0,00 | 12,66 | −12,66 |
| K | Cam Little | 6,00 | 9,31 | −3,31 |
| **Gesamt** | | **164,92** | **194,27** | **−29,35** |

Die vier FLEX-Starter erzielten zusammen **21,50 Punkte**, gegenüber **44,44** modellierten Punkten. Die **−22,94** sind ein Modell-/Ergebnisresiduum, kein Beleg für eine ex ante vermeidbare 22,94-Punkte-Entscheidung. Mahomes/Puka/McBride und die festen TE-Slots waren überzeugend; Walker enttäuschte trotz hoher Einsatzquote.

**Liga-Kontext:** Scores aller sechs Teams: 258,88 / 184,00 / 177,06 / 175,58 / **164,92** / 136,46. Mighty Giants mit dem **fünfthöchsten** Wochenscore. Der 4–4-Record bedeutet Platz 4/6 und weiterhin einen Playoff-Platz.

## 2. Historischer Bank- und Hindsight-Vergleich

| Aktive, nicht gewertete Alternative | Punkte Week 8 | V4-C-Modellwert | Ex-ante-Relevanz |
| --- | ---: | ---: | --- |
| Harold Fannin Jr. (TE) | **23,40** | 10,18 | Relevanter TE3-/FLEX-Grenzfall; externe Experten widersprechen sich |
| Jaylen Waddle (WR) | **14,90** | 9,01 | Talent-/Target-Upside, vor dem Spiel Brust-/Availability-Risiko |
| Dylan Sampson (RB) | **12,90** | 8,98 | RB-Entwicklung, ex ante relativ niedrige Experteneinstufung |
| Ladd McConkey (WR) | **12,60** | 8,43 | Plausible und dokumentiert diskutierte gesunde FLEX-Alternative |
| Brian Thomas Jr. (WR) | 8,20 | 5,25 | Niedrige damalige Startpriorität |
| Germie Bernard (WR) | 8,00 | 9,60 | Usage plausibel, aber schwankende Produktion |
| Tyler Warren (TE) | 5,80 | 13,55 | Comeback nach Leistenproblemen; direkter TE2-/FLEX-Vergleich |
| Jakobi Meyers (WR) | 4,40 | 10,48 | Verletzungs-/Role-Risiko |
| Seth McGowan (RB) | 2,90 | 3,59 | Stash/Backup, kein regulärer Start |
| Michael Penix Jr. (QB) | 2,10 | 16,69 | Gegenüber beiden QB-Starterkandidaten nachrangig |
| Travis Hunter (WR) | 0,50 | keine verfügbare Projektion | Prospect; kein aktueller Startanspruch |

Die bei späterem Roster-Readback auf Taxi geführten Antonio Williams (10,40) und Chris Bell (6,90) werden **nicht** als unproblematisch legale FLEX-Alternativen behandelt. Reserve-, Bye- und Inactive-Spieler sind ebenfalls keine automatischen Bench-Starts.

**Das veröffentlichte TeamWeekPerformance-Optimum** lautet: Mahomes 25,44; Daniels 14,98; Brown 16,10; Sampson 12,90; Nacua 25,00; Waddle 14,90; Fannin 23,40; McBride 20,20; McConkey 12,60; Barkley 12,40; Walker 12,40; McMillan 11,80; Little 6,00 = **208,12**. Es ersetzt keine unabhängig attestierte historische Lock-/Taxi-Legalität und keine mögliche Vorabentscheidung.

Rein **rechnerische Ex-post-Swaps**: Fannin statt Tucker +23,40 (188,32, Sieg); Fannin statt Love +21,10 (186,02, Sieg); Fannin statt Pickens +16,60 (181,52, Sieg); Waddle statt Tucker +14,90 (179,82, Sieg); Sampson statt Tucker +12,90 (177,82, Sieg); McConkey statt Tucker +12,60 (177,52, Sieg). **Keiner dieser hypothetischen Punktegewinne ist automatisch Decision Regret.** Der historische Lock- und Intent-Nachweis ist gesondert zu führen.

## 3. Chronologische Decision-Opportunity-Matrix

| Fenster / MEZ (soweit belegt) | Damals bekannter oder belegter Zustand | Bewertungsgrenze |
| --- | --- | --- |
| Do 29.10., vor CAR@GB | McMillan war Starter; vor seinem Kickoff keine Week-8-Punkte bekannt. | Seine späteren 11,80 Punkte und Rankings, die erst Samstag erschienen, sind **keine** Ex-ante-Prognose für die Donnerstagentscheidung. |
| 29.–31.10. | Loveland leicht vor Warren; vorübergehend dritter TE Warren im FLEX erwogen, dann zugunsten Barkley nach vollständigerem RB/WR/TE-Vergleich verworfen. Waddle wegen Brust-/Einsatzunsicherheit, Pickens Schulter/Hamstring, Love Rückkehr nach zwei Spielen Pause. | Bewusster FLEX-/Roster-Trade-off, nicht nachträglich aus Week-8-Punkten ableiten. |
| Fr 30.10. | Arizona meldet Love nach drei Practices als einsatzbereit; grundsätzlich attraktives Dallas-Matchup, aber Re-Entry-/Backfield-Split-Risiko. Pickens offiziell Questionable; bei Waddle Chest-Issue weiter Unsicherheit. | Spielbereitschaft ≠ normaler Snap-/Touch-Floor. Individuelle Chance und kumulierte FLEX-Downside trennen. |
| Sa 31.10., 22:17 EDT (= So 01.11., **03:17 MEZ**) | Athlon veröffentlicht Cross-Position-PPR-FLEX-Ranking: Pickens 23, **Fannin 37**, Tucker 40, McConkey 46, Barkley 50, Love 57, Loveland 62, Warren 70, Sampson 114. | Die Veröffentlichung liegt vor dem Sonntag-19-Uhr-Lock. Ohne Archiv der konkreten Ranglistenrevision keine Garantie, dass *jede heute sichtbare Zeile* unverändert war. |
| So 01.11., 17:30 MEZ | Breece Hall von den Jets offiziell inactive; der zuvor geplante FLEX wird frei. | Ausdrücklich diskutierter Hall-Ersatz: Love vor McConkey/Warren; Roberts bestätigter Start. |
| So 01.11., 19:00 MEZ | Gleichzeitig unter anderem Love, Pickens, Tucker, Fannin und Sampson bei NFL-Kickoff. | Nur **vor** diesem Lock bestand ggf. ein legaler Direktvergleich unter den genannten Kandidaten. Die minutengenaue letzte User-/Sleeper-Konfiguration und individuelle AutoSub-Paarungen sind nicht vollständig archiviert. |
| So spätere Spiele / Mo 02.11. | McConkey startet später, Loveland erst Montag; andere Slots bereits gelockt. | Nicht nachträglich einen schon gespielten Early-Spieler durch Late-Score ersetzen. Nachträgliche Verletzung Loves erst **Outcome**. |
| Mo 02.11. / danach | Alle 14 NFL-Spiele final, Scoring/Usage materialisiert. | Nur Ergebnis, Modellkalibrierung und Spieler-Follow-ups; keine Veränderung des damaligen Entscheidungszustands. |

**Waiver-Sonderfall:** Little wurde per erfolgreich abgeschlossenem Week-8-Waiver statt Fairbairn hinzugefügt (Einreichung 29.10., Abschluss 01.11. 12:05 MEZ). Ein zusätzlich beantragter Spieler ohne Drop war wegen Roster-Überfüllung nicht verfügbar. So ist der historische Move belegt, aber kein weiterer fiktiver Week-8-FA-Start.

## 4. Ex-ante-Expertenvergleich — *vor* dem Outcome-Urteil

### 4.1 Belegte und eingeschränkt belegte Quellen

| Kürzel | Quelle / Datierung | Aussagekraft und Caveat |
| --- | --- | --- |
| **ATH** | Cory Bonini, Athlon: [Week-8-PPR-FLEX-Rankings](https://athlonsports.com/fantasy/fantasy-football-flex-ppr-rankings-2026-nfl-week8), Veröffentlichung **31.10.2026, 22:17 EDT** | Entscheidungsrelevante gemeinsame RB/WR/TE-Rangfolge vor den Sonntagsspielen. Cross-Position-Ranking eignet sich besonders für **unsere vier FLEX-Slots**. Revisionshistorie der heute angezeigten einzelnen Ränge nicht gesichert; generische Ligaannahmen, keine individuellen 6-Team-/2-TE-Rosterregeln. |
| **FP** | FantasyPros: [Week-8-Start/Sit-Quick-Grades](https://www.fantasypros.com/2026/10/fantasy-football-week-8-player-grades-start-sit-advice-2026/), Artikel im **Oktober 2026** veröffentlicht | Vergleichbare qualitative Start-/Sit-Bewertung je Position; **nicht** als gleichwertige positionsübergreifende Punkt-/FLEX-Rangfolge interpretieren. Auf Consensus/Primer basierende Grade, deshalb **kein zusätzlicher unabhängiger** FantasyPros-ECR-Beleg; exakte Erstveröffentlichungs-/Änderungszeit der sichtbaren Grade nicht belegt. |
| **NFL** | Matt Okada, NFL.com: [WR Start 'Em/Sit 'Em Week 8](https://www.nfl.com/news/nfl-fantasy-2026-start-em-sit-em-wide-receivers-for-week-8), veröffentlicht **28.10.2026** | **Tucker explizit „Notable Start“** wegen 19 Targets, 200 Yards, 3 TD in den zwei vorherigen Spielen; direkte, unabhängige qualitative Begründung, trotz nicht idealem Jets-Matchup. |
| **SI** | Sports Illustrated: [Week-8-TE Start/Sit](https://www.si.com/fantasy/week-8-start-em-sit-em-tight-ends), vor der Woche publiziert (Suchindex: ca. **28.10.2026**) | **Fannin explizit „Sit“**: vorher zwei Wochen mit unter zwei Punkten und ungünstige Steelers-TE-Defense. Einzelfallberatung aus klassischem TE-Kontext, kein vollständiges Cross-Position-FLEX-Board. |
| **ARI** | Cardinals: [offizieller Injury-Report vom 30.10.](https://www.azcardinals.com/news/injury-report-week-8-vs-cowboys) | Love nach zwei verpassten Wochen als spielbereit; dennoch nicht als voller Workload garantiert. Pickens Schulter/Hamstring als gegnerische Injury-Information. |
| **NYJ** | Jets: [offizielle Week-8-Inactive-Liste](https://www.newyorkjets.com/news/jets-vs-raiders-nfl-game-inactives-11-1-2026), **01.11., 11:30 ET** | Hall inactive, genau **ab dann** neues Replacement-Informationsfenster. |

**Explizit nicht als Pregame-Rangliste verwertet:** öffentlich inzwischen auffindbare **4for4-Rankings mit angezeigtem Update vom 02.11.2026, 19:06 EST** und FantasyPros-/Drittseiten-Consensus-Abzüge mit Update nach Sonntag. Eine Website-URL allein beweist keinen historischen vor dem Kickoff identischen Snapshot.

### 4.2 Kandidatenbezogene Expertenmatrix

| Startbarer Grenzkandidat | ATH PPR-FLEX (veröff. Sa) | FP Quick-Grade (Positionsformat) | Weitere Pregame-Evidenz | Ex-ante-Schluss |
| --- | ---: | --- | --- | --- |
| **George Pickens** (Starter) | **23** (Q) | WR **A** | Schulter/Hamstring, offiziell Questionable; im Entscheidungsdialog als wahrscheinlich spielend beurteilt. | Starkes Expertenprofil trotz erhöhtem Gesundheitsrisiko. Start **vertretbar**, falls zum Lock active; kein begründeter pauschaler Bench-Zwang. |
| **Harold Fannin Jr.** (Bank) | **37** | TE **D+** | **SI: Sit**, unvorteilhaftes TE-Matchup; aber 83 % Snaps in W7 und 13,10 PPR. | **Echte Evidenzdivergenz:** Athlon rangiert ihn knapp **vor Tucker**; FP/SI deutlich vorsichtiger. Bewusste Grenzprüfung erforderlich, **kein** klarer Konsens-Start. |
| **Tre Tucker** (Starter) | **40** | WR **B** | **NFL.com: Start** wegen jüngstem Target-/Yardage-/TD-Lauf (19 Targets in 2 Spielen); W7 82 % Snaps, 21,30 PPR. | Mehrere damalige Gründe **für** einen Start. Null Punkte erst nachher bekannt; kein eindeutiger Einzelprozessfehler. |
| **Ladd McConkey** (Bank) | **46** | WR **B** | Gesunde/relativ belastbare Week-Alternative; im dokumentierten Hall-Ersatz-Pool; einzelnes damals besprochenes Modell ca. 11,0 vs. Love 10,4. | **Nahe an Tucker**; gegenüber Love in ATH und FP besser, relevante Floor-/Workload-Gegenhypothese. |
| **Saquon Barkley** (Starter) | **50** | RB **B−** | Verletzungs-/Snap-Limit-Risiko; nach Comeback-Freigabe bewusst statt Warren gewählt. | Start auf Ceiling-Grundlage möglich, aber erhöht die kumulierte FLEX-Downside. |
| **Jeremiyah Love** (Starter) | **57** | RB **C+** | Cardinals meldeten gesund genug für Rückkehr; nach 2 verpassten Spielen Backfield-Split-/Workload-Fragezeichen, Dallas-Matchup attraktiv. | **Bewusst contrarian** gegenüber ATH/FP und im Dialog zitierter Modellnähe zu McConkey; kein Konsenssieger. |
| **Colston Loveland** (TE2) | **62** | TE **B−** | W6/W7 18,50 / 19,90 PPR bei 84 % Snap Share W7; aktuelle Rolle positiv. | Gezielte TE2-Präferenz vor Warren **gut begründet**; ATH wertete Fannin höher, FP wertete Loveland höher. |
| **Tyler Warren** (Bank) | **70** | TE **D** | Comeback nach Leistenproblemen; vor der Woche im engeren TE2-/TE3-Pool. | Temporäre Zurückhaltung nachvollziehbar, trotz später erheblicher Zielspieler-Nutzung. |
| **Jaylen Waddle** (Bank) | **Q-GTD / kein normaler Rang** | WR **C+** | Brustverletzung/Questionable, Routen-/Snaprisiko; nicht unbesehen als gesunder sicherer Floor behandeln. | Punktgewinn gegenüber Tucker war **ex post**; Pregame-Risikobild ist real. |
| **Dylan Sampson** (Bank) | **114** | RB **D+** | Stärkerer W7-Output, aber noch unklare volumenstabile Backfield-Rolle. | Kein gut belegter Ex-ante-Starter über etablierte WR/TE; Week-8-Breakout bleibt neue Opportunity-Evidenz. |

**Warum drei Quellen nicht automatisch drei Stimmen sind:** FantasyPros-Grade werden aus hauseigenen Consensus-Projektionen, Rankings und Derek Browns Primer erzeugt. Separater FantasyPros-ECR und derselbe Grade sind darum **nicht** zwei unabhängige Abstimmungen. ATH ist eine andere Cross-Position-Rangliste; NFL.com und SI sind unabhängige qualitative Einzelbewertungen. Zugleich sind TE-Positionsgrade nicht numerisch wie ein FLEX-Gesamtrang vergleichbar.

**Rollen-/Sonderformat-Korrektur:** ATH und FP gehen nicht von exakt unseren 6 Teams, 2 Pflicht-TE und 4 FLEX aus. Die Expertenbasis informiert über erwartete Wochenleistung, entscheidet aber nicht automatisch unsere konkreten letzten vier Starter. Für einen zusätzlichen TE im FLEX gibt es keinen pauschalen Abschlag; die gemeinsame FLEX-Position ist RB/WR/TE-offen.

## 5. Same-Information-Review: getrennt von Ergebnis

### 5.1 Tucker vs. Fannin: „übersehen“ bedeutet nicht „offensichtlicher Start“

**Damals pro Tucker:** 21,30 Punkte in Week 7, 82 % offensive Snaps, 19 Targets und 200 Receiving Yards über zwei Wochen, NFL.com startete ihn ausdrücklich, FP beurteilte WR Tucker mit B. **Damals pro Fannin:** 13,10 Week-7-Punkte und 83 % Snaps; Athlon stellte ihn in derselben PPR-FLEX-Liste **37 vor Tucker 40**. **Contra Fannin:** SI riet wegen des Steelers-Matchups und vorheriger schwacher Wochen zum Sit; FP gab als TE D+.

**Re-Decision bei identischem Wissen:** **Kein eindeutiger Vorzug für Fannin** belegbar. Ein differenzierter Analyst konnte Tucker bevorzugen. Dass Fannin nachher 23,40 und Tucker 0,00 erzielte, darf die damaligen Expertenurteile nicht umdrehen. Der belastbare Prozessmangel lautet enger: Das Ex-ante-Protokoll dokumentiert **keinen expliziten vollständigen FLEX-Pool-Abgleich inklusive Fannin**. Die fehlende *Prüfung* ist ein Dokumentations-/Boundary-Defizit; ein unterlassener *Start* ist **nicht** als gesicherter Decision Regret ausgewiesen. Confidence für die konkrete Starter-Umkehr: **niedrig**.

### 5.2 Love vs. McConkey: bewusstes Ceiling gegen plausiblen Floor

**Damals:** Hall fiel um 17:30 MEZ als Fantasy-Starteroption weg; Love war nach zwei Wochen Pause für den Einsatz freigegeben. Unsere dokumentierte Begründung: gutes Dallas-Run-Matchup und Touchdown-Ceiling, aber geteiltes Backfield und Verletzungsrückkehr. McConkey hatte ein gesundes/erwartbar hohes Einsatzprofil; im Chat zitierte Einzelmodelle waren ungefähr 11,0 vs. 10,4 **für McConkey**. ATH stellte **McConkey 46 vor Love 57**, FP gab **WR B vs. RB C+** (nur qualitativ positionsbezogen).

**Re-Decision:** Ohne belegten materiellen Aufholbedarf und bei schon riskanter FLEX-Gruppe **leichte Präferenz für McConkey**. Loves Upside-Begründung war aber sachlich vorhanden, nicht bloß eine erfundene Projektion. **Leichter potenzieller Decision Regret auf Portfolioebene**, keine definitive mathematische Fehlentscheidung. Die *neue* Knöchelverletzung, die Love **im laufenden Spiel** erlitt, ist primär **Outcome Regret**; sie war nicht dieselbe zuvor behandelte Verletzung (Bestätigung des Trainers am 02.11.: https://www.azcardinals.com/news/jeremiyah-love-with-new-ankle-issue-as-cardinals-offense-catches-injury-bug). Der Injury-Ausgang darf nicht als Beweis für einen ex ante unvermeidlichen Reinjury-Fall missverstanden werden.

### 5.3 Pickens: Experten stärkten den Start, Injury-Risiko blieb

ATH FLEX23 (Questionable), FP WR A. Die bekannten Schulter-/Hamstring-Beschwerden erhöhten die Unsicherheit, aber ein genereller Sit wäre durch diese Ex-ante-Evidenz **nicht** gedeckt. Seine späteren 6,80 Punkte und 57 % Snaps begründen keine rückwirkende Behauptung, wir hätten ihn zwangsläufig bench-en müssen. **Einzelentscheidung vertretbar; Risikohäufung in der FLEX-Vierergruppe bewusst prüfen.**

### 5.4 Barkley statt Warren: die damalige korrigierte Auswahl bestätigt

Unser erster Vorschlag eines dritten TE Warren im FLEX wurde nach Roberts berechtigtem Vergleichseinwand neu bewertet. Barkley erhielt nach Rückkehr-Freigabe den Vorzug. ATH FLEX50 vs. Warren70, FP RB B− vs. TE D (nicht 1:1 in Punkten vergleichbar). 12,40 Barkley vs. 5,80 Warren bestätigen das Ergebnis, **begründen aber nicht erst nachträglich** die Entscheidung. **Guter Prozess – der vollständige Pool hätte dabei dennoch auch Fannin prüfen müssen.**

### 5.5 Loveland vs. Warren und Fannin: Rollen-, Experten- und Eligibility-Abwägung

Loveland war nach W6/W7 klar aufsteigend, Warren im Comeback. ATH hatte **Fannin TE6, Loveland TE12, Warren TE14**, FP hingegen **Loveland B−, Fannin D+, Warren D**. Das ist gerade **kein Konsens**, Loveland hätte über Fannin zwingend oder Fannin über Loveland zwingend starten müssen. Die dokumentierte Loveland-vor-Warren-Wahl ist gut begründet. Ein ergänzender Fannin-TE2-/FLEX-Stresstest wäre methodisch sauber gewesen; dessen Fehlen ersetzt keine belegbare vor Kickoff getroffene Gegenentscheidung.

### 5.6 Waddle, Sampson, QBs und Kicker

Waddle erzielte später 14,90, trug vor dem Spiel aber ein Chest-/Active-but-limited-Risiko; sein FP-WR-C+ und fehlender normaler ATH-Rang machen einen unbedingten Start über Tucker oder Pickens **nicht** selbstverständlich. Sampson lag bei ATH FLEX114, FP RB D+ — 12,90 Punkte sind ein Ex-post-Signal, keine klar übersehene Pregame-Pflichtwahl.

Mahomes/Daniels waren angesichts der QB-Alternativen solide gewählt; Penix erzielte nur 2,10. Die **Kicker-Transaktion Little für Fairbairn** löste den Bye mit einem statt zwei Kaderplätzen und ist unabhängig von Littles späteren sechs Punkten plausibel; FP bewertete Little mit **B+**, also ebenfalls positiv. 

### 5.7 FLEX-Portfolio statt vier isolierter Rankingplätze

Die Ex-ante-Risiken waren **kombiniert**: Pickens (Schulter/Hamstring, Questionable), Love (Rückkehr nach Verletzung, Timeshare), Barkley (Workload/Return) und Tucker (hohe jüngste Produktion, aber zu validierende Nachhaltigkeit des Targets-Floors). „Vier riskante Spieler“ bedeutet **keine** nachgewiesene statistische Korrelation oder vier unabhängige Ausfallwahrscheinlichkeiten.

Eine verlässlichere Alternative war insbesondere McConkey. Fannin blieb wegen widersprüchlicher Expertenmeinungen offen; Waddle wegen Brust-Status nicht als pauschaler Sicherheitsgewinn. Der neue kanonische FLEX-Portfolio-Check aus PR #1297 erfasst genau diese aggregierte Risikoabwägung, **ohne** spätere Erkenntnisse für frühere Entscheidungen als bereits bekannt auszugeben. 

## 6. Ex-post-Entwicklung und Rollen-Updates – ausdrücklich nach dem Entscheidungsfenster

| Spieler | W7 Snap Share | W8 Snap Share | W8 Ist | Konsequenz für künftige Rechecks |
| --- | ---: | ---: | ---: | --- |
| Trey McBride | 93 % | 95 % | 20,20 | stabiler TE-Kern |
| Puka Nacua | 85 % | 96 % | 25,00 | stabile Top-Rolle |
| Colston Loveland | 84 % | 93 % | 11,50 | Einsatztrend bleibt positiv |
| Harold Fannin Jr. | 83 % | 86 % | **23,40** | NFL Week 8: 10 Catches / 154 Yards; hoher Receiving-Einsatz, aber nicht als vorher sicherer Breakout ausgeben |
| Tetairoa McMillan | 68 % | 89 % | 11,80 | Gelegenheit positiv; Punktwert separater Aspekt |
| Kenneth Walker III | 74 % | 81 % | 12,40 | niedrige Punkte ≠ verlorene Rolle |
| Dylan Sampson | 46 % | 56 % | 12,90 | Passing-Game-Usage und Touchverteilung prüfen |
| Saquon Barkley | 15 % | 32 % | 12,40 | Einsatzanteil trotz Verbesserung limitiert |
| George Pickens | 60 % | 57 % | 6,80 | Arbeitspensum und Verletzung rechecken |
| Jaylen Waddle | 56 % | 45 % | 14,90 | Punkte hoch trotz begrenzter Snap-Basis |
| Tre Tucker | 82 % | 54 % | 0,00 | Target-/Route-Floor kritisch neu prüfen |
| Seth McGowan | 33 % | 25 % | 2,90 | contingent RB stash, kein Pflicht-FLEX |

Love erreichte in Week 8 **15 offensive Snaps / 19 %**, bevor seine neue In-Game-Verletzung die Partie verkürzte. McConkey hatte **55 Snaps / 90 %**, Fannin **60 / 86 %**, Warren **44 / 72 %**. Fannins zehn Receptions für 154 Yards sind auch über die Browns-Clubstatistik belegt: https://www.clevelandbrowns.com/news/harold-fannin-jr-records-career-high-154-receiving-yards-by-the-numbers

**Dynasty-/Weekly-Folgen:** Fannin ab Week 9 im vollen RB/WR/TE-FLEX-Kandidatenpool führen, aber nicht automatisch starten; Loveland/Warren anhand aktueller Targets und Routes erneut prüfen; Sampson als aktiven Development-/Receiving-RB beobachten, nicht wegen einer Woche unreflektiert promoten oder cutten; Tucker Target-/Route-Stabilität prüfen; Love Injury-/Practice-Status; Pickens/Barkley verbleibenden aktiven Workload; Waddle echte Snap-/Target-Verfügbarkeit; McConkey gesundes Routenprofil.

Die aktuelle 30/30-Aktiv-, 2/2-Taxi-, 5/5-Reserve-Situation erzeugt **keinen** aus diesem Wochenreview automatisch erlaubten Drop. Spätere Spielerklassifikationen oder Taxi-Zuordnungen sind keine historische Entscheidungswahrheit.

## 7. Endurteil und Kalibrierungs-/Prozess-Follow-ups

| Bereich | Ex-ante-Prozessurteil | Konfidenz | Outcome separat |
| --- | --- | --- | --- |
| Hall nach offizieller Inactive-Meldung aus dem Lineup | **Richtig** | Hoch | 0,00 Hall auf Bank |
| Little für Fairbairn-Bye | **Richtig** | Hoch | 6,00 Little |
| Mahomes/Daniels | **Vertretbar/gut** | Mittel | 40,42 kombinierte Punkte |
| Loveland vor Warren | **Begründet, Experten nicht einheitlich** | Mittel | 11,50 vs. 5,80 |
| Barkley statt Warren im FLEX | **Begründete Korrektur** | Mittel | 12,40 vs. 5,80 |
| Pickens trotz Questionable | **Durch Experten gestützt, riskant** | Mittel | 6,80 |
| Tucker im FLEX | **Ex ante gut vertretbar** (NFL.com-Start, FP B); Volatilität bekannt | Mittel | 0,00, W8-Targets/Snaps schlecht |
| Love vor McConkey | **Leichter möglicher Decision Regret**; Contrarian-Upside und Re-Entry-Risiko transparent | Niedrig–mittel | 2,30 vs. 12,60; **neue In-Game-Verletzung = Outcome Regret** |
| Fannin nicht explizit gegen gesamte FLEX-/TE2-Grenze geprüft | **Prüf-/Dokumentationslücke**, nicht gesicherter falscher Start | Mittel für fehlenden Aktenvergleich, niedrig für hypothetische Umkehr | 23,40 auf Bank |
| Vier FLEX-Plätze gemeinsam abgesichert | **Portfolio-Risikovergleich im Ex-ante-Artefakt nicht vollständig belegt**; die spätere Regel schließt Lücke | Mittel | Nur 21,50 aus vier FLEX |

**Eine klare Trennung:** (a) Unser internes V4-C-Modell unterschätzte Fannin und überschätzte unter anderem Tucker/Walker — **Kalibrierung**, keine automatische Decision Quality; (b) die externen Pregame-Stimmen waren teils **pro Tucker / contra Fannin**, teils **pro Fannin**; (c) die ex ante gewählte Aufstellung war nicht so eindeutig falsch, wie es 43,20 Hindsight-Punkte nahelegen. Die gravierendste verlässlich belegbare Schwäche ist ein **unvollständig dokumentierter Cross-Position-/Portfolio-Abgleich**, nicht ein aus Scores rückwärts festgestellter Fannin-Pflichtstart.

**Konkreter Folgeschritt für kommende Spieltage:** In jeder engen FLEX-/TE2-Entscheidung eine datierte Kandidatenmatrix mit unabhängiger Pregame-Expertenevidenz, widersprüchlichen Rankings, erwarteter Nutzung und Injury-/Lock-Zeitpunkt erstellen. Source-Level-Evidenz angeben; keine bloße modellbasierte Entscheidung und keine gespielten Punkte als Pregame-Argument. Für die generische Regel war die Grundanforderung bereits vor diesem Review in `MONITORING_AND_WEEKLY_DECISIONS.md` vorhanden; das Problem lag bei ihrer Durchsetzung im konkreten Review.

### Persistenz, offene Verifikation und Quellenverweise

- Diese Datei ist die **neue retrospektive Auswertung**, nicht die Ex-ante-Akte und nicht ein späteres versiegeltes Decision Record. PR #1276 bleibt ein **offener** separater Branch-Referenzstand und darf nicht stillschweigend als nach `main` gemergt ausgegeben werden.
- Keine autonome Änderung an Lineup, Waivers, Watchlists, Player Security/Role, Modellen, Derived-Daten oder CI. Offene technische Finalität: `snap-counts/2026/08.json -> Finalized=false`; `player-week-fantasy/2026/08.json -> TargetWeeklyRosterFinalized=false`; nachgewiesen: 14/14 NFL-Spiele final, 726/726 Fantasy-Istwerte final, offizielles Liga-Matchup final und alle 13 Starter konsistent.
- Ungeklärte Details: genaue originale AutoSub-Paarungen und Lock-Reihenfolge, vollständig eingefrorener historischer Taxi-/Reserve-Status und revisionssichere Erstversionen sämtlicher externen Rankings. Deshalb bleibt das Best-Ball-Maximum **konditional** und das Same-Information-Urteil in Grenzfällen ausdrücklich nicht absolut.
- Verwandte Issues: [#208](https://github.com/Lolindhir/fantasy-app/issues/208) für Post-Week-Reviews; [#206](https://github.com/Lolindhir/fantasy-app/issues/206) für Weekly Workflow; [#629](https://github.com/Lolindhir/fantasy-app/issues/629) für separat geplante Decision-Record-Architektur.
