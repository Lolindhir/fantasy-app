# CP7c – Fünf- und Zehnjahresvergleich der Dead-Cap-Ökonomie

> Stand 27.11.2026 · Issue #1344 · Draft PR #1576 · **Forschung, keine Regeländerung und keine ligaweite Ratifizierung.** Grundlage: [Benchmark CP7a](2026-11-26-benchmark-v1.md), [CP7b](2026-11-26-cp7b-market-comparison.md), [Nordstern](../../league-context/league-philosophy.md). Vollständiger maschinenlesbarer [Auswertungsstand](2026-11-27-cp7c-synthesis.json).

## Ergebnis und Entscheidung

Im gemeinsamen festen Vertragsmarkt spricht der Fünfjahresvergleich **vorläufig für P1 als pragmatischen Dead-Cap-Kandidaten**: gegenüber P0 13 statt 5 simulierte 1:1-Trades, 11 statt 7 Top-4-Starterindex-Teamjahre der anfangs zwei schwächsten Teams pro Seed, 3 statt 1 nachhaltige Aufholfälle (mindestens zwei Jahre hintereinander Top 4), bei annähernd gleicher Cut-Zahl (340 vs 338). P2 generiert 17 Trades, aber deutlich mehr Debt und einen niedrigeren mittleren Endindex. Im neu ausgeführten Seed29/-20%-Stresslauf scheitert P2 im ersten Jahr an 327.950 $ nicht geheiltem Cap-Überhang; P0/P1 bleiben fünf Jahre legal. **Kein mathematischer Insolvenzbeweis**: begrenzter Greedy-Transaktionsraum, kein globaler Solver.

Die vorliegenden Modelle benutzen im Hauptvergleich bewusst **dieselbe feste dreijährige Veteranen-Preisstruktur (100/125/150)** auch bei P0 und P1, um die Cut-Kosten zu isolieren. Das ist **nicht** das vollständige ursprüngliche P1-Konzept mit jährlich neu bewerteten Veteranengehältern. Ein separat neu berechneter jährlicher Veteranen-Repricing-Pilot für Seed11 zeigt weiterhin P1-Handelsanreiz (7 statt 4 Trades), aber **keinen robusten Beweis für Gesamtüberlegenheit**. Beide Preiswelten separat ausweisen. Weder der Gesamtsieger der vollständigen Reformpakete (Status quo/Reload/Hybrid/Franchise Cycles) noch echte Championship-Odds sind durch diesen Block bestimmt.

## 1. Hauptvergleich: drei gepaarte 5-Jahres-Welten, −10 % Cap-Stress

Gemeinsam: Oktober-2026-Archiv mit 1.268 Spielern, synthetische sechs Owner pro Seed 11/29/47, 45 reguläre Plätze, 20 Mindestbelegung als Research-Grenze, keine Taxi/IR, 13 Starter, CP6r-Criticality-Preisschicht, fünf Rookie-Runden je Jahr (150 Picks/Liga über fünf Jahre), identischer exogener Spielerentwicklungs- und Exit-Pfad je Seed. Rookie-Zuteilung und damit Preis-/Top120-Cap können durch endogene Ownerentscheidungen leicht variieren; nicht als stets gleiche Dollar-Caps ausgeben. Keine echten 2027–36 NFL-Ergebnisse. Top4 ist **Rang im Starterindex, keine Playoff-Qualifikation**.

| Modell | Legale 5-Jahres-Pfade | Trades | Settlement-Cuts | Ø Endindex | Ø höchster Endindex | Median Endspread | Anfangs schwache Teams: Top4-Jahre | Nachhaltig aufgeholt | Anfangsleader Rang 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 – keine Dead Cap | 3/3 | 5 | 338 | 172,89 | 185,30 | 20,46 | 7/30 | 1/6 | 11/15 |
| P1 – Retained Salary | 3/3 | 13 | 340 | 174,47 | 179,80 | 11,46 | 11/30 | 3/6 | 9/15 |
| P2 – mehrjährige Garantien | 3/3 | 17 | 347 | 170,13 | 176,47 | 12,22 | 8/30 | 2/6 | 6/15 |

Definitionen: Anfangs schwach = die beiden niedrigsten Startindizes je Seed. Nachhaltig aufgeholt = wenigstens zwei aufeinanderfolgende Top4-Indexjahre, nicht Championship-Wahrscheinlichkeit. Endspread = höchster minus niedrigster Index in 2031; Median über drei Welten. Anfangsleader jeweils anhand eingefrorener Startwelt ermittelt. Es gibt keinen Passiv-vs-Skill-Kausaltest. Niedrigere Indexstreuung kann durch echte Verbesserung der Schwächeren **oder** durch Schwächung der Stärkeren entstehen; insbesondere P2 hat geringeren mittleren Endindex. Hohe Managementqualität darf weiter belohnt werden.

### Cap-Ökonomie und Vollzug

| Modell | Summe jährlicher Current Dead Cap über 15 Liga-Jahre (Mio. $) | Ende 2031 noch fällige Future Dead Cap über drei Alternativen (Mio. $) | NFL-Exits | Draft-Kapazitätscuts | Settlement-Schritte |
|---|---:|---:|---:|---:|---:|
| P0 – keine Dead Cap | 0,00 | 0,00 | 28 | 0 | 338 |
| P1 – Retained Salary | 952,53 | 0,00 | 28 | 0 | 340 |
| P2 – mehrjährige Garantien | 1.789,99 | 96,60 | 27 | 0 | 347 |

Die Dead-Cap-Summe über alternative Pfade und Jahre ist weder aktueller Schuldenstand noch ein echter Liga-Dollarbetrag. Zukünftiges Debt wird **nur am letzten Zustand** aggregiert, nicht mehrfach über Jahre aufsummiert. Settlement-Cuts sind nicht gleich alle Abgänge; Exits und Draft-Kapazitätscuts separat. Zählbare Schritte sind kein gemessener Commissioner-Zeitaufwand. Es gab keinen Beleg, dass 45 Slots im fünfjährigen Hauptvergleich limitieren (maximal 44 belegt).

## 2. Starker Cap-Stress: zwei unabhängige −20-%-Welten

| Seed | Modell | Durchlaufene Jahre | Trades | Settlement-Cuts | Ø Endindex nur vollständiger Pfade | Offener Cap-Überhang beim Abbruch (Mio. $) |
|---:|---|---:|---:|---:|---:|---:|
| 11 | P0 – keine Dead Cap | 5/5 | 3 | 120 | 169,44 | 0 |
| 11 | P1 – Retained Salary | 5/5 | 3 | 124 | 170,19 | 0 |
| 11 | P2 – mehrjährige Garantien | 5/5 | 3 | 131 | 167,25 | 0 |
| 29 | P0 – keine Dead Cap | 5/5 | 0 | 132 | 166,30 | 0 |
| 29 | P1 – Retained Salary | 5/5 | 2 | 134 | 165,54 | 0 |
| 29 | P2 – mehrjährige Garantien | 1/5 | 2 | 21 | – | 0,33 |

Seed29 ist ein neuer kompletter Source-Lauf in diesem Auftrag. In P2 bleibt Team 2 nach 2027 bei 393.750.529 $ gegenüber Cap 393.422.579 $ und 20 regulären Spielern. Die Buchung ist konsistent; weitere erlaubte Greedy-Moves fehlen. P0/P1 erreichen 2031. **Keine Extrapolation fehlender vier Jahre und keine Durchschnittsbildung über gemischte Beobachtungsfenster.** P2 kann durch andere Trade-Pakete, andere Strategie oder FA-Vertragswahl eventuell legal werden. Der frühere CP7b-Fail in dieser Ausgangswelt und der neue CP7c-Fail sind ein Warnsignal, keine formale Insolvenz.

## 3. Zehnjahres-Sensitivität: Seed11, −10 %, P0/P1

| Modell | Trades | Settlement-Cuts | Draft-Kapazitätscuts | Ø Endindex | Max Endindex | Endspread | Anfangsleader Top4 | Anfangs schwach Top4-Teamjahre | Nachhaltige Aufholfälle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 – keine Dead Cap | 4 | 215 | 88 | 161,98 | 165,43 | 14,55 | 10/10 | 6/20 | 2/2 |
| P1 – Retained Salary | 7 | 274 | 71 | 164,36 | 172,50 | 11,33 | 6/10 | 10/20 | 2/2 |

Beide Pfade vollständig legal; Jahre 2027–31 stimmen exakt mit dem zugehörigen Fünfjahreslauf überein. Das ist eine verlängerte Gegenwelt, **keine unabhängige Replikation**. Der Anfangsleader bleibt in P0 10/10 unter den vier stärksten Teams, in P1 6/10; keine Aussage über Titel. Über zehn Jahre werden 45 Plätze tatsächlich erreicht; 88 bzw. 71 Draft-Kapazitätscuts sind Modellereignisse und kein Nachweis eines Optimums 45 vs 40/50. P1 schafft mehr Wechsel und bessere Aufholindikatoren, verursacht aber zusätzliche Settlement- und Dead-Cap-Kosten. Kein zehnjähriger P2-Pfad vorhanden; nicht als unterlegen über zehn Jahre bezeichnen.

## 4. Neue Preisarchitektur-Gegenprobe: jährlich neu bewertete Veteranen

Eigene [Source-Variante](cp7c_annual_salary_sensitivity.mjs), [vollständige Eventdaten](2026-11-27-cp7c-seed11-annual-veteran-sensitivity.json). Seed11, −10 %, fünf Jahre, identische Ausgangsspieler; P0/P1-Veteranen erhalten jeweils bei Salary Reprice einen aktuellen CP6r-Criticality-Preis statt einer dreijährigen festen Veteranenstaffel. Initiale Erwerbstenure bleibt erhalten; Rookie-Schedules bleiben separat. Die bestehende vereinfachte Rookie-/FA-/Exit-Logik des Forschungsrechenkerns bleibt bestehen: insbesondere die Behandlung rabattierter wiederaufgenommener Rookies und inaktive Spieler ist **nicht** vollständig als kanonisches Konzept rekonstruiert. Daher Sensitivität, nicht finale P1-Implementation.

| Modell | Legale Jahre | Trades | Settlement-Cuts | Ø Endindex | Max Endindex | Endspread | Summe jährlicher Dead Cap (Mio. $) |
|---|---:|---:|---:|---:|---:|---:|---:|
| P0 – keine Dead Cap | 5/5 | 4 | 67 | 178,63 | 185,88 | 16,25 | 0,00 |
| P1 – Retained Salary | 5/5 | 7 | 81 | 180,31 | 188,03 | 19,26 | 159,57 |
| P1 – Retained Salary (Reset zuerst) | 5/5 | 4 | 67 | 178,63 | 185,88 | 16,25 | 0,00 |

Die jährlich neu bewertete Variante produziert deutlich weniger Cuts als die Fixpreisvariante in derselben Ausgangswelt. P1 behält mehr Trades gegenüber der entsprechenden Nullkontrolle, aber auch mehr Cuts. Endspread ist in der jährlichen P1-Welt größer als in P0: ein direktes Gegenbeispiel zur Annahme, P1 mache die Liga stets ausgeglichener. Das isolierte Ergebnis ist **ein Seed**, keine belastbare allgemeine Rangfolge. Fixpreis- und Annual-Pfade nicht als identische Pakete zusammenfassen.

## 5. Reset-Gate: was ist tatsächlich bewiesen?

Die vier gespeicherten fixpreisigen P1-Reset-first-Pfade (drei Seeds −10 %, Seed11 −20 %) und der jährliche Sensitivitätspfad sind in **sämtlichen** Jahreszuständen exakt gleich ihrer P0-Kontrolle. Das ist die erwartete Folge der **expliziten Modellannahme**, dass im Reset-first-Extrem vor der bindenden Compliance weder Cut-Debt noch Rabatt wirksam sind; nicht eine unabhängig entdeckte empirische Aussage über den realen Kalender. Historische CP4c/CP5c-Gegenprobe: 30.06.2026 23:59:59 UTC als tatsächliche Cap Deadline, aber Reihenfolge Repricing/Reset/Compliance im neuen Konzept nicht beschlossen. Die Simulation modelliert keinen exakten datierten Vor-Reset-Handelsmarkt mit altem Preisvektor, anschließendem Repricing und realem Waiver-Claim. CP7b hatte 13/40 volle versus 16/40 rabattierte historische finanzierbare Käuferpaare. Daher muss die verbindliche Offseason-Kontrollphase so liegen, dass der gewünschte Cut-Anreiz wirtschaftlich wirksam ist. Keine neue Kontrollregel festgelegt.

## 6. Sechs Nordstern-Ziele – Entscheidung ohne Scheinpräzision

| Ziel | Evidenz aus CP7c | Bewertung |
|---|---|---|
| 1 Langfristige Chancengleichheit | P1 3/6 nachhaltige Index-Aufholfälle vs P0 1/6, P2 2/6; ein P2-Greedy-Fail im harten Stress | P1 günstiger im vorliegenden Hauptvergleich, nicht kalibrierte Titelchancen |
| 2 Management belohnen | Unterschiedliche Agentengewichte in Draft/Handel, kein identischer Skill-Interventionstest, keine echten Angebote | offen |
| 3 Keine zementierte Dominanz | Anfangsleader Rang 1 in 11/15, 9/15, 6/15; 10y P0/P1 mit 10/10 vs 6/10 Top4 | P1/P2 vermindern beobachtete Index-Persistenz, kein dauerhaft finanzierbares globales Startermaximum |
| 4 Wirtschaftliche Konsequenzen | Current/Future Debt, vollständige Transfer-Salaries, Cut-Ersatzkosten; mehrjährige Schulden können Settlement erschweren | wirksam, stärkere Strafe nicht automatisch besser |
| 5 Strategische Freiheit | Rookie-Draft und unterschiedliche Agentengewichte, 1:1-Trade und Cut-Option; keine Picks/Bundle, kein freiwilliger Markt ohne Cap-Druck, kein vollständiger Rebuild/Reload-Agent | teilweise |
| 6 Operative Umsetzbarkeit | P1/P0 alle getesteten Pfade legal; P2 1 beobachteter Greedy-Fail; mehrjährige Verpflichtungen und zusätzliche Kontrollereignisse | Vorteil der einfacheren Buchhaltung plausibel; Sleeper-Vollzug und reale Operator-Minuten offen |

**Keine Gesamtpunktzahl und kein Schluss, dass Ergebnisgleichheit ein Ziel wäre.** Nur die geschützte Philosophie gilt; Liga-Ratifizierung weiterhin offen.

## 7. Validierung und fünf ökonomische Achsen

Über die sieben eingelesenen Datenartefakte sind 24 gespeicherte Pfade (23 vollständig legal), 126 Jahreszustände / 756 Teamjahre, 82 angenommene Proxy-Trades, 2849 Settlement-Cuts und 164 Folgejahr-Transferzeilen erneut geprüft. Enthält Reset-Kontrollen und überlappende 5-/10-Jahrespräfixe; **keine 24 unabhängigen Stichproben**. Dollar-Invarianten für Trade-Seller/Buyer, Cut/Replacement/Dead und Folgejahres-Transfers sowie Cap-/Roster-Legalitätsflags bestanden. 1 abgebrochener Greedy-Fall erhalten. Source und Archiv-Blob pro Datei dokumentiert. Das alte Seed29-v1-Artefakt mit abweichender Source ist ausgeschlossen. Neue Runs in V8 mit Datei-/Moduladapter ausgeführt, **kein unabhängiger Node CLI/CI-Lauf**.

1. Seller Relief: kompletter aktueller Vertrag abzüglich Gegenleistung und Cut-Schuld; alle Event-Bilanzen überprüft. Kein aktives Top20-Äquivalent im Full-Salary-45-Slot-Modell.
2. Buyer Burden: volle restliche Verträge, 1:1 Gegenspieler, aktuelle Cap-/Positionsdeckung, Folgejahr-Schedules bilanziert; reale zukünftige Zahlungsfähigkeit/Owner-Consent nicht bekannt. Annual-Veteranen-Future-Contract-0 ist kein Beweis kostenloser künftiger Gehälter, sondern fehlende bindende feste Verpflichtung.
3. Roster: eindeutige Ownership gemäß Engine, 20–45 Slots und modellierte Positionen; tatsächliche IR/Taxi/Sleeper-Eligibility unmodelliert. In zehn Jahren werden Slots erreicht. Draft-Kapazitätslog ist begrenzt auf beobachtete vorherige Owner; keine unabhängige Prüfung aller eventuell innerhalb desselben Rookie-Drafts verworfenen Picks.
4. Ligaweite Debt: jährlich fällige und letzte zukünftige Verpflichtungen getrennt; keine Kredite, kein Schuldenerlass außer P1-Zyklusreset; echte Schuldenkonzentration je Owner über alle Jahre nicht vollständig separat erfasst.
5. Future Repayment: jedes modellierte Folgejahr tatsächlich settled oder Pfad abgebrochen, keine echte künftige Cap-Prognose; keine automatische Sanktion oder fiktiver Commissioner-Kredit.

## 8. Empfehlung und verbleibende Grenzen

**P1 bleibt die bevorzugte einfache Forschungshypothese, nicht beschlossene Regel.** P2 ist für eine breitere Franchise-Cycles-Strategie noch relevant, aber der stärkere Trade-Anreiz allein rechtfertigt Mehrjahresgarantien nicht. P0 bleibt notwendige einfache Nullkontrolle. Die neue jährliche Sensitivität relativiert die Fixpreisresultate: weniger Cuts bei jährlichen Preisen, aber P1 nicht immer besserer Endspread. Aus dem Pilot lässt sich noch nicht der optimale Cap-Faktor, DMLI-Salary, dauerhaft maximale Starterindex oder die richtige Rookie-/Veteranenvertragsmischung wählen.

Für einen belastbaren Paketvergleich fehlen: tatsächlich datierter Salary-Check-/Reset-Kalender samt Waiver-/FA-Claims; historisch rekonstruierte Tenure und Kader der sechs Owner (keine rückwärts erfundenen Vertragsdaten); vollständiger S0-Replay unter echtem 30+5IR+2Taxi-Format und altem Top20-Cap; ein gemeinsames vollständiges Paketmodell mit dynamisch neu ermittelter Criticality-Kurve bzw. alter Performance-Salary als Preis-Kontrolle; realistische Rookie-Pick-/Asset-Transfers und freiwilliger Handel; echte Skill-Gegenwelten, explizite Verletzungs-/Availability-Schocks; weitere Seeds für Annual- und −20%-Stress, 10y P2, exakte/maximale Starterindex-Optimierung, unabhängige Node-/CI-Verifikation sowie empirischer Commissioner-Aufwand. Die P2-Neuvertrags-FA-Preisregel bleibt undefiniert und Cut-Spieler sind deshalb im selben Jahr blockiert; das ist eine wesentliche asymmetrische Marktannahme. **Kein abschließendes Gesamtranking und keine aktive Regeländerung.** Nicht jede dieser Grenzen benötigt eine weitere isolierte Forschungsserie; vor weiteren Runs zuerst die vollständigen Modellpakete/Preis- und Kalenderregeln im Benchmark trennscharf festlegen.

### Quelldaten

- [2026-11-27-cp7c-seed11-shock10-fiveyear.json](2026-11-27-cp7c-seed11-shock10-fiveyear.json) · Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`
- [2026-11-27-cp7c-seed29-shock10-fiveyear-v2.json](2026-11-27-cp7c-seed29-shock10-fiveyear-v2.json) · Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`
- [2026-11-27-cp7c-seed47-shock10-fiveyear.json](2026-11-27-cp7c-seed47-shock10-fiveyear.json) · Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`
- [2026-11-27-cp7c-seed11-shock20-fiveyear.json](2026-11-27-cp7c-seed11-shock20-fiveyear.json) · Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`
- [2026-11-27-cp7c-seed29-shock20-fiveyear.json](2026-11-27-cp7c-seed29-shock20-fiveyear.json) · Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`
- [2026-11-27-cp7c-seed11-shock10-tenyear-p0p1.json](2026-11-27-cp7c-seed11-shock10-tenyear-p0p1.json) · Source-Blob `3005ac081215f04eb62812961511d178cfacdf53`
- [2026-11-27-cp7c-seed11-annual-veteran-sensitivity.json](2026-11-27-cp7c-seed11-annual-veteran-sensitivity.json) · Source-Blob `09cdcc3bf7fe2401be7a317d081af76e6a02312b`
