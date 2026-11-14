# CP5b – Legaler Cap-Start, Gegenmaßnahmen und Settlement-Fenster

> **Datum:** 14.11.2026 · **Issue:** [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · **Status:** abgegrenzte kontrafaktische Mechanikprüfung, **keine** Regelentscheidung oder Einführung.  
> **Nordstern:** [sechs geschützte Designziele](../../../league-context/league-philosophy.md); von Robert als Arbeitsgrundlage fixiert, ligaweite Ratifizierung noch offen.  
> **Vorläufer:** [CP2b](2026-11-06-salary-cap-cp2b-historical-compliance.md), [CP3](2026-11-14-salary-cap-cp3-market-retention.md), [CP4](2026-11-14-salary-cap-cp4-contract-deadcap-sensitivities.md), [CP5a](2026-11-14-salary-cap-cp5a-system-windows.md).  
> **Metrik-Anhang:** [CP5b JSON](2026-11-14-salary-cap-cp5b-metrics.json).

## 1. Prüfauftrag und Trennung der Evidenz

CP5a zeigte, **wann** die jährlich kontrollierte Cap-Disziplin nachlässt; CP5b prüft, wie ein bereits legaler Startkader auf spätere historisch **beobachtete** Transaktionen reagieren könnte und welcher operativ belastbare Vollzug dafür notwendig wäre. Verglichen werden A (jährliche Deadline), F2 (Juni + verbindliches Post-FA-Settlement), F3 (F2 + eine Midseason-Prüfung) und B (permanentes Cap-Gate). Eine Änderung von Performance Salary, Positional Criticality, Rookie Contracts, Minimum oder Dead Cap ist **nicht** Teil der Vergleichsbasis.

Vier Evidenzebenen bleiben getrennt:

1. **Historische Tatsachen:** Archivierte Kader, damalige individuelle Salaries, veröffentlichte Caps, abgeschlossene Transaktionen.
2. **Deterministische Existenzbeweise:** Welche identifizierbaren Spieler-Kombinationen stellen die Cap-Konformität rechnerisch her, wenn eingetragene Starter geschützt werden?
3. **Kontrafaktische Versuche:** Historische Events *als unveränderte Anfragen* nach einem hypothetischen Settlement. Abweichende historische Folgeschritte werden bei fehlender Vorbedingung als **nicht fortsetzbar**, nicht als „unter B gescheiterte reale Transfers“, markiert.
4. **Nicht identifizierbare Wirkung:** Präferenzen, realisierbare Gebote, veränderte Waiver-Reihenfolge, Ersatzqualität, mehrjährige Aufholzeit, Champion-Wahrscheinlichkeit und Commissioner-Minuten. Diese werden **nicht** erfunden.

Die Liga hat sechs Teams, vier Playoffplätze; tatsächliche Roster-/Taxi-/IR-Zuweisungen wurden aus den datierten jeweiligen `League.json` gelesen. Die Salary-Usage zählt – analog CP2/CP5a – die **20 höchsten Salaries der einzigartigen IDs in `Teams[].Roster`**. Reserve-/Taxi-IDs sind nicht erneut addiert, wenn sie ohnehin in `Roster` enthalten sind. Die potenziell nach Cut freiwerdenden sportlichen Slots und die Zulässigkeit aller Taxi-/IR-Veränderungen sind **nicht** als bewiesen behandelt.

## 2. Start von einem legalen Zustand: 2026

### 2.1 Realer Preis-Freeze, echte Ausgangskader

Alle sechs Kader am **25.08.2026** sind mit dem realen 2026er Cap **434.255.984 $** legal. Am **09.09.2026 nach dem Free-Agent-Draft** stehen bei unveränderten September-Salaries vier Teams über dem Cap. Für die folgende *hypothetische* Settlement-Probe wurden nur im September-Roster **nicht als Starter eingetragene** Spieler als mögliche Cuts zugelassen.

| Team-ID / Team | September-Überhang | Minimal nötige Nichtstarter-Cuts | Ein mögliches Paket (keine Empfehlung) |
|---|---:|---:|---|
| 1 Mighty Giants | 0 $ | 0 | – |
| 2 Ruhr Valley Packers | 27.486.107 $ | **2** | Sam Darnold, DK Metcalf |
| 3 Just Bill | 7.406.779 $ | **1** | Josh Jacobs |
| 4 Mammoth Marauders | 41.763.737 $ | **2** | Brock Purdy, Trevor Lawrence |
| 5 DennisLACards | 0 $ | 0 | – |
| 6 TimpaBay | 45.910.392 $ | **2** | Jared Goff, Jordan Love |
| **Liga** | **122.567.015 $** | **7** | **alle eingetragenen Starter erhalten** |

Die sieben Cuts lösen den September-Überhang, jedoch **nicht kostenlos**: Es handelt sich um potenziell wertvolle QB-/RB-/WR-Absicherung, nicht um beliebige Waiver-Füller. Dass ein Spieler kein Starter in dieser einen archivierten Aufstellung war, ist kein Beleg fehlenden langfristigen sportlichen oder Trade-Werts.

**Rechenbeweis:** Bei festem Salary-Vektor ist für jede Cut-Zahl `k` die resultierende Top-20-Usage minimal, wenn aus der nicht geschützten Menge die `k` teuersten Spieler entnommen werden (monotone Ordnungsstatistik). Die erste `k`, für die Usage ≤ Cap gilt, ist daher die *exakte* minimale Cut-Zahl **unter diesem Schutzfilter**. Die Liste ist eine Existenz-/Untergrenzenprobe, kein gewählter Managerplan. Das aktive Minimum-/Dead-Cap-Konzept ist hierbei **nicht** eingeschaltet.

### 2.2 Sensitivität: teure Kernwerte nicht automatisch opfern

Als wesentlich konservativerer Schutzfilter wurden zusätzlich zu den Startern die **zehn teuersten Spieler jedes September-Kaders** geschützt (Salary-Rang ist dabei nur Proxy für Kernschutz, **kein** geprüfter sportlicher Star-Score). Dann benötigt die Liga im September **21** statt sieben Nichtstarter-Cuts: Team 2 **4**, Team 3 **1**, Team 4 **6**, Team 6 **10**; alle vier Kader sind mathematisch noch legalisierbar. Hoher Kernschutz erhöht somit die Zahl und den Verlust an Breitenoptionen, nicht automatisch die realistische Attraktivität dieser Maßnahmen.

Bei einem **separaten, unbereinigten** beobachteten November-Kader unter eingefrorenen Septemberpreisen benötigt Team 3 / Just Bill selbst nach Ausschöpfen aller 17 unter diesem gemeinsamen Schutzfilter entfernbaren Spieler noch **9.476.589 $** zusätzliche Entlastung. Unter dieser strengen Schutzannahme reicht reine Nichtkern-Bereinigung dort also **nicht** aus. Das ist keine Aussage, dass Flo tatsächlich einen bestimmten Kernspieler hätte abgeben müssen: ein Austausch, andere Trade-Vorbedingungen oder andere 2026er Manageraktionen können eine andere legale Ausgangslage erzeugen.

## 3. Event-Replay **nach** legalisiertem September-Start

### 3.1 Gemeinsames Testverfahren

- Preismodell: die archivierten **September-`Players[].Salary`**, Cap **434.255.984 $**, für alle weiteren Events eingefroren. Keine verdeckte November-Neubewertung.
- Anfangsbestand: die in Abschnitt 2.1 beispielhaft legalisierten sechs September-Kader.
- 54 vollständig abgeschlossene Ereignisse `EffectiveAt > 2026-09-09T20:33:55Z` bis 05.11.2026 aus archiviertem `Transactions.json`: **43 Waiver, 8 Free-Agent, 3 Trades**. Das ursprüngliche A-Replay rekonstruiert **alle sechs** Endroster ohne Widerspruch.
- **Atomar** pro Event: alle Drops vor allen Adds, bei Trades beide Seiten zusammen. Fehlt ein zu droppender Spieler wegen einer früheren hypothetischen Abweichung oder entsteht doppelte Ownership, wird das **ganze** Event als inkompatibel übersprungen. Es erfolgt kein erfundener Ersatzmove.
- Optionale zusätzliche Entlastung: minimal nötige Cuts aus dem **post-event** Kader, September-Starter geschützt; in der vorsichtigeren Variante ist zudem jeder im gerade betrachteten Event **hinzugekommene** Spieler geschützt. Eine Schutzmarke ist **keine** vertragliche Uncuttable-Regel. Alle ausgewiesenen Cuts sind hypothetisch und müssten vom betroffenen Manager genehmigt werden.
- Sequenzen sind **Pfad-abhängig** und nicht als alternative historisch tatsächlich beobachtete Saison zu verstehen.

### 3.2 Vergleich der mechanischen Fortführungen

| Test nach sieben Start-Cuts | Von 54 historischen Anfragen fortsetzbar/angenommen | Inkompatibel wegen geänderter Historie | Weitere Cap-Hürde bzw. Gegen-Cuts |
|---|---:|---:|---|
| **F2 ohne laufendes Gate** | **50** | **4** | Zwischen Terminen nicht zwingend legal; am 05.11. noch **3 Teams** über Cap |
| **B strikt, ohne neue Gegen-Cuts** | **43** | **8** | **3** direkt Cap-seitig abgelehnt: **2 Waiver + 1 Trade** |
| **B mit hypothetischer gleichzeitiger Nichtstarter-Entlastung** | **50** | **4** | **4** Events brauchen jeweils **1** zusätzlichen Cut (2 Waiver + 2 Trades) |
| **F3 als F2 + 05.11.-Settlement** | zunächst **50**, danach Prüftermin | **4** | **3** weitere Nichtstarter-Cuts möglich: Davante Adams, De’Von Achane, Lamar Jackson |

**Leseregel:** Die 3 unter B abgelehnten Events sind nicht die 10 CP5a-Zusatzlast-Signale: CP5a startet beim **historisch bereits über Cap liegenden** Septemberbestand und zählt Belastungserhöhungen; CP5b startet dagegen mit **anderen, legalen** Kadern. Die entstehenden 8 bzw. 4 Inkompatibilitäten zeigen, warum es **keinen** „real abgespielten B-2026-Saisonverlauf“ gibt.

**F2-Pfad vor dem November-Settlement:** Team 1 **+3.882.700 $**, Team 2 **+8.165.477 $**, Team 3 **+34.463.824 $**; die anderen drei Teams sind unter dem Freeze legal. Die drei genannten Cuts lösen diese Defizite bei Erhalt der **am 05.11. eingetragenen Starter**. Es handelt sich um *7 September- plus 3 November-Cuts entlang genau dieses F2-Szenariopfads*, **nicht** um die Summe der unabhängig auf dem echten November-Kader errechneten CP2b-Cuts.

**B-Variante mit Incoming-Schutz:** 16.09. Team 2 müsste beim Bryce-Young-Waiver hypothetisch Travis Kelce abgeben; 04.10. Team 3 für den Tyreek-Hill-Waiver Kyler Murray; 03.11. Team 3 für den CMC-Trade Kirk Cousins; 05.11. Team 1 für den D’Andre-Swift-Trade Patrick Mahomes. Diese Paket-Möglichkeiten sind mechanisch legal, **wirtschaftlich keineswegs selbstverständlich**. Gerade Mahomes und Murray zeigen, weshalb „vier mögliche Gegen-Cuts“ kein Beweis für eine funktionierende Transaktionsökonomie ist.

### 3.3 Robustheit über zwei historische Preiswelten

Zusätzlich wurden die drei archivierten 2025er Zustände mit ihrem damals tatsächlich gültigen `Players[].SalaryDollars` und `round_half_up(Top120/6)` gerechnet – ausdrücklich **nicht** mit dem 2026er Faktor 0,9. Das veröffentlichte Cap **581.658.383 $** wurde **3/3** dollar-genau reproduziert; jeweils Teams **2, 3, 4** oberhalb Cap. Unabhängige hypothetische Nichtstarter-Cut-Minima:

| Beobachteter 2025er Zustand | Über-Cap-Teams | Separate Starter-erhaltende Cut-only-Minima |
|---|---:|---:|
| 05.11.2025 | 3/6 | **5** (2 + 2 + 1) |
| 05.12.2025 | 3/6 | **5** (2 + 2 + 1) |
| 21.12.2025 | 3/6 | **4** (1 + 2 + 1) |

**Weder addieren noch als echte 2025er Cap-Maßnahmen lesen.** Für 2025 ist kein zusammenhängend beobachteter **legaler Post-Deadline-Start** mit damals gültigen Salaries gesichert; 2024er Gründungs-/Contract-Welt und der 2025→2026-Y4-Übergang fehlen. Eine echte mehrjährige kausale Franchisesimulation kann CP5b daher **nicht** behaupten.

## 4. Operatives Settlement-Protokoll: testbarer Entwurf, keine Regel

Eine belastbare F2/F3-Variante benötigt nicht nur Daten, sondern *Endzustands- und Fristenregeln*. Als zu entscheidende, **noch nicht aktive** Referenzsemantik:

1. **Normativer Freeze:** Veröffentlichter Salary-Vektor inklusive Top120-Cap, Datenzeitpunkt, Season, Modellversion und Hash/Commit; dieselben festgelegten Dollarpreise gelten für alle sechs Teams im betreffenden Settlement. Ein reiner **Cap-Kontrolltermin ist kein neuer Salary-Zyklus**.
2. **Eingang:** Vor dem geplanten Post-FA-Draft-Check werden tatsächliche, abgeschlossene Draft-Picks und der autoritative Sleeper-Kader-Stand eingefroren, einschließlich Roster/Taxi/Reserve ohne Double-Counting. Unfertige Waiver-/Trade-/Pick-Bundles bleiben getrennt. Eine App-Anzeige ist keine Freigabe.
3. **Soft Deadline → Grace → Hard Settlement:** Jeder Manager erhält einen reproduzierbaren Überhang und einen klaren Zeitraum für *freiwillige* Cuts, Trades oder gemeinsam abgestimmte Gegenbewegungen. Exakte Dauer, Uhrzeit und Ausnahmen gehören in einen späteren Ligabeschluss; CP5b erfindet sie nicht.
4. **Atomare Pakete:** Der gesamte Trade mit beiden Teamseiten und allen player-/pickbezogenen Änderungen wird nach allen Drops und Adds geprüft; bei gleichzeitigen Waiver-Gegenabgängen werden Reserve-/Taxi-Eignung, eventuelle Roster-Limits und Ownership separat gegen Sleeper geprüft. Kein Teil-Commit, kein automatisches Verschieben fremder Spieler.
5. **Konfliktfall:** Nach der Hard Deadline muss festgelegt sein, ob neue Adds/Trades gesperrt, Maßnahmen zurückgesetzt oder ein klar definierter Commissioner-Entscheid nötig wird. **Kein automatischer Starter-Cut** und kein stilles „ist schon legal“ wegen einer bloß im App-Dashboard angezeigten Rechnung. Offene Appeals/Salary-Korrekturen müssen ein Audit-Protokoll haben.
6. **Dead Cap / Refresh:** Die bisherige *Konzeptentscheidung* „Dead Cap endet am nächsten regulären Salary Check“ bleibt erhalten. Bei der **jährlichen** Salary-/Dead-Cap-Grenze ist weiterhin **unbeschlossen**, ob zuerst unter altem Dead Cap geprüft und danach resettet wird und ob Dead Cap additiv oder als virtuelle Top20-Slots zählt. Der **zusätzliche F2/F3-Kontrolltermin darf nicht stillschweigend erneut Salary oder Dead Cap resetten**. Diese Punkte sind Ligaentscheidungs-Gates, nicht Implementierungsdetails.

**F2-Fenster:** bestehende jährliche Deadline und einmaliger Post-FA-Draft-Check, letzterer **nach** verbuchtem Draft und zugehörigem Grace-Fenster. **F3:** zusätzlich ein **datierter Midseason-Check** (05.11. dient hier nur als archivierter Testanker, kein empfohlener Termin). **B:** jeder wertverändernde Add-/Drop-/Trade-/Draft-Bundle-Commit erfordert ein sicheres Gate auf derselben Freeze-Basis, inklusive Drift-Checks bei Salary-Refresh, Taxi/IR und Dead Cap.

## 5. Reale Sleeper-/App-Grenzen und Verwaltungsaufwand

| Funktion | Aus offiziell verifizierten Quellen ableitbar | Konsequenz |
|---|---|---|
| Historische/current Roster, Transactions, Drafts | Öffentliche [Sleeper-API](https://docs.sleeper.com/) dokumentiert lesende Endpunkte, **keine Schreib-API** | Pull-/Abgleich-/Audit möglich; **keine** selbsttätige Waiver-Ablehnung oder atomare Salary-Trade-Freigabe über diese API |
| Waiver-Zeitfenster/Locks | Offizielle [Waiver-Hilfe](https://support.sleeper.com/en/articles/3978868-waivers-for-regular-season-playoffs) und [Lock-Anleitung](https://support.sleeper.com/en/articles/4037431-why-can-t-i-drop-players) | Für feste Settlement-Termine potenziell nutzbare Organisationsmittel; **kein** Cap-spezifisches Validierungs-Gate |
| Trades | Offizielle [Trade-Hilfe](https://support.sleeper.com/en/articles/3188802-how-to-trade) und [Commissioner-Trade](https://support.sleeper.com/en/articles/4033467-how-do-i-force-a-trade-through) | Moderation möglich; ob die konkreten Liga-Settings/Genehmigungspfade verlässlich zu **allen** Arten von Deals passen, vor Umsetzung prüfen |
| Eigene App/Derived Data | Exakte historische Checks mit archivierten Salaries vorgeführt | Read-only Cap-Vorschau, Warnungen und unveränderliche Prüfprotokolle möglich; keine transaktionale Sleeper-Sperre nachgewiesen |
| Operator-Aufwand | 2026er Archiv: **54** vollständige Event-Bundles, davon **46 mit Adds**; zwei bzw. drei geplante Termine je **6 Teams** als F2/F3-Basis | **Keine** gemessenen Minuten, Zahl der Einsprüche, Retry-/Reversal-Fälle, manueller Touches oder echte Automatisierungsquote. 54 ≠ 54 manuelle Aktionen |

Die tatsächlich archivierten Liga-Settings verändern sich zwischen Preseason und November (u. a. `disable_adds`, Waiver-Konfiguration, Reserve-Slots, `trade_deadline`). Keine der beiden as-of-Konfigurationen wird als dauerhaft gültige 2027er Systemeinstellung fortgeschrieben. Für eine Pilotierung wären Settings, API-Latenz, Draft-/Waiver-Finality, Identitäten, Ghost-Bundles, Error-/Appeal-Handling und Wiederholung bei gleichzeitigen Events live zu testen.

## 6. Gegenüberstellung mit dem geschützten Sechs-Ziele-Nordstern

| Ziel | A jährlich | F2 / F3 Settlement | B permanentes Gate |
|---|---|---|---|
| **1 – Langfristige Aufholbarkeit** | Verifizierte Jahresbereinigung, danach 2025/26 wieder zulässige Überhänge; mehrjährige Titelchancen ungemessen | Begrenzen zusätzliche Aufrüstung an 1–2 mehr Zeitpunkten, erzwingen aber keine nachweisliche Aufholzeit | Verhindert *unter zulässigem Start* neue Überhänge nach jedem erfassten Event; Erholung/Championship-Wahrscheinlichkeit ungemessen |
| **2 – Management belohnen** | Höhere Freiheit, aber weniger wiederkehrende wirtschaftliche Knappheit | Planbare Jahres-/Midseason-Entscheidungen; sept. 7 Nichtstarter-Cuts möglich, trotzdem Verlust von wertvollem QB-/WR-/RB-Wert | Aktive Budgetierung wertvoll; starre Gates könnten auch freiwillig angebotene, strategisch sinnvolle Trades mit zwei legalisierbaren Teams organisatorisch erschweren |
| **3 – Gratisvorteile nicht zementieren** | Eine reale Deadline, anschließend mehrere Monate neues Akkumulationsfenster | Weitere Checks reduzieren Dauer des unkontrollierten Überhangs, zwischen ihnen bleibt die Lücke | Begrenzen ständiges Einlagern ohne wirtschaftlichen Gegenzug; kostengünstiger Rookie-/Pick-Surplus über Y1–4 bleibt **getrennt** |
| **4 – Wirtschaftliche Konsequenzen** | 2026 Juni alle Teams legal; Sep 122,57 Mio. $ aggregierter positiver Überhang | Sep-Settlement löst 4 Team-Defizite; F3 kann 3 neue F2-Pfad-Defizite abräumen | 3 direkte Blockaden im starren Verlauf bzw. 4 Pakete mit rechnerischem Offset; keine realisierten Transaktions- oder Titelwirkungen |
| **5 – Strategische Freiheit** | Große In-Season-Flexibilität | Geplante Reload-/Buyer-/Seller-Entscheidungen, mögliche Deadline-Effekte, Risiko späterer Gratis-Aufrüstung | Laufende Cap-Raum-Optionen und härterer Buyer-Markt; kann sich als *niedrige Trade-Liquidität* statt gewünschte freiwillige Asset-Verschiebung äußern |
| **6 – Verlässlicher Vollzug** | Bekannte Jahresprüfung | 2/3 jeweils sechsfache geplante Prüfungen plus definierte Ausnahmen und Deadline-Sperre; organisatorisch realistischer, aber noch ungetestet | 54 historische Bundle-Kandidaten, atomare Vorabprüfung aller relevanten Adds/Trades nötig; Sleeper-Public-API rein lesend, Integrations-/Operator-Kosten unbelegt |

**Kein numerischer Gewinner-Score:** Ein Score würde derzeit fehlende Evidenz für Titel-Aufholbarkeit, Käufer-Nachfrage, echte Managerreaktionen und Aufwand vortäuschen. Ein gutes Management darf wiederholt gewinnen; erzwungene Gleichverteilung ist gerade **nicht** das Ziel. Der alternative Criticality-Kandidat C und bestätigte Vertragskonzepte sind **preisliche bzw. vertragliche** getrennte Sensitivitäten; kein vermischtes „B+C+DeadCap+Rookie“-Resultat.

## 7. QA, Provenienz, Handoff

**Quellenfixierung:** 2026: `League.json` bei 25.08. `539aae40da3de444000805cea3170a116fae129d`, 09.09. `b40956172a704ff616008d7835f527b86f128063`, 05.11. `799be2a25203f18face8185303f32b31be3d40a7`; September-`Players.json` Blob `f8cc9a97cbe19eed6907a7630da053052a35e577`, November-`Transactions.json` Blob `0aa85766a962a9d499fe5610a269771dd3b02ce1`. 2025 bei `ea9d7666ad655ccf9a45dafb3463046cb0c49908`, `e7afd83ab8f141397d05d151362a1f64409c153f`, `0ede4b63ab6f424bd854112ca7f2c551b68af0d7`; jeweils gleicher Commit für `League` und `Players`.

**Validierte Invarianten in der unabhängigen JS-/Connector-Forschungsausführung:** 2025 Caps 3/3 identisch, alle 2025er Checks mit damals `SalaryDollars`; 2026 Sep-Cap-Check reproduziert 4/6 und **122.567.015 $** Überhang; 2026 Original-Event-Replay **54/54** ohne fehlende Drops oder Doppelownership, **6/6** Endroster identisch; kontrafaktische Varianten auf *legalem* Start und Cap 434.255.984 $; alle ausgewiesenen F2-/F3-/B-Offset-Endroster cap-konform nach dem jeweiligen Enforcement; 2025er Cut-Proben separat auf damaligen Preisen.

**Restunsicherheit für CP5/CP6:** (a) Fehlen eines mehrjährigen, exakt historisch legalen 2024/2025 Starts mit allen Rookie-/Year4-/Trade-Pick-Asset-Preisen; (b) Managerverhalten, Gegnernachfrage und Kosten des Verlusts von Nichtstartern; (c) echte Operator-Minuten, Settings und Pre-Commit-Waiver-Sicherheit; (d) Draft-/IR-/Taxi-Atomizität; (e) Dead-Cap-Top20-Abrechnung und jährliche Prüfreihenfolge; (f) keine 2027/28-Aufhol- oder Champion-Wahrscheinlichkeiten; (g) vollständige Zustimmung aller sechs Manager zum Nordstern offen.

**CP5b-Checkpoint:** Die **mechanisch überprüfbaren** legalen Starts, Path-Divergenzen und Settlement-Vollzugsgrenzen sind dokumentiert. **Nicht** abgeschlossen ist die **kausale, mehrjährige** ökonomische Bewertung. Vor CP6 zuerst die Entscheidungsschwelle klären: Reicht F2/F3 bei empirisch erreichbarer praktischer Kontrolle als minimaler Eingriff, oder belegt ein kontrollierter Test einen spezifischen Zusatznutzen von B bei akzeptablen Vollzugskosten? Criticality und neue Contracts nur dann zuschalten, wenn ein isolierter Mehrwert nachweisbar wird. Kein Claim- oder Auto-Cut-Modell begründet, keine aktive Regel geändert.
