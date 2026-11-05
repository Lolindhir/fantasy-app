# CP2a – A/B/C-Cap-Stresstest: Salary-Verteilung versus permanenter Vollzug

> **Stand:** 05.11.2026 · Zentrales [Research-Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) · Anschluss an [CP1](2026-11-05-salary-cap-cp1-baseline.md).
> **Status:** Reproduzierbarer, quantitativer **Proxy- und Transaktions-Stresstest**. **Noch kein vollständig kausaler oder historisch zu exakten Gehaltsstichtagen abgeglichener A/B/C-Backtest. CP2 bleibt daher offen.** Keine neue Ligaregel, keine neue Konzeptentscheidung, keine produktive Daten-/Codeänderung.

## 1. Kontrollierte Szenarien

| Test | Salary | Cap-Vollzug | Was wird isoliert? |
|---|---|---|---|
| **A – Istzustand** | Bereits aktives Performance-Salary | Einmalige Offseason-Deadline | Beobachtete Talentumverteilung und spätere Aufrüstung |
| **B – nur permanentes Cap** | **Exakt dieselben Preise wie A** | Ganzjährig, hypothetisch | Reiner Effekt der Cap-Durchsetzung; keine automatische Salary-Neubewertung |
| **C – Criticality + permanentes Cap** | Führendes isoliertes Criticality/k=1,5-Arbeitsmodell | Ganzjährig, hypothetisch | Wirkung beider Hebel zusammen |
| **D – rechnerische Kontrollvariante** | Dieselben Criticality-Preise wie C | Wie heute, nur Deadline | Trennung des **Formel-Effekts** von der Durchsetzung; gleiche rechnerische Roster-Cap-Belegung wie C |

**Nicht in B/C/D enthalten:** Rookie Contracts (Y1–3), gleitendes Minimum ab Y4, Dead Cap, Top-25/30, Year-4-Optionen, Rollover oder Salary-Retention in Trades. Diese teils bereits **konzeptionell festgelegten**, aber **nicht produktiven** Mechaniken sind gesondert zu testen. In A und C gelten die **gleichen** gehaltenen Spieler aus der realen Historie, nicht vom Modell erfundene „optimale“ Kader.

Die aktive Cap-Formel bleibt für alle Tests strukturell gleich: **6 Teams × 20 relevante Spieler = Top 120**, auf den marktweiten Top-120-Gesamtbetrag ein Faktor **0,9**, danach durch sechs Teams teilen. C kalibriert seinen Cap **endogen** anhand der anderen individuellen Salaries.

## 2. Datenstände und Reproduktionsvertrag

- Ausgangsfreeze Git-Commit **799be2a25203f18face8185303f32b31be3d40a7** (05.11.2026 19:40:24 UTC; Week 8 final).
- Die **1.268** Spielersalaries stammen aus [2026-10-05-salary-simulation-players.csv](2026-10-05-salary-simulation-players.csv) (Blob **96ef8deac5930ffc3dc84dbf12cbbf4719c58489**, 1.268 Zeilen): **A/B** Spalte `salary_published`, **C/D** Spalte `salary_B_k15_ohne_vertraege`. **Nicht** Spalte `salary_C_hauptszenario` (alter vollständiger Entwurf mit inzwischen überholtem additivem Minimum).
- Kader vom 07.06., 09.06., 29.06., 25.08., 09.09. und 05.11. aus den exakt aufgelisteten Git-Commit-Refs in [CP1, Abschnitt 3](2026-11-05-salary-cap-cp1-baseline.md#3-quellen-freeze-und-datenzeitpunkte). Roster-ID pro Team deduplizieren; enthaltene Taxi-/IR-Spieler nicht zusätzlich aufaddieren.
- Transaktionen: [2026er abgeschlossene Transaktionen](https://github.com/Lolindhir/fantasy-app/blob/799be2a25203f18face8185303f32b31be3d40a7/public/data/Transactions.json), Blob **0aa85766a962a9d499fe5610a269771dd3b02ce1**. Status **complete**, nach dem archivierten 09.09.-Commit **20:33:55 UTC** gemäß `EffectiveAt`; **Trades als atomare Zwei-Team-Transfers**, Add und Drop zusammen.
- Kein `SalaryProjected` und keine 2027er Outlook-Salaries; keine unterstellten historischen Tradeangebote, keine angenommenen Salary-Retention-Vereinbarungen.
- **Signifikante Datengrenze G1:** Große historisch datierte Player-Valuation-Derivate für Juni und 2024/2025 sind über die verfügbare GitHub-Textschnittstelle nicht vollständig lesbar. Die Oktober-Preise werden deshalb **transparent rückwirkend** auf alle Kader gelegt. Das erzeugt eine kontrollierte Vergleichsbasis, aber noch **keine historisch exakte individuelle Valuation**.

**Vier Preise/Zeitstände niemals verwechseln:** veröffentlichtes damaliges Juni-Cap **434.255.984 $**, intern aus 05.10.-Spielern neu berechnetes A/B-Cap, aktuelles Live-Cap **427.653.631 $** (05.11., Week 8), und das aktuelle `SalaryCapProjected`. Die folgenden A/B/C-Vergleiche verwenden bewusst die **jeweils vollständige einheitliche 05.10.-Marktpopulation**, nicht wechselnde veröffentlichte Caps.

## 3. Marktvergleich: gleiche Cap-Formel, andere Salary-Struktur

| Kennzahl | A/B (heute) | C/D (Criticality) |
|---|---:|---:|
| Neu berechnetes Cap | **432.611.104 $** | **437.083.780 $** |
| Cap-Differenz zu A | – | +4,47 Mio. $ |
| Anteil der teuersten 10 an den marktweiten Top 120 | 17,4 % | 21,6 % |
| Anteil der teuersten 20 an den marktweiten Top 120 | 30,9 % | 36,2 % |
| Anteil der teuersten 40 an den marktweiten Top 120 | 51,9 % | 56,4 % |
| QB-Anteil an marktweiter Top-120-Salary-Masse | 34,0 % | 30,2 % |
| RB-Anteil an marktweiter Top-120-Salary-Masse | 25,7 % | 27,6 % |
| WR-Anteil an marktweiter Top-120-Salary-Masse | 32,9 % | 33,2 % |
| TE-Anteil an marktweiter Top-120-Salary-Masse | 6,0 % | 7,2 % |
| K-Anteil an marktweiter Top-120-Salary-Masse | 1,3 % | 1,8 % |

Die Criticality-Formel ist **kein pauschaler Cap-Cut**: Das endogene Cap liegt rund 1 % höher, gleichzeitig steigt die Kostenkonzentration auf die Topspieler. Teilweise werden QB aus der mittleren Salary-Spitze günstiger, Elite-WR/RB dagegen teurer. Es kann deshalb mehr Kernbelastung und zugleich günstigere Tiefe geben. **Eine bessere League Economy folgt daraus nicht automatisch.**

## 4. Statische historische Kader-Stresstests – niemals als damalige Regelverstöße lesen

### 4.1 Alle sechs Zeitpunkte: Anzahl Teams und aggregierte positive Cap-Überschreitung

| Kaderstand | über A/B-Cap | über C/D-Cap | Summe positiver Überschreitungen A/B | Summe positiver Überschreitungen C/D |
|---|---:|---:|---:|---:|
| 07.06. | 3/6 | 5/6 | 167,0 Mio. $ | 217,9 Mio. $ |
| 09.06. | 3/6 | 5/6 | 57,9 Mio. $ | 116,6 Mio. $ |
| 29.06. | 1/6 | 3/6 | 1,3 Mio. $ | 69,7 Mio. $ |
| 25.08. | 1/6 | 2/6 | 1,3 Mio. $ | 60,8 Mio. $ |
| 09.09. | 4/6 | 5/6 | 140,5 Mio. $ | 179,6 Mio. $ |
| 05.11. | 5/6 | 5/6 | 193,2 Mio. $ | 264,9 Mio. $ |

**A und B sowie C und D haben jeweils identische statische Cap-Belegungen.** Unterscheiden kann sie erst eine **Transaktionsregel und das daraus mögliche künftige Managerverhalten**. Der B-/C-Vollzug wird deshalb nicht durch eine bloße Prozentanzeige simuliert.

**Sonderfall 29.06.:** Das archivierte Cap betrug 434,26 Mio. $, womit in der CP1-Rückrechnung **0/6** Teams über dem Cap lagen. Die vollständig **neu kalibrierte** 05.10.-A/B-Preismenge ergibt 432,61 Mio. $; Flo liegt damit bei exakt gleicher retrospektiver Roster-Belegung um rund 1,29 Mio. $ darüber. Das ist ein methodischer **Preis-/Cap-As-of-Unterschied**, kein Beweis, dass Flo die geltende Deadline verfehlte. C/D wäre allein durch andere Preise schon vor der Deadline für mehrere Teams deutlich angespannter, müsste also vorab vorbereitet werden.

### 4.2 Team-Stresstest (Salary-Belegung in Mio. $)

| Team | 29.06. A/B | 29.06. C/D | 09.09. A/B | 09.09. C/D | 05.11. A/B | 05.11. C/D |
|---|---:|---:|---:|---:|---:|---:|
| Mighty Giants | 427,2 | 446,0 | 416,8 | 437,7 | 440,5 | 460,0 |
| Ruhr Valley Packers | 427,5 | 472,3 | 465,0 | 499,2 | 460,1 | 496,5 |
| Just Bill | 433,9 | 462,7 | 449,2 | 474,4 | 510,9 | 549,1 |
| Mammoth Marauders | 425,3 | 425,9 | 481,6 | 479,6 | 484,3 | 482,2 |
| Team DennisLACards | 409,6 | 401,0 | 411,2 | 398,7 | 348,2 | 318,8 |
| Team TimpaBay | 429,0 | 437,1 | 475,1 | 474,1 | 460,5 | 462,6 |
| **Modell-Cap** | **432,6** | **437,1** | **432,6** | **437,1** | **432,6** | **437,1** |

Den tatsächlichen **05.11.-Current-Cap-Readmodel-Wert** behandelt [CP1, Abschnitt 4.1](2026-11-05-salary-cap-cp1-baseline.md#gegencheck-mit-dem-aktuellen-w8-cap-readmodel) getrennt. Dort sind **5/6** Teams über dem real veröffentlichten Current Cap, Flo **+83.218.306 $**; hier beträgt Flos Differenz zum **homogenen Modell-Cap** bei A/B etwas weniger. Beides darf nicht summiert werden.

## 5. Draft-Effekt: nicht nur Regular-Season-Transaktionen

Im 2026er Free-Agent-Draft wurden **30** Spieler erfolgreich ausgewählt. Im archivierten Post-Draft-Kader vom 09.09. gehören davon **17** zu den 20 teuersten Spielern ihrer jeweiligen Teams, sowohl mit A- als auch mit C-Bepreisung. Das belegt, dass Draftzugänge in einer permanenten Cap-Regel nicht schlicht als kostenloses Sonderfenster gelten dürfen.

**Direkte Rookie-Grenze der A/B/C-Reihe:** Für **30 von 30 gedrafteten 2026er Rookies** liefert die eingefrorene Preisquelle in **beiden** isolierten Preisvarianten (heutiges Performance-Salary A/B und Criticality ohne Rookie Contracts C/D) ein **Salary von 0 $**. Dies ist ein bestätigter Datensatzbefund, kein neuer Rookie-Salary-Vorschlag. Er macht die A/B/C-Reihe zu einem starken Test für Veteranen-Knappheit und Cap-Vollzug, aber **nicht** zu einem ausreichenden Test für mehrjährige Rookie-Vertragsüberschüsse. Genau dafür existiert der separate, noch nicht produktive dreijährige Rookie-Contract-Konzeptbaustein. Ein beobachteter Nullpreis darf weder mit einem bereits geltenden Y1-Draftvertrag noch mit der ökonomischen Bedeutung eines Taxi-/Rosterplatzes verwechselt werden.

Vom archivierten Vor-FA-Kader vom 25.08. bis zum 09.09. verändern sich die Team-Roster außerdem durch andere Aktivitäten. Die Differenz ist deshalb ein **beobachteter Zeitraum**, nicht die isolierte marginale Wirkung jedes einzelnen Draft-Picks. Die genaue atomare Validierung von Draft-Picks versus nachfolgenden Drops bleibt Teil der späteren fachlichen Cap-Vollzugsspezifikation (Issue #1344, G4).

## 6. Transaktions-Replay nach dem Post-Draft-Freeze

**Stichtag:** Das Post-Draft-League-Snapshot vom 09.09. wurde **20:33:55 UTC** committed. In `Transactions.json` sind alle **54** danach effektiv abgeschlossenen Transaktionen nach `EffectiveAt` sortiert, ohne fehlgeschlagene Claims. Bei jedem Event werden zuerst alle `Drops`, dann alle `Adds` der gesamten Transaktion für alle beteiligten Teams eingetragen. Beide Team-Salarios eines Trades werden **gemeinsam vor und nach dem gesamten Bundle** bewertet.

**Validierung:** Im Replay **0** widersprüchliche Drops/Adds, **0** abweichende PlayerIDs am Ende; alle **sechs** rekonstruierten Roster vom 05.11. stimmen vollständig mit `League.json` überein. Enthalten sind **3** abgeschlossene Trades; andere Bewegungen einschließlich Waiver/FA und reiner Cuts werden nach ihrem tatsächlichen Transaktionstyp verarbeitet.

### 6.1 In welchem Maß wären die beobachteten Schritte unter permanentem Cap erklärungsbedürftig?

| Transaktions-Kennzahl, 09.09. → 05.11. | B, heutige Preise | C, Criticality-Preise |
|---|---:|---:|
| Alle vollständig rekonstruierten Transaktionen | 54 | 54 |
| Bewegungen mit Spielerzugang | 46 | 46 |
| Transaktionen mit **Cap-Anstieg bei Team, das danach über Cap liegt** | 11 | 15 |
| Davon **neue** Grenzüberschreitung aus zuvor legalem Zustand | 1 | 0 |
| Teilnehmer-Bundles, die unter einem **strikten** Post-Event-Cap-Test für alle beteiligten Teams unter Cap enden | 20 | 7 |

**Wichtig für die Interpretation:** Bereits zum 09.09.-Snapshot liegen nach einheitlicher Rückrechnung **4 von 6 Teams (B)** bzw. **5 von 6 Teams (C)** oberhalb des jeweiligen Caps. Ein sturer „Post-Event muss jeder unter Cap sein“-Test würde daher auch verbessernde Cuts oder neutrale Waiver einzelner bereits überlasteter Teams verwerfen. Die Zeile mit vollständig legalem Post-Event-Zustand ist **keine realistische Verbotszahl**. Die engeren **Cap-erhöhenden** Fälle sind ein sinnvolleres **diagnostisches Signal**, aber noch keine Simulation tatsächlich abgelehnter Transaktionen.

Zwei mögliche, **nicht beschlossene** Testsemantiken für bereits oberhalb des Caps liegende Teams: **(i)** nur Cap-senkende/neutrale Vorgänge zur Bereinigung zulassen („No Worsening“), **(ii)** strikte vollständige Compliance für jedes neue Transaktionsbundle. Beide erfordern eine faire Einführung, gemeinsame Trade-Validierung, Taxi-/IR-Definition und einen legalen Anfangszustand. Sie dürfen nicht als bestehende Liga-Policy ausgegeben werden.

### 6.2 Reale Moves mit großer marginaler Top-20-Wirkung

Die Werte sind die **Differenz der Top-20-Teambelegung nach vollständiger Transaktion**, nicht einfach das Salary des hinzukommenden Spielers.

| Datum | Beobachtetes Bundle (betroffenes Team) | Marginal A/B | Marginal C |
|---|---|---:|---:|
| 2026-09-15 | Bryce Young → Ruhr Valley Packers | +9,27 Mio. $ | +6,35 Mio. $ |
| 2026-10-01 | Tyreek Hill → Just Bill | +20,77 Mio. $ | +20,81 Mio. $ |
| 2026-11-03 | Jared Goff → Just Bill | +14,61 Mio. $ | +11,50 Mio. $ |
| 2026-11-03 | Christian McCaffrey → Just Bill | +47,65 Mio. $ | +65,60 Mio. $ |
| 2026-11-05 | D'Andre Swift → Mighty Giants | +13,49 Mio. $ | +13,04 Mio. $ |

Bei Flos CMC-Trade **sinkt** zugleich die Salary-Belegung von Dennis (in derselben atomaren Transaktion); der **Verkäufer** und **Käufer** sind ökonomisch verschieden positioniert. Die hypothetische Legalität des Käufers hängt von seinem vorherigen legalen Cap-Spielraum oder einem zusätzlichen **gleichzeitigen Offset** ab. Die real beobachteten Trades wurden unter dem heutigen Regelwerk abgeschlossen und werden **nicht** rückwirkend beanstandet.

## 7. Wirkliche ökonomische Spannung: bezahlbarer Kern versus austauschbare Tiefe

Zur Prüfung des ursprünglich formulierten Designziels reicht „wie viele Teams über Cap?“ nicht. Wir betrachten deshalb ergänzend die **zehn teuersten Spieler** jedes Teams als eine rein **salary-basierte** Näherung für den ökonomischen Kern. Dieser ist **nicht** automatisch mit zehn besten Starter-/Trade-Assets identisch.

Zwei bewusst extreme, **nur statische** Prüfgrößen:
- **Kernquote:** Salaries der zehn teuersten gehaltenen Spieler dividiert durch das modellierte Team-Cap.
- **Best-Case-Depth-Cuts bei vollständigem Erhalt des Top-10-Kerns:** Außerhalb der zehn teuersten Spieler werden der Reihe nach die teuersten Spieler entfernt und die Top-20-Summe nach jedem Schritt neu bestimmt. Gemessen wird die kleinste Zahl solcher Cut-only-Schritte, um unter dem Cap zu landen. Das ist eine **theoretische Untergrenze für diese festgelegte Strategie**, ohne Neuverpflichtungen, Dead Cap, Marktgebote oder Roster-Mindestbesetzung; es ist **weder** eine geeignete operative Cut-Liste **noch** ein Beweis, welche Starter tatsächlich geopfert würden.

| Team | Kernquote 05.11. A/B | C/D | Best-Case-Depth-Cuts A/B | C/D |
|---|---:|---:|---:|---:|
| Mighty Giants | 69,7 % | 76,0 % | 1 | 3 |
| Ruhr Valley Packers | 78,1 % | 87,6 % | 3 | 10 |
| Just Bill | 87,8 % | 96,8 % | 7 | 14 |
| Mammoth Marauders | 79,5 % | 80,5 % | 5 | 6 |
| Team DennisLACards | 54,6 % | 48,0 % | 0 | 0 |
| Team TimpaBay | 75,2 % | 75,8 % | 3 | 3 |

Flos Entwicklung des Top-10-Kerns:
- **09.09.:** A/B **76.2 %** des Caps, C/D **81.7 %**; im vereinfachten Kern-erhalten-Cutmodell mindestens **2** versus **5** teure Tiefenspieler abgeben.
- **05.11.:** A/B **87.8 %** des Caps, C/D **96.8 %**; im gleichen Extremmodell mindestens **7** versus **14** Tiefenspieler abgeben.

Das passt zu der Hypothese, dass ein positionsrelevanzbasiertes Salary den **Erhalt eines Elitekerns** wirtschaftlich teurer machen kann – ohne dessen Verkauf **fest vorzuschreiben**. Eine weitere mögliche Folge ist gerade, dass Tiefenspieler durch kurzfristig preiswerte Alternativen ersetzt werden; ob daraus **mehr echte Rookie-Entwicklung** wird, zeigt dieser Test **noch nicht**.

### Der Käufermarkt ist ebenfalls zu prüfen

Am 05.11. liegt unter beiden modellierten Preisbasen **nur Dennis** rechnerisch unter Cap. Sein **statischer** rechnerischer Spielraum beträgt bei A/B rund 84,44 Mio. $ und bei C/D rund 118,31 Mio. $. Andere Teams waren in den **beobachteten**, unter heutigen Regeln aufgebauten Rostern bereits über dem Cap. Daraus darf **nicht** gefolgert werden, dass unter einem seit Juni durchgesetzten Cap real nur Dennis Trade-Käufer sein könnte: sämtliche Rosters hätten anders aussehen können.

## 8. Technische Reproduktionskontrakte

**Vollständige Rohdaten bleiben in ihren bestehenden kanonischen Quelldateien.** Dieses Research-Dokument ist eine **datierte Analyse**, keine neue source-of-truth-Definition, kein Ligabeschluss. Rechnen ist ohne neue App-/Salary-Implementierung möglich:

1. Aus dem git-fixierten CSV eine eindeutige PlayerID→A-Salary- und PlayerID→Criticality-B-Salary-Abbildung erstellen; jeweils marktweite **Top 120**, Faktor 0,9, geteilt durch sechs, auf Dollar runden.
2. Für jeden fixierten historischen `League.json`-Roster alle PlayerIDs deduplizieren; die **20 teuersten Werte** aufsummieren. Mit dem jeweils **modellierten** Cap vergleichen. **D hat dieselben Beträge wie C, A dieselben wie B.**
3. Für den Post-FA-Replay **nur** 2026er Transaktionen mit `Status == "complete"` und `EffectiveAt > 2026-09-09T20:33:55Z` chronologisch sortieren (bei gleichen effektiven Zeiten deterministisch nach TransactionID). Transaktionsweise **alle** Spieler-Drops dann **alle** Spieler-Adds ausführen und pro betroffenen Team Vorher-/Nachher-Top-20 messen.
4. Invarianten prüfen: **54** vollständig rekonstruierte Transaktionen, **0** inkonsistente Add/Drop-Referenzen, vollständige **6/6** Endroster-Übereinstimmung mit `public/data/League.json` im Freeze. Unter beiden Preisbasen **28** von **57** betroffenen Team-Sides mit Null-Cap-Änderung, **16** mit positivem und **13** mit negativem Cap-Delta.
5. Draft-Picks werden anhand des archivierten `2026_Free_Agent`-Drafts (30 Picks) und ihres Auftritts in der salary-relevanten Top 20 des 09.09.-Rosters bewertet. Geprüfter Wert: **17** Picks für A und **17** für C in den Top 20.

Für Flo/alle Teams darf ein historisches **geringfügig** abweichendes Cap **nicht** mit dem Modell-Cap gleichgesetzt werden. Ebenso darf eine statische „so viele Cuts zur Optimierung“-Frontier **nicht** als reales Verhalten simuliert werden.

## 9. Fachliches Zwischenfazit und noch offene CP2-Schritte

**Quantitativ gestützt:**
- A: Jährliche Cap-Deadline bewirkt bereits echte Offseason-Entlastung, aber die beobachteten Kader überschreiten später die konstruierte Vergleichsgrenze wieder.
- B: Ein hypothetisch **durchgängig durchgesetztes** Cap würde bei derselben beobachteten Transaktionshistorie **11** Cap-erhöhende Bundles eines danach über Cap liegenden Teams **erklärungsbedürftig** machen; das sind **keine** automatisch zu verbietenden Trades.
- C: Criticality verschiebt Salary stark zur Leistungsspitze, erhöht bei mehreren Contendern den Druck und macht im gleichen Replay **15** solche Bundles erklärungsbedürftig; C ist auch **vor** der Saison teils enger als A.
- Gegenbefund: Teure Starts können weiter möglich sein, solange günstige Tiefe nachrückt; ein permanentes Cap **allein** beweist noch **keinen** hinreichenden Rookie-Entwicklungsanreiz. Hoher Cap-Druck bei vielen Teams könnte zugleich echte Trade-Käufer verknappen.

**Noch offen / nicht als erledigt abhaken:**
- **G1:** Historisch exakte individuelle Salary-Versionen aus großen Derived-Datensätzen lokal prüfen. Der vorhandene Vergleich ist ausdrücklich eine feste **Oktober-Preis-Projektion** auf beobachtete Juni–November-Roster; der historische Cap-Readmodel-Gegencheck vom 05.11. gilt nur für diesen Endstand.
- **G4:** Ausgewogene Einführung eines permanenten Caps (zeitlich nach Deadline), Beginn mit legalem Roster, atomare Trades, Drafts, Waiver-Claims, Taxi/IR, späteres Auto-Cut und Zeit-/Grace-Policy **nur als offene Testsemantik** festhalten.
- **Sportliche Kosten:** Echte Starter- und Ersatzspielerproduktion, Einsatz-/Verletzungsfenster, Transaktionsvolumen nach legalem B-/C-Ausgangsroster und mögliche Trade-Käufer nicht aus Salary allein ableiten.
- **Behaviorszenarien:** Es ist ein **Stresstest der beobachteten Handlungen**, keine kontrafaktische Simulation, welche Mannschaft Flo/Marcel/Dennis bei damals permanentem Cap tatsächlich aufgebaut hätten. Solche Annahmen bedürfen transparenter Grenzen/Alternativen.
- **CP3:** Käuferliquidität, real bepreiste Trade-Alternativen, Rookie-Cut→Re-Add→Breakout, tatsächlich langfristiger Franchise-Wert.

**Entscheidungsstatus:** Noch **keine** Empfehlung, A/B/C als neue Liga-Policy zu beschließen oder bestehende kanonische Rookie-/Dead-Cap-Entwürfe zu ändern. Zentrales [Issue #1344](https://github.com/Lolindhir/fantasy-app/issues/1344) bleibt auf `status:analysis`; **CP2a (Proxy-Belastung und beobachteter Transaktions-Replay) ist erledigt, die vollständige CP2-Entscheidungsbasis noch nicht.**
