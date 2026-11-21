# CP6f – Fünfjahres-Zielmodell und virtueller Zehn-Team-Expansionstest (16.11.2026)

> **Status:** reproduzierbare, **synthetische Forschungssimulation**, weder Prognose für die NFL-Saisons 2027–2031 noch beschlossene Ligaregel.  
> **Auftrag:** Zuerst die eingeschwungene Ökonomie einer auf sechs Teams begrenzten Dynasty-Liga untersuchen, die von Anfang an unter dem neuen Criticality-/Rookie-/Cap-Regelentwurf wirtschaftet. **Keine Rückrechnung der heutigen 2026er Kader, kein historischer Dead-Cap-Überhang.** Dann aus dem verbliebenen freien **Veteranenmarkt** vier weitere konkurrenzfähige Teams ohne Expansion Draft bauen. Erst danach separate Umstellung von den echten 2026er Kadern.  
> **Issue:** [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344) – CP6f.  
> **Reproduktionscode:** [cp6f_equilibrium.mjs](../simulation/cp6f_equilibrium.mjs). **Strukturierte Ergebnisübersicht:** [cp6f-5y-summary.json](2026-11-16-cp6f-5y-summary.json).

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

**Seeds 11, 29, 47**, alle Cap-Faktoren mit denselben **externen synthetischen Spielerentwicklungs- und Rookie-Zufallsströmen** je Seed; Manager-Akquisitionen reagieren auf ihren Faktor und den jeweiligen Markt, die Shadow-Expansion verwendet **separaten** Zufall und beeinflusst nicht die künftigen Ligaereignisse. Vollständige reproduzierbare numerische Übersicht: [CP6f-5y-summary.json](2026-11-16-cp6f-5y-summary.json).

In allen **15** kombinierten Läufen war die Initialisierung erfolgreich, jeder der fünf Pre-FA-/Post-FA-Checks der sechs echten Teams legal und jeder Vier-Team-Shadow-Draft mit **vier vollen cap-konformen 30er-Kadern** möglich. Kein Dead Cap und keine Übergangscuts wurden dazu benötigt.

| Cap-Faktor | Relative Expansionsteam-Stärke nach Jahr 5, Seed 11 | Seed 29 | Seed 47 | Median | Range |
|---|---:|---:|---:|---:|---|
| 0,90 | 90,4 % | 89,2 % | 85,1 % | **89,2 %** | 85,1–90,4 % |
| 0,85 | 90,7 % | 86,1 % | 86,7 % | **86,7 %** | 86,1–90,7 % |
| **0,80** | **92,6 %** | **91,2 %** | **87,4 %** | **91,2 %** | **87,4–92,6 %** |
| **0,75** | **93,3 %** | **90,0 %** | **90,5 %** | **90,5 %** | **90,0–93,3 %** |
| 0,70 | 94,5 % | 91,8 % | 91,5 % | **91,8 %** | 91,5–94,5 % |

**Interpretation:** Die ambitionierte, nur als Indikator vorgeschlagene 90-%-Hürde schaffen die drei aggressiveren Varianten in vielen, nicht allen Läufen. **0,75** erreicht in diesen drei Seeds mindestens 90,0 %, **0,70** mindestens 91,5 %. **0,80** erreicht zwar den höheren Median als 0,75, im dritten Seed aber nur 87,4 %. 0,85 und 0,90 können einzelne gute Expansionsergebnisse zeigen, haben aber schwächere/instabilere Verläufe. Das ist **keine** statistisch abgesicherte Wahrscheinlichkeit, da **n=3** und die Zukunftsmodelle künstlich sind.

### Absolute Teamstärke und schwächstes Team nicht übersehen

Die vier neuen Teams dürfen **nicht künstlich stark erscheinen**, weil die sechs etablierten Teams vernichtet wurden. Die **Medians** etablierter Teams (13er-Performance-Index, identische Scoring-Slots) im fünften Jahr:

| Faktor | Seed 11 | Seed 29 | Seed 47 |
|---|---:|---:|---:|
| 0,90 | 154,5 | 154,7 | 165,4 |
| 0,85 | 152,2 | 159,5 | 165,4 |
| 0,80 | 151,5 | 157,7 | 164,8 |
| 0,75 | 153,5 | 156,6 | 163,8 |
| 0,70 | 153,0 | 156,3 | 159,6 |

Auch die **schwächsten Expansionsteams** sind im Jahr 5 bei 0,75 im Vergleich zum **schwächsten etablierten Team** je Seed bei rund **94,7 / 95,3 / 96,7 %**; bei 0,70 **97,5 / 99,4 / 101,8 %**. Das bedeutet **nicht**, dass alle vier neuen Teams jedes der sechs Etablierten erreichen – die Vergleichspaare und Medianlagen sind bewusst ausgewiesen.

Die Werte sind **synthetische Drei-Jahres-/Forecast-Leistungsindizes**, nicht Week-Projektionen oder reale Fantasy-Punkte der Jahre 2027–2031. Die Umverteilung ist **teilweise** eine Verringerung der Star-Konzentration der bisherigen sechs Teams; unter allen getesteten Faktoren bleiben diese hier aber mit validen Startaufstellungen aktiv.

### Shadow-Kader nicht nur sportlich, auch wirtschaftlich

- Alle vier **disjunkten** virtuellen 30er-Kader pro Seed/Faktor sind Top20-cap-konform, nicht nur einzelne Startergruppen.
- Kein bestehender Teambesitz wird für den Shadow-Expansion-Draft beschlagnahmt. Grundlage ist der Free-Agent-Pool **nach** den simulierten FA-Runden.
- Der virtuelle faire Gegenentwurf verwendet dieselbe Balanced-Strategie für alle vier Neueinsteiger. Er beweist **weder** tatsächliche Managerentscheidungen **noch**, dass eine echte Zehn-/Zwölf-Team-Liga dieselbe Criticality- und Salary-Kurve behalten dürfte.

## 5. Free-Agent-Markt nach dem FA-Draft: drei Seeds nach Jahr 5

**Definition:** Tier 1/2 über positionsabhängige Ränge der **synthetischen** aktuellen Leistungs-Forecasts. Nur **freie, aktive Veteranen ab Year 4**. Als *hochpreisig* gilt ≥ **5 % des Team-Caps**; diese Grenze ist lediglich ein Auswertungsindikator, keine neue Salary-Regel. Ein finanziell legaler Kaufpfad ist ein Ersatz eines eigenen Spielers in einem vollständigen 30er-Kader unter Cap, bei weiter gültigen 13 Startpositionen.

| Faktor | Median freie Tier-1-/Tier-2-Veteranen | Median davon hochpreisig | Median mit wenigstens einem finanzierbaren Add/Drop-Pfad |
|---|---:|---:|---:|
| 0,90 | 15 | 11 | 15 |
| 0,85 | 16 | 13 | 16 |
| **0,80** | **18** | **17** | **18** |
| **0,75** | **19** | **18** | **19** |
| 0,70 | 20 | 19 | 20 |

Exemplarischer Seed 11 im fünften Jahr: 0,90 = 6 Tier1 / 9 Tier2, 11 hochpreisig und 15 finanzierbar; 0,80 = 9/9, 17 hochpreisig und 18 finanzierbar; 0,75 = 11/7, 16 hochpreisig und 18 finanzierbar; 0,70 = 12/7, 17 hochpreisig und 19 finanzierbar. Die übrigen zwei Seeds sind im JSON-Befund gesondert dokumentiert.

Die **sechs** Manager besaßen in diesen Szenarien jeweils mindestens einen theoretischen legalen Aufnahmepfad. **Nicht nachgewiesen:** Bereitschaft zur Verpflichtung, Injury-/Week-Startbarkeit, Auswirkungen auf die Zukunft der dann gedroppten eigenen Spieler, mehrjährige Cap-/Dead-Cap-Konsequenzen, echte Trades oder ein atomarer Sleeper-Operationsvollzug. Eine nominell bessere Startelf kann ökonomisch schlechter sein.

**Befund:** Auch nach dem FA-Draft scheint unter den angenommenen Strategien nicht nur billige Resttiefe, sondern eine **echte teure und produktive Veteranenschicht** im Markt verbleiben zu können. Ihre tatsächliche Dauerverfügbarkeit während aller 17 NFL-Wochen ist noch nicht simuliert. Der Befund hängt stark von den 30 gedrafteten plus 50 undrafted synthetischen Rookies, der 2023–2025-Criticality-Kurve und den Managerheuristiken ab.

## 6. Stabilität über Jahr fünf hinaus (Seed 11, neun Salary-Zyklen)

Alle drei zusätzlichen 9-Jahres-Kontrollen verwendeten dieselbe bereinigte Exogen-Zufallslogik; sechs bestehende sowie vier virtuelle Teams blieben cap-/slot-konform.

| Faktor | Median-Ratio Jahr 5 | Jahr 7 | Jahr 9 | Modell-Cap Jahr 5 / Jahr 9 |
|---|---:|---:|---:|---|
| 0,80 | 92,6 % | 86,1 % | 89,6 % | ca. 315,8 / 309,0 Mio. $ |
| 0,75 | 93,3 % | 90,3 % | 91,0 % | ca. 294,7 / 289,0 Mio. $ |
| 0,70 | 94,5 % | 92,5 % | 94,8 % | ca. 273,9 / 269,3 Mio. $ |

**Die Dauerergebnisse bleiben aussagekräftig, aber nicht statisch.** In diesem einen Exogen-Szenario liegen 0,75/0,70 auch in Jahr 9 um/über 90 %, während 0,80 zeitweise unter 90 % fällt. Der dynamische Cap sinkt zunächst, nähert sich später einem stabileren Bereich an und kann wieder steigen. **Ein Jahr-5-Ergebnis ist keine Stationaritätsgarantie; n=1 für die 9-Jahres-Probe.**

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

**Die zentrale Nutzerkorrektur bleibt bestätigt:** Die alten CP6d/e-Migrationsstresse mit 2026er Dead-Cap-Lasten dürfen kein Ausschlusskriterium für das **langfristig etablierte** Cap sein. Bei einem ökonomisch neutralen Neustart können sowohl 0,80 als auch 0,75 und 0,70 über fünf Zyklen vollständige, legale sechs bestehende Teams und **vier finanzierbare Shadow-Veteranenteams** ermöglichen.

**Derzeitige führende Zielkorridor-Hypothese: 0,80 / 0,75 / 0,70**, mit **0,75 als neutralem nächsten Prüfpunkt**, 0,80 als moderater und 0,70 als aggressiver Seite. 0,70 hat hier den höchsten 3-Seed-Median der Expansion-Stärke (91,8 %), aber alle Werte liegen nahe genug, dass künftige Rookieentwicklung und reguläre Cut-Retention die Entscheidung umwerfen können. **Kein Faktor ist beschlossen oder als echter Langzeitmarkt bewiesen.**

Der nächste Fachtest muss **in der eingeschwungenen Zielwelt** stattfinden: (a) alternative Rookie-Pool-Größe und Talent-Verteilung; (b) mehr Seeds und 7–10+ Jahre; (c) tatsächliche wöchentliche Injury-/FA-/Trade-/Waiver-Reaktionspfade; (d) **jährlich regulär neu entstehende** Ein-Zyklus-C-add-Retention **getrennt** von historischen Altlasten; (e) Performance-/Criticality-Kurve im neuen dynamischen 10-Team-Veteranenvergleich, aber keine echte Erweiterung vorgeben. Erst nach diesem Zielbildtest wird die reale **Migration** aus 2026er Beständen entworfen.

**Kein aktiver Liga-/App-/Generator-/Sleeper-Wechsel**, keine Veränderung der sechs geschützten Nordstern-Ziele.

### Cross-Check: unabhängiger CP6g-Explorationsprototyp im zentralen Issue

**Während dieser Forschungsarbeit wurde im selben [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) ein weiterer CP6g-Lauf dokumentiert:** Dort wurden **30 synthetische Fünfjahrespfade** mit **nur 30** neuen Rookies/Jahr, anderen Leistungs-/Manager-Heuristiken und einem weniger stark slotvorausschauenden Expansion-Draft exploriert. Auch dort waren die sechs bestehenden Teams cap-konform; die **vier vollständigen und cap-konformen Expansionsteams** gelangen bei **f=0,80 in 2/6**, bei **f=0,75 in 0/6** und bei **f=0,70 in 0/6** der dortigen sechs Läufe. Hier dagegen gelingen sie in 15/15 Läufen über die Faktoren hinweg.

**Die Diskrepanz ist fachlich entscheidend und darf nicht weginterpretiert werden.** Dieses CP6f-Skript stellt bei der neutralen Initialisierung **17 sehr günstige Depth-Plätze pro Team vor den 13 Pflichtstarter-Akquisitionen** bereit, fügt **30 gedraftete + 50 undrafted synthetische Rookies/Jahr** hinzu und erlaubt im Vergleich zu CP6g eine andere Qualität/Preisallokation. CP6g nutzt weniger Spielerzufluss und einen anderen Greedy-/Startup-Pfad. Zudem ist weder die echte zukünftige NFL-Active-/Retirement-Rate, noch der Anteil wirksamer undrafted Talente oder der langfristige Manager-Optimierungsgrad empirisch kalibriert.

Die **4×30-Shadow-Cap-Legalität** im vorliegenden Skript ist eine gültige interne Arithmetikprüfung unter **diesen Annahmen**, **kein** belegter Nachweis, dass der reale 2027er Veteranenmarkt vier Teams tragen würde. Die beiden Piloten sind **nicht** unabhängig kalibrierte Welten mit direkt vergleichbaren Erfolgshäufigkeiten; ihre Quoten dürfen daher nicht gemittelt werden.

**Forschungs-Hard-Gate vor einer konkreten Cap-Empfehlung:** einen gemeinsamen, empirisch begründeten Spielerzufluss/-abfluss (NFL-Active, Retirement, undrafted-Rookies), gleiches Manager-/Optimierungsbudget, dieselbe Criticality-Rang-/Dollarformel und robuste 30er-Slot-Optimierung verwenden und **beide** Prototypen auf denselben Eingaben gegeneinander prüfen. Erst wenn die Ergebnisse dann zusammenlaufen, sollte eine konkrete Cap-Stufe bewertet werden.

## 10. Reproduzieren / technische Abnahme

Am Repository-Root:

\`\`\`bash
node fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs
# Vollständige fünfjährige Matrix + einzelne Saisondetails:
node fantasy-management/league-economy/salary/simulation/cp6f_equilibrium.mjs --json
\`\`\`

Benötigt Node.js mit ESM-Support. Das Skript **liest** nur die beiden bestehenden Repository-Artefakte und schreibt **keine** produktiven Daten. Default: Faktoren 0,90/0,85/0,80/0,75/0,70, Seeds 11/29/47, fünf Zyklen. Für die unabhängige 9-Jahres-Kontrolle kann die exportierte Funktion \`simulate(csvText, draftsText, {seeds:[11],factors:[0.80],seasons:9})\` aufgerufen werden.

**Fachliche Abnahme dieses Piloten:** 15/15 vollständig cap-/slot-konforme Fünfjahres-Szenarien, 15/15 verfügbare 4×30er-Veteranen-Shadow-Kader, mehr Star-/Tier2-Markttiefe bei aggressiveren Faktoren; **keine** Abnahme einer stationären realen Ökonomie, 2027er Preise oder einer verbindlichen Ligaregel.
