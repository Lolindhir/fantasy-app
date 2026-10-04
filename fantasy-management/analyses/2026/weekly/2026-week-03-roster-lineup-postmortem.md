# Mighty Giants — Week 3 2026 Roster + Lineup Postmortem

## Status und Quellen

- Saison: 2026
- Woche: 3
- Gegner: Marcel (TeamID 2)
- Finaler Score: Mighty Giants 173,64 — Marcel 178,96
- Ergebnis: Niederlage, -5,32 Punkte
- Persistiert: 2026-10-01
- Record-Typ: retrospektive Analyse, kein sealed Decision Record
- Basis: finale Week-3-Ligadaten plus die während Week 3 geführte Start/Sit- und Matchup-State-Diskussion

Primäre periodenstabile Evidenz:

- `source-data/leagues/nfl-reise/seasons/2026/matchups/week-3.json`
- `public/data/Matchups.json`
- `public/data/League.json` @ Commit `1292f8d421b96873e404ea914be737ef6d02f463` als erster Week-4-Stand nach Abschluss von Week 3 für Starter-/Reserve-/Taxi-Rekonstruktion
- contemporaneous Week-3-Lineup-Diskussion, insbesondere der späte Wechsel **Cam Skattebo → Tetairoa McMillan** zur bewussten Ceiling-Erhöhung gegen Marcel

Zusätzliche zeitgenössische externe Kontextquellen der interaktiven Week-3-Auswertung:

- FantasyPros Week-3 Outlooks für Tetairoa McMillan, Cam Skattebo, Harold Fannin Jr., Jeremiyah Love, Jakobi Meyers, Jaylen Waddle, Malik Nabers und Ladd McConkey
- NFL/NFL Pro Team-/Game-Insights für Rollen- und Usage-Kontext
- Carolina Panthers Postgame-Kontext zur veränderten Browns-Coverage gegen Tetairoa McMillan

Die Bewertung trennt strikt zwischen damaliger Entscheidungsqualität und späterem Outcome. Week-4-Informationen dürfen den Week-3-Prozess nicht rückwirkend verändern.

## 1. Matchup-Ergebnis

Mighty Giants verloren **173,64 : 178,96** gegen Marcel.

Die Niederlage fiel mit **5,32 Punkten** sehr knapp aus. Gleichzeitig war 173,64 kein außergewöhnlich hoher Teamertrag: Week 3 enthielt mehrere gleichzeitig schwache oder mittelmäßige Outputs etablierter Starter.

Die drei bisherigen Mighty-Giants-Wochenscores lauten:

- Week 1: 205,36
- Week 2: 188,02
- Week 3: 173,64

Der fallende Dreispielverlauf ist noch kein belastbarer Teamtrend. Für Week 4 muss zwischen normaler Scoring-Varianz und echten Rollen-/Usage-Veränderungen unterschieden werden.

## 2. Final gewertete Aufstellung

| Slot-Gruppe | Final gewerteter Spieler | Punkte |
| --- | --- | ---: |
| QB | Tyler Shough | 24,80 |
| QB | Patrick Mahomes | 16,94 |
| RB | Chase Brown | 8,90 |
| RB | Kenneth Walker III | 21,30 |
| WR | Davante Adams | 20,70 |
| WR | George Pickens | 15,20 |
| TE | Trey McBride | 16,50 |
| TE | Tyler Warren | 14,70 |
| FLEX | Saquon Barkley | 9,00 |
| FLEX | Breece Hall | 8,50 |
| FLEX | Tetairoa McMillan | 3,70 |
| FLEX | Jaylen Waddle | 6,40 |
| K | Jake Bates | 7,00 |
| **Gesamt** |  | **173,64** |

Die Aufstellung enthielt viele ex ante klar vertretbare Starts. Der entscheidende Retrospektivfall ist deshalb nicht ein generelles Lineup-Versagen, sondern die konkrete Boundary-Entscheidung **McMillan statt Skattebo**.

## 3. Wichtigste Entscheidungsreviews

### Tetairoa McMillan statt Cam Skattebo

- McMillan: 3,70
- Skattebo: 13,00
- direkter Outcome-Gap: **9,30 Punkte**

Unser ursprüngliches Week-3-Board hatte Skattebo vor McMillan. Am Spieltag wurde diese Reihenfolge bewusst überschrieben, weil Marcel aus **242,80 und 202,50 Punkten** in den ersten beiden Wochen kam und deshalb eine erneut sehr hohe gegnerische Scoring-Erwartung plausibel war. Die Entscheidung war damit bewusst gegnerspezifisch: Gegen ein bis dahin regelmäßig über 200 Punkte scorendes Team wurde McMillans höheres Receiving-/Big-Play-Ceiling gegenüber Skattebos stabilerem Volumenprofil stärker gewichtet.

Christian Watsons bereits erzielte 22,60 Donnerstagspunkte waren dabei **kein eigenständiger Auslöser und kein als außergewöhnlicher Outlier behandeltes Signal**. Sie lagen noch im Rahmen dessen, was gegen Marcel ohnehin einkalkuliert wurde, und veränderten die Grundthese nicht wesentlich.

Die McMillan-These war ex ante nicht unbegründet. Er kam mit hohem Target-/First-Read-Anteil, Deep Targets und Red-Zone-Usage in die Woche. Cleveland veränderte im Spiel seine bisherige Coverage jedoch sichtbar gegen McMillan und begrenzte ihn auf 2 Receptions für 17 Yards.

Skattebos Gegenargument war der stabilere Volumenpfad. Schon vor Week 3 hatte er einen klaren Snap-/Carry-/Route-Anteil gezeigt. In Week 3 bekam er 20 Carries plus vier Targets und produzierte trotz fehlendem Touchdown 13,00 Fantasy-Punkte.

Mit Skattebo statt McMillan hätte Mighty Giants **182,94 : 178,96 gewonnen**.

**Bewertung:** leichter **Decision Regret / vertretbarer aggressiver Call**. Der McMillan-Start war ex ante nachvollziehbar, weil Marcels bisheriges Scoring-Profil eine höhere als normale Team-Scoring-Anforderung plausibel machte und McMillan das höhere Ceiling-Profil bot. Im Rückblick war Skattebos stabilerer Median die bessere Wahl, aber der Call war kein klarer Prozessfehler und insbesondere keine Überreaktion auf Watsons Donnerstagsspiel.

**Same-Information-Re-Decision:** leichter Lean zu Skattebo wegen des stabileren Median-/Volumenprofils, aber McMillan bleibt eine vertretbare Alternative, wenn die vorab erwartete Gegnerstärke bewusst ein höheres Risikobudget rechtfertigt. Die Gegner-Erwartung ist dabei von einem tatsächlich entstandenen Live-Matchup-Rückstand zu trennen.

### Harold Fannin Jr. auf der Bank

- Fannin: 24,10

Fannin kam aus 4,10 und 10,40 Punkten in den ersten beiden Wochen. Vor Week 3 war seine Rolle interessant, aber noch nicht so belastbar, dass er McBride/Warren oder einen etablierten FLEX-Spieler automatisch verdrängen musste.

Week 3 brachte dann neun Targets, sieben Receptions, 51 Yards und zwei Touchdowns. Entscheidend für die Zukunft sind nicht primär die zwei Touchdowns, sondern das neue Target-/Opportunity-Niveau.

**Bewertung:** **Outcome Regret, kein Decision Regret**. Der Sit war mit der damaligen Evidenz vertretbar. Week 3 erzeugt jedoch einen klaren Week-4-Recheck und hebt Fannin in den echten Starter-/FLEX-Boundary-Pool.

### Jeremiyah Love auf der Bank

- Love: 21,90

Vor Week 3 hatte Love 13,00 und 7,50 Punkte erzielt und in der Rollenverteilung noch keinen stabilen klaren Starterstatus gezeigt.

In Week 3 änderte sich die Struktur: Love startete, übernahm den klaren Hauptanteil der Carries und kam insgesamt auf 26 Touches. Das ist wesentlich stärker als ein reiner Boxscore-Spike.

**Bewertung:** **Outcome Regret, kein Decision Regret**. Der zentrale Befund ist ein materieller Rollenwechsel. Dieselbe alte Evaluation darf in Week 4 nicht fortgeschrieben werden.

### Jakobi Meyers auf der Bank

- Meyers: 19,40

Meyers hatte in den ersten beiden Wochen nur 12,20 und 3,80 Punkte und sehr wenig Target-Volumen. Deshalb war er vor Week 3 kein vorrangiger FLEX-Start.

In Week 3 kamen acht Targets, sieben Receptions und 19,40 Punkte. Das ist ein neues positives Usage-Signal.

**Bewertung:** **Outcome Regret**. Ein Spiel reicht noch nicht für automatischen Starterstatus, aber Meyers gehört wieder in den Week-4-Boundary-Pool.

### Jaylen Waddle starten

- Waddle: 6,40

Waddle kam aus einer starken Week 2 mit 21,80 Punkten und deutlich verbessertem Target-/First-Read-Profil. Ein Week-3-Start war damit nachvollziehbar.

In Week 3 produzierte er trotz sieben Targets nur 2 Receptions für 10 Yards, ergänzt durch Rushing Yards und eine Two-Point Conversion. Die Opportunity verschwand nicht vollständig; vor allem die Conversion war schwach.

**Bewertung:** **Outcome Regret, kein Decision Regret**.

### Malik Nabers auf der Bank

- Nabers: 7,60

Nabers war vor Week 3 körperlich ausreichend freigegeben. Der wesentliche negative Kontext war jedoch die Quarterback-/Passing-Umgebung.

Er erhielt sechs Targets und fing fünf davon, kam aber nur auf 26 Receiving Yards.

**Bewertung:** Der Bench-Call war vertretbar und die Sorge um die Target-Qualität wurde eher bestätigt als widerlegt. Kein Decision Regret.

### Ladd McConkey auf der Bank

- McConkey: 10,60

McConkey kam mit Rib-/Workload-Uncertainty und deutlich reduziertem Week-2-Snap-/Target-Profil in die Woche.

Seine 10,60 Punkte hätten gegenüber McMillan ausgereicht, um das Matchup zu drehen. Diese Erkenntnis entsteht aber erst aus dem Outcome.

**Bewertung:** **Outcome Regret, kein klarer Prozessfehler**.

## 4. Legales Hindsight Best Ball

Für den Hindsight-Vergleich werden nur Spieler verwendet, die in der rekonstruierten Week-3-Population startberechtigt waren. Der Week-4-Stand von `League.json` direkt nach Abschluss der Woche bestätigt für die Rekonstruktion:

- Reserve: Jonathon Brooks, Ricky Pearsall, Dylan Sampson, Jaxson Dart, De'Zhaun Stribling
- Taxi: Antonio Williams, Chris Bell

Diese Spieler werden aus dem legalen Best Ball ausgeschlossen.

| Slot-Gruppe | Hindsight-Spieler | Punkte |
| --- | --- | ---: |
| QB | Tyler Shough | 24,80 |
| QB | Patrick Mahomes | 16,94 |
| RB | Jeremiyah Love | 21,90 |
| RB | Kenneth Walker III | 21,30 |
| WR | Davante Adams | 20,70 |
| WR | Jakobi Meyers | 19,40 |
| TE | Harold Fannin Jr. | 24,10 |
| TE | Trey McBride | 16,50 |
| FLEX | George Pickens | 15,20 |
| FLEX | Tyler Warren | 14,70 |
| FLEX | Cam Skattebo | 13,00 |
| FLEX | Ladd McConkey | 10,60 |
| K | Jake Bates | 7,00 |
| **Maximum** |  | **226,14** |

Realisierte Hindsight-Effizienz: **173,64 / 226,14 = 76,8 %**.

Der Abstand von **52,50 Punkten** zum Hindsight-Maximum ist ausdrücklich kein Maß für vermeidbare Managementfehler. Ein großer Teil stammt aus Rollen-/Usage-Sprüngen, die erst Week 3 selbst belastbar sichtbar machte.

## 5. Decision Regret vs. Outcome Regret

| Entscheidung | Gap | Kategorie | Begründung |
| --- | ---: | --- | --- |
| McMillan statt Skattebo | 9,30 | **leichter Decision Regret / vertretbarer aggressiver Call** | Marcels 242,80/202,50-Punkte-Start rechtfertigte ein höheres Risikobudget; Skattebos stabilerer Median wäre im Same-Information-Re-Decision dennoch leicht vorzuziehen. |
| McMillan statt Love | 18,20 | Outcome Regret | Loves klarer Rollenanstieg materialisierte sich erst im Spiel. |
| McMillan statt Fannin | 20,40 | Outcome Regret | Fannins neues Target-/Scoring-Level war vor Week 3 noch nicht ausreichend belastbar. |
| McMillan statt Meyers | 15,70 | Outcome Regret | Meyers kam aus sehr niedrigem Target-Volumen; Week 3 war ein neues Usage-Signal. |
| McMillan statt McConkey | 6,90 | Outcome Regret | McConkey trug relevanten Rib-/Workload-Kontext. |
| Waddle trotz 6,40 | — | Outcome Regret | Week-2-Usage machte den Start vertretbar; Week 3 scheiterte primär an Conversion. |
| Nabers benchen | kein Verlust gegenüber den gewählten Kernstarts ableitbar | neutrale/positive Decision Quality | Die problematische QB-/Target-Qualität blieb real. |

Der zentrale Prozessbefund ist damit nuancierter: **Week 3 hatte keinen klaren groben Start/Sit-Prozessfehler.** McMillan statt Skattebo war ein vertretbarer aggressiver Call mit leichtem Decision Regret, während die übrigen großen Bench-Gaps überwiegend Outcome Regret beziehungsweise neue Week-3-Evidenz waren.

## 6. Spieler-für-Spieler-Review

### Quarterbacks

| Spieler | W3 Punkte | Status | Week-3-Einordnung |
| --- | ---: | --- | --- |
| Tyler Shough | 24,80 | Starter | Drittes starkes Spiel in Folge; in der 2-QB-Liga aktuell klarer Weekly-Starter. |
| Patrick Mahomes | 16,94 | Starter | Solider Floor; Startentscheidung klar richtig. |
| Jayden Daniels | 0,00 | Bench | Availability dominiert; kein Leistungsurteil aus dem Nuller. |
| Jaxson Dart | 0,00 | Reserve | Nicht lineup-relevant. |

### Running Backs

| Spieler | W3 Punkte | Status | Week-3-Einordnung |
| --- | ---: | --- | --- |
| Jeremiyah Love | 21,90 | Bench | Größtes neues Rollen-/Usage-Signal der Woche; klarer Week-4-Boundary-Riser. |
| Kenneth Walker III | 21,30 | Starter | Drittes starkes Spiel; klarer Weekly-Starter. |
| Cam Skattebo | 13,00 | Bench | Volumen/Floor bestätigt; muss Week 4 ernsthaft gegen etablierte FLEX-Namen antreten. |
| Saquon Barkley | 9,00 | Starter | Ex ante klar vertretbar; drei schwache Fantasy-Wochen erzwingen trotzdem neuen Boundary-Test ohne Namensbonus. |
| Chase Brown | 8,90 | Starter | Scoring sinkt, Rolle blieb aber stabil genug für Recheck statt Panik. |
| Breece Hall | 8,50 | Starter | Schwacher Output plus anschließender Availability-/Quad-Recheck für Week 4. |
| Kyle Monangai | 3,10 | Bench | Kein neues Startsignal. |
| Jonathon Brooks | 0,00 | Reserve | Keine Week-3-Lineup-Relevanz. |
| Dylan Sampson | 0,00 | Reserve | Keine Week-3-Lineup-Relevanz. |

### Wide Receiver

| Spieler | W3 Punkte | Status | Week-3-Einordnung |
| --- | ---: | --- | --- |
| Davante Adams | 20,70 | Starter | Zweites sehr starkes Spiel; Puka-Kontext bei Fortschreibung beachten. |
| Jakobi Meyers | 19,40 | Bench | Deutlicher positiver Usage-Rebound; zurück in den Boundary-Pool. |
| George Pickens | 15,20 | Starter | Drittes Spiel mit aufsteigendem Scoring-Verlauf; Start bestätigt. |
| Ladd McConkey | 10,60 | Bench | Stabilisierung trotz vorherigem Injury-/Workload-Kontext. |
| Malik Nabers | 7,60 | Bench | Targets vorhanden, aber geringe Target-Qualität/Passing-Effizienz bleiben Problem. |
| Marvin Harrison Jr. | 7,00 | Bench | Kleiner Rebound, noch kein klarer Starterstatus. |
| Jaylen Waddle | 6,40 | Starter | Schlechte Conversion bei weiter vorhandener Opportunity; nicht aufgrund eines Spiels überreagieren. |
| Dontayvion Wicks | 5,20 | Bench | Rückschritt nach zwei positiven Wochen; weiter Depth statt Weekly-Autostart. |
| Malachi Fields | 3,90 | Bench | Kein materieller Startimpuls. |
| Tetairoa McMillan | 3,70 | Starter | Schlechter Outcome durch defensive Anpassung; Spielerthese nicht verwerfen, aber Week-4-Boundary offen. |
| Antonio Williams | 3,50 | Taxi | Nicht lineup-eligible. |
| Chris Bell | 10,70 | Taxi | Guter Score, aber taxi-lockbedingt kein legaler Week-3-Starter. |
| Puka Nacua | 0,00 | aktive Population / ohne gewertete Produktion | Availability-Kontext; kein Performance-Urteil. |
| Ricky Pearsall | 0,00 | Reserve | Keine Week-3-Lineup-Relevanz. |
| De'Zhaun Stribling | 0,00 | Reserve | Keine Week-3-Lineup-Relevanz. |

### Tight Ends

| Spieler | W3 Punkte | Status | Week-3-Einordnung |
| --- | ---: | --- | --- |
| Harold Fannin Jr. | 24,10 | Bench | Breakout mit neuem Target-/Opportunity-Niveau; klarer Riser. |
| Trey McBride | 16,50 | Starter | Core-TE bleibt unangetastet. |
| Tyler Warren | 14,70 | Starter | Drittes stabiles Spiel; Starterentscheidung bestätigt. |
| Colston Loveland | 7,10 | Bench | Verbesserung, aber Fannin/Warren liegen aktuell klar vor ihm. |

### Kicker

| Spieler | W3 Punkte | Status | Week-3-Einordnung |
| --- | ---: | --- | --- |
| Jake Bates | 7,00 | Starter | Dritte 7-Punkte-Woche; neutraler Hold/Stream-Kontext, kein struktureller Alarm. |

## 7. Rosterweite Week-3-Signale

### Größte positive Signale

- **Jeremiyah Love:** klarer Rollen-/Usage-Sprung; stärkster neuevaluierter Spieler des Rosters.
- **Harold Fannin Jr.:** Target- und Scoring-Breakout; in dieser 2-TE-Liga besonders relevant.
- **Cam Skattebo:** stabiler Volumen-Floor bestätigt.
- **Jakobi Meyers:** Target-Volumen springt zurück und macht ihn wieder startrelevant.
- **Tyler Shough:** 25,20 → 22,38 → 24,80; aus Coverage ist echte Weekly-Startstärke geworden.
- **Kenneth Walker III:** 34,10 → 23,80 → 21,30; klarer stabiler Core-Starter.
- **Tyler Warren:** 10,30 → 14,40 → 14,70; zuverlässiger zweiter TE.
- **George Pickens:** 5,80 → 10,00 → 15,20; positive Entwicklung.

### Größte Risiken / Rechecks

- **Breece Hall:** Performance plus Quad-/Availability-Kontext.
- **Saquon Barkley:** 9,00 → 3,00 → 9,00; kein automatischer FLEX-Bestandsschutz allein durch Namen.
- **Chase Brown:** 18,80 → 11,20 → 8,90; Rolle vs. fehlende Scoring-Ausbeute neu prüfen.
- **Tetairoa McMillan:** 3,70 ist keine Thesis-Zerstörung, aber Boundary muss ohne Incumbency-Bonus neu aufgemacht werden.
- **Malik Nabers:** Target-Anteil bleibt interessant, Target-Qualität/QB-Environment begrenzt den Floor.
- **Jaylen Waddle:** Opportunity und Conversion getrennt bewerten.
- **Davante Adams:** starke Week-2/3-Produktion nicht ohne Puka-/Teamkontext als neue dauerhafte Baseline fortschreiben.

## 8. Prozesslehren

1. **Erwartete Gegnerstärke und Live-Matchup-State sind getrennte Risikosignale.** Ein Gegner, der wie Marcel mit 242,80 und 202,50 Punkten in die Woche kommt, kann bereits vor Kickoff ein etwas höheres Risikobudget rechtfertigen. Das ist etwas anderes als eine nachträgliche Reaktion auf einen einzelnen Donnerstagsscore oder einen optischen Live-Rückstand.
2. **Ein bewusster Ceiling-Override sollte explizit dokumentiert werden.** Mindestens: ursprüngliche Boundary-Reihenfolge, geänderte Reihenfolge, ob der Grund aus der vorab erwarteten Gegnerstärke oder aus dem tatsächlichen Live-Matchup-State stammt, und der erwartete Ceiling-/Median-Trade-off. Ein einzelner früher gegnerischer Score erzeugt dabei keine eigene Sonderregel.
3. **Bench-Breakouts sind nicht automatisch Managementfehler.** Love, Fannin und Meyers erzeugen neue Evidenz für Week 4; sie machen ihren Week-3-Sit nicht rückwirkend falsch.
4. **Namen erhalten keinen Bestandsschutz.** Barkley, Breece und Chase müssen gegen Love, Skattebo, Fannin, Meyers und andere aktuelle Boundary-Spieler nach denselben Kriterien neu geprüft werden.
5. **Usage/Opportunity und Boxscore getrennt führen.** Besonders Love/Fannin sind nachhaltig interessanter, weil nicht nur die Punkte, sondern die Opportunity stieg.
6. **Same-Information-Re-Decision bleibt der zentrale Regret-Test.** Für Week 3 würde die Aufstellung im Kern gleich bleiben; bei Skattebo vs. McMillan läge der leichte Re-Decision-Lean bei Skattebo, ohne den damaligen McMillan-Call als klaren Fehler zu klassifizieren.

## 9. Abschlussurteil

Week 3 war **keine generell schlecht gemanagte Lineup-Woche**. Der engste Retrospektivpunkt ist **Tetairoa McMillan statt Cam Skattebo**, aber auch dieser Call war ex ante vertretbar: Marcel kam aus 242,80 und 202,50 Punkten, sodass ein bewusst höheres Risikobudget plausibel war. Watsons Donnerstagsspiel war dabei kein eigenständiger Auslöser.

Im Same-Information-Re-Decision würde Skattebos stabilerer Median leicht vor McMillans Ceiling liegen. Deshalb bleibt ein **leichter Decision Regret**, aber kein klarer Matchup-State- oder Start/Sit-Prozessfehler. Der 9,30-Punkte-Gap war größer als die 5,32-Punkte-Niederlage und erklärt damit den Outcome, nicht automatisch einen groben Entscheidungsfehler.

Die großen Bench-Scores von Harold Fannin Jr., Jeremiyah Love und Jakobi Meyers sind dagegen überwiegend **neue Week-3-Evidenz** statt rückwirkender Start/Sit-Fehler. Genau daraus entsteht die wichtigste Folge für Week 4: Der bisherige Starterkern darf an der FLEX-Grenze keinen Incumbency-Bonus erhalten. Love, Fannin, Skattebo und Meyers müssen zusammen mit Waddle, McMillan, Nabers, Barkley, Breece und Chase in einen neuen gemeinsamen Boundary-Stresstest.

Die wichtigste Prozessverbesserung aus Week 3 ist deshalb **keine spezielle Donnerstag-Regel**. Sinnvoll ist stattdessen eine saubere Dokumentation des Risikobudgets: Vorab erwartete Gegnerstärke darf einen aggressiveren Call rechtfertigen; ein später Live-Matchup-State muss separat anhand bereits absolvierter Starter, verbleibender Slots und Erwartungswert eingeordnet werden.
