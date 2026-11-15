# CP5g – F2 nach dem Free-Agent-Draft unter additivem Dead Cap

> **15.11.2026 · [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · Forschung, keine verabschiedete oder aktive Ligaregel.** Nutzerpräferenz **C-add** (harte additive Cut-Retention) als *Forschungshypothese*, nicht automatisch ein zusätzlicher F2-Kontrolltermin. Der [geschützte Nordstern](../../../league-context/league-philosophy.md) bleibt unverändert. Quellen: [CP5b](2026-11-14-salary-cap-cp5b-legal-start-settlement.md), [CP5d](2026-11-15-salary-cap-cp5d-debt-backtest.md), [CP5e](2026-11-15-salary-cap-cp5e-additive-debt-amortization.md), [CP5f](2026-11-15-salary-cap-cp5f-buyer-clearing-hard-settlement.md), [vollständige CP5g-JSON-Metriken](2026-11-15-salary-cap-cp5g-f2-additive-checkpoint-metrics.json).

## 1. Ergebnis in drei Sätzen

- **C-add und F2 sind gemeinsam härter als F2 ohne Retention.** Das historische Post-Free-Agent-Draft-Kaderbild vom **09.09.2026** hat vier über Cap liegende Teams mit insgesamt **122.567.015 $** Überhang (aktives damaliges System: **kein** Regelverstoß). Der in CP5b berechnete theoretische Ausgleich von **sieben** Nichtstarter-Cuts genügt mit 5 % einheitlicher Retention, bei 15/30/50 % aber nicht durchgängig.
- Die **exakt minimalen Cut-Zahlen**, wenn *alle* im September eingetragenen 13 Starter je Team unberührt bleiben und für jede zusätzliche Abgabe dieselbe hypothetische 5/15/30/50-%-Rate gilt, sind **7 / 8 / 11 / 22**. Das ist eine brute-force vollständige Subset-Grenze unter engen Voraussetzungen, keine wirkliche Managerentscheidung.
- **Eine neue Pflicht zur vollständigen Schuldenrückzahlung beim F2-Termin wäre eine weitere, bisher nicht beschlossene Mechanik.** Juni-Schuldjahrgänge von CP5d dürfen nicht beim F2-Termin als neue September-Schuld nochmals entstehen, und der zusätzliche Cap-Check darf den regulären Salary-/Cut-Retention-Reset nicht auslösen.

## 2. Warum die sieben bisherigen F2-Cuts nicht automatisch funktionieren

Wir verwenden exakt die [CP5b-Referenz](2026-11-14-salary-cap-cp5b-metrics.json): archivierte `League.json` vom September-Commit `b40956172a704ff616008d7835f527b86f128063`, dazu **Original-Salary** aus `Players.json`-Blob `f8cc9a97cbe19eed6907a7630da053052a35e577`. `SalaryCap=434.255.984 $`, sechs Teams, **RosterSize=30** reguläre Plätze plus tatsächlich belegte Taxi/Reserve. Der damalige FA-Draft war abgeschlossen. Alle sechs Teams hatten im unveränderten Septemberkader **null freie reguläre Plätze**; Zusatz-Trade-Zugänge würden daher reguläre Gegenbewegungen benötigen.

Bei genau den sieben von CP5b **hypothetisch** gestrichenen Nichtstartern bleiben `Top20(remaining)+SUM(retained cut cost)` folgende offene Beträge:

| Einheitliche Cut-Retention | Noch über Cap liegende Teams | Restüberhang nach genau sieben Cuts | Gesamt-Retention der sieben Cuts | Einzeln mögliche Cut→Trade-Ersatzpaare ohne weitere Aktion |
|---|---:|---:|---:|---:|
| 5 % | 0 | 0 $ | 11,58 Mio. $ | 3 / 35 |
| 15 % | 1 | 4,32 Mio. $ | 34,75 Mio. $ | 0 / 35 |
| 30 % | 3 | 14,61 Mio. $ | 69,50 Mio. $ | 0 / 35 |
| 50 % | 3 | 55,09 Mio. $ | 115,83 Mio. $ | 0 / 35 |

Bei **30 %** entfallen vom Restüberhang **11.032.568 $** auf Packers, **48.102 $** auf Mammoth und **3.530.159 $** auf TimpaBay. Bei **50 %** sind es **19.980.060 $**, **15.350.460 $** und **19.756.623 $**. Just Bill und die beiden vorher nicht über Cap liegenden Teams wären nach dem jeweiligen unveränderten Paket noch legal.

Das ist ein **bewusst konservativer einheitlicher Retention-Stresstest**: In einem echten Konzeptdurchlauf könnten die sieben Spieler jeweils **verschiedene** 50/30/15/5-%-Quoten haben. Dafür müssten Team-Tenure, Unterbrechungen, aktive Salary-Reduktion nach früheren Cuts und Floor für jeden Spieler nachweislich vollständig rekonstruiert werden. Das wurde **hier nicht** vorgetäuscht. Insbesondere ist die September-`Players.Salary`-Welt nicht bereits ein korrekt um alle Juni-Konzeptcuts rabattierter Preisvektor.

## 3. Vollständige Cut-only-Optimierung ohne Starterverluste

Für jedes der vier im September über Cap liegenden Teams werden **alle Kombinationen der nicht als Starter eingetragenen Spieler** gegen die **gemeinsame** Top20-Neuberechnung und individuelle `round_half_up(Salary × Quote)`-Retention geprüft; es wird nicht bloß wiederholt der nächste teuerste Spieler herausgenommen. Je Team sind 19–20 Nichtstarter eligible (2^19 oder 2^20 exakte Teilmengen), für **jede** der vier Retention-Quoten und die 0-%-Referenz. Die übrigen beiden Teams benötigen keine Cuts. Ohne weitere Trade-/Käuferbewegungen ergeben sich:

| Cut-Quote | Mighty Giants | Packers | Just Bill | Mammoth | Dennis | TimpaBay | Liga |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 % | 0 | 2 | 1 | 2 | 0 | 2 | **7** |
| 5 % | 0 | 2 | 1 | 2 | 0 | 2 | **7** |
| 15 % | 0 | 3 | 1 | 2 | 0 | 2 | **8** |
| 30 % | 0 | 4 | 1 | 3 | 0 | 3 | **11** |
| 50 % | 0 | 9 | 1 | 4 | 0 | 8 | **22** |

Diese exakte **mathematische** Machbarkeit unter Starter-Schutz zeigt nicht, dass Manager die betroffenen Spieler freiwillig entlassen würden. Bei 50 % erfordert das Optimierungsbeispiel **9 Packers- und 8 TimpaBay-Cuts** – erhebliche Tiefe-/Asset-Abgaben. Die konkreten Spielerbeispiele, in der einheitlichen Preiswelt:

| Team | Ausgangsüberhang | Min. Cuts 30 % | Beispiel bei 30 % | Min. Cuts 50 % | Beispiel bei 50 % |
|---|---:|---:|---|---:|---|
| Ruhr Valley Packers | 27.486.107 $ | 4 | Sam Darnold, DK Metcalf, Travis Kelce, Rachaad White | 9 | Sam Darnold, DK Metcalf, Travis Kelce, Rachaad White, Deebo Samuel, Zach Charbonnet, Dalton Schultz, Rome Odunze, Tyrone Tracy |
| Just Bill | 7.406.779 $ | 1 | Josh Jacobs | 1 | Josh Jacobs |
| Mammoth Marauders | 41.763.737 $ | 3 | Brock Purdy, Trevor Lawrence, C.J. Stroud | 4 | Brock Purdy, Trevor Lawrence, C.J. Stroud, Courtland Sutton |
| Team TimpaBay | 45.910.392 $ | 3 | Jared Goff, Jordan Love, Drake Maye | 8 | Jared Goff, Jordan Love, Drake Maye, Rico Dowdle, Jayden Reed, Romeo Doubs, Juwan Johnson, Emeka Egbuka |

**Wichtige Interpretationsgrenze:** „Nicht als Starter eingetragen“ bedeutet **nicht** sportlich unwichtig und ist **keine Cut-Freigabe**. Unter den möglichen Abgängen sind etablierte Veteranen, zusätzliche Quarterbacks und potenziell attraktive Dynasty-Spieler. Positionale Depth, Taxi-Locks, Gegenleistungen, Waiver-Verfügbarkeit und späterer NFL-Wert wurden nicht als zustimmender Managerwille ersetzt.

## 4. Verpflichtender Fünf-Achsen-Ausweis aus der neuen Forschungsrichtlinie

Der [neue verbindliche Research-Standard](../../AGENTS.md) ergänzt das vorhandene ökonomische Vergleichsraster. Er gilt **für künftige Cap-Analysen**, nicht als aktives Ligarecht.

### 4.1 Verkäuferentlastung und korrespondierende Cut-Kosten

Für die **jeweils optimale reine Cut-only-F2-Abnahme** – die Spielerpakete unterscheiden sich pro Quote – sind die Brutto- und Nettoentlastungen über alle sechs Teams (einschließlich unveränderter Teams):

| Einheitliche Retention | Brutto-Top20-Entlastung | Gebuchtes Cut-Retained-Salary | **Nettoentlastung** | Neu gebuchte Schulden aus bestandenem striktem F2-Check | Zukunftssalary |
|---|---:|---:|---:|---:|---|
| 0 % | 185,57 Mio. $ | 0 $ | 185,57 Mio. $ | 0 (strict-pass) | 2027 nicht belegt |
| 5 % | 185,57 Mio. $ | 11,58 Mio. $ | 173,99 Mio. $ | 0 (strict-pass) | 2027 nicht belegt |
| 15 % | 200,03 Mio. $ | 37,81 Mio. $ | 162,22 Mio. $ | 0 (strict-pass) | 2027 nicht belegt |
| 30 % | 266,00 Mio. $ | 99,58 Mio. $ | 166,42 Mio. $ | 0 (strict-pass) | 2027 nicht belegt |
| 50 % | 360,42 Mio. $ | 230,37 Mio. $ | 130,05 Mio. $ | 0 (strict-pass) | 2027 nicht belegt |

**Diese Retention ist eine Haftung bis zum nächsten regulären Salary-Zyklus**, keine bereits bestätigte mehrjährige individuelle Vertragsanrechnung. Die Nettoentlastung ist in diesem Cut-only-Existenzaudit kein realisierter Tradegewinn; weggefallene sportliche Kaderwerte sind real potenziell teuer, aber nicht in Dollar quantifiziert.

### 4.2 Käuferlast und tatsächlich freie Kaderplätze

Im Cut-only-Existenzaudit gibt es **keine Käufertransaktion**. Käuferzahlungen, Gegenwerte und real angenommene Angebote sind daher **nicht beobachtet**, nicht einfach „0 $“. Für die streng begrenzte **Alternative: einer der sieben Referenz-Cuts wäre stattdessen ein Trade zum vollen originalen Salary** wurde jedes der **7×5=35** Spieler-Käufer-Paare bei bereits hypothetisch vollzogenen anderen sechs Cuts einzeln erneut gerechnet; bei jeder Quote getrennt.

- Vor den hypothetischen F2-Cuts: **0/6** Teams mit freiem regulärem Slot, obwohl manche Cap-Luft haben.
- Nach den sieben hypothetischen Cuts: Packers **2**, Just Bill **1**, Mammoth **2**, TimpaBay **2**, Mighty Giants **0**, Dennis **0** freie reguläre Plätze.
- Bei **5 %** erfüllen **3 von 35** Einzel-Szenarien zugleich **Seller- und Buyer-Cadd plus tatsächlichen freien regulären Slot** ohne weitere Aktion: Sam Darnold (Packers) → Mammoth; DK Metcalf (Packers) → Mammoth; DK Metcalf (Packers) → TimpaBay.
- Bei **15/30/50 %** sind unter *genau demselben noch nicht vollständig legalisierten Sieben-Cut-Paket* **0/35** solcher Einzelpfade vollständig compliant. **Das widerlegt nicht**, dass weitere freiwillige gleichzeitige Trade-/Cut-Pakete eine Lösung schaffen können.

Jeder dieser drei individuellen Pfade führt beim Käufer ein **volles ursprüngliches Salary**, beim Verkäufer **keine** zu diesem Spieler gehörende Cut-Retention. Keine verhandelbare Trade-Salary-Übernahme ist beschlossen. Die drei Einzelfälle lassen sich **nicht** als drei gleichzeitig abschließbare Trades ausgeben, weil sie teilweise dieselben Kader/Spieler/Ressourcen beanspruchen. Alle sechs September-Kader müssen als Ganzes mit Cap, Rosterplätzen, tatsächlicher Managerzustimmung und assetseitiger Gegenleistung geprüft werden.

### 4.3 Liga-Gesamtschuld, Jahrgänge und Kreditversuch

Die Tabelle in 4.1 zeigt bei **streng bestandener F2-Abnahme** stets **0 neue F2-Überschreitung**. Das **bedeutet nicht**, dass eine bereits früher gebuchte aggregierte Jahresschuld verschwinden würde. Das in CP5d für Juni hypothetisch ausgewiesene Loan-Total **35.094.437 $** ist ein **separates** Konzept-Szenario (4,07 Mio. $ Packers, 31,03 Mio. $ Just Bill), kein realer September-Loan.

Wenn ein Nutzer **beides zugleich** will, muss zuerst ligaweit entschieden werden, **wie ein September-F2-Check mit einem bereits gültigen Juni-Schuldjahrgang umgeht**. Rein rechnerisch ist `max(0,Sept-Top20 + Sept-Retention + Juni-Alt-Debt − Cap)` auf den unveränderten sieben Referenz-Cuts:

| Uniforme September-Retention | Konditionale gesamte September-Bilanzüberschreitung mit Juni-Vortrag (kein gebuchter Neu-Kredit!) | Betroffene Teams |
|---|---:|---|
| 5 % | 19,50 Mio. $ | Packers 3,92 Mio. $; Just Bill 15,59 Mio. $ |
| 15 % | 26,91 Mio. $ | Packers 8,39 Mio. $; Just Bill 18,52 Mio. $ |
| 30 % | 41,59 Mio. $ | Packers 15,10 Mio. $; Just Bill 22,91 Mio. $; Mammoth 48.102 $; TimpaBay 3,53 Mio. $ |
| 50 % | 87,92 Mio. $ | Packers 24,05 Mio. $; Just Bill 28,76 Mio. $; Mammoth 15,35 Mio. $; TimpaBay 19,76 Mio. $ |

Diese Zahlen sind **weder** die reale 2026er Debt **noch** automatisch neu gebuchte 2026er Forderungen. Wer die Juni-Debt bei F2 bereits vor ihrer 2027er H2/H3-Ratenfälligkeit vollständig tilgen müsste, würde eine **zusätzliche frühe Tilgungspflicht** schaffen, die CP5e/H2/H3 bisher **nicht** beschlossen haben. Umgekehrt darf niemand denselben vorgetragenen Betrag beim F2 einfach erneut als neue Schuld verbuchen oder eine offene Rate mit neuem Kredit refinanzieren. Auch 5-%-Kreditgrenzen sind mit der historischen Juni-Cadd-Schuld von Just Bill von 31,03 Mio. $ **nicht** rückwirkend kompatibel.

### 4.4 Tilgungsfähigkeit und Finanzierung in Folgejahren

Für das reine F2-Cut-only-Szenario ohne alte Juni-Schuld fällt nach strikt bestandener F2-Prüfung **keine neue aggregierte F2-Debt-Ratenzahlung** an. Die **individuelle Cut-Retention** bleibt für die jeweilige Zyklusdauer bestehen, bis der reguläre Salary-Check sie resetten würde. **2027er Spieler-Salaries, dann tatsächliche Roster, Floor-/Portfolioeffekte und Cap sind nicht beobachtet**. Daher kann weder eine echte H2- noch eine echte H3-Zahl für September-Cuts belegt werden.

Für bestehende hypothetische Juni-Jahrgänge gelten die schon in [CP5e](2026-11-15-salary-cap-cp5e-additive-debt-amortization.md) ausgewiesenen frozen-June-Varianten **nur als separate 2026er mathematische Szenarien**. Sie dürfen nicht per stillschweigendem Overlay zur 2027er Prognose nach einem veränderten FA-Markt gemacht werden.

## 5. Zeit- und Durchsetzungskonflikte bei einem harten F2-Termin

**Vorgeschlagene, nicht aktive Statusmaschine (für Papierpilot):**

1. `freeze`: gemeinsamen Salary-/Cap-/Roster-/Taxi-/Reserve-/Cut-/Debt-Jahrgang-Stand inklusive Commit, UTC-Zeit und Hash fixieren; dokumentierte abgeschlossene FA-Draft-/Trade-/Waiver-Bundles erfassen.
2. `candidate`: `Top20 + R + alte Schulden` getrennt in vier Komponenten anzeigen, **fällige Altjahrgangsraten** separat und **kreditfähigen neuen Überhang** ausschließlich gemäß erst noch festzulegender Policy. Ein Zusatztermin ist **kein** neuer Salary-Zyklus und kein schon fälliges Juni-Debt-Rollover-Gate.
3. `voluntary_correction`: Manager wählen freiwillig zugelassene Cuts oder Trade-Bundles; beide Seiten, freie Kaderplätze/Taxi/Reserve, aktive Salary-Slices und additive neue Cut-Retention neu berechnen. Keine „einzelnen passenden“ Deals addieren, wenn sie nicht gemeinsam durchführbar sind.
4. `pass`: alle tatsächlich im künftigen Reglement vorgegebenen Grenzen und **fälligen** Raten erfüllt, Datenquellen und Manageraktionen final verbucht.
5. `pending_correction`: data-/event-/status-Konflikt noch offen und auditierbar. **Kein** stilles Pass bei fehlenden Belegen.
6. `failed_unresolved`: trotz tatsächlicher Abschlussdeadline verbleibender Überhang oder Pflichtzahlung. Dieser Status begründet **keine** Auto-Cuts, erzwungenen Starterverluste, geheime Debt-Abschreibung, Pick-Sperren, Trade-Vetos oder sonstige automatische Bestrafung. Was operativ **wirklich** darauf folgt, inklusive Grace-Frist/Appeal, muss erst durch die Liga beschlossen werden.

Ein F2-System ohne **frühzeitig bekannten und fair durchsetzbaren** Hard-Failure-Ausgang ist nicht vollständig spezifiziert. Ein permanentes Sleeper-Cap-Transaktionsgate ist laut der bis CP5b dokumentierten Plattformverifikation **nicht** über die öffentlich dokumentierte Lese-API nachgewiesen. Ein Offseason-Pilot müsste Vorgänge und tatsächlich beanspruchte Commissioner-Minuten erheben; historische Event-Counts sind **keine gemessenen Minuten**.

## 6. Vergleichsstand gegenüber A, F2, B (permanent), F3 und sechs Nordstern-Zielen

| Mechanik | Getesteter September-Effekt, keine Vermischung von Vertragswelten | Grenzen |
|---|---|---|
| **A** jährlicher Cap, keine September-Kontrolle | Historische 4/6 über Cap, 122,57 Mio. $; unter geltender Liga-Logik kein Verstoß | Keine sofortige wirtschaftliche Korrektur |
| **F2** ohne Dead Cap (CP5b) | Seven **hypothetische** Nichtstarter-Cuts genügen für September-Cap | Keine Cut-Haftung; ein einziger Nutzerstart-Pfad |
| **F2 + C-add** (CP5g) | Uniform 5/15/30/50-%-Varianten verlangen 7/8/11/22 Cut-only-Maßnahmen für strikte September-Legalität | Nicht tatsächliche Tenure, mögliche Trade-/Salary-Discount-Welt ungetestst |
| **F3** zusätzliche In-Season-Abnahme | CP5b konnte am 05.11. entlang eines F2-legalisierten Pfads 3 weitere Schnitte zeigen | Nur **ohne** C-add im F2-Ausgangspunkt; nicht „F3+C-add=3“ |
| **B** permanentes Cap-Gate | CP5b-Audit aus ehemals legalem F2-Start: 43 Events angenommen, 8 historische Fortsetzungen inkompatibel, 3 cap-seitig abgelehnt | C-add würde die gesamte Transaktionshistorie ändern, nicht gleichbedeutende Zahlen |

**Nordstern-1 Aufholbarkeit:** F2+C-add erzeugt künftig mehr wirtschaftliche Entscheidungen, aber die Wirkung auf mehrjährige Titelwege ist nicht gemessen. **2 Management belohnen:** richtige Preis-/Liquiditätsplanung gewinnt; es gibt keine Beweise für reale Käufergebote. **3 Keine Gratis-Persistenz:** Cut-Retention macht sofortige Gratis-Entlastung schwieriger, aber einzelne starke Roster können weiterhin Vorteile halten. **4 Wirtschaftlicher Preis:** hoher 50-%-Fall erzwingt rechnerisch 22 statt 7 Abgaben; Härte sollte ökonomisch tragbar sein, nicht bloß maximal. **5 Strategische Freiheit:** starre F2-Frist kann Reload und Buyer/Win-now erschweren, obwohl nur die Starter geschützt wurden. **6 Operative Umsetzung:** zwei fixe Checks sind viel leichter nachzuvollziehen als 54 und mehr atomare Transaktionsprüfungen; aber Tenure- und Rosterbuchung plus Hard-Failure-Verfahren brauchen valide Daten und sind nicht kostenlos.

## 7. Ergebnis, verbleibende Unsicherheit und nächster Gate

**F2 + C-add ist nach dem historischen September-Freeze grundsätzlich rechnerisch bis 50 % Retention durch Nichtstarter-Cuts legalisierbar, aber extrem unterschiedlich teuer.** Die zunächst nur sieben Cuts aus CP5b werden bei hohen Rates gerade *nicht* als kostenloses Settlement übernommen. Die 22-Cut-Grenze ist nur ein mit einheitlichen 50 % auf *jeden* Kandidaten generierter Extremfall, kein erwartbares Managerverhalten.

Der neue verpflichtende **Fünf-Achsen-Forschungsstandard** wurde in `fantasy-management/league-economy/AGENTS.md` als **Research-Reporting-Disziplin** dokumentiert. Für künftig besprochene Cap-Alternativen sind Verkäuferentlastung, Käuferlast, tatsächliche Kapazität, Liga-Schuld und Tilgungsfähigkeit separat nachzuweisen oder transparent als nicht beobachtet auszuweisen. Dieser Standard **ändert keine Ligaregel**.

**CP5 Gesamt und CP6 bleiben offen**, weil folgende Dinge nicht belegt sind: individuelle 2026er September-Tenure für den verpflichtenden *echten* Mischsatz-Cutledger, 2026er Discount-/Reacquisition-Continuity aus vorherigen Cuts, real angenommene Trades, mehrjährig legaler Preis-/Roster-Pfad, Zeitpunkt/Erlaubnis einer zusätzlichen F2-De-Facto-Schuldaufnahme, operativer Failure-Sanktionstatbestand, exakte Commissioner-Minuten sowie eine saubere zusätzliche F3/B+C-add-Gegenfaktik. Die historische `F2`-Mindestcutzahl **darf nicht als Ligaentscheidung** ausgegeben werden.

**QA:** 41 programmatische Quell-/Cut-Subset-/Buyer-/Carry-Over-Invarianten bestanden. [Detailliertes Audit-JSON](2026-11-15-salary-cap-cp5g-f2-additive-checkpoint-metrics.json) hält Original-IDs, 6 Teamzeilen, 5 Retention-Quoten, konkrete Minimum-Sets, 140 isolierte Käuferpaare, sechs Nordstern-Begrenzungen und offene Fehlzustände fest. **Keine aktiven Liga-/Salary-/App-/Datenproduktions-/Workflow-Änderungen.**
