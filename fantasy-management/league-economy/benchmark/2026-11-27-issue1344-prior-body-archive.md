<!-- Immutable historical snapshot of Issue #1344 before compacting its exceptionally long body. It is not the current operative work-tracking source of truth. Current state remains Issue #1344. Source: actual GitHub Issue body retrieved 2026-11-27. -->

## CP7b – PR-Beschreibung mit historischer Deadline-Gegenprobe synchronisiert

[Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) enthält jetzt CP4c-/CP5c-Kalender-/Käufer-Gate: historisch reale Dead-Cap-Reset-Reihenfolge und billigere Waiver-Angebote können den synthetisch gemessenen P1-Handelsanreiz aufheben. Branch-Head `072c64268096d0e8531b77b22e2712c0c1eac1ba`, Bericht und Benchmark-Präzisierung auf gleichem Stand. Kein Merge und keine aktive Ligaregel geändert.

---

## CP7b – Draft PR #1576 mit konsolidiertem Benchmark synchronisiert

PR [#1576](https://github.com/Lolindhir/fantasy-app/pull/1576) auf Head `acb8decbcabd42a237be352cd2602269a2fc2686` aktualisiert, bleibt **offen / Draft**. CP7b-Bericht, Aggregate und drei Voll-Event-Ledger auf Forschungsbranch vorhanden; Issue #1344 bleibt operative kanonische State-Quelle. Kein Merge, kein produktiver Salary-/Roster-/Sleeper-/Frontend-Writer verändert. Noch ausstehend: zukünftige regulatorische Parameter und CP7c-Mehrjahresvergleich, unabhängige Node-/CI-Verifikation.

---

## CP7b – dritter Seed nach finalen P1/P2-Preis- und Vertragskorrekturen auditiert

[Seed47-V2-Ergebnisse](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed47-results.json), Commit `7ae375f03682de3a9fc8f18e3edbf2ca45b40f56`, Source-Blob `42b3cf71681ee22df7bfa395839473f656475807`; 9/9 legale 2027er Paarszenarien, 10 hypothetische bilaterale Trades, 21 Cuts/FA-Replacements, 20 auditiert künftige Vertragszahlungstransfers, 0 tatsächlich rabattierte P1-Weiteraufnahmen. Seed11/29/47 wieder auf identischem letzten Source-Blob – danach faire Drei-Seed-Auswertung möglich. Keine echte Marktgleichgewichts-/Championship-/historische Vertragsbehauptung.

---

## CP7b – Seed29 im aktuellen P1/P2-FA-Preisvertrag verifiziert

[Seed29-V2-Forschungsdaten](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed29-results.json), Commit `357ad169130ebc25bb4a5ea24a665594a6d58473`, Source `42b3cf71681ee22df7bfa395839473f656475807`: 8/9 cap-/rosterlegal, 9 Proxy-Trades, 42 exakt abgerechnete Cuts; 18 künftige volle Buyer-/Seller-Contract-Transferzeilen konserviert; 1 nicht gecurete Settlement-Pfade transparent dokumentiert und ausdrücklich **kein mathematischer Insolvenznachweis**. 2 P1-Replacements zum tatsächlich rabattierten Released-Player-Preis. Waiver-Wartewahrscheinlichkeit 0/1 Sensitivität auditiert; echte Claims/Käufer weiterhin unmodelliert. Live-Liga unverändert.

---

## CP7b – Seed11 Neuvalidierung nach P1-Waiver-Preis-Korrektur

[Seed11, neun Pair-Snapshots](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed11-results.json), Commit `b62ccec01bb4baaca40546ce50dbe56562c673be`, Source-Blob `42b3cf71681ee22df7bfa395839473f656475807`: 9/9 legal, 19 hypothetische 1:1-Trades, 17 Cuts, alle 38 Future-Salary-Transferzeilen bilanziert; 0 P1-Cutplayer wurde(n) in den nachfolgenden Cut-Replacement-Schritten tatsächlich zum niedrigeren aktiven Preis aufgenommen. P2 post-Cut-FA-Preis weiterhin undefined → keine künstlichen vergünstigten P2-Signings. Voraussichtlicher vollständiger Seedvergleich erst nach Seed29/47-Neulauf. Nur Forschungsmodell.

---

## CP7b – zwingende P1-Waiver-/P2-Neuvertrags-Korrektur

[CP7b-Markt](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs) Commit `3131509acb4e6ef957978d016a8f9d8506453c2c`: Ein späterer Seller-Cut in derselben Research-Offseason darf einen zuvor entlassenen P1-Spieler jetzt zum **verbindlich reduzierten aktiven Retained-Salary-Wert** als Replacement übernehmen (auch in Nutzenprüfung und Vertragsledger), statt fälschlich wieder zum ursprünglichen Vollpreis. Für P2 bleibt der neue FA-Vertragspreis nach Cut **ungeregelt**; daher werden gecuttete P2-Spieler in dieser 2027-Simulationsphase nicht als scheinbar kostenlos/neuvertraglich definierte FA-Replacements angeboten. Das ist eine Modellabgrenzung, keine neue Ligaregel. **Seed 11/29/47 Batch-JSONs unter altem Source-Blob jetzt veraltet und neu auszuführen**, bevor Vergleich/Empfehlung veröffentlicht wird.

---

## CP7b – Seed47 als dritter vollständiger Quellenkontrolllauf

[Seed47-Ergebnisse](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed47-results.json), Commit `30224845106dec00bc5cfe4abb6639aeaee443f2` gegen denselben CP7b-Simulationsblob `30937b747102f89073093f9384e24d7ee5ae1148`: **9/9** cap-/rosterlegal, 10 beidseitig nutzenpositive **hypothetische** Trades, 22 Ersatz-Cuts, 20 geprüfte Jahrestransfers der vollständigen Vertragskosten. P1-Warte-Sensitivität 0/1 samt Anzahl von Proxy-Angeboten dokumentiert. Drei Seed-Pakete sind jetzt quellen-/parameteridentisch und können konsolidiert werden; kein echter Mehrjahres-/Trade-Angebots-/Commissioner-Beweis. Keine produktive Änderung.

---

## CP7b – Seed29 nach finaler Contract-Transfer-Korrektur neu geprüft

[Seed29-Paarwelten](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed29-results.json), Commit `b97a152e2b198c0fb2840131ca3508064435b067`, endgültiger gemeinsamer Source-Blob `30937b747102f89073093f9384e24d7ee5ae1148`; **8/9** legal, 9 Proxy-Trades, 42 Cut-Events, 18 Zukunftsgehalts-Transferbuchungen vollständig geprüft. 1 nicht gecurete Greedy-Pfade getrennt vom mathematischen Unmöglichkeitsbeweis geführt. P1-Buyer-Wait-Sensitivität 0/1 dokumentiert, nicht als reale Waiver-Signings ausgegeben. Keine produktive Ligaänderung.

---

## CP7b – finaler Seed11-Source-Lauf mit Zukunftslast und Waiver-Sensitivität

[Seed11-Ergebnisse](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed11-results.json) nach Commit `1749e78e158bfee32c3f6ee252f58136d5a44d8f` vollständig unter CP7b-Source-Blob `30937b747102f89073093f9384e24d7ee5ae1148` neu berechnet. 9/9 aktuell cap-/rosterlegal; 19 gegenseitig durch Agenten angenommene **hypothetische** 1:1-Deals, 17 Cut-/Replacement-Events mit exakten Jahres-Salary-/Dead-Cap-Invarianten und 38 zukünftigen Vertragslast-Jahresbuchungen konserviert; echte künftige Cap-Werte weiterhin unbekannt. Retained-Salary-Waiver-Wartewahrscheinlichkeit 0/0,5/1 bei -10/-20 % kontrolliert. Weitere Seeds werden nun identisch aktualisiert; alte Seed29/47-Dateien referenzieren noch Vorversion und dürfen nicht ungekennzeichnet aggregiert werden. Keine produktive Änderung.

---

## CP7b – zusätzliche fünf-Achsen-Vertragsprüfung vor finalem Ranking

[Research-Source](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs), Commit `b694ff3095ad8c040cac4fa3f7d53db0421348fb`: je 1:1-Trade jetzt kompletter Käufer-/Seller-Folgejahres-Salary-Schedule 2028/29, Vor-/Nach-Bilanz und Cap-Headroom bei **eingefrorenem Cap als Stress-Counterfactual**, ausdrücklich **nicht** als tatsächliche zukünftige Finanzierbarkeit oder 2028/29-Cap-Prognose. Zukunfts-Salary wird beim Trade ligaweit exakt konserviert. Synthetische Player-Tenure wird bei Teamwechsel korrekt auf 2027 zurückgesetzt (vorher altes Vintage beibehalten), damit P1-Quote bei einer späteren Wiederabgabe nicht falsch ist. Frühere Seeddaten stammen **vom Vorläuferblob** und dienen nur QA; alle Seed-Auswertungen sind gegen den neuen endgültigen Source-Blob erneut auszuführen. Kein Merge oder aktive Regeländerung.

---

## CP7b – Seed47 durchgerechnet und auditiert

[Neun gepaarte Seed47-Marktversuche](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed47-results.json), Commit `87644c28e5eada5624d8021427812062123c5929`. **9/9 legal**, 0 offene Greedy-Fälle, 10 hypothetisch bilaterale 1:1-Deals, 22 Cuts, alle Event-Salary-/Owner-Eindeutigkeit geprüft. Forschungswelt 2027-Querschnitt / synthetische Owner/Vintages, kein fünfjähriger Vergleich. Vollständige Synthese aller drei Seeds und Modellkritik ist der folgende Checkpoint.

---

## CP7b – Seed29 und potenzieller Settlement-Hard-Failure reproduziert

[Neun gepaarte Seed29-Marktversuche](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed29-results.json), Commit `9cda2450cdeacc9cc577cb20add39abe4e00b78f`, unter derselben Archiv-Preis-/Cap-Basis wie Seed11, 45 Slots, 3 Dead-Cap-Policies × 0/-10/-20 % Stresstest. **8/9** abschließend cap-/rosterlegal; 1 Modellszenario ohne ausreichende legalen Greedy-Settlement-Moves. Letzteres **nicht als mathematisch insolvent bewiesen**, aber als plausibler operativer Hard-Failure gegen die Algorithmus-Policy offengelegt – kein automatischer Commissioner-Kredit oder unsichtbarer Cut. 9 bilaterale synthetische Trades und 42 Cuts mit überprüften Buchhaltungsinvarianten. Referenzwerte sind ausschließlich eine CP7b-2027-Querschnittswelt mit synthetischen Eigentums- und Vertragshistorien. Seed47 und Modellübersicht folgen.

---

## CP7b – Paartest Seed 11 validiert (26.11.2026)

[9 Regime-/Cap-Stress-Snapshots mit vollständigem Trade-/Cut-Event-Ledger](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed11-results.json), Commit `ee4cb857f606ac135d93331c08509758657e00b2`: aus Source-Blob `f029d8d502cb141082600d4dfbfc8ac7ff5076ad`, historischer Oktober-2026-Preisarchiv-Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`, synthetische 6 Owner / 45 Plätze. **9/9 Snapshots legal**, alle 19 bilateralen Proxy-Transaktionen in Seller-/Buyer-Salary konsistent, 17 Cuts je Event exakt gebucht, drei Regime pro identischem 0/-10/-20-%-Cap-Schock vor Settlement. [Leseergebnisse anhand gespeicherter JSON](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-cp7b-seed11-results.json); spätere Seeds noch ausstehend. Das ist **einjährige 2027-Kontrafaktik, kein gültiger 5-Jahres-Economy-Rank oder reales Trade-Angebot**. Nächster Seed und Agentenrollensensitivität folgen.

---

## CP7b – Modellkonformität vor finalen Batch-Auswertungen

[Markt-Simulator](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs), Commit `70f7e512af265f9c5ee83a67b9c6a67a948bdcce`: Retained-Salary-Mindestgehalt jetzt mit **derselben** 0,25–0,50-%-Erfahrungsstaffel und dem eingefrorenen CP6r-Preisanker 434.255.984 $ statt unpräziser fixer 2027-Mindestquote. Sechs Agentenrollen pro Seed tatsächlich rotiert (alte Seeds 11/29/47 hatten wegen Modulo6 identische Rollen). Früherer einzelner Test seed11 nach Quote-Fix war syntaktisch/ledgerlegal, **aber aufgrund beider Modellabweichungen keine finale CP7b-Auswertung**. Nächster Schritt: gepaarte Source-kompilierte Batch-Ergebnisse erneut aus dem aktuellen Blob und vertragliche Invarianten für jeden Pfad verifizieren, persistieren. Keine Live-Änderung.

---

## CP7b – stillen Quote-Feldfehler korrigiert (26.11.2026)

Commit `869bd0391b3c95a16e25accf5465c6663f4da186`, [CP7b-Source](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs): Feldadapter von `cut()` auf `now` und `futureDebt` korrigiert. Vorherige 0-Cut-/0-Trade-Rohresultate durch `NaN` bei Seller-Relief **ungültig**, ausdrücklich nicht als ökonomischer Befund verwenden. Erneute Simulation und Geld-/Kader-Invarianten aus repariertem Source notwendig.

---

## CP7b – gesicherte Modellfehler vor Ergebnisveröffentlichung korrigiert

[CP7b-Source](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs) auf Commit `475e5c6f6f53e92f5b9799f6565946aff710d60b` aktualisiert. Erster Einzel-Seed-Smoketest fand unerreichbare Cut-Replacements (naive billigste FA-Pool-Auswahl mit Null-Leistung) und einen falschen NaN-Buyer-Waiver-Option-Koeffizienten; 1:1-Seller-Nutzen mit ungewollter Doppelwertung des Cap-Reliefs ebenfalls korrigiert. Noch **keine gültigen quantitativen Trade-vs-Cut-Paare** publiziert; erneuter Paartest mit eindeutigen legalen Kader- und Salary-Buchungen erforderlich.

---

## CP7b – ausführbares vorgezogenes Trade-vs-Cut-Marktlabor angelegt

[CP7b-Szenario-Engine](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/cp7b_pre_cut_market.mjs), Commit `4a4e177e644786047115c3897f15819b69e66c28` auf Draft PR #1576: gemeinsamer 6-Team-/45-Slot-/Top120-/Criticality-Snapshot, gleicher Cap-Stress und Archive-Spielerpool; für P0 ohne Dead Cap, P1 Retained-Salary und P2 Contract-Vintage wird **vor** Cut-/FA-Settlement ein beidseitiger 1:1-Spielervertragsmarkt unter positiver Proxy-Managerutility und Buyer-Cap-Legality geöffnet. Keinerlei echte Trades behauptet; keine Pick-/Bundle-/IR- oder echte 2027-NFL-Simulation. **Source syntaktisch kompiliert, unabhängiger Node/CI-/Fullrun noch ausstehend.** Es folgt die Ausführung mit Seed-/Cap-Stress-Paarwelten und Prüfung von Settlement-Hard-Failures.

---

## CP7b – gemeinsamer Sechs-Team-Startzustand verfügbar (26.11.2026)

[CP6r Research-Simulator](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6r_45slot_trade_strategy.mjs) um ausschließlich einen Forschungs-Export `createCP7bBase` für **dieselben disjunkten sechs synthetischen Owner und die historische 1.268-Spieler-Preisbasis** ergänzt (Commit `a19a31bb7b7d62c15cf36e4e5e797d867f19a18b`). Zurückgegeben werden Spielerwelt, sechs Kader, synthetic Vintage-Ledger und Cap; der Export selbst führt **keinen** Trade, Cut oder Liga-Writer aus. CP7b Trade-vor-Cut-Control-Paare und tatsächliche Ergebnisse noch in Bearbeitung. PR bleibt Draft, Live-Liga unverändert.

---

## CP7a – Prüfer nach GitHub-Reread validiert und PR synchronisiert

Forschungsbranch `research/1344-cp6i-starter-ceiling-20261119`, Head `cbd64ac64590e4351708dadcc1fb5e6f33087e2e`; [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) um die Benchmark-Designpflicht aktualisiert. Eingespielte Source `benchmark/deadcap_contract_probe.mjs` nochmals via GitHub gelesen: **21/21 reine V8-Vertragsassertions erfolgreich**. Kein Node-/CI-Teststatus, kein vollständiger Offseason-Markt bzw. sechs-Team-Paarweltbeweis. CP7b bleibt nächster Forschungsschritt. Aktive Liga unangetastet.

---

## CP7a – isolierter Rechenkern getestet (26.11.2026)

[Cut-vs-Trade-Rechenkern](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/deadcap_contract_probe.mjs) als Commit `cbd64ac64590e4351708dadcc1fb5e6f33087e2e` auf offenem Draft PR #1576. **21 V8-Assertions** bestanden: Null-Cut, Tenure-Retained-Salary (0/1/2/3+), Salary-Floor, separater Cap-Only-vs-True-Salary-Reprice-Reset, 45er-Slot-/Buyer-Cap-Blockaden, vollständige Folgejahresgarantien, keine stillschweigende günstigere Free-Agent-Neusignierung im Guarantee-Modell, unbekannter Käufer als Nicht-Trade. Nach wie vor **kein** unabhängig ausgeführter Node-/CI-Test oder echter Market Clearing. Ausgangsspezifikation im vorherigen CP7a-Checkpoint. Als nächstes CP7b mit tatsächlicher Buyer-/Seller-Entscheidungsfolge **vor** Zwangscuts. Keine produktive Regeländerung.

---

## CP7a – Benchmark-Testdesign begonnen (26.11.2026)

**Durchgeführter Checkpoint:** [Gemeinsame Benchmark-Spezifikation](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/benchmark/2026-11-26-benchmark-v1.md) im Forschungszweig als Commit `65d4e303c5cb6ea2daffe9cb1a9740c859e3234b`; PR #1576 bleibt Draft. S0 echte Ist-Liga separat vs. P0 (null Dead Cap), P1 (Tenure 50/30/15/5 % Retained Salary mit Reset NUR beim tatsächlichen Salary-Repricing), P2 (mehrjährige garantierte Vertragsvintages). Alle P-Paare unter identischen 45-Slot-/Criticality-/Cap-/Rookie-/Datum-/Owner-Futures. Trade-/Buyer-Markt **vor** dem erzwungenen Cut; keine Trade-Annahme ohne Käufer, finanzierten Vertrag, Asset-Gegenleistung und Owner-Consent. Einzelergebnisse sind kein vergleichendes Ranking; offen: isolierte Unit-Tests und gemeinsamer Event-Ledger/CP7b sowie Mehrjahres-Backtest. Keine aktive Regeländerung.

---

## Benchmark-Designpflicht: Offseason-Trade-Anreiz durch Dead Cap (Nutzerpräzisierung 26.11.2026)

**Designabsicht (Forschungsanforderung, keine neue aktive Regel):** Dead Cap ist vor allem ein gezielter **Cut-vs-Trade-Anreiz in der Offseason**: Wenn das abgebende Team cuttet, muss ein definierter Salary-/Garantieteil bei ihm bleiben; bei einem Trade kann es mehr laufende Cap-Last abgeben. Erfolg wird **nicht** allein an hohen Cut-Strafen, niedriger Cut-Zahl oder der Existenz hypothetischer Trade-Paare gemessen. Gleichwertige Criticality-/Salary-Welt, Datum, 45er Research-Kaderbasis, Cap-Settlement-Timing und dieselben Spieler/Manager/Seeds sind für isolierende Gegenwelten zu verwenden. Status quo in seinem realen 30+5IR+2Taxi-Format **zusätzlich** separat unverändert abbilden; die 45er-Normalisierung darf nicht unbemerkt zur "Ist"-Historie werden.

**Pflicht-Gegenmodelle für den Vergleich:**
- Kontrolle 0: identische Performance-Salary-/Criticality- und Cap-/Roster-Logik **ohne Dead Cap**;
- Kandidat 1: bestehendes bestätigtes **Retained-Salary-/Team-Tenure-Konzept** aus `fantasy-management/league-economy/salary/salary-dead-cap-concept.md`: Dead-Cap-Quoten 50/30/15/5 % nach ununterbrochener League-Season-Tenure; aktives Salary beim Cut um denselben Betrag reduziert (Minimum-Salary-Floor-Ausnahme), **Reset beim nächsten regulären Salary-Zyklus**. NICHT stillschweigend als mehrjährigen Rookie-/Veteranen-Vertrag modellieren;
- Kandidat 2: CP6-Variante mit **mehrjährigen vertraglichen Garantie-Verpflichtungen** (Rookie nach tatsächlicher Fantasy-Draftrunde, Veteranen mit separat festzulegenden Verpflichtungen). Verpflichtung bei Cut und vollständige Übertragung eines bestehenden Vertrags beim Trade – eindeutig getrennt von Konzept 1;
- Optional Kombination/Hybrid nur als **explizite weitere Hypothese**, keine automatische Addition beider Cut-Strafen (Doppelbelastung vermeiden). Dynamic Criticality ist der Salary-Preismechanismus und ein eigenständiger Faktor; Dead Cap ist der Transaktionsanreiz.

**Zentrale vorab zu definierende Auswertung:** Vor dem Cut-/Cap-Settlement, pro *identischem Spieler und Datum*, (A) halten, (B) traden samt **beidseitig akzeptablem** Käufer, vollständiger verbleibender Salary-/Asset-Gegenleistung und Cap-/Roster-Last, (C) cutten mit **behaltenem Dead Cap** und tatsächlichem unowned-FA-/Claim-Preis; jedes Paket muss auf allen fünf Cap-Wirtschaftsachsen legal und in Zukunft finanzierbar sein. Den Angebotsmarkt **vor** Zwangscuts öffnen. Bei nicht existierendem Käufer ausdrücklich "unverkaufbar" markieren statt einen hypothetischen Verkauf zu verbuchen. Vergleich als Paarwelt gleiche Startaufstellung/Marktpreise/Score-Seeds: `trade-against-cut advantage ($)`, Anteil erfolgreich gehandelter statt gecutteter Spieler, beiderseitige angenommene Trades/Angebote, Cap-Entlastung netto, Verfügbarkeit/Preisvorteil des Free-Agent-Käufers nach Cut, Zahl unverkaufbarer Spieler, Dead-Cap-Last und Konzentration, Dauer und Höhe notwendiger Nachbesserungen, Starterindex/Champion-Option/Catch-up, sowie messbarer Commissioner-Aufwand.

**Timing-Hard-Gate:** Prüfen, **ob der Dead-Cap-Reset an der Cap Deadline den Offseason-Cut-Anreiz neutralisiert** (Cut kurz vor Deadline; Debt wird danach gelöscht). Nur reale Zyklusgrenzen benutzen; zusätzliche Cap-Checkpoints dürfen nicht als Salary-Neubewertung/Dead-Cap-Reset gelten. Außerdem prüfen, ob die niedrigeren aktiven Salaries nach Cut Käufer zum Warten auf den Waiver statt zum Trade bewegen und ob die Quote bei langen Tenures 5 % zu schwach ist. Netto-Heldensalary, Buyer Burden und Dead Cap über den gesamten Trade-vs-Cut-Zeithorizont prüfen.

**Benchmark-Entscheidungsregel:** Dead-Cap-/Vertrags-Komplexität wird nur empfohlen, wenn gegenüber der Nullkontrolle **nachweislich tatsächlich durchführbarer, für Käufer und Verkäufer sinnvoller Handel** oder strategische Vorteile entstehen, ohne Aufholbarkeit / wirtschaftliche Stabilität / operative Durchsetzbarkeit unverhältnismäßig zu verschlechtern. Sonst kann die einfachere Lösung gewinnen. Alle sechs geschützten Nordstern-Ziele, realer Ratifikationsstatus und fehlende Markt-/Commissioner-Beobachtungen bleiben sichtbar. Zentraler Status: Issue #1344; keine produktive Code-/Ligakonfiguration, kein neues festgelegtes Vertragsmodell.

---

## Aktueller Forschungsstand 22.11.2026 – CP6r: 45 Slots als Base, bilateraler Spielervertragsmarkt

**Forschungspräferenz des Nutzers:** 45 reguläre Plätze, kein Taxi, volle Salary-Anrechnung aller gehaltenen Spieler, drei Rookie-Garantieklassen (R1–2 100/100/100, R3–4 100/100/50, R5/UDFA 100/50/25), Rookie-Salary 100/125/150. Nicht aktiv oder ligaweit ratifiziert; aktuelle Sleeper-Konfiguration 30 regulär +5 IR +2 Taxi bleibt. IR-Ausgestaltung ausdrücklich offen.

**Neuer reproduzierbarer Pilot:** [CP6r-Forschungsbericht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6r-45slots-trade-strategy-pilot.md), [CP6r-Übersicht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6r-pilot-overview.json), [CP6r-Simulator](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6r_45slot_trade_strategy.mjs). Commit `77c71bd1f97911992fb183fc9c1f59031bdeed1f` auf [Draft PR #1576] (PR-Beschreibung synchronisiert)(https://github.com/Lolindhir/fantasy-app/pull/1576). Zwei synthetische gepaarte Fünfjahreswelten (Seed 11 ohne Schock, Seed 29 mit −20 % Cap-Schock) mit/ohne gegenseitig akzeptierte 1:1-Spielervertragstrades: **4/4 legale Pfade, 120 Teamjahre, 16 bilaterale Proxy-Trades**. Vertragssalary und künftige Zahlungen übertragen, 16/16 geprüfte aktuelle Salary-/Dead-Cap-Invarianten, null neue Retention oder Deal-Dead-Cap. 2031 Team-0-Indizes **+4,92/+5,75** durch Trade-Variante, **Ligaspanne gleichzeitig größer** (27,63→30,12 und 9,31→18,14). Keine realen Angebote oder Zustimmung, kein Gleichgewicht oder Competitive-Balance-Beweis.

**Offene Gates:** realistisch vertrags- und strategieempfindliches 2025–27-Burn-in; echte mehrjährige All-in/Reload/Rebuild/Flex-Entscheidungen inklusive Cuts/Extensions/FA/Picks; Buyer-Side und Trade-gegen-Cut **vor** Settlement, Paket-/Pick-Tausch, mehr Seeds und Stressbedingungen; Sleeper-IR/Transaction/Commissioner-Hard-Failure; unabhängige Node-/CI-Validierung. Forschung bleibt im offenen Issue #1344 und Draft PR #1576. Kein Merge, keine produktive Regeländerung.

---

## Stand 22.11.2026 – CP6q vollständig gerechnet, Forschung noch nicht ratifiziert

**Forschungscheckpoint (auch in Draft PR #1576 synchronisiert):** [CP6q-Bericht](fantasy-management/league-economy/salary/analyses/2026-11-22-cp6q-round-guarantees-capacity.md), [162-Szenarien-Übersicht](fantasy-management/league-economy/salary/analyses/2026-11-22-cp6q-round-guarantees-capacity-overview.json), [reproduzierbarer Simulator](fantasy-management/league-economy/salary/simulation/cp6q_round_guarantees_capacity.mjs), sechs Seed-/Veteranen-Batch-JSONs, Commit `4576ac9ddf510254c89be207f46ada4fea54a829` auf [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576).

**QA:** 162/162 fünfjährige sechs-Team-Pfade legal; 810 Saison-/4.860 Teamjahre; 120 Rookie-Signings pro Pfad (2028–31), exakte simulierte Rookie-Draftrunde zur Salary-/Garantiezuordnung. 40→45 Plätze ersparen 46 erzwungene Draft-Cuts über 54 alternative Paarpfade; 45→50 liefert bei dem derzeitigen Greedy-Agenten in 54/54 Paaren keinerlei wirtschaftlichen oder sportlichen Output-Unterschied. Keine Taxi-/IR-Ausnahme in der Researchwelt, voller Salary/Dead Cap. **45 ohne Taxi führt als Vorschlagskandidat; die Runden-Garantiestaffel bleibt unratifiziert.**

**Grenzen:** V8-Simulationsausführung der Repo-Quelle; Node-CLI/CI unabhängig noch nicht verifiziert. Vertragsjahrgänge 2025/26 und Owners synthetisch, keine echte frühere Risikowahl, kein bilateraler Trade- oder Pick-/Buyer-Markt, keine realen 2027–31 NFL-Daten. Realer Sleeper-IR-Einsatz und der operative Enforcement-/Hard-Failure-Pfad offen. Nordstern/Ratifizierung aller sechs Manager noch ausstehend. **Kein aktives Liga-/Salary-/Frontend-/Workflow-Setting verändert.**

**Weiteres Vorgehen:** kontraktsensitives Multi-Year-Burn-in mit unterschiedlichen All-in/Reload/Rebuild/Flex-Managern und Käufer-/Trade-Markt; unabhängig Node/CI; IR- und Realroster-Migration; danach vollständige sechs-Manager-Abstimmung. Issue #1344 bleibt offen.

---
## Auftrag, Status und Ownership

**Stand 19.11.2026: CP6i – führender 40er-Maximum-/Full-Salary-Kandidat und Einzelteam-Starterobergrenze als Research-Branch dokumentiert.** Forschungsbericht auf Branch `research/1344-cp6i-starter-ceiling-20261119`, Commit `66ce087c15984a0fde75458ec395cdf8a55ab2a5`; keine aktive Regeländerung. Vorherige 30er-/Top20-/f=0,75-Proben sind nur Kontrollwelten, nicht der neue Hauptkandidat. CP6g Mehrjahresvalidierung bleibt offen. 

**Stand 16.11.2026: CP5a–CP5g auf main; CP6a–CP6g. CP6f: eingeschwungene 6er-Zielökonomie vor Migration; CP6g: 30×5 Erstprototyp und 15×5 reproduzierbarer Gegenprototyp ausgeführt, widersprüchliche Shadow-Cap-Resultate wegen unkalibrierter Rookie-/Roster-Modelle; noch keine belastbare Faktorentscheidung. Weiterhin keine aktive Regel-/Salary-Änderung. CP5-Gesamtauswertung (echte mehrjährige/individuelle Team-Tenure-/Salary-Portabilitätsdaten, freiwillige Buyer-/Manager-Reaktionen, gemessener Vollzugsaufwand und integrierter F2+Debt-Regelpfad) sowie CP6-Ligaentscheidung offen. Keine aktive Ligaregel geändert.** Dieses Issue ist das **einzige zentrale operative Design-/Research-Issue** für die noch offene Salary-Cap-/League-Economy-Synthese beider Nutzer-Chats. Die weitere fachliche Diskussion findet im zentralen Chat statt; **dieser Issue-Body** ist der persistente aktuelle Stand und wird bei materiellen Erkenntnissen synchronisiert. Einzelne Analysen und Konzeptpapiere sind Beleg-/Fachquellen, keine konkurrierenden Arbeitsstände.

**Ziel – präzisiert am 14.11.2026:** Wir streben **langfristige wettbewerbliche Chancengleichheit und Durchlässigkeit (Competitive Balance)** an, **nicht** eine künstlich gleiche Verteilung von Ergebnissen, Meisterschaften oder identische Titelwahrscheinlichkeiten in jedem einzelnen Jahr. Jeder Manager soll über einen realistischen, auch nach mehreren Saisons erreichbaren Weg zum Titel verfügen. Ein außergewöhnlicher Rookie-Hit, guter Draft, Trade oder Entwicklung darf erhebliche, auch mehrjährige sportliche Vorteile schaffen; ein einzelner teils glücksabhängiger Draft-Treffer soll aber nicht über sehr viele Jahre nahezu kostenlos einen uneinholbaren oder ständig wachsenden Vorsprung sichern. Überlegene Leistung soll **wirtschaftliche Opportunitätskosten/Cap- und Asset-Entscheidungen** erzeugen. Wiederholte Championships bleiben ausdrücklich legitim, wenn sie durch nachhaltig gutes Management und finanzierbare Kaderentscheidungen ermöglicht werden. Der Cap soll den Wettbewerb langfristig **angreifbar** halten, nicht Ergebnisse nivellieren. Ob zusätzliche direkte Umverteilung nötig und legitim ist, bleibt eine **zu testende offene Designfrage**; kein automatischer Starter-/Starverlust und keine Flo-spezifische Bestrafung sind vorab beschlossen. Auch „bestehende Mechaniken genügen“ bleibt ein zulässiges Ergebnis.

**Arbeitsprinzip:** Beobachtung ≠ Interpretation ≠ Nutzerziel ≠ getestete Hypothese ≠ bestätigte Konzeptentscheidung ≠ aktiv geltende Ligaregel ≠ technische Implementierung. NFL-Nähe ist nur sinnvoll, wenn die Mechanik in der 6-Team-/4-Playoff-Liga das gewünschte Verhalten erzeugt.

## Konsolidierte sechs Designziele – Präzisierung 14.11.2026

**Status:** Von Robert als weitere Präzisierung der bereits mit Marcel geteilten und von Marcel ausdrücklich bejahten **fünf sportlich-ökonomischen Ziele** formuliert. Ziel **6 – operative Umsetzbarkeit** wird von Robert als zusätzliches eigenständiges Designziel gewünscht; Marcels Zustimmung zu Ziel 6 ist noch nicht dokumentiert. Das sind **Bewertungsziele**, keine beschlossenen Mechaniken.

1. **Langfristige wettbewerbliche Chancengleichheit / Aufholbarkeit:** Jeder Manager soll trotz unterschiedlicher Ausgangslage in angemessener Zeit wieder einen realistischen Weg in den Titelwettbewerb haben. Das bedeutet nicht gleiche Erfolgsquote, Spielstärke oder Titelverteilung.
2. **Leistung und Können müssen sich lohnen:** Gute NFL-Einschätzung, Draft-Entscheidungen, Trades, Kaderplanung und wirtschaftliche Entscheidungen dürfen erhebliche, auch mehrjährige Vorteile bringen. Kein Regelwerk soll Kompetenz neutralisieren oder gute Trades pauschal verbieten.
3. **Kein dauerhaft zementierter Vorsprung – unabhängig von seiner Entstehung:** Ein einmalig aus Draftglück, überlegener Analyse, sportlicher Leistung oder einem sehr einseitigen Trade entstandener Vorteil soll **nicht automatisch und ohne wiederkehrende Kosten/Entscheidungen über lange Zeit praktisch uneinholbar bleiben oder sich selbst verstärken**. Der Vorteil darf eine Zeit lang wirken; langfristig muss er **angreifbar, neu zu finanzieren oder erneut zu verdienen** sein. Die Aussage „nicht dauerhaft“ bezieht sich auf den **garantiert fortwirkenden strukturellen Vorteil eines einmaligen Ereignisses**, nicht auf ein Verbot wiederholter Meisterschaften durch laufend gutes Management. Ob und ab wann der Ausgleich ausreicht, ist offen und empirisch zu prüfen.
4. **Wirtschaftlicher Preis sportlicher Überlegenheit:** Wertvolle Spieler und starke Kader sollen reale Salary-/Cap-/Asset-Opportunitätskosten auslösen. Ein günstiger/ungleicher Trade darf stattfinden, aber die daraus entstandene Verstärkung soll nicht ohne weitere wirtschaftliche Auswirkungen dauerhaft akkumuliert werden können. Ein bloßer Managervergleich „wer weiß mehr?“ ist kein Ersatz für Systemdesign.
5. **Strategische Freiheit:** Win-now/Reload/Rebuild/Hybrid sowie unterschiedliche Draft-/Trade-/Entwicklungsstrategien sollen echte, plausible Wege zum Erfolg bleiben. Das System darf nicht eine einzige Strategie erzwingen.
6. **Operative Umsetzbarkeit und verlässlicher Vollzug:** Regeln müssen für sechs Manager verständlich, transparent, reproduzierbar, fair prüfbar und mit vertretbarem Verwaltungsaufwand tatsächlich durchsetzbar sein. Wo Sleeper keine native Kontrolle bietet, sind **Offseason oder wenige definierte Prüftermine** und einfache, robuste Verfahren besonders zu bevorzugen. Ein ganzjähriger Cap bleibt als Vergleichsvariante offen, muss aber seine zusätzliche Wirkung **gegen** laufenden App-/Commissioner-Abgleich, technische Integrationen, Fehler- und Umgehungsrisiko rechtfertigen. Bei vergleichbarer Wirkung ist ein einfacher zuverlässig durchsetzbarer Mechanismus einem komplexeren vorzuziehen.

**Trade-/Wissens-Präzisierung aus Roberts anschließender Klarstellung:** Marcel und Robert wollen nicht die Auswirkungen von Unterschieden im Wissen oder in der Aktivität vollständig wegregeln. Sie wollen **gerade verhindern**, dass wiederholte oder besonders einseitige Trades mit weniger aktiven/erfahrenen Managern zu einem **dauerhaft unaufholbaren Kader- oder Asset-Vorsprung** eines anderen Teams führen. Einzelne ungleiche Trades bleiben möglich und dürfen für guten Managerblick belohnend sein. Das System soll jedoch die *langfristige Kumulation und Persistenz* solcher Vorteile wirtschaftlich begrenzen, ohne im konkreten Einzelfall behaupten zu müssen, ein Manager sei absichtlich ausgenutzt worden, oder jeden Trade manuell nach Marktwert zu genehmigen. Trade-Fairness im Einzelfall, Regeln gegen nachweisbaren Missbrauch und langfristige Competitive Balance sind unterschiedliche Fragen; hierfür ist noch **keine** konkrete Trade-Veto-/Wertkontrolle beschlossen.

**Messbare Leitfragen:** Wie lange wirkt ein einzelner ex ante Vorteil ohne neue Entscheidungen? Wie schnell kann ein gut geführtes schwächeres Team aufholen? Welche fortlaufenden wirtschaftlichen Kosten entstehen bei wertvollen Neuzugängen oder sehr gutem Draft-Ergebnis? In welcher Häufigkeit braucht der Commissioner manuelle Eingriffe? Können Regeln über Sleeper oder klar datierte Checkpoints verlässlich und von allen überprüfbar abgewickelt werden? Wiederholte Siege allein sind kein Scheitern; dauerhafte Dominanz ohne erneut zu tragende Opportunitätskosten wäre ein Warnsignal.



### Ergänzende Forschungshypothese 17.11.2026 – bewirtschaftete Flexibilität und Vertrags-Commitment (kein Ligabeschluss)

**Nutzerpräzisierung (17.11.2026):** Ein Salary-/Dead-Cap-System soll unterschiedliche erfolgreiche Managementstrategien ermöglichen, aber permanentes kostenfreies Auswechseln der gerade besten verfügbaren Spieler wirtschaftlich begrenzen. Ein Spieler-Contract ist ein bewusstes *Commitment*; das ist eine gewünschte Wirkung in der Fantasy-Liga, kein Auftrag, NFL-Vertragsrecht wörtlich zu kopieren. Diese Hypothese operationalisiert die bestehenden Nordstern-Ziele 2, 4, 5 und 6; sie ist **kein siebtes Nordstern-Ziel** und **keine aktive Ligaregel**.

**Zu vergleichende Strategien (keine Gewinnerannahme):**
- **All-in/volle Belegung:** Cap und verfügbare Kaderplätze schon in der Offseason für maximale unmittelbare Kaderqualität ausschöpfen; geringere In-Season-Reaktionsreserve.
- **Flexibilitätsreserve:** bewusst Cap Space und/oder freie reguläre Kaderplätze in die Saison mitnehmen, um auf Verletzungen, Breakouts, Waiver und Trades zu reagieren; dafür zunächst auf andere Kaderqualität/Absicherung verzichten.
- **Vertragsbindung/Entwicklung:** potenziell wertvolle Spieler länger halten, statt kurzfristig auf Waiver zu rotieren; Risiko belegter Plätze und gebundenen Cap Spaces gegen Entwicklungs- und Halteoptionen abwägen.
- **Aktiver Trade-Markt:** teure, entbehrliche Spieler eher anbieten als kostenfrei cutten; tatsächliche Buyer-Salary-, Cap-, Kaderplatz- und Gegenwertbedingungen berücksichtigen. Höhere Cut-Kosten **garantieren nicht** mehr Trades.

**Prüfbare Mechanik-/Nebenwirkungsfragen:**
1. **Cut vs. Trade vs. Hold:** Für dieselben datierten Kader und Salary-Welten Track von Cut-Rate, wiederholtem Cut/Re-Add, Verweildauer, tatsächlich finanzierbaren Gegenparteien und erforderlichen Drop-Bundles; die beobachtete Transaktionszahl allein ist kein Erfolgsmaß.
2. **Cap Space und freie Slots als Optionswert:** Unter identischen Spielerverfügbarkeiten die Opportunitätskosten der Offseason-Reserve und den späteren Nutzen möglicher Startverbesserungen quantifizieren; neben dem Cap die **realen** regulären Roster-, Taxi- und Reserve-Belegungen/Eligibility berücksichtigen.
3. **Kadergröße als eigener Sensitivitätshebel:** Bei gleicher Salary-/Cap-Logik mehrere Rostergrößen auf Flexibilität, Bindung, Replacement-Level, verbliebene spielbare Free Agents, Trade-Liquidität und sinnvolle Waiver-Aufnahmen testen; nicht automatisch größere Kader empfehlen. Flexible freie Slots sind nur nützlich, wenn sportlich sinnvolle Spieler zugänglich bleiben.
4. **Dead-Cap-Höhe und Churn-Härte:** Zu niedrige Kosten können kostenfreies Rotieren begünstigen, zu hohe Cut-Kosten in engen Kadern können Spieler festsetzen, Buyer blockieren und Trades ebenso wie Waiver verhindern. Fairness für weniger aktive Manager nicht durch implizite Trade-Wert-Vetos herstellen.
5. **Permanenter Cap mit Borrowing gesondert prüfen:** Roberts aktuelle Diskussionspräferenz ist ein **maximaler Übertrag bis 50 % des Caps** in das Folgejahr, dort als zusätzliche Dead-Cap-/Debt-Last. Kreditgrenze, Tilgung im Folgejahr, No-Refinance und Interaktion mit spielerbezogenem Cut-Dead-Cap **sind nicht beschlossen**. Mögliches Deebo-/Injury-Pickup-Budget nur als durchgerechnete Transaktion samt 2027er Last prüfen; weder als garantiert legal noch als kostenlos bezeichnen.
6. **Operative Wirkung:** Bei all diesen Varianten notwendige Sleeper-/App-/Commissioner-Eingriffe, Fairness der Prüfzeitpunkte und Ausnahmefälle prüfen, bevor eine operative Empfehlung ausgesprochen wird.

**Bewertung/Abgrenzung:** Strategische Vielfalt und bezahlte Flexibilität sind Wirkungskriterien innerhalb des geschützten Sechs-Ziele-Nordsterns. Pro Szenario die verpflichtenden fünf Finanzierungsachsen (Seller, Buyer, Slots, ligaweite Debt, echte Rückzahlbarkeit) einschließlich ungeklärter Daten ausweisen. Historische Managerreaktionen, freiwillige Tradeangebote und zukünftige Saisonergebnisse nicht als gemessen ausgeben. Die Hypothese gehört in CP5/CP6 und nicht als neue Mechanik in die laufende Saison.

## Quellen und Zuständigkeiten

### Neu vollständig abgeglichene, datierte Inputs (beide **keine** Ligabeschlüsse)
- [Empirische Flo-/Just-Bill-Fallstudie, 05.11.2026](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-05-flo-cap-impact-case-study.md): eingefrorene historische Daten, Quellen, Methodengrenzen.
- [Salary-Cap-Designziele – Gesprächsübergabe, 05.11.2026](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-05-salary-cap-design-goals-handoff.md): neue Nutzerziele, hypothetische Mechaniken und Tests, **kein** Regelstatus.

### Kanonische fachliche Detail- und Synthesequellen (bleiben Eigentümer ihrer Themen)
- [Rookie Contracts / Minimum Salary / Dead Cap](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/salary-dead-cap-concept.md) — Detailregeln und bisherige Konzeptentscheidungen.
- [Performance Salary / Positional Criticality](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/salary-system-redesign-concept.md) — Modellarchitektur, Formel-Kandidaten, Marktvalidierung.
- [Team-Window-Strategie](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/team-window-strategy-concept.md) — Reload / Rebuild / Hybrid und Zukunftsanreize.
- [League-Economy-Synthese](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/league-economy-redesign-options.md) — spätere ligaweite Entscheidungsvorlage, **nicht** zweite Quelle für Detailformeln.
- [League-Format-Notizen](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-context/league-format-notes.md) und dynamisch aktuelles `public/data/League.json`; für Cap-Readmodel das aktuelle `public/data/TeamCapOutlook.json`.
- Historische Simulation [#879](https://github.com/Lolindhir/fantasy-app/issues/879), datierte Analysen in `fantasy-management/league-economy/salary/analyses/`, bestehendes reproduzierbares Simulationsskript `fantasy-management/league-economy/salary/simulation/salary_simulation.py`.

**Keine** neue zweite Konzept- oder TODO-Datei anlegen. Nach explizit geklärten neuen fachlichen Entscheidungen die jeweils zuständige kanonische Markdown-Datei in einem **gesondert autorisierten** Dokumentationsschritt fortschreiben; anschließend die übergeordnete Synthese aktualisieren. Dieses Issue verwaltet Forschungsfortschritt, ersetzt die Fachquellen aber nicht.

## Inventar: Statusmatrix am 05.11.2026

| Sachverhalt | Status | Was daraus folgt |
|---|---|---|
| Derzeitige Liga: 6 Teams, 4 Playoffplätze, hohe Starterdichte, 2 Taxi-Plätze; SalaryRelevantTeamSize = 20 | **Aktiv / dynamisch aus League ableiten** | Kleine Liga und hohes Replacement-Level in allen Tests beachten; keine fixen Team-/Slotzahlen für spätere Saisons voraussetzen. |
| Aktuelles Salary + endogenes Cap aus den 120 teuersten Spielern (Top 20 × 6, Faktor 0,9), Cap-Deadline; kein durchgängiger In-Season-Cap-Vollzug | **Heute aktiv / Baseline A** | Nicht mit vorgeschlagenen neuen Vertragssalaries vermengen. Salary-Neubewertung und laufende Cap-Prüfung strikt unterscheiden. |
| Ziel: Horten ohne wirtschaftliche Gegenkräfte vermeiden, gutes Management belohnen | **Vom Nutzer ausdrücklich formulierter Designwunsch** | Muss in messbare Erfolgskriterien übersetzt werden; kein automatischer Liga-Regelbeschluss. |
| Flo gab am 09.06.2026 acht teure Spieler ab; retrospektiv Top-20-Belegung ca. 543,0 → 433,9 Mio. $, acht Juni-Cuts wurden im anschließenden FA-Draft zu sieben Spielern aufgenommen | **Empirisch, Fallstudie mit rückblickenden Salaries** | Das bisherige Cap verteilt Talent tatsächlich um; keine Aussage über Flo-Motive oder frühere realisierbare Tradegebote. |
| Flo blieb nach Week 8 bei 7–1 und verstärkte sich am 03.11. mit CMC/Goff gegen Spieler und 2027er Picks | **Empirisch, zeitlich getrennte Ereignisse** | Erfolg der Frühphase nicht rückwirkend dem November-Trade zurechnen; die Transaktionen als Stresstest für Cap-/Asset-Kosten verwenden. |
| Flo lag im 05.11.-Cap-Readmodel bei 510.871.937 $ gegenüber 427.653.631 $ Cap (+83.218.306 $) | **Empirischer Snapshot, kein Regelverstoß** | Zeigt potenziellen In-Season-Cap-Effekt; kein rückwirkender Beweis, ob die Transfers unter hypothetischen Regeln möglich gewesen wären. |
| Früherer Chat: 2025er Rookies 30 gedraftet, 20 noch in Liga; 15 wenigstens einmal gecuttet, 6 wiederverpflichtet; viele Veteranen in Startaufstellungen | **Vorläufige historische Chat-Auswertung; zu reproduzieren** | Retention allein misst weder Development-Wert noch verlorene Trade-Assets; Cut/Re-Add, Startwochen und 3Y-Wert gesondert erheben. |
| Rookie Year 1 aus Fantasy-/NFL-Draft (65/35); Year 2 = 125 %, Year 3 = 150 % der festen Year-1-Dollarbasis; Year 4 normales Performance-Salary | **Bestätigte Konzeptentscheidungen, nicht aktive Regeln** | Nicht stillschweigend auf Year 4 verlängern. Zusätzliche Teamoption erst als spätere Alternative prüfen. |
| Erfahrungs-Mindestgehalt und **gleitende** Formel `Salary = max(P, M + 0,50 × P)` ab Year 4 | **Bestätigte Konzeptentscheidung vom 11.10.2026, nicht aktiv** | Das früher vollständig additive Minimum aus dem alten 05.10.-Simulationsbericht ist **überholt**, darf nicht als aktueller Entwurf ausgegeben werden. |
| Dead Cap: Tenure 0/1/2/3+ = 50/30/15/5 %, bei Cut Retained Salary und reduziertes aktives Salary bis zum Floor; Reset beim nächsten Salary Check; keine mehrjährige Altlast | **Bestätigte Konzeptentscheidungen, nicht aktiv** | Nicht ohne Beschluss auf mehrere Jahre verlängern, Cut-Strafe addieren oder Trade-Salary-Retention neu definieren. |
| Dynamische historische, positions-/rangbasierte Criticality; führender Modifier Centered-25, Top-10%-Referenz, Dollar-Exponent k=1,5 | **Architektur konkretisiert / führender Arbeitskandidat, nicht aktiv** | Die 2023–25-Kurven und Snapshot-Werte sind datiert; Modellwirkung und Preisverteilung müssen frisch und auf Liga-Scoring berechnet werden. |
| Reload-first vs. Rebuild-supportive vs. Hybrid | **Offen** | Rebuild nicht als Pflicht oder per Default als unerwünscht setzen. |
| Permanentes Cap, Top-25/30, Teilkosten für Bank, Rookie-Year-4-Option, verhandelbare Salary-Übernahme in Trades, Cap-Rollover | **Offene Hypothesen / Optionen** | Zuerst die einfachen A/B/C-Tests, danach nur bei verbleibender Evidenzlücke weitere Mechaniken prüfen. |
| Technische Cap-Verifikation/Auto-Cut-Modelle und Trade-Simulator | **Eigenständige bestehende Data/App-Arbeiten** | Keine Fachregel auf technische Issues übertragen; spätere Umsetzung nach Ligaentscheid getrennt beauftragen. |

## Präzise Leitfragen und Spannungen (noch **keine** Entscheidungen)

1. **Cap-Wirkung:** Soll das Cap primär zu teurer-Tiefe-Verlust, wiederkehrenden Starterentscheidungen, Trade-Verkäufen oder zur Unmöglichkeit weiterer All-in-Aufrüstung führen? Was ist die minimale ausreichende Wirkung?
2. **Zeitpunkt:** Jährliche Salary-Neuberechnung ≠ jährlicher Cap-Vollzug. Welche Transaktionen wären bei verbindlichem Cap wie als **Gesamtpaket** zu prüfen? Trades, Adds, Waiver, Rookie-/FA-Draft, Taxi, Reserve/IR, Cut und Dead Cap, Validierung von Bestand bereits >Cap und Übergänge.
3. **Konzentration vs. Rebuild:** Flo/Marcel waren 2024/2025 die beiden Playoff-Finalisten, doch Flo hatte 2024 auch sofort produktive Rookies. Wiederholter Erfolg beweist weder fehlende langfristige Kosten noch falsches Design. Weiter prüfen: Kann derselbe teure Kern jährlich erhalten und zusätzlich erweitert werden, oder entsteht realer Zukunftsopportunitätsverlust?
4. **Cap-Größe vs. Salary-Verteilung:** Endogene Cap-Formel bedeutet, dass Top-N-Erhöhung oder gleichförmige Salary-Anhebung die Knappheit **nicht monoton** erhöht. Ergebnisse müssen auf gleicher Bewertungsbasis und mit kalibriertem Cap verglichen werden; „mehr Spieler zählen“ ≠ automatisch „mehr Druck“. Ältere informelle Top-20/25/30-Rechnungen sind explorativ, nicht vollständiger Verhaltens-Backtest.
5. **Rookie-Entwicklung:** Ein Jahr-3-Breakout kann nur kurz günstigen Vertragssurplus bringen; günstige Spieler außerhalb der cap-relevanten Top 20 verursachen bei Slots 21–30 oft nur Rosterplatz- statt Cap-Kosten. Muss Rookie-Halten über Bank/Taxi und Verträge stärker lohnen, ohne frühe Rookie-Cuts künstlich zu verbieten?
6. **Cut vs. Trade:** Flo hätte eventuell vor Juni Spieler gegen Zukunftspicks verkaufen können. Spätere FA-Picks beweisen Nachfrage, **keine ex-ante erzielbaren Tradepreise**. In der Retained-Salary-Logik wird der nach Cut erworbene Spieler für Käufer günstiger; das kann Abwarten statt Trade fördern. Prüfen, ob aktive Käufer das Salary finanzieren können und ob Trades sich tatsächlich rechnen.
7. **Dead-Cap-Konsistenz / Zeitachse:** Der kanonische Entwurf resettet beim nächsten Salary Check (kein Mehrjahres-Dead-Cap). #879 dokumentiert als damalige Tendenz „In-Season-Cuts bei Deadline berücksichtigen, erst prüfen, dann resetten“. Exakte Reihenfolge von Cap-Gültigkeit, Carry-In, alten Dead-Cap-Anteilen und neuen Salaries sowie **Einbeziehung von Dead Cap in Top 20** ist für permanenten Cap zu präzisieren, nicht einseitig zu interpretieren.
8. **Daten-/Modellstände:** 05.10.-Simulation mit additivem Minimum ist historisch, 11.10.-gliding-50%-Modell löst es ab. 2026er Cap-Snapshots wechselten zeitlich (z. B. 428,89 Mio. vs. 427,65 Mio.); jede Rechnung muss Modellversion, Scoring, as-of-Zeit, Roster, Cap-Basis und historische Spielersalaries explizit fixieren. Keine Saldo-/Prognosemischung.
9. **Tanking / sechs Teams:** 4/6 Playoffs, späte Trades, zweiwöchige Playoffs und die bereits bestätigte **gekoppelte** Rookie-Draftorder/Legacy-Anreizlogik dürfen nicht beiläufig verändert werden. Die Reihenfolge 5.→1.01, 6.→1.02, 4.→1.03, 3.→1.04, 2.→1.05, 1.→1.06 bleibt zunächst feste Designabsicht.
10. **Grad der Persistenz:** Kein längerfristiger Cap-Schulden- oder Rolloverzwang beschlossen; erst messen, ob dauerhafte Cap-Disziplin + relevanzgerechte Salaries + vorhandene Rookie-/Dead-Cap-Konzeptbausteine bereits reichen. Wenn ja: **Komplexität nicht erhöhen.**

### Keine verdeckten Widerspruchsauflösungen
- „Flo bleibt stark“ widerspricht **nicht** „jährlicher Cap-Cut hat umverteilt“.
- „Wir wollen mehr wirtschaftliche Langfristigkeit“ ist **noch keine Freigabe**, die bestätigte Ein-Zyklus-Dead-Cap-Logik auf Mehrjahres-Dead-Cap umzustellen.
- „Rookies lohnen sich stärker“ ist **noch keine Freigabe**, den bestätigten Year-4-Übergang zur Performance-Bepreisung zu verlängern.
- Kritikalität und Cap-Vollzug sind **verschiedene, separat isolierbare** Mechaniken. Kandidat C darf nicht zugleich unsichtbar Rookie-/Dead-Cap-Regeln aktivieren.
- Die Qualität einer Ligaökonomie wird **nicht** über möglichst viele Cuts, Tradeanzahl, künstlich schwache Favoriten oder NFL-Regeltreue allein entschieden.

## Neue Zielschärfung und Marcels Franchise-Claim – Gesprächsinput 14.11.2026 (kein Ligabeschluss)

**Provenienz/Status:** Robert hat das präzisierte Ziel der *langfristigen Chancengleichheit statt Ergebnisgleichheit* ausdrücklich als gewünschte Zielformulierung bestätigt und um Aufnahme in das zentrale Repository-Research gebeten. Marcels Vorschlag ist **eine diskutierte Idee**, keine von der Liga beschlossene Mechanik. Keine Änderung von Salary-Formel, Salary-Cap-Fachregel, Rookie-Draftorder, Dead Cap, Live-Rostern, App oder Workflow.

### Normativer Kern

- **Wettbewerb soll dauerhaft offen bleiben:** Ein Team darf durch gute Entscheidungen zeitweise dominieren und auch wiederholt Meister werden. Die strukturelle Wahrscheinlichkeit des dauerhaften Abgehängtseins soll aber nicht aus einem einzelnen glücklichen Rookie-Hit entstehen.
- **Glück wirkt, darf aber nicht kostenlos perpetuiert werden:** Rookies sollen einen wertvollen, zeitlich begrenzten Vertrags-Surplus erzeugen können; ab dem etablierten Year-4-Übergang zur Performance-Salary ist zu prüfen, ob der Wert außergewöhnlicher Spieler ausreichend preiswirksam wird. Diese Aussage **ändert nicht** den bereits bestätigten dreijährigen Rookie-Contract-Entwurf.
- **Zielgröße ist nicht Cuts pro Jahr:** Entscheidend ist der Trade-off zwischen Elite-Spieler halten, verbleibende Starter-/Bench-Qualität, Pick-Assets, Cap-Raum und fortlaufendem Management. NFL-Ähnlichkeit ist funktionales Vorbild für wirtschaftlichen Druck, nicht Selbstzweck.
- **Nicht verwechseln:** Langfristige Chancengleichheit ≠ identische Stärke aller sechs Teams zu jeder Zeit ≠ garantierter Titelwechsel ≠ nachträgliches Entwerten erfolgreicher Drafts.

### Marcels Vorschlag: Franchise-Claim / Schutzrecht (Arbeitshypothese)

- Nach einer Saison könnten schlechter platzierte Teams einen **ungeschützten** Spieler eines besser platzierten Teams auswählen. Beispielpaarungen aus der Diskussion: 6.→1. und 5.→2.; 4.→3. **noch nicht vereinbart**.
- Jeder Manager dürfte zuvor **einen** eigenen Spieler als Franchise-Tag-geschützt deklarieren (Roberts Beispiel: Josh Allen). Alle übrigen Spieler wären nach der noch zu bestimmenden Eligibility grundsätzlich potenzielle Ziele.
- Die Kompensation an das abgebende Team ist **ungeklärt**. Als spontaner Kandidat genannt: ein Spieler des abgebenden Teams wird vom Salary Cap ausgenommen. Andere Kompensationen (z. B. begrenzter Cap Credit oder Pick) sind lediglich zu prüfende Alternativen, **nicht** beschlossen.
- Das unterscheidet sich funktional eher von einem **Expansion-/Dispersal-Draft mit Schutzrecht** als vom klassischen NFL-Franchise-Tag; der Name ist offen.
- Schwierige Designfragen: Welches Team darf wie viele Claims? Welche Platzierung zählt (Playoffs vs. Regular Season)? Wer wählt in welcher Reihenfolge? Können junge sehr wertvolle Spieler mit niedrigem Salary gewählt werden? Wer zahlt das Salary des übernommenen Spielers? Wie zählen Taxi/Reserve, Rookie-Verträge, Dead Cap, bestehende Salary-/Roster-Grenzen und Pick-/Trade-Rechte? Wie werden Mehrfach-Claims und mögliche Kaderüberhänge abgewickelt?
- **Risiken:** Erzwungener Verlust wertvoller, selbst entwickelter Spieler kann Managerleistung zu stark entwerten; ein einzelnes Schutzrecht macht jedes Star-Duo verwundbar; eine **unbegrenzte Cap-Ausnahme** kann zusammen mit der Salary-Entlastung durch einen Abgang zu Überkompensation führen. Ein billig bepreister Superstar schafft dagegen wenig Cap-Entlastung. Ein Claim für den Letzten kann die bewusst gekoppelte Rookie-Draftorder (5.→1.01, 6.→1.02) und Anti-Tanking-Anreize unterlaufen.

### Zwei übergeordnete Vergleichspfade (nicht mit den technischen A/B/C-Szenarien verwechseln)

1. **Wirtschaftliche Competitive Balance:** Dynamisch relevanzgerechte Performance-/Criticality-Salaries, die bereits bestätigten Rookie-/Dead-Cap-Konzeptbausteine in ausdrücklich separaten Tests, und ein durchgehend verbindlich durchsetzbarer Cap. Reicht dies, um außergewöhnliche Draft-Treffer nach ihrem günstigen Einstiegsfenster mit spürbaren Team-Opportunitätskosten zu versehen?
2. **Wirtschaftliche Competitive Balance + Franchise-Claim:** Erst auf derselben wirtschaftlichen Basis testen, welchen *zusätzlichen* Aufholeffekt ein geschützter, ggf. kompensierter Spieler-Claim erzeugt und wie groß dafür der Eingriff in Management-Belohnung, Cap-/Asset-Balance und Tanking-Verhalten ist.

**Messkriterien für spätere CP3–CP5-Forschung:** Aufholbarkeit bzw. realistische Titelchance schwächerer Teams binnen mehrerer Jahre; Dauer/Kosten anhaltender Dominanz; über Jahre kumulierter Vorteil einzelner Rookie-Hits; Wert von Managemententscheidungen; Dynasty-/Rookie-/Trade-/Replacement-Effekte; langfristige Cap-Disziplin; Tanking-Anreize; Erklärbarkeit und Eingriffstiefe. Eine tatsächliche Titelwahrscheinlichkeit folgt **nicht** allein aus dem 2026-Week-9-Salary-Snapshot.

**Forschungsreihenfolge bleibt:** CP3 Markt-/Retention; danach CP4 nur kontrollierte Konzeptvarianten, CP5 systemischer Mehrjahresvergleich. Die Claim-Idee ist **kein neues parallel auszuführendes Work Package** und wird nur dann als zusätzliche Variante simuliert, wenn die wirtschaftlichen Mechaniken als alleinige Lösung nicht hinreichend wirken oder die Liga einen gezielten Vergleich ausdrücklich wünscht. Der zentrale Research-Owner bleibt **Issue #1344**. Das bereits aktive A/B/C(+D)-Szenario-Vokabular bleibt unverändert.

### Rückmeldung Marcel / Durchsetzbarkeit im Ligaalltag (14.11.2026, 09:50–10:01)

**Provenienz:** Marcel bestätigt am 14.11. um 09:50 ausdrücklich, dass er sich mit den fünf vorgeschlagenen Zielen identifiziert. Die nachfolgenden Aussagen werden getrennt nach Marcels Einwand und Roberts Antworten festgehalten, nicht als Ligabeschluss interpretiert.

**Marcel – ungleiche Managerkompetenz und kumulativer Trade-Effekt, durch Robert präzisiert:** Unterschiedliches NFL-Wissen, unterschiedlich hohe Aktivität und persönliche Umstände bleiben reale, nicht gleichstellbare Bedingungen. Marcel verweist als Beispiel auf Trades Dennis→Flo und eine aus seiner Sicht überlegene Football-Einschätzung bei Flo. **Gemeinsame Zielrichtung nach Roberts Klarstellung:** Ein wissensstarker, aktiver Manager soll durch kluge Trades und Drafts profitieren dürfen, **aber nicht einmalig oder wiederholt ohne langfristige wirtschaftliche Gegenkräfte einen praktisch uneinholbaren Vorsprung aufbauen können**, insbesondere wenn die Gegenseite weniger informiert oder aktiv ist. Unfaire Absicht, objektiver Trade-Marktwert und tatsächliche Ausnutzung sind für den konkreten Fall nicht nachgewiesen und werden **nicht** unterstellt. Das System muss strukturelle Aufholbarkeit schaffen, ohne unterschiedliche persönliche Fähigkeiten zu neutralisieren oder konkrete Trades pauschal zu verbieten.

**Robert – wirtschaftlicher Trade-Druck:** Zustimmung zu dieser Grenze; im aktuellen Beispiel bewertet Robert Flos Gegenleistung als zu gering. Als mögliche Gegenkraft nennt er **ganzjährig durchgesetzten Salary Cap**, hält aber den nötigen ständigen App-Abgleich für potenziell komplex. Sein Satz, dass „der Trade so nicht möglich gewesen“ wäre, ist **eine Hypothese zur unveränderten Transaktionskonstellation**, kein bewiesenes rechtliches Replay und keine Behauptung, dass Flo unter anderem Transaktionspaket keinen Trade hätte abschließen können. CP2a/CP2b belegen lediglich relevante zusätzliche marginale Cap-Kosten und die Notwendigkeit atomarer, stichtagsgenauer Compliance-Prüfung.

**Robert – nun ausdrücklich eigenständiges sechstes Designziel: operative Umsetzbarkeit:** Alles, was sich **nicht unmittelbar über Sleeper steuern oder kontrollieren lässt**, soll nach Möglichkeit auf die **Offseason oder wenige eindeutige Checkpoints** beschränkt werden; ein Dead-Cap-System könnte dies ermöglichen. Nicht bloß sekundäre technische Präferenz: Die tatsächliche zuverlässige Kontrolle, Transparenz und der Aufwand für App/Commissioner gehören zur Zielbewertung. **Permanenter Cap ist damit nicht verworfen**; seine zusätzliche Wirkung muss im Vergleich zu praktikablen Checkpoint-Lösungen belegt werden. Marcel hat diesem sechsten Ziel in den hier vorliegenden Nachrichten **noch nicht ausdrücklich zugestimmt**.

**Zusätzliche Evaluationsfragen für CP4/CP5 und die spätere Liga-Vorlage:**
- Welche Vorteile lassen sich mit **wenigen verlässlichen Saison-/Offseason-Stichtagen** erzielen, und welche zusätzlichen Wirkungen hätte ein tatsächlich permanent verbindlicher Cap?
- Welche Ereignisse kann Sleeper selbst zuverlässig erzwingen, was braucht App-/Commissioner-Kontrollen, und welche Mechanik wäre ohne Echtzeit-Validierung überhaupt sauber umsetzbar?
- Wie wird der historische CMC-Trade in einer **vergleichbaren hypothetischen legalen Ausgangslage** bewertet – einschließlich möglichen Cap-Clearings, Gesamtpaket und Gegenleistung, statt „verboten“ als gegeben vorauszusetzen?
- Welche Regeln sind gegen Informations-/Aktivitätsunterschiede robust, ohne individuell schlechtere Trades nachträglich zu neutralisieren oder leistungsstarke Manager zu bestrafen?
- Wie werden operative Kosten (Checkpoints, manuelle Konflikte, Fehlerpotential, Transparenz) neben Competitive Balance, strategischer Tiefe und Tanking gemessen?

**Handoff:** Zentraler Owner bleibt #1344; CP3 Markt-/Retention-Test bleibt der aktuelle Forschungscheckpoint. Kein neuer paralleler Forschungsstrang, keine Änderung aktiver Fachregeln und keine Bewertung konkreter Manager als objektiver Datenbefund.

## Primärer reproduzierbarer A/B/C-Testplan (erste Priorität)

**Konstante Inputs:** Dieselben sechs Team-IDs, archivierten Roster/Transactions/Drafts/Owner- und Spielersalary-Zeitpunkte; historische 2026er Offseason inklusive Flo-Cuts/FA-Draft, relevante Wochen und die Trades vom 03.11.; später andere Teams und Saisons. **Gleiche Datenprovenienz und klar gekennzeichnete hypothetische Regeln.** Verhaltensreaktionen sind Counterfactuals und nicht direkt aus realen Transaktionen beweisbar.

| Szenario | Salary-Preise | Cap-Vollzug | Isolierte Fragestellung |
|---|---|---|---|
| **A – Istzustand** | Heute aktives Salary-Modell | Jährliche Deadline | Welche Umverteilung, Core-Retention, Reload-Kosten und Trading-Optionen existieren bereits? |
| **B – Vollzug isoliert** | Genau dasselbe heutige Salary-Modell | Ganzjährig verbindlich | Welche Änderungen allein durch verpflichtende Cap-Einhaltung entstehen? |
| **C – Zwei-Hebel-Kandidat** | Führendes Criticality-Arbeitsmodell | Ganzjährig verbindlich | Erzeugen relevanzgerechtere Salaries + permanentes Cap die gewünschte Ökonomie ohne zusätzliche Sondermechanik? |
| **D – optionales Kontrollszenario** | Criticality-Arbeitsmodell | Jährliche Deadline | Reine Wirkung der Salary-Formel von der Vollzugswirkung trennen, falls Attribution offen bleibt. |

**Für die erste Reihe keine stillschweigende Einführung neuer Rookie-Contracts, Dead-Cap-Mechaniken, Top-N-Änderungen oder Salary-Retention-Trades**: sonst wird die Wirkung der zwei Hebel nicht isoliert. Bestätigte *Konzeptentscheidungen* werden danach als klar benannte zusätzliche Varianten gegen die A/B/C-Basis getestet.

**Metriken pro Team/Datum/Modell:**
- Top-20-Salary-Belegung, Cap und Differenz; permanenter Cap-Verstoß als **hypothetischer** Transaktions-/Bestandsstatus, nicht rückwirkende Disqualifikation.
- Zahl und **Qualität** der nötigen Entlastungsmaßnahmen: durch welche real verfügbaren Kombinationen aus Cuts/Trades/gleichzeitigen Moves wäre ein legaler Zustand möglich? Nicht schlicht die teuersten Starter automatisch wegnehmen.
- Starterqualität / Replacement-Level / kritische Positionen, Top-End-Kern vs. teuerste Tiefe und tatsächliche/erwartete Wochenpunkte. Fehlende Actual-Records nicht mit 0 gleichsetzen.
- Entwicklung/Retention/Re-Acquisition von Rookie-Jahrgängen, Überlebensdauer von Draft-Picks, tatsächliche Starterrolle, Rookie-Contract-Surplus über Year 1–4.
- Realistisch finanzierbare Trade-Nachfrageseite, potenzieller Verkaufswert vs. Free-Agent-/Waiver-Zugang; konkrete historische Tradeangebote nur wenn belegt, niemals erfunden.
- Käufer-/Verkäuferfenster, wertvolle künftige Picks, zukünftiger Cap-/Contract-Spielraum, Rebuild-/Reload-Zeit, mögliche anhaltende Favoriten.
- Robustheit gegen Verletzungen, Teamanzahl/Starterformat und Salary-Modellversion; Komplexität, Regelerklärbarkeit und Tankingrisiko.

## CP2a – quantitativer A/B/C-Stresstest (05.11.2026)

**Persistiert:** [datierter CP2a-Bericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-05-salary-cap-cp2-abc-stress-test.md); [PR #1358](https://github.com/Lolindhir/fantasy-app/pull/1358) (**erfolgreich nach main gemergt**, CI Selection, Contracts & Publication Safety und Merge Gate erfolgreich; Squash-Commit ae97a7482febad8b974cf4b269670a331685fba1). **Damals war CP2 noch offen (CP2a allein); inzwischen hat CP2b diese Grundlage ergänzt. CP2a ist der abgeschlossene, methodisch begrenzte Modell-/Transaktions-Stresstest; **CP2b wurde am 06.11.2026 abgeschlossen; damaliger Status ist durch den neueren Abschnitt „CP2b“ ersetzt.****

| Parameter / Beobachtung | Ergebnis (einheitlich bepreiste 05.10.-Marktpopulation) |
|---|---|
| A/B aktiv/published Salary, Cap unterschiedlich durch Vollzug | **432.611.104 $** endogenes Vergleichs-Cap; A und B gleich teure Spieler, unterschiedlich nur in hypothetischer Compliance |
| C/D isoliertes Criticality-k=1,5 Salary, Cap separat endogen | **437.083.780 $**; C permanent, D Deadline zur reinen Salary-Effekt-Kontrolle |
| 29.06. theoretisch über Cap | A/B **1/6** vs. C/D **3/6**; bei damals **veröffentlichtem Cap** in CP1 hingegen **0/6**. Preis-/Cap-As-of-Effekt, kein historischer Regelverstoß |
| 09.09. nach FA-Draft | A/B **4/6**, C/D **5/6** über eigenem Preis-/Cap-Modell |
| 05.11. | A/B **5/6**, C/D **5/6**; Flo-Kernquote (Top-10-Salary / Cap): A/B **87,8 %**, C/D **96,8 %** |
| Transaktions-Replay | **54** abgeschlossene Add/Drop-/Trade-Bundles ab 09.09. 20:33:55 UTC; **0** Inkonsistenzen; **6/6** Endroster exakt |
| Cap-erhöhende Bundles bei danach über Cap liegendem Team | B **11**, C **15**; **Exposition**, keine tatsächlich abgelehnten Transaktionen |
| CMC-Trade marginale Top-20-Belastung bei Flo | A/B **+47,65 Mio. $**, C/D **+65,60 Mio. $**; beide Teamseiten atomar berücksichtigt |
| 2026 Free-Agent-Draft | **30** erfolgreiche Picks, davon **17** in salary-relevanter Top-20 des beobachteten 09.09.-Kaders (A und C) |
| 2026 Rookie-Draft (30 Picks) | **30/30** im aktuellen A- und isolierten C-Salary-Preisvektor bei **0 $**; A/B/C belegen **keinen** mehrjährigen Rookie-Contract-Surplus, der separat zu testen bleibt |

**Einordnung / Gegenbefund:** Die beobachteten Roster waren beim Start des Transaktions-Replays bereits 4/6 (B) bzw. 5/6 (C) über dem **retrospektiven** Vergleichs-Cap; ein strikter Nachher-Check würde daher auch bereinigende/neutralen Vorgänge fälschlich als verbotene historische Aktionen darstellen. Ein **legaler hypothetischer Anfangszustand und eine klare Compliance-/Grace-Semantik** sind nötig, bevor man von „verhinderten Trades“ spricht. Die historische Salary-Versionierung (G1), Starter-/Replacement-Kosten und Käuferliquidität (G4/CP3) sind offen. **Keine** Rookie Contracts/Dead Cap/Salary-Floor-Entwürfe wurden aktiviert oder geändert.

## CP2b – historisch exakte Preise, legale Kader und sportliche Opportunitätskosten (06.11.2026)

**Neuester übergeordneter Evidenzstand für den 2026er A/B/C-Basistest:** [CP2b-Fachbericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-06-salary-cap-cp2b-historical-compliance.md), [Dokumentations-PR #1369](https://github.com/Lolindhir/fantasy-app/pull/1369) (**erfolgreich nach `main` gemergt**, alle erforderlichen CI-Prüfungen bestanden; Squash-Commit `cefafd1ecd55d0d97cb790e3c32006c44bea2c89`). **Diese neuere Evidenz präzisiert den älteren CP1-/CP2a-Oktober-Preis-Proxy.** Die ursprünglichen datierten Berichte bleiben für ihre damalige Methode unverändert und werden nicht rückwirkend als historisch exakt umgedeutet.

| Befund | Empirische Aussage / Gegenprüfung |
|---|---|
| Historische Preisbasis **G1 für alle sechs 2026er Testzeitpunkte geklärt** | Jeweils `League.json` **plus damals committetes** `Players.json`; **6/6** historisch veröffentlichte Caps auf Dollar genau aus marktweiten Top 120 wiederhergestellt; **0** fehlende Roster-PlayerIDs. 2024/2025 für Mehrjahres-Outcomes bleiben CP3/5. |
| Tatsächlicher Flo-Cut im Juni | 07.06. **547.568.190 $** → 09.06. **427.729.579 $**, **119.838.611 $** Entlastung. Älterer offengelegter Oktober-Backcast 109.086.072 $ ist **nicht** der exakte Juni-Betrag. |
| Exakte Liga-Snapshots | Teams über Cap: **07.06. 3/6 → 09.06. 2/6 → 29.06. 0/6 → 25.08. 0/6 → 09.09. 4/6 → 05.11. 5/6**. Preis August→September bei **1.242** gemeinsamen Spieler-IDs unverändert; danach änderten sich Daten-/Preisstände. |
| 2026 Free-Agent-Draft / B-C-Vollzug | 30 dokumentierte Picks: isolierter Pick-only-Replay ohne dazwischen liegende Cuts überschreitet unter B **5×** erstmalig die Cap-Grenze aus einem vorher legalen Zustand; C **3×**, wobei C bei Beginn schon 2/6 oberhalb Cap ist. **Keine Behauptung 5/3 historisch illegaler Picks.** Draft-/Grace-/Bundling-Semantik bleibt unbeschlossen. |
| Hypothetische Salary-konforme **Starter-erhalten-Cut-only-Kader** | Im September unter B **7** Nichtstarter-Cuts über alle Teams, C **13**; im November A mit aktuell tatsächlich geltenden Preisen **10**, B mit eingefrorenem September-Salary **8**, C **12**. **Kein Team** muss in dieser Cut-only-Existenzprobe einen am jeweiligen Zeitpunkt **eingetragenen Starter** abgeben. Das sagt nichts über strategisch wertvolle Nichtstarter oder zulässige weitere Kaderaufstellung. |
| Tatsächlicher Wert der gefährdeten Nichtstarter | Beispiele aus 05.11. mit Week-8-NFL-Spielerhistorie: Lamar Jackson **16,02 PPG 2026**, Kirk Cousins **20,58**, Jordan Love **19,36**, Trevor Lawrence **19,66**; verletzte Assets Achane **20,18 PPG 2025**, Hurts **19,07 PPG 2025**. **Kein** Beweis gleicher kurzfristiger/mehrjähriger Ersatzbarkeit. |
| Kaufkräftige Tradegegenseite | Flo hatte acht Juni-Cuts; hypothetisch am **29.06.** könnten andere Teams diese einzeln ohne Gegenabgang je nach Spieler bei **0–3** Teams cap-seitig aufnehmen; für Brock Purdy **0/5**. Reine Kapazität, **keine** dokumentierten Tradeangebote. |
| Preis-Refresh & Vertrag | 2026er Derived Week-00 und Week-08: **956/956** gemeinsame Salaries identisch, doch historisches September→November-`Players.json` weicht bei **385 von 933** gemeinsamen Spielern ab. Konsequenz: Ein permanenter Cap-Vollzug braucht **explizite Salary-Freeze-/Refresh-Semantik**. Die Testannahme B fixiert Septemberpreise für November; ein tatsächlich beobachteter November-Salarystand ist **A as-of**, nicht automatisch B. |

**Validierungsnachtrag:** PR [#1369](https://github.com/Lolindhir/fantasy-app/pull/1369) erfolgreich nach `main` gemergt; neuer [CP2b-Bericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-06-salary-cap-cp2b-historical-compliance.md) und README-Querverweis auf `main` geprüft. **CP2** in der expliziten 2026er Daten-/Mechanik-Interpretation abgeschlossen, **CP3** offen. Die A/B/C-Reihe ersetzt weder bestätigte Rookie-/Dead-Cap-Konzepte noch ist sie eine historische Aussage darüber, welche Trades ein Manager unter anderen Regeln gewählt hätte.

**Methodische Grenze:** Die Cut-only-Kader sind nur konstruktive **Existenzbeispiele** ohne neues Dead Cap, ohne Waiver-/Trade-Reaktionen und ohne garantierte Ersetzbarkeit. Auch die später zu untersuchende Rookie-Contract-Economy wird nicht mit A/B/C verwechselt. **Weder Nachweispflicht teure Starter abzugeben noch ein tatsächlicher historischer Dealpreis ist bislang empirisch belegt.** B wirkt mechanisch auf In-Season-Aufrüstung; zusätzlicher Wert von Criticality, Trade-Markt, Rookie-Persistenz und künftige Titelbalance bleiben offen.

## CP3 – Markt-/Retention-Befunde (14.11.2026; datiert, keine Regelentscheidung)

**Forschungsbericht:** [CP3 – Käufermarkt und Rookie-Retention (14.11.2026)](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp3-market-retention.md), erfolgreich über [PR #1467](https://github.com/Lolindhir/fantasy-app/pull/1467) nach `main` gemergt (Squash `1a9c2b89c05f4945cc11a4f8c3e9cc257b7cda22`). Die bereits abgeschlossenen CP1/CP2-Befunde werden **ergänzt** und nicht rückwirkend geändert.

- **Käufermarkt 29.06.2026, echte historische Salary-Version:** Acht Flo-Cuts × fünf potenzielle Käufer = 40 Paar-Checks; **13/40** ohne eigenen Cut sofort unter Cap. Mit einem beliebigen einzelnen eigenen Cut wären 40/40 mathematisch erreichbar, teils nur durch Aufgabe eines sehr wertvollen Top-10-Salary-Spielers. **Keine realen Tradegebote**.
- **Endogenes gemeinsames Clearing** der acht Kandidaten bei tatsächlichen legalen Käuferrosters (kein doppeltes Ausgeben des Cap-Spielraums): **maximal 4/8** ohne Cuts; **7/8** mit maximal einem Nicht-Top-10-Cut je Käufer; **8/8** mit maximal zwei Nicht-Top-10-Cuts je Käufer. Dies sind **Cap-only-Obergrenzen** ohne Tradepreis, Managerpräferenz und Roster-/Positionsoptimierung. Für Purdy gibt es ohne Cut **0/5** direkte Käufer.
- **Cut vs. Trade/FA:** Alle acht dokumentierten Flo-Cuts am 09.06.; **7/8** wurden später im Free-Agent-Draft gepickt (Purdy 1.03), **kein** Beleg für erzielbare Rookie-/Zukunftspicks zum früheren Cutzeitpunkt. 2026 bis 05.11. sind **121** vollständige Transaktionen, **11** Trades und **66** reine Cut-Events dokumentiert. Das 03.11.-CMC-/Braelon-Allen-Paket umfasst Flos 2027er Rookie-R1/R2 → Dennis, Dennis 2027er Rookie-R3 → Flo; tatsächliche Managerwelt **ohne** permanentes In-Season-Cap.
- **Rookies:** 2025er 30 Picks, am 05.11.2026 **20 ligaweit / 14 beim Draft-Team**, 2026er 30 Picks **27 / 23**. 2025er Jahrgang im 2025er Abschlussroster noch **23** beim Draft-Team. Sämtliche **60** Fantasy-Draft-Spieler mit canonical NFL Draft gematcht, Positionen QB/RB/WR/TE: 2025 NFL-Pool **86**, 2026 **80**. Y1–3-Draftsalary als **nicht aktive** 65/35-Konzeptrechnung reproduziert, **noch kein tatsächlich beobachteter dreijähriger Surplus oder Year-4-Effekt**.
- **Wirkungsgrenzen:** Der aktuelle Markt wurde unter jährlichem Cap-Vollzug beobachtet. Käufer und Verkäufer hätten unter B/C anders disponieren können; 2024er Gründungsdraft nicht mit Rookiejahrgang vergleichen. **Nicht** aus möglichen Cuts oder tatsächlich abgeschlossenen Deals unter A auf Trade-Verhalten, Titelchance oder notwendige Starterabgänge unter B/C schließen.
- **Handoff:** CP3 als **abgegrenzter Evidenzcheckpoint** abgeschlossen; realer Trade-Anreiz und mehrjähriger Rookie-Surplus **inconclusive**. **CP4** nur die bereits bestätigten nicht aktiven Rookie-/Minimum-/Ein-Zyklus-Dead-Cap-Bausteine transparent nachvariieren, wenn die offenen Wirkungsfragen sie erfordern; **CP5** muss zusätzlich wenige verlässliche Cap-Prüfstichtage vs. permanentes Monitoring und Marcels separate Franchise-Claim-Hypothese entlang der **sechs 14.11.-Designziele** prüfen. Keine produktive Regel-/Workflow-/Draftorderänderung.

## CP4 – Vertrags-/Dead-Cap-Mechaniktest (14.11.2026; PR #1472 nach `main` gemergt)

- **Quellen und Regelstatus:** [Fachbericht CP4](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp4-contract-deadcap-sensitivities.md) mit [maschinenlesbaren Kennzahlen](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp4-metrics.json); alle Aussagen sind **isolierte hypothetische Regel-Sensitivitäten**, **keine aktive Salary-/Cap-Regel**. Sechs Ziele laut geschütztem `fantasy-management/league-context/league-philosophy.md` einschließlich operativer Umsetzbarkeit bewertet.
- **Minimum:** In der gefrorenen 05.11.-Population (955 Spieler) erhöht das gleitende Minimum bei **292/483** Veteranen das Salary, aber **keinen** der ursprünglichen ligaweiten Top120 oder der Team-Top20; kein messbarer Cap-/Team-Usage-Effekt. Das überholte voll additive Minimum ist ausdrücklich nicht Modellbasis.
- **Rookie-Kohorten:** 2025 Year2 und 2026 Year1, 30+30, 60/60 Draft-/NFL-IDs aufgelöst. Bei **offengelegtem, nicht historisch belegtem** gemeinsamen Juni-2026-Cap-Proxyanker steigt endogenes 05.11.-Cap **427.653.631 → 431.964.895 $**, fünf Teams weiterhin über Cap. ±10%-Anker-Sensitivität und fehlende 2024-/2025-Cap-Kette dokumentiert. 2024 Startup- und undrafted Cohorts sowie nach-Cut-Contract-Portabilität nicht als entschieden behandelt.
- **Flo Dead Cap:** acht 09.06.-Cuts, 6×Tenure2/15 %, 2×Tenure1/30 %, aus historischen 2024/25-Roster-/Tradequellen rekonstruiert. Nominal hypothetisches Dead Cap **37.551.933 $**. Additive Abrechnung: **31.025.528 $ über Cap**; virtuelle Top20-Slot-Abrechnung: **4.941.734 $ über Cap**. Beide **unbeschlossen** – das Ergebnis hängt elementar von TopN-Semantik ab.
- **Settlement:** Tatsächliche Deadline `2026-06-30T23:59:59Z`. **Reset vor einziger Compliance-Prüfung** kann den alten Dead Cap am Termin neutralisieren, **Prüfung vor Reset** kann ihn belasten. Bereits beschlossen ist nur der Konzept-Reset spätestens am Salary Check; genaue Prüf-/Reset-Atomizität muss vor einer Implementierung explizit geklärt werden.
- **Liquidität:** Vor dem Reset bewirkt hypothetische vollständige aktive Salary-Reduktion nach Cuts Käufer-Paar-Checks **13→16/40**, gemeinsame 0-Cut-Markträumung **4→5/8**. Dies ist **kein** beobachteter FA-Draft nach Reset, und kein Beweis echter Trade-Gebote; Verkäufer- und Käuferanreiz können gegenläufig sein.
- **Scope:** Drei reine Forschungs-/Index-Dateien im PR #1472, 21 QA-Checks bestanden. CP5 soll A, wenige feste Cap-Checks, B, C und optionale bestätigte Verträge nach denselben sechs Designzielen vergleichen; Marcels Franchise-Claim bleibt ein eigener, nicht beschlossener Prüfpfad. **CP4 als abgegrenzter Research-Checkpoint erfolgreich abgeschlossen; CP5/CP6 weiterhin offen.** PR #1472 mit Squash `c7b9f9197527d81d38f08833bb5e5db9cf535f8c` nach `main` gemergt; CI Selection, Core Contracts & Publication Safety und Merge Gate erfolgreich. Alle drei Dateien nach Merge auf `main` geprüft. Kein produktiver Regel- oder Codeeingriff.

## CP5b – legaler Start, verhaltensgebundene Pfadabhängigkeit und Settlement (14.11.2026, Branch-Checkpoint)

**Datierte Forschungsbasis (noch kein Ligabeschluss):** [CP5b-Bericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp5b-legal-start-settlement.md) und [Kennzahlen](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp5b-metrics.json), Forschungscommits `7f628d4244ae973f7fb49ba796fa5e9d213f8b74` und `c05f63531b4c090826bd862cd2b526913a74e3eb`; **[PR #1479](https://github.com/Lolindhir/fantasy-app/pull/1479) erfolgreich nach main gemergt**, Squash-Commit `6aa0e0765c1cc18b894dae168bd3040e88a1c9a4`. CI • Selection, CI Core • Contracts & Publication Safety und CI / Merge Gate **alle erfolgreich**, 12 lokale Datums-/JSON-/Quellverweis-Assertions; drei Dateien auf main nachgelesen. Der geschützte Sechs-Ziele-Nordstern blieb unverändert.

- **Legaler Ausgangspunkt:** Alle sechs Teams sind 25.08.2026 unter dem veröffentlichten 434.255.984-$-Cap. Nach FA-Draft 09.09. vier Teams mit insgesamt 122.567.015 $ positivem Überhang. Hypothetische Starter-erhaltende minimale Cut-only-Bereinigung **7** Spieler (2/1/2/2), aber mit wertvollen Nichtstarter-Assets. Unter zusätzlichem Schutz der je zehn teuersten Spieler sind es **21** Cuts (4/1/6/10). Das ist weder Managerwille noch freie Ersatzbarkeit.
- **Divergentes Event-Replay:** Das ursprüngliche Sep→Nov-2026-Replay rekonstruiert **54** abgeschlossene Events und **6/6** Endroster. Nach legalisiertem Start: **F2 ohne Event-Gate 50** fortsetzbar, **4** inkompatibel; am hypothetischen 05.11.-F3-Check noch **3** Über-Cap-Teams, die in diesem Pfad durch **3 weitere** Nichtstarter-Cuts legalisierbar wären. **B strikt 43** zulässig, **3** aus Cap-Gründen abgelehnt (2 Waiver / 1 Trade), **8** wegen geänderter Historie inkompatibel. **B mit gleichzeitigem, Incoming-schützendem Cut-Szenario 50** zulässig, **4** hypothetische weitere Cuts zu **4** Events und **4** inkompatibel. Keine dieser Abweichungen ist eine tatsächlich bewiesene Managerentscheidung oder Titelwirkung.
- **Zweites Saisonfenster:** 05.11./05.12./21.12.2025 mit originalem `SalaryDollars` und **Top120/6**: alle drei Caps **581.658.383 $**, 3/6 über Cap, unabhängig je Datum 5/5/4 Starter-erhaltende Nichtstarter-Cuts möglich. **Kein** vollständiger legaler 2025er Post-Deadline-Start und deshalb **kein** mehrjähriger kausaler Liga- oder Rookie-Y4-Backtest.
- **Volle Kernschutz-Sensitivität:** Im separat beobachteten 05.11.2026-Kader bei Septemberpreisen lässt Just Bill unter Schutz von Startern + Top10-Salary-Spielern nach allen 17 zulässigen Nichtkern-Cuts noch **9.476.589 $** Überhang. Der Kernschutzfilter ist Proxy, kein reales Verbot.
- **Vollzug:** Die [offiziell dokumentierte Sleeper-API](https://docs.sleeper.com/) ist **read-only**. Waiver-Locks und Commissioner-Trade-Verfahren sind nicht gleichbedeutend mit einer automatischen Cap-Transaktionssperre. Für F2/F3/B fehlen gemessene Commissioner-Minuten, operative Ausnahmequoten und technische Finality-/Race-Proben. Ein Kontrolltermin darf **nicht** verdeckt einen zusätzlichen Salary-/Dead-Cap-Reset erzeugen; die bestätigten Dead-Cap-Konzeptbestandteile bleiben ansonsten unangetastet.
- **Fachurteil:** F2/F3 bleiben ernsthafte niedrig-komplexe Vergleichsvarianten; B zeigt nur mechanisch zusätzliche Grenzen. Keine Sieger-/Punktwertung der sechs Ziele und **keine** Einführung oder Implementierungsfreigabe. Criticality/Contracts/Franchise-Claim getrennt lassen.

**Rest-Gates für CP5/CP6:** 2024/2025 legaler mehrjähriger Start mit Contract-/Pick-Historie, qualitätsbewertete tatsächlich finanzierbare Käufer-/Trade-Alternativen, realer End-to-End-Sleeper-Operator-Test inkl. Waiver/IR/Taxi/Draft sowie klarer Dead-Cap-Reset/Top20-Entscheid. Hand-off: zunächst dokumentierte Zusatzwirkung von F3/B **gegen** tatsächlichen Bedienaufwand und Chancenverbesserung prüfen; CP6 erst danach zur Ligaabstimmung vorbereiten. Bestehendes Issue bleibt **offen**.

## CP5g – F2 gegen additive Dead-Cap-Abrechnung und verbindlicher Fünf-Achsen-Forschungsstandard (15.11.2026)

**Nutzerauftrag:** „ok, mach das“ nach CP5f; CP5g vergleicht F2/Post-Free-Agent-Draft-Settlement mit additiver Cut-Retention im einheitlichen September-2026-Salary-Freeze und führt verbindliche Forschungsangaben zu **Verkäuferentlastung, Käuferlast, realer Roster-Kapazität, Gesamt-Liga-Schuld und Folgetilgungsfähigkeit** ein. **Keine Einführung einer neuen aktiven Ligaregel**, kein automatisches Sleeper-Gate, kein erzwungener Cut, kein Salary-/DeadCap-Reset am zusätzlichen F2-Stichtag.

**Checkpoint A – Research Reporting Standard:** In `fantasy-management/league-economy/AGENTS.md` als bereichseigene **agent-facing Regel** (keine Liga-Policy) eingefügt. Branch `research/1344-cp5g-f2-additive-settlement-20261115`, Commit `48ab4e39e9915319b69f1d95971b47915090ea67`. Die fünf Achsen sind für künftige Salary-/Cap-Systemtests auszuweisen oder begründet als fehlend zu markieren, inklusive einheitlichem Preis-/Roster-Freeze, Szenariotrennung, Käufer-/Seller-Bündel, Deadline-Failure und geschütztem Nordstern. Weitere CP5g-Replay/Report/README-Änderungen offen.

**Bereits errechnete CP5g-Zwischenevidenz:** Unter dem historischen September-2026-Preis-Freeze liegen nach F2s bisher sieben rein hypothetischen Starter-geschützten Cuts bei uniformen zusätzlichen Cut-Retention-Sätzen 5/15/30/50 % **0/1/3/3** Teams erneut über Cap mit additivem Überhang **0 / 4.321.949 / 14.610.829 / 55.087.143 $**. Exakte Cut-only-Minima für vier Teams (ohne neue Schuld) 7/8/11/22 Cuts; diese vier einheitlichen Raten sind **kein** individuell nachgewiesener Team-Tenure-Ledger. Alle sechs September-Kader zeigen in der archivierten RosterSize-30-Welt **0 freie reguläre Plätze** vor weiteren Bewegungen. Ergebnisse stehen unter Quell-/Szenariovorbehalt, Bericht/JSON/QA/CI noch offen.

**Checkpoint B – CP5g-Hard-F2-Quantifizierung:** 41 eigene Quell-/Subsets-/Dollar-/Buyer-Assertions erfolgreich. [Reproduzierbare CP5g-Metriken](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp5g-f2-additive-settlement-20261115/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5g-f2-additive-checkpoint-metrics.json), Commit `f5efd55df12cd0fe10d11b090d377e52a554b298`. Basis: September-2026 original Salary und Sechs-Team-Kader; vollständige Starter-geschützte Cut-only-Subset-Enumeration (4× 2^19/2^20). F2-NoDeadCap 7 Cuts; C-add uniform 5/15/30/50 % 7/8/11/22 hypothetische Cuts. Separat 140 unabhängig geprüfte 7-Cut-Trade-statt-Cut-Paare: unter 5 % nur 3 einzelne beiderseitig cap-/slot-kompatible Fälle; 15/30/50 % unter exakt dem unveränderten 7-Cut-Basispaket keiner. 2026er Juni-Cadd-Altschuld nicht als neue F2-Schuld nochmals gebucht; alternative Juni-Debt-Carry-Exposure ausdrücklich nur unbeschlossene Accounting-Sensitivität.

**Checkpoint C – CP5g-Bericht:** Vollständiger [Bericht zu F2+C-add](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp5g-f2-additive-settlement-20261115/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5g-f2-additive-checkpoint.md) im Forschungsbranch dokumentiert; Commit `235ef6a78a049d4c34fdbaa5ccabf949c91d7f82`. Vergleich enthält neue Fünf-Achsen-Research-Disclosure, 7/8/11/22 hypothetische Cut-only-Clearance, Buyer-Trade-Full-Salary-Marginalkosten, tatsächliche 30er-Roster-Slots, separate Juni-Loan-Vintage-Semantik und den nicht autorisierten Hard-Failure-Policy-Fall. **Checkpoint D – Branch-Abnahme:** Standard, Bericht, JSON und Salary-README vollständig auf Forschungsbranch `research/1344-cp5g-f2-additive-settlement-20261115`; README-Commit `71d8dd5e601f7dd92637c9156cb1a41d8ff308de`, **22 Branch-Konsistenztests bestanden**, im Vergleich zu main genau vier erlaubte Forschungs-/Instruktions-Dateien. Komplette fünf Achsen samt fehlenden echten Käufergeboten, nicht verifiziertem 2027er Salary, fehlender operativer Zeitmessung und Altschuldjahrgang dokumentiert. Berichtsredaktion `4faf91fe530d2aa1c4b483b84407820232c4c97b` nachgezogen; **Nach main gemergt:** [PR #1495](https://github.com/Lolindhir/fantasy-app/pull/1495), Squash `7dc50c7d35b793bedf6d97ffeded26ef6059b235`. CI Selection, Core Contracts & Publication Safety und Merge Gate erfolgreich; **41** Quell-/Berechnungschecks, **22** Branch-Readback-Checks und **23** Post-Merge-Invarianten bestanden. Agent-facing Research-Governance in `fantasy-management/league-economy/AGENTS.md`, Bericht, JSON und README auf `main` vollständig gelesen; keine Liga-Ratifikation, keine Salary-/App-/Data-Source-/Workflow-Änderung. **CP5/CP6 offen.** CP5 und CP6 bleiben offen; die tatsächliche individuelle September-Tenure, freiwillige Käuferentscheidung, realer 2027er Schuldendienst und Operator-Minuten sind nicht belegt.

## CP5f – Käufer-Kapazität, C-add-Schuldverschiebung und Hard Settlement (15.11.2026)

**Nutzerfreigabe:** „ok, dann weiter“ nach CP5e; C-add als bevorzugte harte *Forschungshypothese*, keine aktuelle Ligaregel, keine neue In-Season-Freigabe oder individuellen Verträge. [CP5f-Quellmetriken](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp5f-buyer-settlement-20261115/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5f-buyer-clearing-hard-settlement-metrics.json) auf Branch `research/1344-cp5f-buyer-settlement-20261115`, erster Research-Commit `da2fc10fed459c41cf786d651ab33e43fcfdaea5`. **42 Quell-/Event-/Buyer-/DP-Assertions erfolgreich**. [CP5f-Bericht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp5f-buyer-settlement-20261115/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5f-buyer-clearing-hard-settlement.md) nun ebenfalls auf Branch, Commit `76933579e0b401f235265acb0760aa98bb29d423`. README ergänzt in Commit `32f550178d2da000271ac9e74741fac4445f082e`; **15 Branch-Readback-Konsistenzchecks erfolgreich**, drei Research-Dateien (Report, JSON, README). **Nach main gemergt:** [PR #1494](https://github.com/Lolindhir/fantasy-app/pull/1494), Squash `51ff4f534b5efd140ebe5864e728ef21dd03d0ed`. CI Selection, Core Contracts & Publication Safety und Merge Gate alle **erfolgreich**; 42 Rechen-/Quellenchecks, 15 Branch-Nachleseprüfungen und **18 Post-Merge-Assertions** bestanden. Report, JSON und README auf main nachgelesen, genau drei reine Research-/Dokumentationsdateien. Keine Produktiv-, Workflow-, Salary-Formel- oder Ligaregeländerung. CP5/CP6 weiter offen.

**Neue Reproduktionsbasis:** 07.06.2026 nach 12:00 UTC → 30.06. aus echten `League.json`-Kadern und `Transactions.json`: **15 complete Events** (14 Cuts + Trade am 12.06.), 6/6 Endkader exact, 0 Doppelownership, 2026er Juni-29-Player Salary Freeze. Aktueller normativer RosterSize-Freeze 29 reguläre Plätze; Mighty Giants/Mammoth haben 0, Dennis 2 freie reguläre Plätze; keine impliziten Taxi-/Reserve-Verschiebungen.

**Markt-Härte:** 70 individuelle Seller-Cut-zu-Trade-Käuferpaare, **24** ohne zusätzliche Buyer-Debt wenn Slots ignoriert, nur **15** zugleich mit offenem regulärem Slot; **30** mit bis 5%-Buyer-Debt und Slot. Flo 7/40 No-New-Debt+Slot, ausschließlich Dennis, doch nur zwei Dennis-Slots. Die 8 Flo-Spieler in einer **disjunkten, Käufer-Top20- und Slot-sensitiven** 256-Masken-DP-Optimierung: ohne neue Buyer-Debt bestes Resultat **Flo 20.932.808 $ Rest-Debt**, zwei Trades Darnold/McLaurin→Dennis mit nur **85.432 $** verbleibender Cap-Luft dort. Diese Zwei-Trade-Lösung erfüllt 5%-Grenze, aber beim eingefrorenen Flo-Puffer weder H2 noch H3-Tilgungspflicht ohne weiteren Schritt. Die frühere reine Salary-Variante „dritter Trade zu Mammoth“ setzt einen dort nicht vorhandenen regulären Slot voraus und ist ohne Rosteraktion **nicht** zulässig.

**Schuldverschiebung:** Käufer können sich rechnerisch verschulden, lösen dadurch aber nicht notwendig das Liga-Problem. Mit 5%-Buyer-Limit: Flo H2-rechnerisch durch Purdy→Dennis, Darnold→Timpa **11.325.357 $** Flo-Debt, **23.332.179 $** neue Buyer-Debt (Liga insgesamt **38.726.445 $** statt 35.094.437 $ Baseline). Buyer-Frozen-H2-Verpflichtung erfordert zusätzliche Freiräume bei Dennis **12.492.707 $** und Timpa **22.505.562 $**. Mit 5% Buyer-Limit H3-Flo-Rechenbarkeit: 19.001.136 $ Flo-Debt und 3.725.522 $ neue Timpa-Buyer-Debt. Bei 10%-Buyer-Limit und minimaler Borrowing-Zuteilung zur vollständigen Flo-Entschuldung: **70.676.173 $** neue Buyer-Debt, insgesamt **74.745.082 $** Liga-Debt – >2× der Ausgangslast. Alle Gegenfaktiken ohne Trade-Gegenwert, Managerzustimmung, echte 2027er Preise oder verifizierte Taxi-Umlagerung.

**Offene Gates:** 5 vs. 10 % Gesamtschuldlimit, H2 vs. H3, Year-vintage No-Refinance, harte `failed_unresolved`-Deadline ohne Auto-Cut/Auto-Sanktion; Käufer-Akzeptanz und saubere F2+DeadCap-Post-FA-Settlement-Probe; tatsächliche Operator-Minuten fehlen. Keine Regel-/App-/Workflow-/Data-Source-Änderung, **CP5/CP6 bleiben offen**.

## CP5e – Additive DeadCap-Härte und harte Tilgungsprüfung (15.11.2026)

**User-Priorität:** C-add ist die bevorzugte harte *Forschungshypothese*, keine beschlossene neue Ligaregel; C-virt bleibt Kontrolle. [CP5e-Report](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp5e-additive-amortization-20261115/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5e-additive-debt-amortization.md) auf Branch `research/1344-cp5e-additive-amortization-20261115`, Commit `997a083a71f41ec3f8c112c8566d43df11891788`. Kein Individualvertrag oder zusätzlicher In-Season-Check aktiviert.

**Neue Daten:** 14 historische Cut-only-Events im Juni mit originalen Salaries/Rostern rekonstruiert: 13 mit positiver Netto-Cap-Entlastung, nur Devin Neal (Rang 28) **−547.215 $** netto, weil additive Retention selbst ohne Top-20-Belastung zählt. Flo/Just Bill: 119.838.611 $ Bruttoentlastung, 37.551.933 $ Retention, 82.286.678 $ netto; C-add-Juni-Debt 31.025.528 $. C-add ligaweit 35.094.437 $, C-virt 4.941.734 $. Uniformer Ein-Cut-Stress Flo: 15 % vier, 30 % ein (Lamar Jackson), 50 % null ausreichende Einzel-Cuts; keine echten Spieler-Entscheidungen.

**Neue H2/H3-Grenzen** bei eingefrorenen Juni-2026-Salaries/Cap: Flo/Just Bill H2 Mindesttilgung 2027 15.512.764 $ (Puffer 6.526.405 $, fehlend 8.986.359 $); H3 10.341.843 $ (fehlend 3.815.438 $). 5%-Schuldlimit wäre im Juni um 9.312.729 $ überschritten, 10/15/25 % nicht. Dezember 2025 bleibt ein Nicht-Deadline-Proxy; keine historische 2027er Entwicklung / Managerreaktion / Commissioner-Minuten vorgetäuscht.

**Offen:** harte Tilgungsfrist, Kreditdeckel, Nicht-Refinanzierung fälliger Raten, additiver Nicht-Top20-Fall, tatsächliche Käuferliquidität, Hard-Failure-Settlement ohne Auto-Cuts, Operatorkosten; A/F2/F3/permanent weiter vergleichen. **CP5 und CP6 offen**. Stand: Report und [CP5e-Metriken](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp5e-additive-amortization-20261115/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5e-metrics.json) auf Branch, neuester Commit `42884e6e5c1ca0fd4044461d0842b683987d329e`; 60 automatisierte Reproduktions-Assertions bestanden. README-Index in Commit `b09dd3b3dea6a19b09d08a28331b12c3011d4a79` ergänzt; Research-Dateien und README auf Branch. Report-JSON-Referenz in Commit `c29c39176c28c21f04af9fd6bbb5c459c0451590` nachgezogen. [PR #1493](https://github.com/Lolindhir/fantasy-app/pull/1493) erstellt (nur Teil-Forschung, `Refs #1344`), 18 Branch-Readback-Assertions bestanden. **Nach main gemergt:** [PR #1493](https://github.com/Lolindhir/fantasy-app/pull/1493), Squash `95194cd1a66848613e238a007fe6790043d17578`. CI Selection, Core Contracts & Publication Safety und Merge Gate **alle erfolgreich**; **60** rechnerische Checks, **18** Branch- und **17** Post-Merge-Checks bestanden. Alle drei Research-/README-Dateien direkt aus `main` verifiziert; keine produktive Regel/Salary-Formel/App/Workflow verändert. CP5/CP6 offen.

## CP5d – automatische Jahres-Schuld mit Cut-DeadCap als separater Mechanik-Backtest (15.11.2026)

**Arbeitsfreigabe:** Nutzer autorisiert vollständige CP5d-Forschung und Repository-Dokumentation, **nicht** die Einführung einer Ligaregel. [Forschungsbericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5d-debt-backtest.md), [vollständig maschinenlesbare Einzelmetriken](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5d-metrics.json), Branch `research/1344-cp5d-annual-debt-20261115`, Commit `ca28d3cb9f24b857125c359cf677faa57cae22dc`. Drei reine Research-Dateiänderungen inklusive Salary-README, **20 automatische Quell-/Rechen-/Zeitachsen-Assertions und 20 readback-Assertions erfolgreich.**

**Modellabgrenzung:** A heutige einzelne jährliche Deadline, kein Debt; B `D_next=max(0,Top20(roster)+D_prior−Cap)`; C-add `+sum(june_cut_retained_salary)` oberhalb Top20; C-virt `Top20(aktiver Kader + einzelne DeadCap-Slots)`. Retention zum Cut: **50/30/15/5 %** nach ununterbrochener Team-Tenure, bisher als **nicht aktive** Detailkonzeptentscheidung. Das noch nicht beschlossene CP5d-Settlement prüft den letzten Junikader **vor** Reset, schreibt nur den positiven **Gesamt-Überhang** als neue Debt fest und resettet den alten Cut-DeadCap, ohne ihn doppelt zu prolongieren. Kein neuer jährlicher Salary-Contract und keine individuell manuell registrierten Transfers. Deadline bleibt **vor FA-Draft**, danach keine retroaktive Debt-Erstattung.

**14 tatsächlich archivierte Cut-only-Events** ab 07.06.2026 mittags bis zur 30.06.-Deadline, 4 Packers/8 Just Bill/2 Mammoth, **14/14 Salaries, Tenure und vollständige Transaktions-IDs** aus damaligen Players-/League-/2024/2025-Roster-/Transaktionsquellen rekonstruiert; gesonderter Cooper-Kupp-Cut vor dem 07.06.-Snapshot ausdrücklich **nicht** doppelt gezählt. Für alle **sechs** Junikader gilt historisch Top20 <= Cap **434.255.984 $**; **B mit Null-Altschuld erzeugt daher 0 $**. Isolierte C-Tenure-Retention nominal **54.996.380 $**; **C-add** Debt Packers **4.068.909 $** plus Flo **31.025.528 $** = **35.094.437 $**; **C-virt** nur Flo **4.941.734 $**. Mammoth 7,19 Mio. $ Retention erzeugt wegen Puffer kein C-add Debt und null marginale virtuelle Top20-Belastung. Devin Neal war vor Cut nur Salary-Rang 29, kostet unter additivem Modell dennoch **547.215 $**, unter virtuellem Slot faktisch null: **Top20-/DeadCap-Strafcharakter bleibt bewusst offen.**

**Kreditlimits gegen echte as-of Preis-/Kader-Welten:** 7 unabhängig beobachtete Snapshotpaare 2025 Nov/Dez und 2026 Juni/Aug/Sep/Nov; 2025 mit `SalaryDollars`/Top120÷6, 2026 `Salary`/0,9×Top120÷6. Bei `D_prior=0` greift **weder 25 %- noch 50 %-Limit bei einem Snapshot**. **10 %** bindet 2026 September TimpaBay (2.484.794 $ zu viel) und November Just Bill/Mammoth (zusammen 54.342.282 $). 2026 November Overhang **217.960.296 $** auf fünf Teams, größter Einzel-Überhang **83.218.306 $**; in-season Overhang historisch **kein** Verstoß.

**Keine wahre mehrjährige Simulation:** Eine als **Hypothese** markierte Rechnung koppelt den 21.12.2025-Nicht-Deadline-Overhang (51.349.556 $ insgesamt) an das echte 2026 Juni-Kaderpricing. Völlig eingefrorene 2026-Juni-Salaries/Cap bei gleichbleibendem Roster und ohne neue Cuts ergeben für Flo **5 zukünftige Jahreschecks**, um 31,03 Mio. $ einmalige additive Schuld abzutragen, bzw. **10** mit dem künstlichen 2025er Seed. **2027–2036 weder beobachtet noch prognostiziert.** Wenn eine Mannschaft alljährlich genau `P=Cap` nutzt, bleibt ein zulässiger Kredit `D` ohne echte Tilgungsregel beliebig lange stehen. Schuldendeckel niemals durch `min(D,Limit)` wegschreiben; Überschreitung erfordert noch unbeschlossenes Settlement.

**PR/QA-Abnahme:** [PR #1492](https://github.com/Lolindhir/fantasy-app/pull/1492) **nach main gemergt**, Squash-Commit `e80600f177d71d23192e795291f693fa470c7656`; CI **Selection, Core Contracts & Publication Safety, Merge Gate alle erfolgreich**. Die drei Research-Dateien (Report, JSON, README) danach aus `main` nachgelesen und 11 Check-/Konsistenz-Assertions erneut bestanden. **Kein Deploy**, keine produktive Regelaktivierung.

**Fachlicher Handoff:** Die Zahl der Variablen wird bewusst reduziert: **Top20 beibehalten**, Salary jährlich bewerten, Deadline vor Free-Agent-Draft; isoliert testen (1) echter Schuldentilgungs-/Jahrgangshorizont statt nur 25/50-%-Limit; (2) C-add vs. C-virt inklusive Nicht-Top20-Cut, (3) verlässliche Deadline-Abwicklung, Käuferreaktion und tatsächliche Operator-Zeit. Keine Annahme über echte 2027er League-Caps, Champion-Zugang oder neue Trades. **CP5-Rest/CP6 weiter offen**, geschützter Nordstern und alle aktiven/kanonisch geklärten Regeln unverändert; keine Pipeline, App, Data-Source/Derived, produktiven Workflows oder Secrets angefasst. CI-Impact: reine Fantasy-Management-Research-Doku, keine neuen Tests/Inventory- oder Impact-Routing-Änderungen; Pflicht-CI im Dokumentations-PR nachzuweisen.

## CP5c – Zusatzprüftermine vs. mehrjährige Dead-Cap-Obligations (14.11.2026; Forschungs-Branch)

**Nutzerauftrag:** Weiteren F2/F3/B-Vollzug vergleichen und als *neue Hypothese* prüfen, ob der beim Cut aus ununterbrochener Team-Tenure bestimmte Dead Cap zusätzlich **mehrere zukünftige Salary-Zyklen** belasten sollte. Die bereits geklärten Konzeptentscheidungen „Retained Salary nur bis zum nächsten regulären Salary Check“, „kein Mehrjahres-Dead-Cap“ und die 50/30/15/5-%-Staffel **bleiben bewusst unverändert**; keine neue Ligaregel.

**Datierte Forschungsartefakte:** [CP5c-Fachbericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp5c-windows-deadcap-carryover.md), [CP5c-Metrik-JSON](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp5c-metrics.json), Commit `e5f4adb2120929b0916fcac8bdbff8ae35cb2f31`. Ein Salary-README-Link ergänzt die zwei neuen Research-Files.

**F3 Timing-Gegenprobe, 2026 Sep→Nov, 54 historische Ereignisse ab legalisiertem Sep-Start:**
- F2 ohne weiteren Check: **66,681** positive Über-Cap-Team-Tage, **661,19 Mio.-$-Tage** positiver Überhang, am 05.11. noch drei Teams zusammen **46.512.001 $** über Cap.
- F3 mit extra Check **01.10.**: **31,681 Team-Tage / 352,94 Mio.-$-Tage**; am 05.11. trotzdem zwei Teams mit **38.346.524 $** über Cap. Extra Check **15.10.**: **43,832 Team-Tage / 461,19 Mio.-$-Tage**, gleiche zwei Über-Cap-Teams im November. Die mechanischen Oktober-Cuts (u. a. Kelce/Hill) sind nicht wirtschaftlich plausibilisierte Managerentscheidungen; Oktober-Starter zeitgenau nicht validiert. Beim 15.10.-Check zusätzlich geänderte Event-Kontinuität (**49** fortsetzbar, **5** inkompatibel; F2 **50/4**). **Keine** isoliert kausale Balance-Wirkung oder Operator-Zeit gemessen.
- B hält bei angenommenen Events rechnerisch null Überhang **per Definition**, aber begrenzte bzw. unvereinbare hypothetische Transaktionen und unbewiesenes automatisches Sleeper-Waiver-Gate. Kontrollzeitpunkt und Ratio sind nicht ohne echte finanzierbare Manager-Alternativen und Aufhol-/Bedienkosten als Sieger wertbar.

**Neue Dead-Cap-Laufzeit-Probe mit acht tatsächlich archivierten Flo-Cuts 09.06.2026 (vor 30.06. Deadline):** CP4 als Basis **37.551.933 $** Retained Salary im alten einen Zyklus; zwei Cuts mit Tenure 1 / sechs mit Tenure 2. Bei zum Cut nominal fixierten künftigen *neuen* jährlichen Garantieverpflichtungen ergeben sich **D1: 3/2/1/1-Zyklen → 57.252.104 $** kumuliert und **D2: 4/3/2/1-Zyklen → 94.804.037 $** (davon **37.551.933 $ Z0**, **37.551.933 $ Z1**, **19.700.171 $ Z2**). Eine **D3-Verteilung nur desselben Gesamtbetrags** über 4/3/2/1-Zyklen bleibt dagegen insgesamt bei **37.551.933 $** (Z0 **15.492.602 $**) und verändert *sofortige* Retained-Salary-/Buyer-Kosten. **Die Mechaniken sind ausdrücklich nicht äquivalent!**

**Wesentliche Fachgrenzen:** Team-Tenure ist **keine** reale Vertrags-Restlaufzeit; Rookie-Verträge sind Y1–Y3 fest, Veteranensalaries hingegen jährlich performance-dynamisch. Fixierte, über den nächsten Reset hinaus gezahlte Schuld erzeugt grundsätzlich **neue additive Cap-Kosten**, sofern nicht eine neue komplexe systemweite Mehrjahres-Retained-Salary-Verrechnung eingeführt wird. Zeitachsen-Falle: Z0 der Juni-Cuts hat nur ~drei Wochen bis zum regulären Check; „3 Salary-Zyklen“ sind **nicht** drei volle Vertragsjahre. Die additive vs. virtuelle Top20-Abrechnung und Prüfung-vs.-Reset bleiben unbeschlossen. NFL-Restrukturierung/Bonus-Proration bewusst **nicht** mit dieser Hypothese vermischen.

**QA / CI-Auswirkung:** 14 strukturierte Quellen-/Rechen-/Link-Assertions + 13 Nachlese-/Konsistenzchecks bestanden. Nur 2 neue Research-Dateien und 1 README-Markdown-Link, **keine** produktiven Modelle, Source-/Derived-Verträge, automatischen Writer, Workflow- oder Testmodule. Keine neue CI-Routing-/Test-Inventory-Abhängigkeit; vorhandene Repository-Doku-/Contract-CI ist ausreichend. [PR #1483](https://github.com/Lolindhir/fantasy-app/pull/1483) **erfolgreich nach main gemergt**; Squash-Commit `1fe3e76d6bb571096161f54104e4b89c2eaed260`. CI Selection, CI Core Contracts & Publication Safety, CI / Merge Gate **alle erfolgreich**. Bericht, JSON und README-Link nach dem Merge aus main direkt verifiziert. Keine Secrets oder personenbezogenen Daten neu persistiert.

**Status/Gates:** CP5c als begrenzter mechanischer Forschungsschritt, **CP5 als Ganzes und CP6 bleiben offen**: Pilot/Messung von F2/F3-Commissioner-Arbeit, echte Buyer-/Manager-Verhaltensalternativen, mögliche 2027/28-Aufholwirkung, Veteranen-Contract-Laufzeit und Bonus-/Carry-Semantik. Kein mehrjähriger Vertrag, keine Restrukturierung, keine Änderung am geschützten Sechs-Ziele-Nordstern und keine aktivierte Ligaregel.

## CP6a – Entscheidungsvorlage V0.1 (16.11.2026): Ein-Zyklus-Dead-Cap, additive Anrechnung, beweglicher/permanenter Cap und Grace

**Provenienz und Status:** Im Nutzerchat am 16.11.2026 bestätigt Robert für die **weitere 2027er Konzeptarbeit**: (1) wirtschaftliche Cut-/Dead-Cap-Folgen grundsätzlich bis zum nächsten regulären Salary-Zyklus (keine pauschale Mehrjahres-Altlast), (2) **additive Dead-Cap-Anrechnung außerhalb der cap-relevanten Top 20** als gewünschte Richtung gerade wegen hoher Ersatz-/Churn-Möglichkeiten der Sechs-Team-Liga, (3) **permanenter, möglicherweise zeitlich verschiebbarer/rollierender Cap** als ernsthafter Kandidat gegenüber wenigen Checkpoints, (4) kurze Korrekturfrist und danach ein möglichst einfacher Cut/Rückabwicklungsmechanismus als bevorzugte Vollzugsidee. **Nicht** beschlossen: League-Ratifikation, konkrete Kredit-/Shift-Semantik oder -Limit, Auto-Cut, individuelle Sanktion, Salary-/Dead-Cap-Formeländerung, technischer Einsatz. Die Formulierung „verschiebbar“ wird vorerst ausdrücklich als **mehrdeutig** markiert, nicht als bereits beschlossener Mehrjahres-Schuldenkredit interpretiert.

### Gemeinsamer fachlicher Sockel – Konzeptpräferenz, keine aktiven Regeln
- **Rookies:** 65 % Fantasy-Draft / 35 % gefilterter NFL-Draft; drei Jahre 100/125/150 % des festen Year-1-Dollarankers, ab Year 4 normales Performance-Salary. Gleitendes Veteranenminimum nach bisherigem Konzept; führende separate Criticality-Arbeitsvariante (Centered-25, k=1,5) **nicht stillschweigend mit dem Cap-Vollzug vermischen**.
- **Salary/Cap:** Reguläre **jährliche Neubewertung**; heutiges endogenes Cap aus Top120 und heutiger **Team-Top20-Relevanz** als Vergleichsbasis. Die neu bevorzugte C-add-Lesart ist: `belastetes Cap = Summe der 20 teuersten aktiven Spielersalaries + Summe sämtlicher aktiver Cut-Retentionen + ggf. ausdrücklich erlaubte/gebuchte fällige Pflichten`. Cut-Retention wirkt auch dann, wenn der gecuttete Spieler **nicht** in den Top 20 stand. Keine automatische Top25/30-Umstellung.
- **Cut / Tenure:** bisherige vorgeschlagene 50/30/15/5 % nach ununterbrochenen Seasons; vollständig vom aktiven Spielersalary abziehen, sofern Floor nicht greift; Seller trägt den additiven retained Anteil. Reset **nur** am nächsten regulären Salary Check; ein zusätzlicher Kontrolltermin selbst erzeugt keinen Salary-Refresh und keinen Dead-Cap-Reset.
- **Keine neue Mehrjahres-Schuld durch bloße Begriffswahl:** Deadline-Überhang als zukünftig abzutragender Debt-Vintage und Rolling-/Borrowing-Cap-Credit wären eigenständige optionale Mechaniken. Ein-Zyklus-Cut-Retention entscheidet weder ihre Zulässigkeit noch Laufzeit oder Mindesttilgung.

### Cap-Vollzugsalternativen für die Liga – eng begrenzte Entscheidung
| Pfad | Semantik | Wichtigster Vorteil | Wichtigste Lücke/Kosten |
|---|---|---|---|
| **F2/F3** | Jährliche Deadline + Post-FA-Check (F2), optional zusätzlicher sinnvoll platzierter In-Season-/Pre-Playoff-Check (F3); kein Salary-Refresh | Wenige planbare Prüfungen | Zwischen den Terminen können neue Überhänge entstehen, gerade Waiver und November-Trades |
| **P-hard** | Jedes vollständig verarbeitete ökonomische Gesamtpaket (Add/Drop, Waiver, Trades, Draft und Cut samt C-add) muss Cap- und Roster-konform enden, ggf. mit eng definiertem Korrekturfenster | Unfinanzierte Neuzugänge nicht dauerhaft kostenlos | Ein sauberes präventives/atomisches Sleeper-Gate ist über öffentliche read-only API nicht nachgewiesen; Grace-/Revert-Policy schwierig |
| **P-flex** | Permanenter Cap mit ausdrücklich beschränktem **temporären** Überhang/Shift und festem Settlement; z. B. nur als zu prüfendes Design ein begrenzter Prozentsatz und harte Rückführung, **nicht automatisch mehrjährig** | Flexibilität für Injury-/Trade-/Waiver-Bundles | Kreditgrenze, Fälligkeit, Verrechnung, No-Refinance und Schuldverschiebung können Complexity/Dominanz verstärken; keine Rate beschlossen |

**Interpretation von „verschiebbar“ bleibt eine Entscheidung:** (i) nur **kurze Transaktions-/Korrektur-Grace** ohne Kredit und ohne zukünftigen Cap-Shift, (ii) ein **befristeter** aktuell zulässiger Überhang, der innerhalb desselben Salary-Zyklus bereinigt werden muss, oder (iii) **echtes** Cap-Borrowing aus einem späteren Salary-Zyklus. Diese drei Mechaniken sind nicht gleichzusetzen; (iii) kann dem bestätigten Wunsch nach höchstens einem Cut-Salary-Zyklus wirtschaftlich widersprechen, falls es zu Mehrjahresverpflichtungen führt. Ebenso wäre ein Übertrag **ungenutzten** Cap-Raums ein vierter, symmetrischer Rollover-Hebel und nicht implizit eingeschlossen.

### Korrekturfrist und „Spieler wieder cutten“: entscheidender Regelkonflikt
- **Cut ist nicht Rückabwicklung.** Unter C-add kann der erzwungene Cut eines frisch hinzugefügten Spielers (Tenure0=50 %) trotz Rückkehr zu den früheren aktiven Top20 **neuen additiven Dead Cap** schaffen und den Überhang stehen lassen. Rechenbeispiel: vor Add Top20=420 Mio. $, Cap=430 Mio. $, neuer Spieler 40 Mio. $ ersetzt 20 Mio. $ im Top20 → nach Add 440 Mio. $; nach Cut des Neuzugangs Top20 wieder 420 Mio. $ + 20 Mio. $ neuer Dead Cap = 440 Mio. $; also weiterhin 10 Mio. $ über Cap. Eine **Nichtzustandekommen-/Void-Regel** mit Rückabwicklung ohne Retention wäre eine zusätzliche bewusst zu beschließende Ausnahme und nur bei technologisch/prozessual verifizierter Rückabwickelbarkeit seriös.
- **Waiver/Add:** Erkennung des auslösenden Vorgangs, Benachrichtigung und z. B. 24–48 h als *Kandidatenfenster* – mit der zwingenden Nebenbedingung **vor dem nächsten NFL-/Fantasy-Spiel-Lock**, sonst wäre kurzfristige illegale Nutzung möglich. Danach Rückabwicklung **falls tatsächlich verfügbar** oder definierter manueller Abschluss; keine Behauptung, eine öffentliche Sleeper-API könne Spieler entfernen.
- **Trade:** Ein einzelner Cut löst nicht zuverlässig mehrere Gegenleistungen/Picks und die Käuferlast auf; priorisiert wird vollständige atomare Prüfung beider Teams **vor Verarbeitung**, ggf. Commissioner-Review/Veto/Reverse bei manueller Verifikation. Bereits gewertete Spiele und Picks erfordern gesonderten Finality-Pfad; keine automatische vollständige Undo-Fähigkeit angenommen.
- **Preis-Refresh / Stichtag:** Hier gibt es u. U. **gar keinen** letzten unzulässigen Neuzugang. Manager benötigen eine freiwillige konforme Korrektur, danach eine noch festzulegende transparente Eskalation. Ein zufälliger oder nach Salary höchster Auto-Cut ist **nicht** beschlossen.
- **Hard failure:** Dokumentierter Status `pending_correction` / `failed_unresolved`, transparente Frist und unabhängig von Manager-Sympathie definierter Weg; keine stillschweigende automatische Sanktion oder kostenlose Schuldabschreibung. Offizielle Sleeper-API nur lesen; manuelle Trade-Reversal-/Commissioner-Fähigkeiten separat beachten.

### Kompaktes Beispiel und Nordstern-Abwägung
- C-add nach Cut eines 40-Mio.-$-Spielers mit 20-Mio.-$-Nachrücker: bei Tenure0/50 % = 20 Mio. $ R, **0 Mio. $** Netto-Top20+R-Entlastung; bei Tenure3+/5 % = 2 Mio. $ R, **18 Mio. $** Entlastung; der Käufer eines freien Spielers trägt den reduzierten aktiven Anteil (Floor zu prüfen), der Trade-Käufer dagegen grundsätzlich volle ursprüngliche Salary. **Beispiel ohne Floor und ohne Käufer-Akzeptanz**.
- **Sechs Ziele:** (1) C-add/P könnten Mehrfachakkumulation verteuern, Aufhol-/Titelwirkung ungemessen; (2) billige selbst erarbeitete langfristige Tenure kann Management belohnen, aber auch dominante Cores schützen; (3) Year4-Repricing/Cap soll einmalige Vorteile wieder finanzierungspflichtig machen; (4) C-add belastet sogar Cuts von Spielern außerhalb Top20, daraus entsteht realer Churn-Preis; (5) P-hard kann Injuries, Waiver und einseitige aber legitime Trades einschränken, P-flex erzeugt neue Option aber Borrowing-Risiko; (6) Sleeper-Gate, Deadline/Grace, Taxi-/Reserve-/Roster-Slots und Commissioner-Zeit sind noch nicht abgenommen.

### Verbindliche fünf Forschungsachsen: belegte Basis vs. offene Entscheidung
1. **Seller:** Flo Juni 2026: Brutto Top20-Entlastung 119.838.611 $, hypothetische Cut-Retention 37.551.933 $, damit C-add Nettoentlastung 82.286.678 $ (CP5e; keine aktive Historie). Cut nicht mit Trade gleichsetzen.
2. **Buyer:** CP5f zeigt bei 70 hypothetischen Seller-Cut-zu-Trade-Paaren, wie wenige ohne Buyer-Cut/Schuld und mit regulären Slots gemeinsam möglich sind; freiwillige Preise/gebotene Pick-Gegenleistungen **nicht beobachtet**. P-hard/P-flex Buyer-Auswirkung als kompletter Bundle-Replay **noch nicht modelliert**.
3. **Roster:** Im September-Snapshot sechs Teams mit **null freien regulären Plätzen**; Taxi/Reserve nur nach verifizierter Eligibility und tatsächlicher Belegung. Keine fiktiven Freiräume.
4. **Ligaweite Debt:** CP5d C-add-Hypothese am Juni-Deadline-Stand = 35.094.437 $ Debt, aber **nicht** aktiv; CP5f Buyer-Borrowing konnte aggregierte Debt erhöhen. P-flex-Zukunftsexposure **nicht modelliert**; nicht alten Debt ohne Satzungsentscheidung fortschreiben.
5. **Tilgung:** 2027+ Salary/Caps und echte freiwillige Manager-Reaktionen **unbeobachtet**. 2026 frozen-H2/H3 sind Sensitivitäten, keine Zukunftsprognosen; eine flexible Kapazität ohne echte Frist/No-Refinance ist unzureichend.

### Nächster CP6-Diskussions-Checkpoint, keine produktive Implementierung
1. F2/F3 vs P-hard vs P-flex mit derselben Salary-/Roster-/Cap-Welt und den sechs Zielen tabellarisch als **Entscheidungsvorlage** verständlich formulieren; keine neuen willkürlichen Mechaniken.
2. Für **P-flex** zuerst klären, was „verschiebbar“ bedeutet und ob Borrowing überhaupt gewünscht ist. Falls ja: Kreditdeckel, Fälligkeit **spätestens an welchem Salary Check**, No-Refinance, Rückzahlbarkeit und C-add-Interaktion offen ausweisen.
3. Für **Grace** 24/48h vor Kickoff, Cut-vs-Void, Multi-Team-Trade, unzulässige Waiver-Aufnahme und ein bestehendes Over-Cap-Roster beim jährlichen Reprice als vier Standardfälle entwerfen. Keine automatische Sanktion ohne Liga-Beschluss.
4. Allen sechs Managern eine verständliche Version zur Diskussion geben; 6/6-Nordstern-Ratifizierung (Marcel Ziel6 noch offen) und separate Regelabstimmung organisieren. **CP5-Rest bleibt historisch/operativ offen, muss aber die Fachkonversation nicht blockieren.**

**Belege:** CP5b, CP5d–CP5g im Issue oben, insbesondere [CP5g nach main](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-15-salary-cap-cp5g-f2-additive-checkpoint.md). Dieses CP6a ist **nur ein ausdrücklich als Draft markierter Issue-Entscheidungsstand**. Kanonisches Detail- und Synthesepapier bleiben unverändert, bis die jeweils erforderliche gesonderte Dokumentationsfreigabe vorliegt. Kein Runtime/League-Change.

## CP6b – 16.11.2026: jährlicher Teil-Redraft als Designziel, Criticality verpflichtend in allen Zielvarianten, Cap-Kalibrierung

**Provenienz/Status:** Neue Nutzerpräzisierung vom 16.11.2026 für die fachliche Entwicklung, **keine 6/6-Ratifizierung und keine produktive Regeländerung**. Diese **neuere CP6b-Priorität präzisiert/übersteuert CP6a**, soweit CP6a den Criticality-Kandidaten noch wie eine optionale spätere Erweiterung oder den Post-FA-Check als gleichwertigen Ersatz des Vor-FA-Checks behandeln konnte.

### Ursprünglicher wirtschaftlicher Zweck ist wieder explizit zentral
- Die jährliche **Salary-Neuberechnung und ein verbindlicher Cap-Check vor dem Free-Agent-Draft** sollen bewusst wertvolle Spieler (nicht nur salary-ineffiziente Bank-/QB-Mittelklasse) in einen ligainternen **Teil-Redraft** bringen: Teams behalten ihren Dynasty-Core, müssen aber regelmäßig echte Qualität/Sport-/Asset-Opportunitätskosten freigeben. *Permanent oder mindestens vor dem FA-Draft* ist das vom Nutzer gesetzte Mindestziel; eine **nur nach** dem FA-Draft erfolgende Prüfung ist **kein** Ersatz.
- Die heutige jährliche Cap-Deadline vor dem FA-Draft existiert bereits und bleibt als Designminimum bestehen. Ob **dauerhafter Cap-Vollzug** oder zusätzliche Checkpoints notwendig sind, bleibt offen; die neue Frage ist vielmehr, ob der vor-FA entstehende **qualitativ relevante FA-Pool** im neuen System groß genug ist.
- Historische Quelle CP3: Flo cuttete 09.06.2026 **8** Spieler; **7/8** gingen anschließend im FA-Draft weg (u. a. Brock Purdy 1.03); tatsächliche Nutzung des Teil-Redrafts bestätigt, aber keine hinreichende jährliche Qualität/Umverteilung oder im neuen Preis-/Regelpaket garantierte Nachfrage nachgewiesen. CP2b zeigt: unter vereinfachten Cap-Cut-only-Grenzen waren **0/6 eingetragene Starterverluste zwingend**. Nichtstarter ≠ sportlich irrelevant; Erfolg nicht allein mit Cut-Anzahl messen.

### Kritikalität als fester gemeinsamer Bestandteil jeder gewünschten 2027er Zielvariante
- Robert priorisiert ausdrücklich das **neue leistungs- plus positions-/rangabhängige Criticality-Salary** als nahezu nicht verhandelbares Ziel; pauschal überteuerte mittelmäßige QBs sollen nicht länger die Cap-/Cut-Ökonomie verzerren. Alle CP6-Zielpakete (F2/F3/P-hard/P-flex, Cap-Faktor, Dead Cap, Rookie Contracts) müssen das **gleiche neue Criticality-Modell** als gemeinsamen Preisanker verwenden.
- Führendes, aber technisch/ligaseitig noch nicht ratifiziertes Modell: drei Jahre Player Performance + drei Jahre dynamische rankbasierte Criticality (Centered-25; Top-10%-Referenz; Modifier 0,75–1,25; k=1,5; endogenes Top-120-Cap). Getesteter 02.10.2026-QB-Anteil Top120 **34,9 % alt → 30,4 %** Criticality; **nicht** als zugesagte spätere Top120-Verteilung oder fertig kalibriertes 2027-Preismodell ausgeben.
- Das **alte** Salary ausschließlich in einem getrennten Diagnose-/Attributionskontrolllauf behalten. Keine Head-to-head-Vollzugswertung bei unterschiedlichen Preispopulationen; jede Alternative wird in **derselben** neuen Criticality-Price/Cap/Roster/Salary-Freeze-Welt und in denselben 2026-/historischen League-Bedingungen verglichen.

### Cap-Höhe als eigenständiger Kalibrierungshebel für den jährlichen Teil-Redraft
- Der heutige Faktor ist `f=0,90` auf die marktweiten Top120-Salaries, geteilt durch 6; der Nutzer schlägt ausdrücklich einen **niedrigeren Faktor** als potentiell einfacheren Weg zu mehr wertvollen verpflichtenden Abgaben vor.
- Als **noch nicht gerechnetes Testgitter** vorläufig `f=0,90 / 0,85 / 0,80` **bei identischem Criticality-Preissatz**, jährlich vor FA-Draft, jeweils mit C-add/Ein-Zyklus-Cut-Retention und endogen neu bestimmtem Cap; als Kontrolle die Wirkung bloßer Faktoränderung ohne zusätzliche Preisrevaluation isolieren. Keine der Zahlen ist beschlossen.
- Wichtig: nominal niedrigere Cap-Grenze bedeutet **nicht automatisch** mehr für andere Manager finanzierbare FA-Draft-Zugänge; Käufer-Slots, Roster, nötige Nach-Cut-Folgen, freiwillige Trade-Alternative, 50/30/15/5-Tenure, Floor und gesamtligaweite verfügbare Liquidität beachten. **Kein rein auf Cut-Anzahl optimierter Redraft!**
- Je Szenario **qualitative Pool-Metriken**: Anzahl und Salary-Rang der bis zum Pre-FA-Check freigesetzten Spieler, davon tatsächlich wertvolle Start-/Dynasty-/positionskritische Assets (nicht „Starter am Snapshot“ als alleiniges Kriterium); Top10-/Top20-Core-Opportunitätskosten; tatsächliche/hypothetische FA-Draft-Nachfrage und beidseitige Cap-/Roster-Aufnahmefähigkeit; übertragene/früher behaltene Rookie-Picks/Assets; Starterqualität und Zukunftsoptionen der betroffenen Teams; potenzielle re-add/Washing-Schlupflöcher. **Buyer-Angebote und realisierte zukünftige Ergebnisse unobserved**. Wenige komplette Manager-/Team-Pfade statt erfundene 2027-Dominanzprognosen.

### Tenure-Klarstellung des Nutzers
- **Keine pauschale Behauptung, dass „Long-Time Hold“ direkt belohnt wird:** Gehaltene produktive Spieler **kosten während der gesamten Haltezeit weiterhin volles reguläres Salary**, keine Halteprämie oder steigender Rabatt auf aktives Salary. Die 50/30/15/5-%-Staffel begünstigt ausschließlich den **späteren Cut durch sinkenden Retained-/Dead-Cap-Anteil**; ältere Spieler sind dadurch **leichter**, nicht schwerer, freizusetzen. Eine neue Aufnahme mit Tenure0 ist bei einem raschen Cut dagegen teuer. Ob daraus langfristiger Core-Halt oder geringerer Churn folgt, ist **ambivalent** und muss als Anreiz-/Laufzeitfrage offengelegt werden.
- Der Preis eines Hold/Trade/Cut ist jeweils relativ zu Top20-Nachrücken, Cut-Retention außerhalb Top20, Neubelegung und Nachfrage zu analysieren. Ein günstigerer Exit alter Spieler erzeugt allein noch keine qualitativ starke FA-Draft-Umverteilung.

### Einheitlicher Entscheidungstest (keine produktive Änderung)
1. **Pre-FA-Pflichtcheck:** neuer Criticality-Preis- und Vertragsstand → Top20 + **additive** noch aktive Retention (auch für Cuts von Spielern außerhalb der Top20) → freiwillige cap-legale Cut/Trade-Pakete → freigesetzter FA-Pool → FA-Draft-Zugang/Bündel/Slots prüfen.
2. **Kalibrierung** des `f`-Faktors an gewünschter **Qualität der tatsächlich freigegebenen Spieler**, nicht möglichst vielen Cuts. Frühere Rookie-Contract- und Cut-Retention-Reset-/Compliance-Reihenfolge explizit erhalten/auf Konflikte hinweisen; Pre-FA-Salary-Check ist gegeben, Post-FA-Zusatzcheck darf keinen zweiten Reset erzeugen.
3. Erst **danach** denselben Pre-FA-legalen Start gegen F2/F3/P-hard/P-flex vergleichen, ohne ein zusätzlicher Salary-Refresh/Cap-Kredit/Franchise-Claim heimlich einzuschmuggeln; alle sechs geschützten Nordstern-Ziele und den fünfteiligen Seller/Buyer/Slots/Liga-Debt/Tilgung-Standard ausweisen.
4. Offene Entscheidungen klar benennen: angemessene jährliche Redraft-Qualität/-Intensität, `f`, wie Cap-Compliance nach FA-Draft/During Season aussehen soll, „verschiebbarer“ Cap, Grace/Void statt normalem Dead-Cap-Cut, zusätzliche Sanktionen/Over-Cap-Failure und ggf. Claim als isolierter späterer Vergleich. **Nicht** die sechs Ziele stillschweigend erweitern, sondern den jährlichen Teil-Redraft als konkreten ökonomischen Wirkungsindikator unter Zielen 1–4 evaluieren.

**Handoff CP6:** Der **erste** nächste sachliche Modellvergleich muss **gemeinsames Criticality-Salary × Cap-Faktor × Pre-FA-Settlement/FA-Pool-Qualität** untersuchen. Danach permanente/temporär verschiebbare Compliance vergleichen. CP5-Gesamtaudit bleibt offen, muss die Regeldiskussion nicht blockieren. Unvollständige historische 2027+-Verhalten/Salary bleiben als nicht beobachtet markiert. **Keine neue Liga-Regel, keine automatische Cut- oder Credit-Erlaubnis, keine Salary-/Produktiv-/Workflowänderung.**


## CP6c – 16.11.2026: In-Season-Free-Agent-Liquidität, capfreie Offseason-Planung und Rookie-/FA-Draft-Timing

**Provenienz / Status:** Nutzervorgabe vom 16.11.2026, **2027er Diskussionsgrundlage und kein geltendes Regelsystem / kein 6/6-Beschluss**. Präzisiert CP6b (jährlicher qualitativer Teil-Redraft) um einen **zweiten Markt während der Saison**, und präzisiert CP6a (permanenter Cap) um eine **explizit ausgenommene capfreie Umstrukturierungsphase nach dem jährlichen Salary-Reprice**. Geschützter Liga-Nordstern mit sechs unveränderten Zielen bleibt maßgeblich. Diese Ziele nicht eigenmächtig ändern: In-Season-Free-Agent-Verfügbarkeit ist ein konkreter überprüfbarer **Wirkungsindikator** für Chancengleichheit, Strategievielfalt und wirtschaftliche Konsequenzen.

### Zielbild: Zwei Märkte mit echter Handlungsoption
1. **Offseason-Teil-Redraft:** Nach neuem Performance-/Criticality-Salary und Rookie-Vertragsstufen soll die bindende Cap-Deadline **spätestens vor dem Free-Agent-Draft** wertvolle und nicht nur schlecht bepreiste Quarterback-Backups zur Verfügung stellen. 2026 Flo: 7/8 Juni-Cuts später im FA-Draft ausgewählt, CP3; weder Marktqualität künftiger Jahre noch späterer Buyer-Spielraum garantiert.
2. **In-Season-FA-Liquidität:** Auch nach dem FA-Draft sollen einzelne **sportlich produktive, für die Liga tatsächlich startbare** Spieler (illustrativ Tier 1 und einige Tier 2, nicht bloß Tier 3) *ungebunden* verfügbar sein. Die Entscheidung `teuren Veteranen ohne Tradepartner sofort aufnehmen` soll eine echte **Win-now-/Injury-/Playoff-Option** sein und **Cap-Opportunitätskosten** gegen gehaltene Veteranen, günstigere Tier-2-/Tier-3-Kerne und preiswerte mehrjährige Rookie Contracts abwägbar machen.
3. **Keine garantierte Zwangsverfügbarkeit und kein Ergebnisziel:** Weder eine feste vorgeschriebene Zahl freier Elite-Spieler noch ein Managerzwang, einen Tier-1-Spieler zu cutten, werden beschlossen. Nicht nur `teuer` oder `FA`, sondern unabhängig definierte **sportliche Qualität/Projektion, Gesundheit/Verfügbarkeit, Startbarkeit und Marktaufnahmefähigkeit** beurteilen; Tier 1/2/3 sind vorläufig qualitative Nutzerbezeichnungen, deren objektive Schwellen noch offen sind.

### Unbedingt getrennte Uhren / Phasen
- **T0 – Nach Saisonschluss: neuer regulärer Salary Check/Salary-Zyklus:** Performance- und Positions-Criticality-Rates sowie neue Rookie-Year-Salaries werden anhand fester Regeln und Preis-Freeze neu berechnet. **Sämtliche bisherigen Dead-Cap-Anteile werden genau hier zurückgesetzt.** Keine mehrjährige Retention durch Reset hindurch.
- **T0→T1 – offene *capfreie* Reorganisation:** Roster darf oberhalb des *neu bewerteten* Salary Cap stehen, ohne automatisch illegal zu sein, ohne sofortigen Zwangscut und **ohne Übertrag/Schuldenbuchung in spätere Salary-Jahre** allein für den Zwischenüberhang. Kommunikation/Trades/Management möglich. **Cap-Exemption ist nicht automatisch Cut-Retention-Befreiung:** Ein Cut nach T0 bleibt vorbehaltlich späterer bewusster Entscheidung nach dem gerade gestarteten Zyklus 50/30/15/5 % C-add-pflichtig und belastet die Bilanz am T1-Stichtag; sonst droht kostenloses Offseason-Cut-Washing. Der Zeitpunkt des Retention-Resets und der Verbindlichkeit des Cap werden damit **gegenüber der bisherigen Gleichsetzung „Salary Check / Cap Deadline“ im Detailkonzept als zwei getrennte Ereignisse** vorgeschlagen; bevor Implementierung beginnt, muss die kanonische Dead-Cap-Konzeption bewusst abgeglichen werden.
- **T1 – erste harte Cap-Deadline vor dem FA-Draft:** Mannschaften müssen Top20 + aktive additive Retentions erfüllen, nachdem sie ihre neue Kaderstrategie gebildet haben. Dies gilt **unabhängig von der Wahl** weiterer F2/F3/P-hard/P-flex-Kontrollen. Nur diese Deadline erzeugt die jährliche qualitätsrelevante Freisetzung als Pflichtmechanik.
- **T2 – FA-Draft und danach laufender Cap-Vollzug:** Die Wirksamkeit einer weiteren Bindung unmittelbar nach FA-Draft und bei In-Season-Waivers/Trades ist separat zu entscheiden. Salary/Dead-Cap-Reset **nicht** an jeden Check koppeln. P-flex darf nicht eine pauschale Schuld für den Zeitraum T0→T1 erzeugen.

### Offenes Rookie-/Deadline-Design: echte zwei Wege, kein falsches NFL-Abbild
- **D1 – Deadline *vor* unserem Rookie-Draft:** Vor Rookie-Auswahl Cap legal; ungenaue künftige Rookie-Costs über den vorhandenen **Pick Salary Envelope** darstellen bzw. ein späteres Rookie-Settlement oder eine verbindliche Reserve explizit definieren. Vorteil: frühe Haushaltsdisziplin; Nachteil: tatsächliche Rookie-Verträge hängen vom NFL- und Fantasy-Pick ab, ein harter Draft-Gate ohne reservierte Mittel kann legitime Rookie-Picks blockieren und die spätere FA-Draft-Welt erneut ändern.
- **D2 – erst Rookie-Draft, dann bindende Deadline *vor* FA-Draft:** Exakte Rookie-Salaries stehen gemäß Konzept beim Pick fest; Manager können bewusst Rookie-Wert vs Veteranen-Halten abwägen, **bis zum Deadline-Zeitpunkt bleibt die capfreie Managementphase**. Vorteil: einmalige harte berechnete Compliance und unmittelbar danach fairer FA-Pool; Nachteil: finanzielle Disziplin vor Rookie-Auswahl ist nur **sichtbar/forecasted**, nicht bindend, bis T1.
- **NFL-Kontext als externe Orientierung, nicht Liga-Regel:** 2026 NFL-League-Year + Cap-Compliance am **11.03.2026** vor dem realen NFL Draft **23.–25.04.2026**; gedraftete Rookies werden am Draft-Tag zunächst mit Minimum-List-Salary bilanziert (Art.13 §5(b)(i)), danach Vertrag. NFL Offseason Top-51-Abrechnungsregeln und Cap-Carryover nicht unbemerkt in unsere Top20-/Ein-Zyklus-Welt übertragen. Quellen https://www.nfl.com/news/2026-nfl-free-agency-questions-answers , https://www.nfl.com/news/2026-national-football-league-important-dates , https://overthecap.com/collective-bargaining-agreement/article/13/section/5 .
- **Vorläufiger CP6-Testfavorit D2**, gerade wegen Year-1-Rookie-Salary nach tatsächlich gezogenem Spieler/Pick und Free-Agent-Pool direkt hinter dem bindenden Settlement. Gegen D1 anhand exakt derselben neuen Price-/Roster-Welt prüfen; *kein Beschluss*. Für D1 live Salary Envelope anzeigen, konkrete Abrechnung vor/bei Rookie Draft eindeutig bestimmen.

### Zentrale ökonomische Gegeneffekte ausdrücklich prüfen
- **Vor-FA-Überhang ≠ Folgejahresschuld.** Nach T1 volle harte Kontrolle, sofern nicht separat beschlossenes begrenztes P-flex. Kein Kredit für die capfreie Phase.
- **Alle nahe Cap + niedriges Cap:** Kann den FA-Pool vermehren, aber **Buyer-Liquidität drastisch senken**, so dass attraktive freie Spieler niemand finanzieren kann. Daher freie **Cap-Reserve** bei aktiven Teams, benötigte konkrete Gegen-Cuts/Trades samt C-add, Buyer-Roster-Slots und begrenztes Buying-Window berücksichtigen.
- **Dead Cap kann Redraft blockieren:** C-add und 50 % Tenure0-Cut sind vor T1 bereits harte Restlast; ein teurer Neuzugang im aktuellen Zyklus kann durch Cut in der Top20+Retention-Welt **netto keine** Cap-Entlastung bringen, während Tenure3+ bei 5 % deutlich günstiger ist. Kein implizites `Cuts in freier Phase kosten keinen Dead Cap`. Sonderregel nur explizit, begründet und getestet.
- **Rookie Contracts:** günstige, planbare 3-Jahres-Salaries fördern hohe Flexibilität und potenziell freie Cap für in-season Tier1-Kauf; Trade-off mit Veteran-Halt und Year4-Performance-Repricing. Keine künstlichen Rookie-Pick-Fixpreise vor Auswahl.
- **Free Agent mit großer Salary muss finanzierbar sein:** Cap-Marginalkosten durch Top20-Verschiebung plus mögliche notwendige C-add-Folgekosten; Startbarkeit / Timing / Injury / Waiver Rules gesondert berücksichtigen. Gratis-Retention vom Verkäufer verändert Buyer-Preis; marktwirtschaftlichen Wert statt nur Nominal-Salary beachten.

### Konkrete Erfolgsmetriken (gemeinsame Szenariowelt; keine Werte erfunden)
1. **Offseason: FA-Draft-Pool**: Anzahl, Qualität, Top-Positions-/Fantasy-Ränge der freigesetzten Veteranen; nicht nur Cut-Zahl, keine QB-Mittelklasse-Scheinwerte.
2. **Saison:** pro Woche Anzahl **ungebundener** Tier1/2-Spieler mit nachweisbarer sportlicher Startbarkeit und relevanter Projektion, deren Salary tatsächlich teuer ist, wie viele unmittelbar Cap- und Slot-kompatibel aufgenommen werden können oder einen C-add-Cut erfordern; keine Wochen mit `FA-Wert ausschließlich billig/ungeeignet`.
3. **Win-now-Option**: mindestens theoretisch **1-2 konkrete echte Käuferpfade** pro Saisonfenster mit Cap-Belastung, Roster-Slots und ggf. erlaubtem Cut/Trade statt bloßer nominal freier Stars; kein garantiertes Outcome / kein verordnetes Angebot.
4. **Dynasty/Rookie:** günstige Rookiejahre und Year4-Repricing vs dauerhafter Veteran-Top20-Druck, Erhalt eigener Team-Identität, strategischer Optionalitätswert der Pick-Trades; keine permanente kostenlose Elite-Akkumulation.
5. **Marktgesundheit/Einfluss**: Unterschieden werden hohe Preise vs fälschlich überteuerte QBs, liquide vs unfinanzierbare FA-Pools, reale vs hypothetische Nachfrage; keine erfundenen freiwilligen Reaktionen.

### CP6 Nachfolge-Handoff
- **Neue Basisentscheidung für nächste Modellauswahl:** (A) gemeinsames Criticality+Rookies+Top20+C-add (Ein-Zyklus) (B) verpflichtender vor-FA-Check und **capfreie T0–T1** (C) D1 vs D2 Rookie-Reihenfolge (D) Cap-Faktor 0.90/0.85/0.80 (E) in-season 1/2/3-Tier-Spielerpool und Buyer-Kompatibilität, bevor über P-hard/P-flex und Grace entschieden wird.
- **Achtung:** Historische 2026er FA-/Rookie-Kader stammen aus einem anderen Cap-/Salary-System; 2027 echte Salaries, freiwillige Verhaltensänderungen, genaue künftige Drafttermine und gewählte Cap-Fristen sind nicht nachgewiesen. Empirische Benchmarks liefern **keine** garantie für verfügbare Stars jede Woche.
- Dokumentation **ausschließlich im operativen Issue**; Detailkonzept, League-Philosophy, produktive Sleeper-/App-/Generatorregeln bleiben vor Liga-Ratifizierung unverändert.


## CP6d – Marktvergleich 16.11.2026: Criticality, Cap-Faktor, Draft-Nachfrage und In-Season-FA-Markt

**Status:** Vom Nutzer freigegebene erste *kontrafaktische* CP6-Rechnung, keine Ligaentscheidung, keine produktiven Änderungen. Ziel: jährlicher wertvoller Teil-Redraft **und** im Saisonverlauf finanzierbare sportlich brauchbare Free Agents ohne nötigen Tradepartner.

### Verifizierte Eingabewelt und bewusst gesetzte Grenzen
- **Preis:** 1.268 Spieler aus der archivierten 05.10.2026-Simulation, Spalte 'salary_I_ohne_base_minimum': Criticality Centered-25 / k=1,5 + historische Rookie-Verträge. Für Nichtrookies (Year4+) den später bestätigten gleitenden Floor 'max(P, M + 0.50*P)' ergänzt. Das Minimum basiert hier auf dem *gerundeten 2025er Cap-Proxy* 428,8 Mio. $ und der NFL-Year-Staffel 0,40/0,45/0,50 %. Exakt ermittelter Referenz-Cap bei f=0,90 **440.875.988 $**. Rookie-Kontrakt-Dollaranker aus dem älteren Oktober-Simulator sind **keine voll validierte 2027er Vintage-Rekonstruktion**. **Nicht die verworfene alte voll additive Minimum-Spalte C mit Cap 478,9 Mio. verwenden.** Für den Faktorvergleich bleibt der gesamte Preissatz identisch, keine Repricing-Schleife.
- **Kader:** unverändertes historisches Pre-FA-Roster vom **25.08.2026** aus Git-Commit 539aae40da3de444000805cea3170a116fae129d, bereits **nach** dem 08.07.-Rookie-Draft und **vor** dem 31.08.-FA-Draft (D2-Reihenfolge). 6 Teams, 185 gehaltene IDs, alle **185/185** mittels originalem 2024er Startup-Draft, 2025/2026 Rookie-Drafts und chronologischen abgeschlossenen 2024–25.08.2026-Transaktionen auf denselben Besitzer rückverfolgt. 2026er Tenureverteilung: **40 Jahr0/50 %, 53 Jahr1/30 %, 92 Jahr2/15 %, 0 Jahr3+/5 %**. Dieser Nachweis betrifft Zuordnung und Tenure, **nicht** historische aktiv geltende Dead Caps.
- **Mechanik:** Top20 aktiver Salaries, zusätzlich **alle hypothetisch neu entstehenden C-add-Cut-Retentionen** außerhalb Top20. Greedy Cut-only: stets den aktuell saldierend am stärksten entlastenden Spieler cutten; im Primärfall alle 13 am historischen August-Stichtag eingetragenen Starter schützen, Top20 nach jedem Cut neu berechnen und individuelle 50/30/15-%-Retention als Seller-Last buchen. **Greedy ist kein globales Minimum, kein echter Managerplan**; Starter-Einträge aus Preseason sind kein vollständiger Wertbegriff; nötige Replacement-Adds, frühere Dead-Cap-Vintages, aktuelle Injury/Week-Projektionen und reale Tradegebote nicht mitmodelliert.
- **Tier nur als messbarer Proxy:** Ranking nach archivierter 3Y-Performance je Position. T1 = QB1–6 / RB1–12 / WR1–12 / TE1–6; T2 = QB7–12 / RB13–22 / WR13–30 / TE7–12. Kein ligaweit beschlossener Tierbegriff und **keine** Aussage über konkrete heutige Gesundheit/Startbarkeit.

### Pre-FA-Deadline: Angebot und Kosten des Teil-Redrafts
| f | Hyp. Cap | C-add-Cuts (13 aktuelle Starter geschützt) | Davon T1/T2 | Teams, die mit Cut-only noch über Cap sind | Cuts ohne neuen Dead Cap |
|---|---:|---:|---:|---:|---:|
| **0,90** | **440,9 Mio.** | **12** | **2/4** | **0**, 0 Mio. | 8 |
| **0,875** | **428,6 Mio.** | **19** | **2/5** | **0**, 0 Mio. | hier nicht einzeln geprüft |
| **0,85** | **416,4 Mio.** | **31** | **4/7** | **1**, 5,5 Mio. | 19 |
| **0,80** | **391,9 Mio.** | **53** | **5/8** | **2**, 44,2 Mio. | 34 |

Die hypothetischen **neuen additiven Dead-Cap-Gesamtbelastungen** lauten 43,8 / 64,7 / 91,1 / 141,3 Mio. $ für f=0,90 / 0,875 / 0,85 / 0,80 (keine übernommenen früheren Vintages). Bei f=0,90 wären u. a. Patrick Mahomes, Travis Kelce, Rachaad White, DK Metcalf, Jordan Addison und Jordan Love in der **mechanischen** Cutliste; tatsächliche Manager würden nicht notwendig diese Spieler cutten. 0,85/0,80 können im schützenden Cut-only-Pfad **nicht alle sechs Teams** bereinigen; bei erlaubten Starter-/Elitespieler-Cuts ist vollständiges rechnerisches Clearing möglich, aber dies kann hohe Kern-Qualität vernichten. **Kein Beleg, dass diese Abgaben 2027 tatsächlich erzwungen werden.**

### FA-Draft-Replay (30 tatsächlich 2026 gewählte Spieler, kein echtes kontrafaktisches Marktverhalten)
- Originale 30/30 2026er FA-Draft-PlayerIDs sind in der Price Population vorhanden und waren im 25.08.-Roster ungebunden. Im reinen Cap-Gate-**Gedankenexperiment** (chronologische alte Picks, fehlgeschlagener Pick ausgelassen, keine weiteren Kompensationscuts) wären **18/30** Picks bei 0,90, **12/30** bei 0,875, **12/30** bei 0,85 und **5/30** bei 0,80 finanzierbar gewesen – letzteres bei 0,85/0,80 schon aus vorher *nicht vollständig* Cap-konformem Ausgangsbild. Die **realen** 2026er Picks waren nicht illegal und sind keine Prognose der neuen Managerentscheidungen.
- Würden alle 30 tatsächlichen Pick-Zugänge ohne Ausgleich auf die hipothetischen 0,90er bereinigten Roster gesetzt, entstünde **130,8 Mio. $** aggregierter Cap-Überhang. FA-Picks benötigen deshalb ein klar definiertes **Draft-/Roster-Korrekturbündel und Post-FA-Settlement** oder eine echte atomische Cap-Abwicklung, *nicht* einen Salary-/Dead-Cap-Reset.
- **Real belegte Kaderplätze:** In der August-Welt stehen nach Taxi/Reserve-Abzug reguläre Belegungen von **31/28/25/34/32/29** gegenüber dem regulären 30er Soll; im echten September-Snapshot sind **alle sechs 30/30**. Isoliert cap-finanzierbare Picks sind ohne regulären Slot oder kompensierenden Cut **nicht** unmittelbar legal. Der Replay ist nur Salary-Stresstest, kein verifizierter vollständiger Slot-/Cut-/Draft-Gate.

### In-Season: Angebot ≠ finanzierbarer Buyer-Markt
- Bei **tatsächlich historisch gehaltenen Rostern** (nicht hypothetisch nachgebauten Teams), aber unter **demselben Oktober-Preis- und 3Y-Tier-Proxy**, frei: **25.08. T1/T2 = 3/8 (9 mit Preis >=15 Mio.)**; **09.09. T1/T2 = 4/3 (5 >=15 Mio.)**; **16.11. T1/T2 = 3/2 (4 >=15 Mio.)**. Die vier jüngsten reinen *Proxy-Beispiele*: Tyreek Hill 28,2 Mio., Alvin Kamara 24,9 Mio., Joe Mixon 17,0 Mio., David Njoku 15,3 Mio. **Aktuelle Verfügbarkeit/gesundheitliche Startbarkeit/Produktivität dieser Spieler ist damit ausdrücklich nicht belegt**.
- Würden die realen 2026er September-Roster *nachträglich* mit f=0,90 und neuer Criticality bewertet, lägen 5/6 rechnerisch über Cap (in Summe 211,1 Mio.), im aktuellen November-Snapshot 5/6 (307,3 Mio.). **Kein tatsächlicher Verstoß:** neue Regeln waren nicht aktiv und Manager haben nicht unter ihnen gehandelt. Zudem sind zum September-/November-Snapshot alle regulären 30er Slots voll. Einen marktreifen, tatsächlich legalen In-Season-Sofortkauf konnten diese Daten **nicht beweisen**.
- Die mechanisch 0,90-cadd freigesetzten Spieler würden die qualitätsrelevante Angebotsschicht verbreitern, aber **selbst der bloße Replay aller realen FA-Picks würde den Cap wieder verletzen**. Eventuelle reduzierte aktive Salary-Portabilität nach Cut (vorbehaltlich Floor) ist ein möglicher Käufer-Anreiz, dessen Seller-Gegenbuchung erhalten bleibt; Manager-Akzeptanz und die komplette Buyer-Cut-/Slot-Kombination sind unbekannt.

### CP6-Bewertung und Empfehlung
1. **Korridor für nächste Fachfassung:** 0,90 als gegenwärtig ökonomisch/operativ sicherere Vergleichsbasis; **0,875** als ernsthafter vorsichtiger Verschärfungstest. 0,85 und insbesondere 0,80 **noch nicht favorisieren**, weil der zusätzliche Cut-Druck mit C-add viel mehr wertvolle Banktiefe und schließlich Kernspieler kosten oder rechnerisch unvollständig bleiben kann, und Buyer-Finanzierbarkeit gleichzeitig schlechter wird. Keine dieser Raten beschlossen.
2. **Feste Prozessfolge (führender CP6-Draft, nicht aktiv):** Salary-Neubewertung und alter Dead-Cap-Reset am Anfang der Offseason; **capfreie** Planung ohne Folgejahrs-Kreditschuld (Cuts im neuen Zyklus dennoch cadd-pflichtig); Rookie Draft mit Live Salary; **harte Cap-Deadline vor FA-Draft**; FA-Draft mit bewussten Nach-Draft-Kader-/Cap-Bundles und eigener verbindlicher Settlement-Deadline; danach separate P-hard/P-flex/Grace-Entscheidung ohne erneuten Salary Reset.
3. **Doppelte Zielgröße für FA-Markt:** (a) wenige tatsächlich sportlich startbare, gesunde und hochpreisige freie T1/T2-Veteranen im Jahresverlauf, (b) mindestens realistische finanzierte Win-now-Add/Drop-Pfade mit Cap-/Roster-Puffer und Dead-Cap-Gegenbuchung. Alle sechs Nordstern-Ziele bewerten. Eine *niedrigere* Cap-Grenze erzeugt nicht automatisch Käufer oder ein erfolgreiches Markt-Clearing.
4. **Quellen-/Fünf-Achsen-Grenze:** Verkäufer-Cut-Relief nur mechanisch; Käufer-Zusatzkosten/Off-sets unbewiesene Managerentscheidung; August-/September-Roster-Slots unterschiedlich; ligaweite neue Dead-Cap-Liabilities siehe oben; keine Mehrjahres-Amortisation oder Zukunfts-Vintage, da Ein-Zyklus-Retention beim nächsten Reprice endet. 2027 echte Price/Rookie/Vintage-/Manager-/Health-Inputs fehlen. **CP6-Ligabeschluss noch offen.**

**Belege:** simulations-players.csv (05.10.), salary-dead-cap-concept.md §11 (11.10.-Gleitminimum), League.json (Aug 25 Commit oben / Sep 09 Commit b40956172a704ff616008d7835f527b86f128063 / aktuelles main), Drafts-2024/25/26 und Transactions-2024/25/26, CP2b/CP3/CP5g in diesem Issue. **Keine neuen Live-Ligaregeln, App-Modelle oder produktiven Daten verändert.**

## CP6e – 16.11.2026: virtueller Expansionstest für vier zusätzliche Veteranenteams (10-Team-Referenz)

**Auftrag/Provenienz:** Nutzer möchte ausdrücklich aggressivere Cap-Faktoren testen und schlägt eine stärkere Zielbild-Probe vor: Bei weiterhin **sechs echten Teams** soll der Free-Agent-Markt idealerweise so tief und sportlich relevant sein, dass **vier zusätzliche hypothetische Teams ohne Expansion Draft oder geschützte Spielerabgabe** aus Veteranen annähernd zu bestehenden Teams aufschließen könnten; später allenfalls 1–2 zusätzliche Rookie-Picks als gesondertes nicht modelliertes Gedankenspiel. Auch sechs zusätzliche virtuelle Teams (=12-Team-Referenz) untersucht. **Keine reale Liga-Expansion, kein neues 7. geschütztes Nordsternziel, keine aktiven Regeln geändert.** Dies ist ein **Wirkungs-/Stress-Test** unter sechs bestehenden Nordsternzielen, keine Garantie gleicher Teams oder nötige Entscheidung.

### Gemeinsame Ausgangswelt
- Gleicher 1.268-Player-Preis-/Performance-Proxy wie CP6d: 05.10.2026 Criticality/k1,5/Centered25-Vektor ('salary_I_ohne_base_minimum') plus **gleitendes** Minimum `max(P, M+0.5P)` für Nichtrookies, 2025-Cap-Anker circa 428,8 Mio.; bestehende simulierte Rookie-Year1–3-Anker aus altem Snapshot **nicht** als fertige 2027er Vintages interpretieren.
- Reale **25.08.2026**-Sechs-Team-Roster und 185/185 verifizierte Acquisition-/Tenure-Zuordnungen, neuer hypothetischer Retention-Anteil bei Cut 50/30/15 % additiv außerhalb Top20. Bestehende historische frühere Retention-Vintages **nicht rückwirkend angenommen**. Keine neue Salary-Neuberechnung mitten im Szenario.
- Starter-erhaltender Cut-only-Algorithmus wie CP6d: 13 archivierte Starter je realem Team bleiben eingefroren, **greedy** größter positiver net Cap-Relief nach C-add. Keine echten Manager-Cuts/Trades, kein global optimaler Kaderplan; bei Fehlbetrag ist der reine Cut-only-Pfad unvollständig, nicht jede denkbare Liga-Lösung unmöglich.
- Aus ungebundenen *Veteranen* Year>=4, **`nfl_team` nicht leer und nicht 'FA'**, mit positiver archivierter 3Y-Performance werden 4 (alternativ 6) virtuelle Teams gebildet. Kaderformat pro Team: 2 QB + 2 RB + 2 WR + 2 TE + 4 FLEX aus RB/WR/TE + 1 K = **13 Startplätze**; beste nach 3Y-Performance in Positionsrunden, im Snake-Fairness-Schema auf virtuelle Teams verteilt. Nachher 17 weitere Depth-Spieler pro Team per Performance/Snake auf 30 reguläre Plätze. **Keine Rookies in Expansionsteams**; vorhandene reale sechs Teams enthalten dagegen ihre tatsächlich gehaltenen Rookies. Diese Bewertung dient nur als Qualitätsproxy, nicht tatsächliche Week-Projektion, Verfügbarkeits-/Injury-Check, Vollzeit-Spielbarkeit oder echte Draftentscheidung. Spieler mit historischer NFL-Teamkennung können inzwischen inaktiv sein.
- Cap-Seite für vier *vor*-FA-Expansionsteams separat mit 30 aufgenommenen Veteranen je Team und Top20 berechnet. Neu gecuttete Spieler können gemäß konzeptioneller Salary-Portabilität nach dem Cut für den Käufer rabattiert sein (vorbehaltlich vorläufiger Erfahrungs-Floor); Seller trägt additiven Dead Cap weiter. Andere zuvor freie Spieler kosten volles Salary. **Alle vier im mechanischen Pre-FA-Snake erzeugten Expansionsteams liegen in diesen Szenarien unter ihrem hypothetischen Cap**; das belegt keine freiwillige Aufnahme/geschlossenen Käufermarkt bei den sechs bisherigen Teams.

### Expansion-Qualitäts-Stress (3Y-Performance-Punkte als reiner *Index*, nicht projizierte Fantasy-Wochenpunkte)
| f | Hyp. Cap | Greedy Nonstarter-Cuts der bisherigen 6 | Bisherige 6 nach Cuts: nicht konforme Teams und Restüberhang | 4 neue Teams **vor FA-Draft** (13er Index, Range) | 4 neue Teams **nach Reservierung aller 30 historisch tatsächlich gewählten FA-Spieler** (13er Index, Range) |
|---|---:|---:|---|---|---|
| 0,90 | 440,9 Mio. | 12 | **0**, 0 Mio. | 137,8–144,0 | 120,3–131,1 |
| 0,875 | 428,6 Mio. | 19 | **0**, 0 Mio. | 138,9–144,6 | 121,1–131,6 |
| 0,85 | 416,4 Mio. | 31 | **1**, 5,5 Mio. | 144,8–152,4 | 131,5–137,0 |
| 0,80 | 391,9 Mio. | 53 | **2**, 44,2 Mio. | 150,1–157,7 | 138,0–147,0 |
| 0,75 | 367,4 Mio. | 74 | **3**, 98,3 Mio. | 154,4–160,8 | 143,0–152,0 |
| 0,70 | 342,9 Mio. | 99 | **5**, 195,0 Mio. | 154,7–161,2 | 143,7–153,4 |

**Baseline:** Vor hypothetischen Cuts können vier Starterkomplett-Teams aus dem freien Veteranenpool zusammengestellt werden, aber nur Index **128,3–137,4**, gegenüber 6 ursprünglichen bestehenden optimal bestückten 13er Startaufstellungen mit Index **176,9–189,3**. Bei Faktor 0,90 sinkt der Median der realen Teams in dieser vereinfachten Freeze-Welt nach Cuts auf etwa **176,8**, der mediane *vor*-FA-Expansions-Index erreicht ca. **140,9 (~80 %) / nach Reservierung der realen 30 FA-Picks ca. 121,9 (~69 %)**. Bei f=0,80 sind es ca. **172,1 vs. 153,4 (~89 %) / 141,4 (~82 %)**, jedoch haben dann zwei bestehende Teams 44,2 Mio. $ Overhang. Bei f=0,75 sind es ca. **169,2 vs. 157,2 (~93 %) / 146,1 (~86 %)**, **aber 3/6** bestehende Teams bleiben unter den Modellrestriktionen 98,3 Mio. $ über Cap. Das ist **keine** valide ausgeglichene 10-Team-Welt. Die historischen realen Teams enthalten günstige/teure Rookies, virtuelle Expansionsteams keine; ein gesonderter Veteran-only-Vergleich wäre sinnvoll.

**Sechs** statt vier neue virtuelle Veteranenteams: Bei f=0,75 *vor* FA-Draft Indizes ca. **140,0–149,7**, *nach* Reservierung der historischen FA-Picks ca. **129,8–141,3**. Die 12-Team-Expansion-Referenz ist deutlich anspruchsvoller.

### Das zentrale asymmetrische Marktproblem
- **Liefermenge:** Niedriger f setzt mit Cut-Druck mehr interessante Veteranen frei, aber niedriger f ist kein direkter Elite-Spieler-Umverteilungsbefehl. Bei schützendem Manager-Verhalten werden zunächst Bank/Depth-Assets freigesetzt, selbst wenn viele Cuts nötig sind.
- **Käufer-/Seller-Grenze:** Die vier neu erstellten 30er-Veteranen-Expansionsteams können bei f=0,75 einzeln mit ihren *hypothetischen* Top20-Gehältern den Cap erfüllen (30er-Roster mit 13 Starter-Bestwahl, 17 anschließenden Depth-Picks), während **drei der ursprünglichen sechs Teams selbst nach 74 C-add-Cuts nicht compliant sind**. Diese Asymmetrie ist kein akzeptiertes fertiges Modell, sondern zeigt, dass aggressives f plus C-add unter dem Ein-Zyklus-Sellermodell an die operativen Grenzen stößt. Seller-DeadCap darf nicht als kostenlose Buyer-Subvention umgedeutet werden.
- **Realistischere Übertragung:** In der tatsächlichen Liga existieren nur sechs Teams und **30 FA-Draft-Picks**. Der hypothetische 4-Team-Pool kann **nicht gleichzeitig unverändert** von zusätzlichen vier Teams UND den realen sechs bestehenden Teams erworben werden. Deshalb das *Post-FA-Reservierungs-Szenario* separat als **rein mechanische Angebots-Stressprobe**; keine Behauptung, die sechs Teams könnten ihre realen Picks unter permanentem Cap wirklich so finanzieren.
- **Kader-Kosten:** die jeweiligen 4 neuen Pre-FA-13er-Startergruppen bei f=0,75 hatten unter dem Salary-Portabilitäts-Proxy ca. **184–243 Mio. $** aktive Preise, ihre vollständigen 30er-Top20-Belastungen ca. **254–322 Mio. $**, unter Cap **367,4 Mio. $**; dennoch sind Qualität, NFL-Aktivität, tatsächliche Nachfrage, Vertrags-Dollars und künftige Nach-Cap-Erwerbe nicht verifiziert.
- **Wirkung auf alte Teams:** Ein Erfolg, der nur dadurch entsteht, dass die alten Teams illegale Cap-Überhänge tragen oder ihre sportliche Qualität völlig verlieren, gilt nicht als bestandener Zielbildtest. Zukunftsstrategie, Rookie-Salary- und Star-Retention-Effekte müssen mit den bestehenden sechs Nordsternzielen abgewogen werden.

### CP6-Fachfolge und bedingte Empfehlung
1. **Expansionstest in CP6 als anspruchsvollen, bewusst nicht formal ratifizierten Marktindikator aufnehmen** (4 virtuelle Teams = 10-Team-Referenz, 6 = 12-Team-Extremfall); kein echtes Ligaerweiterungs- oder Expansion-Draft-Vorhaben. Prüfen: Rollenbesetzung, 13er-Projektion, 30er-Top20-Kaufkraft, Cap-/Slot-Compliance, bestehende sechs Teams, tatsächlicher In-Season-Bestand **nach** FA-Draft, 1–2 hypothetische Rookie-Picks nur als offener eigener Mechaniktest.
2. **Nicht f=0,75 automatisch empfehlen, obwohl die 4 virtuellen Teams dann konkurrenzfähiger aussehen.** Der 0,75er Cut-Pfad enthält 74 mechanische Abgänge, 98,3 Mio. $ ungelösten Seller-Cadd-Überhang und deutlich schlechtere spätere Marktqualität nach dem FA-Draft. Gleiches gilt verschärft für f=0,70. Frühere 0,90/0,875 bleiben realistische Referenzen, sind aber am neuen ambitionierten *Markttiefen-Ziel* offensichtlich zu schwach.
3. **Nächster sinnvoller Systemhebel:** Nicht nur f senken, sondern vor-FA- und post-FA-Redraft-/Nachfrage-Liquidität zusammen mit wirksamen Dead-Cap-/Grace-/Eintrittsfenstern und entsprechendem Star-/Rookie-Preisgefüge testen. Ein einfacher star-lasts/teurere Elite-Bepreisung unter bestehender Criticality wäre **eine neue Hypothese**, keine stillschweigend beschlossene Formeländerung; 4-Team-Vergleich muss einen hinreichend sportlichen Markt **und** korrekte Seller-Buyers-Settlement-Pfade zeigen.
4. **Keine Überinterpretation:** 3Y-Performance aus Oktober 2026 ist nicht Weekly-Projektion/echte aktuelle NFL-Verfügbarkeit; greedy-Seller-Verhalten nicht optimal oder freiwillig; kein richtiges 10- oder 12-Team-Scoring-/Roster-/Cap-Repricing, kein einheitlicher 2027er Rookie-Vintage-Preis, keine komplette handelsfähige Verteilung der 30 FA-Picks. Kein Nachweis von Championship-Parität oder automatischem Nachwuchsvorteil.

**Rückverfolgbare Eingänge:** CP6d; salary-simulation-players.csv (05.10.), salary-dead-cap-concept.md §11, Pre-FA-League.json Commit 539aae40da3de444000805cea3170a116fae129d, archivierte Drafts 2024–2026 und Transactions 2024–25.08.2026. Alle 185 gehaltenen ID-/Tenure-Joins vom CP6d-Basischeck. **Nur Issue-Dokumentation, keine aktive Liga- oder Produktionsänderung.**

## CP6f – Zielzustand zuerst: eingeschwungene Sechs-Team-Ökonomie statt historischer Transition (16.11.2026)

**Nutzerkorrektur, neuer CP6-Forschungsrahmen:** Nicht primär von den heutigen/archivierten 2026er, unter einer anderen Salary-Policy aufgebauten sechs Teamrosters ausgehen und diese mittels Schuld/Dead Cap gewaltsam bereinigen. **Zuerst untersuchen**, wie sich sechs Teams *in einem dauerhaft eingeführten, befolgten Regelwerk* über idealerweise fünf volle Saison-/Salary-Zyklen organisieren, mit neuen Rookie-Jahrgängen, neuen Criticality-Salaries, Drafts, FA-Märkten und dynamischen Rosterentscheidungen. **Danach** vier zusätzliche, rein virtuelle Veteranen-Expansionsteams aus dem **am Ende dieses eingeschwungenen Systems noch ungebundenen Markt** finanzieren und sportlich vergleichen. Erst nach erfolgreicher Zielvalidierung rückwärts zur **Einführung/Übergangsfrage**. Kein aktiver Ligabeschluss/Implementierung.

### Strikte Trennung dreier Welten
1. **Welt Z: gewünschter etablierter Zielzustand** – six incumbent teams have acclimated from their initial empty/provisioned base through five modeled seasons. All rosters legal, prices refresh annually after preceding season, each rookie contract runs 3 years, permanent / designated in-season cap compliance can be tested under explicit nonlegacy policy. **Für die erste Kernprüfung weder künstlichen Altlasten-/Borrowing-Deckel noch alte 2026er Dead-Cap-Seller-Lasten ansetzen; C-add/Retention kann als separate spätere Sekundär-Sensitivität zugeschaltet werden, nicht als Bedingung des Primärzielbildes.** Die temporär capfreie Reorganisation nach Salary-Reprice und anschließende harte Deadline vor FA-Draft bleiben als **Entwurfsprozess** bestehen.
2. **Welt M: Migration/Übergang aus der echten Liga** – später separat: 2026er vertragliche Bestände, sofortige oder mehrjährige Umstellung, optional befristet kostenlos cutten, Bestandsschutz/Grace, vorheriges Ende alter Retention, Commissioner-Fähigkeiten. **Nicht** das Ziel-Cap von Übergangsschuld oder einmaligen Pflichtcuts abhängig machen.
3. **Welt E: rein virtueller Expansion-Benchmark** – vier weitere Veteranen-Teams würden in einem bestimmten Free-Agent-Fenster zum *bestehenden* 6er-Preis-/Cap-/Scoring/Top20-Modell aufgenommen, ohne echte Liga-Erweiterung, Expansion-Draft oder Schutzlisten. Ein tatsächlicher dauerhafter Wechsel zu zehn oder zwölf Teams würde die Criticality-Rank-Kurven, Aufstellungs-Knappheit und evtl. Cap-Marktanker verändern und ist ein **eigener zusätzlicher Sensitivitätstest**, nicht automatisch im Shadow Expansion Score enthalten.

### Verbindliche Qualitätsmessung, nicht Cut-Metrik
- **Konkurrenzfähigkeit von vier realen Alternativ-Kadern:** Je 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX / 1 K = **13 Starter pro Team**, insgesamt **52 Starter** zusätzlich. Hinzu kommen je Team ausreichende Backups/Roster-Plätze; bestehende 30er-Kadergrenze als separate Cap-/Depth-Finanzierbarkeit prüfen. **Vier disjunkte** Rookie-freie Veteranen-Kader zusammen konstruieren, keinen Topstar viermal verbuchen. Gegenprobe: sechs neue Teams = virtueller 12er-Markt.
- **Athletischer Index im realen Scoring:** getrennte Kontrolle auf 3Y-Performance, saisonale Projektionen, positionsbezogene Replacement-Knappheit, Verletzungen, tatsächliche Week-Startbarkeit. Expansionsteams zunächst **ohne Rookie-Boost**, hypothetische spätere 1–2 Zusatz-Rookie-Picks *nur optionaler Folgetest*.
- **Vergleichsdenominator:** vollständige Scoring-Startaufstellungen gegen bestehende sechs plus **fairer Veteran-only-Vergleich**, um die bestehenden günstigen Rookie-Picks nicht dem hypothetisch rookie-freien Expansionsteam als strukturelles Qualitätsdefizit anzulasten. Position QB/TE gesondert prüfen. Saisonschluss-/FA-Draft-/In-Season-Snapshot **unbedingt getrennt**.
- **Testschwellen als Vorschlag, nicht Ligaregel:** z.B. Median der vier Expansionsteams >=85–90 % des Median der sechs Etablierten und schwächstes Expansionsteam nicht weit unter unterem Bereich bestehender Teams, **alle vier cap-/slot-konform**, ohne den verbleibenden sechs Teams die Regelkonformität/Kernstärke zu zerstören; Sensitivität auf 80/85/90/95 % statt eine willkürliche Zielzahl fixieren. Keine Verwechslung von 3Y-Punkte-Proxy mit wöchentlichem projizierten Punktekonto.
- **Beidseitige Marktliquidität:** gute, teure und wirklich verfügbare Veteranen nach dem FA-Draft, aber auch Budget/Slots/ökonomische Bereitschaft für In-Season-Käufe bei bereits eingespielten Incumbents; ein öffentlich freier Superstar ohne legalen Käufer ist kein Markt-Erfolg. Top20-Cap plus günstige 3Y-Rookie-Verträge können die Allokation wesentlich ändern.

### Für den Test noch zu realisierende Simulation: nicht schon als fünffach ausgeführtes Ergebnis darstellen
- **Initialisieren ohne 2026er Besitzrechte/Altschulden:** alle sechs Teams beginnen in einem gemeinsamen Modellmarkt mit neutralen Startbedingungen und erlaubten fünf Rookie-Picks/Jahr; kein angehäufter Alt-Cap. Ein einzelner Neustart-Snake ist selbst **noch kein** 5-Jahres-Gleichgewicht.
- **Jährlicher Mechanismus 5+ Zyklen:** echte/gesampelte Leistung/Verletzungen + Rookie-Eintritt/Year1–3 + Year4-Veteran-Repricing → capfreie Managementphase → Rookie Draft → freiwillige Value-/Win-now-/Rookie-Balanced-Trade/Add/Drop-Entscheidungen → Cap-Deadline vor FA-Draft → tatsächliche FA-Entscheidungen unter Cap → echte laufende Cap-Kontrolle → nächster Zyklus. In jeder Saison müssen alle sechs vollständige 30er-Kader und 13er-Starter **legal** halten (keine vorgetäuschte „Cap-konforme“ 13er-Liste ohne Bench).
- **Mehrere plausible Managerstrategien**, nicht alle sechs als unendlich weitsichtige mathematische Maximierer: win-now, salary-/rookie value, geduldiges Reload und gemischt; verschiedene Seed-/Marktbeobachtungsvarianten sowie alle sechs Nordsternziele beobachten. Tatsächliche Manager-Akzeptanz von Trades nicht erfinden; Handelsmechanik in einfacher Phase auslassen oder klar beschränken.
- **Allokation und Free Agency müssen gegenseitig konsistent sein:** die sechs etablierten Teams dürfen nach dem FA-Draft nicht kostenlos weitere Stars adden und ihr eigenes Cap verletzen; ebenso darf kein unplausibler Zwang „immer x Stars frei halten“ eingebaut werden. Zu optimieren ist *endogen entstehende* FA-Markttiefe bei rationalen wirtschaftlichen Entscheidungen.
- **Cap-Kandidaten** offen lassen, inklusive aggressiver Faktoren **0,90 / 0,85 / 0,80 / 0,75 / 0,70**; jeweils bei gleicher Criticality-k1,5-/Rookie-/Floor-Welt. Die alte CP6d/e-Cut-only-Simulation darf nicht zur Ablehnung eines Faktors aus dem **Zielzustand** benutzt werden, weil sie eine falsche Vorwelt sanktioniert. Erst fragen, ob z.B. 0,75 über fünf Zyklen stabile sechs legale Teams und vier starke FA-Expansionsteams erzeugt; dann überlegen, wie 2026er Kader ohne unfaire Umstellung dorthin migrieren könnten.
- **Schulden-/Retention-Klarstellung:** Im primären Z-Lauf kein `legacy_debt` und kein erzwungener historischer `C-add`-Saldo. Falls Dead Cap im Zielsystem weiter diskutiert wird, ist *neu im jeweiligen laufenden Zyklus entstehende Retention* eine **eigene regelmäßige Mechanik** und **nicht automatisch gleich alten Umstellungslasten**. Keine stille Abrogation der dokumentierten Ein-Zyklus-Retention als Konzeptentscheidung; Primärmodell kann diese bewusst zu Forschungszwecken isoliert abschalten.
- **Fünf Forschungsachsen/operativ:** Seller/Buyer/Slots/Liga-Debt/Tilgung auch bei `debt=0` als `N/A: absichtlich abgeschaltete Mechanik` oder belegte Null ausweisen; nicht aus fehlendem Retention-Ledger berechnete Null mit belegten realen Kontoständen verwechseln.

### Wichtiges Korrektiv zu CP6d/e
Die vorher dokumentierten **53/74/99** (0,80/0,75/0,70) hypothetischen *aus heutigen August-2026-Kadern* erforderlichen Dead-Cap-Cuts und daraus verbleibende Überhänge waren **historische Migrations-Stressbilder**. Sie sagen *nicht*, dass die gleiche Cap-Höhe nach fünf Jahren etablierter Cap-gesteuerter Kaderführung unspielbar wäre. Die virtuellen CP6e-Teams waren gute Angebots-/Kompositionsproben, aber **kein** eingeschwungenes Sechs-Team-Equilibrium. Ihre 2026er Querschnittsergebnisse bleiben nachvollziehbar, verlieren jedoch den Charakter einer finalen Entscheidung über das Ziel-Cap.

**Aktueller Handoff:** Zuerst ein technisch prüfbares, vollständige 30er-Roster berücksichtigendes **5+-Zyklen-Zielzustandsmodell**, dann ein vierfacher Veteranen-Expansionstest mit 13er-Score, 30er-Cap und Freimarkt-Nachfrage; erst danach Transition-Strategie. Keine fünffache Dynamiksimulation als bereits erfolgt behaupten, keine produktiven Daten/Rules ändern.

## CP6g – 16.11.2026: erster dynamischer Fünf-Zyklen-Prototyp (Zielzustand, ohne historische Dead-Cap-Altlasten)

**Status:** Auftrag CP6f exemplarisch als erste **tatsächlich ausgeführte** programmatische Szenario-Rechnung gestartet und ausgewertet. **Nicht** reproduzierbar als committetes, getestetes Repository-Simulationswerkzeug und **keine** ausreichend kalibrierte fünfjährige Liga-Prognose. Hier ausdrücklich als *Prototyp-/Modell-Diagnostik* ablegen, nicht als Cap-Entscheidung; CP6g bleibt für fachlich belastbare Simulation und vollständiges reproducible artifact **offen**. Keine aktiven Liga-Regeln verändert.

### Versuchsanordnung (30 tatsächlich durchlaufene dynamische Modellläufe)
- Preis-Ausgangsbasis: exakt dieselben **1.268 archivierten Spieler-Salaries** wie CP6d/f (historischer Oktober-2026-Criticality-k1,5-/Rookie-/Gleitminimum-Proxy, nicht aktueller 2027er Vertragssatz). Veteranen für neutralen Startup ohne historische Teamrechte initial verteilen, **sechs vollständige Kader mit je 30 Spielern**, 13 relevante Starter, Top20-Limit. Alle sechs Manager bekommen verschiedene heuristische Ziele: Win-now, Salary-Value, Rookie-Entwicklung, gemischt (wiederholt). Im Modell **kein C-add/Dead-Cap und keine Altlast**; Cap-Faktor wird auf jährliche markweite Top120-Preis-Summe angewendet.
- Fünf synthetische Jahreszyklen: repricte Marktpreise von Veteranen bei zufälligem, an eigener historischer 3Y-Performance orientiertem saisonalen Leistungsdrift; je Jahr **30 synthetische neue Rookies** aus den Positionen und Salary-Year1-Proxies der **2026er** Rookieklasse, im Modell fünf pro Team. Year1/Year2/Year3 Rookie-Kontrakt 1,00/1,25/1,50; Jahr4 Performance-Übergang nur **vereinfachte unkalibrierte Funktion** und keine exakt gleiche reale Criticality-Bewertung. Nach dem simulierten Rookie-Draft Cap-/Rosterbereinigung (30er Kader, keine Dead Caps), danach eine in-season-repräsentative wert-/punktgetriebene FA-Swap-Runde je Team, ohne erzwungene Star-Freigabe.
- Je f **0,90/0,85/0,80/0,75/0,70** jeweils zwei Verletzungs-/Leistungsvolatilitäten (stabil ~10% / volatil ~29% unkalibrierter Zufallsskala), je 3 feste Seeds 31/47/59, somit **30 fünfjährige Pfade**. Abschließend vier disjunkte virtuelle Vet-only-Expansionsteams aus dem jeweils verbleibenden Free Agent Pool per Snake-Verteilung mit Cap-Gate und normaler 30er-Rosterpflicht. `Score` = Leistungssumme der 13er Bestaufstellung nach 3Y-/Synthetik-Performance, **keine echten wöchentlichen NFL-Punkte oder robusten Projektionen**.
- **Keine tatsächlichen externen Leistungsprojektionen, echte zukünftige Injury-/Retirement-Events, NFL-Draftklassen 2027–30, Trade-/Waiver-Markt-Forecasts oder vollständige Salary-Vintage-Jahrgänge**. Insbesondere: Das Fehlen eines validierten Retirement-/Active-Player-Mechanismus und die wiederverwendeten 2026er Rookie-Salary-Typen lassen nach fünf Jahren unrealistisch viele hochproduktive Veteranen und junge Spieler übrig. Manager-KI entscheidet mit schlichten Greedy-Heuristiken, **kein Gleichgewicht und keine Game Theory**, mit Bias durch frühe Startup-Draftwahl. Die Ergebnisse sind **nicht** kausale Belege für eine konkrete Cap-Höhe.

### Ergebnis der tatsächlich gelaufenen sechs unabhängigen Modellpfade pro f
Alle sechs realen Modellteams waren am Ende im Programm unter dem jeweiligen Cap und wieder auf 30 Slots aufgefüllt (6/6 Pfade je f); das Validierungsmerkmal betrifft *nur* das interne Modell. Die Zahl der gleichzeitig **vollständigen UND Cap-konformen vier Expansionsteams** schwankt deutlich:

| Faktor | Vollständige und legale 6 Bestandsroster nach fünf Jahren | Alle vier Expansion-Roster mit 30 Spielern und unter Cap | Median Bestands-Starterindex über 6 Pfade | Median Expansion-Starterindex über 6 Pfade | Beobachtete Expansion/Bestand-Median-Ratios: 3 Seeds stabil; 3 volatil |
|---|---:|---:|---:|---:|---|
| 0,90 | 6/6 | **5/6** | 173,4 | 172,9 | 1,17/1,06/1,05; 0,86/0,94/0,88 |
| 0,85 | 6/6 | **3/6** | 182,7 | 170,9 | 0,93/1,01/1,06; 0,88/0,89/0,90 |
| 0,80 | 6/6 | **2/6** | 184,5 | 171,1 | 1,03/0,98/1,06; 0,86/0,89/0,82 |
| 0,75 | 6/6 | **0/6** | 179,3 | 174,6 | 0,98/1,00/0,98; 1,00/0,89/0,87 |
| 0,70 | 6/6 | **0/6** | 175,9 | 171,6 | 0,95/1,02/1,01; 0,98/0,93/1,01 |

**Achtung: Das sind NICHT robuste oder miteinander wirtschaftlich/empirisch kalibrierte Erfolgsquoten!** Extrembeispiele Expansion > Bestand bei f=0,90 deuten auf **Management-Heuristik-/Fairness-Fehler** hin: Das Modell belässt trotz günstiger Aufnahme mehr Elitequalität im freien Pool, als bei gut adaptierten Managern plausibel wäre. Bei f<=0,75 reicht der Cap trotz starker virtueller Starterindices oft nicht aus, um mit dem schlichten Draft-Heuristik-Verfahren auch vier *vollständige* 30er-Teams legal zu bilden. Das könnte ein heuristisches Versagen oder reale Knappheit sein und ist **noch nicht** auseinanderdividiert. Manche frühen Rookie-Year4-Salaries sind unkalibriert günstig und junge Spieler wachsen pro Jahr nach, während erfahrene Spieler im Programm nicht in plausibler Anzahl ausscheiden. Aus dieser Kombination darf **keine Cap-Rangordnung** abgeleitet werden.

### Qualitätskontrollen / fachlicher Handoff (Pflicht vor Rating des Zielsystems)
1. **Exakte Reproduzierbarkeit:** Simulationscode und Maschinenresultate als eigenständige Forschungsartefakte auf Repository-Branch mit Tests/PR ablegen; diese in-memory-Prototyp-Rechnung ist eine explorative Vorprüfung, kein auditiertes CP6-Resultat.
2. **Lebenszyklus/Marktversorgung:** reale 2024–26 Rookie-Klassen getrennt und bewusst gegen mögliche 2027+ Prospects synthetisch modellieren, jährliche Retirement-/Practice-Squad-/NFL-FA-Effekte und Verletzung/Season-Availability, echte Year4-Performance-Neubewertung mit neuer Criticality. Kein unbewiesener Starter-Score als echte 2027er Punkteleistung.
3. **Agenten/Marktequilibrium:** mehrere Startup-Seed-Strategien; vollständiger 30er-Cap-Optimierer bzw. constraint solver mit 13 Starter-, Slot- und Top20-Constraints sowie Reserve für In-Season-Verstärkungen; Überprüfung, dass niemand offenkundig finanzierbare Elite liegen lässt; Tradepartner nicht fälschlich voraussetzen.
4. **Endogen fairer Test:** Aus demselben Eingesessenen-FA-Markt vier Veteranen-Shadow-Kader **unter Cap** optimieren, nicht nur einen heuristischen Draft. Vergleich von 13er und Veteran-only Baselines, plus 6er-Erweiterung, Pre-/Post-FA/In-season und tatsächlichem Buyer-Gate. **Nach 5 Jahren neue Price-Vintage und Projections**.
5. **Metrik / Governance:** alle sechs geschützten Ziele, fünf Economics-Achsen, gesamtmarktweite Salary-Quote und Cost/Fairness/Opportunitätskosten. **0,70/0,75 nicht endgültig ausschließen, 0,90 nicht als Gewinner erklären.** Der Nutzer hat explizit Zielzustand vor Transition priorisiert; **keine Einführung/Grace/Altlasten-Optimierung** vor Zielmodell-Abnahme.

### Aktueller Stand
**CP6f als Forschungsauftrag begonnen, erster synthetischer 30-Läufe-Pilot ausgewertet, Produktionswert noch nicht beweisbar.** Eine ausführlich validierte mehrjährige Simulations-Engine mit echten Source-Snapshots, harten Invarianten und testbaren Artefakten steht noch aus. Bisheriger CP6e-August-Cut-Stress bleibt separat als Migrations-/Transitional-Problem gekennzeichnet. Kein Ligabeschluss.

### CP6g Cross-Check 16.11.2026 – reproduzierbarer Gegenprototyp gegen 30-Läufe-Erstmodell

**Stand:** Parallel zum obigen CP6g-Erstprototyp wurde im Branch [research/cp6f-equilibrium-expansion-20261116](https://github.com/Lolindhir/fantasy-app/tree/research/cp6f-equilibrium-expansion-20261116) (zuletzt Commit \`b78c111b1a9dbe217be8a3308b19c79e110b298b\`) ein **ausführbares, read-only Research-Skript** fertiggestellt: \`fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs\`. Es liest den archivierten Criticality-/Rookie-Preisvektor und den 2026er Rookie-Draft, erzeugt jährliche simulierte Performance und Dynamic-Criticality-Rank-Salaries, wertet 3 fixierte Seeds × 5 Faktoren × 5 Zyklen (15 Szenarien) aus und testet je Jahr **sechs vollständige 30er-Kader und vier disjunkte 30er-Veteranen-Shadow-Teams**. Externe Spieler-/Rookie-Shocks sind nun für gleichen Seed **über alle Faktoren gepaart**, Manager-/Shadow-RNG getrennt; keine Historien-Altlasten und **keine** regulär entstehende Dead-Cap-Retention im bewusst isolierten Basislauf.

**Dokumentierter Research-[Draft-PR #1511](https://github.com/Lolindhir/fantasy-app/pull/1511) (CI/Reviewer-Abnahme offen):** [Fachbericht](https://github.com/Lolindhir/fantasy-app/blob/research/cp6f-equilibrium-expansion-20261116/fantasy-management/league-economy/salary/analyses/2026-11-16-cp6f-dynamisches-zielmodell-expansion.md), [15-Läufe-Metriken](https://github.com/Lolindhir/fantasy-app/blob/research/cp6f-equilibrium-expansion-20261116/fantasy-management/league-economy/salary/analyses/2026-11-16-cp6f-5y-summary.json), [Source](https://github.com/Lolindhir/fantasy-app/blob/research/cp6f-equilibrium-expansion-20261116/fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs). Die 15/15 internen Kernprüfungen (alle 6×30 Bestandsteams legal in allen fünf Jahren und vier disjunkte 30er-Shadow-Teams legal) bestehen **unter den eigenen Annahmen**; Median Shadow-/Bestands-Starterindex 0,90→**89,2 %**, 0,85→**86,7 %**, 0,80→**91,2 %**, 0,75→**90,5 %**, 0,70→**91,8 %**. Median hochpreisige freie Tier1/2 nach FA-Draft 11/13/17/18/19. Ein Seed-11-9-Jahres-Gegentest zeigt andauernde Schwankungen (0,80 in Jahr9 89,6 %, 0,75 91,0 %, 0,70 94,8 %).

**WICHTIGE REPLIKATIONS-DIVERGENZ / Entscheidungssperre:** Der separate 30×5-Jahres-CP6g-Erstlauf **weiter oben** konnte bei 0,80 nur in 2/6 und bei 0,75/0,70 in 0/6 Läufen vier voll cap-konforme Shadow-Teams bauen, während der neue Zweitprototyp 15/15 erreicht. Der Unterschied erklärt sich teils durch **andere Rookie-Versorgung (hier pro Jahr 30 Draftpicks +50 modellierte Undrafteds statt nur 30), vorausschauende 17 günstige Anfangs-Depth-Reserven, andere Startup-/FA-Optimierer, detailliertere k1,5-Criticality-Neubewertung und eigenständige RNGs**. Ohne empirisch kalibrierte NFL-Active-/Retirement-Dynamik, gleiche Rookie-Kohorten/Verfügbarkeit und **einheitlichen 30er-Solver** ist **keine definitive Cap-Rangordnung zulässig**. Die alte CP6g-Probe bleibt erhalten, ihre divergierenden Resultate dürfen nicht stillschweigend durch die günstigere CP6f-Matrix ersetzt oder beide Prozentquoten vermischt werden.

**Validierung:** GitHub-Fetch, vollständige Simulationsausführungen pro Seed/Faktor via verbundener Research-Laufzeit; 15/15 ausgabeseitig Cap-/Starter-/Roster-Checks erfolgreich; 9-Jahres-Kontrollen für 0,80/0,75/0,70, Report-/JSON-Konsistenz und Branch-Diff auf **4 rein research-/Dokumentationsdateien** geprüft. **Noch nicht**: getrennte Node-CLI-/CI-/Reviewer-Abnahme, Kalibrierung auf echte zukünftige NFL-Quellen, Source-generische 7–10-YR-Robustheit, realistischer wöchentlicher Injury-/Retirement-/Waiver-/Tradepfad, Dead-Cap-in-Zielwelt.

**PR-Status:** Draft-[PR #1511](https://github.com/Lolindhir/fantasy-app/pull/1511) eröffnet, Refs #1344 (nicht schließend); vier reine Fantasy-Research-/Dokumentationsdateien, kein Produktions-/Ligamodell-Wechsel. Reviewer-/CI-/Node-CLI-Abnahme nicht behauptet. Erst nach Peer-Review, Cross-Prototyp-Kalibrierung und separatem Ligaentscheid kann CP6 als Fachentscheidung weiterlaufen.

**Nächster CP6g-Gate:** Prototypen auf gemeinsame **kalibrierte** Eingabe und denselben gesetzeskonformen 30er-Roster-/Cap-Optimierer bringen, gesamte Market Supply/Buyer Paths in der Zielwelt testen. **Erst dann** Cap-Faktor fachlich empfehlen. Danach separat Transition. Dieses Pilot-Arbeitspaket verändert keine aktive Ligaregel.


## CP6h – 16.11.2026: Sechs vollständige 75%-Cap-Neukader auf 2026er Ist-Salary

**Ziel:** Auf expliziten Nutzerwunsch zunächst **kein** fünfjähriges Manager-Agent-Gleichgewicht und **keine** Übergangs-/Dead-Cap-Probleme, sondern für das laufende **Ligajahr 2026** sechs sportlich möglichst starke, wirtschaftlich regelkonforme, **vollständig neu verteilte** 30er-Roster unter einem f=0,75 berechnen. Keine realen Teamzugehörigkeiten, keine Trades, keine Verlängerungen, keine Verschiebung des Caps, keine historische oder neue C-add-Retention. Spieler-IDs sind ligaweit einzigartig; das sind **Simulationsteams**, keine empfohlenen real durchführbaren Trades, Sleeper-Roster-Veränderungen oder bereits eingeführten Satzungsregeln.

### Exakte Quelle und Preisgrenze
- Stand Repository `public/data/League.json` Saison 2026, `FinalScoredWeek=9` und `CurrentWeek=10`. `public/data/Players.json` 958 Spieler, 638 im gewählten NFL-Team-/Produktions-Screen; **nicht** aus dem 05.10.2026er Modell-Vektor rückprojizieren.
- Tatsächlich veröffentlichtes **2026er Salary 427.653.631 $ bei f=0,90** stimmt bei Abruf genau mit der Summe der 120 teuersten veröffentlichten `Players[].Salary` × 0,90 / 6 überein. Hypothese f=0,75 bedeutet **356.378.026 $** pro Team, d.h. **nicht** einfach 75 % des bereits um Faktor 0,90 rabattierten Caps.
- Status **Ist-Salary 2026** (`Players[].Salary`), **nicht** neues unratifiziertes Criticality-/Rookie-/Gleitminimum-Konzept. Letzteres ist eigene Forschungssensitivität, kein Resultat dieser Probe.
- Spielerqualitäts-Index: aktuelles `Players[].FantasyPointsAvgGame` 2026, bei Vorjahresdaten mit `PointHistory.SeasonMinus1.AvgPotentialGame` geglättet. Genauer für g=2026 absolvierte Spiele und p=Vorjahrspunkte: bei g=0 ergibt sich 0,38*p; bei g>0 und p>0 ergibt sich (g*current + 2,5*p)/(g+2,5); bei g>0 und p=0 ergibt sich current*(0,92 wenn g>=4, sonst g/(g+2)). Alle Endwerte mindestens 0; Filter `score>0,15` oder `GamesPlayed>0`. Qualifikationsscreen: QB/RB/WR/TE/K, belegtes NFL-Team nicht `FA`, kein `IsFreeAgent`. **Eingeschränkte Rookies können >0 Punkte auf Basis kleiner Stichproben haben. Das ist kein validierter Forecast, sondern ein nachvollziehbarer Index.**
- Injured/Inactive/NFL-Sperren *nicht* hart ausgeschlossen, weil konzeptionelle 2026er Kaderqualität statt tatsächlicher Week-10-/Week-11-Einsatzfähigkeit simuliert wird. Spieler können trotz `Injured=true` ins Lineup kommen; kein Anspruch auf sofort legale Sleeper-Aufstellung. Zero-Salary-Spieler im aktuellen produktiven Modell werden wie dokumentiert akzeptiert; ein Veteranenminimum ist **nicht** stillschweigend hinzugefügt.

### Optimierung und Invarianten
- Pro Team **30 reguläre Spieler** ohne Taxi/IR-Zusatzslots, davon beste 13: 2 QB, 2 RB, 2 WR, 2 TE, 1 K, 4 FLEX (RB/WR/TE). Weitere 17 als Bank/Depth.
- Exakte Top20-Salary-Neuberechnung bei jedem Add/Swap. Drei Seeds `1241,2051,5029` für einen interleavten Snake-Start mit score-/cost-bewusster Auswahl; anschließend iterativer Free-Agent-1-zu-1-Ersatz sowie zwei-Team-1-zu-1-Swaps. Optimiert werden Starterindex plus gewichtete Banktiefe und eine Ausgleichskomponente zwischen sechs Team-Startwerten. Beste lokale Lösung Seed **1241** mit einer Auswahl von **180/180 eindeutigen Spielern**, **6/6 vollständig / Cap-legal / positionslegal**, kein globales MILP-Zertifikat/kein mathematischer Beweis globaler Optimalität.
- **Starterscore-Index ist nicht eine offizielle Projektion** und ist durch die explizite Balance-Optimierung auffällig gleichmäßig verteilt. Eine reine individuelle Win-now-Maximierung kann ungleichere Teams und andere Starzuordnungen ergeben. Benchscore intern als 20% Top5 und 7% nächste7 der nicht gestarteten Spieler-Indizes; zählt zur Lösungsauswahl, nicht zur Starterpunktzahl.
- Die sechs Teams verbrauchen fast das ganze Cap; **freie Spieler sind nicht automatisch bei beliebigen Teams für Salary zulässig**. Zusätzliche Signings erfordern entsprechende 1:1-Cuts/Trades unter einem permanenten f=0,75, ohne Dead-Cap-Altlast in dieser Probe. Nur ein Modell-Zustand, noch keine selbststabilisierende 5-Jahres-Dynamik.

| Modellteam | Top20 Mio. $ | Cap-Rest Mio. $ | 13er Starterindex | gewichteter Benchindex | Starter mit >=4 2026 Games |
|---|---:|---:|---:|---:|---:|
| 1 | 355.64 | 0.74 | 204.16 | 15.10 | 12/13 |
| 2 | 356.12 | 0.26 | 205.15 | 16.03 | 13/13 |
| 3 | 356.01 | 0.37 | 202.74 | 16.63 | 13/13 |
| 4 | 356.07 | 0.31 | 202.27 | 17.52 | 12/13 |
| 5 | 356.38 | 0.00 | 202.75 | 17.07 | 12/13 |
| 6 | 355.69 | 0.69 | 202.08 | 15.58 | 13/13 |

### Vollständige sechs Kader

### Modellteam 1 — Starterindex 204.16; Top20 355.64 Mio. $; Rest 0.74 Mio. $

**13 optimale Starter innerhalb dieses Rosters:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Josh Allen | QB | 9 | 69.28 | 25.26 | 8 |
| Trevor Lawrence | QB | 6 | 34.00 | 19.26 | 8 |
| James Cook III | RB | 5 | 34.00 | 18.61 | 8 |
| Travis Etienne Jr. | RB | 6 | 22.76 | 12.70 | 3 |
| Jaxon Smith-Njigba | WR | 4 | 31.82 | 24.87 | 9 |
| Amon-Ra St. Brown | WR | 6 | 45.43 | 19.46 | 8 |
| Juwan Johnson | TE | 7 | 8.15 | 10.08 | 8 |
| T.J. Hockenson | TE | 8 | 11.43 | 9.85 | 8 |
| Ka'imi Fairbairn | K | 11 | 12.04 | 11.20 | 8 |
| Nico Collins | WR | 6 | 27.83 | 14.94 | 6 |
| Michael Wilson | WR | 4 | 10.49 | 13.21 | 9 |
| Parker Washington | WR | 4 | 6.39 | 12.89 | 8 |
| Rhamondre Stevenson | RB | 6 | 14.21 | 11.83 | 9 |

**17 weitere Kaderspieler:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Deshaun Watson | QB | 10 | 5.76 | 13.91 | 8 |
| Cam Ward | QB | 2 | 7.39 | 12.79 | 8 |
| Tre Tucker | WR | 4 | 6.97 | 11.62 | 9 |
| Jalen Coker | WR | 3 | 2.91 | 10.27 | 7 |
| Emanuel Wilson | RB | 4 | 2.51 | 9.33 | 7 |
| Tyquan Thornton | WR | 5 | 1.63 | 8.85 | 4 |
| Dominic Zvada | K | 1 | 0.00 | 8.51 | 8 |
| Drew Stevens | K | 1 | 0.00 | 7.59 | 8 |
| Emmett Johnson | RB | 1 | 0.00 | 6.99 | 8 |
| Malachi Fields | WR | 1 | 0.00 | 6.18 | 8 |
| Treylon Burks | WR | 5 | 0.66 | 6.04 | 6 |
| MarShawn Lloyd | RB | 3 | 0.08 | 5.96 | 8 |
| Jadarian Price | RB | 1 | 0.00 | 5.80 | 5 |
| Kyle Williams | WR | 2 | 0.51 | 3.96 | 9 |
| Josh Cameron | WR | 1 | 0.00 | 3.83 | 8 |
| Charlie Kolar | TE | 5 | 0.41 | 3.51 | 6 |
| Chris Bell | WR | 1 | 0.00 | 3.36 | 8 |

### Modellteam 2 — Starterindex 205.15; Top20 356.12 Mio. $; Rest 0.26 Mio. $

**13 optimale Starter innerhalb dieses Rosters:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| C.J. Stroud | QB | 4 | 28.73 | 18.78 | 8 |
| Jared Goff | QB | 11 | 43.40 | 18.52 | 8 |
| Javonte Williams | RB | 6 | 16.65 | 17.18 | 9 |
| Derrick Henry | RB | 11 | 34.58 | 16.00 | 9 |
| Puka Nacua | WR | 4 | 43.80 | 24.01 | 7 |
| Ja'Marr Chase | WR | 6 | 48.18 | 19.52 | 8 |
| George Kittle | TE | 10 | 23.01 | 13.17 | 8 |
| Sam LaPorta | TE | 4 | 15.85 | 10.46 | 8 |
| Will Reichard | K | 3 | 7.11 | 10.66 | 8 |
| Chuba Hubbard | RB | 6 | 16.50 | 15.77 | 8 |
| Ashton Jeanty | RB | 2 | 11.75 | 15.28 | 9 |
| Luther Burden III | WR | 2 | 3.61 | 13.48 | 9 |
| Garrett Wilson | WR | 5 | 20.46 | 12.31 | 8 |

**17 weitere Kaderspieler:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Kirk Cousins | QB | 15 | 17.93 | 17.01 | 9 |
| Jacoby Brissett | QB | 11 | 12.93 | 14.51 | 8 |
| RJ Harvey | RB | 2 | 8.88 | 11.64 | 6 |
| Caleb Douglas | WR | 1 | 0.00 | 11.15 | 5 |
| Devaughn Vele | WR | 3 | 2.53 | 9.51 | 8 |
| Jeremiyah Love | RB | 1 | 0.00 | 8.19 | 6 |
| Germie Bernard | WR | 1 | 0.00 | 7.68 | 8 |
| Makai Lemon | WR | 1 | 0.00 | 7.53 | 9 |
| Trey Smack | K | 1 | 0.00 | 6.54 | 9 |
| Eli Raridon | TE | 1 | 0.00 | 5.81 | 8 |
| Savion Williams | WR | 2 | 0.19 | 5.58 | 4 |
| Case Keenum | QB | 15 | 0.00 | 5.24 | 3 |
| Jordan Watkins | WR | 2 | 0.03 | 4.60 | 6 |
| Athan Kaliakmanis | QB | 1 | 0.00 | 4.01 | 1 |
| Elijah Mitchell | RB | 6 | 0.00 | 3.94 | 3 |
| Mike Washington Jr. | RB | 1 | 0.00 | 3.85 | 9 |
| Seth McGowan | RB | 1 | 0.00 | 3.34 | 9 |

### Modellteam 3 — Starterindex 202.74; Top20 356.01 Mio. $; Rest 0.37 Mio. $

**13 optimale Starter innerhalb dieses Rosters:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Joe Burrow | QB | 7 | 31.31 | 21.28 | 8 |
| Dak Prescott | QB | 11 | 37.87 | 19.38 | 9 |
| Bijan Robinson | RB | 4 | 43.37 | 20.59 | 9 |
| Bucky Irving | RB | 3 | 12.53 | 15.57 | 9 |
| CeeDee Lamb | WR | 7 | 40.35 | 20.26 | 9 |
| Chris Olave | WR | 5 | 21.35 | 17.47 | 8 |
| Tyler Warren | TE | 2 | 7.11 | 11.83 | 7 |
| Dalton Kincaid | TE | 4 | 8.55 | 9.84 | 8 |
| Tyler Bass | K | 7 | 4.91 | 10.23 | 8 |
| DeVonta Smith | WR | 6 | 22.47 | 15.27 | 4 |
| Matthew Golden | WR | 2 | 1.26 | 15.18 | 9 |
| Breece Hall | RB | 5 | 26.53 | 13.33 | 4 |
| Kyle Monangai | RB | 2 | 4.30 | 12.50 | 4 |

**17 weitere Kaderspieler:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Patrick Mahomes | QB | 10 | 44.55 | 18.32 | 8 |
| Geno Smith | QB | 14 | 25.33 | 14.21 | 9 |
| Michael Penix Jr. | QB | 3 | 6.36 | 12.79 | 7 |
| Blake Corum | RB | 3 | 2.83 | 9.78 | 9 |
| Rome Odunze | WR | 3 | 8.54 | 9.71 | 9 |
| Jacory Croskey-Merritt | RB | 2 | 4.10 | 8.85 | 5 |
| Malik Washington | WR | 3 | 2.39 | 8.78 | 8 |
| Jaylin Noel | WR | 2 | 0.95 | 8.11 | 7 |
| Pat Bryant | WR | 2 | 1.14 | 7.74 | 5 |
| Roman Wilson | WR | 3 | 0.40 | 6.78 | 5 |
| Audric Estime | RB | 3 | 1.19 | 6.15 | 2 |
| Tre' Harris | WR | 2 | 0.91 | 6.03 | 7 |
| Isaiah Williams | WR | 3 | 0.97 | 4.47 | 9 |
| Elijah Higgins | TE | 4 | 1.09 | 4.30 | 9 |
| George Holani | RB | 3 | 0.41 | 3.46 | 9 |
| Ja'Kobi Lane | WR | 1 | 0.00 | 3.29 | 5 |
| Jack Bech | WR | 2 | 0.45 | 3.24 | 5 |

### Modellteam 4 — Starterindex 202.27; Top20 356.07 Mio. $; Rest 0.31 Mio. $

**13 optimale Starter innerhalb dieses Rosters:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Drake Maye | QB | 3 | 29.28 | 21.21 | 9 |
| Caleb Williams | QB | 3 | 27.49 | 19.23 | 6 |
| Christian McCaffrey | RB | 10 | 54.04 | 21.90 | 8 |
| Tony Pollard | RB | 8 | 18.47 | 13.72 | 8 |
| Tee Higgins | WR | 7 | 21.43 | 18.09 | 8 |
| Christian Watson | WR | 5 | 9.83 | 17.19 | 9 |
| Isaiah Likely | TE | 5 | 4.07 | 13.11 | 8 |
| Harold Fannin Jr. | TE | 2 | 7.54 | 11.43 | 9 |
| Chase McLaughlin | K | 8 | 9.21 | 10.51 | 9 |
| Tetairoa McMillan | WR | 2 | 8.76 | 14.85 | 8 |
| George Pickens | WR | 5 | 25.13 | 14.25 | 8 |
| De'Von Achane | RB | 4 | 37.87 | 13.65 | 3 |
| Jameson Williams | WR | 5 | 14.54 | 13.14 | 8 |

**17 weitere Kaderspieler:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Aaron Rodgers | QB | 22 | 16.11 | 14.94 | 8 |
| Sam Darnold | QB | 9 | 23.35 | 14.62 | 7 |
| Jaxson Dart | QB | 2 | 13.82 | 13.94 | 2 |
| Quinshon Judkins | RB | 2 | 7.18 | 11.30 | 8 |
| Marcus Mariota | QB | 12 | 6.00 | 10.04 | 3 |
| Tyler Allgeier | RB | 5 | 6.59 | 9.52 | 9 |
| Cam Skattebo | RB | 2 | 7.96 | 9.51 | 7 |
| Tucker Kraft | TE | 4 | 9.54 | 9.45 | 9 |
| Evan McPherson | K | 6 | 7.27 | 9.31 | 8 |
| Colston Loveland | TE | 2 | 4.54 | 9.15 | 9 |
| Pat Freiermuth | TE | 6 | 6.29 | 9.10 | 8 |
| Jameis Winston | QB | 12 | 7.25 | 8.98 | 7 |
| Chad Ryland | K | 4 | 5.04 | 8.72 | 9 |
| Tyler Loop | K | 2 | 3.78 | 8.25 | 8 |
| Keon Coleman | WR | 3 | 4.03 | 8.19 | 8 |
| Dylan Sampson | RB | 2 | 1.64 | 8.02 | 3 |
| Tanner McKee | QB | 4 | 1.07 | 5.89 | 3 |

### Modellteam 5 — Starterindex 202.75; Top20 356.38 Mio. $; Rest 0.00 Mio. $

**13 optimale Starter innerhalb dieses Rosters:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Jordan Love | QB | 7 | 36.49 | 19.88 | 9 |
| Brock Purdy | QB | 5 | 40.73 | 19.49 | 8 |
| Kenneth Walker III | RB | 5 | 19.58 | 21.30 | 8 |
| Jaylen Warren | RB | 5 | 15.13 | 16.42 | 8 |
| Davante Adams | WR | 13 | 29.27 | 16.10 | 6 |
| Malik Nabers | WR | 3 | 13.99 | 13.22 | 8 |
| Trey McBride | TE | 5 | 27.31 | 18.27 | 9 |
| Dallas Goedert | TE | 9 | 12.11 | 10.83 | 7 |
| Spencer Shrader | K | 3 | 3.16 | 9.71 | 9 |
| D'Andre Swift | RB | 7 | 21.63 | 16.40 | 9 |
| Josh Jacobs | RB | 8 | 28.79 | 14.70 | 3 |
| Chase Brown | RB | 4 | 22.96 | 13.58 | 8 |
| Stefon Diggs | WR | 12 | 22.50 | 12.84 | 7 |

**17 weitere Kaderspieler:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Matthew Stafford | QB | 18 | 36.20 | 17.71 | 9 |
| Tyler Shough | QB | 2 | 7.31 | 16.54 | 8 |
| Denzel Boston | WR | 1 | 0.00 | 10.50 | 9 |
| Carnell Tate | WR | 1 | 0.00 | 10.16 | 7 |
| DeMario Douglas | WR | 4 | 6.57 | 9.62 | 9 |
| Jake Bates | K | 4 | 5.75 | 9.46 | 8 |
| Braelon Allen | RB | 3 | 1.16 | 9.34 | 9 |
| Ryan Flournoy | WR | 3 | 2.60 | 8.68 | 9 |
| Adonai Mitchell | WR | 3 | 1.96 | 8.30 | 5 |
| Andre Szmyt | K | 5 | 2.27 | 8.22 | 9 |
| Michael Mayer | TE | 4 | 2.03 | 8.01 | 9 |
| Xavier Hutchinson | WR | 4 | 1.55 | 7.58 | 8 |
| Pierre Strong Jr. | RB | 5 | 0.48 | 4.05 | 5 |
| Joe Milton | QB | 3 | 0.08 | 4.03 | 1 |
| Davis Allen | TE | 4 | 0.85 | 3.73 | 9 |
| Mitchell Evans | TE | 2 | 0.47 | 3.25 | 8 |
| Konata Mumpfield | WR | 2 | 0.14 | 3.23 | 9 |

### Modellteam 6 — Starterindex 202.08; Top20 355.69 Mio. $; Rest 0.69 Mio. $

**13 optimale Starter innerhalb dieses Rosters:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Bryce Young | QB | 4 | 17.82 | 17.68 | 8 |
| Jalen Hurts | QB | 7 | 54.81 | 17.42 | 5 |
| Jahmyr Gibbs | RB | 4 | 45.25 | 25.08 | 8 |
| Jonathan Taylor | RB | 7 | 33.04 | 18.20 | 9 |
| Zay Flowers | WR | 4 | 21.28 | 15.32 | 8 |
| Drake London | WR | 5 | 22.08 | 13.08 | 9 |
| Brock Bowers | TE | 3 | 15.52 | 18.27 | 7 |
| Travis Kelce | TE | 14 | 20.26 | 12.27 | 8 |
| Cam Little | K | 3 | 5.78 | 9.59 | 8 |
| Kyren Williams | RB | 5 | 36.64 | 17.26 | 9 |
| Bhayshul Tuten | RB | 2 | 1.61 | 13.31 | 8 |
| Justin Jefferson | WR | 7 | 28.36 | 13.03 | 7 |
| Jonah Coleman | RB | 1 | 0.00 | 11.57 | 5 |

**17 weitere Kaderspieler:**

| Spieler | Pos | NFL-Year | Salary Mio. $ | Leistungsindex | 2026 Games |
|---|:--:|--:|--:|--:|--:|
| Jayden Daniels | QB | 3 | 24.52 | 15.71 | 6 |
| Omar Cooper Jr. | WR | 1 | 0.00 | 11.52 | 5 |
| Emeka Egbuka | WR | 2 | 8.16 | 11.40 | 7 |
| Malik Willis | QB | 5 | 4.26 | 11.34 | 8 |
| Wan'Dale Robinson | WR | 5 | 14.36 | 10.60 | 8 |
| KC Concepcion Jr. | WR | 1 | 0.00 | 9.03 | 9 |
| Ollie Gordon II | RB | 2 | 0.59 | 8.35 | 8 |
| Jalon Daniels | QB | 1 | 0.00 | 7.37 | 5 |
| Darnell Washington | TE | 4 | 1.31 | 7.04 | 8 |
| Antonio Williams | WR | 1 | 0.00 | 6.95 | 8 |
| Kenyon Sadiq | TE | 1 | 0.00 | 5.60 | 9 |
| Darius Cooper | WR | 2 | 0.04 | 5.11 | 9 |
| Kaelon Black | RB | 1 | 0.00 | 4.33 | 8 |
| Nate Boerkircher | TE | 1 | 0.00 | 4.08 | 8 |
| Ted Hurst III | WR | 1 | 0.00 | 3.46 | 9 |
| Kevin Coleman Jr. | WR | 1 | 0.00 | 3.43 | 8 |
| Josh Cuevas | TE | 1 | 0.00 | 3.01 | 9 |

### Nicht vergebene spielbare Top-30-Namen nach diesem Team-Draft (beide Kennzahlen: aktueller Index, Salary Mio. $)

| Spieler | Pos | Index | Salary Mio. $ |
|---|:--:|--:|--:|
| Bo Nix | QB | 15.87 | 30.81 |
| Lamar Jackson | QB | 14.86 | 52.44 |
| Justin Herbert | QB | 13.19 | 37.30 |
| Mike Evans | WR | 11.93 | 23.34 |
| Deebo Samuel Sr. | WR | 11.89 | 19.83 |
| Baker Mayfield | QB | 11.40 | 44.51 |
| Daniel Jones | QB | 11.14 | 18.07 |
| Rashee Rice | WR | 10.54 | 19.53 |
| Kyler Murray | QB | 10.49 | 24.31 |
| Rico Dowdle | RB | 10.39 | 13.97 |
| Keenan Allen | WR | 10.29 | 24.87 |
| DK Metcalf | WR | 10.21 | 20.44 |
| DJ Moore | WR | 10.09 | 23.64 |
| Saquon Barkley | RB | 10.00 | 35.62 |
| Romeo Doubs | WR | 9.87 | 12.88 |
| Jaylen Waddle | WR | 9.77 | 16.86 |
| A.J. Brown | WR | 9.73 | 31.28 |
| Khalil Shakir | WR | 9.73 | 11.07 |
| Jakobi Meyers | WR | 9.68 | 18.24 |
| Aaron Jones Sr. | RB | 9.66 | 14.57 |
| Rachaad White | RB | 9.59 | 19.39 |
| Alvin Kamara | RB | 9.41 | 24.18 |
| David Montgomery | RB | 9.41 | 20.72 |
| Ladd McConkey | WR | 9.40 | 12.99 |
| Chris Boswell | K | 9.37 | 10.64 |
| Brandon Aubrey | K | 9.31 | 14.75 |
| Dalton Schultz | TE | 9.28 | 10.04 |
| Hunter Henry | TE | 9.25 | 10.60 |
| Zach Charbonnet | RB | 9.09 | 10.85 |
| Jason Myers | K | 8.91 | 11.38 |

### Beweis-/Geltungsgrenzen und nächste Forschungsprobe
- Harte Invarianten **alle erfüllt**: 180 einzigartige IDs, sechs 30er Kader, je 13 lineup-konforme Starter, je 17 Benchspieler, alle Top20 <= **356.378.026 $**. Historische Teamowners sowie 2026er tatsächliche Transaktionen bewusst ignoriert.
- **Nicht** garantiert global optimal; nicht der tatsächliche 2026er Saisonabschluss; kein NFL Injury-/Week11-Verfügbarkeitsstatus; keine vollständige 2027er Criticality-/Rookie-Wirtschaft. Nur ein einzelner stationärer Umverteilungs-Snapshot.
- Als nächste isolierte Sensitivität sinnvoll: identische 2026er Leistung mit *neuem* Criticality-/Rookie-/Gleitminimum-Salary f=0,75 durchrechnen, dann Marktqualität für 4 Veteranen-Schatten-Teams und Cap-Kaufbarkeit inklusive Nach-FA nach genau dieser 180er Verteilung beurteilen.
- **Wichtige realökonomische Beobachtung:** Teams haben fast keine Rest-Cap-Reserve; im gewünschten In-Season-Free-Agent-Markt ist daher ein Abgang oder günstiger Ersatz notwendig. Dieses Problem ist die zu testende Zielökonomie, keine historische Debt-/C-add-Altlast.

**Verhalten:** Nur berechnet und hier als Research dokumentiert. **Keine aktiven Liga- oder Software-Regeln geändert.**

## CP6i – 19.11.2026: 40er-Kader mit vollständiger Salary-Anrechnung und Dominanz-Obergrenzen

**Autorisiert:** Robert hat am 19.11.2026 die Dokumentation und Fortführung der Untersuchung ausdrücklich beauftragt. **Status: neue führende Forschungshypothese, kein Liga-Beschluss / keine produktive Regeländerung.** Dieser neuere Ansatz ergänzt CP6f–CP6h; er ersetzt insbesondere die alten Top20-/f=0,75-Tests nicht rückwirkend.

### Zu prüfendes 2027er Wirtschaftsmodell
- Bis zu **40 reguläre Kaderplätze, ohne Pflicht zur Vollbelegung**; 13 lineup-legale Starter gemäß dynamischer Liga.
- **Vollständige Salary-Anrechnung jedes gehaltenen Spielers** statt allein der 20 teuersten. Ob separate IR-/Taxi-Plätze dabei zählen und wie der Zeitraum von Cap-Vorgriff/Dead Cap abgegrenzt wird, bleibt ausdrücklich zu definieren und im Sensitivitätstest separat auszuweisen.
- Endogenes Cap = **Summe der Top-120-Spielersalaries / 6, Faktor 1,00**, ohne den bisherigen 0,90-Marktspannungsabschlag; für die veröffentlichte 2026er Ist-Preiswelt: Top120 **2.851.024.206 $**, Cap **475.170.701 $**. Nicht identisch mit dem 2026er geltenden Cap 427.653.631 $.
- Preisziel ist **Performance/Criticality (Centered-25, k=1,5), 3Y-Rookie-Contracts und gleitendes Minimum** nach den bestehenden Konzeptpapieren. **Keinen alten vollständig additiven Minimum-Salary-Proxy stillschweigend verwenden.** Cap-Vorgriff, Folgejahrestilgung und C-add/Retained Dead Cap bleiben separat, ebenso die operative Compliance.
- Für die komplette Liga gilt bei vollständiger Anrechnung: Die aufsummierten sechs Caps entsprechen genau der Top120-Markt-Salarysumme. Da alle zusätzlichen gehaltenen Spieler Geld kosten, erzeugt eine lange und teure Bank echte Opportunitätskosten; gleichzeitig können besonders günstige oder junge Spieler eine 40er-Strategie ermöglichen.

### Zentraler neuer Prüfstein: maximaler langfristig finanzierbarer Starterindex
Der vorherige CP6h-Sechservergleich (~202–205 Indexpunkte bei bewusst ausgeglichener 30er-Verteilung) ist **keine Obergrenze für ein dominantes Einzelteam**. Zuerst getrennt testen:
1. **A / Konzentrationsgrenze:** Für eine Snapshot-Preis-/Leistungswelt das stärkste mögliche legale 13er-Lineup unter vollständiger Salary-Anrechnung; 13er-Optimum nicht als voll belastbaren 40er-Kader ausgeben. Gegenprüfen mit Upper Bound und vollständigen Positions-/ID-Constraints.
2. **B / tragfähiger Kader:** Dieselbe Startermaximierung mit expliziter Belegung von 20/30/35/40 und verschiedenen qualitativen Backup-/Verfügbarkeitsanforderungen. Teamgröße ist **Obergrenze, keine Pflichtbelegung**. Bench-Salary wird voll bezahlt; bei Ist-Salary-Nullspielern deshalb separate Modellkontrolle gegen realistische Floors.
3. **C / passive Dominanz:** Einen bereits gebildeten Star-Kern über fünf Salary-Zyklen weitgehend unverändert fortführen; Salary-Neubewertung, Rookie-Year4, Injury, jährliche Verträge und notwendige Cuts als wirtschaftliche Gegenkräfte erfassen.
4. **D / aktiv verdiente Dominanz:** Über fünf Zyklen bei laufend guten Draft-/FA-/Trade-/Cap-Entscheidungen die maximale **in jedem Jahr** haltbare Startqualität und die dafür erforderlichen wirtschaftlichen Opfer messen, zusammen mit den anderen fünf eigenständig handelnden Managern. Nicht von perfekter Voraussicht ausgehen.

**Kernmetrik:** `H5 = max_Strategie min(Jahr1_Index, …, Jahr5_Index)` plus Verteilung über mehrere gepaarte Leistungs-/Verletzungsszenarien, jährliche Obergrenzen, Cap-/Asset-Kosten, Änderungen der Kernspieler, relativer Anteil an theoretischer All-Star-Qualität und sportlicher Abstand zum zweitstärksten Team. Gutes wiederholtes Management soll wiederholte Dominanz ermöglichen; passive, dauerhaft kostenlose Überlegenheit ist der Risikoindikator. Das ist eine zusätzliche **Forschungsoperationalisierung** der sechs geschützten Nordstern-Ziele, **kein neues siebtes Ziel** und kein hart festzulegender Index-Deckel.

**Szenarien/Attribution:** Identisches Scoring, gleiche Preis- und Spielerwelt pro Vergleich. Primär Hauptkandidat Cap f=1,00 + All-Player-Salary + max40; alternative Obergrenzen 20/30/35/40 und qualitative Bank; Criticality-/Rookie-/Floor-Preiswirkung isolieren; anschließend 5+ Zyklen mit dokumentierten externen/gesampelten NFL-Entwicklungen und Gegenstrategien. Gegebenenfalls stärkere Elite-Progression als separaten Hebel untersuchen, ohne endogene Cap-Rückwirkung zu ignorieren. Für den primären Einzelteamtest zunächst keine historischen Besitzrechte, keine C-add-/Debt-Belastung und keine unterstellten Buyer/Trades; diese Mechaniken in ausdrücklich getrennten Zielwelt-Sensitivitäten mit vollständigen fünf Wirtschaftsachsen prüfen.

**Quellen-/Evidenzgrenze:** Snapshots unter aktuellen 2026er veröffentlichten Salaries enthalten zahlreiche 0-$-Spieler und sind kein Beleg für 2027er Finanzierbarkeit. Der alte Oktober-2026-Modellvektor ist nur ein datierter Proxy, kein aktueller NFL-/2027-Contract-Forecast. Die bisherigen CP6g-Prototypen weichen stark voneinander ab und liefern weder ein validiertes 5-Jahres-Gleichgewicht noch ein beweisbares Startermaximum. IR/Taxi, Cap-Vorgriff, Dead-Cap-Rechnung, NFL-Availability, Retirements, reale Buyer-Angebote, Operator-Zeit und 2027+ tatsächliche Preise bleiben unbekannt, wo nicht konkret geprüft.

**CP6i Research-Checkpoint 19.11.2026 – jetzt auf Branch, weiterhin kein Ligabeschluss:** [Fachbericht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-full-salary-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6i-full-salary-starter-ceiling.md), [Metriken](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-full-salary-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6i-full-salary-starter-ceiling-metrics.json), [read-only Rechner](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-full-salary-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6i_starter_ceiling.mjs), README-Link; Commit [5c50ed8fcb24](https://github.com/Lolindhir/fantasy-app/commit/5c50ed8fcb2487ac8e6e1c0f72de263c91f2967c) auf `research/1344-cp6i-full-salary-starter-ceiling-20261119`. Datenquellen Player-Blob 113ffa77, League 923e42dd, Oktober-CSV 96ef8dea; 2026 Live-Cap 475.170.701 $, Criticality-/Rookie-/gliding-Floor-Oct-Proxy-Cap 489.862.208,83 $. Gepaarter positiver 2026-Indexpool 560 Spieler, zwei Proxy-Missing. **Erreichbare** 13er-Werte Live **274,670** (Obergrenze aus Lagrange-Relaxation 275,257), Concept **268,199** (Relaxations-Obergrenze 269,135). Unter voller Concept-Preis-Anrechnung liegt ein günstiges 40er-Fundroster bei **266,700** mit 31,182 Mio. $ Bankkosten; qualitativ stärkere Bank 40× Mindestindex 8 ergibt **260,739**, aber 30,998 Mio. Restcap signalisiert ungelöste Optimierungslücke. Das ist noch kein MILP-zertifiziertes/globales Maximum und keine fünfjährige Prognose. Echte 5Y-H5, Konkurrenzabstand, Injury/Availability, Jahr4-Repricing, Dead Cap/Debt und IR/Taxi offen. QA: Quellen/Caps gegengeprüft, Node `--check` + synthetischer CLI-Ausführungstest bestanden, strukturiertes JSON validiert; keine CI oder unabhängige Real-Daten-CLI-Ausführung behauptet. **Geändert: ausschließlich 4 Forschungs-/README-Dateien, keine aktiven Liga-/Produktionsdaten.** Nach Review/CI offen, Entscheidungssperre bleibt.

**Review-PR:** [Draft PR #1567](https://github.com/Lolindhir/fantasy-app/pull/1567) ist offen (nur Forschung, kein Merge/keine Regelfreigabe). Reviewer/CI, unabhängige Real-Input-Reproduktion und der global optimierte Mehrjahres-Solver sind weiterhin offen.

**Research-Handoff:** Einzelteam-Snapshot samt 2026er Istpreis und Oktober-2026-Kandidatenpreis (gleitendes Minimum korrekt) mit Bound/Bank-Qualität dokumentieren. Danach echten Mehrjahres-Portfolio-Solver / gut kalibrierte Ereignisse und die zweite Gegenstrategie-/Marktstufe erarbeiten, erst anschließend Regelpaket für alle sechs Manager empfehlen. Fortschritt und Ergebnisse in einem datierten Bericht unter `fantasy-management/league-economy/salary/analyses/` und hier im Issue pflegen.

## Forschungs-Checkpoints / aktueller Fortschritt

- [x] **CP0 – Quellenübernahme und Governance:** Beide Dokumente vollständig gelesen; bekannte kanonische Fachquellen und geschlossene Issues #1336/#1342/#879/#793/#744/#755/#956/#801 abgeglichen; ein zentrales Issue festgelegt. Keine aktive Fachregel geändert.
- [x] **CP1 – Reproduzierbare Baseline:** Datums-/Modellmatrix und Price/Cap-Versionen fixieren; Flo 2026 und andere Teams 2024–2026 mit Cut/FA/Rookie/Trade-Pfaden nachvollziehen; 05.10.-historische Formel gegen 11.10.-aktuellen Entwurf ausdrücklich trennen; Datenlücken/Tradeangebot-Lücken katalogisieren.
- [x] **CP2 – A/B/C (+ D falls nötig), abgeschlossen als strikt begrenzter, evidenzgetrennter 2026er Cap-/Mechanik-Stresstest (keine Manager-/Titelprognose):** Dieselben Roster/Transaktionen unter drei Szenarien rechnen; Cap-Einhaltung für Bundles, Waiver, Draft und Saison prüfen; pro Team effektiven finanziellen und sportlichen Zwang quantifizieren; **keine Managerentscheidungen erfinden**.
  - [x] **CP2a:** Einheitlicher Preis-/Cap-Stresstest, 6 Kaderzeitpunkte, 54 Transaktionsbundles, A/B/C(+D) und Trade-/Kernprofile dokumentiert. Kein historisch-exakter Preis-/Verhaltens-Backtest.
  - [x] **CP2b:** Historische individuelle Price-Versionen (G1) lokal überprüfen, rechtliche Cap-Transaktions-/Draft-/Taxi-/IR-Testsemantik (G4) transparent definieren und sportliche Starter-/Replacement-Kosten mit legalen kontrafaktischen Ausgangsrosters ergänzen; erst dann CP2 insgesamt abschließen.
- [x] **CP3 – Markt-/Retention-Test (14.11.2026, begrenzte historische Mechanik-Evidenz):** 40 Käufer-Paare + simultanes 8-Spieler-Clearing (0/1/2 Nichtkern-Cuts), historischer Cut/FA/Trade-/Re-Acquisition-Pfad, 2025/26 Rookie-Retention und 60/60 Draftsignal-Contract-Sensitivitäten; CMC-Trade mit exakten PickKeys. Die Frage realer ex-ante Tradeangebote und tatsächlichen Verhaltens unter permanentem Cap bleibt ausdrücklich unentscheidbar und ist kein fingiertes Ergebnis.
- [x] **CP4 – bestätigte Konzeptbausteine kontrolliert hinzuvariiert (14.11.2026, abgegrenzter Vertrag-/Settlement-Stresstest):** Rookie-Kohorten 2025/26 (60/60) mit **offen deklariertem Proxy-Anker** und eigenem endogenem Cap, isoliertes gleitendes Minimum, Flo 2026 mit historisch rekonstruierter Tenure und zwei **unbeschlossenen** Dead-Cap-Top-N-Abrechnungen, Käufer-Cut-Discount, Cap-Prüfung vs. Salary-Reset. **Kein** vollständiger historischer Y1–Y4-Vertragsbacktest oder kausaler Manager-Verhaltenstest. Weitere Mechaniken (Top-25/30, partielle Bankkosten, Rookie-Y4-Option, Salary-Retention-Trades, Cap-Rollover) **nicht** aktiviert. Ergebnis: [CP4-Bericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp4-contract-deadcap-sensitivities.md), [Metriken](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp4-metrics.json).
- [ ] **CP5 – Systemvergleich/Robustheit:** Gleiche Bewertungsmatrix für Istzustand, pragmatischen Zwei-Hebel-Ansatz und nur bei Bedarf komplexere Franchise-Varianten. Mehrere Teams/Saisons statt Einzelfall-Flo; langjährige Dominanz darf bestehen, wenn tatsächlich verdient/finanziert.
  - [x] CP5a – historische Cap-/Event-Fenster und Sleeper-Gates, PR #1477 gemergt.
  - [x] CP5b – kontrafaktisch legaler 2026er Start, Pfad-Divergenz, 2025er unabhängige Spät-Snapshots und Settlement-Vollzug, [PR #1479](https://github.com/Lolindhir/fantasy-app/pull/1479) / Squash `6aa0e0765c1c`; keine kausale Manager-/Mehrjahresbewertung.
  - [x] CP5c – zusätzliche Check-Fenster und isolierte Dead-Cap-Laufzeit-/Garantie-/Amortisations-Hypothesen, [PR #1483](https://github.com/Lolindhir/fantasy-app/pull/1483) / Squash `1fe3e76d6bb5`; nur mechanischer Research-Checkpoint, kein Liga-/Konzeptbeschluss.
  - [x] CP5d – automatische Annual-Cap-Schuld und DeadCap-Top20-Abrechnung, 14 archivierte Juni-Cuts und sieben Pricing-Snapshots; [PR #1492](https://github.com/Lolindhir/fantasy-app/pull/1492) / Squash `e80600f177d7`, keine Ligaentscheidung.
  - [ ] CP5-Rest – echte Mehrjahres-/Käufer-/Operator-Wirkung und Entscheidungsschwellen.
- [ ] **CP6 – Liga-Fachentscheidung vorbereiten:** Entscheidungsvorlage mit Nachweisen, Nicht-Zielen, Nebenwirkungen und ggf. Empfehlung „kein weiterer Eingriff“. Bestehende kanonische Detailpapiere erst **nach separater dokumentarischer Freigabe** fachlich fortschreiben; technische Einführung danach **in eigenem, explizit autorisierten Implementierungs-Scope**.
  - [x] **CP6a:** Nutzerpräferenzen vom 16.11.2026 als ausdrücklich unratifizierten Entwurf eingearbeitet: additive Cut-Retention außerhalb Top20, Ein-Zyklus-Laufzeit, F2/F3/P-hard/P-flex, mögliche kurze Grace und Fallstricke des Auto-Cuts; Entscheidung zu „verschiebbar“ und Vollzug bleibt offen.
  - [x] **CP6b:** Nutzerziel „jährlicher qualitativer Teil-Redraft“ sowie Mindest-CapCheck vor FA-Draft, verpflichtende Criticality-Bepreisung in allen Zielvarianten, separates Faktor-Kalibrierungsgitter (0,90/0,85/0,80 ungetestet) und Tenure-Anreizkorrektur im aktuellen Issue dokumentiert; keine Liga-Ratifizierung oder technische Änderung.
  - [x] **CP6c:** Neue Nutzerpräferenz zu während der Saison finanzierbaren, produktiven Tier1/2-Free-Agents und nach Reprice capfreier, nicht verschuldender Reorganisationsphase festgehalten; Trennung Salary-Reset/Cap-Deadline und D1/D2 Rookie-vs-FA-Reihenfolge inklusive NFL-Quellen, Dead-Cap- und Markt-Liquiditätskonflikten dokumentiert. Keine beschlossene Regel.
  - [x] **CP6d (erste Sensitivität):** Criticality-/Rookie-/Gleitminimum-Proxy mit vier Faktoren, 185/185 2026er Tenure-Nachweis, individuelles C-add, historische 30 FA-Picks als nicht-kausaler Replay sowie tatsächliche September-/November-FA-Markt-Supply erhoben; 0,90/0,875 priorisiert, keine vollständige 2027er Abnahme.
  - [x] **CP6e (Expansionstest):** 4 und 6 zusätzliche virtuelle Veteranenteams ohne Rookie-/Expansion-Draft anhand identischen 3Y-Performance-/Criticality-Proxys und aggressiver Cap-Faktoren 0,90–0,70 getestet; Pre-FA-/Post-FA-Qualität, vollständige 30er-Top20-Kaufpreise sowie Seller-Cadd-Overhang als limitierende Achsen ausgewiesen. Keine Liga-Ratifizierung/Implementierung.
  - [x] **CP6f (Zielmodell-Priorität):** Nutzerkorrektur dokumentiert: schuldenfreie, 5+ Zyklen eingespielte 6-Team-Ökonomie und 4 disjunkte Veteranen-Shadow-Expansionsteams vor Migration untersuchen. Ausführbarer *synthetischer* Zweitprototyp im Research-Branch erstellt (15 Fünfjahresläufe, 9-Jahres-Spotchecks), aber empirische Modell-/Cross-Prototype-Abnahme CP6g bleibt offen. Keine aktiven Regeln.
  - [ ] **CP6g (5-Jahres-Zielzustand-Abnahme):** 30 erste synthetische, nicht kalibrierte 5-Zyklen-Modellpfade explorativ ausgeführt und ihre Bias-/30er-Cap-Fehler diagnostiziert; reproduzierbare, realistisch kalibrierte 5-Zyklen-Simulation + 4-Veteranen-Expansionsteams samt qualitäts-/finanzierbarem Markt noch offen.
  - [x] **CP6h (2026 Ist-Salary 75%-Neuverteilung):** 638 geeignete NFL-Spieler, 180 eindeutige IDs, sechs vollständige 30er und 13er-Roster mit exakt berechnetem Top20-Cap 356.378.026 $; drei Optimierungs-Seeds, Starter-/Bench- und Free-Agent-Ausgabe erstellt; reiner lokaler 2026er Kader-Optimierungs-Proxy, kein globaler Solver und keine 2027er Criticality-Prognose.
  - [ ] **CP6i (40er / vollständige Anrechnung / Starter-Dominanz):** explorativer Preiswelt-/Bankindex-Snapshot samt read-only Research-Rechner auf Branch [Commit 5c50ed8fcb24](https://github.com/Lolindhir/fantasy-app/commit/5c50ed8fcb2487ac8e6e1c0f72de263c91f2967c) dokumentiert; globaler Solver, gleichzeitige sechs Manager und kalibrierte 5+-Zyklen-H5-Validierung noch offen. Kein Ligaentscheid.

**Priorität nächster Schritt:** **CP5-Rest nach CP5d: minimalen Debt-Jahrgangs-/Tilgungs-Gate, offene Top20-/Cut-Strafdefinition und deadlinefähige Settlement-Fälle gegen F2/F3 vergleichen; dafür echte Operator-Minuten/Manager-Reaktionen recherchieren, aber keine 2027+ Titelwirkung erfinden; danach CP6-Liga-Fachentscheidung.** anhand der sechs geschützten Nordstern-Ziele: A/Istzustand, wenige feste Cap-Checks, B permanent, C Criticality nur mit empirischem Zusatznutzen und die geprüften Rookie-/Minimum-/Dead-Cap-Bausteine als **separat gekennzeichnete** Add-ons. Offene CP4-Gates: echte historische Vertragsanker, 2024/undrafted-Scope, Rookie-Portabilität, DeadCap-TopN-Abrechnung, Prüfung vs. Reset, atomare Draft/Trade/Taxi/IR-/Grace-Semantik. Marcels Franchise-Claim bleibt unbeschlossen und isoliert. Keine Produktivregel geändert; Issue bleibt `status:analysis`.

## Akzeptanzkriterien für den Gesamtauftrag

- [ ] Strategische Vielfalt und Flexibilitätskosten sind im gemeinsamen Szenariorahmen geprüft: All-in vs. Cap-/Slot-Reserve vs. längeres Halten; Cut/Trade/Hold und Waiver-Churn, Buyer-Liquidität sowie Kadergrößen-Sensitivität mit realen Slot-Constraints und unbekannten Managerreaktionen ausdrücklich ausgewiesen.
- [ ] Eine fakten- und hypothesengetrennte, in kanonischen Quellen rückverfolgbare Antwort auf die Hauptfrage liegt vor: „Welcher strukturelle Cap-Druck verhindert kostloses dauerhaftes Horten, ohne gutes Management zu bestrafen?“
- [ ] A/B/C sind auf gleichen Daten, mit definierter Salary-/Cap-Zeitachse und dokumentierten Counterfactual-Grenzen vergleichbar.
- [ ] Flo-Cuts, Umverteilung, 7–1 vor November-Trades sowie 03.11.-Win-now-Investition sind als **verschiedene** Vorgänge korrekt eingeordnet; andere Manager/Saisons werden zum Gegencheck verwendet.
- [ ] Der wirtschaftliche Wert von langfristiger Rookie-Entwicklung und realistischen Trades vs. einfachen Cuts ist separat messbar oder mit benannter Evidenzlücke ausgewiesen.
- [ ] Bestätigte Konzeptentscheidungen und optionale Änderungen sind durchgängig getrennt; aktive Produkt-/Ligalogik unverändert, bis die Liga später beschließt.
- [ ] Nach den Forschungs-Checkpoints kann eine kurze ligaweite, neutrale Entscheidungsvorlage aus den zuständigen bestehenden Konzeptpapieren erstellt werden.
- [ ] Issue-Body bleibt nach jedem materiellen Forschungs-/Entscheidungscheckpoint selbstständig übergabefähig und ist keine bloße Sammlung von Chatlinks.

## Beziehungen und Abgrenzung anderer Issues

- **#1336**: abgeschlossen, eingefrorene Flo-Fallstudie, **keine** laufende Design-Ownership.
- **#1342**: abgeschlossen, datierter Übergabevermerk, ausdrücklich **keine** laufende Design-Ownership.
- **#793**, **#759**, **#801**, **#879**, **#744**, **#755**, **#956**: abgeschlossene fachliche Dokumentations-/Simulationsvorarbeiten, werden nicht wiedereröffnet und ihre Entscheidungen nicht stillschweigend umgedeutet.
- **#919** / **#1237**: getrennte technische Migration/zentralisierte Cap-Modelle der derzeit geltenden Regeln, **kein** Fachentscheid über permanentes Cap.
- **#194**: eigenständiger App-/UX-Trade-Simulator, keine Design-Ownership.
- **#209**: eigenständige spätere Out-of-Sample-Salary-Effizienzprüfung nach Saison 2026; möglicherweise ergänzende Evidenz, keine Doppelbearbeitung.
- **#810**: gekoppelte All-Time-/Rookie-Draft-Incentive-Thematik, **nicht** in diesem Issue stillschweigend neu aufrollen.
- **#1319**: historischer separater Draft-/Pick-Besitz-Synchronisationsdefekt; für Datenzuordnung Quelle/As-of prüfen, keinen neuen Produktfehler in dieses Research-Issue ziehen.
- Spätere produktive Modell-/Regelimplementierung bedarf eigenem autorisierten Scope. **Kein Konkurrenz-Issue für diese Synthese anlegen.**

## Validierung / Handoff

- **Erstellung:** 05.11.2026, ausschließlich GitHub-Issue-Dokumentation. Beide Nutzer-Links vollständig gelesen, kanonische Designkonzepte/AGENTS und verwandte Issue-Grenzen geprüft.
- **CP1 (05.11.2026):** Quell-, Zeit- und Modellmatrix sowie die rückblickend einheitlich bepreiste Sechs-Team-Baseline in [2026-11-05-salary-cap-cp1-baseline.md](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-05-salary-cap-cp1-baseline.md) erstellt; Salary-README verlinkt den Bericht. Snapshot-Werte: vor der Deadline 0/6, nach dem FA-Draft 4/6 rechnerisch über dem damaligen Cap (mit einem festen späteren Preisstand als ausdrücklich gekennzeichnetem Proxy); 05.11. live 5/6 über dem Cap, Flo +83.218.306 $. Roster-Kontinuität und Transaktion-/Draft-Inventar 2024–2026 berücksichtigt, CP2-Gaps dokumentiert. **Commit `83985a18d2e8f34c1bbb956c07571d5cf23c023a`**; Dokumentations-PR [#1356](https://github.com/Lolindhir/fantasy-app/pull/1356) **nach `main` gemergt** (Refs #1344; dieses Research-Issue bleibt offen), Squash-Commit `d3cf15b20b8ea5ade370b6ec9c1ef9fc4abc4e58` auf Branch `research/1344-cp1-baseline-20261105`. Validiert: nur zwei Markdown-Dateien; PR #1356 und `CI / Merge Gate`, `CI Core • Contracts & Publication Safety`, `CI • Selection` erfolgreich; Bericht und README-Link nach Merge auf `main` geprüft; 0 fehlende Salary-IDs und 6/6 Top-20-Gleichheit mit aktuellem Readmodel, Flo-Juni-Delta stimmt zur Fallstudie. Keine Laufzeit-/Modell-/Workflowänderung und keine neue Ligaregel. Historische Juni-Preise noch nicht exakt nachgewiesen.
- **Nicht ausgeführt:** keine A/B/C-Backtests, keine historischen hypothetischen Tradegebote, kein Ligabeschluss, keine Änderungen an `data-*`, `public/data/**`, Generator, App oder GitHub Actions.
- **Fachliche Fortsetzung:** Ausschließlich im vom Nutzer ausgewählten zentralen Salary-Chat. CP1 abgeschlossen, CP2a als bedingter Proxy-/Transaktions-Stresstest dokumentiert, **CP2b inzwischen abgeschlossen, CP3 offen**. Weitere Ergebnisse im Issue-Body konsolidieren; keine neue Regel, keine neuen Mechaniken/Issues ohne begründeten Scope.

- **Post-Merge-Abgleich 05.11.2026:** PR #1356 erfolgreich gemergt, `main` enthält den CP1-Bericht und README-Link; Issue bleibt `open`, `status:analysis`, `priority:p2`; CP1 abgenommen als Quellen-/Ist-Baseline mit G1–G8-Grenzen; CP2 bleibt offen. Keine produktive Cap- oder Salary-Regel verändert.

- **CP2a Post-Merge-QA:** [PR #1358](https://github.com/Lolindhir/fantasy-app/pull/1358) nach `main` gemergt; neuer [CP2a-Bericht](https://github.com/Lolindhir/fantasy-app/blob/main/fantasy-management/league-economy/salary/analyses/2026-11-05-salary-cap-cp2-abc-stress-test.md) und Salary-README-Link auf `main` direkt abgerufen; ausschließlich zwei Markdown-Dateien. Keine neuen produktiven Salary-Regeln oder überschriebenen Konzeptentscheidungen. CP2a erledigt; CP2b inzwischen als separater Folgecheckpoint abgeschlossen.

- **CP2b Handoff, 06.11.2026:** [Fachbericht im Dokumentations-PR #1369](https://github.com/Lolindhir/fantasy-app/pull/1369), historische 2026er Preis-/Cap-Zeitachse 6/6 dollar-genau, Nonstarter- und Käuferliquiditätsprobe, volle Trennung von A as-of / B Salary-Freeze / C Criticality. Zwei Markdown-Dateien; keine produktive Regel oder Designentscheidung geändert. CP2-Checkliste abgeschlossen **nur als mechanischer/historischer 2026er Stresstest**, nicht als historisch kausale Manager-/Trade-Verhaltenssimulation. CP3 bleibt offen. CI/Merge-Status nach PR-Finalisierung nachtragen.

- **CP2b Post-Merge-QA 06.11.2026:** [PR #1369](https://github.com/Lolindhir/fantasy-app/pull/1369) erfolgreich nach `main` gemergt (CI Core, Selection, Merge Gate erfolgreich), Bericht und Salary-README-Link im main erneut geprüft, ausschließlich zwei Markdown-Dateien; Issue #1344 bleibt `open`, `status:analysis`. **Keine produktive Modell-/Salary-/Draft-/Workflowänderung.** CP3 ist jetzt der nächste offene Forschungscheckpoint.

- **Designinput 14.11.2026:** Roberts ausdrücklich gewünschte Präzisierung zu langfristiger Chancengleichheit und Marcels unbeschlossene Franchise-Claim-Idee in den aktuellen Issue-Body aufgenommen. Als zwei systemische Vergleichspfade abgegrenzt; bestehende CP3-Priorität, aktive Ligaregeln und kanonische Detailformeln unangetastet. Keine parallelen Dateien, Implementierung oder simulationsfremden Behauptungen.

- **CP3 Arbeitsstand 14.11.2026, vor QA:** Datierter Markt-/Rookie-Forschungsbericht als erster Dokumentationscommit `4d4187e2848e15ab9641537bbcbdaa4b7332e858` auf Branch `research/1344-cp3-market-retention-20261114` erstellt; 40 Käufer-Paare, gemeinsame Acht-Spieler-Clearing-Probe, Rookie-Kohorten und 65/35-Draftsignal-Verknüpfung ausgewertet. QA-Korrektur zu 2025 Rookie Pick 3.02 und Ka'imi Fairbairn ist mit Commit `434810809f8751161626be052c063549877cf366` erfolgt; README-Link mit Commit `4104ce01543e897503f4c2dff9d44b80ef9ad65a` ergänzt; Branch-Dateien nachgelesen, Draftslot und Re-Acquisition-Name korrigiert, Source-Freeze/40-Paare/Clearing/60-Draftsignale und einmaligen README-Link geprüft. **QA der dokumentierten Research-Artefakte bestanden.** PR [#1467](https://github.com/Lolindhir/fantasy-app/pull/1467) als Teil-PR mit `Refs #1344` eröffnet; GitHub hat danach `mergeable=true` bestätigt. **CI Selection, CI Core • Contracts & Publication Safety und CI / Merge Gate: alle erfolgreich.** Nur zwei Markdown-Dateien; Head `4104ce01543e897503f4c2dff9d44b80ef9ad65a`. **PR #1467 nach `main` gemergt**, Squash `1a9c2b89c05f4945cc11a4f8c3e9cc257b7cda22`, CI Selection/Core/Merge Gate bestanden; CP3-Bericht und README-Link nach Merge auf `main` erneut geprüft. **CP3 abgeschlossen als abgegrenzter Forschungscheckpoint; Issue #1344 bleibt offen für CP4/CP5/CP6.** Kein produktiver Regel-/Daten-/Workflowwechsel.

- **CP4 Dokumentationscheckpoint 14.11.2026 (Arbeitsstand):** Bericht zu Rookie-Overlay (60/60), Veteranen-Minimum, Flos historischer Dead-Cap-Tenure, Käuferliquidität und Reset-/Settlement-Reihenfolge auf Branch `research/1344-cp4-contract-deadcap-20261114` mit Commit `42737466fbb1350657beb24c22e330b36b4c82dc` erstellt. Die Bewertung stützt sich auf den inzwischen kanonischen sechs-Ziele-Nordstern `fantasy-management/league-context/league-philosophy.md`. Zusätzlich wurde das datierte maschinenlesbare CP4-Metrikpaket mit Commit `e8870bfa31bbf5ec61ceb8fbedd948b89b0a83fa` angelegt. README-Eintrag mit Commit `0e7e9ad324cd0d10e415fdf1000b415793a3ff16` verlinkt Bericht und Metriken. **21 strukturierte QA-/Rechen-/Verweisprüfungen erfolgreich**, Dokumentations-PR [#1472](https://github.com/Lolindhir/fantasy-app/pull/1472) nach `main` gemergt, Squash `c7b9f9197527d81d38f08833bb5e5db9cf535f8c`; CI Selection/Core/Merge Gate alle grün, Bericht/Metriken/README nach Merge nachgelesen. Produktive Fachregeln bleiben unverändert.


### CP5a Research Checkpoint (14.11.2026)

- **Persistiert:** Forschungsbranch `research/1344-cp5a-system-windows-20261114`, Commit `9fe5c809108d4e388d9e5cb815babe5df3a36261`. Datierter CP5a-Systembericht `fantasy-management/league-economy/salary/analyses/2026-11-14-salary-cap-cp5a-system-windows.md`, separates `2026-11-14-salary-cap-cp5a-metrics.json`, genau ein README-Link; drei Artefakte auf Commit nachgelesen, JSON/QA geprüft.
- **Neue Evidenz:** 2025 drei as-of `SalaryDollars`-Märkte und Caps dollar-genau aus Original-Commits rekonstituiert, jeweils Teams 2/3/4 über damaligem Cap. 2026 4 as-of Märkte 0/6 (Juni/August), 4/6 (September), 5/6 (November). November-Kader zum September-Salary-Freeze ebenfalls 5/6 über Cap, positive Summe 176.958.042 $. Exaktes September→November-Replay 54 Bundles, davon 46 mit Adds und 3 Trades, 10 Over-Cap-Zusatzeffekte (7 Waiver, 3 Trades), Endroster 6/6 exakt.
- **CP5a bewertet:** A jährlicher Cap vs. F2 nach FA-Draft, F3 plus Midseason, B permanent. C Criticality, R60, MIN, Dead Cap separat, Claim nicht beschlossen. Wenige Checks adressieren Zeitpunkt-Slippage, lassen aber Zwischenereignisse zu; reine Trade-Gates verpassen Waiver-Effekte. Keine Ligaentscheidung, keine Runtime-/Cap-Regeländerung.
- **QA:** Source-Blob- und Player-ID-Prüfungen, Cap-Rekonstruktion, Event-Atomicity, finaler Kaderabgleich, 6 Nordstern-Ziele, Bericht und JSON-Link bestanden. **CP5 insgesamt und CP6 bleiben offen**, mangels kausalen mehrjährigen legalen Gegenfaktik-, vollständigen Contract-Portabilitäts- und gemessenen Operator-Kosten-Nachweisen. Nächster Schritt: PR/CI/Post-Merge und CP5b.

- **CP5a Post-Merge-Abnahme (14.11.2026):** [PR #1477](https://github.com/Lolindhir/fantasy-app/pull/1477) als Dokumentations-/Research-PR nach `main` gemergt (Squash `0c773faadd72a837427baa34fc32609cdec5a38d`). CI Selection, Core Contracts & Publication Safety und Merge Gate **erfolgreich**. Nach Merge Bericht, JSON-Metriken und README-Link direkt aus `main` geprüft: 3×2025, 4×2026, 0/0/4/5 Over-Cap, 54 Event-Bundles und 10 Signale (7 Waiver, 3 Trades). `CP5` bleibt offen für die ausdrücklich ausstehenden mehrjährigen legalen Verhaltens-/Kosten-Gates; `CP6` bleibt offen. Keine fachliche oder technische produktive Regel geändert.


## CP6i – 19.11.2026: 40er-Maximum, vollständige Salary-Anrechnung, Starterobergrenze

**Status:** explizit beauftragte Forschungsfortsetzung, keine Liga-Ratifizierung. [Fachbericht (Branch)](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6i-starter-ceiling-40er-full-salary.md), Commit `66ce087c15984a0fde75458ec395cdf8a55ab2a5`.

**Führender neuer Kandidat:** bis zu 40 *frei belegbare* reguläre Plätze; alle gehaltenen Spieler voller Salary; endogenes Cap = Top120-Summe/6 bei Faktor 1,00; künftig gemeinsam Criticality, 3Y-Rookie Contracts und gleitendes Minimum; C-add/Dead Cap, Kredit/Tilgung, IR/Taxi und Vollzug als explizit getrennte Prüfungen. Keine stillschweigende Rückkehr zu Top20-/30er-Pflichtkader und f=0,75 als Hauptszenario.

**Kernfrage:** cap-konformes Einzelteam-Maximum und passiv versus durch gutes Management über fünf Jahre haltbares Maximum, jeweils mit relativer All-Star-Qualität, Abstand zu Verfolgern und realen Opportunitätskosten. Bei optionaler Besetzung erhöht die zulässige Maximalgröße 20/30/35/40 den mathematischen reinen 13er-Grenzwert nicht unmittelbar; Depth-/Injury-/Mehrjahresanforderungen sind für sinnvollen Vergleich nötig.

**Erstprobe (isolierter 05.10.2026er 1.268-Spieler-3Y-Qualitätsproxy, 719 qualifiziert, *nicht* aktueller 2026er 475,17-Mio.-Cap):** Preiswelt Published f=1: Cap 480,679 Mio., All-Star 235,280 Index für 547,455 Mio., gefundener legaler 13er 221,313 für 480,464 Mio.; k1,5-Performance **ohne Mindestgehalt** f=1: Cap 489,862 Mio., derselbe All-Star 235,280 für 709,586 Mio., gefundener legaler 13er 212,841 für 489,598 Mio. Alle Zahlen 13er-only, lokale heuristische feasible Untergrenzen des globalen Maximums, keine vollwertigen saisonal abgesicherten 20–40er Kader und keine validierte 2027er Preiswelt. Kein Cap-/Debt-/Rookie-/IR-/Trade-Gesamtpfad behauptet.

**Nächster Gate:** full-cost legaler 13+Depth-Solver, 20/30/35/40 nur als *Maximalplätze*, gleicher Criticality+Rookie+Floor-Vektor, sechs rational konkurrierende Manager, anschließend passive/aktive gepaarte 5+ Zyklen und expliziter Seller/Buyer/Slots/Liga-Debt/Tilgungs- und Vollzugsvergleich. CP6g-Prototypenabweichung bleibt ungeklärt, vorhandener Draft PR #1511 unverändert. Keine Produktionsdateien/Regeln verändert.


**CP6i Reproduzierbarkeit (19.11.2026):** [Ausführbares Diagnose-Skript](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6i_starter_ceiling.mjs), Commit `0f2ef9dab4926b6fff8264448a66bc29fbbecdb7`. Liest die archivierte CSV, wertet feste 10.001 Salary-Shadow-Preise + lokale Tausche aus und prüft 13er-/Positions-/Cap-Invarianten. Die vorangehende Rechnung wurde bereits auf derselben mathematischen Methodik in der verbundenen JS-Laufzeit ausgeführt; unabhängiger Node-CLI-Lauf im Repository/CI und Peer Review **noch offen**. Kein Anspruch auf MILP-Optimum oder 5-Jahres-Abnahme.

**CP6i PR-/Handoff-Status:** [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) eröffnet (2 reine Forschungsdateien, `Refs #1344`, kein Closing). Letzter Head `0f2ef9dab4926b6fff8264448a66bc29fbbecdb7`. **Nicht gemergt**, reviewer-/CI-/Node-CLI-Validierung noch nicht beansprucht. Fachnächster Schritt: 13+Depth-Full-Salary-Optimierung in der gemeinsamen 2027er Preiswelt, dann passiv/aktiv 5+ Jahre; 6-Ziele-Nordstern und Fünf-Achsen-Finanzierung zwingend.

**CP6j – 19.11.2026: Full-Cost-Depth-Solver (Forschungscheckpoint)**

- **Skript-Checkpoint persistiert:** Branch `research/1344-cp6i-starter-ceiling-20261119`, Commit `c97fb6727d296629069226b24cb499e2af1d366d`, `fantasy-management/league-economy/salary/simulation/cp6j_full_cost_depth.mjs`, Draft PR #1576; Node-ESM-Researchskript für 13+Reserve-Full-Cost-Lagrange-Heuristik, exakt belegte 13/20/30/35/40 Slots und Bench-Quality-Thresholds 0/3/5/8, 3 Preiswelten. Preis-/Qualitätsbasis archiviert 05.10.2026; Cap marktweit Top120/6 f=1; 50%-Minimum nur für Year>=4, Rookie-Dollarverträge unverändert, expliziter Vorjahres-Cap-Anker 434.255.984 $. Kein Produktiveingriff.
- **Vorläufig in verbundener JS-Forschung ausgeführt (Skriptidentität/Node-CLI noch nicht separat belegt):** K+Minimum Cap 489,862 Mio.; Starterscore 13-only 212,841; bei erzwungener Belegung und Bench-Mindestindex 3: 20er 211,094, 30er 209,274, 35er 207,457, 40er 206,106. 20er-Bench-Qualität>=8: 206,106. Dies sind **erreichbare heuristische Werte**, keine globalen Maxima, keine echte Availability-/Six-Manager-Validierung; Maximalplätze sind nicht Belegungspflicht.
- **Validierung:** initiale Ausführung der äquivalenten V8-Suche auf 1268 archivierten CSV-Zeilen, 13er-Reproduktion P=221,313 / K=212,841; Roster-ID-/Positions-/Cap-Prüfung. **Node-CLI im verbundenen GitHub-Branch, CI, Reviewer und exakter Solver weiterhin offen.** Bericht, README-Link, 5Y-Paarvergleich und CP6g-Divergenz ebenfalls offen. Nächster Schritt: dokumentierten CP6j-Bericht persistieren, anschließende Prüfungen, kein merge/keine Regeländerung.

**CP6j datierter Ergebnisbericht (19.11.2026):** [Full-Cost-Depth-Sensitivität](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6j-full-cost-depth-sensitivities.md), Commit `48227f72db42979ca6124427b0bc1eab05213e85`; doppelter Berichtsstil vermieden: einzelner datierter CP6j-Forschungsbeleg mit P/K/KF-Preisprotokoll, genauen 13/20/30/35/40-Belegungssensitivitäten und Bench-Quality 0/3/5/8, Fünf-Finanzierungsachsen-N/A, alle sechs Nordstern-Ziele und offenen 5Y-Gates. Daten- und Rechenvalidierung zunächst nur über äquivalente verbundene JS-Exploration; unabhängiger Node-CLI/CI/MILP/Peer Review nicht behauptet. **CP6/Issue bleiben offen; keine Produktiv-/Ligawirkung.**

**CP6j README-/Repro-Checkpoint:** README-Index auf CP6i/CP6j ergänzt, Commit `4c7b1524f0f8443cae2d63c28c9bf45be6b930d0`. **Exakt der auf PR-Branch gespeicherte CP6j-Sourcecode** (Blob `b1e52a72cc33c27ecfdfc475ed9a9f4ee7d4e498`) wurde mit Originalarchiv-CSV in verbundener V8-Ausführung unter Adapter für `node:fs`/CLI-Args erneut ausgeführt: alle drei Preiswelten und die 13/20/30/35/40-Indexwerte bestätigten sich. Dies ist **kein native Node-CLI-/CI-/Peer-Review** und kein MILP-Globaloptimum. Weiterhin Draft PR #1576, kein Merge/keine Ligaänderung; 5Y-Paired-Simulation offen.

**CP6j Exakt-Script-Replay im Bericht nachgetragen:** Commit `f9de8b7499399a2a0580a043c89b7256d15fb009`, Originalskript-Blob `b1e52a72cc33c27ecfdfc475ed9a9f4ee7d4e498` mit unveränderter Archiv-CSV in V8-Adapter erfolgreich wiederholt; sämtliche P/K/KF-Profilwerte bestätigt. Nativer Node-CLI/CI/Peer-Review bleibt ausstehend. Nächster Fachblock: gemeinsame sechs Team-Eigentumswelt und gepaarte passive/aktive 5Y-Welten, inklusive CP6f/g-Divergenzabnahme. Kein Produktions-/Ligavollzug.

**CP6j PR-Abgleich (19.11.2026):** Draft [PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) auf Stand CP6i+CP6j aktualisiert, letzter Head `f9de8b7499399a2a0580a043c89b7256d15fb009`; umfasst CP6i- und CP6j-Berichte, beide Diagnoseskripte, README-Index. PR offen/draft, nicht gemergt; keine Freigabe als finale Cap-Empfehlung. Offene Gates: native Node-/CI-/Reviewer-Abnahme, globaler Solver, konsistente Rookie/Minimum-Preiswelt, sechs disjunkte Teams, valide 5–10-Jahres-passiv/aktiv-Tests und Finanzierungs-/Vollzugsebene.

**CP6k Prototyp-Checkpoint (19.11.2026):** [Sechs-Team-/gepaarter 5Y-Forschungsprototyp](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6k_six_team_paired_5y.mjs) auf CP6i/CP6j-Branch angelegt, Commit `97c11c7ea24c8483d9649a34c63e28c302dd5d7e`. Ansatz: sechs disjunkte Teams, Top120/6 f=1, alle gehaltenen Salaries, max40 optional/20 Forschungspraxis-Untergrenze, jährliches Performance-/Rookie-Repricing, 3 synthetische Seeds × Rookie-Zufluss 0/30/50 und gepaart passiv/aktiv. **Nur Code-/Methodencheckpoint, Ergebnisrechnung/QA noch ausstehend**; Trades, wöchentliche Injuries, Dead Cap, IR/Taxi, globaler Solver ausdrücklich ausgeschlossen. Für 2027–31 keine echten NFL-Daten. Kein produktiver Eingriff, keine Ligaentscheidung.

**CP6k 40-Slot-Draft-Korrektur:** Der erste verbundene Ausführungsversuch scheiterte in Year5 an einem 41. Spieler während eines verpflichtenden 5-Runden-Rookie-Drafts. Behoben durch expliziten legalen gleichzeitigen Kaderschnitt (Pick-Verfall notfalls erlaubt) im 40er-Maximum-Prototyp, Commit `39cfe609dd380ff33c83bae05b5e21350e1c29af`. Andere Simulationsergebnisse/QA noch offen. Kein produktiver Regel- oder Datenwechsel.

**CP6k Settlement-Bugfix:** Eine gepaarte Pilot-Ausführung (Seed 11, Rookie-Zufluss 0) zeigte 2029 einen unzulässigen False-Block bei Bedarf für Ersatzdeckungen: das temporäre Über-Cap während des gleichen Salary-Settlements war voreilig verboten, bevor legale kompensierende Cuts/Swaps geprüft wurden. Commit `fec23cf0c01991d0e503fbf9ab466074ef1dce11` ermöglicht die notwendige gleichzeitige Cap-Repair-Sequenz; **finaler Cap-Check bleibt hart**. Gegenrechnung und Model-Gates weiterhin offen.

**CP6k Index-/Cap-Korrektur:** Commit `ea87eaca450b92985b159d2f1554b5b77ce8eae6`: jährliches Zielsportmaß von roher Einjahresleistung auf denselben geglätteten Drei-Saison-Index wie CP6i umgestellt; jährliches endogenes Top120/6-Cap jetzt **nach** Eintritt der 30 plus 0/30/50 synthetischen Rookies und **vor** Salary-Lock berechnet; Rookie-Dollarvintage ab 2027 aus dem vorherigen vollen f1-Cap statt aus dem ursprünglichen 2026-Modell-Anker. Pilot 1×5 vor dieser Korrektur hatte legalen passiven und aktiven Pfad, aber seine alten Zahlen sind **kein belastbarer neuer Ergebnisstand**. Vollmatrix nach diesem Fix ausstehend.

**CP6k Rookie-/Retirement-Draft-Randfall:** Vollmatrix-Versuch scheiterte beim Draft mit anfangs 40 gehaltenen Spielern und noch nicht vollzogenen NFL-Exits, bevor die Cap-/Slot-Kette geprüft wurde. Commit `f3760b3573d86dba06860e437d435b8703d984fd` verschiebt Retirement-Clearance vor Rookie-Picks, verbucht zeitgleiche 40er-Kapazitätsschnitte nach Coverage-Priorität, und protokolliert fehlgeschlagene Simulationspfade statt stillen Abbruchs oder fingierter Legalität. Jahresabschluss-Hard-Gate bleibt vollständig bestehen. Matrix noch ausstehend.

**CP6k Seed-11-Ergebnis-Checkpoint:** [CP6k Seed 11 strukturierte Originalergebnisse](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6k-seed-11-results.json), Commit `df439f4cd1158312b7d83c8987c35987478fab60` mit exakt gespeicherten sechs 5Y-Runs (passiv/aktiv × extra-undrafted 0/30/50). 6/6 jährliche 6-Team-Full-Salary/40-Slot-Checks bestanden. H5: passiv 167,145/167,513/167,513; aktiv 172,515/175,498/177,382 (synthetische Indizes), Differenz +5,370/+7,985/+9,869. Ein einzelner Seed ist keine Verteilungs- oder Maximalitätsaussage. Full-3Seed-Matrix in einem V8-Rechenaufruf TIMEOUT, deshalb per-seed Resultfiles; Seed 29/47 ausstehend. Aktive Ligaregeln unverändert.

**CP6k Seed-29-Ergebnis-Checkpoint:** [CP6k Seed 29 strukturierte Daten](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6k-seed-29-results.json), Commit `caf80e10e0463f69e60f9aa06a3a5f24cea26864`. 6/6 gekoppelte Passiv-/Aktiv-Fünfjahrespfade bei zusätzlichen Rookies 0/30/50 vollständig 6-Team-/Full-Salary-konform; H5 passiv 166,393 alle drei, aktiv 175,309/178,150/179,932, Differenzen +8,916/+11,757/+13,539. Seed 47 ausstehend. Kein Multi-Seed-/Global-Optimalitätsbeweis, keine Ligaentscheidung.

**CP6k Seed-47-Ergebnis-Checkpoint:** [CP6k Seed 47 strukturierte Daten](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6k-seed-47-results.json), Commit `6a26e2df28baaaac195d8566d100ef97b1c0f066`. 6/6 Pfade jährlich 6-Team-/Full-Salary-legal. H5 bei Supply 0/30/50: passiv 174,393/174,393/174,393, aktiv 168,944/182,119/180,738, Differenz -5,449/+7,726/+6,345. **Kritische Gegenprobe:** Aktives Management ist nicht garantiert besser; bei weniger Rookie-Nachschub kann es den Fünfjahres-Minimumindex sogar verschlechtern. Alle 18 Pfade (3 Seeds × 3 Zuflussvarianten × 2 Regime) sind nun separat persistiert und zunächst interne Jahres-Cap-/Roster-Gates legal, aber keine externe Modell- oder MILP-Validierung. Bericht/Synthese/PR-Update noch offen. Keine Ligaregel geändert.

**CP6k 3-Seed-Forschungsbericht (19.11.2026):** Datierter, vollständiger [CP6k-Methodik-/Ergebnisbericht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-19-cp6k-six-team-paired-5y.md), Commit `d19ed7586f274e9347ba7665d02d52ce0310ebaa` mit 9 H5-Paaren, drei originalen Seed-JSONs und offenem Maximalitäts-/Trade-/Debt-/CI-Gate. QA aus den gespeicherten Daten: 18/18 Fünfjahrespfade und 90/90 Sechs-Team-Jahresendzustände intern legal (entspricht 540 Team-Jahresprüfungen), 45/45 gepaarte Caps/Allstar-Referenzen identisch, 8/9 gepaarte H5-Verbesserungen positiv, eine negativ (Seed47 undrafted0). Im Supply30-Hauptvergleich Median H5 167,513 passiv vs. 178,150 aktiv, Median gepaartes Delta +7,985. **Keine bewiesene nachhaltige Obergrenze**, CP6f/g nicht gelöst, 2027–2031 ausschließlich synthetisch. README-/PR-Index noch nachzutragen, keine Regeländerung.

**CP6k README-Index:** Research Overview auf CP6k-Bericht, Simulator sowie drei Seed-Metrikdateien ergänzt, Commit `f910ea33c80894232bcf09bfd340b388563e10b3`. Nachfolgende Arbeit: Draft-PR aktualisieren, Prüfgates/CI status lesen und vorhandene Result-Dateien auf Branch verifizieren. Keine aktive Ligaregel-/Produktivänderung.

**CP6k Draft-PR-Abgleich:** [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) auf **CP6i–k Full-Salary/Starter-/Bank- und gepaarte Sechs-Team-5Y-Forschung** aktualisiert; letzter Head `f910ea33c80894232bcf09bfd340b388563e10b3`, **nicht gemergt**. PR verweist auf den 19.11.2026er CP6k-Bericht, drei Ausgabedateien, die Prototypen, 18 intern legale 5Y-Pfade, offenes globales Maximum, 5 Finanzierungsgates und unabhängige CI-/Reviewer-/Solver-Abnahme. Issue weiter offen, aktive Ligaregeln unverändert.

**CP6k CI-/Persistenz-Abnahme:** PR-Head `f910ea33c80894232bcf09bfd340b388563e10b3`: GitHub Actions **CI • Repository Validation = success**. Von Draft-Branch wurden CP6k-Skript (Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`), Bericht und drei Originalresult-JSONs erneut gelesen. Eigenständige JSON-Querprüfung 18/18 legale Runs, 90/90 Sechs-Team-Jahreschecks, 45/45 gepaarte Cap-/All-Star-Welten; keine Inkonsistenzen gefunden. **CI-Gesamterfolg behauptet ausdrücklich keine unabhängige native Node-CLI-Reproduktion, empirische 2027–31-Validität, globales MILP-Optimum oder Peer Review.** PR #1576 verbleibt offen und Draft, Issue #1344 offen; keine produktive Ligaregel geändert.


**CP6l Kredit-/Rebuild-Finanzierungsresearch:** Am 20.11.2026 wurde auf dem bestehenden Draft-Branch zu PR #1576 das neue rein forschende, reproduzierbare [CP6l H2/H3-Kredit-/Rebuild-Headroom-Skript](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6l_cap_deferral_overlay.mjs) angelegt, Commit `dfe4fb188549916a196bc89902a4401e21b07a16`. Es vergleicht 5/10/15-%-anfänglichen Cap-Vorgriff unter 10/25-%-Deckeln, verbindliche H2/H3-Tilgungsraten und frühe Tilgung ohne Refinanzierung auf identisch gespeicherten CP6k-Sechs-Team-Jahresbudgets. Rebuild-Headroom-Gegenprobe mit 5/10/15-%-nicht genutztem Cap (kein automatischer Cap-Carryover und keine gratis Picks). **Explizit nur Finanzierungshülle, keine neue All-in-Player-Akquisition, keine echten Trades/Buyers, kein sportlicher H5-Effekt oder Manager-Asset-Backtest.** Validierung/Resultdatei/Researchpaper offen, aktive Regeln unverändert.

**CP6l Replay-/Kreditpolicy-Abnahme:** Neues CP6l-Skript auf gespeicherten CP6k-Original-JSONs in der verbundenen JS-Laufzeit ausgeführt (Simulator-Blob ursprünglich `012b7c084566a52b26bb2136430c47e7ab0a7553`, CSV weiterhin CP6k-Archiv); 18 ursprüngliche 5Y-Pfade, 216 H2/H3-Finanzierungsfälle und 54 Rebuild-Headroom-Ziele reproduziert. Kleine redaktionelle Kreditpolicy-Kodierungsbereinigung Commit `241ca4bdd2c6ff47725d0b783e2550a3d03818c6`. Hauptbeispiel 30 zusätzliche undrafted/aktives Management: 10%-Draw/H2/H3 Mindestpflicht jeweils 2/3 Seed-Pfade aus freier Cap-Luft deckbar; bei freier vorzeitiger Tilgung 3/3. 15%-Draw/H2 nur 0/3 Minimum bzw. 1/3 vorzeitig; keine Hypothese zu realen sportlichen Verbesserungen belegt. Ergebnisdatei/Methodikbericht weiter offen; nicht als neues Spielregelwerk interpretieren.

**CP6l strukturierte Finanzierungsmetriken:** [Ergebnis-JSON](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-20-cp6l-financing-metrics.json), Commit `5d5823a100c73a51812d7793bda3f89e0d7a17a0`, gepinnt auf CP6l-Script-Blob `9278e3a5950a55130deef97272364678b3a07a62` und drei CP6k-Seed-Dateien. 216 Kredit-H2/H3- und 54 Rebuild-Headroom-Fälle; **88/216** Kreditfälle scheitern nach vorgegebenem harten No-Refinance-/Tilgungs-Finanzierungsgate, nicht als erfolgreich markieren. Fokus Seed47 Supply30 aktiv: 10%-Kredit/H2 Minimum-Tilgung 2029 **8.901.710 $** zu wenig, höhere Frühzahlung aus 2028er Headroom dagegen finanzierbar. Sportliche Wirkung, echte Übernahme-Deals, C-add-Cuts, 6-Team-Debt-Vintages und alle tatsächlichen Buyer-/Asset-Kosten weiter nicht modelliert. CP6l-Forschungsbericht und README/PR-Handoff folgen.

**CP6l datierter Forschungsbericht (20.11.2026):** [All-in/Cap-Vorgriff/H2-H3-Tilgung/Rebuild-Headroom](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-20-cp6l-allin-rebuild-capvorgriff.md), Commit `7c3dfff3dca243e1171769710e553799dbf2333d`. Durchgerechnete Finanzierung über vollständige CP6k-Salary-Kosten, **216** Kreditfälle + **54** Rebuild-Headroom-Ziele, Nullzins-H2/H3 und frühzeitige Tilgung, No-refinance, bewusste C-add/Trades/Assets als nicht modelliert. Für Hauptvariante aktiver Seed-30-Supply: 5% Kredit in allen 3 Seeds selbst mit H2 finanzierbar, 10% H2/H3 bei Mindesttilgung je 2/3 (Seed47 fehlende 2029er Rate H2 **8.901.710 $**), bei Frühzahlung 3/3; 15% H2 0/3 Mindestrate oder 1/3 frühzeitig. Rebuild 15% freies Cap verlangt zusätzlich 23,361/20,691/11,336 Mio. $ 2027-Entlastung in Seed11/29/47, ohne Asseterwerb. Kritischer methodischer Befund: H5 alleine verzerrt All-in- und Rebuild-Strategien, zukünftige Titel-/Window-/Asset-Metriken nötig. Dies ist noch **kein** vollständiger sportlicher All-in-Rebuild-Test. Kein Ligabeschluss, PR weiterhin Draft.

**CP6l README-Index-Checkpoint:** Salary-/Research-README verlinkt nun CP6l-Bericht, 216/54-Case-Finanzierungs-JSON und gekoppeltes Ledger-Skript, Commit `a66448747ecf929a466f704ead685781f9b0dc44`. Weiteres Gate: Draft PR #1576 aktualisieren; CI-Gesamterfolg und unabhängige Methodik/Solver/Trade-Validierung getrennt berichten. Keine aktiven Ligaregeln geändert.

**CP6l Draft-PR-Handoff (20.11.2026):** [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) in Titel und Body auf CP6i–l aktualisiert (Head `a66448747ecf929a466f704ead685781f9b0dc44`); enthält getrennte Quellenlink-/Abnahme-/Ungewissheitsliste für H2/H3-Kredit, 216 Cashflow-Fälle, 54 Rebuild-Headroom-Fälle, keine Aussage zu neu erworbenen Startern/Picks/realen Trades. PR bewusst offen/Draft, keine Produktivregeln geändert. Nächste fachliche Arbeit: gekoppelte 6-Team-Trade-/Pick-/Salary-Cadd-Engine für echten sportlichen All-in/Reload/Rebuild-Vergleich; H5 nur Sekundärmetrik. Offene unabhängige Node-/Peer-/Solver-Abnahme und Hard-Failure-Vollzug nicht als bestanden markieren.


**CP6m (20.11.2026) jährliche vs. permanente Cap-Kontrolle – neuer Trade-Frontier-Prototyp:** Forschungsdatei [cp6m_cap_window_swap_frontier.mjs](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6m_cap_window_swap_frontier.mjs), Commit `bb74011b14123c96549c90e55838ecfaf299923f`. Bounded same 2026-10-05 CP6k Full-Salary 6-team start, 1:1/2:2 hypothetische Player-Swaps und sofortige beidseitige Cap-/Roster-Konformität (permanent) vs. nur jährlich (unterjährig Überhang möglich), drei Seeds. **Keine echten Manager-Akzeptanzen, Picks, C-add, 2027er Cap Deadline oder langfristigen sportlichen Outcomes.** Gefrorener CP6k-Source-Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`. Ausführung/validierte JSON-Ergebnisse, Bericht/README/PR-Abnahme stehen noch aus; Nordstern/produktive Regeln unverändert.


**CP6m quantifizierter Cap-Window-Vergleich (20.11.2026):** [Bericht annual vs dauerhaft](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-20-cp6m-annual-vs-permanent-cap-decisions.md) Commit `515ec6a73cff5d691c83eca458da00f5a3fde123`; [1:1/2:2 Test-Ergebnisse JSON](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-20-cp6m-cap-window-swap-metrics.json) Commit `86882df05264a59e74fd342f58cf8e5def212976`, Script-Blob `e32fe7986461b398547bac3114e84188abffb56d`, CSV-Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`. 3 CP6k-Seedstartwelten, 6 disjunkte full-salary-legale Teams, T0 9–11 Mio $ Cap Headroom: 1:1 322 potenzielle +Starter-Upgrades falls innerhalb Saison über-Cap erlaubt, davon nur 46 mit sofort bilateralem Cap, +2 Index 179 zu 0; 2:2 17.296 zu 1.167, +2 10.038 zu 1. Keiner der besseren Deals macht zugleich Verkäufer-Starterindex besser: **Trade-Gegenwert/Picks fehlen, Zahlen sind nicht realisierbare Trades**. Gepaart CP5a/b historischer Top20-Check unterscheidbar dokumentiert. Forschungspriorität jährliches Cap (A) vs. F2/F3 vs. permanentes Bundle-Gate (B), ohne H2/H3-Kreditannahme; tatsächlicher jährlicher Dead-Cap-Reset bleibt. **6 Nordstern-Ziele, 5 Finanzachsen, Sleeper read-only Vollzugsgrenze, Hard-Failure-Unsicherheit** dokumentiert. Kein kausaler 5Y-Champion-Vergleich; keine aktiven Änderungen.


**CP6m README-Index:** CP6m jährliches Cap vs. permanentes Event-Gate samt CP5a/b-Vergleich, Simulator, 3-Seed-1:1-/2:2-Metriken im Salary Research README referenziert. Commit `11388a714d597e721d7c19bf9e3145c37460ca4e`. Draft PR #1576 weiter aktualisieren, CI prüfen, keine produktive Regeländerung.


**CP6m Abnahme / Draft-PR-Handoff (20.11.2026):** [PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) weiterhin **Draft/open**, CP6i–m Titel und Body ergänzt, HEAD `11388a714d597e721d7c19bf9e3145c37460ca4e`. [CP6m-Audit-JSON](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-20-cp6m-cap-window-swap-metrics.json) aus verbundenem V8 reproduziert, Blob `701014d492b71b7347fd78ffafbee84d43fe6f02`, 3 Seeds × 2 Trade-Gruppen, Positional-/Salary-/bilaterale-Cap-/Zählinvarianten erneut ohne beobachtete QA-Fehler geprüft. **CI • Repository Validation für HEAD `11388a714d597e721d7c19bf9e3145c37460ca4e` ist completed/success (am 20.11.2026 erneut geprüft).** Native Node CLI, unabhängiger Solver, Verkäuferakzeptanz, All-in-Saison nach folgendem Deadline-Settlement, 5Y-Rebuild-/Titelwahrscheinlichkeiten und realer Sleeper-Gate-Vollzug weiter offen. Kein neues aktives Cap/Regelwerk und keine H2/H3-Schuldregel eingeführt.


**CP6n – 3Y Market-Value/Contract-Cooperativ Szenario (22.11.2026):** Neuer vom Nutzer gewünschter Vertrags-Alternativentwurf: **Rookie 100/125/150 % beibehalten**, Veteranen bei Verpflichtung 3Y Marktwert-Freeze mit möglicher Vertrags-Eskalation, annualisiertes market-based Top120-Cap getrennt vom locked ContractSalary, Trades übernehmen Restvertrag, Cuts mit 14-Tage-Claim und ggf. zukünftiger Garantie/Dead-Cap. Kein Beschluss; **Widerspruch** zum bisherigen Ein-Zyklus-Cadd-Reset und bisheriger Salary-Jahr-4-Repricingmechanik ausdrücklich als Versionenvergleich behandeln. Erstes reproduzierbar gefrorenes [CP6n-2027-Kohorten-Input](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6n-contract-cohort-inputs.json), Commit `e81cdea2d69c4f846373efad3d866e8e989935fd`, original CP6k-Source-Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`, CSV `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`. 2027 sechs synthetic legal cohorts mit Seed 11/29/47 und historisch modellierten 2027–2029 Markt-Cap-Verläufen, kein tatsächlicher 2027 Forecast. Analyseskript, Dokument und CI/PR-Review sind noch offen. Keine aktiven Regeln geändert.


**CP6n-Simulator (22.11.2026):** Standalone [cp6n_market_cap_contract_guarantee_stress.mjs](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6n_market_cap_contract_guarantee_stress.mjs) Commit `e778a459cabba37d29cc5381363db0b1de3c3743`. Liest gefrorenes 2027er CP6k-Kohorten-Input und testet 3 Seeds × Veteran-Staffeln 100/100/100, 100/105/110, 100/110/120 × synthetische Markt-Cap-Schocks 0/−10/−20% × Jahre 2027–29, Rookie Staffel 100/125/150 bleibt. Getrennte Owner-Überhänge/aggregierte Liga-Kapazität/Unmöglichkeit bei voll garantierten unverkäuflichen Verpflichtungen; keine neuen Rookies-/FA-Verträge 2028/29, keine echte Marktwert-/Contract-Ledger-Pipeline oder Markttransaktionen. Ausführung, Bericht und CI noch offen. Nur Forschung, nicht produktiv.


**CP6n 27-Szenario-Stressauswertung (22.11.2026):** [Audit-Metriken](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6n-contract-cap-stress-metrics.json) Commit `ae5413e15a2f862540b121b2efe05816a148568b`, Input Blob `679b7994d6a88ac506beb3e886686e5d0cd19e25`, Script Blob `dd4d3a1614343b20115afad9763e035cd473ef9c`. Genau **27** Szenarien × 2027/2028/2029 = 81 Jahreszustände, 23 mit **globalen Verpflichtungen > 6×TeamCap** bei 100 % Garantien und keinem Käufer/Offset, 154 einzelne Team-Jahr-Overcap-Vorfälle (nicht unabhängige Sportdaten). Seed11, Veteranenvertrag 100/110/120 und 20 %-Cap-Absenkung: 2029 fünf Teams über Cap und **490,405 Mio. $** aggregatbezogene harte Unterdeckung, Seeds29/47 ~550,250/~542,356 Mio. $. Diese Schocks hypothetisch; Rookie 100/125/150 erhalten. Tests auf kumulative Kosten, Cap-Gap, gemeinsame 2027 legal, CP6k-2027-29-Cap und Team0-2027-Budget validiert. Kein echter allseitiger Markt-/Contract-/Cut-/Garantie-Mehrjahres-Simulator, nicht als Ligabeschluss. Bericht folgt, CI noch offen.


**CP6n Designabgleich/Nordstern (22.11.2026):** [Vollständiger CP6n-Forschungsbericht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6n-three-year-contract-market-cap-design.md), Commit `213304e28afeb63ea63c8d4e14a029166ad65f9c`. Neues Drei-Jahres-Contract/MarketValue-Modell **als eigenständiger, unratifizierter Kandidat** mit alten Konzepten (CP6k, CP6m, CP6l, Rookie 100/125/150, C-add/Reset) verglichen; sechs Nordstern-Ziele und fünf Finanzierungsachsen, 27-Szenario-/81-Year-Stresstest dokumentiert. **Wichtig**: CP6k-Top120 hat 2027 ca. 11 % und 2029 ca. 14–15 % Rookie-Contract-basierte Preise, nicht strikt Marktwert; echtes duales Marktwert-/ContractSalary-Produkt benötigt vor Modellentscheid getrennte Rookie-Marktwertdefinition und contract-ledger. Hard insolvency bei 100%-Guarantees, Market-Cap-Schock, Cut ohne wirksame Garantie-Reduktion mathematisch möglich. Keine Änderung der kanonischen bestehenden Konzepte oder aktiven Ligaregeln; Pipeline/Year4/Claim/Cut-/Trade-Semantik noch nicht implementiert oder ratifiziert.


**CP6n Research Index (22.11.2026):** Salary Research README verlinkt CP6n Bericht, V8/Node-Stresstest, archivierte 2027er sechsfachen Kohortendaten und Audit-Szenarien; Commit `4539ee1867d44815df24f77ce44e9950818ca4d6`. Nächste Entscheidung: Garantie/Offset/Claim/ContractYear definieren und echten MarketValue von Rookie-ContractSalary entkoppeln, vor 5Y-Markt-Trade-Simulation. Keine Änderung aktiver Regeln.


**CP6n PR-/CI-Handoff (22.11.2026):** [PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) Draft/open, HEAD `4539ee1867d44815df24f77ce44e9950818ca4d6`, 3Y Contract/MarketValue-Stresstest + 6 Nordstern-Ziele dokumentiert; `CI • Repository Validation` zuletzt `queued` (nicht als bestandene CI nennen, solange status != success). **V8-Berechnung 27×3 mit Budget-/Ledger-Invarianten erfolgreich**; unabhängige CLI-/vollständige dynamische Vertragswelt-/Markt-Abnahme noch nicht erfolgt. Design-Gates: Veteran-Y2/Y3-Skalierung, Garantie/Offset, zwei 14-Tage-Uhren, Marktwert Rookie Year2/3, Buyer-Cap, reale 30/5/2-Roster und 6-Team-Markt mit Deadline/HardFailure. Kein Merge, keine aktive Ligaregel.


**CP6o 100/50/25 Guarantee-Cut Recovery (22.11.2026):** Neue [CP6o sechs-Team-Contract/DeadCap/Cut-/FA-Recovery-Forschungssimulation](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6o_guaranteed_cut_recovery.mjs), Commit `cb99c1a9b72de80ffe94f40c29d35368be2f3c88`. Grundlage gefrorene CP6k-Engine-Quelle `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`; 2027 legale 6-Team-Kader, 2028/29 fünf Rookie-Draft-Signings pro Team, danach freiwillige Cuts und aus dem echten Pool der synthetischen Welt gewählte unowned FA-Replacements. Kontraktgewährleistung 100/50/25 vs volle 100/100/100; Veteranenstaffeln und Cap-Schocks wie CP6n; Dead-Cap-Year-Vintages, alle Teams und Positionen, no-claim/Trade explizit. **Ausführung, Fehlerprüfung und Resultatbericht noch nicht abgeschlossen**; keine aktive Regeländerung.


**CP6o Suchkosten-Checkpoint (22.11.2026):** [CP6o Recovery-Simulator](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6o_guaranteed_cut_recovery.mjs) in Commit `515e691332ee7b0b45a15732cf12c0eae700d68e` für seriöse, begrenzte FA-Suche optimiert. Vorheriger Seed11 schwerster CP6n-Stress mit Rookie-Draft 2028/29: 100/50/25 brachte 2028 und 2029 alle 6 Teamkader unter Cap nach 67+11 Cuts und 26 FA-Signings, 100%-Vollgarantie strukturell unmöglich schon 2028 (ca. 402,6 Mio. $ Nettounterdeckung); heuristische Kandidatenpräferenz nach Suchoptimierung erneut zu berechnen. Keine echten 2027 Ergebnisse, Käufer/Claims, tatsächlichen Roster-/IR/Taxi-Regeln oder optimales Liga-Gleichgewicht. Kein produktiver Regelsatz geändert.


**CP6o Seed11 all 18 scenarios (22.11.2026):** [Seed11 Recovery-Audit](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6o-seed11-guarantee-recovery.json), Commit `164198d4611a672624ef471eb65e2bb4b1236b95`, Simulator Blob `3480ae90191051c13b108642f6da508c059cc1bc`: alle 9 Rookie-100/125/150 + Garantie-100/50/25 Varianten über 2027–29 mit 6 legalen Kadern im 2028/29-Settlement bestanden, über 9 Sensitivitäten zusammen 417 Cuts, 102 FA-Replacements (NICHT unabhängige Trades), 5 Rookie-Draftverträge pro Team in jedem 2028/29. Full 100/100/100 Garantien **0/9** ohne reale Buyer-/Claim-Möglichkeit vollständig legal; bei nicht geschockten Szenarien auch individualisierter Buyer-Mangel/retirement ohne Annahme, nicht automatisch globale Deckungslücke. 2027 Cap und Owner0..5-Salary identisch zum CP6n 2027 Input; jede legale Roster-Abdeckung, ID-Eindeutigkeit, Cut-Nettoentlastung validiert. Seeds29/47, vollständiger Bericht, CI noch offen. Draft-Projektion benutzt synthetische Scout-Werte, keine NFL 2027 Ergebnisse.


**CP6o Seed29 all 18 scenarios (22.11.2026):** [Seed29 Recovery-Audit](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6o-seed29-guarantee-recovery.json), Commit `478aed7cc2744edbe80302fa23135827f024a3fc`. Alle neun 100/50/25-Szenarien unter heuristischer Cut+FA-Recovery bis 2029 6/6 legal (über 9 Szenarien insgesamt 470 Cuts +116 Replacements, **keine** unabhängigen Ligawirklichkeiten); alle 9 Vollgarantie-Szenarien ohne Buyer/Claim-Pfad 2028 nicht legalisiert. Harter Fall 100/110/120 und -20% Markt: 83 Cuts, 35 FA-Replacements bis 2029; 2029 413,661 Mio. $ zeitjahresbezogener Dead Cap. 2027 6-Team-Cap/Salaries gegen CP6n validiert, Cut/Team-Legalitäten geprüft. Seed47 und Berichts-/CI-Abnahme offen.


**CP6o Seed47 alle 18 Szenarien (22.11.2026):** [Seed47 Recovery-Audit](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6o-seed47-guarantee-recovery.json), Commit `5517ff2046a444b55bd5d779bc55cf5d0be93269`. Alle 9 100/50/25-Szenarien über 2028/29 mit legalen sechsfachen Roster-/Cap-Endständen (9 Pfade zusammen 443 Cuts/110 aus unowned Pool signierte Replacements); alle 9 Full 100/100/100 im no-buyer-Gegenfaktum bei 2028 nicht vollständig legal. Im harten Fall 100/110/120 und -20% zusätzlichem Marktcap 81 Cuts, 32 Replacements, 2029 365,567 Mio. $ Dead Cap. CP6n Owner0..5 2027 genau abgeglichen; Cut-/Rosterslot-/Owner-Duplicate-/Budgetprüfungen bestanden. Zusammen 3 Seeds × 3 Sal-Staffeln × 3 Marktshocks × 2 Garantievarianten = 54 Pfade vorhanden. Berichts-/CI-Review folgt; kein Ligabeschluss.


**CP6o Vollständiger Analysebericht (22.11.2026):** [CP6o 100/50/25-Cuts, Dead-Cap und sechsfacher Ersatzspieler-Markt](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6o-100-50-25-cuts-and-deadcap.md), Commit `36c25f565646f3ab23b35caf4f04681b2e3858ea`. Drei Seeds 11/29/47 × 3 Veteranenstaffeln × 3 Marktschocks × 2 Garantien =54 Pfade; Teilgarantie 100/50/25 in **27/27** 2028/2029 sechsfach Cap- und Research-20er/13er-Positionsdeckungs-konform, Vollgarantie 100/100/100 ohne echte Buyer/Claim in **0/27** bis 2029 vollständig legal. Über 27 **alternative** Teilgarantiepfade: 1.330 modellierte Cuts und 328 bezahlte FA-Replacements, 60 neue Draftverträge pro vollständigem Pfad (30×2028 +30×2029). Hartes Fallpaar slope10%/Markt−20%: **79/83/81 Cuts**, 2029 fälliger Dead Cap **376,7/413,7/365,6 Mio. $** nach 2028/29 Legacy-Zuweisung. Seed11 2028 teilw. sportliche Starterindexverluste −56,0/−57,9 statt kostenfreie Bereinigung. Vollgarantie-Mildfall 2028 nur einzelner Owner 1,2/14,1/5,1 Mio $ über Cap bei **keiner globalen Pflichtlücke** – strikte fehlende Käuferliquidität != mathematische Gesamtliga-Insolvenz. Definierte 2027-29 synthetische Welt, CP6k-Price enthält noch Rookie-Contract-Komponenten, keine echte Markt-/Contract-Entkopplung, keine realen NFL-2027 Daten oder echten Claims/Trades. Der Bericht enthält sechs geschützte Nordstern-Ziele und 5 Finanzachsen. Aktive Liga- und kanonische Rookie-/C-add-Regeln unverändert; PR Draft, CI offen.


**CP6o Research README/Index (22.11.2026):** CP6o [Analysedokument](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6o-100-50-25-cuts-and-deadcap.md) plus ausführbare Source/Seed-11/29/47-Audits im [Salary README](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/README.md) indexiert. Commit `f6090599aaad92a4e4e81e8757e41688ba6e5ec6`; PR #1576 Handoff/CI-Abnahme noch ausstehend. Keine Änderung der aktiven Regeln.


**CP6o Draft-PR-/Audit-Handoff (22.11.2026):** [Draft-PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) aktualisiert, HEAD `f6090599aaad92a4e4e81e8757e41688ba6e5ec6`, alle CP6o 3 Seed-Detailaudits und vollständige Vergleichsdokumentation indexiert. **Ex-post drei Seed-Ausgaben unabhängig gegen CP6n exogene Markt-Cap-Jahre erneut validiert: 54 Szenarien, 135 Cap-Jahresvergleiche, 1.349 Cut-Netto-Buchungschecks, 27/27 Carry-Checks aus 2028er bis zu 2029er DeadCap ohne Abweichungen**. 100/50/25 27/27, Vollgarantie ohne Käufer 0/27; **keine echte Trade-/Claim-/Slate-/30er/Taxi/IR- oder 2030+ Vollsimulation**. CI • Repository Validation für HEAD `f6090599aaad92a4e4e81e8757e41688ba6e5ec6` **completed/success** (22.11.2026); dedizierte vollständige Node-CLI-/Solver-Sport-/Handelsvalidierung noch offen. Forschung only, no Merge/aktive Regeln.


**CP6p mature vintages – Seed11 (22.11.2026):** [12 Fünfjahres-Vertragsvarianten, Seed11](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-seed11-mature-contracts.json), Commit `7cf0168ca5a0ec622c2e6a1b64f10cc81b76698a`. Gegenfaktisch **2027 bereits drei Vertragsjahrgänge** (45 Start 2025, 45 Start 2026, 58 Start 2027), alte Rookies anhand Player.Year, Veteranenvintages deterministisch verteilt, 2027 alle 6 Teams exakt gegen CP6n-Roster-Salaries und Cap abgeglichen. 2028–2031 jährliche Draftklasse (5 Picks/Team), ggf. **kostenloses Nichtverlängern auslaufender Verträge** oder neuen 3Y-Vertrag zum aktuellen Markt, Cut mit garantierten Restjahreskosten, legaler Roster/Cap-Check; Rookie-Teilgarantie vs 100%-Garantie, Veteran 100/110/120 vs 100/125/150, Market shock 0/−10/−20%. Seed11 12/12 Cap-Legalität, **nicht** globale Modellbestätigung; kein echter 2025/26 Contract-Konsens/Owner-Entscheid und keine Alt-DeadCaps erfunden. Hard shock: Teilrookie 65/86 garantierte Cuts bei 10/25% Veteranen-Eskalation, Rookies voll 31/49 cuts, dafür mehr kostenfreies Expiry-Declines 73/74. Wichtig keine scheinbar gratis Käufer. Script + weitere Seeds/Handoff offen.


**CP6p mature vintages – Seed29 (22.11.2026):** [Seed29-Audit, 12 Fünfjahrespfade](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-seed29-mature-contracts.json) Commit `996287ee19b6f0bc2d95fee41cf0ccfba0821bbb`, 2027 Vertragsjahrgänge 45/49/54 aus 2025/26/27. Alle 12 Pfade 2027–31 unter den CP6k 20–40/13-Starter-Rechercheconstraints mit echter zusätzlicher jährlicher Rookie-Draft, kostenlosem nicht signierten Expiration-Decline, Cap-gebundenem Re-Sign und garantierten mehrjährigen Cut-Kosten legal. Veteran 100/110/120 vs 100/125/150 und Rookie-Garantie 100/50/25 vs 100/100/100, Cap 0/−10/−20% im Folgejahr mit Feedback in Rookie-Dollaranker; marktwerttechnischer Vorbehalt und konterfaktische Vintage-Synthese unverändert. Seed47 folgt. Keine produktiven Änderungen.


**CP6p mature vintages – Seed47 (22.11.2026):** [Seed47-Audit, zwölf weitere 2027–31-Mature-Contract-Pfade](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-seed47-mature-contracts.json) Commit `a45ae344f0b98dd920a21cb63abd011caf8d2081`. Gegenfaktisch 53/40/55 Vertragsjahrgänge aus 2025/26/27. Alle 12 unter 20–40 Research-Positionsdeckungsmodell legal; harte Variante Veteran 100/125/150 + Rookie 100/50/25 => 61 garantierte Cuts, Rookie voll => 45 Cuts, aber mehr expired nonrenewals. 2027 Besitzer-Salaries und Cap gegen 2027 CP6n exakt geprüft. Zusammen alle **36 Fünfjahrespfade** über 3 Seeds × Veteraneskalation 10/25% × Rookiegarantie partiell/voll × 0/−10/−20%-Cap-Schocks gelaufen; jetzt Synthese/QA/CI und Handoff. Kein Ligabeschluss.


**CP6p Full Five-Year Mature-Ledger Design-/Results Review (22.11.2026):** [CP6p Fachbericht](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-mature-vintages-rookie-guarantee-and-125-150.md), Commit `a1b2c4aa9716e14b6ead1a66c1065f2d83a6ef46` plus [kompakte 36-Pfade-Summary](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-mature-vintage-summary.json) Commit `50a02094eeea6d5c6f0112596b1e92a8dd94e178`, vollständige Seed 11/29/47-JSON-Audits. **2027 Vertragseinstiegsjahrgänge synthetisch 2025/26/27 statt alle 2027 neu**, Veteranen-Ladder 100/110/120 vs 100/125/150; Rookie Salary fest 100/125/150, Rookie Garantie 100/50/25 vs 100/100/100, Veteranen in beiden Fällen Garantie 100/50/25. Alle **36/36** 2027–31 Fünfjahres-Szenarien mit jährlichen 30 Rookie-Verpflichtungen, Cap-Schocks 0/-10/-20%, korrekter DeadCap-Vintage pro Cut und kostenlosem Nichtverlängern zur Deadline 6/6 legal. Je 9 alternative Seed/Cap-Pfade: Veteran 110/120, Rookie-P: 435 Cuts +397 Nichtverlängerungen, Rookie-F:243 Cuts+591 Nichtverlängerungen; Veteran 125/150 Rookie-P:576 Cuts+384 Nichtverlängerungen, Rookie-F:386 Cuts+577 Nichtverlängerungen. **Nicht direkt als 9× reale 6er-Liga interpretieren.** Hartes Szenario 125/150 +−20% zeigt Team0 2031 Starterindex Seed11/29/47 für Rookie-P 175,24/170,93/167,06 vs Full 165,13/173,14/167,31 — kein pauschaler Winner Rookie-Garantie. **Kritischer Reality Gate:** vor 2027 keine wirklichen historischen Vertragsschlüsse/Alt-Deadcap-Daten in neuer Regelwelt, Veteranen-Signing-Preise 2025/26 rückwärts aus 2027 Kosten abgeleitet und 2027er Kader nicht Vertragsaware gebaut; CP6k Marktindex enthält Rookie-Vertragspreise, nicht unabhängig berechneten Rookie-Year2/3-Marktwert; realer 30+IR+Taxi-Ligavollzug und echte Trades/Claims fehlen. 720 zusätzliche quergeprüfte 6-Team-/Cap-/DeadCap-Assertions bestanden, CI/PR noch in Abnahme. Keine aktive Salary-Regel geändert.


**CP6p Research-Index (22.11.2026):** CP6p Fachvergleich und alle 3 vollständigen Seed-Audits + kompakte 36-Szenario-Zusammenfassung im [Salary Research README](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/README.md) indexiert, Commit `ed494309f08f532b7f4d66bb8211cd02c1a376a7`. Draft PR #1576 Handoff folgt; active rules unchanged.


**CP6p PR-/CI-Handoff 22.11.2026:** [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576) Head `ed494309f08f532b7f4d66bb8211cd02c1a376a7`; CP6p mature contract 36 five-year scenarios and 720 2028–31 financial/roster/DeadCap assertions checked, [full report](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-mature-vintages-rookie-guarantee-and-125-150.md), [summary](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/analyses/2026-11-22-cp6p-mature-vintage-summary.json), [script](https://github.com/Lolindhir/fantasy-app/blob/research/1344-cp6i-starter-ceiling-20261119/fantasy-management/league-economy/salary/simulation/cp6p_mature_vintage_contracts.mjs); CI • Repository Validation zuletzt `success` for head. Kein Merge, keine aktive Ligaregel, Trade-/Claim-Markt und echte 2025/26 Vertragsentscheidungen offen.
