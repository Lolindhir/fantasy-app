# Mighty Giants roster role/security recheck — 2026-09-19

## Status

Dieser Recheck ersetzt für den aktuellen In-Season-Kontext den Bewertungsstand vom 2026-08-19 und aktualisiert die datierte Einschätzung vom 2026-09-11.

Aktueller Strukturstand aus dem produktiven Managed-Roster-Readmodel:
- Active: 30/30
- Taxi: 2/2, locked
- Reserve: 3/5
- Held players: 35
- General-Churn-Ziel: 2
- Tatsächliche allgemeine aktive Churn-Slots nach diesem Recheck: **0**
- Vergleichs-Boundary für einen materiellen neuen Zugang: **Malachi Fields → Dontayvion Wicks**
- Dylan Sampson bleibt `prospect | conditional`, liegt aktuell aber auf Reserve/IR und ist deshalb kein aktiver Boundary-Slot.

## Verwendete Evidenz

Priorität gemäß `ROSTER_ARCHITECTURE.md`:
1. aktueller League-/Roster-/Reserve-/Taxi-State;
2. aktuelle Regular-Season-Usage aus `source-data/providers/nflverse/snap-counts/raw-2026.csv`;
3. aktuelle Injury-Signale aus dem Managed-Roster-Signal-Dataset;
4. aktuelle Dynasty-Markt-/ECR-Signale aus FantasyPros/FantasyCalc im Managed-Roster-Signal-Dataset;
5. bestehende datierte Roster-Analyse vom 2026-09-11 als Kontext, nicht als aktuelle Wahrheit.

Besonders material:
- Caleb Douglas spielte in Week 1 91 % der Miami-Offense-Snaps; sein Rookie-/Marktprofil und die sofortige Rolle rechtfertigen Schutz oberhalb der Comparison Boundary.
- Dontayvion Wicks spielte in Week 1 91 % der Philadelphia-Offense-Snaps; seine aktuelle NFL-Rolle verhindert eine Einstufung als allgemeiner Churn.
- Kyle Monangai spielte in Week 1 43 % der Chicago-Offense-Snaps; zusammen mit aktuellem Marktwert bleibt er klar oberhalb der Cut-Line.
- Dylan Sampson wurde auf Injured Reserve geführt und belegt aktuell Reserve statt aktiver Kapazität.
- Ricky Pearsall und De'Zhaun Stribling liegen ebenfalls auf Reserve; Reserve-Kapazität zählt nicht als allgemeiner Churn.

## Aktuelle Klassifikation

| Pos | Spieler | Area | Roster Role | Security | Comparison Boundary | Begründung |
|---|---|---|---|---|---|---|
| QB | Jayden Daniels | active | core_starter | locked | – | Core asset |
| QB | Patrick Mahomes | active | core_starter | locked | – | Core asset |
| QB | Jaxson Dart | active | backup | strong_hold | – | 2QB-Coverage und Marktwert |
| QB | Tyler Shough | active | backup | strong_hold | – | 2QB-Coverage |
| RB | Breece Hall | active | core_starter | locked | – | Core asset |
| RB | Jeremiyah Love | active | core_starter | locked | – | Core / elite dynasty asset |
| RB | Kenneth Walker | active | starter_rotation | strong_hold | – | Startable RB |
| RB | Chase Brown | active | starter_rotation | strong_hold | – | Startable RB |
| RB | Saquon Barkley | active | starter_rotation | strong_hold | – | Contender production |
| RB | Cam Skattebo | active | starter_rotation | strong_hold | – | Startable current role |
| RB | Kyle Monangai | active | backup | strong_hold | – | Relevante aktuelle Usage + Dynasty-/Contingency-Wert |
| RB | Jonathon Brooks | active | prospect | hold | – | Young asset / comeback upside, klar oberhalb Churn |
| RB | Dylan Sampson | reserve | prospect | conditional | future recheck | Aktuell IR; Reserve nimmt aktive Slot-Kosten weg |
| WR | Puka Nacua | active | core_starter | locked | – | Core asset |
| WR | Malik Nabers | active | core_starter | locked | – | Core asset |
| WR | George Pickens | active | starter_rotation | strong_hold | – | Startable |
| WR | Ladd McConkey | active | starter_rotation | strong_hold | – | Startable |
| WR | Jaylen Waddle | active | starter_rotation | strong_hold | – | Startable |
| WR | Marvin Harrison Jr. | active | starter_rotation | strong_hold | – | Startable / dynasty upside |
| WR | Tetairoa McMillan | active | starter_rotation | strong_hold | – | Hoher aktueller Dynasty-Wert / Startability |
| WR | Davante Adams | active | starter_rotation | hold | – | Produktiv, aber Age/Salary/Depth machen ihn zum Consolidation Candidate |
| WR | Alec Pierce | active | backup | hold | – | Aktuelle NFL-Utility; trade before cut |
| WR | Jakobi Meyers | active | backup | hold | – | Aktuelle NFL-Utility; trade before cut |
| WR | Caleb Douglas | active | prospect | strong_hold | – | Rookie + sofortige 91-%-Snap-Role; kein Churn |
| WR | Malachi Fields | active | prospect | hold | **1** | Erster aktiver Opportunity-Cost-Vergleich, aber kein Default Cut |
| WR | Dontayvion Wicks | active | backup | hold | **2** | Zweiter aktiver Opportunity-Cost-Vergleich; 91-%-Snap-Role verhindert Churn |
| WR | Antonio Williams | taxi | prospect | hold | – | Taxi locked; Entwicklungsasset |
| WR | Chris Bell | taxi | prospect | hold | – | Taxi locked; Entwicklungsasset |
| WR | De'Zhaun Stribling | reserve | prospect | strong_hold | – | Reserve; positiver Young-Asset-Wert |
| WR | Ricky Pearsall | reserve | prospect | hold | – | Season-ending injury, aber Reserve statt aktiver Slot-Cost |
| TE | Trey McBride | active | core_starter | locked | – | Core asset |
| TE | Colston Loveland | active | starter_rotation | strong_hold | – | 2TE-format starter value |
| TE | Tyler Warren | active | starter_rotation | strong_hold | – | 2TE-format starter value |
| TE | Harold Fannin | active | backup | strong_hold | – | Hochwertige TE-Coverage |
| K | Jake Bates | active | specialist | churn | specialist only | Austauschbarer Spezialplatz; zählt nicht als allgemeiner Churn-Slot |

## Boundary- und Churn-Schluss

`roster_security` und Comparison Boundary sind unterschiedliche Dimensionen.

- **General Churn:** aktuell 0/2.
- **Specialist Churn:** Jake Bates; zählt nicht in die zwei allgemeinen Slots.
- **Comparison Boundary:** Malachi Fields (1), Dontayvion Wicks (2).
- **Conditional Reserve:** Dylan Sampson; bei Aktivierung erneut gegen die dann aktuelle Boundary bewerten.

Ein `hold` kann der erste Opportunity-Cost-Vergleich sein, wenn das Roster so asset-dicht ist, dass kein echter `churn`-Spieler existiert. Daraus folgt **nicht**, dass dieser Hold ohne materiellen Vergleich gecuttet werden darf.

## Operating conclusion

Das Roster bleibt bewusst unter dem Zwei-Churn-Slot-Ziel. Der korrekte Ausweg ist Konsolidierung, Reserve-Nutzung oder ein Zugang, der Fields/Wicks im direkten Gesamtwertvergleich tatsächlich schlägt. Die Guardrail darf nicht durch künstliches Downgrade positiver Assets erfüllt werden.

## Recheck-Trigger

Diese Klassifikation ist dynamisch und muss insbesondere bei folgenden Ereignissen neu geprüft werden:
- Aktivierung von Sampson, Pearsall oder Stribling;
- materielle Week-2+-Usage-Änderung bei Douglas, Wicks, Fields, Brooks oder Monangai;
- Trade/Add/Drop auf dem Mighty-Giants-Roster;
- relevante Injury-/Depth-Chart-Änderung;
- deutliche Markt-/Replacement-Level-Verschiebung.
