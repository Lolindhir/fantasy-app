# Performance Salary Redesign – Research- und Designstand

Status: **offenes Research-/Designpapier**  
Stand: **27.09.2026**

Dieses Dokument hält den aktuellen Diskussions- und Analyse­stand für ein mögliches Redesign des normalen Performance-Salary-Systems fest.

Es ist **keine beschlossene neue Salary-Regel**.

Das bestehende Konzept für Rookie Salary, Minimum Salary und Dead Cap bleibt separat unter:

`fantasy-management/league-context/salary-dead-cap-concept.md`

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
