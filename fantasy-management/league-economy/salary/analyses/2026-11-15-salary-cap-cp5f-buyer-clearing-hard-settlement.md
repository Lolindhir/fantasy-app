# CP5f – Additiver Dead Cap: Käufer-Clearing, Roster-Kapazität und Hard-Deadline-Settlement

> **Forschungsstand:** 15.11.2026 · [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · **Status: kein Ligabeschluss, keine aktive Regel.** Auf Nutzerwunsch ist **C-add** die bevorzugte harte Forschungshypothese. C-virt bleibt Kontrollrechnung. Die [sechs geschützten Nordstern-Ziele](../../../league-context/league-philosophy.md) sind unverändert. Die Daten stammen aus [CP3](2026-11-14-salary-cap-cp3-market-retention.md), [CP5d](2026-11-15-salary-cap-cp5d-debt-backtest.md), [CP5e](2026-11-15-salary-cap-cp5e-additive-debt-amortization.md) und den [vollständigen CP5f-Metriken](2026-11-15-salary-cap-cp5f-buyer-clearing-hard-settlement-metrics.json).

## 1. Kurzbefund

**Echte Käuferfähigkeit ist enger als eine reine Salary-Paarliste suggeriert.** Die zusätzlichen Randbedingungen sind die additive Cut-Retention, die **29 regulären Rosterplätze**, bereits bestehende Schulden und die Belastungen mehrerer Spieler beim selben Käufer. Die historische Juni-Rekonstruktion reproduziert **15 vollständige Transaktionen** zwischen dem 07.06.2026 mittags und dem 30.06.2026, darunter **14 reine Cuts und ein Trade am 12.06.**, sowie alle **6/6 Endkader**.

Unter dem eingefrorenen damaligen Juni-Salary und Cap von **434.255.984 $** ergeben sich für 14 gecuttete Spieler jeweils fünf hypothetische Käufer:

| Prüfgrenze | Einzeln rechnerisch passende Cut-zu-Trade-Paare |
|---|---:|
| 70 Paare insgesamt | **70** |
| Kein zusätzlicher Schuldenanstieg beim Käufer, Rosterplätze zunächst ignoriert | **24** |
| Kein neuer Käufer-Schuldenanstieg **und** ein tatsächlich freier regulärer Rosterplatz | **15** |
| Käufer darf höchstens 5 % Cap-Schuld halten und hat einen freien regulären Platz | **30** |

Die Paarzahlen dürfen **nicht addiert** werden: Mehrere Transfers zu demselben Manager teilen sich den einen Cap-Puffer und seine wenigen offenen Plätze. Ebenso sind sie **keine akzeptierten Tradeangebote**, kein Beleg tatsächlicher Käuferbereitschaft und keine Aussagen über die Güte einer Gegenleistung.

Die separat zeitlich rekonstruierte Käuferprobe **unmittelbar vor den 14 Cut-Ereignissen** ergibt unter demselben, rückblickend eingefrorenen Juni-Salary **23 von 70 Paaren ohne zusätzlichen Käufer-Schuldenanstieg** (davon 21 mit vollständiger Schuld-Nullstellung). Es sind **keine echten tagesgenauen Preisversionen**: Erst der zeitlich korrekte Roster und die bisherige Retention ändern sich. Die 29.06.-Endlage ist ein **anderer** hypothetischer Markt, nicht rückwirkend der reale 09.06.-Käufermarkt.

## 2. Quellen, Replay und Modellgrenzen

- **Startroster 07.06.:** Git-Commit 5b4ed63172deae79759e7150f8511bd2ea3edb4e; bereits vor diesem Zustand vollzogener Cooper-Kupp-Cut wird nicht erneut simuliert.
- **29.06.-Endroster und Salary Cap:** Commit 85e22feb064fdaf2257d6c3149c8d1655ada0908; archiviertes Players-Blob 21001d6c0819dbbcb3deff084d63fe377714541c. Ein identischer Dollar-Salary-Vektor wird für alle historischen Ereignisse innerhalb dieses Replayfensters verwendet.
- **Transaktionen:** archiviertes Transactions-Blob 0aa85766a962a9d499fe5610a269771dd3b02ce1; nur vollständig abgeschlossene Events zwischen 07.06. 12:00 UTC und Deadline 30.06. 23:59:59 UTC. Alle 15 Events werden atomar nach Drop/Trade/Add verarbeitet. Kein Drop ohne tatsächlichen Vorbesitzer; 6/6 Endroster stimmen nach Replay exakt.
- **Cut-Retention:** dieselben 14 individuell historisch verifizierten Cut-Sätze 50/30/15/5 % wie CP5d/e. Beim *hypothetischen Trade statt Cut* spart der Verkäufer die individuelle Retention; der Käufer trägt das volle, ursprüngliche Spieler-Salary. Die übrigen historischen Cuts bleiben bis zur jährlichen Prüfung aktiv. Eine verhandelbare Salary-Retention in Trades wird **nicht** eingeführt.
- **Rosterplätze:** Die eingefrorene League hat 29 reguläre Plätze, dazu Taxi/Reserve-Slots mit eigenen Voraussetzungen. Die strenge Probe lässt **keine** zusätzliche Taxi-/IR-Verschiebung und **keinen** kompensierenden Cut zu. Das ist eine pessimistischere **No-Other-Move-Grenze** und kein Beweis, dass ein geeigneter Manager niemals einen weiteren Platz schaffen könnte.

Im 29.06.-Endkader stehen den Käufern ohne weitere Bewegungen folgende reguläre Plätze offen:

| Team | Freie reguläre Plätze | Ausgangs-C-add-Schuld |
|---|---:|---:|
| Mighty Giants | 0 | 0,00 Mio. $ |
| Ruhr Valley Packers | 4 | 4,07 Mio. $ |
| Just Bill | 8 | 31,03 Mio. $ |
| Mammoth Marauders | 0 | 0,00 Mio. $ |
| Team DennisLACards | 2 | 0,00 Mio. $ |
| Team TimpaBay | 3 | 0,00 Mio. $ |

**Wichtige Korrektur gegenüber reinen Salary-Proben:** Mighty Giants und Mammoth haben **null** freie reguläre Plätze. Der zuvor rechnerisch günstige zusätzliche Transfer **Romeo Doubs zu Mammoth** wäre ohne gleichzeitige andere rechtmäßige Bewegung nicht vollständig ausführbar. Ein Spieler unter die vorhandenen Top 20 zu rechnen genügt nicht, um seinen Rosterplatz nachzuweisen.

## 3. Flo: disjunkte gemeinsame Marktverteilung statt 40 Paarangebote

Die **acht tatsächlichen Cuts von Just Bill** werden als acht unterschiedliche Kandidaten in allen **256 möglichen Teilmengen** pro potenziellem Käufer durchgerechnet. Ein anschließender disjunkter Abgleich verteilt jeden Spieler auf **höchstens ein** Käuferteam; die Gesamtheit wird beim jeweiligen Käufer erneut als echte Top-20-Summe und mit offenen regulären Slots bewertet. Kreditlimit und Retained Salary werden pro Team geprüft.

Die Optimierung verändert nur diese *Cut-statt-Trade*-Entscheidungen; sie simuliert weder Draftpick-Gegenwerte noch Verhandlungsbereitschaft. Die Zahl der gegenfaktischen Lösungen beweist nicht, dass ein solcher Markt tatsächlich zustande gekommen wäre.

| Käufer-Schuldenregel | Geringste erreichbare Flo-Restschuld | Konsequenz |
|---|---:|---|
| **Keine neue Käufer-Schuld** | **20,93 Mio. $** | Höchstens zwei für Flo entlastende Transfers im bestmöglichen Pfad |
| Bis **5 %** des Caps als Käufer-Schuld | **3,10 Mio. $** | Weitere Entlastung nur durch erhebliche Neuverschuldung anderer Teams |
| Bis **10 %** Käufer-Schuld | **0 Mio. $** | Vollständige Flo-Entschuldung über sechs Transfers möglich, aber Verschuldung der Käufer steigt massiv |

**Die schärfste schuldenfreie Käufer-Kombination:** Sam Darnold und Terry McLaurin statt Cuts direkt zu Team DennisLACards. Beide zusammen vermeiden **10.092.720 $** Flo-Retention und drücken seine C-add-Schuld auf **20.932.808 $**. Dennis hätte anschließend **434.170.552 $** Top-20-Payroll und gerade einmal **85.432 $** Cap-Luft, bei ausgeschöpften zwei freien regulären Plätzen.

Unter einem 5-%-Schuldlimit von **21.712.799 $** wäre Flo damit zum Juni-Check *mechanisch* innerhalb des Limits. Es wäre aber eine Transaktion, der Dennis freiwillig zu angemessenen Bedingungen zustimmen müsste; die ausgewertete Historie belegt kein solches Angebot. Im identisch eingefrorenen 2027-Preisstand bleibt bei Flo sogar eine **H3-Mindestrate** von **6.977.603 $** knapp über seinem 6.526.405-$-Puffer: **451.198 $** müssten zusätzlich freigemacht werden. H2 ist noch deutlich strenger.

## 4. Wenn Käufer selbst Kredit aufnehmen: Verlagerung statt Auflösung

Die neuen Debt-Posten und die spätere Tilgung sind pro Seite zu zählen. Folgende drei vollständige Szenarien sind **ausschließlich mechanische Existenzbeispiele im 2026-Freeze**:

| Ziel beim Flo-Manager | Flo-Restschuld | Neue Käufer-Schulden | Gesamtverschuldung aller sechs Teams |
|---|---:|---:|---:|
| **5-%-Schuldlimit** ohne neue Käufer-Schuld: Darnold, McLaurin → Dennis | **20,93 Mio. $** | **0 Mio. $** | **25,00 Mio. $** |
| **H3-Erstrate** allein aus eingefrorenem Flo-Puffer: zusätzlich Doubs → TimpaBay | **19,00 Mio. $** | **3,73 Mio. $** | **26,80 Mio. $** |
| **H2-Erstrate** allein aus eingefrorenem Flo-Puffer: Purdy → Dennis, Darnold → TimpaBay | **11,33 Mio. $** | **23,33 Mio. $** | **38,73 Mio. $** |

Die tatsächliche hypothetische Ausgangslage aus den unveränderten 14 Juni-Cuts ist **35.094.437 $ Gesamtschuld**, davon Flo **31.025.528 $** und Packers **4.068.909 $**.

Im **H2-Fall** bringt der Flo-Schuldabbau nicht etwa die Käufer automatisch auf einen zulässigen Langfristpfad: Dennis übernähme **8.328.471 $**, TimpaBay **15.003.708 $** Kredit. Bei denselben künstlich konstant gehaltenen 2026er Salaries müssten die Käufer zusätzlich zu ihren erforderlichen Zweijahresraten bei der ersten Folgeprüfung Cap-Raum freimachen: Dennis **12.492.707 $**, TimpaBay **22.505.562 $**. Das ist ein sehr hoher wirtschaftlicher Preis dafür, dass Flo seine eigene 2027er Mindestrate erfüllen könnte.

Im **H3-Fall** bleibt nach den zwei Dennis-Transfers ein dritter hypothetischer Käufer **TimpaBay** für Doubs. TimpaBay erhält dadurch **3.725.522 $** eigene Debt und müsste bei den konstanten Gehältern für seine H3-Erstrate **4.967.363 $** zusätzlich entlasten. Die Gesamtschuld sinkt, aber der Mechanismus ist damit noch kein belegter gesellschaftlich akzeptierter Trade.

**Extremfall bei 10-%-Käuferlimit:** Zur vollständigen Flo-Entschuldung werden im besten disjunkten Beispiel sechs seiner acht Cut-Spieler zu anderen Teams transferiert. Die mindestens nötige **neue Käufer-Schuld** beträgt **70.676.173 $**. Zusammen mit der unveränderten Packers-Schuld stünden ligaweit dann **74.745.082 $** aus – mehr als das Doppelte des ursprünglichen C-add-Gesamtüberhangs. Das ist der zentrale neue Gegenbeleg gegen eine zu eng am Verkäufer optimierte Settlement-Logik: **Eine verschwundene Verkäuferschuld kann andere Teams erheblich belasten.**

## 5. Harte Deadline: welche Situationen wären tatsächlich zu entscheiden?

Die 2026er Bestandsaufnahme enthält bei **Null-Altschuld** am Juni-Endstichtag zwei Teams mit neuer positiver C-add-Debt. Bei **10 %** Gesamtlimit wären nach dem historischen Cut-Pfad **alle sechs Teams innerhalb des Limits**, bei **5 %** würde **Just Bill um 9.312.729 $** das Limit überschreiten. Eine fällige H2/H3-Altjahrgangsrate bestand 2026 noch **nicht**. Das ist ein Forschungstest, kein rückwirkender Regelverstoß.

**Vollzugsprotokoll – Vorschlag für späteren Offseason-Pilot, derzeit keine neue Regel:**

1. **Normativen Freeze sichern:** Kader/Taxi/Reserve-Zuordnung, vollständige Cut-Events und deren Ownership/Tenure, Spieler-Salary-Vektor, Cap samt Modellversion, bestehende Jahrgänge, Deadline-Zeit, Datenhash und Zeitstand für alle sechs Teams identisch protokollieren.
2. **Vier Größen getrennt ausweisen:** gehaltene Top-20-Usage, additive noch gültige Cut-Retention, vorhandene Team-Schuld *pro Jahrgang* und **dieses Jahr zwingend fällige Mindesttilgung**. Den zulässigen Gesamtschuldrahmen **nicht** als Ersatz für diese Fälligkeit behandeln.
3. **Rechnerisches Pass/Fail:** Fällige Rate muss aus tatsächlicher Budgetluft gedeckt werden, nicht aus frischer Refinanzierung; ein Überschuss über den Kreditdeckel verlangt eine echte, vom Manager freiwillig entschiedene Ausgleichsmaßnahme. Alternative Trades immer beim Verkäufer **und allen Käufern zugleich** mit Cap- und regulärer Rosterbelegung bewerten.
4. **Frist/Abnahme:** Nach vorab geregelter freiwilliger Korrekturphase wäre ein vollständig abgesicherter Status **pass** möglich. Solange Daten oder Transaktionsfinalität unklar sind, **pending_correction**. Ohne realisierten legalen Ausgleich: **failed_unresolved** – nicht automatisch ein erlassener Betrag, nicht „passt schon“, aber auch **kein** Forschungsmandat für Auto-Cut, Pick-Sperre, Ergebnisstrafe oder manuelles eigenmächtiges Blockieren von Trades.
5. **Jahres-Reset getrennt halten:** Erst nach der final definierten Jahresbilanz Cut-Retention des alten Salary-Zyklus löschen und den neuen Salary-Zyklus neu bewerten. Ein F2/Post-FA-Draft-Check darf **keinen** zweiten Salary-Reset einschmuggeln.

**Der eigentliche Konflikt ist noch offen:** Was geschieht, wenn ein Manager an der Hard Deadline trotz rechtzeitigem Handeln keine finanzierbare freiwillige Lösung findet oder mit dem Ergebnis nicht einverstanden ist? Die Historie belegt mathematische Möglichkeiten, keine durchsetzbaren Marktabschlüsse. **Sanktion, Grace-Dauer, Appeals, abschließende Commissioner-Zuständigkeit sowie zuverlässige Sleeper-Abwicklung müssen die Liga später ausdrücklich festlegen.** Ein „failed_unresolved“-Status ist kein bereits gültiges Ligarecht.

**Operative Evidenz:** Die historische Juni-Prüfung umfasst 6 Teams, 15 abgeschlossene Events, 14 Cut-Ledger-Posten, 70 einzelne Käufer-Kombinationen und eine disjunkte Acht-Spieler-Simulation. Die bisherige Sleeper-Public-API-Recherche in CP5b bestätigt keine automatische sichere transaktionale Cap-Sperre. **Es wurden keine echten Commissioner-Minuten, Käuferzustimmungen, Einspruchsquoten oder operative Ausnahmefälle gemessen.**

## 6. Bewertung entlang der sechs geschützten Nordstern-Ziele

| Ziel | Was CP5f zeigt | Noch nicht bewiesen |
|---|---|---|
| **1 Langfristige Aufholbarkeit** | Die additive Verkäuferhaftung schafft späteren Budgetdruck. | Ob schuldenbelastete Käufer dadurch länger vom Titel ausgeschlossen bleiben. |
| **2 Management belohnen** | Frühe Tradeplanung, Liquidität und Rosterplätze haben erkennbaren Optionswert. | Ob ein Manager die synthetischen Trades zu sinnvoller Gegenleistung tatsächlich anbieten/akzeptieren würde. |
| **3 Kein unbegrenzt kostenloser Vorteil** | Nicht sämtliche Kaderkosten lassen sich einfach per Cut und Schuldverschiebung neutralisieren. | Ob das System dominierende Assets über mehrere echte Saisons angreifbar macht. |
| **4 Wirtschaftliche Folgen sportlicher Stärke** | 5 % und H2/H3 können spürbare Entscheidungen verlangen. | Ob die Folgepflicht bei Käufern insgesamt ineffizient höhere Liga-Schulden erzeugt. |
| **5 Strategische Freiheit** | H3 mit begrenzter Käuferbelastung bleibt rechnerisch denkbar; H2 ist wesentlich härter. | Ob Käufer-/Verkäufermärkte in der kleinen Liga liquide genug dafür sind. |
| **6 Verlässliche Umsetzbarkeit** | Ein Jahresledger und Stichtagschecks sind mit archivierten Daten überprüfbar. | Wie ohne eindeutige Hard-Failure-Regel, Sleeper-Cap-Gate und echte Zeitmessung ein Streit abschließend entschieden würde. |

## 7. Bedeutung für F2/F3/B und nächste CP6-Entscheidung

**C-add plus jährlicher Schuldvortrag und F2 sind keine funktional identischen Regeln.** CP5b fand nach dem 2026er Free-Agent-Draft unter einem eingefrorenen September-Preisstand **vier Teams mit insgesamt 122.567.015 $ positivem Überhang**. Der jährliche Debt-Vortrag bepreist Überschreitungen erst beim nächsten regulären Jahresabschluss; F2 würde zusätzlich schon nach dem FA-Draft einen verbindlichen Check verlangen. F3 und permanente Event-Gates unterscheiden sich wiederum im Zeitpunkt und operativen Aufwand. Die neue C-add-Schuld-/Roster-Kapazitätsprobe lässt sich nicht ungeprüft auf den September-F2-Pfad übertragen.

**Nächster abgrenzbarer Forschungsschritt:** (a) für beide Varianten einen realen Offseason-Settlement-Papierpilot mit gemessenen Commissioner-Schritten/Minuten und offenem Failure-Fall durchführen, (b) C-add im selben sauberen Post-FA-Draft-Zustand gegen F2 vergleichen, (c) Käuferseitige Schuldendienstkosten und ob reale künftige Spielergehälter überhaupt genug Headroom bieten testen. H2/H3 und 5/10-%-Kreditlimit sind weiter **unbeschlossene separate Parameter**. Ein vollständiger Mehrjahres-Titelchancen- oder Managerverhaltens-Backtest liegt weiterhin **nicht** vor.

## 8. Reproduzierbarkeit und Status

Die [JSON-Metriken](2026-11-15-salary-cap-cp5f-buyer-clearing-hard-settlement-metrics.json) speichern alle 70 Endkader-Paare sowie 70 zeitlokale Event-Paare, reguläre Slots, die disjunkte Optimierung aus acht Cut-IDs und 0/5/10-%-Käufergrenzen, offene H2/H3-Tilgungsfälle und **42 erfolgreich geprüfte Source-/Rechen-/Replay-Invarianten**. Sie sind eine archivierte Rechnung, nicht ein Programmlauf für echte Trades. Keine individuellen Veteranenverträge, kein neuer Salary-Check, keine echte Ligaregel, keine technische Implementierung und keine realen Managerentscheidungen geändert. **CP5-Mehrjahreswirkung und CP6-Ligaentscheidung bleiben offen.**
