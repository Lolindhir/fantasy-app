# CP6i – Starterobergrenze bei 40er-Maximum und vollständiger Salary-Anrechnung

> Stand: 19.11.2026 · **Research / keine neue Ligaregel** · Owner: [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344).
> Dieser Bericht ist ein datierter Forschungsbeleg, **keine zweite normative Salary-Konzeptquelle**. Die sechs geschützten Ziele gelten unverändert gemäß `fantasy-management/league-context/league-philosophy.md`.

## 1. Nutzerbestätigter Forschungs-Hauptkandidat

Die bisherige Diskussion mit einem 30er-Pflichtkader, Top-20-Abrechnung und aggressiven Cap-Faktoren wird **nicht** als geltende Zielvariante unterstellt. Der **führende zu prüfende Hauptkandidat** lautet:

- **Maximal 40 reguläre Kaderplätze, keine Pflicht, alle zu belegen.** Die tatsächliche optimale Kadergröße ist eine wirtschaftliche Managemententscheidung.
- **Alle gehaltenen Spieler belasten das Cap mit ihrem vollständigen Salary**, unabhängig von Starter-/Bankplatz. IR/Reserve/Taxi-Definition und damit verbundene Cap-Anrechnung sind vor endgültiger Simulation explizit zu entscheiden; nichts unbemerkt ausnehmen.
- **Team-Cap = Summe der marktweit 120 teuersten Salaries ÷ 6**, Faktor **1,00** ohne bisherigen 0,90-Abschlag, als endogene Preiswelt.
- Gewünschte künftige Preiswelt: Performance + dynamische positions-/rangbezogene Criticality, **dreijährige Rookie Contracts** (Year 1 100 %, Year 2 125 %, Year 3 150 %, Year 4 Performance-Salary) und das **gleitende Mindestgehalt** `max(P, M+0,50×P)` ab Year 4.
- **Cut-/Retained-Dead-Cap** und **Cap-Vorgriff / Tilgung** sind explizite, getrennt zu buchende Sensitivitäten. Kein stillschweigender Default zu uneingeschränkter Kreditaufnahme, mehrjährigem Dead Cap oder kostenloser Flexibilität.
- Vollzug (Offseason-Deadline, In-Season-Checkpoints bzw. permanent, Grace/Hard-Failure) bleibt offen und wird gegen die operative Machbarkeit bewertet.

Diese Komponenten sind **Forschungshypothese / führende Arbeitsvariante**, weder 6/6 ratifiziert noch produktiv implementiert. Direkte Vergleichsvarianten mit 20, 30, 35 und 40 maximalen Plätzen bleiben sinnvoll, jedoch **mit derselben vollständigen Salary-Anrechnung**.

## 2. Zwei unterscheidbare Optimierungsaufgaben

**A. Konzentrationsobergrenze pro Salary-Zyklus:** Ein einziger Manager darf aus einem fixen Spielerpool alle Kandidaten wählen; alle 13 Starter erfüllen 2 QB / 2 RB / 2 WR / 2 TE / 4 FLEX (RB/WR/TE) / 1 K. Gesucht ist das höchste Starter-Qualitätsmaß, für das ein **vollständiger legaler Kader** einschließlich jeder tatsächlich gehaltenen Reserve und ihrer Salary-Kosten finanzierbar ist. Weitere fünf Teams werden nicht künstlich ausgeglichen. Spieler dürfen ligaweit nicht mehrfach vergeben werden.

**B. Nachhaltige Dominanz über fünf oder mehr Salary-Zyklen:** Jedes Jahr tatsächliche oder plausible Alterung, Retirement, Availability/Injuries, Rookie-Zugang, 3Y-Performance-Reprice, jährlicher Cap-Neubau und legal mögliche Transfers berücksichtigen. Zwei Managementregime **aus derselben initialen Eigentums-/Preis-/Leistungswelt** vergleichen:
1. **Passiv:** ein einmaliger Elite-Kern ohne wiederholte überlegene Transaktionsentscheidungen; gesetzlich notwendige Cap-Korrekturen und normale Ausfälle bleiben zulässig.
2. **Aktiv:** guter Manager nutzt fortlaufend Draft, Trades, Cuts, Free Agents, Flexibilität und günstige Rookie-Verträge bei realistischen Informations- und Marktbedingungen.

Primäre quantitative Zielgröße bei identischer Definition des jahresspezifischen Score `I_t`:
`H_5 = max_{legalen Managementstrategien} min(I_1,I_2,I_3,I_4,I_5)`.
Sie ist **nicht** mit einem garantierten ex-ante Prognosewert gleichzusetzen. Ergänzend: Verteilung/P10/P50/P90 über gepaarte Performance-/Injury-/Rookie-Szenarien, Wahrscheinlichkeit andauernder Dominanz, maximaler Abstand zu Team #2, normalisierter All-Star-Anteil, Cap-/Roster-/Asset-Opportunitätskosten und Time-to-Catch-up der Verfolger. Star-Kontinuität und aktive Qualitätserneuerung getrennt zählen.

**Wichtige analytische Eigenschaft:** Ohne Pflicht zur Mindest-Kaderbelegung und ohne zusätzliche Bank-/Availability-Bedingung ist das punktuelle *reine 13-Starter-Maximum* bei Maximalgrößen 20, 30, 35 und 40 zunächst **identisch**; denn derselbe 13er-Kader ist in allen vier Varianten zulässig. Mehr Kaderplätze erhöhen den Wert von Absicherung, Flexibilität und Entwicklung, nicht automatisch die theoretische Obergrenze der 13 Besten. Ein fairer Größenvergleich muss deshalb Anforderungen an Einsatzfähigkeit, Reserve, Mindestkosten und mehrjährige Aufrechterhaltung ausdrücklich modellieren, statt 40 Slots zwangsweise zu füllen.

## 3. Referenzökonomik und Endogenität

Als **veröffentlichtes 2026er Salary-Snapshot** wurde im vorausgehenden Chat die Summe der Top 120 von **2.851.024.206 $** und damit das hypothetische f=1,00-Cap von **475.170.701 $ je Team** dokumentiert (gegenüber aktuell veröffentlichter f=0,90-Cap **427.653.631 $**; Dollar-Rundungen gemäß Produktregel). Dieser Cap ist **nicht** mit dem unten benutzten archivierten Oktober-Preisvektor identisch.

Das Liga-Budget ist `6×Cap = Top120-Summe`. Unter voller Anrechnung ist damit selbst bei vollständiger Belegung aller Top-120-Salaries kein weiterer positiver Salary-Raum ligaweit vorhanden. Jedoch kann ein individuelles Team Elitespieler konzentrieren; Durchschnitts- und Gleichverteilung sind **kein** systemisches Einzelteam-Limit.

Ein Elite-Premium verteuert die Cap-Basis mit: Für einen Spieler innerhalb der Top 120 steigert zusätzliche **1 Mio. $ Salary** das Cap eines jeden der sechs Teams um rund **166.667 $** bei f=1. Für dessen Besitzer ergibt sich bei vollständiger Anrechnung bei sonst unverändertem Markt und Cap-Auslastung ein direkter Netto-Cap-Druck von rund **833.333 $**. Die frühere Top20/f=0,75-Rechnung ist **nicht** auf diesen Kandidaten zu übertragen. Für Spieler außerhalb Top120, Rangwechsel und tatsächliche Cap-Knappheit muss die vollständige Rangliste neu berechnet werden.

## 4. CP6i-A: erste tatsächlich ausgewertete Querschnittsprobe

**Daten:** archivierte `fantasy-management/league-economy/salary/analyses/2026-10-05-salary-simulation-players.csv` (1.268 Zeilen). Der historische `performance_3y`-Wert ist **ein Qualitätsindex**, weder 2026er Week-11-Forecast noch echte 2027-Projektion. Filter: NFL-Team != `FA`, Position QB/RB/WR/TE/K, Index > 0; **719** Kandidaten. **Kein** live `Players.json`-Inhalt wurde als neue 2026er Beobachtung ausgegeben; diese Datei war über den Connector beim Versuch nicht vollständig lesbar.

**Zwei absichtlich getrennte damalige Preiswelten** (jeweils Cap marktweit Top120 ÷ 6, Faktor 1,00):
- P: archiviertes `salary_published` (damaliger veröffentlichter Salary-Vektor); Cap **480,679 Mio. $**.
- K: `salary_I_ohne_base_minimum` (archivierter k=1,5 Criticality-Performance-Preisvektor **ohne** neues gleitendes Minimum/Rookie-Kohorten-Reprice); Cap **489,862 Mio. $**.

**Optimierungsverfahren:** 13er-Starterwahl bei 2/2/2/2/4 FLEX/1 K. Unbeschränkte All-Star-Auswahl als obere Referenz. Cap-konforme Kandidaten durch 10.001 feste Lagrange-Salary-Gewichte und deterministische einteilige Tauschverbesserungen. Nur Spieler-IDs und Starterpositionen explizit geprüft. **Lokales Suchverfahren, keine gemischt-ganzzahlige globale Optimalitätsbescheinigung.** Für dieses reine Obergrenzen-Basisszenario sind **keine Bankspieler vorgeschrieben**; dies ist daher **keine** nachgewiesene über die Saison legal spielbare 20-/30-/40er-Mannschaft. Kein Dead Cap, kein Cap-Vorgriff, keine IR-Kosten, kein Transaktionsmarkt und kein fünfjähriger Zukunftspfad.

| Größe | P: historisch veröffentlicht | K: k1,5 ohne Floor |
|---|---:|---:|
| Top120-Cap bei f=1 | 480,679 Mio. $ | 489,862 Mio. $ |
| Absoluter 13er-All-Star-Index | 235,280 | 235,280 |
| Kosten des All-Star-13ers | 547,455 Mio. $ | 709,586 Mio. $ |
| **Gefundener** cap-konformer 13er-Index (Untergrenze des echten Maximums) | **221,313** | **212,841** |
| Kosten des gefundenen 13ers | 480,464 Mio. $ | 489,598 Mio. $ |
| Restbudget, bevor weitere Spieler/Verpflichtungen kosten | 0,215 Mio. $ | 0,265 Mio. $ |

**Interpretation:** Bei identischem 3Y-Qualitätsindex erzwingt das volle Cap im ersten Einzelteam-Extremtest eine Wahl zwischen Startern: Unter P liegen bereits der optimale All-Star-13er und sein Preis auseinander; K macht Elite-Verteilung deutlich teurer. Dass der gefundene K-Index niedriger ist, **beweist nicht**, dass das fertige Criticality+Rookie+Floor-Modell schlechter oder ausgeglichener wäre; K ist gerade **nicht** diese vollständige Preiswelt. Die Lösung ist **ein nachgewiesener erreichbarer Index**, nicht die obere Grenze. Die absolut maximalen 235,280 sind nur eine sportliche Oberreferenz ohne Cap. Ebenso ist das frühere **274,67** aus einer **anderen 2026er Quality-/Preiswelt** ausdrücklich **nicht vergleichbar**, weil damaliger `Players[].FantasyPointsAvgGame`-Proxy anders als `performance_3y` gewichtet wurde.

**Wichtigstes Limit:** Als die 13er im P/K-Extrem nahezu das komplette Cap verbrauchen, ist ein 30er/40er-Kader mit allgemeinem positivem Minimum ohne Starterverzicht nicht finanzierbar. Eine nur 13er-konforme Liste gilt nicht als finanzierbarer Saisonkader. Die nächste Iteration muss **zusätzliche reguläre Spieler inklusive echter Mindestgehaltskosten und IR/Taxi-Regel** zusammen mit den Startern optimieren; sonst entstehen künstlich hohe Dominanzwerte.

## 5. Verbindliche Testmatrix für die Fortsetzung

Für **dieselbe** vollständige Criticality+Rookie+Gleitminimum-Preiswelt und gepaarte Spielerentwicklungen:

1. **Zuerst vollständiges Einjahres-Maximum:** 20/30/35/40 als **Obergrenzen**, nicht als Belegungspflicht. Profile `13er-Extrem`, `funktionsfähige Minimum-Depth`, `gute Injury-Absicherung`; Salary-Anrechnung **alle** gehaltenen Spieler; globale MILP/CP-SAT-Solver-Abnahme plus heuristische Gegenprobe. IR/Taxi inklusive eindeutiger Kosten- und Aktivierungssemantik separat.
2. **Dann 6-Team-Gegenmarkt:** Gegner mit jeweils eigenen legalen vollständigen Rostern; keine doppelten Spieler, keine künstliche Stärkeangleichung. Maximale Differenz zum zweitbesten Team, Rookie-Surplus, freie Cap-Option, tatsächlicher Free-Agent-Buyer-Markt. 4 disjunkte Veteranen-Shadow-Teams bleiben **Stressbenchmark, kein zwingendes Gesetz für 6-Team-Tauglichkeit**.
3. **Dann 5–10 Zyklen:** jährliche Rank-/Performance-Neubewertung, neue Rookie-/Salary-Vintages, NFL-Exit/Retirement, Verletzungen, Cap- und Marktreaktionen; **passiv vs aktiv** und verschiedene Managerstrategien in gepaarten Seeds. Alle Teams jederzeit vollständige/regelkonforme Kader, keine stillschweigende automatische Gratis-Nachrüstung.
4. **Sekundär** C-add/Retained-Dead-Cap, Cap-Vorgriff, echte Rückzahlung ohne Refinanzierung, Settlement-/Kontrollintervalle und Migrations-/Grace-Fälle vergleichen. Je Transaktionsszenario die verbindlichen fünf Finanzierungsachsen aus `fantasy-management/league-economy/AGENTS.md`: Seller-Nettoentlastung, Buyer-Bundle-Kosten, reale Slots, ligaweite Debt nach Vintage und echte Folgejahrs-Tilgbarkeit. Hier in CP6i-A wegen ausgeschalteter Transaktionen **nicht angewandt/nicht beobachtet**, nicht als faktischer Debt-Nullstand interpretieren.

**Nordstern-Gates:** (1) realistische Aufholbarkeit, (2) Management-Belohnung, (3) kein kostenlos zementierter Vorteil, (4) wirtschaftliche Opportunitätskosten, (5) Strategievielfalt, (6) für sechs Manager nachvollziehbarer Vollzug. Ein hoher Index allein darf **weder** als Systemversagen **noch** als Leistungsbeweis eines einzigen Managers behandelt werden.

## 6. Offene Validierung / Handoff

- **Noch ausstehend:** vollständige Rookie-Year1–3-Vintages und Year4-Salaries, Mindestkosten auf jeder Bench, dynamische aktuelle Saison-Scoring-Projektionen, IR/Taxi-Accounting, gültiger 40er-Roster-Fachbeschluss, exakter globaler Solver und gepaarte Fünfjahres-Welten.
- Das ursprüngliche CP6g-Prototypenproblem bleibt: die zwei 5-Jahres-Simulationsansätze lieferten stark divergierende Shadow-Team-Cap-Ergebnisse. Die Ergebnisse dürfen nicht als validiertes Gleichgewicht oder harte Obergrenze ausgegeben werden.
- **Kein Eingriff:** kein Live-Salary, Roster, Cap, Sleeper, Workflow oder Liga-Setting wird geändert. Dieser Bericht ist ein neuer Forschungscheckpoint **innerhalb #1344**, kein neues operatives Issue.
