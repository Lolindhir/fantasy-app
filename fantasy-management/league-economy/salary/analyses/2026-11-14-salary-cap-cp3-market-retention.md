# CP3 – Käufermarkt, Cut/Re-Acquisition und Rookie-Retention

> **Forschungsstand 14.11.2026 · [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · Anschluss an [CP1](2026-11-05-salary-cap-cp1-baseline.md), [CP2a](2026-11-05-salary-cap-cp2-abc-stress-test.md) und [CP2b](2026-11-06-salary-cap-cp2b-historical-compliance.md).** Historische Evidenz plus streng markierte kontrafaktische Cap-/Vertrags-Sensitivitäten; **kein Ligabeschluss, keine produktive Regeländerung**.

## 1. Kurzurteil und Evidenzstufen

1. **Tatsächliche Nachfrage ist beobachtbar, aber nicht zu damaligen Tradepreisen:** Flo gab am 09.06.2026 acht Spieler ab; sieben davon wurden im späteren 2026er Free-Agent-Draft gewählt, darunter Brock Purdy 1.03. Das belegt Interesse an den Spielern *nach* ihrem Cut, nicht die damalige Bereitschaft oder Cap-Fähigkeit zu einem Trade gegen Picks.
2. **Der Markt ist als Gesamtsystem enger als 40 Einzeltests suggerieren:** Am 29.06. sind für die acht Spieler bei fünf potenziellen Käufern **13 von 40** Spieler-Käufer-Paaren ohne Gegenabgang cap-fähig. Werden die acht Spieler aber **gemeinsam** auf die fünf tatsächlich legalen Juni-Kader verteilt, können ohne weitere Cuts **höchstens vier von acht** aufgenommen werden. Mit je einem Cut außerhalb des salary-basierten Top-10-Kerns pro Käufer sind es höchstens sieben; mit je zwei solchen Cuts acht. Dies sind *optimistische Cap-Existenzgrenzen*, keine Trades, Angebote oder sportlich akzeptablen Kader.
3. **Einzelfall Purdy ist aussagekräftig:** Für Purdy gibt es **0/5** direkte Käufer. Jede der fünf Käuferseiten könnte ihn rechnerisch nach **einem beliebigen** eigenen Cut aufnehmen, aber vier der fünf Käufer benötigen innerhalb der vereinfachten Probe entweder einen Abgang aus dem jeweiligen Top-10-Salary-Kern oder mehr als zwei Cuts außerhalb dieses Kerns. Unter der gemeinsamen 1-Nichtkern-Cut-Grenze bleibt Purdy unverteilt.
4. **Re-Acquisition ist real, aber kein sicherer Profit-/Handelsbeleg:** Erfolgreiche Cut→Add-Bewegungen desselben oder eines anderen Teams treten in 2024–26 auf. Das 2026er Transaktionsprotokoll bis 05.11. zeigt z. B. vier erste Wiederaufnahmen beim cuttenden Team und 17 erste Aufnahmen durch andere Teams nach einem Drop. Die FA-Draft-Bewegungen sind ein eigener Mechanismus und werden nicht mit Waiver-Adds vermischt.
5. **Rookies werden nicht automatisch drei Jahre gehalten:** Von 30 Rookie-Picks des Jahrgangs 2025 sind am 05.11.2026 20 ligaweit und 14 beim ursprünglichen Draft-Team; für den Jahrgang 2026 27 beziehungsweise 23. Dokumentiert sind Cut- und Trade-Abgänge, nicht allein spontane Endkaderunterschiede.
6. **Konzept-Verträge sind rechnerisch rekonstruierbar, aber ein realisierter Surplus nicht:** Für alle 60 Rookie-Picks 2025/26 sind Fantasy-/NFL-Draft-Ränge zuordenbar. Das verabredete **nicht aktive** 65/35-Year-1-Modell und die Y2/Y3-Faktoren lassen sich als Anteile des maßgeblichen Vorjahres-Caps berechnen. Ein Vorteil gegenüber einem hypothetisch *sonst* zu zahlenden Performance-Salary und sein konkreter Top-20-Cap-Effekt verlangen jedoch vollständige Gegenmodelle und weitere NFL-Saisons.
7. **Marktverhalten unter permanentem Cap bleibt unbekannt:** Die 2026 realen Deals, Käuferkader, Abgaben und Draftpreise entstanden bei **nur jährlicher Cap-Deadline**, ohne permanenten Cap-Vollzug. Kein retrospektiver Verstoß, kein erfundenes hypothetisches Angebot.

**Vorläufige Einordnung:** Das permanente Cap *könnte* wertvolle Tiefe und Investitionen stärker bepreisen, ohne etablierte Stars unmittelbar zwangsweise zu verlieren. Ob daraus ein funktionierender Trade-Markt statt Cuts/FA-Zugängen entsteht, ist **nicht empirisch nachgewiesen**. Ein teureres Criticality-Modell könnte den Käufermarkt sogar stärker einengen. Die sechs zuletzt in #1344 präzisierten Ziele – insbesondere langfristige Aufholbarkeit **und** einfacher, verlässlich umsetzbarer Vollzug – bleiben Prüfmaßstab.

## 2. Quellen, Stichtage und Zählregeln

| Aspekt | Verwendete Quellen / Freeze |
|---|---|
| Historischer Salary-Markt | **29.06.2026:** Commit `85e22feb064fdaf2257d6c3149c8d1655ada0908`, jeweils `public/data/League.json` und `public/data/Players.json` aus **demselben Commit**, Players-Blob `21001d6c0819dbbcb3deff084d63fe377714541c`; Cap **434.255.984 $** |
| Flo-Kandidaten | Roster 07.06. `5b4ed63172deae79759e7150f8511bd2ea3edb4e` minus 09.06. `7ece134fec39741aba8e82bda554f8f13e8bead4`; genau **acht** IDs |
| Historische Transaktionen und Drafts | `public/data/Transactions.json`, `public/data/past_seasons/Transactions/Transactions_2024.json`, `.../Transactions_2025.json`, `public/data/Drafts.json`, `public/data/past_seasons/Drafts/Drafts_2025.json`; **alle mit Ref `799be2a25203f18face8185303f32b31be3d40a7` vom 05.11.2026**, keine nachträglichen Week-9/10-Transaktionen |
| Kader-/Retention-Zeitachsen | `data-source/leagues/nfl-reise/seasons/2025/rosters.json` (2025er Abschlussroster) und `public/data/League.json` (05.11.-Snapshot), derselbe 05.11.-Ref |
| NFL-/Fantasy-Rookie-Draft | `data-source/nfl/draft/{2025,2026}.json`, `data-source/leagues/nfl-reise/seasons/{2025,2026}/drafts.json`; Join über canonical player ID und Sleeper-Player-ID, 05.11.-Ref |
| Produktionskontext | `public/data/Players.json` vom 05.11., Blob `6459aef56b661eb9f3f83ac6c2516577d328cf93`; NFL-Saisondaten und damalige Salaries, keine Zukunftsprognosen |
| Regel-/Konzeptbasis | `salary-dead-cap-concept.md`, `salary-system-redesign-concept.md`, `team-window-strategy-concept.md`, `league-economy/AGENTS.md`, aktueller Body von #1344 |

**Cap-Rechenregel:** Je Team die **20 teuersten einzigartigen** IDs aus `Teams[].Roster` summieren. Taxi/Reserve sind bereits in `Roster` und werden nicht erneut hinzugefügt. Nach jedem hypothetischen Add/Cut wird Top 20 erneut sortiert. Alle fünf Käufer liegen am 29.06. unter dem echten veröffentlichten Cap. Für Flo gilt die CP2b-historisch exakte 07.→09.06.-Entlastung von **119.838.611 $**; der ältere CP1-Oktoberpreis-Proxy bleibt historische Methodik, nicht diese Junizahl.

**Unterschiede der Testwelten:** Hier wird für die Käuferprüfung ausschließlich der historische A-Preisstand als *hypothetische B-Cap-Prüfung* benutzt. Es wird weder der erst spätere Oktober-Criticality-Vektor C auf Juni als damalige Realität ausgegeben noch Rookie/Dead Cap, Salary-Retention-Trades, Preisrefresh oder neue Draft-/Claim-Regeln stillschweigend aktiviert. 29.06. ist ein **nach Flos 09.06.-Cuts bereits bereinigter Käufermarkt**, kein Beleg, dass dieselbe Kapazität **vor** dem Cut für Trades existiert hätte.

## 3. CP3a – Käuferfähigkeit eines einzelnen Spielers

Die folgenden Zahlen stellen pro Kandidat fünf **separat** geprüfte Käufer vor. Eine Prüfung geht von einem unmodifizierten 29.06.-Kader aus; mehrere gleichzeitige Käufe teilen sich diese Reserve nicht automatisch.

| Abgabe Flo | Salary 29.06., Mio. $ | Direkte Käufer ohne Cut | Mit höchstens 1 eigenem Cut (auch Top-10-Kern erlaubt) |
|---|---:|---:|---:|
| Alvin Kamara | 24,37 | 1/5 | 5/5 |
| George Kittle | 23,01 | 2/5 | 5/5 |
| Sam Darnold | 24,16 | 1/5 | 5/5 |
| Terry McLaurin | 18,97 | 2/5 | 5/5 |
| Travis Etienne | 22,83 | 2/5 | 5/5 |
| Javonte Williams | 16,95 | 2/5 | 5/5 |
| Romeo Doubs | 12,88 | 3/5 | 5/5 |
| Brock Purdy | 41,51 | **0/5** | 5/5 |
| **Insgesamt** | | **13/40** | **40/40** |

`Mit 1 Cut` ist eine ausgesprochen **großzügige** Existenzprobe: Sie erlaubt notfalls den Verlust eines enorm wertvollen Spielers. Dass jede Aufnahme damit *möglich* wird, sagt nichts über realistische Managerpräferenzen. Es gibt **keinen** empirischen Beleg für 40 zahlungswillige Käufer.

### 3.1 Top-10-Salary-Kern-Sensitivität je Spieler-Käufer-Paar

Die zehn teuersten Käufer-Spieler bleiben als **rein salary-basierter** Schutzkern erhalten; das ist **keine Qualitätsrangliste**, schon gar keine im Juni verbindliche Starterliste. Die übrigen Spieler dürfen in der Probe entfernt werden; weder sportlicher Ersatz noch Roster-Kapazität, Taxi/IR-Lock oder konkrete Tradegegenleistung werden optimiert.

| Kleinste zulässige Entlastung zum Add | Spieler-Käufer-Paare |
|---|---:|
| Ohne Cut direkt legal | 13 |
| Genau 1 Nicht-Top-10-Cut genügt | 15 |
| Erst 2 Nicht-Top-10-Cuts genügen | 8 |
| Mit bis zu 2 Nicht-Top-10-Cuts nicht erreichbar | **4** |
| **Summe** | **40** |

Die vier zuletzt genannten Paare betreffen **Purdy** bei Mighty Giants, Packers, Jan und TimpaBay. Für Purdy ist ein einzelner Nichtkern-Cut nur bei Dennis ausreichend. Ein **beliebiger** Einzel-Cut aus dem gesamten Roster wäre auch bei den vier anderen Teams finanzierbar, müsste dann aber in den salary-basierten Top-10-Kern greifen. Beispiele minimaler Salary-Abgänge aus der mechanischen Ein-Cut-Probe sind Saquon Barkley (Mighty Giants), De'Von Achane (Packers), Justin Jefferson (Jan) und CeeDee Lamb (TimpaBay). Das sind ausdrücklich **keine Cut-Empfehlungen**.

### 3.2 Gemeinsames Market-Clearing statt 40 unabhängiger Adds

Für jeden Käufer werden alle **256 Teilmengen** der acht Kandidaten gebildet. Die Cap-Kosten jeder Teilmenge werden gemeinsam (Top-20-Neuberechnung) geprüft. Anschließend werden disjunkte Teilmengen auf die fünf Käufer verteilt; jeder der acht Spieler darf höchstens einmal zugeteilt werden. Ziel ist ausschließlich, die **Anzahl** aufnehmbarer Spieler zu maximieren, ohne einen Tradepreis oder Nachfragewillen zu erfinden.

| Je Käufer erlaubte zusätzliche Abgänge | Maximal gleichzeitig aufnehmbar |
|---|---:|
| **0** | **4/8** |
| **Bis 1** Spieler **außerhalb** Käufer-Top-10-Salary | **7/8** |
| **Bis 2** Spieler **außerhalb** Käufer-Top-10-Salary | **8/8** |

Eine mögliche 0-Cut-Zuteilung ist **Kittle → Jan** sowie **McLaurin, Javonte Williams, Doubs → Dennis**. Auch bei einem Nicht-Top-10-Cut je Käufer bleibt in jeder optimalen 7/8-Variante **mindestens ein Spieler** nicht aufgenommen; die dokumentierte berechnete Beispielzuordnung lässt Purdy außen vor. Bei zwei Nichtkern-Cuts je Käufer existiert eine rein rechnerische vollständige Acht-Spieler-Verteilung. Sie verursacht aber zusätzliche, wirtschaftlich nicht bewertete Kaderverluste.

**Methodische Grenzen:** Keine Annahme über gegenseitige Verhandlung, Präferenzen, Spielerbedarf, zukünftige NFL-Verfügbarkeit, Picks, Startaufstellung, Rosterlimits, Free-Agent-Gegenbewegungen oder die Akzeptanz von Gegenabgängen. Das optimistische Maximum ist kein erwartbarer Trade- oder Draft-Ausgang; vor allem kann 29.06.-Clearance nicht rückwärts als realer Käufermarkt am 09.06. behauptet werden. Die 2026er Manager haben sich tatsächlich **ohne** ganzjährigen Cap-Zwang positioniert.

## 4. CP3b – Cut, Trade, FA-Draft und Wiederaufnahme getrennt

### 4.1 Historisch nachgewiesene Flo-Umverteilung

Die acht Cuts datieren auf den **09.06.2026** und sind in den abgeschlossenen Transaktionen belegt. Sieben Spieler erscheinen anschließend als gewählte Free Agents im Draft:

| Spieler | 2026er FA-Draft | Draft-Team-ID |
|---|---:|---:|
| Javonte Williams | **1.02** | 6 |
| Brock Purdy | **1.03** | 4 |
| Travis Etienne | **1.04** | 5 |
| Terry McLaurin | **2.01** | 5 |
| George Kittle | **2.03** | 4 |
| Romeo Doubs | **2.05** | 6 |
| Sam Darnold | **5.05** | 2 |
| Alvin Kamara | **nicht gedraftet** | – |

Das ist **ex-post-Nachfrage im FA-Draft** für 7/8 Spieler, aber kein ex-ante-Angebot für einen Trade. FA-Picks wurden in einem anderen Markt abgegeben als die gegen einen Veteranen verhandelten **Rookie-/Zukunftspicks**. Der FA-Draft und die Käuferroster sind durch die geltende **jährliche** Cap-Deadline und die fehlende In-Season-Compliance geprägt; unter B oder C könnten sowohl Draft-Reihenfolge als auch Teilnehmer- und Free-Agent-Pool anders aussehen.

### 4.2 Beobachtete Move-Typen 2024–2026

**Zählregel:** Nur `Status=complete`; reine Cuts sind Transaktionen mit Drops, ohne Adds, nicht vom Typ Trade. Für eine vereinfachte Re-Acquisition-Analyse werden alle nicht-Trade-**Drop-Einträge pro Spieler** chronologisch dem **ersten** späteren nicht-Trade-Add desselben Spielers **innerhalb derselben Saison** zugeordnet. Draft-Picks werden hier **nicht** als Adds gezählt. Identische Spieler können mehrfach auftreten; dies sind Bewegungsereignisse und keine unabhängigen Franchise-Entscheidungen.

| Saison / Datenfreeze | Abgeschlossen | Trades | Reine Cut-Transaktionen | Nicht-Trade-Drop-Einträge | Nächster Add durch gleiches Team | Nächster Add durch anderes Team |
|---|---:|---:|---:|---:|---:|---:|
| 2024 final | 132 | 7 | 7 | 118 | 19 | 27 |
| 2025 final | 127 | 2 | 21 | 104 | 9 | 23 |
| 2026 bis 05.11. | 121 | 11 | 66 | 91 | 4 | 17 |

2024 war ein initialer 162-Pick-Liga-/Free-Agent-Draft, kein gleichartiger Rookie-Draft. 2026 ist hier eine **unvollständige** Saison. Die Verteilungen sind daher weder eine zeitbereinigte Trendanalyse noch Beweis, dass ein permanenter Cap Cuts in Trades verwandelt. Sie demonstrieren lediglich die tatsächlich genutzten **verschiedenen** Transaktionskanäle.

**Praktische Beispiele 2026 für Re-Acquisition beim selben Team:** Ka'imi Fairbairn (Kader-ID 1, 29.10. Cut → 02.11. Add), daneben drei weitere erste erfolgreiche Wiederaufnahmen nach vorangegangenem Cut. Ein wiederaufgenommener Spieler ist nicht zwingend wieder langfristig gehalten. Entsprechende Mehrfach-Cut- und Floor-Behandlung würde erst mit dem **nicht aktiven** Retained-Salary-Konzept greifen.

### 4.3 Retained Salary / Dead Cap als **separater** späterer Mechaniktest

Der bestätigte Konzeptentwurf, **nicht aktiv**, enthält:
- Dead Cap beim Cut nach ununterbrochener Team-Tenure 0/1/2/3+ von **50/30/15/5 %**, nur innerhalb **eines** Salary-Zyklus; Reset am nächsten regulären Salary Check.
- Der alte Manager behält einen Salary-Anteil, der aktive Spieler wird für den nächsten Aufnehmer entsprechend günstiger, begrenzt durch das Minimum.
- Bei Trade ist **keine** zusätzliche verhandelbare Salary-Retention beschlossen; daher keine stillschweigende Trade-Salary-Übernahme erfinden.
- Ohne Floor als **illustratives** Rechenbeispiel: Purdy bei 29.06.-Salary **41,51 Mio. $** wäre nach einem hypothetischen 50-%-Cut für den *neuen* Aufnehmer etwa **20,75 Mio. $** teuer; der alte Manager trüge zugleich etwa 20,75 Mio. $ Dead Cap. Das ist **kein historischer Juni-Fall**, keine abgesicherte tatsächliche Flo-Tenure und wegen der offenen Top-N-/Floor-Semantik **keine vollständige Cap-Compliance-Simulation**.

**Marktspannung:** Ein Trade kann dem Verkäufer künftig Dead Cap und den ersatzlosen Verlust des Assets ersparen; ein nachfolgender Cut kann für den Käufer den aktiven Preis senken. Ohne Gegenangebote kann nicht beantwortet werden, wann der Verkaufserlös den Käufernachteil gegenüber Warten/FA aufwiegt. CP4 darf den bereits bestätigten Ein-Zyklus-Mechanismus getrennt hinzufügen; weder eine Mehrjahresstrafe noch neue verhandelbare Trade-Retention sind dadurch beschlossen.

## 5. CP3c – Rookie-Retention, Transaktionsunterbrechungen und Contract-Outlook

### 5.1 Historischer Bestand und tatsächliche Abgänge

Die Draft-Teams werden über die **tatsächlich gepickten Spieler** (`Drafts[].Picks`, `CurrentOwnerRosterID` zum Pick) und Sleeper-Spieler-ID zu den datierten 2025-/2026-Kadern sowie den vollständigen erfolgreichen Transaktionslogs verbunden.

| Kennzahl | Rookie 2025 | Rookie 2026 |
|---|---:|---:|
| Erfolgreiche Picks | 30 | 30 |
| 2025er Abschlussroster: noch beim Draft-Team | **23** | nicht anwendbar |
| 05.11.2026 ligaweit gehalten | **20** | **27** |
| 05.11.2026 noch beim ursprünglichen Draft-Team | **14** | **23** |
| Vom Draft-Team durch dokumentierten Nicht-Trade-Cut abgegangen | **15** | **5** |
| Vom Draft-Team durch dokumentierten Trade abgegangen | **1** | **2** |
| Dokumentiert mindestens einmal vom Draft-Team nach dessen eigenem Cut wiederaufgenommen | **1** | **0** |

Die Cut-/Trade-Abgangsereignisse reichen über 2025–05.11.2026 bzw. Rookie-2026-Draft–05.11.2026. Für den 2025er Jahrgang wurde Shedeur Sanders vom ursprünglichen Team nach Unterbrechung wieder aufgenommen und später erneut entlassen. 2026er Beispiele: Germie Bernard wurde von Flo gecuttet und von Mighty Giants aufgenommen; Emmett Johnson von Flo gecuttet und von Dennis aufgenommen; Antonio Williams und Kaelon Black wechselten durch Trades. Damit ist `am Enddatum beim Draft-Team` **nicht** identisch mit `lückenlose Vertrags-/Team-Tenure`.

Die 2024er 162er Gründungsdraft-Kohorte darf nicht als identischer Rookie-Draft-Jahrgang in die 30/30-Auswertung eingehen. Das Folgejahr 2027/2028 und der erstmalige Year-4-Übergang sind für die untersuchten 2025-/2026-Kohorten noch nicht beobachtet.

### 5.2 Reproduktion der **nicht aktiven** Rookie-Contract-Kurve

Die bestätigte Formel lautet:

```text
DraftPct(r,N) = 0,30 % + 3,20 % × (1 − (r−1)/(N−1))^3,5
für undrafted-Signal: 0,25 %
Y1Pct = 65 % × FantasyDraftPct + 35 % × NFLDraftPct
Y1Salary = Y1Pct × maßgebliches Vorjahres-Salary-Cap
Year 2 = 1,25 × festes Y1-Dollar-Salary
Year 3 = 1,50 × festes Y1-Dollar-Salary
Year 4 = reguläres Performance-Salary (noch nicht beobachtet)
```

`N_Fantasy=30` in beiden Jahren; `N_NFL=86` im Draft 2025 und `80` im Draft 2026, jeweils nur NFL-gedraftete QB/RB/WR/TE nach NFL Overall Pick zu eigenen NFL-Position-Rängen neu sortiert. **60/60** Spieler zwischen Fantasy-Draft, canonical NFL-Player und NFL-Draft erfolgreich gematcht; **0** fehlende NFL-Draft-Ränge. Dies ist ein erneutes eigenständiges Nachrechnen der **Konzeptformel**, nicht die produktive Rookie-Salary.

| Jahrgang | Niedrigstes Y1-Salary in % des einschlägigen Vorjahres-Caps | Median der 30 Y1-Prozente | Höchstes Y1-Prozent |
|---|---:|---:|---:|
| 2025 | 0,300 % | ca. 0,993 % | 3,410 % |
| 2026 | 0,342 % | ca. 0,853 % | 3,404 % |

**Konkrete Vertrags-Beispiele als Prozentwerte, keine bereits gezahlten Dollar:**

| Pick und Spieler | Y1-Pct | Y2-Pct | Y3-Pct | Beleg zur Entwicklung, nicht Forecast |
|---|---:|---:|---:|---|
| 2025 Pick 1.01 Ashton Jeanty | 3,410 % | 4,263 % | 5,116 % | 2025 14,54 PPG; bis 05.11.2026 16,54 PPG (8 Spiele) |
| 2025 Pick 3.02 Bhayshul Tuten (Overall 14) | 0,774 % | 0,967 % | 1,161 % | 2025 5,74 PPG; bis 05.11.2026 16,90 PPG (7 Spiele) |
| 2026 Pick 1.01 Carnell Tate | 3,404 % | 4,255 % | 5,106 % | bis 05.11.2026 11,04 PPG (7 Spiele) |
| 2026 Pick 1.02 Jeremiyah Love | 3,211 % | 4,013 % | 4,816 % | bis 05.11.2026 8,90 PPG (6 Spiele) |

Eine 0,774-%-Rookie-Verpflichtung kann sich nach einem Breakout günstig **anfühlen**, aber der echte *ökonomische Surplus* ist nur `vergleichbares alternatives Salary − Contract-Salary`, **nach** Top-20-Marginalkosten, verfügbarer Roster-/Taxi-Kapazität, Opportunity Cost und tatsächlichem Marktwert. Ein Draft-Pick am oberen Ende kostet im Konzept schon im zweiten Jahr einen substanziellen Prozentsatz des Caps. Nicht jeder Rookie ist automatisch ein wirtschaftlicher Gewinn. Vergleichs-Dollarcaps, tatsächliche Zukunftsleistung und ein legaler kontrafaktischer Gesamtmarkt sind für diese Kohorten kein vollständig beobachtetes Faktum.

**Aktive Baseline:** Die 30 Rookies des 2026er Rookie-Drafts haben im eingefrorenen 05.11.-Players-Stand **0 $** veröffentlichtes Salary; das ist *nicht* die bestätigte Rookie-Vertragsformel. `SalaryProjected` ist keine vertragliche Zahlung und wird hier nicht mit dem festen Y1/Y2/Y3-Dollar-Vertrag gleichgesetzt.

## 6. CP3d – Win-now-Deals und mehrjährige Aufholbarkeit

### 6.1 Datierter beobachteter Trade: Flo ↔ Dennis, 03.11.2026

Die abgeschlossene Transaktion dokumentiert:
- **Flo / Just Bill (ID 3)** bekommt **Christian McCaffrey** und einen **2027 Rookie Round-3-Pick** mit Ursprung Dennis (Pick `2027_Rookie_R3_OO5`).
- **Dennis (ID 5)** bekommt **Braelon Allen**, **Flos 2027 Rookie Round 1** (`2027_Rookie_R1_OO3`) und **Flos 2027 Rookie Round 2** (`2027_Rookie_R2_OO3`).

Die vollständigen Pick-Identitäten sind belegt, aber künftige konkrete Slotwerte, ex-ante Verhandlungsspielraum und zukünftige Spielergebnisse **nicht**. Das ist ein beobachteter Austausch kurzfristiger Starproduktion gegen mehrere Zukunftsassets und Jugend; **kein** Beweis, dass derselbe Trade bei B oder C legal beziehungsweise wirtschaftlich attraktiv wäre. Im datierten CP2a-Oktober-Vergleich betrug die isolierte marginale Top-20-Belastung von CMC bei Flo **+47,65 Mio. $** unter A/B und **+65,60 Mio. $** unter C/D; dies sind **nicht** tatsächliche im November gezahlte Vertrags- oder Dealpreise.

### 6.2 Systemische Unsicherheit und operative Durchsetzbarkeit

Weder die Zahl von 11 Trades im bisherigen 2026er Verlauf (2024 insgesamt 7, 2025 insgesamt 2), noch Flos wiederholter Erfolg, noch die Juni-/November-Snapshots beweisen, wie schnell andere Teams unter neuen Regeln aufholen würden. 2024 hatte die besondere Gründungsphase, 2025 einen anderen Markt und 2026 ist unvollständig. Der bewusst breite Playoff-Zugang (4/6), spätere Trades und der hohe Optionswert des Wartens bleiben relevant.

Die **14.11.2026 in Issue #1344 präzisierten sechs Ziele** sind deshalb explizit zu erhalten: langfristige Aufholbarkeit ohne Ergebnisgleichheit; verdiente mehrjährige Vorteile; keine kostenlos perpetuierten einmaligen Gewinne; wirtschaftlicher Preis von Elite-Kadern; Strategievielfalt; und **verlässliche einfache praktische Kontrolle**. Insbesondere darf die zusätzliche Wirkung eines permanenten Caps nicht gegen die Kosten eines dauernd synchronisierten Sleeper-/App-/Commissioner-Checks unsichtbar gestellt werden. Wenige klar definierte Prüftermine sind eine **offene** Vergleichsvariante, keine Entscheidung. Marcels Franchise-Claim-/Schutzrechtsidee bleibt ein **getrennter, nicht beschlossener** systemischer Vergleichspfad und wird hier weder mit Cap- noch Rookie-Kosten vermischt.

## 7. Hypothesen, Evidenzgrad und Entscheidungsgates

| ID | Präzise Hypothese | Jetzt verfügbarer Befund | Status für den nächsten Test |
|---|---|---|---|
| **H-CP3-01** | Ein Cap-Vollzug schafft finanzielle Verhandlungsknappheit, die bei acht simultanen Star-Angeboten mehr als einzelne Pair-Checks sichtbar macht | 29.06. gemeinsames Clearing 4/8 ohne Cuts; 7/8 bei bis 1 Nichtkern-Cut je Käufer | **supported als rein mechanische Existenz-/Knappheitsprobe; tatsächliche Tradequote inconclusive** |
| **H-CP3-02** | Permanentes Cap macht Trades gegenüber Cuts für Verkäufer und Käufer tatsächlich attraktiver | 7/8 spätere FA-Draft-Picks, aber keine gesicherten historischen Tradegebote; Käufer haben Cap-Offsets zu tragen | **inconclusive**; erst klare Transaktions- und Dead-Cap-Semantik + realistische Angebote / Verhalten |
| **H-CP3-03** | Langfristiges Rookie-Halten erzeugt belastbaren wirtschaftlichen Surplus und bessere Aufholbarkeit | 2025: 14/30 Originalowner nach ca. 1¼ Saisons; 2026: 23/30; Y1–3-Prozentsätze 60/60 rekonstruierbar | **partially_supported** für Retention als knappe Option; Dollar-Surplus / Y4 **inconclusive** |
| **H-CP3-04** | Criticality verbessert die Ligaökonomie *zusätzlich* zum Cap-Vollzug | CP2-Salary-Verteilung verschärft teils Kernkosten; CP3 findet schon im B-Markt knappe Käuferkapazitäten | **inconclusive**; keine Begründung für zusätzliche Aktivierung |
| **H-CP3-05** | Permanentes Cap ist gegenüber seltenen Stichtagsprüfungen netto überlegen | Kein gemessener Betreiber-/Integrationsaufwand, keine verhaltenskausalen Ergebnisse | **inconclusive**; CP5 muss Wirkung **und** Vollzugskosten vergleichen |

Bei H-CP3-01 bezeichnet `supported` **nur die deterministische Cap-Mechanik** des klar beschränkten Tests, keine kausale Wirkung auf reale Trades. Für H-CP3-03 ist nachzuprüfen, ob hypothetische Y1–Y3-Verträge unter tatsächlicher Top-20-Zählweise einen positiven *marginalen* Cap-Wert gegenüber Performance-Alternative und Draft-Pick-Opportunity-Cost erbringen.

## 8. Reproduktion und QA

1. Historische Juni-`League.json` für 07., 09. und 29.06. abrufen; vom 29.06. **beide** `League.json` und `Players.json` vom gleichen Git-Commit. Bestätigen: 8 Flo-Abgänge, 6/6 legale Juni-Kader, Cap = 434.255.984 $ und 0 fehlende Kader-IDs.
2. Pro Käufer 29.06. eine `usage(roster) = sum(top20(Salary[id] for id in unique(roster)))`-Funktion verwenden; nach Hinzufügen jeder Kandidaten-ID Top20 neu bestimmen. 8 × 5 = 40 Add-Checks. Separat alle einzelnen Cut-Kandidaten und dann alle Paare **außerhalb** der zehn teuersten Käufer-IDs prüfen. Assertions: `13+15+8+4=40`, Purdy 0 direkte Käufer.
3. Für simultanes Clearing pro Käufer alle 2⁸ = **256** Teilmengen prüfen. Je Regime (0, 1 Nichtkern-Cut, 2 Nichtkern-Cuts) eine zulässige Teilmengenliste erstellen; mit Masken-DP über fünf Käufer disjunkte Zuweisungen maximaler Spielerzahl finden. Assertions: **4**, **7**, **8**. Einmal genutzte Cap-Reserve nicht pro Kandidat erneut ausgeben.
4. 2024/25 historische und 2026 bis 05.11. eingefrorene `Transactions` nach `Status=complete`, `Type`, `Adds`, `Drops`, `EffectiveAt` trennen; reine Cut-Transaktionen, nicht-Trade-Drop-Ereignisse und **erste** spätere nicht-Trade-Add-Ereignisse je Saison zählen. Assertions: 2024 **132/7/7/118/19/27**, 2025 **127/2/21/104/9/23**, 2026 **121/11/66/91/4/17** (Spalten: complete / trades / pure cuts / drop events / same-team first add / other-team first add).
5. 2025 und 2026 Rookie-Fantasy-Draft-Picks 30/30 gegen den tatsächlichen Draft-Team-ID-Owner, 2025er Abschlussroster, 05.11.-League-Roster und historische erfolgreiche Adds/Drops/Trades joinen. Assertions: 2025 **20 ligaweit / 14 original**, 2026 **27 ligaweit / 23 original**; 2025 noch 23 beim Draft-Team im 2025er Abschlussroster; keine Spieler anhand des Nachnamens matchen.
6. Für die Salary-Prozente NFL- und Fantasy-Drafts per **canonical NFL-Player-ID** und Sleeper-ID verbinden; NFL-Pool nur QB/RB/WR/TE in `OverallPick`-Reihenfolge. Assertions: NFL-N 2025 **86**, 2026 **80**, **60/60** gematchte Spieler, ohne fehlenden Rang; Y2 = 1,25 × **festes** Y1, Y3 = 1,50 × Y1, **kein** additiver Minimum-Aufschlag während Y1–Y3.
7. Den 03.11.-CMC-Trade aus **einem** vollständigen Transaktions-Event mit sämtlichen PlayerIDs und **exakten PickKeys** lesen. Keine aus späteren Outcomes rekonstruierten Angebote.

**Präzisionsgrenze:** Das Report-Git-Ref vom 05.11. ist bei Players/League ein Week-8-Snapshot; andere spätere Readmodels oder 2026er Regular-Season-News dürfen die hier datierten Messwerte nicht ersetzen. `2024/25` sind im Archiv dokumentiert, aber mehrjährige historische Salary-Preis-Versionen und Titelwahrscheinlichkeiten wurden **nicht** in CP3 rekonstruiert. Das ist keine falsche Gleichsetzung von Marktmechanik und Managerverhalten.

## 9. CP3-Abschluss als begrenzter Forschungsschritt; Handoff an CP4/CP5

**CP3a–d als datierte historische Markt-/Retention-Bestandsaufnahme mit kontrollierten Käufer- und Rookie-Kontrafaktika abgeschlossen.** Anders als in einem vollständigen kausalen Verhaltenstest ist die Frage `Trades attraktiver als Cuts?` **methodisch offen** und ausdrücklich als solche dokumentiert; sie darf nicht durch freie Erfindung von Managerangeboten `gelöst` werden.

**Nächster Gate:** CP4 *nur, falls nötig*, die bereits bestätigten **nicht aktiven** Rookie-Contracts (Y1–3), gleitendes Minimum und Ein-Zyklus-Dead-Cap **einzeln** in gleiche Preis-/Cap- und Team-Snapshots einspielen, inklusive Draft-/Settle-, Floor-, Top-N- und Cut→Re-Add-Zeitachse. CP5 danach Systemwirkung, Aufholbarkeit, Marktliquidität, Strategievielfalt und operativen Aufwand gegen A/B/C und alternative wenige Check-Termine bewerten. **Keine** neue Salary-/Cap-Regel, kein Auto-Cut, kein neuer Franchise-Claim und kein Change an Draftorder oder bestehenden Konzeptentscheidungen aus diesem Bericht ableiten.