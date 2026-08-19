# Roster Architecture Decisions 2026

Dieses Dokument protokolliert bewusst gewählte operative Roster-Standards der Mighty Giants. Dynamische Spieler-Einstufungen und konkrete Coverage-Zielzahlen gehören in datierte Analysen.

## 2026-08-19 – Zwei-Achsen-Roster und Churn-Budget

- Type: roster architecture
- Decision: Mighty-Giants-Spieler werden künftig getrennt nach `roster_role` und `roster_security` klassifiziert.
- Roster Role: `core_starter`, `starter_rotation`, `backup`, `prospect`, `specialist`.
- Roster Security: `locked`, `strong_hold`, `hold`, `conditional`, `churn`.
- Streamer-Regel: `streamer` ist keine dauerhafte Spielerrolle. Streaming ist die Nutzung bewusst freigehaltener Roster-Kapazität.
- Default Churn Budget: **2 allgemeine aktive Churn-Slots**.
- Drei-Slot-Modus: temporär möglich, wenn Bye-/Injury-/Waiver-/Playoff-Kontext mehrere parallele kurzfristige Moves rechtfertigt.
- Taxi: zählt nicht zum allgemeinen Churn-Budget.
- Reserve/IR: zählt nicht zum allgemeinen Churn-Budget.
- Kicker: der gehaltene Kicker kann `specialist | churn` sein; der notwendige Kicker-Platz selbst ersetzt keinen der zwei allgemeinen Churn-Slots.
- Transaction Standard: Wenn ein Add oder Draft Pick einen bisherigen Churn-Slot in einen dauerhaften Hold verwandelt, muss gleichzeitig der neue Churn-Boundary-Spieler benannt werden.
- Roster-Clogging: Ein Roster kann trotz Einhaltung des harten Liga-Limits als zu voll gelten, wenn keine zwei realistisch repurposable aktiven Plätze mehr vorhanden sind.
- FA-Draft-Folge: Späte FA-Draft-Picks sollen nicht allein deshalb genutzt werden, weil sie vorhanden sind. Der eingehende Spieler muss den erforderlichen Cut plus den Verlust operativer Flexibilität rechtfertigen.
- Canonical guardrail: `fantasy-management/_ai/ROSTER_ARCHITECTURE.md`
- Current baseline: `fantasy-management/analyses/2026/roster/2026-08-19-roster-role-security-baseline.md`

## 2026-08-19 – Positional Coverage vor Churn

- Type: roster architecture
- Decision: Die Mighty-Giants-Rosterplanung berücksichtigt vor Taxi- und Churn-Optimierung ausdrücklich die positionsspezifische Starter- und Backup-Coverage.
- Starter Minimum: Feste Starteranforderungen werden immer dynamisch aus dem aktuellen `League.json -> RosterSize` abgeleitet; keine Positionszahl wird dauerhaft hartcodiert.
- Coverage Floor: Für relevante feste Positionen wird eine aktuelle Mindestabdeckung bestimmt, unter die das Roster ohne bewusst geplanten Stream-/Notfallpfad nicht sinken soll.
- Preferred Coverage: Zusätzlich wird eine aktuelle gewünschte Abdeckung bestimmt, wenn der zusätzliche Backup gegenüber seiner Roster-Opportunity-Cost sinnvoll ist.
- FLEX Rule: FLEX-eligible Skill-Positionen werden zusätzlich als gemeinsamer `startable_skill_pool` bewertet. Relevant sind benötigte Skill-Lineup-Slots, tatsächlich startbare Spieler und die verbleibende Marge.
- Coverage Reserve: Ein strukturell notwendiger Backup ist nicht automatisch unantastbar, aber sein Coverage-Wert muss beim Cut-/Trade-Vergleich zusätzlich zum isolierten Player Value berücksichtigt werden.
- Churn Rule: Ein Spieler kann nur dann als allgemeiner Churn-Slot zählen, wenn seine Repurposierung die Position nicht unter den aktuellen Coverage Floor drückt.
- Kicker: Genau ein Kicker bleibt der Default-Spezialplatz; ein temporärer zweiter Kicker verbraucht allgemeinen Churn.
- Taxi Interaction: In der Pre-Lock-Phase wird die virtuelle Taxi-Zuweisung erst nach Starter-/Coverage-Prüfung vorgenommen; ein Rookie mit notwendiger früher Lineup- oder Coverage-Utility soll nicht nur wegen Taxi-Upside weggeparkt werden.
- Evaluation Order: feste Starteranforderungen → Positions-Coverage → gemeinsamer FLEX-/Skill-Pool → Taxi → allgemeine Churn-Slots.
- Canonical guardrail: `fantasy-management/_ai/ROSTER_ARCHITECTURE.md`
- Current coverage baseline: `fantasy-management/analyses/2026/roster/2026-08-19-positional-coverage-baseline.md`
