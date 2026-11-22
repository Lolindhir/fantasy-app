# CP6r – 45er-Kader als Forschungsbasis: bewusste Franchise-Strategien und bilateraler Spielervertragsmarkt (Pilot)

> **22.11.2026, Forschung / Pilot-Checkpoint zu [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) auf [Draft PR #1576](https://github.com/Lolindhir/fantasy-app/pull/1576).** Keine Änderung an produktiven Liga-/Salary-/Sleeper-Regeln oder den sechs geschützten Nordsternzielen.

## 1. Fortführungsentscheidung: 45 als feste Base, nicht als beschlossenes Ligaformat

Nach [CP6q](2026-11-22-cp6q-round-guarantees-capacity.md) wird ab CP6r **45 reguläre Plätze als einheitliche Research-Basis** verwendet: keine Taxi-Sonderplätze; jeder gehaltene Spieler zählt mit vollem aktiven Vertragsgehalt gegen den Cap, zusätzlich bleibt die abgerechnete Dead Cap fällig. Die Option 45 ist ein von Robert bestätigter *Forschungsfokus*, keine verbindliche Umstellung der heute aktiven 30 regulären + fünf IR + zwei Taxi-Slots auf Sleeper. CP6q fand 46 erzwungene Draft-Cuts bei 40 Slots über 54 alternative Pfade, keine bei 45 und keine zusätzliche Wirkung von 50 in seinen simulierten Greedy-Welten.

Für den reinen Pilot gelten aus Rechenpragmatik **45 maximale und 20 minimale reguläre Spieler**, 13 Starter, keine Taxi/IR-Mechanik; fünf Runden und fünf automatische Rookie-Auswahlen pro Team und Saison, vor- und nachgelagertes Cap-Settlement. Später muss die tatsächliche IR-/Reserve-Behandlung und das Verhältnis eines harten Sleeper-Maximums zu frei belegbaren Plätzen geprüft werden.

## 2. Vertragspolitik und Agentenprofile

- Rookie-Dollarverträge für drei Jahre **100/125/150 %** vom **tatsächlich bei Draft-Auswahl festgesetzten Year1-Dollarpreis**; 65 % Liga-Fantasy-Pick-Kurve +35 % bereinigter NFL-Draft-Rang. Garantie: Fantasy-R1/2 **100/100/100**, R3/4 **100/100/50**, R5/Undrafted **100/50/25**. Unbekannte Alt-2025/26-Rookie-Draftrunden werden nicht rückwirkend erfunden und erhalten Teilgarantie.
- Veteranen-Vertragsbasis im ausgeführten Pilot **100/125/150 %**, Garantien **100/50/25**; das laufende Jahr und vorab vertraglich bestimmte Folgejahre werden pro Spieler abgerechnet. Nach drei Jahren kostet Nichtverlängerung 0 Dead Cap. Referenz-Cap aus jährlichem Top120-Markt/6; im zweiten Seed −20 % Marktschock ab 2028.
- Sechs Proxy-Owner (0/4 **All-in**, 1/5 **Rebuild**, 2 **Reload**, 3 **Flex**): Die Stilprofile verändern im Pilot bewusst die Rookie-Draft-Rangfolge und die beidseitigen Trade-Nutzenfunktionen (aktuelle Starterstärke, bekannte Rookie-/Youth-Option, Kader-Tiefe, laufende/vertraglich bekannte Zukunftskosten und Cap-Reserve). **Das ist noch kein voll strategisch konsistenter Mehrjahresmanager:** Die bisherigen Salary-Settlement-, Extension- und FA-Greedy-Algorithmen bleiben weitgehend gleich; es gibt kein echtes 2025–27-Burn-in mit früher intentional gewählten All-in-/Rebuild-Verträgen.
- Handelskandidat **nur einfacher gleichzeitiger 1:1-Spielervertragstausch** unter real bereits besessenen Spielern. Beide Teams müssen nach allen betroffenen Cap- und Positionsprüfungen legal sein. Beide Proxy-Nutzen müssen *positiv* steigen. Bestehende Vertragsjahre, Garantien und Salaries werden **ohne Neu-Signatur** auf das Käuferteam übertragen. Alte Cut-Dead-Cap-Vintages verbleiben beim jeweiligen ursprünglichen Schuldner. Kein neu entstehender Dead Cap durch den Trade, keine Retained Salary und kein Debt/Borrowing. Pro Team im Pilot maximal ein Trade je jährlicher Markt-Runde, insgesamt höchstens drei ligaweite Trades pro Jahr. Es gibt **keine echten Managerangebote oder Consent-Daten**.
- Als gepaarte Kontrollwelt wird dieselbe Welt mit *abgeschaltetem Trade-Markt* ausgeführt. Bei gleicher Startwelt und gleichen exogenen NFL-Synthetikpfaden dürfen spätere Marktpreise und Drafts aufgrund verschiedener Besitzer und Entscheidungen endogen divergieren.

## 3. Ausgeführte und gespeicherte Experimente

[Ausführbarer CP6r-Simulator](../simulation/cp6r_45slot_trade_strategy.mjs), auf [CP6q](../simulation/cp6q_round_guarantees_capacity.mjs) aufbauend; Oktober-2026-CSV mit 1.268 historischen Spieler-Zeilen (Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`), spätere sportliche Entwicklung **synthetisch**.

Gepaarte vollständige Fünfjahrespfade je Welt:

| Ausgangs-Seed | Cap-Stress 2028–31 | Legal (ohne/mit Markt) | Hypothetisch akzeptierte Trades 2028–31 | Team0-Starterindex 2031 ohne → mit | 2031er Ligaspanne ohne → mit |
|---:|---|---:|---:|---:|---:|
| 11 | 0 % | 2/2 | 8 | 182.93 → 187.85 (+4.92) | 27.63 → 30.12 |
| 29 | −20 % | 2/2 | 8 | 166.42 → 172.17 (+5.75) | 9.31 → 18.14 |

**Validierungsumfang:** **4/4 intern legale** 2027–31-Simulationspfade (2 kontrastierende Preis-/Seed-Welten × [ohne/mit Handel]), **120 Teamjahre**, je Pfad 120 neu gedraftete Rookie-Verträge über 2028–31, **16** akzeptierte hypothetische 1:1-Deals. Jeder Deal ist samt beide Owner-IDs, beider konkreter Spieler-IDs, zwei realen aktuellen Vertrags-Salaries, vor/nach Cap, voller künftiger Vertragszahlung, Netto-Entlastung, finalem Kader und Starterindex in den verlinkten JSON-Daten auditiert. Alle 16 Geld-/Owner-/Nullsummen-Invarianten bestanden. Die 2027er Teams und Caps sind jeweils zwischen Handels- und Nullmarktwelt exakt gleich, **nicht** zwingend zwischen unterschiedlichen Seeds.

Details:
- [Seed 11, kein Cap-Schock](2026-11-22-cp6r-seed11-vet125-unshocked-trade-pair.json)
- [Seed 29, −20 % Cap-Stress](2026-11-22-cp6r-seed29-vet125-shock20-trade-pair.json)
- [Pilot-Übersicht als JSON](2026-11-22-cp6r-pilot-overview.json)

### 3.1 Warum „Team 0 gewinnt“ kein Trade-Markt-Beweis ist

Team 0 ist in beiden Pfaden ein **All-in-Proxy**, kein echter Owner. Er steigert den 2031er Starterindex um 4.92 bzw. 5.75 Punkte, **während die Liga-Spanne zwischen stärkstem und schwächstem Team in beiden Fällen wächst** (27.63→30.12 und 9.31→18.14). Ein beidseitig *ex ante* rationaler Trade kann die später realisierte Teamkonkurrenz verstärken oder die Spanne vergrößern. Das verletzt die sechs Nordstern-Ziele nicht automatisch, ist aber ein **Hard Gate** gegen eine voreilige Aussage, das Modell erzeuge Chancengleichheit.

Im Seed 11 schwanken die Team-0-Indexeffekte über die Jahre: 2028 positiv, 2029 negativ, 2030 und 2031 positiv. **Ein Endindex allein** erklärt All-in-Fenster und realisierte Folgekosten nicht. Hier wurden weder Titelchancen noch die konkrete 4-von-6-Playoffwahrscheinlichkeit modelliert.

### 3.2 Beispiel eines vollständigen Vertragstauschs

2028 Seed 11: Das synthetische **Rebuild-Team 1** tauscht einen Veteranen mit **68.445.886 $** Jahres-Salary gegen einen Rookie-Vertrag mit **5.987.186 $** des synthetischen **All-in-Teams 4**. Rebuild erhält **62.458.700 $** Netto-Cap-Freiraum im aktuellen Jahr; All-in bindet denselben Mehrbetrag. 2029/30 gehen die noch offenen Vertragszahlungen der beiden Spieler an die jeweiligen neuen Owner; kein Cut, keine neuen Dead-Cap-Vintages. Dieser konkrete Tausch ist mathematisch und unter dem gewählten Nutzenmodell möglich, aber **kein Beleg**, dass menschliche Owner denselben Deal zum selben Gegenwert anbieten würden. Es fehlen insbesondere Future Picks, Tauschpakete und echte Verhandlungen.

## 4. Fünf Finanzierungsachsen (Pflichtdisclosure)

1. **Seller Relief:** Innerhalb jedes 1:1-Pakets sind voller abgegebener Salary, empfangener Salary, Netto-Cap-Gewinn und vertragliche Folgejahr-Gesamtbelastung des abgebenden Owners belegt; Cuts und kostenlose Nichtverlängerungen werden getrennt geführt. **Keine Retained Salary** in diesem Pilot.
2. **Buyer Burden:** Dieselbe Transaktion wird für den Käufer mit dem **ganzen** neuen Vertrags-Salary inklusive zukünftiger vertraglicher Zahlungen geprüft, nicht bloß dessen isoliertem Spielerwert. Beide Owners erfüllen den aktuellen Cap. Kein echter Marktpreis/Manager-Consent, keine Mehrspieler- oder Future-Pick-Kombination; spätere Cap-Werte noch nicht garantiert finanzierbar.
3. **Roster Capacity:** 45/20 reguläres Forschungs-Max/Min, 13 Starter/Positionsdeckung, disjunkte Ownerships, 1:1 ohne Kapazitätserhöhung, nach Marktbewegung vollständige Legality-Prüfung. Keine Taxi-/Reserve-/IR-/Real-Sleeper-Mechanik.
4. **League-wide Debt:** Alle Trades sind Salary-Umverteilungen mit unveränderter ligaweiter Summe im Handelsmoment, ohne neue Deal-Dead-Cap/Retention/Debt. Bereits angesammelte Dead-Cap-Schulden bleiben beim ursprünglichen Owner; pro Year und Owner im Ledger. **Kein Käufer-Borrowing und keine verschobene Schuldenlast** in diesem begrenzten Trade-Modell.
5. **Future Repayment:** Vertragliche 2029/30/31+ Zahlungen werden mitgeführt; jährliche Folgebudgetprüfungen 2027–31 unter realisiertem synthetischem Cap durchgeführt. **Ein isolierter Deal beweist keine zukünftige Cap-Finanzierbarkeit im nächsten Schockjahr**; der Agent muss danach ggf. andere Spieler cutten/nicht verlängern. Keine Debt-Kreditaufnahme/Refinanzierung, keine 2032–34-Nachhaltigkeitsprognose.

## 5. Sechs geschützte Nordstern-Ziele: vorläufiges Urteil

1. **Langfristige Aufholbarkeit:** **Nicht bewiesen**; in beiden Piloten wächst sogar die finale Liga-Indizes-Spanne. Mehr Seeds, andere Rollenverteilungen, intentionaler Rebuild und Titelpfade erforderlich.
2. **Gutes Management belohnen:** Das Proxy-Modell erzeugt freiwillige gegenseitig positive Trade-Entscheidungen, erlaubt aber keine Bewertung tatsächlichen Managerwissens, Risk Assessment oder langfristig stabiler Qualität.
3. **Keine unverdiente ewig zementierte Dominanz:** Mehrjährige Gehaltskosten werden übernommen und Expiries sind real im Rechenmodell; die echte Dauer eines Vorteilsmoments unter guten Mitmanagern wurde nicht nachgewiesen.
4. **Wirtschaftliche Folgekosten:** Durchgängige Full-Salary-Anrechnung, die Übernahme ganzer Vintage-Kosten und garantierte Rookie-Verpflichtungen erzeugen Opportunitätskosten; reale Buyer-Liquidität fehlt.
5. **Strategische Wege:** Es gibt sinnvolle divergente Pilot-Nutzenfunktionen und tatsächlich zustande gekommene 1:1-Trades. Ein echter All-in-/Reload-/Rebuild-/Flex-Zyklus mit konsistenten mehrjährigen Drafts, Vertragsneuverhandlungen, Cut-/Pick-Markt und bewusstem Championship-Window fehlt.
6. **Operative Durchsetzung:** Vertragstransfer lässt sich mit exakten Owner-ID-/Player-ID-/Contract-ID- und Cap-Buchungen auditieren. Aber auch hier sind Sleeper-Ausführbarkeit, Eigentumsstichtage, UDFAs, IR/Lock, Trade-Batch-Settlement und Commissionersanktions-/Appeal-Verfahren offen.

## 6. Nächste Untersuchung – nicht als aktive Regel implementieren

**45 ist für die nächste Forschungsphase die Basis.** CP6r ist ein erster reproduzierbarer *Existenztest* für cap-legale kontraktübertragende bilaterale Deals, **keine fertige Marktgleichgewichtsstudie**. Die nächsten Prüf-Gates sind:
- Vergleich derselben Seeds für 100/110/120-Veteranen und zusätzliche Schocks/Phasen; höhere Zahl unterschiedlicher synthetischer NFL-Startkohorten;
- 2025–27 echtes vertrags- und pick-sensitives Burn-in anstatt rückgerechneter Jahrgänge; explizite per Team gewählte All-in, Reload, Rebuild, Flex-Policies über Verlängerungen, Cuts, FA, Picks, Trade-Timing;
- vor einem notwendigen Cut **Trade-Alternative** inklusive Buyer, realistischen Bundles, Pick-Zahlungen/Assetwert, Kauf/Verkauf von Zukunftskapazität und optionaler retained salary;
- Abgrenzung IR/Reserve nach Taxi-Abschaffung, harte Sleeper-Deadline-/Simultan-Transaktionsregeln;
- unabhängiger Node-/CI-Lauf, Datenschutz/Promotions-/Rookie-Provenienz-Prüfungen, tatsächliche Commissioner-Minuten und eventueller unheilbarer Cap-Verstoß. Keine automatischen Sanktionen oder unilateralen Cuts erfinden.

**Kein Merge, kein aktives Salary-/Cap-/Roster-Update.** CP6r bleibt im zentralen Issue #1344 und dem vorhandenen Draft PR #1576.
