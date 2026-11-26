# CP7a – Einheitlicher Benchmark für Ligaökonomie und Dead-Cap-Trade-Anreize

> Stand 26.11.2026. Forschung zu Issue #1344, bestehender Draft PR #1576. Keine aktive Liga-Regeländerung oder Ratifizierung.

## Zweck und Forschungsfrage

Das primäre neue Dead-Cap-Ziel lautet: **Abgabewillige Teams sollen in der Offseason einen finanziellen Anreiz haben, Spieler vor einem Cut tatsächlich zu traden.** Dies ist nur erfolgreich, wenn sich beidseitig legale und akzeptable Trade-Pakete mit realistisch möglichen Käufern ergeben. Eine höhere Cut-Strafe, weniger Cuts oder mehr theoretisch cap-legale 1:1-Paare allein sind keine Erfolgskriterien.

Ein gemeinsamer Benchmark soll auch langfristige Aufholbarkeit, Leistungsbelohnung, die Vermeidung automatisch zementierter Dominanz, wirtschaftliche Konsequenzen, echte Strategiealternativen sowie die operative Durchsetzbarkeit anhand der sechs geschützten Nordsternziele prüfen.

## Einheitliche Vergleichsarchitektur

**S0 – Unveränderte historische Liga:** tatsächliche jeweilige Regeln, Eigentumsstände, Salary, normale Spielerplätze + echte Taxi-/IR-Slots und Kalenderdaten. Der zuletzt abgerufene aktive Rahmen hatte 30 reguläre / fünf IR / zwei Taxi. S0 wird nicht stillschweigend auf 45 Plätze normalisiert.

**P0 – Null-Dead-Cap-Kontrolle:** gemeinsame Reform-Research-Welt, 45 reguläre Plätze, kein Taxi, kein kostenlos erfundenes IR, alle aktiven Spieler voll gegen den Cap. Cut erzeugt keine Dead-Cap-Schuld. Kein automatisch behaupteter neuer FA-Marktpreis.

**P1 – Tenure-Retained-Salary:** dieselbe Reformwelt mit ursprünglichem Konzept aus salary/salary-dead-cap-concept.md. Bei Cut 50/30/15/5 Prozent gemäß 0/1/2/3+ aufeinanderfolgenden Team-Seasons als einbehaltene aktive Salary. Das aktive Salary für den nächsten Besitzer sinkt um genau diesen Betrag, vorbehaltlich Minimum-Salary-Floor. Die Schulden werden NUR bei regulärer Salary-Neubewertung/Ende des Salary-Zyklus zurückgesetzt; ein weiterer Cap-Checkpoint ist NICHT automatisch ein Repricing.

**P2 – Mehrjährige Vertragsgarantie:** dieselbe Reformwelt mit CP6-Vertragsvintages. Rookie-Year-1-Salary basiert auf tatsächlich ausgeübtem Fantasy-Pick und 65/35 Fantasy-/NFL-Draft-Wertung, für Jahre 1/2/3 mit 100/125/150 Prozent. Garantien nach Fantasy-Runde 1–2: 100/100/100; R3–4: 100/100/50; R5/UDFA: 100/50/25. Veteranenverträge und deren Steigerung werden als separater Parameter fixiert. Cut erzeugt im alten Owner-Ledger fällige Garantien je Vertragsjahr; Trade überträgt den ungekürzten Restvertrag. **Das neue FA-Salary eines gecutteten Vertragsspielers ist damit noch nicht definiert** und darf nicht erfunden werden.

Ein P3-Hybrid darf später nur unter ausdrücklicher Hypothese ergänzt werden. Keine automatische Doppelbestrafung aus Retained-Salary- und Guarantee-Ledger.

**Trennschärfe:** Zunächst gleiche dynamische Criticality-Salary-Kurve, gleiche Cap-Definition, Spieler- und Managerwelt, Rookie-Draftpreis, Veteranenslope sowie gleiche Salary-/Cap-Stichtage bei P0/P1/P2. Danach orthogonaler Preisvergleich zur heutigen Performance-Salary-Kurve. Die wirklich aktive S0-Welt ist eine historische Systembaseline und kein isolierter Dead-Cap-Test.

## Zeit- und Transaktionsablauf je Offseason

1. Aus exakt datierter Quelle vor Transaktionen: Owner, Spieler, Cap, Vertragspreis, Tenure, Cash-/Dead-Cap-Vintages, Positionen, Slots, Picks, Verletzungen und Salary-Zyklusstatus konservieren; synthetische 2025/26-Verträge ausdrücklich synthetisch kennzeichnen.
2. Gleiche Preise, Top-N-Cap, Rookie-Entwicklung und NFL-Futures anhand stabiler Seed-IDs bestimmen. Salary-Check/-Neubewertung und Cap-Only-Kontrolle sind unterschiedliche Events.
3. **Buyer-/Seller-Trade-Markt zwingend VOR Zwangscuts** öffnen. Verkäufer vergleicht Halten, Trade und Cut. Eine Transaktion kann nur ausgeführt werden, wenn der Käufer vollständig finanzieren kann, beide Teams mit allen Positions-/Kaderpflichten legal sind, die gesamte Asset-Gegenleistung in den Ledgern auftaucht und beide Manager-Agenten sie akzeptieren. Kein Käufer oder kein akzeptables Paket bedeutet **unverkaufbar**, nicht fiktiv gehandelt.
4. Cuts inklusive tatsächlich fälliger Dead Cap vornehmen. Für P1 ist der eventuell niedrigere aktive Waiver-Preis für wartende Käufer sichtbar. Für P2 bleibt der FA-Preis offen, bis eine ausdrückliche Regel gewählt ist; keinesfalls wird der Buyer-Discount aus P1 unterstellt.
5. Gleiche Final-Cap-/Roster-Abrechnung mit nachvollziehbarer Hard-Failure-Option, ohne automatische Fantasie-Commissioner-Sanktion, Kredit oder kostenlosen Debt-Reset.
6. Alle sechs Owner, Assets, Dead-Cap-/Garantieverpflichtungen und Starterindizes über den vollständigen Jahrespfad fortschreiben. Historische beobachtete Resultate strikt von synthetischen künftigen NFL-Ergebnissen trennen.

## Pflicht-Messgrößen

**Primäre Hypothese, Trades:** tatsächlich akzeptierte und ausgeführte Trades (getrennt von rein technisch möglichen Pairings), Anteil gehandelter statt gecutteter abgabewilliger Spieler, Buyer-Verfügbarkeit, unwirtschaftliche / unverkaufbare Spieler, bewusst wartende FA-/Waiver-Käufer, Seller-Nettoentlastung heute und in Folgejahren, Käufer-Nettokosten inklusive Picks/Assets, Positions-/Kader- und Cap-Erfüllung, Deal-Timing relativ zum tatsächlichen Dead-Cap-Reset.

**Alle sechs Nordstern-Ziele:** (1) Zeit und Wahrscheinlichkeit für ein schwaches Team, wieder Championship-relevant zu werden; (2) Skill-Prämie bei gleichem NFL-Glück; (3) Haltbarkeit eines hohen Starterindex ohne erneute gute Entscheidungen; (4) Opportunitätskosten von Stars und gesamte Dead-Cap-Exposition; (5) All-in/Reload/Rebuild/Flex, Pick- und Veteranen-Marktliquidität; (6) Fehlerfälle, erklärbare Regeln und gemessener Commissioner-Aufwand.

**Verpflichtende fünf Wirtschaftsachsen pro Cut und Trade:** Seller-Bruttoentlastung/Dead Cap und Netto, vollständige Buyer-Last/Gegenleistung, tatsächlich ausführbare Roster- und IR-/Taxi-Belegung, ligawerte und Owner-Dead-Cap-/Garantie-Vintages, zukünftige Zahlungsfähigkeit ohne versteckte Refinanzierung. Nicht beobachteter realer Buyer-Consent, echte künftige NFL-/Salary-Werte, Operator-Minuten als unbekannt markieren, niemals als null.

## Methodik und Abnahmeregeln

- Gepaartes Vergleichsdesign: identische NFL-Spieler-, Injury-, Rookie-, Aging- und Preisentwicklung (Common Random Numbers); identische sechs initiale Kader und Draftrechte. Managerrollen rotieren durch alle sechs Owner, um Team-0-Bevorzugung auszuschließen.
- Historische Backtests und ausdrücklich synthetische 2027+ Mehrjahrespfade separat, Minimum fünf Jahre, selektive längere Extreme; viele Seeds, Markt-Cap-Schocks und schwach/stark verwaltete Manager.
- Preis-/Criticality-Faktoren nur in einer separaten kontrollierten Faktoranalyse variieren, damit Dead-Cap-Wirkung kausal interpretierbar bleibt.
- Prüf-Gates vor jeder Rangfolge: gültige Geld- und Owner-Bilanzen, keine unfinanzierbaren Käufer, Kader-/Positions- und Pick-Eindeutigkeit, Dead-Cap-Reset-Timing, Hard-Failure-Pfade, unabhängiger Node-/CI-Lauf. Kein einzelner Team-0- oder Seed-Wert ist ein Liga-Erfolgsbeleg.
- Erst nach gültigen Kontrollläufen alle sechs Ziele bewerten und Gewichtungen sowie Gewichtungs-Sensitivität vor dem finalen Ranking festlegen. Das einfachere Paket gewinnt, solange Mehrkomplexität keinen robusten zusätzlichen Nutzen zeigt.
- **Stoppkriterium:** entweder stabiler Sieger/Gleichstand über Seeds, Rollen, Stress und Bewertungsgewichte oder zusätzliche Forschung kann nur noch unbekanntes echtes Managerverhalten ersetzen. Kein unbegrenzter Ausbau von CP6r um reine Detailfeatures.

## Checkpoints

**CP7a (hier):** dokumentierter Benchmark-Contract und isolierte Testfälle zu Cut-/Trade-/Debt-Buchhaltung.

**CP7b:** gemeinsames Szenario-/Event-Ledger und Trade-vor-Cut-Paarwelten P0/P1/P2 unter identischen Criticality-Preisen, Käufern und Zeitfenstern.

**CP7c:** kontrollierte fünf- bis zehnjährige Owner-Agenten-, Verletzungs-/Liquiditäts-/Cap-Stress-Simulation mit sechs-Nordstern-Scorecard und Gegenprobe einfacher vs. komplizierter Modelle.

**Finaler Schritt:** ausführbare Offseason-Ligaoptionen mit tatsächlichem Sleeper-/IR-/Commissioner-Aufwand für alle sechs Manager zur Abstimmung; keinerlei produktive Regelumstellung ohne separaten Beschluss.
