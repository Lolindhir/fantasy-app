# CP6n – Drei-Jahres-Verträge, Rookie-Eskalation und marktwertabhängiges Cap: Variantenabgleich und Stresstest

> **22.11.2026 · Issue [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · Forschungsstand, keine aktive oder ratifizierte Ligaregel.** Neuer Nutzerimpuls: alle neu aufgenommenen Spieler sollen mit klaren drei League-Season-Jahren und übertragenem Vertrag verpflichten; die Rookie-Staffel **100/125/150 % bleibt**; Veteranenverträge könnten ebenfalls eine **vorab bezifferte, nicht kumulativ steigende Staffel** erhalten. Der **jährliche Marktwert** soll vom Vertrag unabhängig weiterbestehen und die Top120-basierte Cap-Höhe bestimmen, auch wenn sich die Leistungslandschaft verschlechtert. Zu prüfen sind Markt-Cap-Risiko, Garantien, veräußerbare Verträge, 14-Tage-Claim/Grace und alle sechs geschützten [Nordstern-Ziele](../../../league-context/league-philosophy.md). Dokumentiert wird die Hypothese **als eigenständiger Kandidat**, nicht als stillschweigende Revision der bisherigen Rookie-/Dead-Cap-Konzeptentscheidung.

## 1. Abgleich der verbindlichen Quellen und Trennung der Varianten

| Mechanik | Gegenwärtiges aktives Ist 2026 | Bisheriger konzeptioneller Full-Salary-/Rookie-/Dead-Cap-Kandidat | Neues CP6n-Vertragsmodell (nicht entschieden) |
|---|---|---|---|
| Cap und Prüfungen | Ein Offseason-Cap-Check, top 20 der gehaltenen Salaries, Cap-Faktor 0,90; unterjährig Cap-Überhang regelkonform | Forschungsvergleich A/F2/F3/B, all-held Full Salary und Top120/6-Faktor 1,0 **nur Hypothese** | Full-Salary-Belastung als Basiskandidat; permanentes Cap, F2 und jährlicher Check weiter **separat** testen |
| Marktpreis | Performance Salary und bisherige Cap-Formel | 3Y-geglättete Performance, rank-basierte Criticality, `k=1,5`, gleitendes Minimum, jährliches Veteranen-Repricing | **Marktwert** weiter jährlich nach derselben Methode neu berechnen, aber separat speichern |
| Veteran Vertrag | Kein neu signierter drei-jähriger, fixierter Salary-/Garantievertrag als aktive Liga-Regel | Jährliches Veteranen-Salary ist gleichzeitig Preis und Kosten | Bei Signierung **eigener dreijähriger Salary-Plan** zum damaligen Marktwert, z. B. 100/105/110 oder 100/110/120 %; keine automatische jährliche Änderung beim Besitzer |
| Rookie | Bisheriger Produktionspreis; neue Rookie-Vertragsregeln nicht ratifiziert | Bereits detailliert konzipiert: Year1 `65 % Fantasy Draft + 35 % NFL Draft`, Year2 `125 %`, Year3 `150 %` von **festem Year1-Dollarwert**, Year4 reguläres Performance Salary | **Diese Rookie-Staffel beibehalten**, drei feste Beträge; unabhängig davon separate künftige Marktwertzeitreihe definieren |
| Trade | Eigentümerwechsel unter Sleeper-Status | Marktwert-basiertes Salary bei aktuellem Owner; C-add ist **Cut**-Konzept, Trade != Cut | Neuer Owner übernimmt **unveränderte vollständige noch nicht abgelaufene künftige** ContractSchedule; **kein neuer 3Y-Reset** beim Trade |
| Cut | Kein neues mehrjähriges Guarantee-Ledger als produktive Regel | C-add: Retained Salary nach Tenure 50/30/15/5 %, **Reset am nächsten jährlichen Check**, kein fortlaufender Dead Cap | 14 Tage Claim zum unveränderten Vertrag; ohne Claim Restgarantie als Dead Cap **bis ursprünglichem Vertragsende**; Garantieprozentsatz/Offset offen |
| Cap-Deadline | Der einzig verbindliche offizielle Salary-Check | Jährlicher Reprice **aller** Salarywerte und Dead-Cap-Reset; zusätzliche F2/F3-Checks **kein** neuer Reset | **Market Value und Cap** jährlich neu; existierende ContractSchedules/Guarantees laufen dagegen **unabhängig** bis Fälligkeit weiter. Kein stiller Dead-Cap-Reset der Altverträge |

Quellen: [Salary-/Dead-Cap-Konzept](../salary-dead-cap-concept.md), [Performance Salary](../salary-system-redesign-concept.md), [CP6k](2026-11-19-cp6k-six-team-paired-5y.md), [CP6m](2026-11-20-cp6m-annual-vs-permanent-cap-decisions.md), [CP6l – Hypothetischer Cap-Kredit](2026-11-20-cp6l-allin-rebuild-capvorgriff.md), [Team Windows](../../team-window-strategy-concept.md). **CP6l H2/H3** ist ein ausdrücklich erwogenes, aber weder aktives noch notwendiges **Cap-Kreditkonto**; CP6n enthält dagegen **vertraglich zugesagte künftige Salary-Zahlungen**. Beide Obligationstypen niemals als dasselbe buchen. 6 Teams, 4 Playoff-Plätze und heute 30 normale Rosterplätze plus 5 Reserve-/2 Taxi-Plätze aus aktuellem `public/data/League.json`; 40 wäre eigener bisher unratifizierter Full-Salary-Kaderkandidat. Startgewichte von Rookie und Kritikalität bleiben unverändert.

## 2. Modellkern: getrennte Markt-/Kontrakt-Zeitreihen

Fachliches Rechenschema **als Vorschlag, nicht implementiert**:

```text
MarketValue(player,t)
  := jährliches, contract-unabhängiges 3Y-Performance/Criticality/Minimum-Mapping
     (Rookie-Marktwert auf Year 1–3 noch SEPARAT zu definieren)
LeagueCap(t)
  := sum(top120 MarketValue(player,t)) / 6 × Faktor
     (für CP6k Full-Salary-Kandidat Faktor 1.00)
ContractSalary(player,owner,t)
  := SignedBaseMarketValue(player,signingSeason) × ContractFactor(yearOfContract)
TeamCapUse(owner,t)
  := sum(ContractSalary of owned signed players)
   + sum(remaining Guaranteed Dead Cap due in t)
   + other explicitly authorized fees/retentions
```

Rookie `ContractFactor` 100/125/150 % in Y1/Y2/Y3 **bereits dokumentiert**, nicht neu beschlossen. Veteranenfaktoren in CP6n-Nebenrechnung `100/100/100`, `100/105/110`, `100/110/120`, jeweils exakt auf ursprünglichen Year1-Wert und kaufmännisch in ganzen Dollarbeträgen gerundet. **Nicht** jährlich kumulativ und **nicht** an neue aktuelle Marktwerte geknüpft. Ein schlechter werdender Spieler kann so einen weiterhin teuren Vertrag behalten; ein Star kann **unter seinem Marktwert** spielen und erst bei Vertragsende neu zu aktuellen Preisen angeboten werden.

**Technische zwingende Präzisierung:** Das bisherige `cp6k_six_team_paired_5y.mjs` bildet sein Top120-Cap aus `world.price`, das bei Year1–3-Rookies die **aktuelle Rookie-Vertragsstaffel** enthält. Das ist im alten Salary=Bewertung-Modell konsistent, aber **kein vom Vertrag unabhängiger Marktwert**. In den drei ausgeführten Seedwelten sind 2027 **21** Vertrags-Rookies unter den Top120 mit ca. **10,97–10,98 %** Top120-Dollaranteil; 2029 **24–26** mit ca. **14,04–15,12 %**. Für einen echten CP6n-Produktionskandidaten müssen entweder unabhängige `MarketValue`-Regeln auch für Rookies **erst spezifiziert** oder der Top120-Index bewusst als **gemischter** Performance-/Rookie-Preismaßstab dokumentiert werden. Ihn automatisch nur als „reiner Marktwert“ zu etikettieren wäre falsch. Die Folgeberechnung der Erfahrungsminima und Rookie-Year1 aus dem **Vorjahres-Cap** bleibt unabhängig davon ohne unmittelbare Gleichjahres-Zirkularität, braucht aber eine klar definierte Historienkette.

## 3. Ausgeführte dreijährige Markt-/Vertrags-Sensitivität

**Programm:** [`cp6n_market_cap_contract_guarantee_stress.mjs`](../simulation/cp6n_market_cap_contract_guarantee_stress.mjs). **Eingaben:** [gefrorene 2027er Kohorten](2026-11-22-cp6n-contract-cohort-inputs.json); **vollständige Auditdaten:** [Szenarioergebnisse JSON](2026-11-22-cp6n-contract-cap-stress-metrics.json).

### 3.1 Exakte Datengrundlage, methodische Grenzen

- Archivierter CP6k-Quell-Blob `8156fa0fdc7f8786ec78b27bc666e5ed94f72b8c`, CSV-Blob `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`, 1.268 archivierte Okt-2026-Spielerdatensätze, gleicher CP6k-Start: drei Seeds 11/29/47 × sechs **disjunkte** synthetische Teams; 30 gedraftete + 30 zusätzliche undrafted Prospects jährlich, Team 0 aktiv. **Kein** realer NFL-2027-Verlauf und **keine** reale aktuelle Eigentümerliste.
- Die sechs 2027er Roster werden einschließlich Rookie Draft, Legalization und legalen Free-Agent-Upgrades wie CP6k eingefroren, also **2027 zunächst 6/6 cap-legal**. Die 2027/28/29-Markt-Caps und Team-0-2027-Salary-Beträge wurden gegen die archivierten CP6k-Seed-JSONs geprüft.
- Der neu signierte **2027er Rookie-Kohortenanteil** wird mit 100/125/150 % bepreist (30/30/31 Rookie-Verpflichtungen in den drei Kohorten). **Alle übrigen 2027er Roster-Verträge** einschließlich Alt-Rookies werden **lediglich als synthetisch neu 2027 unterschriebene übrige Kontrakte** behandelt: 100/100/100, 100/105/110, 100/110/120 %. Das ist **keine** rückwirkend ermittelte echte Altvertragszeitachse; Übergangsregeln sind weiter offen.
- Für 2028/29 werden **dieselben 2027er Verpflichtungen** Jahr für Jahr fortgeführt; keine vom Manager freiwillig durchgeführten Trades, Cuts, Claims, Restrukturierungen, neue Rookie-/FA-Verträge, Roster-Backfills oder Retirements als günstiger erlassene Garantien. Damit messen wir nicht die optimal oder überhaupt tatsächlich legal ausführbare Managerreaktion. Im Gegenteil: Fehlende zusätzliche Rookie-/FA-Verpflichtungen können die wahre Belastung **unterschätzen**.
- Die CP6k-Marktzukunft enthält bereits **Year2-/Year3-Rookie-Contract-Preise** im Top120. Markt-Cap-Schocks **0/−10/−20 %** werden als **einmalige zusätzliche proportionale Absenkung** des jeweiligen 2028er und 2029er CP6k-Markt-Caps angewandt, **nicht kumulativ** zwischen diesen beiden Jahren. Diese Schocks sind arithmetische Stressparameter, keine aus aktuellen Verletzungen/Leistungswerten reproduzierte alternative 2028/29-NFL-Welt; Floor/Top120-Rank unter dem Schock nicht neu optimiert. `0 %` heißt **jeweiliges synthetisches CP6k-Cap**, nicht exakt konstant gehaltenes absolutes Cap.
- Die Hochrisikoanalyse setzt zunächst **100 % Garantie der künftigen Jahresbeträge** ohne veräußerte Vertrags-Claims, späteren Offset oder Neuverhandlungen voraus. Unter dieser Annahme ist ein Cut mit nicht abgelöstem Restvertrag **keine** Verringerung der geschuldeten Zukunftssumme; er wechselt nur das Konto von aktivem Salary zu Dead Cap. Das ist ein **Constraint-Test**, keine bereits beschlossene Garantiequote.

### 3.2 Seed 11: Wie viele der sechs Teams wären 2029 ohne Anpassungen über Cap?

| Veteranen-Year1/2/3 | Kein Zusatzschock | Marktkapazität −10 % | Marktkapazität −20 % |
|---|---:|---:|---:|
| **100/100/100** | **0/6** | **2/6** | **3/6** |
| **100/105/110** | **2/6** | **3/6** | **5/6** |
| **100/110/120** | **3/6** | **4/6** | **5/6** |

**Unveränderte 2027er Kader, keine neuen Signings, nur Vertrags-/Marktstress.** 2027er Basis-Teams 0–5 nutzen zusammen **2.318.356.069 $** bei sechsfacher Cap-Summe **2.951.371.290 $**, ca. 78,55 % der theoretischen Gesamtkapazität. Andere Seeds ca. 81,03 % / 80,56 %. Die Kapazität ist also im Start ausreichend, **aber ungleich** verteilt.

### 3.3 Kritischer Unterschied: individueller Cap-Stress vs. mathematischer Gesamtkollaps

Die neue zentrale Pflichtprüfung lautet:

```text
L_t = Summe aller weiterhin garantierten jährlichen
      Vertrags-/Dead-Cap-Verpflichtungen über alle sechs Teams
K_t = 6 × MarketCap(t)

Wenn L_t > K_t:
  Kein reiner Trade, kein Transfer unverändert garantierter
  Verträge und kein Cut ohne wirksame Garantie-Reduktion
  kann gleichzeitig alle sechs Teams legal machen.
```

Dies ist eine **notwendige**, keine hinreichende, Bedingung. Auch bei `L_t ≤ K_t` können einzelne Teams unlösbar über Cap bleiben, wenn niemand ihre Verträge übernimmt, Slot-/Starterzwänge binden oder kein sinnvoller Rebuild-Käufer existiert.

**Seed 11:**

- 2029 bei Veteranen 100/105/110 und **−10 % Marktkapazität**: **3/6** individuell über Cap, aber ligaweit nur **99,35 %** Gesamtauslastung. Re-Allokation *könnte* rechnerisch helfen – keine realen Trade-/Claim-Zusagen.
- 2029 bei 100/110/120 und **0 % Zusatzschock**: **3/6** individuell über Cap, aber nur **96,74 %** ligaweite Auslastung. Das ist potenziell genau die gewünschte verhandlungsintensive Cap-/Contract-Strategie.
- 2029 bei 100/110/120 und **−10 %**: **4/6** über Cap, Garantie-Verpflichtungen **197,511 Mio. $ über der Summe aller sechs Team-Caps**. Ohne wirksame Auflösung von Garantien kann die Liga **nicht vollständig legal** werden.
- 2029 bei 100/110/120 und **−20 %**: **5/6** über Cap, ligaweite garantierte Jahressumme **490,405 Mio. $ über allen sechs Team-Caps**. Seeds 29 und 47: **550,250** bzw. **542,356 Mio. $**. Im jeweiligen 2028er Vorjahr dieses harten Falls bestehen ebenfalls große Summenlücken (Seed 11 ca. 228,392 Mio. $).
- Über alle **27** gepaarten Seed/Eskalations-/Schock-Kombinationen und **81** Jahreszeilen insgesamt melden **23** eine aggregierte Unterdeckung unter den harten Garantie-/Nichtreaktionsannahmen. Das sind **zusammenhängende Sensitivitätszeilen**, keine 23 beobachteten unabhängigen künftigen NFL-Fälle; sie begründen keinen realen Ausfall-Anteil.

**Fachliche Schlussfolgerung:** Mehrjährige Verpflichtungen sind durchaus attraktiv für Ziel 2/4. Ein **marktwertbasierter sinkender Cap** und **zunehmende volle garantierte ContractSalary** können sich aber im selben Modell so überschneiden, dass selbst perfektes Management oder freiwillige Trades allein nicht genügen. Die sechste Liga-Zielsetzung („umsetzbar“) ist dann **mathematisch** betroffen, nicht bloß administrativ. Man darf einen derartigen Konflikt nicht durch willkürliche automatische Cuts, Schulderlass, fictive Käufer oder Verdeckung von Debt lösen.

## 4. Testbare Contract-/Guarantee-Varianten – ohne voreiligen Sieger

1. **Voll garantierter 3Y-Vertrag (CP6n-Hard):** 100 % der zukünftigen Year-by-Year-Schedules bleiben nach erfolglosem 14-Tage-Claim als Dead Cap für den ursprünglichen Club. **Maximale Konsequenz**, aber wie gezeigt kein universell legaler Sanierungsweg garantiert.
2. **Teilgarantierter 3Y-Vertrag:** Derselbe fixierte 3Y-Schedule und dieselbe Rookie-Staffel, aber beispielsweise nur **50 % der zukünftigen Jahre** nach einem nicht übernommenen Cut verpflichtend; übriger Teil erlischt. Die auflösbare Vertragsverpflichtung ist **nicht** identisch mit „50 % des aktuellen Vertragsgehalts auf Dauer“; sie ist **pro Vertragsjahr/jeder unterschriebenen Vintage** zu berechnen. Auch dies muss auf alle sechs Teams und Mindest-20 bzw. tatsächliche 30 Plätze inklusive Ersatz-Cap getestet werden.
3. **Garantiertes erstes, begrenzt garantiertes zweites, ungarantiertes drittes Jahr:** Jahr 2 = z. B. 50 % geschützt, Jahr 3 = 0 % bei Cut; kein automativer Cap-Aufschlag aus Garantien selbst. Vertrag hält trotzdem mit Year2/3-Salary voll solange Spieler auf Team ist.
4. **Alternative Laufzeiten / ein kleiner Garantiebetrag statt Volljahres-Garantie:** Als zusätzliche Kontrollvariante untersuchen, aber nicht ohne Nutzerentscheidung als neue Regel ausgeben.
5. **MarketCap-Puffer/-Glättung** wäre eine andere, gesondert quantifizierte Option. Ein Cap-Floor, der alle garantierten Verträge automatisch rettet, neutralisiert die vom Nutzer ausdrücklich erwünschten fallenden Marktwerte. Deshalb nicht als automatische Lösung einbauen.

**Rookie Escalation bleibt in allen Varianten 100/125/150.** Die Veteraneneskalation von 5/10 % oder 10/20 % in Y2/Y3 ist **eine Sensitivität**, keine bereits gewählte Zahl. Ebenso ist `Rookie-Year4` nach abgelaufenem Vertrag ein **neues Angebot** zum neuen Marktwert, nicht lautlos eine 3Y-Renewal-Garantie. Optional halten, zum Marktwert neuen Contract signieren oder kostenlos bei Vertragsende entlassen; Frist/Timing und mögliche Free-Agency-Exklusivität offen.

## 5. Präzise Verträge, Claims, Traden und 14-Tage-Fenster

**Zwei verschiedene Uhren:**

- **Claim Window** nach Cut: 14 Tage für einen neuen Owner, um den **unveränderten ursprünglichen** Vertrag mit verbliebenen Jahresgehältern und definierter Garantie zu übernehmen. Während der 14 Tage muss die Verpflichtung **beim alten Owner reserviert** bleiben, bis sie tatsächlich angenommen und technisch bestätigt ist. Nach Ende ohne Übernahme setzt `guaranteedSalaryByYear` die nach Regeln fälligen Dead-Cap-Jahrgänge; das alte Salary darf weder verschwinden noch an einen fiktiven Käufer gehen. Nach dem Fenster neuer FA-Vertrag nur bei explizit geregeltem **Offset** oder Doppelbelastung: Eine billigere Neuverpflichtung darf nicht heimlich dieselbe Altgarantie löschen.
- **Signing/Cap Grace** nach eigenem Draft-/Waiver-/FA-Zugang: ebenfalls vorgeschlagene 14 Tage zum freiwilligen Ausgleichen der **vollständigen** Cap-/Roster-Belastung des atomaren Bundles. Mehrwöchiges Spielen unter noch nicht gebuchter Cap-Last wäre eine Gratis-Kurzleihe. Ein cap-nicht-konformer vorläufiger Spieler sollte **nicht** ohne zusätzliche, vorab festgelegte Einsatzstrafe/Startverbot in Matchups eingesetzt werden dürfen. Ein bloßes App-Banner kann dieses Startverbot in Sleeper **nicht automatisch garantieren**. Freie Rückgabe während Grace nur für **noch nicht verbindlich gewordene** Anträge und ohne bereits erfolgte sportliche Nutzung; sonst entsteht ein Arbitrage-Loch.
- **Trade** überträgt zukünftige noch nicht verdiente Vertragsjahre vollständig, kein neuer drei Jahre langer Contract, kein Salary-Reset. **Laufende Saison** ist als eigene Policy offen: kompletter aktueller jährlicher Cap-Charge beim jeweils aktiven Besitzer (einfacher) oder wohldefinierte proratisierte Zuordnung `old paid / new remaining` (NFL-näher). Beides darf **nicht** rückwirkend unsichtbare Doppelbelastung oder einen kostenlosen zweiten Jahresvertrag erzeugen. Kein frei verhandelbarer Salary-Discount ohne eindeutige begrenzte Retained-/Offset-Mechanik.
- **Expiration** nach genau drei League Seasons, nicht 36 Wochen oder beliebige drei Jahrestage. 2027er Signatur -> 2027/28/29, vor 2030 kostenlos auslaufen oder zum neuen 2030er Marktpreis **neu signieren**; bei Vertragstrade bleibt Expiration 2029. Für während der Saison neu verpflichtete Spieler zählt ohne beschlossene Proration die gesamte League Season 2027 als Vertrag Year1 (nicht automatisch 2028–30).
- **NFL-Inaktive/Retirement/Injury**: klären, ob die Garantie trotzdem weiterzahlt oder die Liga eine explizite Injury-/Retirement-Ausnahme beschließt; keine automatische Freigabe in der Forschung. Bei unseren 5 Reserve-/2 Taxi-Slots muss **nachweisbar** entschieden werden, ob und wie Salary/Contracts weiter zählen. Diese Slots sind keine kostenlosen Ersatzlager.
- **Hard Failure**: kein automatischer Commissioner-Cut, keine Vertragslöschung oder rückwirkende Salary-Korrektur. Eventualfall mit Deadline/Nachfrist/Einspruch/Audit und Ligaentscheidung definiert; unter Vollgarantie möglicherweise mathematisch nicht sanierbar.

### NFL-Verifikationsgrenze

Die NFL kennt garantierte und nicht garantierte Contract-Bestandteile, Waiver-Assignment und Zuweisung **noch nicht bezahlter** Verpflichtungen an das übernehmende Team ([NFL Football Operations](https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language), [CBA Art. 13 §6](https://overthecap.com/collective-bargaining-agreement/article/13/section/6)). Die NFL bucht manche garantierte Beträge/Signing-Bonus-Reste **beschleunigt** als Dead Money und ihr Cap hängt **nicht** an jährlichen Top120-Performance-Marktpreisen, sondern am CBA-Revenue-Verfahren ([CBA Art. 12](https://overthecap.com/collective-bargaining-agreement/article/12/section/1)). **Voll garantierte drei Seasons und unveränderte langfristige Verteilung pro Jahr sind eine bewusste eigene Fantasy-Mechanik**, nicht „so macht es die NFL“. NFL-Rookie-Standardverträge sind regulär vier Jahre, diese Fantasy-Rookie-Staffel bleibt drei Jahre.

## 6. Die fünf obligatorischen Finanzierungsachsen

| Achse | Für CP6n fachlich geklärt / offener Beleg |
|---|---|
| **1. Seller Relief** | Ein Trade würde den ganzen verbliebenen **zukünftigen** Contract-Plan an den Käufer übertragen; Verkäufer entlastet brutto die betreffenden noch nicht fälligen Jahre, netto abhängig von verabredetem aktuellem Jahres-Split und ggf. Retention. Ein erfolgloser Cut unter 100%-Garantie verschiebt dieselben Beträge in Dead Cap, **0 garantierte Entlastung**. **Keine realen Trades/Cuts/Claims ausgeführt.** |
| **2. Buyer Burden** | Käufer muss **alle verbleibenden Jahresgehälter** übernehmen, nicht nur aktuell günstiges MarketValue. Eine hypothetische Waiver-Claim-Übernahme tilgt den gesamten übertragenen Rest-Contract beim Seller; Cap- und Roster-Feasibility auf **beiden Seiten** noch nicht modelliert. |
| **3. Roster-Kapazität** | CP6k-2027-Roster nach Draft und FA sind 24–25 Plätze; Positionsminima im Forschungsmodell erfüllt. **Echte Liga: 30 normale Slots + 5 IR + 2 Taxi**, 13 Startplätze; keine tatsächlichen 2027-Taxi-/IR-Claims, atomaren Waiver-Claim-/Cut-Bundles oder 40er-Neuregelung verifiziert. |
| **4. Gesamtliga-Schuld/Guarantee** | Der komplette jährliche garantierte Rest-Contract je Team und Vintage muss erhalten bleiben, auch wenn ein Cut den Account zu Dead Cap umklassifiziert; **nur** angenommener Trade/Claim verteilt Teamzuordnung. `sum due > six caps` ist harte Unmöglichkeit ohne zulässige echte Verringerung. CP6n Stresstest zeigt diese Grenze, enthält **keine** künstliche H2/H3-Borrow-Vintage. |
| **5. Künftige Erfüllbarkeit** | Für 2028/29 gegenüber exogenem CP6k-Cap mit −0/10/20%-Stress geprüft. 27 × 3 Jahreszustände und 23 strukturelle Undercap-Failure-Zeilen unter **100 % Garantie**, ohne automatische Umstrukturierung, ohne Folge-Cash. Komplette legale Reaktionssimulation und tatsächliche Zahlungs-/Insolvenzstrategie **offen**. |

**Zusätzliche Klarstellung:** In CP6n ist `sum guaranteed future year salaries` die Vertragsverpflichtung, **nicht** eine neue Geldschöpfung oder ein aus dem Cap geliehener Kredit. Übernahmen verändern die Besitzerzuordnung, aber nicht die Liga-Gesamtsumme. New Signings und neue Dead-Cap-Ansprüche können diese Summe erhöhen; rechtlich geregelte Garantiereduktion kann sie senken. Ein nur positiver Cap-Puffer eines Nachbarteams ist **kein Beweis** für dessen Bereitschaft, einen problematischen Vertrag zu übernehmen.

## 7. Vergleich am geschützten Sechs-Ziele-Nordstern

| Geschütztes Ziel | Möglicher Nutzen des 3Y-Vertrags + MarktCap | Zwingend zu testendes Risiko |
|---|---|---|
| **1. Langfristige Chancengleichheit** | 3Y günstige Stars müssen bei Verlängerung/Free Agency wieder zum Marktpreis; contract-value-Trades öffnen eigene Wege | Schlechte Vollgarantien und Markt-Einbruch können sechs Teams blockieren, ebenso kontraktgebundene sehr billige Stars für 3 Jahre |
| **2. Gutes Management belohnen** | Scouting, früh unterschreiben, Cap-Planung, Vertragswert/Restlaufzeit und rechtzeitiger Sale haben hohen Optionswert | Mehrjährige Zufallsverletzungen/Breakouts können Manager über Gebühr irreversibel bestrafen |
| **3. Keine zementierten Vorteile** | Jede Verpflichtung besitzt Ablaufdatum und Marktpreis-Resigning-Gate | 3Y künstlich günstige Superstars + späte Trades erlauben erhebliche, aber zeitlich befristete Vorteile; kein Nachweis über mehrjährige Rivalen-Titelchance |
| **4. Wirtschaftliche Konsequenzen** | Explizite 2027–29-Zusage, steigender Year2/3-Schedule und Dead Cap machen Fehlentscheidungen teuer | Aggregate Insolvenz bei Markt-Cap-Rückgang statt hilfreicher Marktanreize |
| **5. Strategische Freiheit** | Win-now-/Rebuild-/Salary-Dump- und Rookie-Pick-Handel wertvoller; Käufer können absichtlich Cap aufnehmen, um Assets zu erhalten | Voll garantierte wertlose Verträge sind für andere Manager unattraktiv, blockieren Käufermarkt und Rebuild-Exit |
| **6. Operative Umsetzbarkeit** | Vertrag pro Spieler als klar versionierte `contractId`, `salaryByYear`, `guaranteedByYear` und Laufzeit automatisch nachvollziehbar | 14-Tage-Claim/Grace, Dead-Cap-Quittierung, Cap-/Startberechtigung, NFL-/Sleeper-Aktionen sind nicht automatisch über öffentliche read-only-Sleeper-API durchsetzbar; Hard-Settlement-Vollzug offen |

**Keine Rang- oder Gesamtsiegerpunkte**: Das bisherige CP6m A/F2/F3/B-Enforcement und das neue Contract-Ledger sind **orthogonale** Achsen. Nur ein gemeinsamer, von sechs Managern realisierbarer, saisonenübergreifender Markt mit Picks, Claims, freiwilligen Deals und Contract-Vintages kann verlässlich zeigen, welche Kombination den Nordstern am besten erfüllt. Ein starres 3Y-Vollgarantie-Modell ist **nicht** allein aufgrund seines NFL-Gefühls zu priorisieren.

## 8. Nächster gebundener Checkpoint: Vertragsregeln vor realisierter Dominanz

1. **Zunächst Cap-Verursacher vollständig trennen**: echter jährlicher Player `MarketValue` (einschl. Rookie-Marktbewertung, ohne rückwirkend Vertragspreise als MarketValue zu verwenden), normativer `MarketCap`, initiale Vertragsangebote und separate persistente `ContractSchedule`-Daten. Für alle Player/Seasons 2024–2026 anhand verfügbaren archivierten Scoring-Quellen präzise as-of, kein retroaktives Erfinden fehlender Vertragsabschlüsse.
2. **Contract-Varianten gepaart testen**: Rookie 100/125/150 fix, Veteran 100/100/100 vs. 100/105/110 vs. 100/110/120, Restgarantie 100 % vs. etwa 50 % vs. optional jahresabhängig; unveränderte Marktpreis-Szenarien und 0/−10/−20%-Schocks. Dazu Cut/Claim-14d, Buyer volle zukünftige Jahresbelastung, gesetzlich definierter Offset und Hard-Failure.
3. **Sechs-Owner-Trade-/Rebuild-Simulation**: wirkliche Pick-/Player-Asset-Transaktionen und freiwillige Gegenleistung, gleiche Informationslage, Year4-Renewal/Expiration, Cap-Prüfmodell A/F2/B mit legalen Bündeln und realer Roster-/Taxi-/IR-Position. Nicht den Verkäufer-Dead-Cap nur zu anderem Eigentümer verschieben und als kostenfrei bezeichnen.
4. **Bewertungsmetriken**: Max/Mean Starterindex pro Year, Zeitraum oberhalb bestimmter Titelkonkurrenz, Rebuild-Turnaround, Manageraktivität und Forderungen an Spieler-/Pick-Markt, System- und Team-Cap-Compliance, `market / contract` Wertlücke, Verfügbarkeit legaler Käufer, Dead-Cap-Jahrgänge, Simulations- und Operatorausfälle. Keine Pflicht zu erzwungenem Championwechsel.
5. **Decision Gates**: Vor jeder Liga-Ratifizierung explizite Entscheidungen über Vertragsende ohne automatische Renewal, Midseason-Proration, Garantiesatz, Offset, Verletzung/Retirement, Claim-Priorität und 14-Tage-Finality, Eingriff bei mathematischer Gesamtkapazitätsunterdeckung. **Kein** Auto-Cut, Cap-Floor, Receiver, Credit, mehrjähriger Erlass als stillschweigende Implementierungsentscheidung.

## 9. Empfohlene Architekturrichtung (noch kein PR-/Runtime-Design)

```text
SOURCE: NFL results, rookies/draft facts, Sleeper ownership & trades,
        immutable league contract signing/claims/expiration decisions
  ├─ DATA DERIVED: player-market-value/{year} (not contract prices)
  ├─ DATA DERIVED: market-cap/{year} (from top120 MARKET values only)
  ├─ PERSISTENT SIGNED CONTRACT LEDGER: contractId, playerId, owner, vintages,
  │      signedMarketValueAsOf, startSeason, endSeason, annualSalary[],
  │      guaranteeBySeason[], transfer/claim/cut history, status
  └─ DATA DERIVED: owner-cap-obligations/{year} (active salaries,
         reserved claims, guaranteed Dead-Cap, cross-team conservation)
        └─ CONSUMER: Roster/Contract board, waivers, trade preview, compliance
```

Eine Verbraucherkomponente darf nicht aus NFL-Raw-Sources selbst neu berechnen, ob ein Vertrag im dritten Jahr ist, welcher Claim rechtzeitig und wirksam einging oder ob ein Cap-Defizit nach Cuts noch garantiert verbleibt. **Marktmodell-Derived und Contract-Event-Ledger müssen klar getrennt versioniert sein**, denn aktuelle Marktpreise dürfen signierte Altverträge nie rückwirkend ändern. Eine zuverlässige data-derived Vorabberechnung ist aber noch **kein** atomarer Sleeper-Eingriff; operativer Vertragseingriff und User-/Commissioner-Freigaben sind gesondert zu spezifizieren.

**Fazit / Status:** Neues Contract-Modell liefert plausible Langzeit-Reize, aber CP6n belegt bereits eine **harte Systemgrenze** unter Vollgarantie bei fallenden Markt-Caps. Denkbare Antwort ist eher **klar begrenzte Garantien/Offset-Regeln mit expliziter Vertragsstaffel** statt ein permanenter Credit oder ein künstlich an Schulden hochgezogenes Markt-Cap. Diese Bewertung bleibt bis zur gepaarten langfristigen Simulation und Liga-Abstimmung eine **Forschungspräferenz**, kein neuer Ligabeschluss. Aktive Salary-/Cap-/Draft- und Sleeper-Regeln, bestehender Rookie-Concept-Dokumentationsstand und die sechs Nordstern-Ziele unverändert.
