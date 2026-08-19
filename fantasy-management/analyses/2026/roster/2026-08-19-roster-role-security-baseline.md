# Mighty Giants Roster Role / Security Baseline – 2026-08-19

Status: datierte Roster-Momentaufnahme. Spielerrollen und Security-Tags sind **keine permanente Wahrheit** und müssen bei materiellen Rollen-, Injury-, Markt-, Roster- oder League-Änderungen neu abgeleitet werden.

## Quellenzustand

Diese Baseline baut auf derselben aktuellen League-/Roster-Basis wie das FA-Draft-Preboard auf:

- `public/data/League.json` @ blob `00957a261eea27db831ca400e84b1fc3e1e098f5`
- `fantasy-management/generated/operations/managed-roster-signals.json` @ blob `3196fc3a57615290dc09a22d0ceebc7480bfad6b`
- Related analysis: `fantasy-management/analyses/2026/free-agents/2026-08-19-fa-draft-preboard.md`
- Canonical method: `fantasy-management/_ai/ROSTER_ARCHITECTURE.md`

## Aktueller Kapazitätszustand

- 33 Spieler-IDs im Mighty-Giants-Roster-Container.
- Taxi: Kaelon Black und De'Zhaun Stribling.
- Reserve: aktuell leer.
- Reguläre aktive Kapazität: 30.
- Regulär aktiv belegt: 31.
- Damit aktuell: **1 aktiver Spieler über dem harten Limit**.

Die fünf bereits ausgeführten Pre-Draft-Cuts sind Joe Mixon, J.J. McCarthy, Kyle Williams, Chimere Dike und Troy Franklin.

## Zwei-Achsen-Klassifikation

### Quarterbacks

| Spieler | Roster Role | Roster Security | Einordnung |
|---|---|---|---|
| Jayden Daniels | `core_starter` | `locked` | Fundament des QB-Lineups. |
| Patrick Mahomes | `core_starter` | `locked` | Fundament des QB-Lineups. |
| Jaxson Dart | `backup` | `strong_hold` | Hochwertige QB-Absicherung mit eigenständigem Dynasty-Wert. |
| Tyler Shough | `backup` | `strong_hold` | Format-relevante QB-Absicherung; kein weiterer QB soll ohne klaren Sonderfall hinzugefügt werden. |

### Running Backs

| Spieler | Roster Role | Roster Security | Einordnung |
|---|---|---|---|
| Jeremiyah Love | `core_starter` | `locked` | Junger Kern-RB. |
| Breece Hall | `core_starter` | `locked` | Kern-RB / oberer Lineup-Pool. |
| Kenneth Walker | `starter_rotation` | `strong_hold` | Regelmäßiger Starter-/FLEX-Kandidat. |
| Chase Brown | `starter_rotation` | `strong_hold` | Regelmäßiger Starter-/FLEX-Kandidat. |
| Saquon Barkley | `starter_rotation` | `strong_hold` | Win-now-Produzent mit klarer Weekly Utility. |
| Cam Skattebo | `backup` | `strong_hold` | Hochwertige RB-Tiefe / Injury Insurance mit eigener Upside. |
| Kyle Monangai | `prospect` | `strong_hold` | Entwicklungs-/Upside-Asset oberhalb der aktuellen Cut-Line. |
| Dylan Sampson | `prospect` | `conditional` | Sinnvoller Stash, aber nahe genug an der Opportunity-Cost-Grenze für direkten Vergleich bei starken Adds. |
| Kaytron Allen | `prospect` | `churn` | Aktuell klarster allgemeiner aktiver Cut-/Churn-Kandidat und naheliegender erster Schritt zur Hard-Cap-Compliance. |
| Kaelon Black | `prospect` | `conditional` | Interessanter Taxi-Stash; Conditional statt geschützt. Taxi-Status zählt nicht als allgemeiner Churn-Slot. |

### Wide Receiver

| Spieler | Roster Role | Roster Security | Einordnung |
|---|---|---|---|
| Puka Nacua | `core_starter` | `locked` | Elite-Kernasset. |
| Malik Nabers | `core_starter` | `locked` | Elite-Kernasset. |
| George Pickens | `starter_rotation` | `strong_hold` | Oberer Starter-/FLEX-Pool. |
| Marvin Harrison Jr. | `starter_rotation` | `strong_hold` | Oberer Starter-/FLEX-Pool mit Dynasty-Upside. |
| Ladd McConkey | `starter_rotation` | `strong_hold` | Oberer Starter-/FLEX-Pool. |
| Jaylen Waddle | `starter_rotation` | `strong_hold` | Oberer Starter-/FLEX-Pool. |
| Davante Adams | `starter_rotation` | `strong_hold` | Win-now-Qualität; Alter bleibt separater Zukunftsfaktor. |
| Alec Pierce | `backup` | `hold` | Startbare Tiefe, aber unterhalb des starken Hold-Kerns. |
| Jakobi Meyers | `backup` | `hold` | Verlässliche Tiefe / Spot-Start-Utility. |
| Antonio Williams | `prospect` | `strong_hold` | Prospect mit genügend aktuellem Markt-/Upside-Puffer über der Cut-Line. |
| Malachi Fields | `prospect` | `hold` | Entwicklungs-Asset; nicht automatisch geschützt. |
| Pat Bryant | `prospect` | `hold` | Entwicklungs-Asset; positive Upside, aber weiter Opportunity-Cost-abhängig. |
| Chris Bell | `prospect` | `conditional` | Draftkapital schützt vor mechanischem Cut, aber nach Rückkehr von IR Teil der aktiven Churn-Boundary. |
| De'Zhaun Stribling | `prospect` | `strong_hold` | Hochwertiger Prospect; Taxi-Platz ist Entwicklungskapazität, nicht Churn-Kapazität. |

### Tight Ends

| Spieler | Roster Role | Roster Security | Einordnung |
|---|---|---|---|
| Trey McBride | `core_starter` | `locked` | Kern-TE. |
| Colston Loveland | `starter_rotation` | `strong_hold` | Hochwertiger Starter-/Rotation-TE. |
| Tyler Warren | `starter_rotation` | `strong_hold` | Hochwertiger Starter-/Rotation-TE. |
| Harold Fannin | `backup` | `strong_hold` | TE-Tiefe mit eigenständigem Upside-/Trade-Wert. |

### Kicker

| Spieler | Roster Role | Roster Security | Einordnung |
|---|---|---|---|
| Jake Bates | `specialist` | `churn` | Der Spieler ist austauschbar, der notwendige Kicker-Platz zählt aber **nicht** als einer der zwei allgemeinen Churn-Slots. |

## Aktuelle Churn-Boundary

Die neue Guardrail unterscheidet zwischen einem Spieler mit niedriger Security und einem tatsächlich nutzbaren allgemeinen Churn-Slot.

### Sofortiger Hard-Cap-Schritt

**Kaytron Allen** ist auf dieser Baseline der klarste aktive `churn`-Spieler und damit der naheliegende Cut, um von 31 auf 30 regulär aktive Spieler zu kommen.

### Zwei allgemeine Churn-Slots nach Compliance

Nach einem Kaytron-Cut sollen standardmäßig **zwei aktive, positionsoffene Churn-Boundary-Plätze** erhalten bleiben.

Auf der heutigen Baseline sind die ersten Kandidaten dafür:

1. **Dylan Sampson – `prospect | conditional`**
2. **Chris Bell – `prospect | conditional`**

Das bedeutet **nicht**, dass beide automatisch gecuttet werden sollen. Es bedeutet, dass ein relevanter Add, ein Notfall-Streamer oder ein später FA-Draft-Pick zuerst gegen diese Boundary geprüft wird, bevor ein stärker geschützter Hold geopfert wird.

Kaelon Black ist ebenfalls `conditional`, befindet sich aber auf Taxi und erfüllt deshalb keinen allgemeinen aktiven Churn-Slot. Jake Bates ist `specialist | churn`; sein notwendiger Kicker-Platz erfüllt die allgemeine Zwei-Slot-Reserve ebenfalls nicht.

## Auswirkungen auf den FA Draft

Tetairoa McMillan an 1.01 ist bereits separat als feste User-Entscheidung persistiert.

Für jeden weiteren FA-Draft-Zugang gilt künftig zusätzlich:

- der eingehende Spieler muss nicht nur besser als ein abstrakter Free Agent sein;
- er muss den **konkreten aktuellen Churn-/Conditional-Boundary-Spieler** deutlich genug schlagen;
- nach jedem Zugang muss erneut geprüft werden, welche zwei aktiven Plätze die allgemeine Churn-Reserve bilden;
- 4.04 und 5.04 sollen nicht erzwungen genutzt werden, wenn dadurch die Zwei-Slot-Flexibilität nur für einen marginalen Asset-Gewinn zerstört würde.

## Recheck-Trigger

Diese Baseline muss neu bewertet werden bei:

- FA-Draft-Pick oder Cut der Mighty Giants;
- relevantem Cut eines anderen Managers, der den FA-Pool verändert;
- Injury-/IR-/Reserve-Änderung;
- deutlicher Rollen-/Depth-Chart-Änderung;
- materiellem Dynasty-/ADP-/Ranking-Signal;
- Beginn der regulären Saison bzw. wenn Weekly Streaming konkret wird;
- außergewöhnlicher Bye-/Injury-Situation, die den temporären Drei-Slot-Modus rechtfertigen könnte.
