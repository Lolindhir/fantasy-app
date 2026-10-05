# Salary-Simulation 05.10.2026: Entwurf auf Liga-Scoring durchgerechnet

> Status: Simulation als Datengrundlage für eine Ligaentscheidung. **Nichts davon ist beschlossen.**
> Nachgehalten in Issue #879. Reproduzierbar mit `simulation/salary_simulation.py`.
> Rohdaten: [`2026-10-05-salary-simulation.json`](2026-10-05-salary-simulation.json), Spielertabelle: [`2026-10-05-salary-simulation-players.csv`](2026-10-05-salary-simulation-players.csv) (Semikolon, öffnet in Excel).

## 1. Kurzfassung

- Die heutige Formel lässt sich exakt nachrechnen (1268 Spieler, 0 Abweichungen, Cap 432,6 Mio. wie veröffentlicht).
- Die Criticality-Kurven auf Liga-Scoring sind fast identisch mit dem Tank01-Stand. C_ref sinkt von 8,6425 auf 8,4417.
- Der komplette Entwurf (Szenario C) hebt das Cap von 432,6 auf 478,9 Mio. (+10,7 %). Fast der ganze Anstieg kommt vom additiven Base Minimum (Vergleich C mit I).
- Im Hauptszenario stehen 15 Spieler mit Rookie-Vertrag in den Top 120. Die QB-Masse sinkt deutlich, WR/RB/TE steigen.
- Die Frage, wer in die Positionsränge zählt (C/D/E), verschiebt das Cap um weniger als 0,2 %. Für einzelne TEs macht sie bis etwa 1 Mio. aus.
- Dead Cap aus den echten Cuts wäre an der Deadline 2026 für mehrere Teams spürbar (bis über 20 % des Caps). Die Cuts sind aber unter Regeln ohne Dead Cap entstanden; das Verhalten würde sich ändern.

## 2. Datenbasis und Prüfung

| Quelle | Verwendung |
|---|---|
| `players` | public/data/Players.json (Liga-Scoring seit #347 D4) |
| `league` | public/data/League.json |
| `rookie_drafts` | public/data/past_seasons/Drafts/Drafts_<season>.json |
| `nfl_draft` | source-data/nfl/draft/<season>.json |
| `transactions` | public/data/past_seasons/Transactions/*.json + public/data/Transactions.json |
| `rosters_2025` | source-data/leagues/nfl-reise/seasons/2025/rosters.json |
| `season_2022` | public/data/past_seasons/Players_2022.json (Tank01-PPR, nur für Zyklus 2025) |

Ligaformat aus League.json: 6 Teams, feste Starter QB 12, RB 12, WR 12, TE 12, K 6, FLEX 24, Cap-relevant Top 120 (20 je Team).

## 3. Criticality-Kurven auf Liga-Scoring

Berechnung wie im Redesign-Papier (DMLI je Saison 2023/2024/2025, Rangmittel über drei Jahre). Population sind alle Spieler aus Players.json mit Punkten in der Saison.

| Saison | FLEX-Verteilung | Poolgröße QB/RB/WR/TE/K |
|---|---|---|
| 2023 | RB 6, WR 18 | 157/281/515/250/65 |
| 2024 | RB 9, WR 15 | 157/281/515/250/65 |
| 2025 | RB 10, WR 14 | 157/281/515/250/65 |

3Y-Kurven (Rangpunkte mit Criticality > 0):

```text
QB: QB1 7,78 · QB2 6,28 · QB3 4,99 · QB4 4,48 · QB5 4,08 · QB6 3,27 · QB7 2,70 · QB8 2,08 · QB9 1,70 · QB10 1,54 · QB11 1,12 · QB12 0,58
RB: RB1 11,56 · RB2 7,95 · RB3 7,23 · RB4 6,77 · RB5 5,67 · RB6 5,12 · RB7 4,30 · RB8 3,94 · RB9 3,42 · RB10 3,07 · RB11 2,76 · RB12 2,61 · RB13 2,29 · RB14 2,15 · RB15 1,90 · RB16 1,39 · RB17 0,99 · RB18 0,94 · RB19 0,66 · RB20 0,41 · RB21 0,10 · RB22 0,01
WR: WR1 10,61 · WR2 8,85 · WR3 6,64 · WR4 6,00 · WR5 5,32 · WR6 4,65 · WR7 3,76 · WR8 3,48 · WR9 3,01 · WR10 2,81 · WR11 2,75 · WR12 2,58 · WR13 2,40 · WR14 2,35 · WR15 2,07 · WR16 1,77 · WR17 1,51 · WR18 1,37 · WR19 1,23 · WR20 1,19 · WR21 1,02 · WR22 0,62 · WR23 0,56 · WR24 0,45 · WR25 0,41 · WR26 0,29 · WR27 0,12 · WR28 0,05 · WR29 0,05 · WR30 0,04
TE: TE1 6,79 · TE2 4,75 · TE3 4,41 · TE4 3,28 · TE5 2,88 · TE6 2,52 · TE7 1,76 · TE8 1,57 · TE9 1,26 · TE10 0,92 · TE11 0,58 · TE12 0,37
K: K1 2,10 · K2 1,35 · K3 1,11 · K4 0,69 · K5 0,24 · K6 0,11
```

C_ref (Mittel der oberen 10 % von 82 positiven Rangpunkten, also 8 Punkte): **8,4417** (vorher 8,6425).

## 4. Szenarien

Alle Szenarien außer A rechnen das Cap mit Rückkopplung: Vorjahres-Cap → Minimum und Rookie-Verträge → neues Cap, bis es sich nicht mehr ändert. Startwert ist das heute veröffentlichte Cap.

| Szenario | Cap (Mio.) | ggü. heute | Top-120-Schwelle (Mio.) | QB | RB | WR | TE | K | Rookie-Verträge in Top 120 |
|---|---:|---:|---:|---|---|---|---|---|---:|
| A · Heute (k=2, keine Verträge, kein Minimum) | 432,6 | 0,0 % | 11,4 | 33 · 34 % | 30 · 26 % | 43 · 33 % | 11 · 6 % | 3 · 1 % | 0 |
| B · Criticality + k=1,5, ohne Minimum und Rookie-Verträge | 437,1 | 1,0 % | 10,8 | 33 · 30 % | 30 · 28 % | 42 · 33 % | 11 · 7 % | 4 · 2 % | 0 |
| C · Hauptszenario: Entwurf komplett | 478,9 | 10,7 % | 13,4 | 28 · 27 % | 31 · 28 % | 45 · 35 % | 12 · 8 % | 4 · 2 % | 15 |
| D · wie C, Rang ohne Rookie-Verträge | 479,5 | 10,8 % | 13,4 | 28 · 27 % | 31 · 28 % | 45 · 35 % | 12 · 8 % | 4 · 2 % | 15 |
| E · wie C, Rang ohne Rookie-Verträge und NFL-Free-Agents | 479,2 | 10,8 % | 13,4 | 28 · 27 % | 31 · 28 % | 45 · 35 % | 12 · 8 % | 4 · 2 % | 15 |
| F · wie C, Bandbreite ±15 % | 504,5 | 16,6 % | 15,5 | 30 · 28 % | 31 · 27 % | 43 · 35 % | 12 · 8 % | 4 · 2 % | 13 |
| G · wie C, Bandbreite ±35 % | 456,2 | 5,5 % | 11,7 | 29 · 27 % | 32 · 29 % | 43 · 34 % | 12 · 8 % | 4 · 2 % | 19 |
| H · wie C, aber k=2,0 | 410,6 | -5,1 % | 9,3 | 29 · 28 % | 33 · 30 % | 45 · 35 % | 10 · 6 % | 3 · 1 % | 22 |
| I · wie C, ohne Base Minimum | 440,9 | 1,9 % | 11,5 | 29 · 27 % | 32 · 29 % | 44 · 35 % | 11 · 7 % | 4 · 2 % | 18 |

Positionsspalten: Anzahl Spieler in den Top 120 · Anteil an der Top-120-Salary-Masse.

**Zerlegung des Cap-Anstiegs:** B zeigt nur Criticality und k=1,5, I zusätzlich die Rookie-Verträge, C zusätzlich das Base Minimum.

- heute → B: 1,0 %
- B → I (Rookie-Verträge): 0,9 %
- I → C (Base Minimum): 8,6 %

### Größte Veränderungen einzelner Spieler (C gegenüber heute)

| Spieler | Pos | Year | Vertrag | heute (Mio.) | C (Mio.) | Differenz |
|---|---|---:|---|---:|---:|---:|
| Amon-Ra St. Brown | WR | 6 | performance | 45,4 | 66,5 | +21,1 |
| Ja'Marr Chase | WR | 6 | performance | 48,2 | 69,2 | +21,0 |
| Christian McCaffrey | RB | 10 | performance | 54,0 | 74,9 | +20,9 |
| Jahmyr Gibbs | RB | 4 | performance | 45,3 | 64,0 | +18,8 |
| Josh Allen | QB | 9 | performance | 69,3 | 85,7 | +16,4 |
| Carnell Tate | WR | 1 | rookie | 0,0 | 16,3 | +16,3 |
| Marvin Harrison | WR | 3 | rookie | 8,1 | 24,1 | +15,9 |
| Bijan Robinson | RB | 4 | performance | 43,4 | 59,2 | +15,8 |
| Jeremiyah Love | RB | 1 | rookie | 0,0 | 15,4 | +15,4 |
| De'Von Achane | RB | 4 | performance | 37,9 | 52,0 | +14,2 |
| Bo Nix | QB | 3 | rookie | 30,8 | 7,6 | -23,2 |
| Drake Maye | QB | 3 | rookie | 29,3 | 10,4 | -18,9 |
| Jayden Daniels | QB | 3 | rookie | 24,5 | 12,7 | -11,9 |
| Bucky Irving | RB | 3 | rookie | 12,5 | 3,0 | -9,6 |
| Jaxson Dart | QB | 2 | rookie | 13,8 | 6,5 | -7,3 |
| Joe Burrow | QB | 7 | performance | 31,3 | 25,0 | -6,3 |
| Trevor Lawrence | QB | 6 | performance | 34,0 | 28,2 | -5,8 |
| Caleb Williams | QB | 3 | rookie | 27,5 | 21,8 | -5,7 |
| Tyrone Tracy | RB | 3 | rookie | 7,6 | 2,1 | -5,5 |
| C.J. Stroud | QB | 4 | performance | 28,7 | 23,4 | -5,4 |

### Rang-Population (C, D, E)

Zählen Spieler mit Rookie-Vertrag nicht in den Positionsrang, rücken Veteranen auf. Am stärksten betroffen:

| Spieler | Pos | C (Mio.) | D (Mio.) | E (Mio.) |
|---|---|---:|---:|---:|
| Mark Andrews | TE | 16,2 | 17,3 | 17,3 |
| David Njoku | TE | 17,7 | 18,2 | 18,2 |
| Kyle Pitts | TE | 14,1 | 14,6 | 14,5 |
| T.J. Hockenson | TE | 13,9 | 14,3 | 14,3 |
| Dalton Schultz | TE | 12,1 | 12,6 | 12,6 |
| Jake Ferguson | TE | 14,7 | 15,1 | 15,1 |
| Dallas Goedert | TE | 15,8 | 16,0 | 16,0 |
| Hunter Henry | TE | 13,0 | 13,2 | 13,2 |

## 5. Rookie-Verträge

| Draftjahr | Fantasy-Signal | Fantasy-Pool | NFL-Pool (QB/RB/WR/TE) |
|---|---|---:|---:|
| 2024 | Free-Agent-Draft (nur Rookies, Annahme) | 30 | 77 |
| 2025 | Rookie Draft | 30 | 86 |
| 2026 | Rookie Draft | 30 | 80 |

Die 15 teuersten Rookie-Verträge im Hauptszenario:

| Spieler | Pos | Year | Fantasy-Rang | NFL-Rang | Year1-% | C (Mio.) | heute (Mio.) |
|---|---|---:|---:|---:|---:|---:|---:|
| Marvin Harrison | WR | 3 | 1 | 4 | 3,35 % | 24,1 | 8,1 |
| Malik Nabers | WR | 3 | 2 | 5 | 3,07 % | 22,0 | 14,0 |
| Caleb Williams | QB | 3 | 3 | 1 | 3,04 % | 21,8 | 27,5 |
| Ashton Jeanty | RB | 2 | 1 | 3 | 3,41 % | 20,4 | 11,7 |
| Rome Odunze | WR | 3 | 4 | 7 | 2,56 % | 18,4 | 8,5 |
| Omarion Hampton | RB | 2 | 2 | 8 | 2,97 % | 17,8 | 7,7 |
| Carnell Tate | WR | 1 | 1 | 3 | 3,40 % | 16,3 | 0,0 |
| Brock Bowers | TE | 3 | 5 | 10 | 2,26 % | 16,2 | 15,5 |
| Colston Loveland | TE | 2 | 4 | 5 | 2,67 % | 16,0 | 4,5 |
| Travis Hunter | WR | 2 | 5 | 2 | 2,61 % | 15,6 | 2,4 |
| TreVeyon Henderson | RB | 2 | 3 | 13 | 2,58 % | 15,4 | 7,7 |
| Jeremiyah Love | RB | 1 | 2 | 2 | 3,21 % | 15,4 | 0,0 |
| Cam Ward | QB | 2 | 6 | 1 | 2,49 % | 14,9 | 7,4 |
| Jordyn Tyson | WR | 1 | 3 | 4 | 2,90 % | 13,9 | 0,0 |
| Xavier Worthy | WR | 3 | 7 | 12 | 1,87 % | 13,4 | 7,3 |

## 6. Teams: Cap-Auslastung (Top 20 je Kader, heutige Kader)

| Szenario | Mighty Giants | Ruhr Valley Packers | Just Bill | Mammoth Marauders | Team DennisLACards | Team TimpaBay |
|---|---:|---:|---:|---:|---:|---:|
| A | 97 % | 110 % | 109 % | 112 % | 95 % | 110 % |
| B | 101 % | 116 % | 113 % | 110 % | 91 % | 108 % |
| C | 106 % | 116 % | 111 % | 111 % | 92 % | 107 % |
| D | 106 % | 116 % | 111 % | 111 % | 93 % | 107 % |
| E | 106 % | 117 % | 109 % | 112 % | 93 % | 108 % |
| F | 104 % | 114 % | 109 % | 112 % | 95 % | 107 % |
| G | 108 % | 119 % | 112 % | 110 % | 90 % | 108 % |
| H | 107 % | 120 % | 114 % | 111 % | 87 % | 108 % |
| I | 107 % | 117 % | 111 % | 111 % | 91 % | 108 % |

Die Werte zeigen nur die Größenordnung. In der Saison ist das Cap ohne Bedeutung; geprüft wird erst an der Deadline mit den dann gültigen Kadern.

## 7. Zeitpunkt der Salary-Umstellung

Kader am Ende der Saison 2025, einmal mit Salary-Zyklus 2025 und einmal mit Zyklus 2026 (heutige Formel). Cap Zyklus 2025: 428,8 Mio., Zyklus 2026: 432,6 Mio.

| Team | Zyklus 2025 (Mio.) | Zyklus 2026 (Mio.) | Sprung | Anteil Cap 2025 | Anteil Cap 2026 |
|---|---:|---:|---:|---:|---:|
| Team DennisLACards | 371,3 | 404,6 | +33,3 | 87 % | 94 % |
| Ruhr Valley Packers | 477,3 | 492,8 | +15,4 | 111 % | 114 % |
| Just Bill | 498,4 | 543,0 | +44,6 | 116 % | 126 % |
| Mammoth Marauders | 488,1 | 469,8 | -18,2 | 114 % | 109 % |
| Mighty Giants | 374,0 | 399,8 | +25,8 | 87 % | 92 % |
| Team TimpaBay | 380,2 | 466,2 | +86,0 | 89 % | 108 % |

Gilt das neue Salary ab Offseason-Start, sieht jedes Team diesen Sprung sofort und hat die ganze Offseason für Trades und Cuts. Gilt es erst an der Deadline, kommt der Sprung ohne Reaktionszeit.

## 8. Dead Cap aus echten Cuts

Annahmen: Tenure-Staffel 50/30/15/5 %, Basis ist das zum Cut-Zeitpunkt geltende Salary (Roberts Entscheidung: altes Salary), Retained Salary bei mehrfachen Cuts im selben Zyklus, heutige Salary-Formel auf Liga-Scoring. In-Season-Cuts der Saison S zählen an der Deadline S+1; Offseason-Cuts vor der Deadline nutzen bereits den neuen Zyklus.

### Deadline 2025 (Cuts der Saison 2024)

Nicht berechenbar: Für den Salary-Zyklus 2024 fehlen die Saisons 2021/2022 auf Liga-Scoring. Cuts je Team: Just Bill 9, Mammoth Marauders 3, Mighty Giants 46, Ruhr Valley Packers 16, Team DennisLACards 25, Team TimpaBay 19.

### Deadline 2026 (In-Season 2025 + Offseason 2026)

Referenz-Cap: 432,6 Mio.

| Team | Cuts | Dead Cap (Mio.) | davon In-Season (Mio.) | davon Offseason (Mio.) | Anteil am Cap |
|---|---:|---:|---:|---:|---:|
| Just Bill | 30 | 81,2 | 38,7 | 42,5 | 18,8 % |
| Mammoth Marauders | 19 | 51,5 | 42,3 | 9,2 | 11,9 % |
| Mighty Giants | 30 | 74,6 | 74,6 | 0,0 | 17,2 % |
| Ruhr Valley Packers | 24 | 98,5 | 76,0 | 22,6 | 22,8 % |
| Team DennisLACards | 18 | 31,0 | 26,4 | 4,7 | 7,2 % |
| Team TimpaBay | 14 | 45,9 | 27,7 | 18,2 | 10,6 % |

### Deadline 2027 (Saison 2026 bis heute, unvollständig)

Referenz-Cap: 432,6 Mio.

| Team | Cuts | Dead Cap (Mio.) | davon In-Season (Mio.) | davon Offseason (Mio.) | Anteil am Cap |
|---|---:|---:|---:|---:|---:|
| Just Bill | 3 | 4,0 | 4,0 | 0,0 | 0,9 % |
| Mammoth Marauders | 8 | 11,1 | 11,1 | 0,0 | 2,6 % |
| Mighty Giants | 9 | 19,1 | 19,1 | 0,0 | 4,4 % |
| Ruhr Valley Packers | 4 | 4,8 | 4,8 | 0,0 | 1,1 % |
| Team DennisLACards | 6 | 11,8 | 11,8 | 0,0 | 2,7 % |
| Team TimpaBay | 4 | 3,1 | 3,1 | 0,0 | 0,7 % |

Die zehn größten Einzelposten:

| Spieler | Team | Saison | Zeitpunkt | Tenure | Salary beim Cut (Mio.) | Dead Cap (Mio.) |
|---|---|---:|---|---:|---:|---:|
| Tua Tagovailoa | Ruhr Valley Packers | 2025 | In-Season | 0 | 31,9 | 15,9 |
| Stefon Diggs | Mighty Giants | 2025 | In-Season | 0 | 30,0 | 15,0 |
| Justin Fields | Mighty Giants | 2025 | In-Season | 0 | 29,3 | 14,7 |
| Austin Ekeler | Team TimpaBay | 2025 | In-Season | 0 | 26,8 | 13,4 |
| Brock Purdy | Just Bill | 2026 | Offseason | 1 | 40,7 | 12,2 |
| Geno Smith | Mammoth Marauders | 2025 | In-Season | 0 | 23,5 | 11,7 |
| Sam Darnold | Ruhr Valley Packers | 2025 | In-Season | 0 | 22,5 | 11,3 |
| Geno Smith | Ruhr Valley Packers | 2025 | In-Season | 1 | 33,5 | 10,1 |
| Deebo Samuel | Ruhr Valley Packers | 2026 | Offseason | 0 | 19,8 | 9,9 |
| Daniel Jones | Team DennisLACards | 2025 | In-Season | 0 | 18,8 | 9,4 |

## 9. Annahmen und Datenlücken

- **Population:** Nur Spieler aus dem heutigen Players.json. Zurückgetretene Spieler fehlen in den historischen Kurven; die Kurven der Saisons 2023/2024 können dadurch leicht zu flach sein.
- **Anker-Cap:** Startwert der Rückkopplung ist das heute veröffentlichte Cap. Rookie-Verträge der Jahrgänge 2024/2025 nutzen denselben Anker statt des Caps ihres Draftjahres.
- **Jahrgang 2024:** Die Liga hatte 2024 keinen Rookie Draft. Als Fantasy-Signal zählt die Reihenfolge der Rookies im Free-Agent-Draft 2024.
- **Zyklus 2025:** Für die Saison 2022 gibt es nur das Tank01-PPR-Archiv; mögliche Spiele = 17. Das betrifft nur Timing und Dead Cap der Deadline 2026.
- **Dead Cap:** Die Cuts entstanden unter Regeln ohne Dead Cap. Auto-Cuts der Commissioner lassen sich in den Daten nicht von Manager-Cuts unterscheiden. Die Tenure startet beim ersten bekannten Zugang (Draft oder Transaktion ab 2024).
- **In-Season:** heißt hier jeder Cut nach der Cap Deadline der Saison, also auch in der Preseason. Für 2024 und 2025 gibt es keine Transaktionen vor der Deadline.
- **Projected:** SalaryProjected ist nicht simuliert.

## 10. Fragen für die Liga

1. Soll das Base Minimum additiv bleiben, obwohl es das Cap allein um etwa 8–9 % hebt? Alternative: Minimum nur als Untergrenze.
2. Wie breit soll der Criticality-Modifier sein (±15/25/35 %) und welches k? Szenarien F, G und H zeigen die Spannweite.
3. Wer zählt in die Positionsränge? Der Effekt ist klein, die Regel sollte trotzdem feststehen.
4. Wie mit Dead Cap aus In-Season-Cuts umgehen, die nach Abschnitt 8 einzelne Teams stark belasten würden?
5. Ab wann gilt das neue Salary: Offseason-Start oder Deadline?
6. Wie werden laufende Rookie-Jahrgänge (2024/2025) beim Systemwechsel behandelt?

