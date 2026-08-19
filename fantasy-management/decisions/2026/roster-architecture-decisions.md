# Roster Architecture Decisions 2026

Dieses Dokument protokolliert bewusst gewählte operative Roster-Standards der Mighty Giants. Dynamische Spieler-Einstufungen gehören in datierte Analysen.

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
