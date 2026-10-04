# Salary Criticality Normalization – Centered-25 + Top-10%-Referenz + k=1,5

> **Status:** führendes Arbeitsmodell / persistierter quantitativer Check  
> **Stand:** 02.10.2026  
> **Issue:** #801  
> **Daten-Snapshot:** `public/data/Players.json` Blob `8af230ad446f1f29bbf3774a16909b1aac631ad6`

## 1. Ziel

Nach der Herleitung der rank-basierten Positional-Criticality-Kurven wird geprüft, wie geglättete individuelle Player Performance und rank-basierte Criticality zu einem gemeinsamen Salary-Signal kombiniert werden können.

Das hier dokumentierte Arbeitsmodell ist:

```text
C_ref = Mittelwert der oberen 10 % aller positiven 3Y-Criticality-Rangpunkte
      = 8.6425

M(C) = 0,75 + 0,5 × min(C / C_ref, 1)

SalarySignal = PlayerPerformance × M(C)

Salary unterhalb Signal 20:
Salary = 50 Mio. × (SalarySignal / 20)^1,5

oberhalb Signal 20:
lineare Extrapolation ab 50 Mio. mit Steigung k = 1,5

Salary Cap:
Ø Top-120-Salary × 20 × 0,9
```

Damit bleibt Criticality ein **Modifier auf Performance** und wird nicht zu einem zweiten eigenständigen Performance-Score.

## 2. Warum Top-10%-Mittel als C_ref?

Es existieren 79 positive Criticality-Rangpunkte. Für die Top-10%-Referenz werden die obersten 8 Punkte gemittelt.

Das ergibt:

```text
C_ref = 8.6425
```

Die zuvor geprüften Alternativen waren:

- Maximum: stark durch einen einzelnen Extremwert geprägt;
- P95 nur über positive Werte: robust, sättigt die Spitzengruppe aber früher;
- Top-10%-Mittel: robust gegen einzelne Ausreißer, gut erklärbar und weniger frühe Deckelung.

P95 über **alle** Rank-Punkte wurde bereits verworfen, weil die vielen Nullwerte die Referenz zu weit absenken würden.

## 3. Warum k = 1,5 statt der bisherigen Quadratik k = 2?

Centered-25 vor einer quadratischen Dollar-Kurve verstärkt das Criticality-Signal zusätzlich.

Bei `k = 2` führt ein Signal-Multiplikator von `1,25` unterhalb der 20-Punkte-Referenz näherungsweise zu:

```text
1,25² = 1,5625
```

also rund +56 % Dollar-Salary.

Der Test mit flacheren Exponenten zeigte, dass `k = 1,5` das bisherige gesamte Cap-Niveau fast exakt erhält, während Criticality die Verteilung gezielt korrigiert.

## 4. Gesamtergebnis

| Kennzahl | heutiges System | Arbeitsmodell |
| --- | ---: | ---: |
| Top-120 Ø Salary | 24,13 M | **24,35 M** |
| Salary Cap | 434,26 M | **438,25 M** |
| Cap-Veränderung | – | **0,92 %** |
| Top-120-Grenze | 10,60 M | **10,33 M** |
| Median Top 120 | 21,42 M | **19,18 M** |
| P90 | 41,75 M | **45,32 M** |
| Maximum | 70,13 M | **83,23 M** |

Der zentrale Befund:

> Das Arbeitsmodell verändert das gesamte endogene Cap-Niveau kaum, verteilt die Salary-Masse aber deutlich anders.

## 5. Positionsverteilung im Top-120-Markt

| Position | Spieler Top 120 | Salary-Masse | Anteil | C=0 innerhalb Top 120 |
| --- | ---: | ---: | ---: | ---: |
| QB | 33 | 888,12 M | 30,40 % | 21 |
| RB | 30 | 809,13 M | 27,69 % | 10 |
| WR | 44 | 992,97 M | 33,99 % | 15 |
| TE | 12 | 220,15 M | 7,53 % | 0 |
| K | 1 | 11,33 M | 0,39 % | 0 |

Im heutigen System lagen die Salary-Massen grob bei QB 34,9 %, RB 25,7 %, WR 33,0 % und TE 6,4 %.

Im Arbeitsmodell:

- QB fällt auf **30,40 %**;
- RB steigt auf **27,69 %**;
- WR bleibt mit **33,99 %** nahezu stabil;
- TE steigt auf **7,53 %**;
- K1 Brandon Aubrey rutscht knapp in die Top 120.

Das adressiert das ursprüngliche Problem: QB bleibt als Eliteposition teuer, die breite QB-Mittelklasse bindet aber nicht mehr pauschal unverhältnismäßig viel Cap.

## 6. QB-Kurve

| Rang | Spieler | Performance | Criticality | Modifier | Salary | Cap-Anteil |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| QB1 | Josh Allen | 24,03 | 7,80 | 1,201 | 83,23 M | 18,99 % |
| QB2 | Jalen Hurts | 21,25 | 6,28 | 1,113 | 63,74 M | 14,54 % |
| QB3 | Lamar Jackson | 20,79 | 5,07 | 1,043 | 56,33 M | 12,85 % |
| QB4 | Baker Mayfield | 19,04 | 4,39 | 1,004 | 46,71 M | 10,66 % |
| QB5 | Patrick Mahomes | 18,94 | 3,96 | 0,979 | 44,65 M | 10,19 % |
| QB6 | Jared Goff | 18,82 | 3,21 | 0,936 | 41,31 M | 9,43 % |
| QB7 | Brock Purdy | 18,22 | 2,57 | 0,899 | 37,05 M | 8,45 % |
| QB8 | Dak Prescott | 17,50 | 2,12 | 0,873 | 33,37 M | 7,61 % |
| QB9 | Justin Herbert | 17,38 | 1,63 | 0,844 | 31,44 M | 7,17 % |
| QB10 | Jordan Love | 17,17 | 1,43 | 0,833 | 30,23 M | 6,90 % |
| QB11 | Matthew Stafford | 17,12 | 1,18 | 0,818 | 29,32 M | 6,69 % |
| QB12 | Trevor Lawrence | 16,73 | 0,62 | 0,786 | 26,66 M | 6,08 % |
| QB13 | Joe Burrow | 15,96 | 0,00 | 0,750 | 23,15 M | 5,28 % |

Die Kurve erzeugt keinen künstlichen QB1/QB2-Tier-Sprung. Sie fällt mit Performance und gemessener Criticality kontinuierlich ab.

Besonders relevant:

- QB1/2/3 bleiben echte Premium-Assets;
- um QB4/5 liegt der Modifier ungefähr neutral;
- QB6–12 werden zunehmend günstiger;
- ab QB13 ist Criticality `0`, Performance kann den Spieler trotzdem im relevanten Salary-Markt halten.

## 7. Positionsanker

### RB

| Rang | Spieler | C | Modifier | Salary |
| --- | --- | ---: | ---: | ---: |
| RB1 | Christian McCaffrey | 11,82 | 1,250 | 72,73 M |
| RB3 | Bijan Robinson | 7,47 | 1,182 | 58,14 M |
| RB6 | Saquon Barkley | 5,43 | 1,064 | 42,88 M |
| RB12 | Alvin Kamara | 2,86 | 0,915 | 25,54 M |
| RB18 | Kenneth Walker | 0,74 | 0,793 | 17,47 M |
| RB20 | Tony Pollard | 0,14 | 0,758 | 15,88 M |
| RB21 | Chuba Hubbard | 0,00 | 0,750 | 14,50 M |
| RB24 | Aaron Jones | 0,00 | 0,750 | 13,08 M |
| RB30 | Zach Charbonnet | 0,00 | 0,750 | 10,33 M |

### WR

| Rang | Spieler | C | Modifier | Salary |
| --- | --- | ---: | ---: | ---: |
| WR1 | Ja'Marr Chase | 10,87 | 1,250 | 67,14 M |
| WR3 | Puka Nacua | 6,91 | 1,150 | 55,80 M |
| WR6 | A.J. Brown | 4,85 | 1,031 | 36,87 M |
| WR12 | Keenan Allen | 2,76 | 0,910 | 25,76 M |
| WR20 | Zay Flowers | 1,31 | 0,826 | 19,91 M |
| WR28 | Jakobi Meyers | 0,09 | 0,755 | 15,44 M |
| WR29 | Jaylen Waddle | 0,04 | 0,752 | 14,44 M |
| WR30 | Chris Godwin | 0,00 | 0,750 | 13,93 M |
| WR36 | Jayden Reed | 0,00 | 0,750 | 11,82 M |
| WR44 | Adam Thielen | 0,00 | 0,750 | 10,33 M |

### TE

| Rang | Spieler | C | Modifier | Salary |
| --- | --- | ---: | ---: | ---: |
| TE1 | Trey McBride | 6,79 | 1,143 | 38,81 M |
| TE3 | Travis Kelce | 4,39 | 1,004 | 25,68 M |
| TE6 | David Njoku | 2,54 | 0,897 | 15,30 M |
| TE12 | Hunter Henry | 0,29 | 0,767 | 10,49 M |
| TE13 | Evan Engram | 0,00 | 0,750 | 9,82 M |
| TE18 | Juwan Johnson | 0,00 | 0,750 | 8,36 M |

### K

| Rang | Spieler | C | Modifier | Salary | Top 120 |
| --- | --- | ---: | ---: | ---: | --- |
| K1 | Brandon Aubrey | 1,70 | 0,848 | 11,33 M | ja |
| K3 | Cameron Dicker | 0,69 | 0,790 | 8,95 M | nein |
| K6 | Chase McLaughlin | 0,05 | 0,753 | 7,25 M | nein |
| K7 | Wil Lutz | 0,00 | 0,750 | 7,11 M | nein |
| K12 | Cairo Santos | 0,00 | 0,750 | 6,12 M | nein |

## 8. Übergang zu Criticality 0

Die letzten positiven Rangpunkte liegen bereits sehr nahe am Minimalmodifier `0,75`:

```text
QB12 -> 0,786 ; QB13+ -> 0,750
RB20 -> 0,758 ; RB21+ -> 0,750
WR29 -> 0,752 ; WR30+ -> 0,750
TE12 -> 0,767 ; TE13+ -> 0,750
K6   -> 0,753 ; K7+  -> 0,750
```

Damit entsteht an keiner Positionsgrenze ein harter Salary-Cliff.

Criticality `0` bedeutet außerdem **nicht**, dass der Spieler wertlos ist. Es bedeutet lediglich, dass für diesen Rang in der historischen optimalen ligaweiten Startaufstellung kein positiver marginaler Lineup-Verlust mehr gemessen wurde.

Im neuen Top-120-Markt besitzen **46 Spieler Criticality 0** und bleiben allein über ihre Player Performance relevant.

## 9. Größte Gewinner relativ zum Cap

| Spieler | Pos | alter Salary | neuer Salary | alter Cap-Anteil | neuer Cap-Anteil | Δ Cap-Anteil |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Amon-Ra St. Brown | WR2 | 45,64 M | 64,57 M | 10,51 % | 14,73 % | 4,22 % |
| Ja'Marr Chase | WR1 | 48,30 M | 67,14 M | 11,12 % | 15,32 % | 4,20 % |
| Christian McCaffrey | RB1 | 54,24 M | 72,73 M | 12,49 % | 16,59 % | 4,10 % |
| Jahmyr Gibbs | RB2 | 45,55 M | 62,48 M | 10,49 % | 14,26 % | 3,77 % |
| Bijan Robinson | RB3 | 43,96 M | 58,14 M | 10,12 % | 13,27 % | 3,14 % |
| Josh Allen | QB1 | 70,13 M | 83,23 M | 16,15 % | 18,99 % | 2,84 % |
| De'Von Achane | RB4 | 38,02 M | 50,57 M | 8,76 % | 11,54 % | 2,78 % |
| Puka Nacua | WR3 | 43,90 M | 55,80 M | 10,11 % | 12,73 % | 2,62 % |
| Trey McBride | TE1 | 27,31 M | 38,81 M | 6,29 % | 8,85 % | 2,57 % |
| CeeDee Lamb | WR4 | 40,64 M | 50,05 M | 9,36 % | 11,42 % | 2,06 % |
| Kyren Williams | RB5 | 36,78 M | 45,17 M | 8,47 % | 10,31 % | 1,84 % |
| Jaxon Smith-Njigba | WR5 | 31,96 M | 39,65 M | 7,36 % | 9,05 % | 1,69 % |
| Jalen Hurts | QB2 | 56,27 M | 63,74 M | 12,96 % | 14,54 % | 1,58 % |
| Saquon Barkley | RB6 | 35,98 M | 42,88 M | 8,28 % | 9,78 % | 1,50 % |
| George Kittle | TE2 | 23,01 M | 28,99 M | 5,30 % | 6,61 % | 1,31 % |

## 10. Größte Verlierer relativ zum Cap

| Spieler | Pos | alter Salary | neuer Salary | alter Cap-Anteil | neuer Cap-Anteil | Δ Cap-Anteil |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Joe Burrow | QB13 | 31,83 M | 23,15 M | 7,33 % | 5,28 % | -2,05 % |
| Trevor Lawrence | QB12 | 35,00 M | 26,66 M | 8,06 % | 6,08 % | -1,98 % |
| Bo Nix | QB14 | 31,07 M | 22,73 M | 7,15 % | 5,19 % | -1,97 % |
| Drake Maye | QB15 | 30,21 M | 22,25 M | 6,96 % | 5,08 % | -1,88 % |
| C.J. Stroud | QB16 | 29,93 M | 22,10 M | 6,89 % | 5,04 % | -1,85 % |
| Matthew Stafford | QB11 | 36,65 M | 29,32 M | 8,44 % | 6,69 % | -1,75 % |
| Caleb Williams | QB17 | 27,99 M | 21,02 M | 6,44 % | 4,80 % | -1,65 % |
| Jordan Love | QB10 | 36,86 M | 30,23 M | 8,49 % | 6,90 % | -1,59 % |
| Tua Tagovailoa | QB18 | 26,80 M | 20,35 M | 6,17 % | 4,64 % | -1,53 % |
| Justin Herbert | QB9 | 37,78 M | 31,44 M | 8,70 % | 7,17 % | -1,53 % |
| Geno Smith | QB19 | 25,64 M | 19,68 M | 5,91 % | 4,49 % | -1,41 % |
| Jayden Daniels | QB20 | 24,77 M | 19,18 M | 5,70 % | 4,38 % | -1,33 % |
| Kyler Murray | QB21 | 24,76 M | 19,17 M | 5,70 % | 4,37 % | -1,33 % |
| Sam Darnold | QB22 | 24,16 M | 18,82 M | 5,56 % | 4,29 % | -1,27 % |
| Dak Prescott | QB8 | 38,29 M | 33,37 M | 8,82 % | 7,61 % | -1,20 % |

Der auffällige Cluster bei den Verlierern ist die breite QB-Mittelklasse – genau die Zone, die im bisherigen positionsneutralen Performance-Salary strukturell problematisch war.

## 11. Konzentration der Salary-Masse

| Anteil | heute | Arbeitsmodell |
| --- | ---: | ---: |
| Top 10 | 17,56 % | **21,72 %** |
| Top 20 | 31,19 % | **36,30 %** |
| Top 40 | 52,31 % | **56,71 %** |
| untere 60 der Top 120 | 31,62 % | **28,61 %** |

Das Arbeitsmodell wird damit **gezielter elitär**:

- der reine Performance→Dollar-Exponent wird von 2,0 auf 1,5 reduziert;
- gleichzeitig konzentriert Criticality Salary auf die tatsächlich schwer ersetzbaren Elite-Ränge;
- hohe Rohpunkte allein reichen nicht mehr für dasselbe Premium.

## 12. Top-120-Grenze und Kicker-Effekt

Die einzige Veränderung der Top-120-Mitgliedschaft gegenüber dem heutigen Salary-Ranking ist im aktuellen Snapshot:

- **neu:** Brandon Aubrey (K1), 11,33 M;
- **raus:** Mac Jones (QB34), neues Salary 10,26 M.

Das ist kein Sonderfaktor für Kicker: Aubrey erhält mit seiner Criticality von 1,70 weiterhin einen deutlichen Discount gegenüber neutralem Performance-Salary. Der Eintritt entsteht aus der Kombination aus hoher eigener Performance und der flacheren allgemeinen `k=1,5`-Kurve.

Dieser Boundary-Effekt bleibt explizit Teil späterer Validierung.

## 13. Arbeitsentscheidung

Aktuell führender Kandidat:

```text
Player Performance:
bestehende 3Y-Floor-Logik

Criticality:
3Y rank-basierte Positionskurve

C_ref:
Top-10%-Mittel aller positiven Criticality-Rangpunkte

Criticality Modifier:
Centered-25 = 0,75 bis 1,25

Salary Signal:
PlayerPerformance × Modifier

Performance→Dollar:
k = 1,5 statt k = 2,0

Salary Cap:
weiterhin endogen aus Top 120
```

Dieser Stand ist **noch keine produktive Regeländerung**. Vor Implementierung soll das Modell mit Rookie Contracts, Minimum Salary, Dead Cap und Team-Level-Cap-Strukturen zusammengeführt und als vollständige League Economy validiert werden.

## 14. Reproduzierbarkeit

Die vollständigen Top-120-Zeilen einschließlich Performance, Positionsrang, Criticality, Modifier, SalarySignal, Salary und Cap-Anteil stehen im maschinenlesbaren Begleitfile:

`2026-10-02-criticality-normalization-k15.json`
