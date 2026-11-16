# CP6f – Fünfjahres-Zielmodell und virtueller Zehn-Team-Expansionstest (16.11.2026)

> **Status:** reproduzierbare, **synthetische Forschungssimulation**, weder Prognose für die NFL-Saisons 2027–2031 noch beschlossene Ligaregel.  
> **Auftrag:** Zuerst die eingeschwungene Ökonomie einer auf sechs Teams begrenzten Dynasty-Liga untersuchen, die von Anfang an unter dem neuen Criticality-/Rookie-/Cap-Regelentwurf wirtschaftet. **Keine Rückrechnung der heutigen 2026er Kader, kein historischer Dead-Cap-Überhang.** Dann aus dem verbliebenen freien **Veteranenmarkt** vier weitere konkurrenzfähige Teams ohne Expansion Draft bauen. Erst danach separate Umstellung von den echten 2026er Kadern.  
> **Issue:** [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) – CP6f.  
> **Reproduktionscode:** [cp6f_equilibrium.mjs](../simulation/cp6f_equilibrium.mjs).

## 1. Die drei getrennten Entscheidungswelten

1. **Zielwelt Z:** Sechs Manager starten unter dem neuen System ohne Altbesitzstände, entwickeln über fünf Jahre finanzierbare 30er-Kader, behalten die 13 Starter, treffen Rookie-/FA-Entscheidungen und beachten jeden Cap-Check. Die sechs unveränderten Nordsternziele sind die Bewertungsbasis.
2. **Shadow-Welt E:** Aus dem **nach dem jährlichen FA-Draft wirklich noch freien** Veteranenpool lassen sich vier weitere **disjunkte** 30er-Kader mit 13 gültigen Starterpositionen finanzieren. Vergleich gegen die sechs echten Simulationsmannschaften; weder Expansion-Draft-Zwang noch geschützte Spieler noch Rookie-Bonus.
3. **Migration M:** Würden wir ein solches System ab 2027 praktisch einführen, könnten temporäre kostenlose Cuts, Grace, Vertragsanpassungen oder Übergangsjahre nötig sein. **Nichts davon darf die Wahl des Zielsystems Z vorab verzerren.** Hier **nicht** simuliert.

## 2. Implementierte Mechaniken und Herkunft

| Element | Modell |
|---|---|
| Realer Quellenstand | Historischer Spieler-Preis-/Performancevektor der 05.10.2026-Simulation, 1.268 Spieler; echte 2026er Rookie-Draftpositionen als Klassenmuster; **keine realen 2026er Besitzer/Kader als Initialzustand** |
| Teams / Format | 6 etablierte Teams, jeweils 30 Spieler, 13 Starter = 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX (RB/WR/TE), 1 K |
| Manager | 6 deterministische, seedverschobene Strategien (Win-now, Balanced, Rookie Value, Cap Value, Reload, Depth) |
| Salary | Performance mit historischer **positionsabhängiger** Criticality-Rangkurve von 2023–2025, k=1,5 und Centered-25 (Referenzwert 8,4417), jährliches rankbasiertes Repricing, Drei-Saison-Floor 50/33/17; Dollar-Kurve über 0–20 PPG exponentiell 1,5, oberhalb linear |
| Minimum | Year 4+ mit konzeptionell gewünschter Gleitregel \`max(P, M + 0,50 P)\`, M nach Year/letztem Cap; Anfangsdaten nutzen gerundeten 2025er Cap-Proxy 428,8 Mio. $ |
| Rookie Contracts | 3 Jahre; Year1 aus 65 % Fantasy-/35 % NFL-Draft-Rang, 3,5-Exponent, 0,25-%-Undrafted-Floor; Year2 = 125 %, Year3 = 150 % des Year1-Ankers (jeweils Floor) |
| Populationserneuerung | Jährlich 30 synthetische gedraftete Rookie-Kandidaten auf Basis 2026er Draft-Positionsverteilung, **zusätzlich 50 synthetische undrafted/neue NFL-Rookie-Kandidaten**; Entwicklung und künftige NFL-Draft-Ränge sind **modellierte Annahmen**. Keine externen NFL-Ergebnisse nach 2026. |
| Team-Cap | Jährlich eingefroren: Faktor × Top-120-Salary-Summe / 6; pro Team 20 teuerste aktive Roster-Salaries; 0,90 / 0,85 / 0,80 / 0,75 / 0,70 |
| Offseason-Reihenfolge | Annual Reprice → capfreie Planung → fünf Rookie-Runden pro Team → **bindende Cap-Deadline** → fünf simulierte FA-Add/Drop-Runden; Salary Cap wird nicht bei jedem Pick neu berechnet |
| Rookie-Draft-Reihenfolge | Vorjahresleistungsproxy; 5. Team zuerst, 6. zweitens, dann 4./3./2./1. – **keine echten Rookie-Pick-Trades** |
| Transaktionen | Zusätzliche cap-konforme **eins-zu-eins-Add/Drop-Swaps** mit festem 30er-Kader; Eigentum und PlayerIDs bleiben disjunkt; starre historische 2026er Transaktionen kommen **nicht** vor |
| **Dead Cap** | Für diese **isolierte Zielzustands-Hypothese ausdrücklich ausgeschaltet** – weder Altlasten noch neue laufende Retention/Cap-Schuld. Bedeutet **nicht**, dass der separat diskutierte Ein-Zyklus-C-add als Regel verworfen wurde |
| Expansion | Vier neue Veteranenteams (je 30 Spieler, keine Rookies) mit gleicher *balanced* Auswahlstrategie und Snake-Fairness aus dem freien **Post-FA**-Pool; **alle vier** müssen 30 Spieler, 13 gültige Starter und Top20 ≤ identischen Team-Cap erfüllen |

**Kritische Einschränkung der dynamischen Preisfunktion:** Die **Rangzuordnung** in den Criticality-Kurven wird jährlich anhand der simulierten Spielerleistungen aktualisiert, die **Kurvenform** ist aber ein eingefrorener historischer 2023–2025-DMLI-Proxy. Eine eigene vollständige Neuberechnung der saisonalen Positions-Knappheitskurven, insbesondere bei tatsächlicher echter Expansion auf 10/12 Teams, ist **nicht** enthalten.

**Wichtig:** Das Modell simuliert **keine** realen 2027–2031-Spielerleistungen, Live-Injuries, Weekly-Startentscheidungen, Trades mit Zustimmung/Verhandlung oder marktendogenes Manager-Lernen. Der Anfangsbestand und die Rookie-Klassen stammen aus einem einzigen 2026er Quellenuniversum plus expliziten Zufallsannahmen. Es ist ein dynamischer **Machbarkeits- und Sensitivitätsprototyp**, **kein** kausaler Backtest und **keine** vollständige empirische Gleichgewichtsbestimmung.

## 3. Akzeptanzkriterien

Für **jeden** Faktor und jede Seed-Variante prüfen:

1. In **jedem der fünf Salary-Zyklen** besitzen die sechs Manager jeweils **genau 30** PlayerIDs, gültige 13er-Starter und Top20-Salary ≤ festes Jahres-Cap **sowohl vor als auch nach dem FA-Draft**.
2. Die vier virtuellen Shadow-Teams können **gleichzeitig** aus *vier verschiedenen, disjunkten* Veteranen-Kadern zusammengestellt werden. Auch sie besitzen je 30 Spieler/13 Starter und sind cap-konform.
3. Qualitativer Erfolg wird **nicht** als bloßer Spieler-Cut gezählt. **Median der vier Shadow-Teams ÷ Median der sechs etablierten 13er-Startaufstellungen**, jeweils auf derselben Modell-3Y/Forecast-Punkteskala. Zusätzlich das schwächste Shadow-Team gegen das schwächste etablierte Team. **85/90/95 %** sind Sensitivitätsmarken, **keine** Liga-Gesetzgebung.
4. Nach dem jährlichen FA-Draft müssen weiterhin hochpreisige und produktive Veteranen im freien Markt vorhanden und **mindestens finanziell** per legalem Add/Drop erreichbar sein. Ein cap-mögliches Paket ist **nicht** automatisch sportlich/strategisch attraktiv.
5. Unterschiedliche Zufallsstarts durchlaufen. Gerade bei 5+ Jahren ist **kein eindeutiges stationäres Gleichgewicht** ohne weitere Validierung behauptet.

## 4. Ergebnisse: drei feste Seeds, fünf vollständige Salary-Zyklen

**Seeds 11, 29, 47.** In allen **15** kombinierten Läufen war die Initialisierung erfolgreich, jeder der fünf Pre-FA-/Post-FA-Checks der sechs echten Teams legal und jeder Vier-Team-Shadow-Draft mit **vier vollen cap-konformen 30er-Kadern** möglich. Kein Dead Cap und keine Übergangscuts wurden dazu benötigt.

| Cap-Faktor | Relative Expansionsteam-Stärke nach Jahr 5, Seed 11 | Seed 29 | Seed 47 | Median | Range |
|---|---:|---:|---:|---:|---|
| 0,90 | 83,6 % | 90,2 % | 85,2 % | **85,2 %** | 83,6–90,2 % |
| 0,85 | 85,2 % | 90,9 % | 84,5 % | **85,2 %** | 84,5–90,9 % |
| 0,80 | 88,6 % | 89,8 % | 95,5 % | **89,8 %** | 88,6–95,5 % |
| **0,75** | **91,8 %** | **91,5 %** | **90,5 %** | **91,5 %** | **90,5–91,8 %** |
| 0,70 | 94,0 % | 94,0 % | 96,5 % | **94,0 %** | 94,0–96,5 % |

**Interpretation:** 0,75 und 0,70 können das vom Nutzer angedachte, schärfere **10-Team-Veteranenmarkt-Ziel** in diesem vereinfachten Fünfjahresmodell erreichen. 0,80 ist ein sinnvoller weniger aggressiver Referenzpunkt. Der 0,90er Mittelwert ist schwächer, einzelne Seeds können auch hier gut laufen. Niedrigerer Faktor = nicht *in jedem* individuellen Lauf monoton bessere Expansion, da Managerentscheidungen und Rookieentwicklung mitvariieren.

### Absolute Teamstärke nicht übersehen

Der Vergleich darf die vier neuen Teams **nicht künstlich stark erscheinen lassen**, indem die sechs etablierten Teams ausgehöhlt werden. Im fünften Jahr liegen die **Medians** etablierter Teams (13er-Index) in den drei Seeds grob bei:

| Faktor | Seed 11 | Seed 29 | Seed 47 |
|---|---:|---:|---:|
| 0,90 | 162,3 | 156,7 | 158,8 |
| 0,85 | 163,1 | 152,7 | 159,0 |
| 0,80 | 160,0 | 154,2 | 155,1 |
| 0,75 | 154,9 | 155,8 | 160,8 |
| 0,70 | 152,6 | 153,8 | 151,3 |

Das sind ausschließlich **modellierte Leistungspunkte**, keine Week-Projektion oder exakte Real-PPG-Vorhersage. Ein Teil des relativen Expansion-Erfolges entsteht tatsächlich durch geringere Star-Konzentration in den alten Teams; deren **absolute** Qualität fällt bei niedrigeren Faktoren hier aber nicht auf Null oder unter das Startbarkeit-Niveau.

### Shadow-Kader nicht nur sportlich, auch wirtschaftlich

- Alle vier disjunkten virtuellen 30er-Kader pro Seed/Faktor sind **Top20-cap-konform**, nicht nur einzelne Startergruppen.
- In der Expansion-Phase werden **keine** ursprünglichen Teamspieler beschlagnahmt. Die Angebotsbasis ist die Free-Agent-Menge **nach** den simulierten FA-Runden.
- Der Prozess ist ein *fairer Gegenentwurf* mit gleicher Balanced-Strategie für die vier Neueinsteiger. Er beweist **weder** die tatsächliche Verpflichtungsbereitschaft dieser hypothetischen Manager **noch**, dass eine echte Liga mit 10/12 Teams automatisch dieselbe Salary-/Criticality-Kurve verwenden dürfte.

## 5. In-Season-FA-Markt: exemplarischer Seed 11 nach Jahr 5

Definition: Tier 1/Tier 2 über **relative Positional Ranks der aktuellen synthetischen Forecasts**; nur **ungebundene aktive Veteranen Year 4+** zählen. Als *hochpreisig* gilt hier mindestens **5 % des aktuellen Team-Caps**. Die Quote ist eine **Messschwelle**, keine neue Salary-Regel.

| Faktor | Freie Tier 1 / Tier 2 | Davon mit Salary ≥ 5 % des Caps | Mindestens ein finanzierbarer Ein-zu-eins-Add/Drop-Pfad |
|---|---:|---:|---:|
| 0,90 | 6 / 8 | 11 | 14 |
| 0,80 | 9 / 9 | 15 | 18 |
| 0,75 | 10 / 9 | 16 | 19 |
| 0,70 | 12 / 11 | 21 | 23 |

Für den jeweils ausgewiesenen Seed 11 besaßen in diesem vereinfachten One-for-One-Test **alle sechs Manager** zumindest eine rechnerische Aufnahmeoption; bei den betrachteten Zielspielern waren viele auch mit einem höheren unmittelbaren Starterwert verbunden. **Nicht nachgewiesen:** tatsächliche Annahme, realer Offseason-/In-Season-Tradeoff, zukünftige Rookie-Vertragsfolgen oder Aufnahme mit größerem Dead-Cap-Paket. Ein einzelner finanziell erlaubter Drop kann strategisch völlig unattraktiv sein.

**Schluss:** Das Ziel eines *teuren, produktiven Free-Agent-Marktes* scheint im Modell nicht nur mit der bloßen Cut-Anzahl vereinbar; auch nach den FA-Drafts existieren finanzielle Zugangspfade. Dieser Befund ist **hochgradig abhängig von den synthetischen Rookies, den Managerheuristiken und der Vereinfachung ohne Dead Cap**.

## 6. Stabilität über Jahr fünf hinaus (Seed 11, 9-Zyklen-Stress)

| Faktor | Median-Ratio Jahr 5 | Jahr 7 | Jahr 9 | Dynamischer Cap Jahr 5 / Jahr 9 |
|---|---:|---:|---:|---|
| 0,80 | 88,6 % | 84,9 % | 86,3 % | ca. 323,8 / 324,0 Mio. $ |
| 0,75 | 91,8 % | 87,6 % | 90,1 % | ca. 300,5 / 296,7 Mio. $ |
| 0,70 | 94,0 % | 88,9 % | 91,6 % | ca. 276,7 / 289,7 Mio. $ |

Alle sechs etablierten und vier virtuellen Teams blieben in diesen drei 9-Zyklen-Kontrollen legal. **Der Cap-Anker nähert sich nach sechs bis neun Modelljahren eher einer stabilen Größenordnung an; die Marktstärke schwankt weiterhin.** Jahr fünf ist deshalb ein begrenzter Beobachtungszeitpunkt, **kein Beweis für Stationarität** oder einen universell optimalen Faktor.

## 7. Fünf-Achsen-Cap-Governance

1. **Seller/Abgebende Manager:** Die sechs Bots geben in einem neuen geschlossenen 30er-Roster-Budgetsystem automatisch einzelne Veteranen/Depth-Spieler bei Rookie- und FA-Entscheidungen ab. Historisches Seller-Verhalten und echte Tradebereitschaft wurden **nicht beobachtet**; kein Cut-Druck aus 2026er Altkadern übernommen.
2. **Buyer/Kaufende Manager:** Alle internen und vier Shadow-Roster rechnen nominale Salaries und Top20-Cap durch; zulässige Eins-zu-eins-Pakete wurden gezählt. Echte externe Angebote/Annahmen, Salary-Portabilität nach Cut und Verhandlungen sind **nicht modelliert**.
3. **Roster/Slots:** Alle bestehenden und virtuellen Kader benötigen **30** Spieler, 13 positionsgültige Starter; keine Abnahme einer bloßen 13er-Qualitätsliste ohne Depth und Slots.
4. **Ligaweite Schuld/Dead Cap:** In dieser isolierten Zielwelt **per Modelldesign ausgeschaltet = 0**, kein empirischer Befund einer realen Schuldlosigkeit; dies testet **nicht** die separat bevorzugte 50/30/15/5-C-add-Mechanik in einem eingespielten System.
5. **Rückzahlbarkeit/Future:** Nicht anwendbar ohne Schuld-/Dead-Cap-Funktion. Keine implizite mehrjährige Abzahlung, kein automatischer Folgejahresvortrag oder Kredit refinanziert. Die drei Rookie-Vertragsjahre sind jedoch konkret im jeweiligen Preiszyklus enthalten.

## 8. Bewertung gegenüber den sechs geschützten Nordsternzielen

- **Chancengleichheit:** Der Shadow-Expansion-Indikator wird bei 0,75/0,70 deutlich stärker als bei 0,90; unterschiedliche echte Managerleistungen bleiben dennoch erlaubt.
- **Gutes Management:** Rookies, Value-Picks, gelegentlicher hoher Veteranenpreis und Free-Agency-Budget werden relevanter. Die demonstrierte Belohnung ist **modellabhängig**, nicht aus realen fünf Managerjahren geschätzt.
- **Keine kostenlose dauerhafte Dominanz:** Annual Salary-Reprice und engeres Cap zwingen zu wiederkehrenden Budgetentscheidungen; keinen tatsächlichen Multi-Year-Champion-Backtest aus der Simulation ableiten.
- **Erfolg kostet Cap:** Hochpreisige freie Veteranen und opportunitätskostenbehaftete Add/Drop-Pfade entstehen; diese Modelle lassen ausdrücklich **keine** Kredit-/Dead-Cap-Last aus historischen Besitzständen mitlaufen.
- **Strategiefreiheit:** Sechs unterschiedliche Managerstile sind vertreten; keine generelle Superstar-Pflichtabgabe oder vorgeschriebene Teamstrategie.
- **Operative Umsetzbarkeit:** Vollständige Cap-/Roster-Prüfung im Prototyp positiv; tatsächliche Sleeper-/Commissioner-Durchsetzung eines permanenten Gates, atomare Transaktionen und wöchentliche Ausnahmen **nicht belegt**.

## 9. Schlussfolgerung und nächste Arbeitshypothese

**Die zentrale Nutzerkorrektur ist bestätigt:** Die alten CP6d/e-Migrationsstresse mit 2026er Dead Caps waren **kein** geeignetes Ausschlusskriterium für einen niedrigeren langfristig etablierten Cap-Faktor. Hier können 0,75 und 0,70 bei Neubeginn der Regeln alle sechs bestehenden Mannschaften legal halten und nach Jahr fünf sogar vier finanzierbare, annähernd gleichwertige Veteranenteams ermöglichen.

**Leading Research-Kandidaten nun 0,80 / 0,75 / 0,70** (0,90 als vertraute Kontrolle), nicht mehr reflexhaft 0,90/0,875 als sicherster Zielzustand. **0,75 als Testzentrum**, **0,70 als aggressiver Grenzfall**, **0,80 als moderater Gegenpol**. Kein endgültiger Beschluss.

Der nächste wichtige Fachtest ist **nicht** eine Transition-Cut-Simulation, sondern die Robustheit des Zielsystems gegen (a) andere Rookie-Entwicklung/Anzahl/Star-Dichte, (b) echte zukünftige Performance-/Injury-Szenarien, (c) zusätzliche in-season Waivers/Trades und (d) **regulär in jedem Zieljahr entstehende** Ein-Zyklus-C-add-Retention (nicht historische Altlasten). Erst nach Validierung und Ligaentscheid separat Migration und eventuell befristete kostenlose Cuts prüfen.

**Kein aktiver Liga-/App-/Generator-/Sleeper-Wechsel** und keine Änderung am geschützten sechs-Ziele-Nordstern.

## 10. Reproduzieren / technische Abnahme

Am Repository-Root:

\`\`\`bash
node fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs
# Vollständige fünfjährige Matrix + einzelne Saisondetails:
node fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs --json
\`\`\`

Benötigt Node.js mit ESM-Support. Das Skript **liest** nur die beiden bestehenden Repository-Artefakte und schreibt **keine** produktiven Daten. Default: Faktoren 0,90/0,85/0,80/0,75/0,70, Seeds 11/29/47, fünf Zyklen. Für die unabhängige 9-Jahres-Kontrolle kann die exportierte Funktion \`simulate(csvText, draftsText, {seeds:[11],factors:[0.80],seasons:9})\` aufgerufen werden.

**Fachliche Abnahme dieses Piloten:** 15/15 vollständig cap-/slot-konforme Fünfjahres-Szenarien, 15/15 verfügbare 4×30er-Veteranen-Shadow-Kader, mehr Star-/Tier2-Markttiefe bei aggressiveren Faktoren; **keine** Abnahme einer stationären realen Ökonomie, 2027er Preise oder einer verbindlichen Ligaregel.
