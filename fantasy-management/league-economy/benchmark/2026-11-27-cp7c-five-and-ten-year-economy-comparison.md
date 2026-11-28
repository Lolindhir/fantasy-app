# CP7c – Fünf- und Zehnjahresvergleich der Dead-Cap-Mechaniken

> **Forschungsstand 27. November 2026 · Issue #1344 · Draft PR #1576.**
> Es sind synthetische, gepaarte ökonomische Gegenwelten. **Keine aktiven Ligaregeln, keine tatsächlich angenommenen Trades und keine NFL-Ergebnisprognose.** [Originalbenchmark CP7a](2026-11-26-benchmark-v1.md) · [CP7b Einjahrestest](2026-11-26-cp7b-market-comparison.md) · [CP7c-Ereignis-Simulator](cp7c_multiyear_economy.mjs) · [maschinelles Aggregat](2026-11-27-cp7c-aggregate.json).

## Executive Summary

**(1) Dead Cap führt in unseren 2027–2031-Manager-Proxywelten tatsächlich zu mehr 1:1-Trades, aber nicht verlässlich zu weniger Cuts.** Bei 10 % Cap-Druck und drei identischen Seeds: P0 **5 Trades / 338 Cuts**, P1 **13 / 340**, P2 **17 / 347**. Die zusätzlichen Trades lösen deshalb den wirtschaftlichen Bereinigungsdruck nicht automatisch.

**(2) Die Reihenfolge am Salary Check ist ein hartes politisches und operatives Gate.** Vier kontrollierte P1-`reset_before_enforce`-Gegenwelten ergeben über alle simulierten Jahresereignisse exakt dieselben Dollar-, Trade-, Cut- und Starterindex-Resultate wie P0 ohne Dead Cap. Darunter sind alle drei Seeds bei −10 % und Seed 11 bei −20 %. Damit würde die ursprünglich beabsichtigte Offseason-Cut-Friktion unter dieser konkreten Reset-Zeitachse komplett verschwinden. Ein verpflichtender Check **vor** dem Reset ist eine neue operativ zu spezifizierende Anforderung, nicht automatisch aktives Ligarecht.

**(3) Mehrjährige Garantien bringen höhere Last und ein härteres Compliance-Risiko.** Bei −20 % Cap-Druck war der P2-Pfad in Seed29 bereits **2027** nach dem Greedy-Settlement noch **327.950 $ über Cap**. Der Simulator stoppt den Pfad: keine erfundenen Folgejahre, keine kostenlose Stundung. Das ist eine **Nichtheilbarkeit im gewählten Suchalgorithmus, kein mathematischer Insolvenzbeweis**. Die anderen beiden Seeds erreichten alle fünf Jahre.

**(4) Das 45er-Kaderlimit wird im 10-Jahres-Stress erstmals sichtbar wirksam:** Seed11, −10 %, im erweiterten Lauf 2027–2036 entstehen **88** draftbedingte Kapazitätscuts P0, **71** P1, **58** P2. Achtung: Dies ist ein **vergleichbarer 45-Slot-Test innerhalb eines Systems**, nicht der bislang fehlende direkte 40/45/50-Paartest. Die sechs Starts hatten je 20 Plätze, und ab 2032 stoßen mehr Kader an das 45er-Limit.

**Vorläufige Schlussfolgerung:** P1 ist weiterhin die sparsamere Dead-Cap-Arbeitshypothese **falls** eine tatsächliche bindende Prüfung vor dem Reset möglich ist. P2 erhält mehr Proxy-Trades, aber keinen überlegenen Ligabefund und bringt zusätzliche Vertragsschulden und Regelaufwand. **Kein finaler Gesamtsieger der Ligaökonomie.**

## 1. Prüfaufbau

- Historisch rekonstruierter Oktober-2026-Spielermarkt mit **1.268 eingefrorenen Preis-/Performance-Einträgen** und gemeinsamer, jährlich fortgeschriebener CP6r-Criticality-/Salary-Mechanik; **keine 2027+ tatsächlichen NFL-Daten**.
- Drei bewusst unterschiedliche **synthetische** Sechs-Team-Startwelten (Seeds **11, 29, 47**) mit rotierten All-in/Reload/Rebuild/Flex-Agenten. Jeweils maximale **45 reguläre Plätze**, keine Taxi-/IR-Kontingente, **alle aktiven Salaries zählen voll**, 13 Starter, je fünf Rookie-Draft-Picks pro Team und Jahr.
- Gemeinsame exogene Spieler-Performance-/Aging-/NFL-Exit-Pfade und Rookie-Angebote je Seed; endogene Ownership, Trades, freiwillige/erzwungene Cuts und neue Verpflichtungen differieren nach Regime. Vertrags-Startvintages 2025/26 wurden **synthetisch** angelegt, nicht historisch als echte Managererwerbe rekonstruiert.
- Je drei P-Dead-Cap-Policen: **P0** ohne Cut-Dead-Cap; **P1** 50/30/15/5 % abhängig von Fantasy-Team-Tenure, ein Salary-Zyklus, voller aktiver Salary-Abschlag bis zum folgenden echten jährlichen Reprice; **P2** 100/50/25 %-Veteranengarantie und nach tatsächlich ausgeübter Fantasydraftrunde gestaffelte Rookie-Garantie, mehrjährige Zahlungsfälligkeiten. In P2 ist die erneute FA-Salary eines gecutteten Vertragsspielers nach wie vor nicht festgelegt; solche Cut-Wiederaufnahmen sind deshalb in derselben Phase blockiert.
- Trades finden **vor** Cuts statt. Die einzige Tradeform ist **ein legaler 1:1-Spieler-/Restvertragsswap** zwischen einem unter Cap stehenden Käufer und einem Verkäufer mit aktuellem Cap-Druck. Positive synthetische Buyer-/Seller-Utility erforderlich. Keine Pick-Preise, echten Besitzerangebote oder Claim-Auktion. Der Käufer trägt die laufende und künftige Salary; die getradete Verpflichtung löst keine neue Dead Cap aus.
- **Entscheidende Isolationsgrenze:** P0/P1/P2 tragen im CP7c-Lauf dieselbe **synthetische dreijährige Grundvertragspreisfolge** (Veteranenslope 25 %, Rookies 100/125/150); ausschließlich die Cut-Verpflichtung unterscheidet sich zunächst. Neue Verträge und der Cap-Markt verwenden jährlich aktualisierte Criticality-Preise, aber **bestehende Veteranengehälter werden nicht ausnahmslos jedes Jahr neu auf Criticality-Marktpreis gesetzt**. Bei P1 wird allein der zuvor vergünstigte Retained-Salary-FA-Preis beim nächsten jährlichen Reprice ausdrücklich auf den neuen vollen Marktwert zurückgesetzt. Daher ist das P1-Ergebnis **ein kontrollierter Dead-Cap-Faktortest**, noch **keine vollständig regelgetreue Simulation des ursprünglichen jährlich neu bepreisten P1-Salary-Systems**. Das muss im abschließenden Vier-Modell-Vergleich als getrennte Salary-Faktorachse getestet werden.
- Cap aus CP6r Top120/6 nach jährlicher Rookie-Aufnahme und dynamischen Preisen, jährlich wiederholte −10 % oder −20 % Cap-only-Stressannahme. **Kein echter historischer 2027+ Cap**. Realer Timestamp des Juni-Salary-Checks wird nicht als Event abgespielt; die Reihenfolge ist stattdessen eine dokumentierte P1-Politik-Gegenwelt.
- Retirements/NFL-Exit werden im **Forschungsmodell** als Vertragsfreigabe mit regimeabhängiger verbleibender Cut-Verpflichtung behandelt. Diese zusätzliche Annahme ist **nicht** ratifiziert und könnte P2 verändern. Verletzungen, echte Playoff-Chancen, Managerpräferenzen und tatsächliche 2025/26 Vertragsentscheidungen sind **nicht** in den Szenarien enthalten.

## 2. Gepaartes Fünfjahres-Experiment 2027–2031

Primärer Vergleich: sechs Teams × fünf Jahre × drei Seeds × drei Dead-Cap-Policen bei gleicher verbindlicher Cap-Prüfung **vor** Salary-Reset. Die zwei Cap-Schocks wurden jeweils getrennt durchgerechnet. Das sind **18 Primärpfade**, davon **17/18** bis 2031 mit vollständiger Cap-/Roster-Legalität in den Modellregeln. Zusätzlich wurden vier Null-/P1-Reset-Reihenfolge-Kontrollpfade gerechnet.

### Bei −10 % Cap-Stress

*Summen über drei alternative sechs-Team-Welten und fünf Jahre; kein tatsächlicher Liga-Jahresdurchschnitt.*

| Modell | 5 Jahre legal | Proxy-Trades | Cuts | Dead Cap 2031, Summe über 3 alternative Welten | Median Abstand stärkstes/schwächstes Team 2031 (Starterindex) |
|---|---:|---:|---:|---:|---:|
| P0 – Keine Dead Cap | 3/3 | 5 | 338 | 0,00 Mio. $ | 20.46 |
| P1 – Ein-Zyklus-Retained Salary | 3/3 | 13 | 340 | 158,00 Mio. $ | 11.46 |
| P2 – Mehrjährige Garantien | 3/3 | 17 | 347 | 452,68 Mio. $ | 12.22 |

**Handelsanreiz:** P1 erhöht die Tradezahl **5 → 13**, P2 **5 → 17**. Die Cut-Zahl verändert sich **338 → 340 → 347**, also keineswegs automatisch nach unten. **Ein Trade zählt nur, wenn beide simulierten Manager-Utilityfunktionen positiv sind**; echte Zustimmung ist nicht erhoben.

**Dead-Cap-Preis:** Am Ende 2031 bestehen bei P1 über die drei alternativen Testwelten zusammen 158,00 Mio. $ für den **aktuellen** Zyklus und keine P1-Schuld für das nächste Jahr. P2 hat 452,68 Mio. $ aktuelle und 96,60 Mio. $ **zukünftige** Cut-Garantien. Diese Summen sind keine Belastung einer einzigen echten sechs-Team-Liga.

**Sportlicher Proxy:** Der Median des 2031er Starterindex-Abstands sinkt von ca. **20.46** unter P0 auf **11.46** unter P1 und **12.22** unter P2. Das ist ein beobachteter Agenten-/Kader-Effekt in drei kleinen synthetischen Welten, **keine Championship-Wahrscheinlichkeit**, kein Beweis von Managementqualität und keine Forderung nach Gleichverteilung.

### Bei −20 % Cap-Stress

*Unterschiedliche Pfadlänge: Der P2-Seed29-Pfad stoppt schon nach 2027. Sein Cut-Zähler darf **nicht** unkommentiert mit fünf vollständigen Jahren der anderen Modelle verglichen werden.*

| Modell | 5 Jahre legal | Proxy-Trades in allen beobachteten Jahren | Cuts in allen beobachteten Jahren | Dead Cap 2031 in vollständigen Pfaden |
|---|---:|---:|---:|---:|
| P0 – Keine Dead Cap | 3/3 | 4 | 380 | 0,00 Mio. $ |
| P1 – Ein-Zyklus-Retained Salary | 3/3 | 7 | 380 | 191,64 Mio. $ |
| P2 – Mehrjährige Garantien | 2/3 | 8 | 293 (nur bis 2027 in einem Pfad) | 331,94 Mio. $ (nur 2 vollständige Pfade) |

Für einen **direkten, gleich langen** Vergleich der beiden vollständigen gemeinsamen Seeds 11+47:

| Modell | Trades (2 Seeds × 5 Jahre) | Cuts (2 Seeds × 5 Jahre) | Legal |
|---|---:|---:|---:|
| P0 – Keine Dead Cap | 4 | 248 | 2/2 |
| P1 – Ein-Zyklus-Retained Salary | 5 | 246 | 2/2 |
| P2 – Mehrjährige Garantien | 6 | 272 | 2/2 |

Der stärkere Cut-Anreiz von P1 bleibt sichtbar, aber der Rückgang der Cuts ist unter starkem Stress in dieser engen Paarbasis marginal. **P2 hat den größten Schuldendruck und einen nicht ausgeheilten Greedy-Fall**. Besonders schwache Käuferliquidität und Ersatzspielerpreise können die zusätzliche Vertragslast in echte operative Schwierigkeiten übersetzen.

## 3. Salary-Reset – die wichtigste Gegenprobe

Die drei 2027–2031-Seedwelten bei −10 % und der zusätzliche Seed11-−20-%-Pfad wurden mit **P1 „Reset vor bindender Compliance“** erneut bewertet. Alle **vier** Vergleiche sind **vollständig event-, cap- und rosteridentisch** zur jeweiligen P0-Gegenwelt: jeder Trade, jeder Cut, jedes Jahres-Salary und jeder Starterindex. Nicht nur das Endergebnis, der gesamte Verlauf ist identisch.

Dieser Befund hängt an der Testsemantik: P1-Cuts haben keinen bindenden Retained-Cap-Betrag, wenn die nächste kontrollwirksame Deadline erst nach dem obligatorischen Salary-Reset eintritt und keine weitere Sanktion existiert. Eine echte vorverlegte Cap-Kontrolle oder eine Reihenfolge **Prüfen, dann Reset** würde P1 wieder aktivieren, benötigt aber eine klare neue Regel und ggf. Commissioner-Arbeit.

**Historischer Check aus CP4c/CP5c:** 2026 war die wirkliche Cap Deadline **30.06.2026 23:59:59 UTC**, nach Flos acht Cuts vom 09.06. Für diese Cuts ergäben sich unter dem ursprünglichen P1-Konzept 37,55 Mio. $ hypothetische Dead Cap im alten Zyklus. Die historische Käuferkapazitätsprobe hat **13/40** Full-Trade-Salary-Paarungen gegenüber **16/40** nach günstigeren Cut-Salaries gefunden; für Brock Purdy 0/5 Käufer im Full-Preisfall gegenüber 1/5 nach hypothetischem Cut. Das sind **keine** echten Tradeangebote, aber ein ernstes Käuferwarte-Argument. Historisches S0 mit Top20-Recht darf nicht als 45er-Research-Welt umgedeutet werden.

## 4. Zehnjahres-Extremprobe bis 2036

Um dauerhafte Starterqualität und den 45er-Roster-Saturation-Effekt sichtbar zu machen, wurden **alle drei P-Modelle** mit Seed11, −10 %, 2027–2036 zusätzlich zehn Jahre durchgerechnet. Wieder: genau eine synthetische Ausgangswelt, keine belastbare Liga-Prognose.

| Modell | 10 Jahre legal | Proxy-Trades | Cuts/FA-Replacements | **Draft-Kapazitätscuts zusätzlich** | Current Dead Cap 2036 |
|---|---:|---:|---:|---:|---:|
| P0 – Keine Dead Cap | 1/1 | 4 | 215 | 88 | 0,00 Mio. $ |
| P1 – Ein-Zyklus-Retained Salary | 1/1 | 7 | 274 | 71 | 62,98 Mio. $ |
| P2 – Mehrjährige Garantien | 1/1 | 8 | 271 | 58 | 130,05 Mio. $ |

Bei allen drei Modellen bleibt der rechnerische Cap-/Roster-Status im Greedy-10-Jahreslauf legal, was das Modell *unter diesen Annahmen* nicht grundsätzlich unlösbar macht. P1 und P2 erfordern jedoch viel mehr Cut-Aktionen und halten deutlich mehr Schuld als P0. **Die Kapazitätscuts ab 2032 dokumentieren, dass die 45 erlaubten Plätze langfristig überhaupt binden**; diese sind **zusätzliche Draft-Slot-Vorgänge** und dürfen nicht als normaler `cuts`-Zähler doppelt gezählt werden.

Gegen 2036 beträgt der Leader-minus-Laggard-Starterindex-Abstand in diesem einen Seed **14.55 P0**, **11.33 P1**, **12.95 P2**. Daraus kann kein globales dauerhaft finanzierbares Startermaximum oder ein automatisches Titelrotationsversprechen abgeleitet werden. CP6i fragt nach dem dauerhaft maximalen Einzelteamindex; CP7c beobachtet nur mögliche Heuristikpfade, nicht das mathematische Maximum.

## 5. Abnahme entlang unserer sechs geschützten Nordstern-Ziele

| Ziel | CP7c-Evidenz | Ergebnisstatus |
|---|---|---|
| 1. Chancengleichheit/Aufholbarkeit | Starterindex-Spreads über fünf und zehn Jahre; keine Titelquoten, keine exakten Rebuild-Counterfactuals | **Teilweise, nicht ausreichend** |
| 2. Gutes Management belohnen | Rollen All-in/Reload/Rebuild/Flex, gegenseitig positive Agenten-Trades, keine identische-Future-Skill-Regression | **Noch nicht quantifiziert** |
| 3. Keine automatische Ewigkeitsdominanz | Leader-Index und 2031/2036-Verteilung beobachtbar; keine global optimierte dauerhafte Top-Starterdecke | **Offen** |
| 4. Ökonomische Konsequenzen | Transfer-Geldkonservierung, aktuelle und spätere Dead-Cap-Last, Cap/Slot-Hard-Fail, Cut-vs-Trade-Anreiz | **Im Modell belastbar** |
| 5. Strategische Freiheit | Drei Preis-/Schuldregime, Rookie-Draft und freie Veteranen; keine Pick-/Bundle-Trades, kein aktiv verhandelbarer Rebuild-Markt | **Eingeschränkt** |
| 6. Operative Umsetzbarkeit | Alle vollständigen Pfade samt Geld-/Owner-/Rostertests; 1 Greedy-Failure; hohe Proxy-Transaktionslast; tatsächliche Sleeper/Commissioner-Umsetzung fehlt | **Hard-Gates offen** |

Es wäre methodisch falsch, jetzt anhand der geringeren Starterindex-Spreads einen Gewinner auszurufen. Die sechs Ziele wurden noch **nicht** abschließend nach den vorgängig festzulegenden Gewichten eingestuft, und die sechs Ligamanager haben den Nordstern noch nicht vollständig ratifiziert.

## 6. Fünf-Achsen-Audit & Grenzen

1. **Seller Relief:** Trade-vs-Cut-Quote je Deal, tatsächlicher Ersatzspielercash und aktuelle Dead Cap in den Event-Ledgers; Cut wird unter Garantie nicht gratis angenommen.
2. **Buyer Burden:** alle 1:1-Trades konservieren aktuelle gemeinsame Salary, beide vollständigen beobachtbaren Folgejahres-Salary-Transfers und Ownerrechte. **Reale zukünftige Käufer-Caps sind nicht bekannt** – die Folgejahres-Legalität wird endogen neu im nächsten Jahr hergestellt, ggf. durch Cuts.
3. **Roster/IR/Taxi:** 13 Starter und Positionsdeckung, 20–45 reguläre Plätze, eindeutige Spielerownership. Keine tatsächliche IR/Taxi-Verfügbarkeit oder Sleeper-Limit-Automation.
4. **Debt/Vintages:** P1-Dead-Cap wird nur im tatsächlich angenommenen Salary-Zyklus gezählt, danach zurückgesetzt; der Retained-Salary-Rabatt für einen Cut-/FA-Zugang wird beim **nächsten jährlichen Salary-Repricing** wieder auf Vollmarktpreis gestellt. P2-Schulden werden im Old-Owner-Ledger bis zur vertraglich fälligen Saison getragen; kein stillschweigender Schuldenerlass.
5. **Mehrjährige Rückzahlbarkeit:** hartes Cap-Gate jedes Jahres, Abbruch beim nicht gecureten Greedy-Fall statt fingierter Kreditaufnahme. Fehlende echte Angebote, Commissioner-Minuten, echte 2027+ Cap-Werte und exakte historische 2025/26 Vertrags-/Acquisition-Tenures ausdrücklich unbekannt.

**Technik:** Die `cp7c_multiyear_economy.mjs`-Quelle lief im gleichen V8-Syntax-/Source-Kontext mit Dateien aus GitHub, jeweils mit Check von Seller-/Buyer-Salary-Identität, bilateraler Future-Salary-Konservierung, Cut-Nettoentlastung und Null-Debt-Kontrolle. Alle 25 gespeicherten Paare stammen vom gleichen Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`. **Unabhängiger Node-CLI-/GitHub-CI-Lauf nicht verifiziert.** Greedy-Handels- und Cut-Agenten sind keine ILP-/Optimalmarkt- oder echten Menschen-Abbildungen. Verletzungsdaten werden noch nicht in jährliche availability-relevante Kaderentscheidungen eingespielt.

## 7. Entscheidung und konkreter nächster Forschungs-Gate

**Für den Teilmechanismus „Dead Cap soll Trades gegenüber Cuts fördern“ bleibt P1 ein plausibler Kosten-/Komplexitätskompromiss, aber kein bestätigter Gesamtsieger.** Ohne verpflichtende Kontrolle vor dem Reset ist P1 im Test exakt P0; mit Kontrolle nimmt die Zahl von Agenten-Trades zu, ohne dass über fünf oder zehn Jahre automatisch weniger Cuts auftreten. P2 treibt Handel stärker, bindet mehr Ressourcen und hat in einer Cap-Stresswelt einen nicht gecureten Pfad.

Der nächste Forschungsschritt ist **nicht** eine vierte Fantasieregel, sondern das Schließen von vier verbliebenen gemeinsamen Benchmark-Gates:
- **Echte historische Daten/Kalender:** tatsächlich beobachtete Team-Tenure und Draft-Contract-Historie, Cap-Deadline- und Salary-Reset-Ereignisse als getrennte, datierte Events, S0-Top20 sauber im eigenen Lane.
- **Trade-/FA-Liquidität:** Käuferwarten, echte Pick- und mehrteilige Pakete, Käufer-Cap und Zukunftsverpflichtung, explizite Verweigerung, P2-FA-Neuvertrag nach Cut; keine fiktiven Erlöse.
- **Long-run Robustheit:** mehr Seeds sowie 0/-10/-20-%-Shock, 40/45/50-Kader und 20/30/45-Startbelegung, reale Verletzungs-/Bye-/Availability-Sensitivität und zukünftige Cap-Stress-Varianz; globaler Starterindex als separater Optimierungstest.
- **Faire Endentscheidung:** S0/Ist-Liga plus vollständige einheitliche Reformpakete, vorher registrierte sechs-Nordstern-Schwellen und Gewichtungs-Sensitivität; unabhängige Node-/CI-Ausführung, tatsächlicher Commissioner-Prozess ohne automatische Credit-/Autocut-Abkürzungen und spätere ligaweite Abstimmung.

**Keine Live-Salary-/Sleeper-/Owner-/Frontend-Regel geändert.** Alles bleibt auf dem Forschungszweig zu Issue #1344 und im offenen Draft PR #1576.

### Rohdaten und Reproduktion

- [seed11-shock10-fiveyear](./2026-11-27-cp7c-seed11-shock10-fiveyear.json)
- [seed29-shock10-fiveyear-v2](./2026-11-27-cp7c-seed29-shock10-fiveyear-v2.json)
- [seed47-shock10-fiveyear](./2026-11-27-cp7c-seed47-shock10-fiveyear.json)
- [seed11-shock20-fiveyear](./2026-11-27-cp7c-seed11-shock20-fiveyear.json)
- [seed29-shock20-fiveyear](./2026-11-27-cp7c-seed29-shock20-fiveyear.json)
- [seed47-shock20-fiveyear](./2026-11-27-cp7c-seed47-shock20-fiveyear.json)
- [seed11-shock10-tenyear-p0p1](./2026-11-27-cp7c-seed11-shock10-tenyear-p0p1.json)
- [seed11-shock10-tenyear-p2](./2026-11-27-cp7c-seed11-shock10-tenyear-p2.json)

**Begründete Modellgrenze:** Aus acht gespeicherten Forschungs-Pfad-Dateien und einem Benchmark und einer engen Kundenanreizhypothese folgt kein mathematischer universeller Champion. CP7c beantwortet den ersten *gemeinsamen Mehrjahresvergleich* der Dead-Cap-Regime, nicht die endgültige Regelwahl.
