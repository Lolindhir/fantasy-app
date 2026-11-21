# CP6j – Full-Cost-Starter/Bank-Sensitivität im 40er-Maximum-Kandidaten

> **19.11.2026 · Forschung, keine aktive oder ratifizierte Ligaregel.** Fortsetzung von [CP6i](2026-11-19-cp6i-starter-ceiling-40er-full-salary.md), Work Package [#1344](https://github.com/Lolindhir/fantasy-app/issues/1344), Draft PR [#1576](https://github.com/Lolindhir/fantasy-app/pull/1576).
>
> Ausführbarer Research-Entwurf: [`cp6j_full_cost_depth.mjs`](../simulation/cp6j_full_cost_depth.mjs). **Einjähriger historischer Sensitivitätstest – kein globaler MILP-Optimumbeweis, keine 2027er Prognose und kein 5-Jahres-Gleichgewicht.**

## 1. Forschungsfrage und Interpretationsgrenze

Wie viel historischer Starter-Qualitätsindex ist bei *vollständiger* Salary-Anrechnung auf **Starter und die tatsächlich finanzierte Bank** erreichbar? Welchen messbaren Preis haben zusätzliche Plätze und bessere Reservequalität?

Der führende, **nicht beschlossene** Designkandidat bleibt: maximal **40 frei belegbare** reguläre Plätze, **keine Belegungspflicht**, voller Salary für alle gehaltenen Spieler, Top-120-Markt-Cap/6 bei Faktor **1,00**, künftig Dynamic Criticality + 3Y-Rookie Contracts + gleitendes 50%-Minimum. Keine stillschweigende Rückkehr zu Top20/f=0,75. **Keine** Änderung der produktiven Liga-, Salary-, Cap-, IR-/Taxi- oder Workflowregeln.

**Mathematischer Kontrollpunkt:** Bei einem reinen 13er-Team sind die vier Obergrenzen 20/30/35/40 gleichwertig. Die nachstehend erzwungenen Belegungen 20/30/35/40 sind **bewusste Managerstrategie-/Versorgungs-Sensitivitäten**, keine neue gesetzliche Mindestbelegung.

## 2. Datiertes Input- und Preisprotokoll

- Fixe Quelle: `analyses/2026-10-05-salary-simulation-players.csv`, Blob-SHA `96ef8deac5930ffc3dc84dbf12cbbf4719c58489`, **1.268** Spielerzeilen, davon **719** mit positivem historischen `performance_3y`-Index und NFL-Team != `FA`. Die historische Qualitätszahl ist keine Week-11- oder 2027-Punktprognose.
- Alle 1.268 Archivzeilen gehen in die **marktweite Top-120-Cap-Basis** ein; bei der Bank sind auch Spieler mit Index 0 zulässig, soweit die vorgeschriebene Reservequalitäts-Schwelle dies erlaubt. In den Startern wird positiver Index verlangt.
- **P:** damaliges `salary_published`, Cap f=1 **480,679 Mio. $**.
- **K:** `salary_I_ohne_base_minimum`, historische Rookie-Draft-Kohorten bereits eingepreist, **ohne** gleitendes Minimum, Cap f=1 **489,862 Mio. $**. Dies ist nicht das fertige neue System.
- **KF:** dieselbe K-/Rookie-Dollarpreiswelt plus 50%-Minimum für Veteranen ab `Player.Year>=4`: `max(P, M+0,5×P)`; Minimum nach NFL-Erfahrung `0,40/0,45/0,50 %` eines ausdrücklich **fixen Modell-Ankers** von **434.255.984 $**. Year 1–3 behalten ihren archivierten Rookie-Dollarvertrag (mit Mindestfloor, kein additiver Aufschlag). Das ist eine **isolierte einjährige Konzept-Sensitivität**, weder mit historisch rekonstruierten originalen Rookie-Cap-Vintages noch mit einem vorwärts endogen gerechneten 2027er Vorjahres-Cap-Anker. Top120-Cap nach diesem partiellen Overlay **489,862 Mio. $**.
- Für alle Welten gilt **volle** Salary-Summe der gehaltenen Spieler als Cap-Anrechnung, kein Top-20-Cap, kein 0,75-Abschlag. Andere Manager werden im Einteam-Test noch nicht allokiert.

## 3. Exakte Anforderungen des Modellkaders

**Starter (13):** 2 QB, 2 RB, 2 WR, 2 TE, 4 FLEX aus RB/WR/TE, 1 K, ohne doppelte Player-IDs.

**Reserveannahme (bei belegter Größe >=18):** zusätzlich mindestens 1 QB, 1 RB, 1 WR, 1 TE, 1 K, die weiteren Bankplätze aus RB/WR/TE. Für jede Bankposition wird jeweils der **billigste noch freie**, qualifizierte NFL-Team-Spieler gewählt. Bench-Index-Cutoffs 0/3/5/8 sind **frei gewählte Stressparameter**, keine empirisch bestätigte echte Starter-Availability, Injury-Fitness oder notwendige Reservequalität. Weder Weekly Bye/Verfügbarkeit noch Salary-Debt, Transaktionskosten, IR/Taxi oder legaler Marktgegenpart werden modelliert.

**Methode:** Für jeden Salary-Shadow-Preis `lambda=0…1` in 10.001 deterministischen Schritten werden 13 Starter auf `Index − lambda × Salary_in_Mio` gerankt und cap-konform um günstigste Positionsdeckung auf der Bank ergänzt. Für die besten gefundenen Kandidaten folgen bis zu sieben Iterationen *eines* profitablen Startertausches, jeweils unter neuer, vollständig berechneter Bank und Cap. Invarianten: genau 13 Starter, zugelassene Positionsmindestanzahlen und 4 FLEX, eindeutige IDs in Starter und Bank, genaue belegte Kadergröße, volle Salary <= Cap, Reservecutoff erfüllt. **Heuristisch erreichbare Untergrenzen, kein globales Maximum.** Zusätzlich sind bei billigsten Bench-Ties mehrere gleichpreisige Kader möglich.

## 4. Ergebnisse – belegbare Indexwerte, nicht Optimalitätsgrenzen

Die Gegenüberstellung mit **gleichem Reserve-Mindestindex 3** isoliert den Preis einer wachsenden tatsächlich belegten Bank. Alle Zahlwerte sind nach der beschriebenen Heuristik **erreichbar**, nicht bewiesen bestmöglich.

| Tatsächliche Kaderbelegung | Starter + Bank | P veröffentlicht | K ohne Minimum | **KF mit gleitendem Minimum** |
|---|---:|---:|---:|---:|
| **13** (Referenz, keine Bank) | 13 + 0 | **221,313** | **212,841** | **212,841** |
| **20** (Index Bank >=3) | 13 + 7 | 219,481 | 211,094 | **211,094** |
| **30** (Index Bank >=3) | 13 + 17 | 216,699 | 209,274 | **209,274** |
| **35** (Index Bank >=3) | 13 + 22 | 215,097 | 207,693 | **207,457** |
| **40** (Index Bank >=3) | 13 + 27 | 213,737 | 206,241 | **206,106** |

**Wichtige Kennzahlen für KF (Mio. $; gerundet):**

| Belegtes Modellteam | Index | gesamte Salary | Bank-Salary | Cap-Rest |
|---|---:|---:|---:|---:|
| 13 | 212,841 | 489,598 | 0,000 | 0,265 |
| 20, Bench >=3 | 211,094 | 484,730 | 10,523 | 5,133 |
| 30, Bench >=3 | 209,274 | 489,797 | 28,274 | 0,065 |
| 35, Bench >=3 | 207,457 | 489,455 | 38,949 | 0,407 |
| 40, Bench >=3 | 206,106 | 489,392 | 51,188 | 0,471 |

**Reservequalität statt bloßer Menge** (KF; exakt 20 belegte Slots):

| Mindestindex jeder der 7 Reserven | gefundener Starterindex | Bankkosten (Mio. $) |
|---|---:|---:|
| 0 (auch nicht produzierende Spieler) | 211,379 | 7,715 |
| 3 | 211,094 | 10,523 |
| 5 | 211,094 | 12,833 |
| 8 | 206,106 | 50,565 |

Ein Index von 3 bedeutet **nicht** automatisch einen NFL-Starter oder einen realistischen Bye-/Injury-Ersatz. Die 40er-Belegung ist ebenso wenig eine Anforderung, 27 Reserve-Spieler dauerhaft zu finanzieren. Der bei KF gemessene Einfluss des Floors auf Nullperformer ist im 20er- und 30er-Qualität0-Szenario wesentlich; dagegen verändert er die Spitzen-Top120-Preissumme hier nicht.

### Wirtschaftliche Interpretation

1. Der einseitige 13er-Extremkader verbraucht fast das gesamte Cap und ist als alleiniger **Saison-Plan** unzureichend. Bereits sieben besetzte Reserveplätze mit positiver Mindestqualität kosten Starterbudget oder erforderliche Umgewichtung.
2. Bei **optional** belegbaren 40 Plätzen kann ein Manager einen 20er-Kader statt 40er-Kader halten; **die maximale Slotzahl wirkt in diesem statischen Index-Test nur über Nutzen/Preis weiterer tatsächlich gehaltener Spieler**.
3. Eine höhere Reservequalitäts-Schwelle kann erheblich teurer sein als fünf weitere Niedrigindex-Bankplätze. Das ist ein konkreter Ansatz für spätere verletzungs-/bye-gewichtete Optimierung.
4. Der scheinbar niedrige Mehrpreis billiger K-Bankkandidaten hängt an der historischen Rookie-/Mindestpreiswelt. Er kann bei Year4-Performance-Repricing, echter Erfahrung, zukünftigen Mindestpreisankern und Gegenbietern erheblich anders ausfallen.
5. Eine **einseitige All-Star-Auswahl aus dem gesamten Spielerpool** zeigt *Konzentrationsfähigkeit*, nicht *erwerbbare Marktposition*: Spieler gehören bereits anderen Managern, Transfers benötigen gültige Bundles, Zustimmung und gleichzeitig legale Gegenseite.

## 5. 5+-Jahres-Gate: noch **nicht** bestanden

Der gesuchte nachhaltige Starterindex bleibt `H5=max_legaler Strategien min(I1… I5)`, ergänzt um normierten jährlichen All-Star-Anteil, Quality-Gap zu Team #2 und paired P10/P50/P90. **Es liegt aus CP6j kein quantifizierter fünfjähriger Maximalindex vor.**

Ein valider passiv/aktiv gepaarter Vergleich benötigt dieselbe initiale sechs-Team-Eigentums-, Cap- und Vertragswelt, separat kontrollierte jährliche ex-ante Informationen, Performance-/Retirement-/Injury-/Bye-Pfade, valide echte Rookie-Year1-Draft-Ränge und jeweilige Year2/3-Dollar-Vintages, Year4-Repricing, gleichzeitige legale Aufnahmen/Abgaben und Counterparty-Akzeptanz sowie jährlich neu erstellte Top120 und Vorjahresminimum. Der frühere [CP6f/g-PR #1511](https://github.com/Lolindhir/fantasy-app/pull/1511) liefert **divergierende Prototypannahmen** (50 zusätzliche undrafted Rookies und vorausschauender Planer vs. andere Expansion). Seine erfolgreichen 5-Jahres-Fälle sind nicht als Beweis für unser neues 40er-/Full-Salary-System übertragbar.

**Kontrollierte Fortsetzungsreihenfolge:**
1. **Independent CLI/CI:** den CP6j-Skriptlauf am Original-CSV-Blob, Vorzeichen-, ID-, 13er-/Positions-/Cap-Invarianten und Quellenhash separat ausführen; Peer-Review und MILP-/CP-SAT-Konkurrenzsolver für obere Grenzen auf *identischer* Preiswelt.
2. **2027er kohärente Preiswelt:** historische Rookie-Cap-Vintages statt konstantem Anker, Player.Year und 3Y-Performance/criticality synchron, vorangehender Cap -> Minimum -> current Salaries -> current Top120-Cap; IR/Taxi/Reserve-Accounting und wirklich startfähige, verletzungs-/bye-spezifische Bench-Profile definieren.
3. **Sechs Manager, keine geschenkten Spieler:** disjunkte Kader, freie Plätze, eigene Cap-Belastung, legitime Käufer/Seller-Bundles und Rookie-/Waiver-/Trade-Assets; Manager dürfen ungleich kompetent sein. 20/30/35/40 als **höchstens** erlaubte Plätze, nicht Zwangsbelegung.
4. **Gepaarte fünf bis zehn Zyklen:** a) passiver Elite-Kern mit ausschließlich legal erforderlichem Cap-/Availability-Handeln; b) aktiver guter Manager mit gleichen Anfangsassets und identischen Szenario-Seeds; vergleichbares Verfolgerverhalten, realistische Marktliquidität, sichtbare Rebuild-/Reload-Alternative, Time-to-Catch-up.
5. **Zweistufige Finanzierungs-/Vollzugsprüfung:** erst ohne Debt/Dead Cap, dann C-add/Retained, Kredit und *echte* Tilgung ohne Refinance sowie Jahresdeadline/F2/F3/permanent mit tatsächlichem Commissioner-Aufwand und definiertem Hard-Failure-Befund.

### Fünf Finanzierungsachsen (Pflichtausweis für diese CP6j-Probe)

| Achse | Hier ausgewiesen |
|---|---|
| Seller-Nettoentlastung / Cut-Retention | **Nicht modelliert** – keine Cuts/Trades |
| Buyer-Gesamtkosten / konkreter Buyer | **Nicht anwendbar** – kein Markttransfer, keine angenommene kostenfreie Akquisition |
| Roster-Kapazität / Taxi-/IR-Simultanmoves | **Nur hypothetische reguläre Slots** als exakte 13/20/30/35/40 Belegung; keine aktive Sleeper-/IR-/Taxi-Ausführbarkeit nachgewiesen |
| Ligaweite Schulden nach Team/Vintage | **Nicht modelliert** – kein Debt-Ledger, nicht als 0 $ Realstand lesen |
| Folgejahresfälligkeit / Tilgung ohne neue Schulden | **Nicht modelliert** – keine fünfjährige Vertrags-/Debt-Simulation |

### Sechs geschützte Nordstern-Ziele – vorläufiger Evidenzstatus

1. **Chancen langfristig:** Einzelteam-Konzentration erstmals mit Bench-Opportunitätskosten belegt, aber kein Sechs-Team-Catch-up.
2. **Gutes Management belohnen:** Freie Bank-/Qualitätsentscheidung erzeugt Handlungsspielraum; kein passiv/aktiv-Test.
3. **Keine zementierte Dominanz:** Höhere Reservequalität fordert budgetäre Abstriche; ob Vorteile nach Reprice 5 Jahre automatisch fortbestehen, offen.
4. **Wirtschaftliche Konsequenzen:** Einjährige volle Salary-Anrechnung und Cap-Bindung beobachtbar; Dead-Cap-/Asset-Folgen offen.
5. **Strategische Freiheit:** Optionales 40er-Maximum erlaubt unterschiedliche Tiefenstrategien; langfristige Rebuild-/Reload-Bewertung offen.
6. **Vollzug:** Berechnungsregeln transparent und deterministisch formuliert, aber weder Live-App-/Sleeper-Vollzug noch Grace-/Hard-Failure- und Operator-Minuten belegt.

**Ratifizierung:** Nordstern ist geschützte Forschungsgrundlage, noch nicht von 6/6 Managern bestätigt. Keine neue verbindliche Ligaregel aus diesem Bericht ableiten.

## 6. Abnahme- und Unsicherheitsregister

- **Durchgeführt:** initiale äquivalente JS-Ausführung auf dem 1.268-Zeilen-Archiv und **erneute Ausführung des exakt im PR gespeicherten CP6j-Sourcecodes** (Blob `b1e52a72cc33c27ecfdfc475ed9a9f4ee7d4e498`) in der verbundenen V8-Laufzeit mit einzigem Adapter für `node:fs`/CLI-Argumente. Alle P/K/KF-Indexzahlen, Team-Summen/ID-/Cap-/Positionsprüfungen und 13er-CP6i-Referenzwerte bestätigt. **Dies ist kein unabhängiger nativer Node-CLI-Lauf im Repository.**
- **Noch nicht durchgeführt:** unabhängiger **Node-CLI-Lauf** des im PR gespeicherten Moduls; CI, Peer-Review, globale Solver-Optimalität, prospektives 2027er Scoring, vollständige reale Rookie-Minimum-Vintage-Kette, disjunkter Markt und gepaarte mehrjährige Simulation.
- **Vermeidung von Überbehauptung:** Alle 13+Bank-Resultate sind *gefundene feasible lower bounds*, die tatsächlichen Maxima können höher sein. Der absolute 13er-All-Star-Index 235,280 bleibt lediglich die unbeschränkte sportliche Oberreferenz dieser historischen Indexwelt.
