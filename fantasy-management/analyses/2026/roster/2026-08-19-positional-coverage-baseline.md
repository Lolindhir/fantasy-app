# Mighty Giants Positional Coverage Baseline – 2026-08-19

Status: datierte Roster-Analyse. Konkrete Coverage-Zielzahlen und Spielerzuordnungen sind **keine permanente Wahrheit**. Die Methode ist in `fantasy-management/_ai/ROSTER_ARCHITECTURE.md` kanonisch.

## Quellenzustand

- `public/data/League.json` @ blob `00957a261eea27db831ca400e84b1fc3e1e098f5`
- `fantasy-management/analyses/2026/roster/2026-08-19-roster-role-security-baseline.md`
- `fantasy-management/analyses/2026/roster/2026-08-19-taxi-prelock-clarification.md`

Taxi-Phase: `pre_lock`. Die aktuelle technische Taxi-Belegung ist deshalb für die strategische Positions-Coverage nicht fest; alle Taxi-eligible Rookies können vor dem ersten Ligaspiel noch neu zugeordnet werden.

## Dynamisch abgeleitete Starterstruktur

Das aktuelle `League.json -> RosterSize` enthält:

- 2 feste QB-Slots
- 2 feste RB-Slots
- 2 feste WR-Slots
- 2 feste TE-Slots
- 4 FLEX-Slots
- 1 K-Slot
- 17 BN-Slots

Damit müssen pro Woche mindestens **10 FLEX-eligible Skill-Spieler** aus den festen RB/WR/TE-Slots plus den vier FLEX-Slots gestellt werden, sofern die aktuelle FLEX-Eligibility diesen Positionen entspricht. Die konkrete FLEX-Eligibility ist bei einer Weekly Lineup Decision erneut zu verifizieren.

## Aktueller gehaltenener Positionsbestand

Aus dem aktuellen Mighty-Giants-Roster-Container mit 33 Spielern:

| Position | Gehalten insgesamt | Davon aktuell als Starter/Rotation bewertet | Zusätzliche Backups | Prospects / sonstige |
|---|---:|---:|---:|---:|
| QB | 4 | 2 | 2 | 0 |
| RB | 10 | 5 | 1 | 4 |
| WR | 14 | 7 | 2 | 5 |
| TE | 4 | 3 | 1 | 0 |
| K | 1 | 1 Spezialist | 0 | 0 |

Die Taxi-Zuordnung innerhalb der Rookie-Bestände ist in dieser Pre-Lock-Phase nicht bindend.

## Aktueller Coverage-Befund

### Quarterback

- `fixed_starter_requirement`: 2
- aktueller Coverage Floor: **3**
- aktuelle Preferred Coverage: **4**
- aktuell gehalten: **4**
- Status: **preferred coverage erfüllt**

Daniels und Mahomes bilden den Starterkern; Dart und Shough bilden die aktuelle QB-Coverage-Reserve. Vier QBs sind auf dieser Baseline sinnvoll, weil zwei feste QB-Slots jede Woche besetzt werden müssen und die vierte Option die Wahrscheinlichkeit reduziert, bei einer normalen Kombination aus Injury + Bye sofort mehrere externe QB-Adds zu benötigen.

Drei QBs wären auf dieser Baseline die untere vertretbare Grenze, aber bereits deutlich weniger komfortabel. Ein Cut des QB4 darf deshalb nicht wie der Cut eines austauschbaren WR-/RB-Prospects behandelt werden; der verlorene Coverage-Wert muss separat eingepreist werden.

### Tight End

- `fixed_starter_requirement`: 2
- aktueller Coverage Floor: **3**
- aktuelle Preferred Coverage: **4**
- aktuell gehalten: **4**
- Status: **preferred coverage erfüllt**

McBride, Loveland und Warren bilden den aktuellen startbaren TE-Pool; Fannin ist die zusätzliche Coverage-/Upside-Reserve. In einer Liga mit zwei festen TE-Startern ist TE4 nicht automatisch Luxus. Ein Rückgang auf drei TEs wäre möglich, aber nur wenn der konkrete Gegenwert die geringere Injury-/Bye-Coverage und den tatsächlichen TE-Replacement-Level rechtfertigt.

### Kicker

- `fixed_starter_requirement`: 1
- Coverage Floor: **1**
- Preferred Coverage: **1**
- aktuell gehalten: **1**
- Status: **Ziel erfüllt**

Bates belegt den notwendigen Spezialplatz. Ein zweiter Kicker ist kein Coverage-Standard und würde nur temporär einen allgemeinen Churn-Slot verbrauchen.

### Running Back und Wide Receiver

RB und WR werden nicht über ein starres dauerhaftes Positions-Cap gesteuert, weil beide die vier FLEX-Slots mittragen und deshalb gemeinsam mit TE im Skill-Pool bewertet werden müssen.

Aktuell:

- RB `core_starter` + `starter_rotation`: **5**
- WR `core_starter` + `starter_rotation`: **7**
- TE `core_starter` + `starter_rotation`: **3**
- aktueller `startable_skill_pool`: **15**
- aktuelle `required_skill_lineup_slots`: **10**
- aktuelle `skill_pool_margin`: **+5**

Zusätzlich existieren mit Skattebo, Pierce, Meyers und Fannin vier als `backup` klassifizierte Skill-Spieler. Sie werden bewusst **nicht** in die +5 Startable-Marge eingerechnet, erhöhen aber die Notfall-Coverage.

Befund: Die Mighty Giants sind im aktuellen Skill-Pool deutlich oberhalb des bloßen Weekly-Bedarfs. Deshalb muss zusätzliche RB-/WR-Tiefe am unteren Roster-Ende besonders über Upside, Marktwert, Entwicklungspfad und Churn-Opportunity-Cost gerechtfertigt werden. Mere Rosterability reicht in dieser flachen Liga nicht.

## Vier Roster-Budgets auf der aktuellen Baseline

### 1. Starter Core

Spieler, die die festen Starter- und FLEX-Anforderungen qualitativ tragen. Dieser Block wird nicht zugunsten marginaler Depth oder Prospects ausgedünnt.

### 2. Positional Coverage Reserve

Aktuell besonders relevant bei QB und TE:

- QB: Dart + Shough hinter Daniels/Mahomes
- TE: Fannin hinter McBride/Loveland/Warren

Coverage Reserve ist kein automatischer Lock, aber ihr struktureller Wert muss vor einem Cut oder Trade berücksichtigt werden.

### 3. Development Budget

Prospects plus zwei Taxi-Slots. Vor dem Taxi-Lock werden alle Rookies gemeinsam bewertet und die Taxi-Plätze erst nach Starter-/Coverage-Prüfung virtuell optimal zugewiesen.

### 4. Operational Churn Budget

Standardmäßig zwei allgemeine aktive Churn-Slots. Sie werden **erst nach** Starter-Coverage, Skill-Pool und Taxi-Zuweisung bestimmt.

Ein scheinbar schwacher Spieler ist kein gültiger Churn-Slot, wenn sein Verlust eine Position unter den aktuellen Coverage Floor drücken würde.

## Aktuelle strukturelle Schlussfolgerung

Die Mighty Giants haben aktuell **kein Coverage-Problem bei QB, TE oder K**. Auch der startbare RB/WR/TE-Skill-Pool besitzt eine komfortable Marge.

Der aktuelle Roster-Druck entsteht deshalb primär durch die Menge an zusätzlichen RB-/WR-Prospects und unteren Depth-Assets, nicht durch zu viele notwendige Coverage-Spieler auf QB/TE/K.

Für kommende Cuts und FA-Draft-Picks gilt daher:

1. Starter Core schützen.
2. QB-/TE-Coverage nicht unbeabsichtigt unter den aktuellen Floor drücken.
3. Skill-Pool-Marge nach jedem Move neu berechnen.
4. Pre-Lock-Taxi optimal unter allen Rookies verteilen.
5. Erst danach die zwei realen aktiven Churn-Slots bestimmen.
6. Einen späteren FA-Draft-Pick nur nutzen, wenn der neue Spieler den konkreten nächsten Boundary-Spieler **und** den strukturellen Rosterpreis ausreichend schlägt.

## Recheck-Trigger

Neu bewerten bei:

- Mighty-Giants-Cut, Trade oder FA-Draft-Pick;
- relevantem Injury-/Bye-/IR-Ereignis;
- Änderung der Starter-/FLEX-Struktur;
- Taxi-Lock;
- deutlicher Rollenänderung eines Coverage-Spielers;
- materiellem Wechsel im Free-Agent-Replacement-Level einer knappen Position;
- Beginn der Weekly Lineup/Waiver Phase.
