# CP7b – Was bewirkt Dead Cap tatsächlich auf dem Offseason-Trade-Markt?

> **26. November 2026 – erster gepaarter systematischer Trade-vor-Cut-Pilot.** Forschungsstand zu [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344), Draft PR #1576. **Noch keine Empfehlung für eine aktive Ligaregel.** Spezifikation [CP7a](2026-11-26-benchmark-v1.md), [Auswertung JSON](2026-11-26-cp7b-aggregate-overview.json), [Rechenkern CP7b](cp7b_pre_cut_market.mjs).

## Zusammenfassung

**Der gewünschte Offseason-Trade-Anreiz ist im Forschungsmodell erkennbar, aber keine der beiden Dead-Cap-Varianten ist damit schon ein erwiesener Gewinner.** Unter mittlerem Cap-Druck (−10 %) bringt das einjährige Retained-Salary-Konzept statt drei nun sieben hypothetisch für beide Proxy-Manager akzeptable 1:1-Trades zustande und reduziert notwendige Cuts von sechs auf drei. Das Mehrjahres-Garantiemodell produziert acht Trades und ebenfalls drei Cuts. Unter hartem Druck (−20 %) erzeugen beide noch mehr Trades als die Nullkontrolle, **aber auch mehr Cuts und deutlich mehr gebundene Salary**; bei garantierten Verträgen bleibt ein Team in einem Szenario nach dem gewählten Greedy-Settlement 5,71 Mio. $ über Cap.

Das ist eine **einjährige Querschnitts-Kontrafaktik**, keine Aussage über tatsächliche Managerzustimmung, Championship-Wahrscheinlichkeiten, realen zukünftigen Cap oder den historischen 2027-Ligastand. Der Nutzer hat das Verfahrensziel festgelegt: Dead Cap soll handeln gegenüber cutten attraktiv machen. Deswegen sind Cut-/Trade-Zahlen hier vorläufige mechanische Signale, nicht die finale Zielbewertung.

## 1. Gleiche Bedingungen

- 1.268 archivierte Player-Preiszeilen zum 05.10.2026; eingefrorene Criticality-Salary-Basis, Top-120/6-Cap zu Beginn **489,86 Mio. $**. Keine aktuelle Live-2027-NFL-Ergebnisse behauptet.
- Drei bewusst verschiedene **synthetische** sechs-Team-Ownership-Seeds (11/29/47) mit rotierten All-in-/Rebuild-/Reload-/Flex-Agenten, jeweils drei einmalige Cap-Only-Schocks 0/−10/−20 %. Das ergibt **27 Szenarien: neun pro Dead-Cap-Regime**, mit identischer Startbelegung, Preisen, Positionen und Agentenannahmen innerhalb jedes Paars.
- 45 erlaubte reguläre Slots ohne Taxi/IR-Sonderplätze; **die sechs Startkader umfassen hier jeweils 20 Spieler**, deshalb ist das **kein** Nachweis, dass 45 tatsächlich gegenüber 40 besser ist. 13 Starter, verbindliche Positionsdeckung und volle Salary auch für Bench. Vorzugsregel ist Trade **vor** Cap-Zwangscut.
- Kein echter Pickhandel, keine mehrteiligen Pakete oder vollständige Waiver-Auktion: pro Ereignis 1:1-Vertrags-Swap mit gegenseitig positiven, synthetisch definierten Manager-Nutzenfunktionen. Cut-Ersatz aus freiem Archivspielerpool mit gleicher Position. Die P1-Retained-Salary-Nach-Cut-Preissenkung wird bei späteren legalen Ersatzsignings berücksichtigt; für P2 ist ein neues FA-Salary des gecutteten Spielers **nicht festgelegt** und deshalb wird dessen Wiederaufnahme innerhalb derselben Phase **nicht** als günstiges FA-Angebot erfunden.
- P1-Tenure 0/1/2/3+ → 50/30/15/5 % vom aktuellen Salary. Da keine echte individuelle Erwerbshistorie in der synthetischen Startwelt vorliegt, wird die synthetische Vertrags-Vintage zunächst **nur als Akquisitionsproxy** verwendet; ein Trade setzt die neue Tenure korrekt zurück. Im echten Benchmark sind historisch belegte Akquisitionsdaten Pflicht.
- P2 verwendet CP6-Guarantee-Quoten; bei Spielern ohne belegte historische Fantasy-Runde Teilgarantie. **Die echte Wirkung von Rookie-R1/2- vs. R3/4-Garantien wird hier nicht getestet**, weil dieser 2027-Querschnitt keinen neuen Rookie Draft durchläuft.
- Für die monetäre Paarkontrolle ändern sich nur Dead-Cap-/Cut-Regime. Ein zusätzliches Cap-Kontrollereignis ist **keine Salary-Neubewertung und kein Dead-Cap-Reset**. Der reale jährliche Deadline-/Reset-Kalender und die 2028+ Kapazität müssen später explizit simuliert werden.

### A. Handels- und Cut-Volumen

*Tabellenzellen = hypothetisch beidseitig angenommene Vertrags-Swaps / tatsächlich im Modell gebuchte Cut-/FA-Replacement-Aktionen. Summen über drei alternative Seeds; keine beobachteten menschlichen Trades.*

| Cap-Schock | P0: Null-Dead | P1: einjähriges Retained Salary | P2: mehrjährige Garantien |
|---|---:|---:|---:|
| 0 % | 0 / 0 | 0 / 0 | 0 / 0 |
| −10 % | 3 / 6 | 7 / 3 | 8 / 3 |
| −20 % | 4 / 19 | 6 / 22 | 10 / 27 **(1 nicht vollständig abgewickelt)** |
| **Über alle drei Schocks** | **7 / 25** | **13 / 25** | **18 / 30** |

**Wichtig:** Ohne Cap-Druck erzeugt der aktuelle Agent **keine Angebote**, weil er primär bei Überschreitung verkauft. Das zeigt eine Grenze der Agentenlogik: freiwillige opportunistische Trades außerhalb von Cap-Notlagen werden nicht repräsentativ gemessen.

### B. Cap-Solvency und tatsächlich gebuchte Dead Cap

| Regime | Legale Snapshot-Welten | Proxy-Trades | Cuts | Current Dead Cap über alternative Welten (Mio. $) | Zukünftig garantiert fällige Dead Cap (Mio. $) |
|---|---:|---:|---:|---:|---:|
| P0 – keine Dead Cap | 9/9 | 7 | 25 | 0,00 | 0,00 |
| P1 – Retained Salary | 9/9 | 13 | 25 | 242,11 | 0,00 |
| P2 – Vertragsgarantien | 8/9 | 18 | 30 | 344,16 | 67,21 |

**Keine dieser Debt-Summen ist ein gemeinsamer echter Liga-Schuldenstand.** Sie summieren jeweils neun alternative sechs-Team-Gegenwelten. Bei P1 gilt der Dead Cap nur im aktuellen Salary-Zyklus, bei P2 können vertragliche Garantie-Jahresvintages zusätzlich in die Zukunft reichen. Die Summen sind deshalb nicht gleichbedeutend mit einer laufenden Jahresgebühr oder realen Zahlung.

**Operatives Hard-Failure-Signal:** Seed 29, −20 %, P2: Team 2 verbleibt nach simuliertem Trade-/Cut-Settlement mit **5.709.465 $ Überhang**. Die Finanzbuchhaltung und Kaderdeckung sind nachvollziehbar; der **Greedy-Algorithmus** fand keine weitere legale Nettocap-Entlastung. **Kein mathematischer Insolvenzbeweis:** Ein anderer Trade, ein mehrteiliger Deal, andere FA-Verfügbarkeit oder ein optimaler Solver könnten die Lücke schließen. Es darf weder heimlich ein Kredit eingebaut noch das Team stillschweigend als legal gezählt werden.

## 2. Besonders aufschlussreich: derselbe Spieler unter P1 und P2

Im Seed 11, −10 % Cap-Schock, möchte synthetisches Team 2 den archivierten Spieler **ID `9221`** mit aktuellem Salary von **62,09 Mio. $** abgeben. Team 5 bietet Spieler **ID `11575`** mit **2,31 Mio. $** zurück. Der volle Vertrag des Verkäufers geht bei einem 1:1-Trade an den Käufer.

| Entlastung des Verkäufers, laufendes Jahr | P1 – Retained Salary | P2 – Garantie |
|---|---:|---:|
| Trade: Brutto-Salary abzüglich Gegenspielersalary | 59,78 Mio. $ | 59,78 Mio. $ |
| Cut: bereits entstehende Current Dead Cap | 31,04 Mio. $ | 62,09 Mio. $ |
| Cut: Nettoentlastung nach legalem FA-Ersatz | 29,67 Mio. $ | -1,38 Mio. $ |
| **Trade statt Cut: zusätzliche aktuelle Cap-Entlastung** | **30,11 Mio. $** | **61,16 Mio. $** |

P1 halbiert das aktive Spieler-Salary nach dem Cut auf **31,04 Mio. $**. Ein möglicher Waiver-Käufer kann auf diese vergünstigte Option warten – was die Bereitschaft, den vollen Trade-Salary zu übernehmen, reduzieren kann. Im P2-Fall würde der Cut des aktuellen Vintage-Vertrags sogar **62,09 Mio. $** Garantie-Schuld für 2028/29 binden. Ein Trade würde diese vertraglichen Zahlungen auf Team 5 übertragen, aber **Käufer-Zustimmung und deren echte Zukunftsfinanzierung sind nicht beobachtet**.

Die Transaktion hat für beide Proxy-Agenten eine positive Nutzenänderung; es handelt sich **nicht** um ein reales Angebot. Die 2028/29-Trajektorie speichert vollständige Salary-Transfers an beide Teams und die Nullsummen-Invariante, doch der spätere *tatsächliche* Cap und neue Trades/Cuts sind offen.

## 3. Was ändert sich unter starkem Druck?

**Bei −10 %** funktioniert der gewünschte Mechanismus im Modell am klarsten: P1/P2 erzeugen vier bzw. fünf zusätzliche angenommene Trades gegenüber P0; dabei brauchen die Teams jeweils drei statt sechs Cuts. Die zusätzliche ökonomische Friktion übersetzt sich damit in früheren Handel und nicht bloß in Schulden.

**Bei −20 %** kippt der Befund: P1 und P2 haben zwar mehr angenommene 1:1-Deals als P0, aber auch mehr Cuts. Über das Cap-Stress-Hard-Failure-Signal bei P2 hinaus wächst die Current-/Future-Dead-Cap-Last; aus mehr Trades allein folgt **nicht** die wirtschaftlich bessere Liga.

**Waiver-Warten als Gegenkraft:** Im P1-Sensitivitätstest wird die Chance, nach einem Cut auf einen günstigeren Spieler zu bieten, hypothetisch mit 0 %, 50 % und 100 % berücksichtigt; die Wahrscheinlichkeit ist **nicht aus echten Managerdaten geschätzt**. Im −20-%-Stress liegen die angenommenen P1-Trades bei **8** (0 %), **6** (50 %) und **6** (100 %). Schon diese kleine Annahmenvariation verändert den Markt. Außerdem wurden in Seed 29 zwei spätere Ersatzspieler aus früheren P1-Cuts tatsächlich zum verminderten aktiven Salary übernommen; diese Rabattlogik wurde vor dem Abschluss der Auswertung korrekt in den Ledger eingebaut.

## 4. Prüfstatus und die fünf verbindlichen Finanzierungsachsen

- **Seller Relief:** für jeden Trade aktuelles Brutto-Salary, Gegenspieler-Salary, tatsächliche Nettoentlastung, Cut-/FA-Kontrafaktik, aktuell einbehaltenes Dead Cap und P2-Folgejahr-Garantien dokumentiert.
- **Buyer Burden:** aktuelle Vollgehaltsübernahme und Gegenspieler-Abgabe; Buyer-Cap-/Positions- und Gleichzeitigkeitstest im aktuellen Snapshot. **76 vollständige 2028/29-Salary-Transferzeilen** für 38 Proxy-Trades mit beiderseitiger Dollar-Konservierung geprüft. Der zukünftige Cap ist unbekannt; `frozenCapStressBuyerHeadroom` in den Daten ist **nur ein Stress-Counterfactual**, kein echter Zahlungsfähigkeitsnachweis.
- **Roster Capacity:** alle finalen Kader haben im Snapshot eindeutige Ownership, 20–45 reguläre Spieler und vollständige modellierte Starter-/Positionsdeckung. Die tatsächliche IR-/Taxi-/Sleeper-Eligibility ist nicht enthalten; alle Teams starten mit genau 20, daher keine quantitative 45-vs-40-Frage beantwortet.
- **Ligaweite Debt:** P0 erzeugt null Cut-Debt; P1 und P2 enthalten für jeden Cut konkrete Original-Owner-/Player-/Fälligkeits-Jahrbuchung. Trade erzeugt keine neue Dead Cap und konserviert Summe aktueller und abgegebener zukünftiger Vertrags-Salaries. Ein späterer Salary-Reprice-Reset von P1 ist im Probe-Rechenkern, **nicht** als real datiertes Ereignis in diesem 2027-Snapshot enthalten.
- **Future Repayment:** bei P2 spätere garantierte Cut-Verpflichtungen erfasst; Käufer-Zukunftslast bei Trades dokumentiert. Mehrjährige Team-Rollover, echte künftige Caps, Schuldner-Cut-Ketten sowie Insolvenzdurchsetzung **nicht modelliert**. Ein Team konnte im Greedy-Stressfall die Frist nicht heilen; keine automatische Schuldenerlass-/Re-Finanzierungsregel erfunden.

**Technische Invarianten:** 27 Weltzustände geprüft, 26 mit vollständigem aktuellem Cap- und Roster-Settlement, 38 Proxy-Deals und 80 Cuts mit exakten Current-Year-Salary-Identitäten, 76 geprüfte bilaterale Future-Salary-Zeilen, drei gemeinsame identische Input-Seeds. Node-CLI-/GitHub-CI-Ausführung **noch nicht** unabhängig ausgeführt: Resultate sind aus dem originalen Source-Blob in einer V8-Umgebung mit ausschließlich Datei-/Moduladapter ausgeführt. Es gab keinen Mathematik-Globaloptimumsnachweis.

## 5. Abgleich mit den sechs geschützten Nordstern-Zielen

| Geschütztes Ziel | Was CP7b wirklich aussagt | Bewertung |
|---|---|---|
| 1. Langfristig aufholen | Ein-Jahres-Querschnitt, kein beobachteter Rebuild- oder Championship-Pfad | **Offen** |
| 2. Gutes Management belohnen | Positive beidseitige Proxy-Nutzen, aber kein externer Skill-/Fehler-Gegenvergleich | **Offen** |
| 3. Keine automatisierte Ewigkeitsdominanz | Kein mehrjähriger haltbarer Spitzenindex und keine Folgejahr-Kaderentscheidungen | **Offen** |
| 4. Sportliche Stärke kostet | Aktuelle Cap-Entlastung, Dead-Cap-Last und zukünftige Vertragsjahre formal sichtbar | **Erster Nachweis im Modell** |
| 5. Verschiedene Strategien | Unterschiedliche Agentenrollen, 1:1-Trades unter Cap-Druck; Picks/echte Rebuilds fehlen | **Teilweise** |
| 6. Operative Durchsetzung | Finanzen auditierbar, aber ein nicht geheilter Greedy-Fall, kein echter Sleeper-Workflow/Commissioner-Aufwand | **Wesentlicher offener Gate** |

Die Liga-Philosophie bleibt in `fantasy-management/league-context/league-philosophy.md` geschützt und **noch nicht durch alle sechs Manager ratifiziert**. Wir bewerten keine einmalige Differenz als absichtliche sportliche Gleichverteilung.

## 6. Vorläufige Modellentscheidung – genau eingegrenzt

**Für das isolierte Ziel „Cut-Kosten lösen mehr Offseason-Trades aus“** liegt **P1 (einjähriges Retained Salary)** im aktuellen engen Experiment als **vorläufig pragmatische Baseline** vorne: deutlicher Trade-Zuwachs gegenüber P0 und 9/9 legalen Ein-Jahres-Pfaden ohne mehrjährige Garantielast. Das ist **kein Beschluss und noch keine endgültige wissenschaftliche Präferenz**. P2 aktiviert stärkere Trade-Anreize und erreicht mehr angenommene Trades, produziert in diesen Stresswelten aber höhere Kosten, mehr Cuts sowie einen nicht geheilten Greedy-Fall. Bei vielen vorhandenen Gewinnern kann wirtschaftliche Reizwirkung statt liquidem Handel auch Schulden- oder Inaktivitätsdruck bedeuten.

**Die zwei größten Unbekannten:** (1) Wie wirkt P1 noch, wenn Salary-Reprice/Dead-Cap-Reset und Cap Deadline tatsächlich im Kalender liegen? Ein Cut unmittelbar vor Reset könnte fast ohne langfristigen Trade-Nachteil bleiben. (2) Ist der Käufer gewillt, den vollen Salary plus echte Assets/Picks zu zahlen, wenn er nach dem Cut einen Rabatt beanspruchen kann? Der aktuelle Waiver-Wahrscheinlichkeits-Proxy ist keine echte dynamische Claim-Auktion.

Deshalb steht der Gesamtsieger von Status quo S0, Reload, Hybrid und Franchise-Cycles **noch nicht** fest. CP6q/CP6r-Mehrjahresdaten dürfen nicht unmittelbar mit dem heutigen CP7b-P0/P1/P2-Querschnitt „gerankt“ werden: sie verwenden andere Handelsphasen und individuelle Vertragspreise.

## 7. Exakter nächster Gate bis zur abschließenden Gesamtentscheidung

**CP7c muss ab jetzt bewusst *ein* gemeinsamer Multi-Year-Benchmark sein**, keine neue Feature-Iteration. Notwendige Gates vor einem Liga-Ranking: echte historische Tenure/2025–26-Eigentümer- und Vintage-Daten, tatsächliche Salary-Check-/Cap-Deadline-Kalenderereignisse, volle neue Vertragsregel für P2-Cut-Free-Agents, realistische symmetrische Buyer/Trade-/Pick-Pakete mit Verweigerungsrecht, mehrfacher Waiver-Claim, unabhängig ausgeführter Node-/CI-Test, 5–10 Jahre mit dieselben exogenen NFL-/Injury-/Cap-Futures, operativer Hard-Failure und Aufwand. Keine willkürliche starre Commissioner-Autocut-Strafe. Erst danach die sechs Nordstern-Ziele und dokumentierte Gewichtungs-Sensitivität gegenüber S0/P0/P1/P2 und vollständigen Reformpaketen bewerten.

### Gespeicherte Rohdaten

- [Seed 11 – 9 gepaarte Welten mit Events](2026-11-26-cp7b-seed11-results.json)
- [Seed 29 – 9 gepaarte Welten einschließlich Greedy-Fehlpfad](2026-11-26-cp7b-seed29-results.json)
- [Seed 47 – 9 gepaarte Welten mit Events](2026-11-26-cp7b-seed47-results.json)
- [Kanonisches Vergleichsdesign CP7a](2026-11-26-benchmark-v1.md)
- [Einzel-Contract-Probe CP7a](deadcap_contract_probe.mjs)

**Keine aktive Liga-/Salary-/Sleeper-Regel verändert; alle Ergebnisse in Forschungs-PR #1576 und Issue #1344.**
