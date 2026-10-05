# Performance Salary Redesign – Research- und Designstand

Status: **offenes Research-/Designpapier**  
Stand: **29.09.2026**

Dieses Dokument hält den aktuellen Diskussions- und Analyse­stand für ein mögliches Redesign des normalen Performance-Salary-Systems fest.

Es ist **keine beschlossene neue Salary-Regel**.

Das bestehende Konzept für Rookie Salary, Minimum Salary und Dead Cap bleibt separat unter:

`fantasy-management/league-economy/salary/salary-dead-cap-concept.md`

Die hier dokumentierte Arbeit betrifft primär das normale Performance Salary ab dem Zeitpunkt, an dem ein Spieler nach dem regulären Mehrjahres-Performance-Modell bewertet wird, sowie die daraus entstehende Salary-Cap-Dynamik.

---

## 1. Ausgangspunkt: Was soll das Salary-System eigentlich simulieren?

Das übergeordnete Ziel ist nicht, Fantasy-Salaries einfach proportional zu Fantasy-Punkten zu verteilen.

Das Ziel ist, eine NFL-artige Cap- und Vertragsdynamik zu simulieren:

> Spieler, die für den sportlichen Erfolg eines Rosters besonders kritisch, schwer ersetzbar oder strukturell knapp sind, sollen entsprechend viel Salary binden.

Die reale NFL zahlt Quarterbacks überproportional, weil die Position für praktisch jeden offensiven Snap zentral ist und der Verlust eines Top-QBs eine Saison massiv verändern kann.

Für Fantasy Football ist die Kritikalität aber **nicht identisch mit der realen NFL**:

- ein Fantasy-QB berührt nicht jeden Fantasy-Snap;
- der Wert hängt stark von Starterzahl und Ersatzmarkt ab;
- RB/WR können durch FLEX-Plätze zusätzliche strukturelle Nachfrage erzeugen;
- zwei feste TE-Spots können TE deutlich relevanter machen als in Standardformaten;
- Kicker können trotz solider Rohpunkte sehr leicht ersetzbar sein.

Daraus folgt:

> NFL-ähnliche Salary-Struktur bedeutet nicht, NFL-Positionsgehälter zu kopieren.  
> Entscheidend ist die Fantasy-spezifische Kritikalität innerhalb dieser Liga.

---

## 2. Bestehendes System als Baseline

### 2.1 Performance-Wert pro Saison

Das aktuelle normale Performance Salary basiert je Saison auf einer 50/50-Kombination aus:

```text
SeasonPerformance
= 0,5 × AvgPotentialGame
+ 0,5 × AvgGame
```

Damit werden sowohl Verfügbarkeit/Konstanz als auch reine Produktion pro tatsächlich gespieltem Spiel berücksichtigt.

### 2.2 Drei-Saison-Glättung mit Floor

Für das reguläre Salary werden die letzten drei abgeschlossenen Saisons verwendet.

Das beste der drei Jahre bestimmt einen Floor für die beiden anderen Jahre:

- bestes Jahr = jüngstes Jahr → Floor 50 % des Bestwerts;
- bestes Jahr = mittleres Jahr → Floor 33 %;
- bestes Jahr = ältestes Jahr → Floor 17 %.

Danach werden die drei gefloorten Saisonwerte gemittelt.

### 2.3 Mapping auf Salary

Der geglättete Performance-Wert wird aktuell positionsneutral auf Salary gemappt.

Referenzpunkte:

```text
0 Performance-Punkte  → $0 variabler Performance-Anteil
20 Performance-Punkte → $50.000.000 variabler Performance-Anteil
```

Bis 20 Punkte wird quadratisch skaliert. Werte oberhalb von 20 werden über die bestehende Extrapolationslogik weiter oberhalb von $50 Mio. abgebildet.

Die zentrale Eigenschaft lautet:

> Ein Performance-Punkt ist aktuell unabhängig von der Position gleich viel wert.

Genau diese Positionsneutralität steht nun zur Prüfung.

### 2.4 Salary Cap ist endogen

Wichtig für jede weitere Diskussion:

Das Salary Cap wird **nicht zuerst festgelegt und anschließend auf Spieler verteilt**.

Die Reihenfolge ist:

```text
Player Performance
→ individuelle Player Salaries
→ Top 120 Salaries
→ daraus Salary Cap
```

Aktuell:

- 6 Teams;
- `SalaryRelevantTeamSize = 20`;
- damit 120 salary-relevante Spieler;
- Durchschnitt der Top-120-Salaries;
- × 20;
- × 0,9 Marktspannungsfaktor.

Aktuelles Salary Cap:

```text
$434.255.984
```

Konsequenz:

> Jede neue Salary-Formel verändert automatisch auch das Salary Cap.

Eine Simulation, die lediglich einen bestehenden festen Salary-Kuchen anders verteilt, kann deshalb nur als Diagnose dienen, nicht als produktives Zielmodell.

---

## 3. Ligastruktur und strukturelle Nachfrage

Aktuelle Liga:

- 6 Teams;
- 2 QB;
- 2 RB;
- 2 WR;
- 2 TE;
- 4 FLEX;
- 1 K.

Daraus entstehen ligaweit zunächst:

- 12 feste QB-Startplätze;
- 12 feste RB-Startplätze;
- 12 feste WR-Startplätze;
- 12 feste TE-Startplätze;
- 6 Kicker-Startplätze;
- zusätzlich 24 FLEX-Plätze für RB/WR/TE.

Diese Struktur ist für Positionskritikalität zentral.

Insbesondere ist "Top 12" bei QB unmittelbar die feste Startergruppe. Bei RB/WR/TE ist Top 12 dagegen nur die feste Basis, weil weitere Spieler über 24 FLEX-Plätze gestartet werden.

---

## 4. Produktionsbenchmarks 2025

Ranking direkt nach Fantasy-Punkten pro tatsächlich gespieltem Spiel.

| Position | relevante Gruppe | Ø Top-Gruppe | Cutoff |
| --- | ---: | ---: | ---: |
| QB | Top 12 | 20,52 PPG | 18,36 PPG |
| RB | Top 12 | 19,07 PPG | 15,89 PPG |
| WR | Top 12 | 17,89 PPG | 14,69 PPG |
| TE | Top 12 | 13,14 PPG | 10,86 PPG |
| K | Top 6 | 9,46 PPG | 8,81 PPG |

Beim Kicker verzerren kleine Samples das Roh-Ranking. Mit mindestens 8 Spielen:

- Ø Top 6: **8,97 PPG**
- Cutoff: **7,87 PPG**

Praktische 2025-Benchmarks:

```text
QB ≈ 20,5 PPG durchschnittlicher Top-12-Spieler
RB ≈ 19,1 PPG
WR ≈ 17,9 PPG
TE ≈ 13,1 PPG
K  ≈ 9,0 PPG
```

---

## 5. Produktionsbenchmarks 2024

| Position | relevante Gruppe | Ø Top-Gruppe | Cutoff |
| --- | ---: | ---: | ---: |
| QB | Top 12 | 21,15 PPG | 17,77 PPG |
| RB | Top 12 | 18,52 PPG | 16,98 PPG |
| WR | Top 12 | 18,69 PPG | 16,68 PPG |
| TE | Top 12 | 12,35 PPG | 10,06 PPG |
| K | Top 6 | 9,61 PPG | 8,19 PPG |

Robustheitsnotizen:

- WR 2024 enthält Chris Godwin mit nur 7 Spielen.
- Bei mindestens 8 Spielen liegt der WR-Top-12-Durchschnitt bei **18,44 PPG**, der Cutoff bei **16,67 PPG**.
- Kicker bei mindestens 8 Spielen:
  - Ø Top 6: **8,91 PPG**
  - Cutoff: **8,12 PPG**

### Erste Beobachtung

Die Mittelwerte der relevanten Top-Gruppen sind über 2024 und 2025 relativ stabil:

- QB: rund **20,5–21,2 PPG**
- RB: rund **18,5–19,1 PPG**
- WR: rund **17,9–18,7 PPG**
- TE: rund **12,4–13,1 PPG**
- K: rund **9 PPG**

Das bestätigt, dass QBs absolut viele Fantasy-Punkte produzieren.

Es beantwortet aber noch nicht die wichtigere Frage:

> Wie viel dieser Produktion ist tatsächlich knapp und schwer ersetzbar?

---

## 6. Aktuelle Salary-Verteilung

### 6.1 Top-120-Markt, aus dem das Cap entsteht

Aktuelle Verteilung der Top 120 Salaries:

| Position | Spieler in Top 120 | Salary-Summe | Anteil |
| --- | ---: | ---: | ---: |
| QB | 34 | $1.011,3 Mio. | 34,9 % |
| WR | 44 | $956,2 Mio. | 33,0 % |
| RB | 30 | $742,7 Mio. | 25,7 % |
| TE | 12 | $184,8 Mio. | 6,4 % |
| K | 0 | $0 | 0,0 % |

Auffällig:

> 34 QBs gehören zu den 120 höchsten Salaries, obwohl ligaweit nur 12 feste QB-Startplätze existieren.

Das allein beweist keine Fehlbewertung, weil QB-Depth in einer 2-QB-Liga strategisch relevant ist. Es zeigt aber, wie stark die Position das Cap-System aktuell mitprägt.

### 6.2 Durchschnittliches Salary der 2025 Top-Produzenten

Für die nach 2025-PPG gerankten Top-Gruppen:

| Position | Gruppe | Ø aktuelles Salary |
| --- | ---: | ---: |
| QB | Top 12 | ca. $41,2 Mio. |
| RB | Top 12 | ca. $32,9 Mio. |
| WR | Top 12 | ca. $32,3 Mio. |
| TE | Top 12 | ca. $14,2 Mio. |
| K | Top 6, min. 8 Spiele | ca. $7,3 Mio. |

Zwei durchschnittliche Top-12-QBs binden damit zusammen ungefähr:

```text
$82,3 Mio.
≈ 19 % des aktuellen Team-Salary-Caps
```

### 6.3 Gehaltene QBs ligaweit

Aktuell werden 30 QBs gehalten.

Diese 30 QBs binden zusammen ungefähr:

```text
$852,9 Mio.
```

Das entspricht rund **28,9 %** des gesamten gehaltenen Spieler-Salaries.

Teamweise lag die QB-Belastung zum Analysezeitpunkt zwischen ungefähr:

```text
21,4 % und 44,8 % eines Team-Caps
```

Beispiel Mighty Giants:

- 5 QBs;
- zusammen rund **$109,7 Mio.**;
- etwa **25,3 %** des aktuellen Caps.

---

## 7. Erste VOR-Diagnose

VOR = Value over Replacement.

Die Idee war zunächst, nicht absolute Fantasy-Punkte zu betrachten, sondern:

> Wie viele zusätzliche Punkte liefert ein Spieler gegenüber einem realistisch ersetzbaren Spieler derselben Position?

### 7.1 Flex-aware Replacement-Test auf 2025-PPG

Für einen ersten Diagnoseversuch wurden verwendet:

- QB18: **16,30 PPG**
- RB-Replacement nach festen Slots + FLEX: **12,13 PPG**
- WR-Replacement nach festen Slots + FLEX: **12,18 PPG**
- TE13: **10,75 PPG**

Daraus:

| Position | Ø Top 12 PPG | Replacement | VOR | Ø Salary | VOR je $1 Mio. Salary |
| --- | ---: | ---: | ---: | ---: | ---: |
| QB | 20,52 | 16,30 | +4,22 | $41,2 Mio. | 0,103 |
| RB | 19,07 | 12,13 | +6,94 | $32,9 Mio. | 0,211 |
| WR | 17,89 | 12,18 | +5,71 | $32,3 Mio. | 0,177 |
| TE | 13,14 | 10,75 | +2,39 | $14,2 Mio. | 0,169 |

Anders dargestellt: ungefährer gesamter Salary-Aufwand pro zusätzlichem PPG gegenüber Replacement:

| Position | Salary je +1 VOR-PPG |
| --- | ---: |
| QB | ca. $9,8 Mio. |
| RB | ca. $4,7 Mio. |
| WR | ca. $5,7 Mio. |
| TE | ca. $5,9 Mio. |

Unter **dieser konkreten QB18-Annahme** erscheint QB damit deutlich ineffizienter als RB/WR/TE.

---

## 8. Warum VOR noch keine Lösung ist

Die Replacement-Definition verändert das Ergebnis massiv.

In einer budgetneutralen Diagnose-Simulation wurde ein Teil des Positions-Replacement-Werts vom Performance-Signal abgezogen und der Gesamtmarkt anschließend wieder auf dieselbe Top-120-Salary-Summe normiert.

Mit QB18 als Replacement ergab sich:

| Modell | QB | RB | WR | TE | K |
| --- | ---: | ---: | ---: | ---: | ---: |
| aktuelles Modell | 34,9 % | 25,7 % | 33,0 % | 6,4 % | 0,0 % |
| 50 % VOR-Anpassung | 32,1 % | 27,7 % | 31,9 % | 7,5 % | 0,8 % |
| 75 % VOR-Anpassung | 29,8 % | 30,3 % | 30,9 % | 8,2 % | 0,8 % |
| 100 % VOR | 26,3 % | 36,1 % | 29,4 % | 7,8 % | 0,4 % |

Auf den ersten Blick wirkte 50–75 % Positionsadjustierung plausibel.

Die Sensitivitätsanalyse zeigte aber:

### QB-Anteil bei unterschiedlichem QB-Replacement

| QB-Replacement | 50 % VOR | 75 % VOR | 100 % VOR |
| --- | ---: | ---: | ---: |
| QB18 | 32,1 % | 29,8 % | 26,3 % |
| QB24 | 37,4 % | 39,5 % | 42,0 % |
| QB30 | 40,9 % | 45,6 % | 52,4 % |

Damit ist klar:

> Reines oder starkes VOR ist extrem abhängig davon, wie Replacement definiert wird.

Eine falsche Replacement-Grenze kann die Positionsbewertung sogar in die komplett entgegengesetzte Richtung drehen.

### Wichtige methodische Korrektur

Diese Simulation hielt die gesamte Top-120-Salary-Summe bewusst konstant.

Das war nur sinnvoll, um die **Verteilungswirkung isoliert zu untersuchen**.

Für das echte System wäre dieser Ansatz falsch.

Produktiv muss weiterhin gelten:

```text
neue individuelle Salaries
→ neue Top 120
→ daraus neues Salary Cap
```

Daher ist die VOR-Simulation ein Diagnosewerkzeug, kein vorgeschlagenes Produktionsmodell.

---

## 9. Konkretes QB-Problem im mittleren Bereich

Der bisherige Eindruck ist nicht:

> "Quarterbacks müssen generell billiger werden."

Vielmehr deutet die Analyse auf ein mögliches Problem im **mittleren QB-Bereich** hin.

2025-PPG-Bänder:

| QB-Rang | Ø PPG | Ø aktuelles Salary |
| --- | ---: | ---: |
| QB1–6 | 21,82 | $43,1 Mio. |
| QB7–12 | 19,22 | $39,3 Mio. |
| QB13–18 | 17,18 | $27,8 Mio. |
| QB19–24 | 15,15 | $22,2 Mio. |

Beispiel:

Jared Goff 2025:

- 18,36 PPG;
- aktuelles Salary: ca. **$44,3 Mio.**;
- gegenüber QB18 mit 16,30 PPG nur ungefähr **+2,06 PPG**.

In der ersten Diagnose bedeutete das:

> mehr als $22 Mio. zusätzliches Salary gegenüber dem verwendeten QB18-Referenzspieler für ungefähr zwei zusätzliche Punkte pro Woche.

Das ist genau die Art von Diskrepanz, die das Redesign untersuchen soll.

---

## 10. Empirischer Marktcheck: Cuts vor der 2026 Cap Deadline

Eine besonders wichtige Beobachtung kommt nicht aus einer Modellrechnung, sondern aus dem tatsächlichen Managerverhalten.

Vor der 2026 Cap Deadline wurden reine Cuts betrachtet:

- keine Trades;
- abgeschlossene reine Drops;
- bis einschließlich 30.06.2026.

Gesamt:

- **31 Cuts**
- etwa **$415,0 Mio.** freigesetztes aktives Salary

Nach Position:

| Position | Cuts | freigesetztes Salary | Anteil am Cut-Salary | Ø je Cut |
| --- | ---: | ---: | ---: | ---: |
| QB | 7 | $157,9 Mio. | 38,0 % | $22,6 Mio. |
| WR | 10 | $109,3 Mio. | 26,3 % | $10,9 Mio. |
| RB | 10 | $104,6 Mio. | 25,2 % | $10,5 Mio. |
| TE | 3 | $39,4 Mio. | 9,5 % | $13,1 Mio. |
| K | 1 | $3,8 Mio. | 0,9 % | $3,8 Mio. |

Damit stellten QBs nur 7 von 31 Cuts, erzeugten aber **38 % des gesamten freigesetzten Salaries**.

### Relevante QB-Cuts

| Spieler | Salary | 2025 PPG |
| --- | ---: | ---: |
| C.J. Stroud | $29,9 Mio. | 15,79 |
| Sam Darnold | $24,2 Mio. | 15,41 |
| Brock Purdy | $41,5 Mio. | 22,90 |
| Jared Goff | $44,3 Mio. | 18,36 |
| Jacoby Brissett | $13,3 Mio. | 17,06 |

Zusätzlich wurden Jalen Milroe mit praktisch $0 und Shedeur Sanders mit rund $4,7 Mio. gecuttet.

Ohne diese beiden Low-Salary-Fälle lagen die fünf relevanten QB-Cuts zusammen bei ungefähr:

```text
$153,1 Mio.
≈ $30,6 Mio. pro QB
```

Das bestätigt die praktische Beobachtung:

> Ein QB-Cut war einer der effektivsten Hebel, um schnell sehr viel Cap Space zu schaffen.

---

## 11. Was geschah danach im 2026 Free-Agent-Draft?

Besonders relevant ist, wie stark die gecutteten QBs anschließend tatsächlich nachgefragt wurden.

| Spieler | vorheriger Cut-Salary | Free-Agent-Draft |
| --- | ---: | ---: |
| Brock Purdy | $41,5 Mio. | **1.03 / Overall 3** |
| Jared Goff | $44,3 Mio. | **4.02 / Overall 20** |
| C.J. Stroud | $29,9 Mio. | **5.03 / Overall 27** |
| Sam Darnold | $24,2 Mio. | **5.05 / Overall 29** |
| Jacoby Brissett | $13,3 Mio. | **undrafted** |

Weitere im Draft gezogene QBs:

- Cam Ward: 5.01;
- Malik Willis: 5.06.

### Interpretation

Purdy ist ein wichtiges Gegenbeispiel gegen die These "QB ist generell überbezahlt":

- 22,9 PPG;
- trotz hohem Salary sofort an 1.03 gedraftet.

Das Verhalten passt zu einem **echten Elite-Premium**.

Anders Goff, Stroud und Darnold:

- relativ hohe Salaries;
- dennoch erst sehr spät im Free-Agent-Draft genommen.

Brissett blieb komplett undrafted.

Das spricht dafür, dass zumindest Teile des mittleren QB-Markts:

> mehr Salary freisetzen als ihre tatsächliche Knappheit und Nachfrage rechtfertigen.

Diese Beobachtung ist besonders wichtig, weil sie direkt aus dem Liga-Marktverhalten stammt und nicht nur aus einer theoretischen Value-Formel.

### Einschränkung

Es handelt sich weiterhin um:

- eine einzelne Offseason;
- sechs individuelle Manager;
- konkrete Roster- und Pick-Situationen;
- einen Free-Agent-Draft mit eigener Strategie.

Der 2026 Markt ist deshalb **starke Indikation**, aber noch keine endgültige statistische Kalibrierung.

---

## 12. Aktueller Free-Agent-Pool als zusätzlicher Hinweis

Zum Analysezeitpunkt am 27.09.2026 waren weiterhin mehrere QBs ungerostert, die 2025 brauchbare Produktion gezeigt hatten.

Beispiele:

| Spieler | 2025 PPG | aktuelles Salary |
| --- | ---: | ---: |
| Daniel Jones | 18,26 | $18,6 Mio. |
| Jacoby Brissett | 17,06 | $13,3 Mio. |
| Justin Fields | 16,30 | $21,9 Mio. |
| Geno Smith | 12,79 | $25,6 Mio. |
| Tua Tagovailoa | 12,62 | $26,8 Mio. |

Auch das unterstützt zumindest die Hypothese, dass ein Teil der QB-Produktion leichter ersetzbar ist, als die absoluten Salaries vermuten lassen.

---

## 13. Zentrale Designziele für ein mögliches Redesign

### 13.1 Kritikalität statt bloßer Rohpunkte

Salary soll nicht nur fragen:

> Wie viele Fantasy-Punkte produziert dieser Spieler?

Sondern zusätzlich:

> Wie kritisch ist genau diese Produktion für einen Roster in dieser Liga?

### 13.2 Elite-Premium erhalten

Das System soll echte Difference Maker weiterhin teuer machen.

Purdy im 2026 Free-Agent-Draft ist ein gutes Beispiel:

- starke Produktion;
- hohe Nachfrage;
- frühe Draftpriorität.

Ein Redesign darf Elite-QBs nicht pauschal entwerten.

Dasselbe gilt positionsübergreifend für echte Elite-RB, WR oder TE.

### 13.3 Mittlere Produktion nicht allein wegen Positions-Rohpunkten überbezahlen

Ein Spieler soll nicht automatisch extrem teuer werden, nur weil seine Position generell hohe Fantasy-Rohpunkte produziert.

Der aktuell wichtigste Prüfbereich ist:

> QB7 bis ungefähr QB24.

### 13.4 Keine künstliche Gleichverteilung nach Position

Es gibt **kein** Designziel wie:

```text
QB = 30 %
RB = 30 %
WR = 30 %
...
```

Wenn eine Position real für diese Liga kritischer ist, darf sie mehr Salary binden.

Positionsanteile sind ein Ergebnis, kein Zielwert.

### 13.5 Salary Cap bleibt endogen

Das Grundprinzip bleibt:

```text
Player Salaries zuerst
→ Salary Cap danach
```

Keine feste Gesamt-Salary-Summe soll rückwärts auf Spieler verteilt werden.

### 13.6 Ligastruktur dynamisch berücksichtigen

Die Bewertung sollte soweit möglich aus tatsächlichen Ligaeinstellungen ableitbar sein:

- Teamzahl;
- feste Starter;
- FLEX-Plätze;
- Positionsberechtigung;
- gegebenenfalls tatsächliche Replacement-Tiefe.

Keine dauerhaft hardcodierte Logik wie "QB18 ist immer Replacement", wenn sich das Format ändern kann.

### 13.7 Stabilität über mehrere Jahre

2024 und 2025 zeigen bereits relativ stabile Top-Produktionsniveaus.

Ein zukünftiges Modell sollte:

- mehrere Jahre verwenden;
- kleine Samples nicht überbewerten;
- Verletzungen weiter sinnvoll glätten;
- nicht durch ein einzelnes extremes Jahr vollständig kippen.

Die bestehende Drei-Jahres-/Floor-Logik ist deshalb grundsätzlich weiterhin wertvoll.

### 13.8 Verständlichkeit und Reproduzierbarkeit

Die Formel muss erklärbar bleiben.

Ein Manager sollte grob verstehen können:

- warum ein Spieler teuer ist;
- warum zwei ähnlich punktende Spieler verschiedener Positionen unterschiedlich teuer sein können;
- warum Elite stärker bepreist wird;
- wie daraus anschließend das Cap entsteht.

### 13.9 Kompatibilität mit Rookie Salary und Dead Cap

Ein neues normales Performance-Modell muss mit dem bereits diskutierten Vertragsmodell zusammenspielen.

Insbesondere:

- Rookie Years 1–3 bleiben ein eigener Contract-Mechanismus;
- ab Year 4 Übergang in das normale Performance Salary;
- erfahrungsabhängiges Base Minimum bleibt separat;
- Dead Cap bleibt Retained Salary innerhalb des Salary-Zyklus;
- neues Performance Salary darf diese Mechaniken nicht unbeabsichtigt widersprechen.

---

## 14. Arbeitsbegriff: Positional Criticality

Für die weitere Diskussion wird vorläufig der Begriff **Positional Criticality** verwendet.

Er ist noch **nicht formal definiert**.

Mögliche Bestandteile:

- Anzahl fixer Starterplätze;
- zusätzliche FLEX-Nachfrage;
- Tiefe des realistisch verfügbaren Ersatzmarkts;
- Leistungsabfall Elite → Starter;
- Leistungsabfall Starter → Replacement;
- Knappheit stabiler Produzenten;
- Kosten einer Verletzung / Qualität des Backups;
- tatsächliche Liga-Nachfrage;
- eventuell Marktverhalten aus Cuts, Free-Agent-Drafts und Waivers.

Wichtig:

> Positional Criticality darf nicht einfach mit VOR gleichgesetzt werden.

VOR ist ein möglicher Input bzw. Diagnosewert, nicht zwangsläufig das endgültige Bewertungsmodell.

---

## 15. Denkbare Modellrichtungen – ausdrücklich noch keine Entscheidung

### A. Positionsnormalisierte Performance

Der bestehende Mehrjahres-Performance-Score bleibt erhalten, wird aber gegen typische Positionsproduktion normalisiert.

Beispielidee:

```text
AdjustedPerformance
= Performance / Positionsbenchmark
```

Offen ist, welcher Benchmark geeignet wäre:

- Top-12-Durchschnitt;
- Starter-Cutoff;
- Replacement-Level;
- Perzentil;
- mehrjähriger Mix.

### B. Partielles VOR-Signal

Absolute Performance bleibt Hauptsignal.

Zusätzlich wird ein Teil der Produktion relativ zum Replacement-Level bewertet.

Beispielstruktur:

```text
SalarySignal
= a × AbsolutePerformance
+ b × PositionalValueOverReplacement
```

Die bisherige Analyse zeigt aber klar:

- `b` darf nicht blind hoch gewählt werden;
- Replacement muss robust und dynamisch definiert werden.

### C. Positional-Criticality-Multiplikator

Der bestehende Performance-Score könnte vor der quadratischen Salary-Kurve mit einem dynamischen Positionsfaktor angepasst werden.

Beispielstruktur:

```text
SalarySignal
= Performance × CriticalityFactor(Position, League)
```

Der Faktor dürfte nicht willkürlich festgelegt werden, sondern müsste aus Liga- und Marktstruktur ableitbar sein.

### D. Drop-off-/Scarcity-Modell

Statt eines einzelnen Replacement-Punkts könnte die gesamte Positionskurve betrachtet werden:

- QB1 → QB6;
- QB6 → QB12;
- QB12 → QB18;
- usw.

Dasselbe für RB/WR/TE.

Damit würde Kritikalität eher aus der **Form der Positionsverteilung** entstehen als aus einem einzelnen hart gewählten Replacement-Rang.

Diese Richtung könnte robuster gegen die in der VOR-Simulation beobachtete QB18/QB24/QB30-Sensitivität sein.

### E. Hybrid aus Performance + Marktvalidierung

Die Formel selbst sollte weiterhin objektiv aus Produktions-/Ligadaten berechnet werden.

Tatsächliches Managerverhalten könnte anschließend als Kalibrierung dienen:

- Welche Spieler werden vor Cap Deadline gecuttet?
- Wie viel Cap wird dadurch frei?
- Wie früh werden diese Spieler wieder gedraftet?
- Welche Spieler bleiben trotz hoher Salary-Produktion ungerostert?
- Welche Positionen erzeugen wiederholt Salary-Arbitrage?

Das Marktverhalten würde damit die Formel **validieren**, nicht direkt bestimmen.

---

## 16. Offene Kernfragen

Vor einer neuen Formel müssen insbesondere diese Fragen geklärt werden:

1. **Was bedeutet "kritisch" konkret?**
   - Punkte über Replacement?
   - Starterknappheit?
   - Drop-off-Kurve?
   - Marktknappheit?
   - Mischung daraus?

2. **Was ist Replacement in dieser Liga?**
   - erster Nicht-Starter?
   - QB3 pro Team?
   - tatsächlicher Free-Agent-Pool?
   - dynamisches Perzentil?
   - positionsabhängig unterschiedliche Definition?

3. **Wie verhindern wir selbstverstärkende Effekte?**
   - Wenn Manager QBs wegen aktueller Salary-Regeln horten oder cutten, darf genau dieses Verhalten nicht unkritisch zur Definition ihrer zukünftigen Knappheit werden.

4. **Soll Positionsanpassung vor oder nach der quadratischen Salary-Kurve stattfinden?**

5. **Bleibt die aktuelle 20-Punkte-/50-Mio.-Referenz sinnvoll?**

6. **Bleibt die quadratische Kurve selbst sinnvoll?**
   - Sie erzeugt bewusst Elite-Premium.
   - Gleichzeitig kann sie positionsbedingte Rohpunktunterschiede stark verstärken.

7. **Wie soll Kicker behandelt werden?**
   - Rohpunkte können solide sein;
   - tatsächliche Ersatzbarkeit ist hoch;
   - im aktuellen Top-120-Cap-Pool liegt kein Kicker.

8. **Wie viel Marktverhalten ist ausreichend Evidenz?**
   - 2026 liefert einen starken ersten Test;
   - mehrere Offseasons wären robuster.

9. **Wie soll SalaryProjected dieselbe Logik nutzen?**
   - Grundmodell sollte zwischen normalem Salary und Projected Salary konsistent bleiben.

10. **Wie wird die neue Formel rückwirkend getestet?**
    - mindestens 2024 und 2025;
    - historische Roster-/Cut-Situationen soweit verfügbar;
    - 2026 Cap-Cuts und Free-Agent-Draft als konkreter Marktcheck.

---

## 17. Vorgeschlagene Validierungsmaßstäbe für spätere Modelle

Eine Kandidatenformel sollte nicht nur nach "schönen" Salary-Anteilen bewertet werden.

Stattdessen sollten mindestens folgende Tests durchgeführt werden:

### Produktionslogik

- Elite-Spieler bleiben klar teurer als Mittelmaß.
- Kleine Leistungsunterschiede im mittleren Bereich erzeugen keine unverhältnismäßigen Salary-Sprünge.

### Positionslogik

- Salary spiegelt tatsächliche Starter- und Ersatzknappheit wider.
- Keine Position wird nur wegen hoher Rohpunktbasis automatisch dominant.
- Keine künstliche Gleichverteilung erzwingen.

### Marktlogik

- Sehr teure Spieler sollten normalerweise auch schwer ersetzbar bzw. stark nachgefragt sein.
- Wiederholtes Muster "riesiger Cap-Cut, danach spät oder gar nicht gedraftet" ist ein Warnsignal.
- Elite-Spieler dürfen trotz hoher Salaries früh priorisiert werden.

### Cap-Logik

Nach jeder Kandidatenformel:

```text
alle Salaries neu berechnen
→ Top 120 neu bestimmen
→ Salary Cap neu berechnen
```

Keine budgetneutrale Rückskalierung als produktives Modell.

### Stabilität

- 2024 und 2025 vergleichen;
- mehrere Replacement-Definitionen als Sensitivität testen;
- kleine Samples kennzeichnen;
- keine Formel auf einen einzelnen Spieler oder eine einzelne Offseason overfitten.

---

## 18. Aktuelle Arbeitshypothese

Der bisherige Stand lässt sich so zusammenfassen:

> Das bestehende Salary-System scheint absolute Fantasy-Produktion sinnvoll zu erfassen, bildet aber Positionskritikalität möglicherweise unzureichend ab.

Der aktuell stärkste konkrete Verdacht lautet:

> Insbesondere mittlere bis gute Quarterbacks können überproportional viel Salary binden, weil ihre ohnehin hohe positionsbedingte Rohproduktion durch die positionsneutrale und überproportionale Salary-Kurve stark monetarisiert wird, obwohl vergleichbarer Ersatz teilweise ausreichend verfügbar ist.

Gleichzeitig zeigt Brock Purdy im 2026 Free-Agent-Draft:

> Ein echter Elite-QB kann weiterhin sehr knapp und sehr wertvoll sein.

Daher lautet die aktuelle Designrichtung **nicht**:

```text
QB pauschal billiger machen
```

sondern:

```text
Salary stärker an tatsächlicher Fantasy-Kritikalität kalibrieren,
ohne Elite-Premium und NFL-artigen Cap-Druck zu verlieren.
```

---

## 19. Noch nicht entschieden

Explizit **nicht** beschlossen sind derzeit:

- eine neue Salary-Formel;
- ein fester Positionsmultiplikator;
- QB18, QB24 oder QB30 als Replacement;
- eine bestimmte VOR-Gewichtung;
- ein Zielanteil für QB/RB/WR/TE am Salary-Markt;
- eine Änderung der quadratischen Kurve;
- eine Änderung der Top-120-Cap-Berechnung;
- eine Änderung an Rookie Salary;
- eine Änderung an Dead Cap;
- eine Änderung am Minimum Salary.

Dieses Dokument dient als Ausgangspunkt für die nächste Designphase.

---

## 20. Empirische Positionskurven 2024/2025

Als nächster Schritt wurde die reine Produktionsverteilung vermessen, bewusst **noch ohne Salary-Mapping**.

Methodik:

- Rankings nach Fantasy-Punkten pro tatsächlich gespieltem Spiel;
- mindestens 8 Spiele, um sehr kleine Samples zu begrenzen;
- QB/RB/WR/TE: Elite-Gruppe = Top 6;
- K: Elite-Gruppe = Top 3;
- fixe Starterplätze aus dem aktuellen Ligaformat;
- die 24 FLEX-Plätze werden pro Saison automatisch an die besten verbleibenden RB/WR/TE vergeben;
- anschließend werden effektive Startergrenze und die nächsten sechs Depth-Spieler betrachtet.

### 2025

FLEX-Verteilung:

```text
11 RB
13 WR
0 TE
```

Damit lagen die effektiven Startergrenzen 2025 bei:

- QB12: **18,36 PPG**
- RB23: **13,06 PPG**
- WR25: **12,30 PPG**
- TE12: **10,86 PPG**
- K6: **7,87 PPG**

### 2024

FLEX-Verteilung:

```text
9 RB
15 WR
0 TE
```

Effektive Startergrenzen:

- QB12: **17,77 PPG**
- RB21: **13,51 PPG**
- WR27: **13,62 PPG**
- TE12: **10,06 PPG**
- K6: **8,12 PPG**

### Zweijahres-Sicht

| Position | Ø Elite | Ø effektive Startergrenze | Ø nächste 6 Depth | Elite → Grenze | Grenze → Depth |
| --- | ---: | ---: | ---: | ---: | ---: |
| QB | 22,60 | 18,06 | 16,95 | +4,54 | +1,11 |
| RB | 20,78 | 13,29 | 11,89 | +7,50 | +1,39 |
| WR | 19,86 | 12,96 | 12,52 | +6,90 | +0,45 |
| TE | 14,53 | 10,46 | 9,50 | +4,06 | +0,96 |
| K | 9,61 | 7,99 | 7,78 | +1,61 | +0,22 |

Die effektive Startertiefe lag dabei im Zweijahresbild ungefähr bei:

- QB: **12**
- RB: **22**
- WR: **26**
- TE: **12**
- K: **6**

### Interpretation der Kurvenform

#### QB: hoher Peak, danach relativ schnelle Kompression

Elite-QBs besitzen einen klaren Vorteil gegenüber der Startergrenze. Hinter QB12 wird die Kurve dagegen deutlich flacher.

Das unterstützt die bisherige Hypothese:

> Elite-QB kann ein sehr hohes Premium verdienen, ohne dass automatisch der gesamte QB7–QB24-Bereich ähnlich teuer sein muss.

#### RB: breiteste Knappheit

RB zeigt:

- einen sehr großen Elite-Vorteil;
- hohe effektive Startertiefe durch FLEX;
- den stärksten Drop von Startergrenze zu Depth unter den betrachteten Skill-Positionen.

Damit ist RB nicht nur an der Spitze wertvoll, sondern über einen vergleichsweise breiten Bereich strukturell knapp.

#### WR: Elite sehr wertvoll, Mitte sehr tief

WR besitzt ebenfalls ein großes Elite-Premium.

Gleichzeitig ist der Übergang von der effektiven Startergrenze zur nächsten Depth-Schicht extrem flach:

```text
ca. 0,45 PPG
```

Die vielen FLEX-Plätze machen WR breit relevant, aber der tiefe Spielerpool reduziert die Knappheit im mittleren Bereich.

#### TE: top-heavy durch Pflichtstarter

TE erhält seine Kritikalität vor allem aus:

- zwei festen TE-Spots pro Team;
- einem deutlichen Elite-Vorteil.

In beiden betrachteten Jahren ging dagegen **kein zusätzlicher FLEX-Platz an TE**.

Damit ist TE eher top-heavy als breit knapp.

#### K: sehr flache Austauschbarkeit

Zwischen K6 und der nächsten Depth-Gruppe liegen im Zweijahresmittel nur rund:

```text
0,22 PPG
```

Das spricht für sehr geringe strukturelle Kritikalität außerhalb weniger kleiner Elite-Unterschiede.

### Vorläufige Kurvencharakterisierung

| Position | Kurvencharakter |
| --- | --- |
| QB | hoher Elite-Peak, danach schnelle Kompression |
| RB | steil und über relativ viele Spieler knapp |
| WR | hoher Elite-Peak, tiefe und flache Mitte |
| TE | top-heavy, moderate Starterknappheit |
| K | fast vollständig flach |

Diese Charakterisierung ist **keine feste Positionsbewertung**, sondern nur die beobachtete Form der 2024/2025-Daten.

---

## 21. Geklärte Designrichtung: Criticality wird jährlich dynamisch berechnet

Eine feste Tabelle wie

```text
QB = 0,85
RB = 1,10
WR = ...
```

soll ausdrücklich **nicht** das Zielmodell sein.

Stattdessen soll Positional Criticality in jedem Salary-Zyklus neu aus zwei objektiven Inputs entstehen:

```text
aktuelles Ligaformat
+
historische Produktionsverteilungen
```

Daraus folgt eine jährlich neu berechnete Positions- und Qualitätskurve.

### Grundprinzip

```text
League Settings des kommenden Salary-Zyklus
+ historische abgeschlossene Player-Performance
→ dynamische Positional-Criticality-Kurven

individuelle Mehrjahres-Performance
+ Position des Spielers auf seiner Criticality-Kurve
→ Performance-Salary

alle Player Salaries
→ Top 120 Salaries
→ neues Salary Cap
```

Damit bleibt das Salary Cap weiterhin **endogen**.

### Keine statische Positionskritikalität

Criticality soll nicht bedeuten:

> "QB ist immer X % wichtiger als WR."

Sondern:

> "Wie kritisch ist dieses konkrete Leistungsniveau auf dieser Position unter dem aktuell geltenden Ligaformat?"

Damit ist Criticality zugleich:

- positionsabhängig;
- leistungsabhängig;
- ligaformatabhängig;
- jährlich neu kalibriert.

---

## 22. Aktuelles Ligaformat bewertet historische Produktion

Für die Salary-Berechnung eines neuen Zyklus soll das **Ligaformat gelten, für das das neue Salary benutzt wird**.

Historische Produktionsdaten bleiben unverändert, werden aber unter dem aktuellen Ziel-Format neu interpretiert.

Beispiel:

Die Liga besitzt heute:

```text
6 Teams × 2 QB = 12 fixe QB-Starter
```

Würde die Liga zukünftig auf drei Quarterbacks pro Team umstellen:

```text
6 Teams × 3 QB = 18 fixe QB-Starter
```

Dann soll kein manueller QB-Faktor angepasst werden.

Stattdessen wird die historische QB-Produktion automatisch unter einer Nachfrage von **18 festen QB-Startern** ausgewertet.

Die relevante QB-Kurve verschiebt sich dadurch tiefer in den Pool und die gemessene Knappheit kann automatisch steigen.

Dasselbe Prinzip gilt für:

- mehr oder weniger FLEX-Plätze;
- zusätzliche oder reduzierte TE-Spots;
- veränderte Teamzahl;
- andere Positionsberechtigungen für FLEX;
- sonstige relevante Starterstrukturänderungen.

---

## 23. Dynamische FLEX-Verteilung

FLEX-Nachfrage soll nicht per fixer Positionsquote hinterlegt werden.

Für jede historische Saison wird zunächst die feste Nachfrage erfüllt.

Danach werden die vorhandenen FLEX-Plätze an die besten verbleibenden FLEX-berechtigten Spieler dieser Saison vergeben.

Dadurch kann sich die effektive Startertiefe jedes Jahr natürlich verändern.

Beispiel aus den bisherigen Daten:

```text
2024:
9 RB + 15 WR + 0 TE in FLEX

2025:
11 RB + 13 WR + 0 TE in FLEX
```

Damit reagiert das Modell sowohl auf das Ligaformat als auch auf die tatsächliche Leistungslandschaft der NFL.

---

## 24. Auch die NFL-Leistungslandschaft darf Positionswerte verändern

Ein zentraler gewünschter Effekt ist, dass sich Positionskritikalität ohne Regeländerung verschieben kann.

### Beispiel: tiefer QB-Pool

Entstehen mehrere Jahre mit sehr vielen produktiven Quarterbacks:

- die QB-Kurve wird tiefer und flacher;
- brauchbarer Ersatz verbessert sich;
- Mid-Tier-QBs werden relativ weniger kritisch;
- ihr Salary-Premium kann automatisch komprimieren.

### Beispiel: knapper RB-Pool

Gibt es dagegen nur wenige produktive Running Backs:

- die RB-Kurve wird steiler;
- Ersatz hinter den relevanten Starter-/FLEX-Plätzen fällt stärker ab;
- gute RBs werden automatisch kritischer;
- Salary-Premium kann steigen.

Damit bildet die Formel nicht nur eine statische Fantasy-Theorie ab, sondern kann auf Veränderungen der realen NFL-Spielerlandschaft reagieren.

---

## 25. Architekturpräzisierung: Criticality gehört zur Position und zum Leistungsrang

Die nach den ersten DMLI-Tests präzisierte Architektur trennt zwei Ebenen bewusst voneinander.

### Ebene A: individuelle Player Performance

Die individuelle Performance eines Spielers bleibt das bereits bestehende Mehrjahressignal.

Für jede abgeschlossene Saison gilt weiterhin:

```text
SeasonPerformance
= 0,5 × AvgPotentialGame
+ 0,5 × AvgGame
```

Für das normale Performance Salary werden die drei abgeschlossenen Saisons anschließend weiterhin mit der bestehenden Player-Floor-Logik geglättet:

- liegt der beste Wert in der neuesten Saison, beträgt der Floor 50 % dieses Bestwerts;
- liegt der beste Wert in der mittleren Saison, beträgt der Floor 33 %;
- liegt der beste Wert in der ältesten Saison, beträgt der Floor 17 %;
- jeder der drei Saisonwerte wird mindestens auf diesen Floor angehoben;
- anschließend wird der Mittelwert der drei gefloorten Werte gebildet.

Diese Logik bleibt **spielerindividuell**. Sie schützt insbesondere vor einer übermäßigen Salary-Reaktion auf eine einzelne verletzungsbedingt schwache Saison.

### Ebene B: Positional Criticality

Criticality wird dagegen **nicht als persönliche Historie eines Spielers** geführt.

Historische Spieler dienen ausschließlich als Messpunkte für die Frage:

> Wie kritisch war in dieser Saison Rang X innerhalb einer Position unter dem heute gültigen Ligaformat?

Nach der saisonalen Messung wird die Spieleridentität für die Criticality-Kurve verworfen.

Dadurch entsteht beispielsweise nicht:

```text
Josh Allen besitzt historische Criticality X
```

sondern:

```text
QB1-Level besitzt historische Criticality X
QB2-Level besitzt historische Criticality Y
...
```

Für einen späteren Salary-Zyklus wird zunächst die individuelle geglättete Player Performance bestimmt. Daraus folgt der aktuelle Leistungsrang innerhalb der Position. Dieser Rang verweist anschließend auf die geglättete Criticality-Kurve der Position.

Damit gilt konzeptionell:

```text
individuelle 3Y Performance mit Player Floor
→ aktueller Positionsrang

historische DMLI-Messungen
→ 3Y Criticality-Kurve je Position und Rang

Positionsrang
→ Criticality am entsprechenden Punkt der Kurve
```

Criticality bewertet damit **die strukturelle Bedeutung eines Leistungsniveaus**, nicht noch einmal die persönliche Verletzungs- oder Karrierehistorie desselben Spielers.

---

## 26. Formale Definition: Dynamic Marginal Lineup Impact als Messverfahren

Für eine historische Saison `y` wird zunächst für jeden Spieler `i` die bestehende saisonale Performance berechnet:

```text
P(i,y)
= 0,5 × AvgPotentialGame(i,y)
+ 0,5 × AvgGame(i,y)
```

Danach wird unter dem **aktuellen Ziel-Ligaformat** die optimale synthetische ligaweite Startaufstellung bestimmt.

```text
L(y)
= maximal erreichbare Summe der SeasonPerformance
  über alle ligaweiten Starterplätze
```

Die Optimierung berücksichtigt:

- alle festen Positionsslots;
- die aktuelle Teamzahl;
- alle FLEX-Slots;
- die aktuelle FLEX-Berechtigung;
- die tatsächliche historische Produktionsverteilung dieser Saison.

Für jeden Spieler wird anschließend exakt dieser Spieler aus dem Pool entfernt und die komplette Aufstellung neu optimiert:

```text
DMLI(i,y)
= L(y) - L(-i,y)
```

Der Wert misst damit den tatsächlichen marginalen Lineup-Verlust, den das Entfernen dieses Spielers unter dem aktuellen Format erzeugt.

### Abstraktion auf Positionsrang

Innerhalb jeder Position werden die Spieler derselben Saison nach `SeasonPerformance` absteigend sortiert.

Sei:

```text
i(p,r,y)
= Spieler auf Position p,
  Leistungsrang r,
  Saison y
```

Dann wird die saisonale Criticality-Kurve definiert als:

```text
C(p,r,y)
= DMLI(i(p,r,y), y)
```

Ab diesem Schritt ist die konkrete Spieleridentität für Criticality nicht mehr relevant.

Fällt Rang `r` in einer Saison außerhalb der optimalen ligaweiten Startaufstellung, ist sein DMLI definitionsgemäß `0`. Dieser Nullwert bleibt Bestandteil der späteren Mehrjahresglättung.

### Drei-Jahres-Glättung

Die aktuelle Architekturentscheidung verwendet die drei letzten abgeschlossenen Saisons gleichgewichtet:

```text
C3Y(p,r)
= [C(p,r,y-2) + C(p,r,y-1) + C(p,r,y)] / 3
```

Für den Salary-Zyklus 2026 werden damit verwendet:

```text
2023 + 2024 + 2025
```

Es gibt **keinen Criticality-Floor**.

### Keine harten Tiers in der Berechnung

Begriffe wie:

- Elite;
- High Starter;
- Starter;
- Replacement

dürfen später zur Erklärung oder Darstellung verwendet werden.

Die Berechnung selbst nutzt jedoch die vollständige Rank-Kurve. Dadurch entsteht kein künstlicher Sprung zwischen beispielsweise QB3 und QB4.

Bei exakt gebundenen aktuellen Player-Performance-Werten sollen die betroffenen Spieler denselben Criticality-Wert erhalten; dafür wird im späteren technischen Mapping der Mittelwert der durch den Tie belegten Rank-Punkte verwendet.

---

## 27. Warum der Player Floor nicht auf Criticality übertragen wird

Der bestehende Performance-Floor und die neue Criticality-Glättung lösen unterschiedliche Probleme.

### Player Performance

Der Floor beantwortet:

> Wie vermeiden wir, dass eine einzelne schlechte oder verletzungsbedingt verkürzte Saison einen etablierten Spieler übermäßig stark abwertet?

Das ist eine **spielerindividuelle Stabilitätsregel**.

### Criticality

Die Criticality-Kurve beantwortet dagegen:

> Wie wertvoll war Rang X dieser Position relativ zur gesamten verfügbaren Produktionslandschaft?

Eine einzelne Verletzung verändert dabei lediglich, **welcher Spieler** einen bestimmten Rang einnimmt. Die Criticality-Historie gehört nicht dem verletzten Spieler selbst.

Deshalb wird Criticality nur rankweise über mehrere Saisons gemittelt.

Diese Trennung verhindert insbesondere eine doppelte Verletzungsbestrafung:

```text
Verletzung
→ beeinflusst individuelle Player Performance
→ wird dort bereits durch den bestehenden Floor geglättet

Verletzung
≠ zusätzliche persönliche Criticality-Abwertung
```

---

## 28. Sample-Behandlung

Für die formale Criticality-Berechnung wird **kein zusätzlicher Mindestspiele-Filter** verwendet.

Grund:

`AvgPotentialGame` ist bereits Bestandteil von `SeasonPerformance` und reduziert den Saisonwert eines Spielers automatisch, wenn er einen großen Teil der Saison verpasst.

Ein zusätzlicher harter Filter wie `mindestens 8 Spiele` würde deshalb eine zweite, diskrete Availability-Regel einführen.

Der Backtest 2023–2025 zeigt dabei keinen problematischen Small-Sample-Effekt in der optimalen ligaweiten Startaufstellung:

- 2023: kein optimaler Starter mit weniger als 8 Spielen;
- 2024: nur Chris Godwin mit 7 Spielen;
- 2025: kein optimaler Starter mit weniger als 8 Spielen.

Damit bleibt die bestehende availability-adjusted SeasonPerformance vorerst die einzige Sample-/Availability-Behandlung.

---

## 29. Berechnungsbasis 2023–2025

Das aktuelle Ligaformat wurde für diese Berechnung erneut aus `public/data/League.json` abgeleitet.

Aktuell gilt ligaweit:

```text
6 Teams
12 QB fixe Starter
12 RB fixe Starter
12 WR fixe Starter
12 TE fixe Starter
24 FLEX
6 K
```

Die FLEX-Verteilung entsteht in jeder historischen Saison neu aus der Optimierung.

| Saison | FLEX RB | FLEX WR | FLEX TE | QB Grenze / nächster | RB Grenze / nächster | WR Grenze / nächster | TE Grenze / nächster | K Grenze / nächster |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 7 | 17 | 0 | 17,43 / 17,13 | 12,74 / 12,70 | 12,85 / 12,72 | 9,41 / 8,79 | 7,69 / 7,63 |
| 2024 | 8 | 16 | 0 | 17,77 / 16,40 | 13,09 / 12,69 | 12,77 / 12,76 | 9,24 / 9,09 | 8,12 / 8,06 |
| 2025 | 8 | 16 | 0 | 17,17 / 16,98 | 11,30 / 11,21 | 11,31 / 11,16 | 10,51 / 10,40 | 7,69 / 7,67 |

Damit ergab sich die effektive Startertiefe:

```text
2023: QB12 / RB19 / WR29 / TE12 / K6
2024: QB12 / RB20 / WR28 / TE12 / K6
2025: QB12 / RB20 / WR28 / TE12 / K6
```

Die Verteilung wird nicht gespeichert oder vorgegeben. Sie ist jeweils nur das Ergebnis aus Ligaformat und historischer SeasonPerformance.

---

## 30. Drei-Jahres-Criticality 2023–2025

Die folgende Tabelle zeigt ausgewählte Ankerpunkte der vollständigen Rank-Kurven.

| Rangpunkt | 2023 | 2024 | 2025 | 3Y Ø |
| --- | ---: | ---: | ---: | ---: |
| QB1 | 7,16 | 9,62 | 6,62 | **7,80** |
| QB3 | 4,38 | 6,90 | 3,94 | **5,07** |
| QB6 | 2,15 | 4,60 | 2,89 | **3,21** |
| QB12 | 0,30 | 1,37 | 0,20 | **0,62** |
| RB1 | 11,86 | 9,51 | 14,10 | **11,82** |
| RB3 | 4,63 | 6,64 | 11,13 | **7,47** |
| RB6 | 3,52 | 5,01 | 7,77 | **5,43** |
| RB12 | 1,44 | 3,04 | 4,09 | **2,86** |
| RB18 | 0,22 | 1,13 | 0,86 | **0,74** |
| RB20 | 0,00 | 0,33 | 0,09 | **0,14** |
| WR1 | 10,39 | 10,83 | 11,40 | **10,87** |
| WR3 | 6,94 | 6,21 | 7,59 | **6,91** |
| WR6 | 5,05 | 3,91 | 5,60 | **4,85** |
| WR12 | 2,96 | 2,61 | 2,70 | **2,76** |
| WR20 | 1,28 | 1,39 | 1,27 | **1,31** |
| WR28 | 0,16 | 0,01 | 0,10 | **0,09** |
| WR29 | 0,13 | 0,00 | 0,00 | **0,04** |
| TE1 | 5,45 | 6,44 | 8,50 | **6,79** |
| TE3 | 5,30 | 5,78 | 2,08 | **4,39** |
| TE6 | 3,91 | 2,30 | 1,41 | **2,54** |
| TE12 | 0,62 | 0,15 | 0,11 | **0,29** |
| K1 | 1,49 | 1,32 | 2,27 | **1,70** |
| K3 | 0,38 | 0,34 | 1,37 | **0,69** |
| K6 | 0,07 | 0,06 | 0,02 | **0,05** |

### Vollständige geglättete QB-Kurve

```text
QB1 7,80 · QB2 6,28 · QB3 5,07 · QB4 4,39 · QB5 3,96 · QB6 3,21 · QB7 2,57 · QB8 2,12 · QB9 1,63 · QB10 1,43 · QB11 1,18 · QB12 0,62
QB13+ 0,00
```

### Vollständige geglättete RB-Kurve

```text
RB1 11,82 · RB2 8,16 · RB3 7,47 · RB4 7,01 · RB5 5,87 · RB6 5,43 · RB7 4,62 · RB8 4,22 · RB9 3,67 · RB10 3,30 · RB11 3,02 · RB12 2,86 · RB13 2,46 · RB14 2,44 · RB15 2,23 · RB16 1,76 · RB17 1,29 · RB18 0,74 · RB19 0,21 · RB20 0,14
RB21+ 0,00
```

### Vollständige geglättete WR-Kurve

```text
WR1 10,87 · WR2 9,10 · WR3 6,91 · WR4 6,22 · WR5 5,56 · WR6 4,85 · WR7 3,99 · WR8 3,72 · WR9 3,22 · WR10 3,07 · WR11 2,89 · WR12 2,76 · WR13 2,62 · WR14 2,36 · WR15 2,13 · WR16 1,92 · WR17 1,71 · WR18 1,53 · WR19 1,43 · WR20 1,31 · WR21 1,00 · WR22 0,84 · WR23 0,71 · WR24 0,65 · WR25 0,58 · WR26 0,34 · WR27 0,18 · WR28 0,09 · WR29 0,04
WR30+ 0,00
```

### Vollständige geglättete TE-Kurve

```text
TE1 6,79 · TE2 4,75 · TE3 4,39 · TE4 3,30 · TE5 2,89 · TE6 2,54 · TE7 1,87 · TE8 1,62 · TE9 1,24 · TE10 0,92 · TE11 0,53 · TE12 0,29
TE13+ 0,00
```

### Vollständige geglättete K-Kurve

```text
K1 1,70 · K2 0,94 · K3 0,69 · K4 0,55 · K5 0,11 · K6 0,05
K7+ 0,00
```

Diese Werte sind **noch keine Salary-Zuschläge in Dollar und keine Positionsmultiplikatoren**. Sie sind ausschließlich die dimensionsgleichen marginalen Performance-Verluste, die aus der ligaweiten Lineup-Optimierung entstehen.

---

## 31. Interpretation der Drei-Jahres-Kurven

### QB

Die geglättete QB-Kurve beginnt bei:

```text
QB1  7,80
QB3  5,07
QB6  3,21
QB9  1,63
QB12 0,62
QB13 0,00
```

Damit bleibt ein klares Elite-Premium erhalten, während die Kurve Richtung letzter fester Starter stark komprimiert.

Das adressiert direkt den Ausgangsverdacht des Salary-Redesigns:

> Ein Elite-QB kann strukturell sehr kritisch sein, ohne dass jeder solide QB automatisch ein ähnlich hohes Positionspremium erhalten muss.

### RB

RB besitzt die breiteste hohe Criticality:

```text
RB1  11,82
RB3   7,47
RB6   5,43
RB12  2,86
RB18  0,74
RB20  0,14
RB21  0,00
```

Die vier FLEX-Spots pro Team verlängern die relevante RB-Kurve deutlich über die zwölf festen RB-Starter hinaus.

### WR

WR besitzt ebenfalls ein sehr hohes Elite-Premium, fällt im mittleren und hinteren Bereich aber deutlich flacher ab:

```text
WR1  10,87
WR3   6,91
WR6   4,85
WR12  2,76
WR20  1,31
WR28  0,09
WR29  0,04
WR30  0,00
```

Das bildet gleichzeitig hohe Elite-Relevanz und die große Breite brauchbarer WR-Produktion ab.

### TE

TE bleibt klar top-heavy:

```text
TE1  6,80
TE3  4,39
TE6  2,54
TE9  1,24
TE12 0,29
TE13 0,00
```

Da in keiner der drei Saisons ein FLEX-Platz an TE ging, entsteht Criticality ausschließlich aus den zwölf festen TE-Slots.

### K

Kicker werden fast vollständig komprimiert:

```text
K1 1,70
K3 0,69
K5 0,11
K6 0,05
K7 0,00
```

Damit erzeugt die Methode ohne Sonderregel genau die gewünschte hohe Austauschbarkeit der Position.

---

## 32. Geklärte Architektur nach dem Drei-Jahres-Test

Der aktuelle Stand lautet damit:

```text
A) historische abgeschlossene Saison
   ↓
SeasonPerformance aller Spieler
   ↓
aktuelles Ziel-Ligaformat
   ↓
optimale ligaweite Startaufstellung
   ↓
DMLI je historischem Spieler
   ↓
Abstraktion auf Position + SeasonPerformance-Rang
   ↓
saisonale Criticality-Kurve

B) 2023 / 2024 / 2025 Rank-by-Rank mitteln
   ↓
3Y Positional Criticality Curve

C) individueller Spieler
   ↓
3Y Player Performance mit bestehendem Floor
   ↓
aktueller Rang innerhalb seiner Position
   ↓
Criticality aus der 3Y Positionskurve
```

Damit ist Criticality:

- nicht spielerhistorisch;
- nicht als fester Positionsfaktor gespeichert;
- positionsabhängig;
- leistungsrangabhängig;
- ligaformatabhängig;
- aus mehreren NFL-Saisons geglättet;
- automatisch FLEX-sensitiv;
- automatisch auf Formatänderungen reagierend.

---

## 33. Nächste Modellfrage: Performance + Criticality

Nach der Herleitung der rank-basierten Criticality-Kurven war die nächste offene Ebene:

> **Wie werden geglättete individuelle Player Performance und die dem aktuellen Positionsrang zugeordnete Criticality zu einem gemeinsamen Salary-Signal kombiniert?**

Diese Frage wurde am 02.10.2026 quantitativ weitergeführt. Der daraus entstandene führende Arbeitsstand ist in den folgenden Abschnitten dokumentiert.

---

## 34. Führendes Arbeitsmodell: Criticality als Performance-Modifier

Criticality bleibt ein Modifier auf individuelle Player Performance und wird **nicht** als zweiter eigenständiger Performance-Score addiert.

Die Normalisierungsreferenz wird aus den positiven Drei-Jahres-Criticality-Rangpunkten abgeleitet:

```text
C_ref
= Mittelwert der oberen 10 % aller positiven C3Y-Rangpunkte
```

Im aktuellen 2023–2025-Snapshot existieren 79 positive Rangpunkte. Die oberen 10 % entsprechen damit acht Rangpunkten.

Aktuell ergibt sich:

```text
C_ref = 8,6425
```

Der Modifier wird als **Centered-25** definiert:

```text
M(C)
= 0,75 + 0,5 × min(C / C_ref, 1)
```

Damit gilt:

```text
C = 0       -> Modifier 0,75
C = C_ref/2 -> Modifier 1,00
C >= C_ref  -> Modifier 1,25
```

Das gemeinsame Salary-Signal lautet:

```text
SalarySignal
= PlayerPerformance × M(C)
```

Dadurch entscheidet Player Performance weiterhin über die individuelle Qualität des Spielers, während Criticality beschreibt, wie stark diese Qualität im aktuellen Ligaformat ökonomisch gewichtet werden soll.

### Warum Top-10%-Mittel?

Verglichen wurden unter anderem:

- Maximum;
- P95 nur über positive Criticality-Rangpunkte;
- Top-3-Mittel;
- Top-10%-Mittel.

P95 über alle Rangpunkte wurde früh verworfen, weil nur 79 von 570 betrachteten Rangpunkten positive Criticality besitzen und die vielen Nullwerte die Referenz dadurch künstlich niedrig setzen würden.

Das Maximum reagiert stark auf einen einzelnen Extremwert.

Positive-P95 und Top-10%-Mittel sind deutlich robuster. Das Top-10%-Mittel bleibt zusätzlich leicht erklärbar, deckelt die Spitzengruppe weniger früh als P95 und wird deshalb als führende Referenz verwendet.

---

## 35. Performance-zu-Dollar-Kurve: k = 1,5

Die bisherige Salary-Kurve verwendet unterhalb der 20-Punkte-Referenz eine quadratische Abbildung mit:

```text
k = 2,0
```

Centered-25 wird jedoch **vor** dieser Dollar-Abbildung angewendet.

Damit würde beispielsweise ein Signal-Multiplikator von `1,25` unterhalb der Referenz bei `k = 2` näherungsweise zu folgendem Dollar-Effekt führen:

```text
1,25² = 1,5625
```

also rund +56 %.

Damit würden Criticality-Modifier und quadratische Elite-Spreizung teilweise dieselbe Funktion doppelt erfüllen.

Der getestete führende Arbeitswert ist deshalb:

```text
k = 1,5
```

Unterhalb der Referenz:

```text
Salary
= 50.000.000 × (SalarySignal / 20)^1,5
```

Oberhalb von `SalarySignal = 20` bleibt die bestehende Architektur einer linearen Extrapolation ab 50 Mio. erhalten, nun mit der Steigung `k = 1,5`.

Damit werden die Aufgaben klarer getrennt:

```text
Player Performance
-> individuelle Produktionsqualität

Criticality
-> ligaformatspezifische ökonomische Relevanz dieser Qualität

k
-> allgemeine Spreizung des Salary-Marktes
```

---

## 36. Vollmarkt-Test 02.10.2026

Der vollständige Test wurde mit der aktuellen `public/data/Players.json`-Population durchgeführt.

Vollständige reproduzierbare Detailanalyse:

- `fantasy-management/analyses/2026/league-meta/salary-efficiency/2026-10-02-criticality-normalization-k15.md`
- `fantasy-management/analyses/2026/league-meta/salary-efficiency/2026-10-02-criticality-normalization-k15.json`

Das JSON enthält zusätzlich die vollständige Top-120-Tabelle mit:

- Player Performance;
- Positionsrang;
- Criticality;
- Modifier;
- SalarySignal;
- Salary;
- Cap-Anteil.

### Endogenes Salary Cap

Der Marktcheck ergab:

```text
heutiges Top-120-Cap: 434,26 Mio.
Arbeitsmodell:         438,25 Mio.
Veränderung:             +0,92 %
```

Damit verändert das Modell die gesamte verfügbare Salary-Masse praktisch nicht, sondern verteilt sie primär neu.

### Positionsanteile der Top-120-Salary-Masse

Aktuell ungefähr:

```text
QB  34,9 %
RB  25,7 %
WR  33,0 %
TE   6,4 %
K    0,0 %
```

Arbeitsmodell:

```text
QB  30,4 %
RB  27,7 %
WR  34,0 %
TE   7,5 %
K    0,4 %
```

Damit wird insbesondere die breite QB-Mittelklasse entlastet, ohne Elite-QB pauschal billig zu machen.

### QB-Anker

```text
QB1  Josh Allen        83,23 Mio.
QB2  Jalen Hurts       63,74 Mio.
QB3  Lamar Jackson     56,33 Mio.
QB4  Baker Mayfield    46,71 Mio.
QB5  Patrick Mahomes   44,65 Mio.
QB6  Jared Goff        41,31 Mio.
QB7  Brock Purdy       37,05 Mio.
QB8  Dak Prescott      33,37 Mio.
QB9  Justin Herbert    31,44 Mio.
QB10 Jordan Love       30,23 Mio.
QB11 Matthew Stafford  29,32 Mio.
QB12 Trevor Lawrence   26,66 Mio.
QB13 Joe Burrow        23,15 Mio.
```

### Weitere Positionsanker

```text
RB1  Christian McCaffrey 72,73 Mio.
RB3  Bijan Robinson      58,14 Mio.
RB6  Saquon Barkley      42,88 Mio.
RB12 Alvin Kamara        25,54 Mio.
RB20 Tony Pollard        15,88 Mio.

WR1  Ja'Marr Chase       67,14 Mio.
WR3  Puka Nacua          55,80 Mio.
WR6  A.J. Brown          36,87 Mio.
WR12 Keenan Allen        25,76 Mio.
WR20 Zay Flowers         19,91 Mio.
WR28 Jakobi Meyers       15,44 Mio.

TE1  Trey McBride        38,81 Mio.
TE3  Travis Kelce        25,68 Mio.
TE6  David Njoku         15,30 Mio.
TE12 Hunter Henry        10,49 Mio.
```

### Übergang zu Criticality 0

Die letzten positiven Rangpunkte liegen bereits nahe am Minimalmodifier:

```text
QB12 -> 0,786 ; QB13+ -> 0,750
RB20 -> 0,758 ; RB21+ -> 0,750
WR29 -> 0,752 ; WR30+ -> 0,750
TE12 -> 0,767 ; TE13+ -> 0,750
K6   -> 0,753 ; K7+  -> 0,750
```

Es entsteht damit kein harter Salary-Cliff am Ende einer Criticality-Kurve.

Im Top-120-Markt bleiben 46 Spieler mit `Criticality = 0` allein über ihre Player Performance relevant.

### Konzentration

Das Arbeitsmodell konzentriert Salary gezielter auf die Spitze:

```text
                  heute   Arbeitsmodell
Top 10            17,6 %      21,7 %
Top 20            31,2 %      36,3 %
Top 40            52,3 %      56,7 %
untere 60/Top120  31,6 %      28,6 %
```

Das ist trotz des flacheren Exponenten kein Widerspruch.

Der allgemeine Performance-Exponent wird reduziert, während Criticality gezielt diejenigen Elite-Ränge aufwertet, deren Produktion im Ligaformat besonders schwer ersetzbar ist.

Die Architektur wird damit **gezielter elitär statt pauschal punkte-elitär**.

### Sichtbarer Boundary-Effekt

Im aktuellen Snapshot tritt genau ein neuer Spieler in die Top 120 ein:

```text
Brandon Aubrey (K1)
```

und verdrängt:

```text
Mac Jones (QB34)
```

Aubrey erhält trotz seines Eintritts einen Criticality-Discount; der Effekt entsteht aus hoher eigener Performance plus der flacheren allgemeinen `k = 1,5`-Kurve.

Dieser Effekt bleibt explizit Teil späterer Validierung.

---

## 37. Aktueller Modellstatus

Führender Arbeitsstand:

```text
Player Performance
= bestehende 3Y-Floor-Logik

Criticality
= 3Y rank-basierte Positionskurve

C_ref
= Top-10%-Mittel positiver Criticality-Rangpunkte
= aktuell 8,6425

Criticality Modifier
= Centered-25
= 0,75 bis 1,25

SalarySignal
= PlayerPerformance × CriticalityModifier

Performance -> Dollar
= k 1,5 statt k 2,0

Salary Cap
= weiterhin endogen aus den Top 120
```

Dieser Stand ist fachlich der führende Kandidat und soll nicht mehr nur als Chat-Experiment behandelt werden.

Er ist dennoch **noch keine produktive Regeländerung**.

Vor der technischen Implementierung folgt die systemweite Validierung zusammen mit:

- Rookie Contracts;
- Minimum Salary;
- Dead Cap;
- Team-Level-Cap-Strukturen;
- gewünschter Team-Window-Ökonomie.

---

Geklärt sind damit zwei aufeinander aufbauende Architekturentscheidungen:

> **Positional Criticality ist eine jährlich neu berechnete und über drei Saisons geglättete Rank-Kurve je Position. Historische Spieler liefern lediglich die saisonalen Messpunkte; individuelle Salary-Spieler werden erst über ihren geglätteten aktuellen Positionsrang auf diese Kurve abgebildet.**

> **Im führenden Salary-Arbeitsmodell modifiziert diese Criticality die individuelle Player Performance über Centered-25 mit einer Top-10%-Referenz; die anschließende Performance-zu-Dollar-Kurve verwendet k = 1,5.**
