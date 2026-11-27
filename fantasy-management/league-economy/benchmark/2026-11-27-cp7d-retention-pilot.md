# CP7d – Salary-Architektur und Dynasty-Spielerbindung (erster gepaarter Pilot)

Stand 27.11.2026 · #1344 · Draft PR #1576 · **Research, kein Regelbeschluss.** Neue vom Nutzer gewünschte Messdimension: langfristige ununterbrochene Teamzugehörigkeit und Entwicklung gedrafteter Spieler. Der Nordstern bleibt unverändert; Spielerbindung ist ein diagnostischer Aspekt strategischer Freiheit, kein siebtes normatives Ziel.

## Design und Ergebnisse

CP6r/CP7c Source-Blobs wie im [Seed11-Datensatz](2026-11-27-cp7d-retention-pilot.json) festgehalten. [Reproduktionsskript](cp7d_retention_pilot.mjs), Node-Aufruf `node fantasy-management/league-economy/benchmark/cp7d_retention_pilot.mjs 11 5 45` (Seed/Seasons/Slots); V8-Ausführung erfolgreich, unabhängiger Node-CLI/CI-Run noch offen. Drei gepaarte 45er-Welten, Seeds 11/29/47, 2027–31, 120 initiale Spieler bzw. 20 je Team, -10% jährlicher Cap-only-Stress, volle Salary-Anrechnung, 13 Starter, kein Taxi/IR. P0/P1 jährliche Veteranen-Neubewertung, P2 gemeinsame dreijährige Veteranenstaffel mit Vertragsgarantien. Gleiche exogene Futures, endogene Picks/Preise können differieren. P0/P1 sind keine S0-Ist-Liga. P2 ist ein kombiniertes Modell, nicht isolierter Vertragseffekt.

| Modell | Initiale Spieler noch beim selben Team (von 360) | Initiale Starter (von 234) | Gedraftete Spieler mindestens zwei weitere Checkpoints behalten (von 270) | Davon aktuelle Starter | Ø Kader | Ø Endindex | Trades | Settlement-Cuts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 261 | 154 | 162 | 40 | 42.00 | 178.46 | 6 | 207 |
| retained_cycle | 245 | 140 | 143 | 40 | 39.83 | 179.32 | 13 | 218 |
| guaranteed_vintage | 118 | 77 | 151 | 60 | 37.56 | 170.13 | 17 | 347 |

Alle 9 Hauptpfade legal. 330/360 der Ausgangsspieler noch NFL-aktiv im synthetischen Modell. Beobachtete Transaktionsunterbrechungen (Trades, Settlement-Cuts, NFL-Exits, Capacity-Cuts) setzen Cohort zurück; Startvintage nur künstlich. Draft-Kohorte umfasst die am Draftende zugeordneten Spieler aus 2027–29, nicht alle denkbaren unmittelbaren Draft-and-Cut-Ereignisse. Starterstatus aus dem jährlichen Known-Index, keine realen Wochenaufstellungen. P2 hält weniger ursprüngliche Spieler und hat mehr Cuts, aber mehr der verbliebenen gedrafteten Spieler sind am Ende Starter (60 statt je 40); das ist kein isolierter Rookie-Effekt oder Skill-Nachweis. P1 senkt die beobachtete Anfangskaderbindung in allen drei Seeds, erzielt mehr Trades und einen leicht höheren mittleren Endindex. Die Daten unterscheiden keine echte Identifikation/Fanbindung und keine kausale Entscheidungsmotivation.

## Slot-Paarprobe Seed11, fünf Jahre

| Slots | P0 Settlement/Capacity-Cuts | P1 Settlement/Capacity-Cuts | P0 Ø Kader | P1 Ø Kader | P0 ursprüngliche Spieler | P1 ursprüngliche Spieler |
|---|---:|---:|---:|---:|---:|---:|
| 40 | 56/17 | 69/13 | 39.67 | 38.83 | 88 | 76 |
| 45 | 67/0 | 81/0 | 41.83 | 40.00 | 88 | 77 |
| 50 | 67/0 | 81/0 | 41.83 | 40.00 | 88 | 77 |

Alle 4 zusätzlichen Pfade legal; 13 gesamte Pfade, 390 Teamjahre, davon überlappende Paarwelten. Größerer Kader reduziert erzwungene Capacity-Cuts; nicht zwingend sämtliche Cuts. 50 liefert in dieser Welt identische Jahresaggregationen zu 45. Keine Aussage über 10 Jahre oder volle Startkader; 40/45/50 nicht abschließend entschieden.

## Finanzachsen und Nordstern

Seller relief und buyer burden werden durch unveränderte CP7c 1:1-Trade-/Cut-Buchungsinvarianten im Lauf geprüft; neue Datei enthält Jahresaggregationen, keine vollständigen einzelnen Cashflows oder angenommenen Menschenangebote. Roster eligibility: vollständige Salary, 40/45/50 reguläre Plätze, 20 Forschungsminimum, keine Taxi/IR, alle modellierten Pfade legal. Debt am Ende 2031 summiert über drei alternative Welten (keine reale Liga): none: 0 current, 0 future; retained_cycle: 122347280 current, 0 future; guaranteed_vintage: 452679267 current, 96603564 future Dollar. Future repayment: Folgejahres-Settlement ist Teil der Simulation, tatsächliche künftige Preise, Käuferzustimmung, exakte Vintages und Commissioner-Minuten nicht beobachtet. Jahresdaten sind kein vollständiger Fünf-Achsen-Audit; vollständiger Eventexport und Replay vor Fachentscheidung erforderlich.

Nordstern: (1) keine Championship-Chancen abgeleitet; (2) Skill nicht isoliert; (3) Anfangskaderbindung nicht gleich zementierte Dominanz; (4) reale Modellkosten, aber kein echter Markt; (5) 45 Slots plausibler Entwicklungsraum, mehrjährige Verträge nicht als Bindungsgarantie belegt; (6) alle Pilotpfade legal, reale Durchsetzung ungeprüft. Keine neue verbindliche Regel.

## Artefakte und nächste Gates

[Seed11 45](2026-11-27-cp7d-retention-pilot.json) · [Seed29 45](2026-11-27-cp7d-seed29-45slot-pilot.json) · [Seed47 45](2026-11-27-cp7d-seed47-45slot-pilot.json) · [40](2026-11-27-cp7d-seed11-40slot-pilot.json) · [50](2026-11-27-cp7d-seed11-50slot-pilot.json).

Offen: tatsächlicher S0-Replay (30 regular + 5 IR + 2 Taxi, Top20, Faktor 0.90; aktueller League.json Cap 427.653.631 Dollar, nicht mit synthetischer 45er-Welt gleichsetzen), vollständige isolierte Faktorprüfung annual/fixed × Dead Cap bei mehreren Seeds und Schocks, 10 Jahre 40/45/50 mit hoher Startbelegung, exakte Draft-and-Cut-Tenure, Rookie-Floor/FA/Reset-Semantik, Skill, echte Verletzungen/Markt/operative Enforcement, unabhängiger Node/CI-Lauf. Große Matrix im interaktiven V8-Ausführungslimit abgebrochen, danach in kleinen überprüfbaren Läufen gespeichert. **CP7d ist ein Teilcheckpoint, nicht der abgeschlossene S0-Gesamtvergleich.**
