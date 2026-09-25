# Mighty Giants — Week 2 2026 Roster + Lineup Postmortem

## Status und Quellen

- Saison: 2026
- Woche: 2
- Gegner: Dennis (TeamID 5)
- Finaler Score: Mighty Giants 188,02 — Dennis 143,00
- Ergebnis: Sieg, +45,02 Punkte
- Persistiert: 2026-09-25
- Record-Typ: retrospektive Analyse, kein sealed Decision Record
- Basis: finale Week-2-Sleeper-Daten plus die während Week 2 geführte Lineup-/AutoSub-Diskussion

Primäre Evidenz:

- source-data/providers/sleeper/leagues/1354177383984267264/matchups/week-2.json
- public/data/Matchups.json
- public/data/WeeklyRecaps.json
- contemporaneous Week-2-Lineup-Diskussion zu T‑Mac vs. Skattebo, McConkey, Puka/Davante und AutoSubs
- Related process hardening: Issue #656 / Commit 032e2bf048da028192c31395e03cfe0529cce742

Die Bewertung trennt strikt zwischen damaliger Entscheidungsqualität und späterem Outcome. Aktuelle Week-3-Verletzungsstände dürfen den Week-2-Prozess nicht rückwirkend verändern.

## 1. Matchup-Ergebnis

Mighty Giants gewannen 188,02 : 143,00 gegen Dennis.

Der Sieg war bereits vor Monday Night Football rechnerisch gesichert, weil Dennis keine verbleibenden Starter mehr hatte. Die Monday-Night-Entscheidung konnte deshalb auf erwartete Points For statt Comeback-Varianz optimiert werden.

188,02 Punkte waren ein gutes Teamergebnis, obwohl mehrere gesetzte Starter durch Verletzung oder extrem schwachen Output enttäuschten.

## 2. Final gewertete Aufstellung

Die ursprünglich geplante Monday-Night-Aufstellung enthielt Puka Nacua. Puka wurde inactive; der vorbereitete AutoSub Davante Adams übernahm deshalb den gewerteten Starterplatz.

| Slot-Gruppe | Final gewerteter Spieler | Punkte |
| --- | --- | ---: |
| QB | Jayden Daniels | 14,74 |
| QB | Patrick Mahomes | 28,98 |
| RB | Saquon Barkley | 3,00 |
| RB | Kenneth Walker III | 23,80 |
| WR | Tetairoa McMillan | 15,10 |
| WR | George Pickens | 10,00 |
| TE | Trey McBride | 18,10 |
| TE | Colston Loveland | 1,30 |
| FLEX | Chase Brown | 11,20 |
| FLEX | Breece Hall | 14,20 |
| FLEX | Malik Nabers | 1,10 |
| FLEX | Davante Adams via Puka-AutoSub | 39,50 |
| K | Jake Bates | 7,00 |
| **Gesamt** |  | **188,02** |

## 3. Wichtigste Entscheidungsreviews

### Mahomes statt Dart

- Mahomes: 28,98
- Dart: 0,80

Mahomes war bereits ex ante die stabilere Week-2-Wahl. Dart verletzte sich früh und konnte kaum produzieren.

Direkter Outcome-Vorteil: **+28,18 Punkte**.

**Bewertung:** sehr starke Entscheidung; Prozess und Ergebnis stimmen überein.

### Tetairoa McMillan statt Cam Skattebo

- McMillan: 15,10
- Skattebo: 9,50

Diese Entscheidung war zunächst zu knapp und wurde erst nach einem User-Gegencheck sauber neu geöffnet. Der anschließende Boundary-Stresstest zeigte McMillans stärkeres Full-PPR-Profil und Skattebos höhere Abhängigkeit von Rushing Volume/Game Script.

Direkter Outcome-Vorteil: **+5,60 Punkte**.

**Bewertung:** finale Entscheidung richtig; ursprünglicher Analyseprozess war zu incumbent-/ranking-anchored. Genau daraus entstand das spätere Boundary-/Counterfactual-Guardrail.

### Puka Nacua starten, Davante Adams als AutoSub absichern

- Puka: 0,00 / inactive
- Davante: 39,50

Dies war die beste taktische Entscheidung der Woche. Statt Puka vorschnell aus der Aufstellung zu entfernen, blieb sein höheres Healthy-Ceiling erhalten; gleichzeitig wurde mit Davante ein korrelierter Ersatz gewählt, dessen Opportunity bei Pukas Ausfall sogar steigt.

Sleeper setzte den AutoSub korrekt um; Davante ging mit 39,50 Punkten in die Wertung ein.

**Bewertung:** exzellente Late-Injury-/AutoSub-Entscheidung.

### McConkey nicht zwanghaft in die Aufstellung/AutoSub-Struktur drücken

- McConkey: 6,50
- Nabers: 1,10

Hindsight hätte McConkey gegenüber Nabers 5,40 Punkte gewonnen. Ex ante war Nabers jedoch gesund genug für einen normalen Start, während McConkey mit einer Rippenverletzung spielte. Ein Nabers→McConkey-AutoSub hätte nur bei Inactive-Status geholfen, nicht bei aktiver geringer Usage.

**Bewertung:** Outcome Regret, aber kein klarer Prozessfehler.

### Loveland vor Tyler Warren

- Loveland: 1,30
- Warren: 14,40
- Fannin: 10,40

Dies ist der klarste vermeidbare Week-2-Miss. Nach Week 1 hatte Loveland bereits 0,00 geliefert, Warren dagegen 10,30. Der neue In-Season-Usage-/Boundary-Ansatz hätte diese TE-Grenze konsequenter neu prüfen müssen.

Direkter Hindsight-Gap Warren statt Loveland: **+13,10 Punkte**.

**Bewertung:** echter Decision Regret / Prozessfehler.

### Nabers vor Waddle

- Nabers: 1,10
- Waddle: 21,80

Der Gap von 20,70 Punkten ist groß, aber ex ante kaum als Fehler zu werten. Waddle kam aus einer Week 1 mit nur 1,20 Punkten, während Nabers trotz damaligem Return-Risiko 12,90 erzielt hatte. Nabers’ Week-2-Desaster wurde zusätzlich vom frühen Dart-Ausfall und eigenem Shoulder-Kontext beeinflusst.

**Bewertung:** Outcome Regret, kein klarer Decision Regret.

### Daniels vor Shough

- Daniels: 14,74
- Shough: 22,38

Shough hätte 7,64 Punkte mehr gebracht. Daniels war vor dem Spiel dennoch ein klar vertretbarer Starter und wurde erst während des Spiels verletzt.

**Bewertung:** Injury-/Outcome Regret.

### Barkley statt zusätzlichem Bench-Skill-Spieler

- Barkley: 3,00
- Fannin: 10,40 als Teil des Hindsight-Optimums

Barkley erlitt im Spiel einen Stinger. Einen gesunden Barkley vor dem Spiel für Fannin zu benchen wäre nicht sachgerecht gewesen.

**Bewertung:** Injury-/Outcome Regret.

### Pickens vor Wicks

- Pickens: 10,00
- Wicks: 12,40

Nur 2,40 Punkte Differenz. Wicks bestätigte ein interessantes Week-1-Signal, aber Pickens war weiterhin die vernünftigere ex-ante Startoption.

**Bewertung:** kleiner Outcome Regret; kein Prozessfehler.

## 4. Hindsight Best Ball

Das legale nachträgliche Maximum aus den damals aktiven und startberechtigten Mighty-Giants-Spielern lag bei **239,26 Punkten**. Taxi und Reserve wurden ausgeschlossen.

| Slot-Gruppe | Hindsight-Spieler | Punkte |
| --- | --- | ---: |
| QB | Patrick Mahomes | 28,98 |
| QB | Tyler Shough | 22,38 |
| RB | Kenneth Walker III | 23,80 |
| RB | Breece Hall | 14,20 |
| WR | Davante Adams | 39,50 |
| WR | Jaylen Waddle | 21,80 |
| TE | Trey McBride | 18,10 |
| TE | Harold Fannin Jr. | 10,40 |
| FLEX | Tetairoa McMillan | 15,10 |
| FLEX | Tyler Warren | 14,40 |
| FLEX | Dontayvion Wicks | 12,40 |
| FLEX | Chase Brown | 11,20 |
| K | Jake Bates | 7,00 |
| **Maximum** |  | **239,26** |

Realisierte Hindsight-Effizienz: 188,02 / 239,26 = **78,6 %**.

Die Differenz von 51,24 Punkten ist ausdrücklich kein Maß für vermeidbare Managementfehler. Der größte Teil stammt aus Injury-/Variance-Regret bei Nabers, Daniels und Barkley sowie überraschender Bench-Outperformance.

## 5. Decision Regret vs. Outcome Regret

| Entscheidung | Gap | Kategorie | Begründung |
| --- | ---: | --- | --- |
| Loveland statt Warren | 13,10 | **Decision Regret** | Week-1-Evidenz hätte einen strengeren TE-Boundary-Recheck verlangt. |
| Nabers statt Waddle | 20,70 | Outcome Regret | Waddle kam aus 1,20 W1-Punkten; Nabers war ex ante klar vertretbar. |
| Daniels statt Shough | 7,64 | Outcome Regret | Daniels wurde während des Spiels verletzt. |
| Barkley statt Fannin/anderer Flex | 7,40+ | Outcome Regret | Stinger während des Spiels; Barkley ex ante klar startwürdig. |
| Pickens statt Wicks | 2,40 | kleiner Outcome Regret | Pickens blieb die plausiblere Pre-Game-Wahl. |
| Nabers statt McConkey | 5,40 | Outcome Regret | McConkey spielte verletzt; Nabers war kein sinnvoller AutoSub-Zielstarter. |
| T‑Mac statt Skattebo | **+5,60 realisiert** | positive Decision Quality | Boundary-Recheck führte zur besseren Wahl. |
| Mahomes statt Dart | **+28,18 realisiert** | positive Decision Quality | klare, robuste QB-Entscheidung. |
| Puka→Davante AutoSub | **+39,50 gegenüber leerem Puka-Slot** | positive Decision Quality | perfekte Absicherung eines echten Inactive-Risikos. |

## 6. Spieler-für-Spieler-Review

### Quarterbacks

| Spieler | W2 Punkte | Status | Week-2-Einordnung |
| --- | ---: | --- | --- |
| Patrick Mahomes | 28,98 | Starter | Elite-Woche; QB-Core bestätigt. |
| Tyler Shough | 22,38 | Bench | Zweites starkes frühes Signal; wird durch QB-Injuries strukturell wichtiger. |
| Jayden Daniels | 14,74 | Starter | Produktion bis zur Verletzung okay; Outcome wird vom Ellbogen-Injury-Event dominiert. |
| Jaxson Dart | 0,80 | Bench | Früh verletzt; Score nicht als Leistungsbewertung verwenden. |

### Running Backs

| Spieler | W2 Punkte | Status | Week-2-Einordnung |
| --- | ---: | --- | --- |
| Kenneth Walker III | 23,80 | Starter | Sehr starke Fortsetzung; klarer Weekly-Starter. |
| Breece Hall | 14,20 | Starter | Solider PPR-Floor trotz ineffizienterem Rushing. |
| Chase Brown | 11,20 | Starter | Volumen bleibt wichtiger als der mittelmäßige Score; Rolle stabil. |
| Cam Skattebo | 9,50 | Bench | Nutzbare Receiving-/Depth-Rolle, aber T‑Mac war die bessere Week-2-Entscheidung. |
| Kyle Monangai | 7,80 | Bench | Wieder reale Opportunities; Depth-Wert steigt. |
| Jeremiyah Love | 7,50 | Bench | Entwicklung offen; kein Alarm, aber noch kein Weekly-Autostart. |
| Saquon Barkley | 3,00 | Starter | Stinger zerstört den Boxscore; kein negativer Rollenbefund. |
| Jonathon Brooks | 2,10 | Bench | Kleine Rolle plus neue Verletzung; kurzfristiger Wert sinkt. |
| Dylan Sampson | 0,00 | Reserve | Auf IR; kein Week-2-Performance-Signal. |

### Wide Receiver

| Spieler | W2 Punkte | Status | Week-2-Einordnung |
| --- | ---: | --- | --- |
| Davante Adams | 39,50 | AutoSub/Starter | Spieler des Mighty-Giants-Spieltags; enorme Opportunity ohne Puka. |
| Jaylen Waddle | 21,80 | Bench | Starker Rebound nach schwacher Week 1; zurück in die FLEX-Boundary. |
| Tetairoa McMillan | 15,10 | Starter | Gute Yardage-/Volume-Produktion; stabilisiert sich als Weekly-Option. |
| Dontayvion Wicks | 12,40 | Bench | Zweites positives Spiel; nicht mehr als irrelevanter Churn-Filler behandeln. |
| George Pickens | 10,00 | Starter | Solide Receptions, noch ohne großen Ceiling-Tag. |
| Ladd McConkey | 6,50 | Bench | Verletzungskontext; Entscheidung, ihn nicht zu forcieren, war sinnvoll. |
| Antonio Williams | 5,40 | Taxi | Reale NFL-Targets/Produktion; positives Taxi-Entwicklungssignal. |
| Malachi Fields | 5,00 | Bench | Solider Depth-Output, noch keine Starter-These. |
| Caleb Douglas | 3,90 | Bench | Rückgang plus Ankle-Kontext; Recheck statt Rollenpanik. |
| Jakobi Meyers | 3,80 | Bench | Schwache Woche; Veteran-Depth muss sich gegen jüngere Boundary-Assets behaupten. |
| Alec Pierce | 2,10 | Bench | Heel Injury dominiert; Score nicht als Rollenurteil nutzen. |
| Malik Nabers | 1,10 | Starter | Katastrophaler Score, aber durch QB-/Shoulder-Kontext stark verzerrt. |
| Marvin Harrison Jr. | 0,00 | Bench | Echter Usage-/Offense-Recheck nötig; Name allein darf keinen Starterbonus erzeugen. |
| Puka Nacua | 0,00 | ursprünglich ausgewählter Starter, inactive | Kein Performance-Fail; korrekt über Davante abgesichert. |
| Chris Bell | 0,00 | Taxi | Noch kein kurzfristiges Weekly-Utility-Signal. |
| Ricky Pearsall | 0,00 | Reserve | IR/keine Week-2-Lineup-Relevanz. |
| De'Zhaun Stribling | 0,00 | Reserve | IR/keine Week-2-Lineup-Relevanz. |

### Tight Ends

| Spieler | W2 Punkte | Status | Week-2-Einordnung |
| --- | ---: | --- | --- |
| Trey McBride | 18,10 | Starter | Core-TE bleibt unangetastet. |
| Tyler Warren | 14,40 | Bench | Zweites starkes Scoring-Signal; muss ab Week 3 mindestens vor Loveland in den Boundary-Test. |
| Harold Fannin Jr. | 10,40 | Bench | Usage-/Produktion wächst; echte Startbarkeit beginnt sich zu materialisieren. |
| Colston Loveland | 1,30 | Starter | Nach 0,00 in Week 1 zweites schwaches Spiel; kein automatischer Starterstatus mehr. |

### Kicker

| Spieler | W2 Punkte | Status | Week-2-Einordnung |
| --- | ---: | --- | --- |
| Jake Bates | 7,00 | Starter | Ordentlich; weiterhin Weekly-Hold/Stream-Position statt strukturell geschützter Asset-Slot. |

## 7. Rosterweite Week-2-Signale

### Größte positive Signale

- Davante Adams: kurzfristig enormer Win-Now-Wert bei Puka-Ausfall.
- Kenneth Walker III: klarer Weekly-RB-Starter.
- Jaylen Waddle: Week-1-Panik deutlich relativiert.
- Tetairoa McMillan: stabile Starter-/FLEX-Tendenz.
- Tyler Warren: TE-Boundary verschiebt sich.
- Harold Fannin Jr.: TE4 entwickelt reale Weekly-Utility.
- Dontayvion Wicks: zweites positives Regular-Season-Signal.
- Tyler Shough: QB-Tiefe gewinnt wegen eigener Leistung und externer Injury-Lage stark an Bedeutung.

### Größte Risiken / Rechecks

- Jayden Daniels: Availability dominiert die QB-Planung.
- Jaxson Dart: schwerer Injury-Fall, kurzfristig keine Coverage.
- Saquon Barkley: Health-Recheck nach Stinger.
- Malik Nabers / Puka: kurzfristige Injury- und Practice-Evidenz weiter prüfen.
- Colston Loveland: Weekly-Usage reicht nicht für automatischen Start.
- Marvin Harrison Jr.: Routes/Targets/Teamkontext ausdrücklich neu prüfen.
- Jonathon Brooks / Alec Pierce / Caleb Douglas: Injury-Rechecks.

## 8. Prozesslehren

1. Starter-Boundary immer als gemeinsamen Kandidatenpool prüfen; aktuelles Sleeper-Lineup erhält keinen Incumbency-Bonus.
2. Bei echten Grenzfällen mindestens eine plausible Gegenhypothese prüfen.
3. FLEX-Slots gemeinsam mit festen Positionen optimieren, nicht isoliert nach Positionsgruppen.
4. AutoSubs gemeinsam mit der Startaufstellung optimieren; Puka→Davante ist das Referenzbeispiel für hohe Versicherungsqualität.
5. AutoSub schützt Inactive-Risiko, nicht active-but-limited oder In-Game-Verletzung.
6. Best-Ball-Gap und Managementfehler sind nicht dasselbe. Week 2 zeigt besonders deutlich die Trennung von Decision Regret und Outcome Regret.
7. Nach Week 1 verfügbare Usage-Evidenz muss in Week 2 konsistent auf den vollständigen Boundary-Pool angewandt werden; Loveland/Warren war die klare Lücke.

## 9. Abschlussurteil

Week 2 war eine gute Management-Woche mit einem klar identifizierbaren TE-Prozessfehler.

Die wichtigsten aktiven Entscheidungen waren stark:
- Mahomes vor Dart;
- T‑Mac vor Skattebo nach erneutem Boundary-Test;
- Puka nicht vorschnell benchen und mit Davante absichern.

Der rohe Abstand von 51,24 Punkten zum Hindsight-Maximum überzeichnet die vermeidbaren Fehler deutlich. Nabers/Waddle, Daniels/Shough und Barkley/Fannin waren überwiegend Injury-/Variance-Regret. Der echte Decision-Regret-Schwerpunkt liegt bei Loveland vor Warren.

Das Team zeigte gleichzeitig außergewöhnliche Tiefe: 188,02 Punkte trotz sehr schwacher Scores von Barkley, Loveland und Nabers sowie Daniels-Injury, während Shough, Waddle, Warren, Wicks und Fannin auf der Bench produktiv waren.
