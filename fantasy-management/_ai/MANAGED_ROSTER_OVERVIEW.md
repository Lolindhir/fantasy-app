# Managed Roster Overview

Purpose: aktueller, materialisierter Read-Model-Vertrag für die Mighty Giants. Er soll Roster-, FA-Draft-, Waiver-, Trade- und Weekly-Entscheidungen mit derselben jederzeit abrufbaren Roster-Struktur versorgen.

## Contract

Canonical current outputs:

- `fantasy-management/generated/operations/managed-roster-overview.json`
- `fantasy-management/generated/operations/managed-roster-overview.md`

Der JSON-Contract ist die maschinenlesbare Quelle. Die Markdown-Datei ist eine deterministisch daraus erzeugte menschenlesbare Ansicht.

## Trennung von Fakten und Bewertung

V1 ist bewusst hybrid.

Automatisch neu abgeleitet werden insbesondere:

- aktuelle Roster-/Taxi-/Reserve-Mitgliedschaft aus `managed-roster-signals.json`, dessen TeamID-1 Membership seit Checkpoint 6Q aus Canonical League Source Data stammt;
- aktive Kapazität und Belegung auf Basis dieser canonical-derived Membership;
- feste Starteranforderungen aus `League.json -> RosterSize`;
- aktuelle Taxi-Phase;
- Positionsbestände und Coverage-Status;
- gemeinsamer startbarer FLEX-/Skill-Pool und Marge;
- Churn-Eignung **unter der aktuell gültigen Role/Security-Klassifikation**.

Noch evaluativ/versioniert sind insbesondere:

- `roster_role`;
- `roster_security`;
- aktuelle `coverage_floor`-/`preferred_coverage`-Ziele;
- Churn-Boundary-Priorität.

Diese Felder stammen in V1 aus `fantasy-management/automation/roster-evaluation-state.json`. Die Datei ist ein versionierter Bewertungs-Seed, keine permanente Spielerwahrheit.

## User Overrides

`user_overrides` in der Evaluation-State-Datei sind ausdrücklich vorgesehen. Ein späterer automatischer Klassifikator darf eine bewusste User-Entscheidung nicht still überschreiben.

Jede Klassifikation muss deshalb ihre Provenienz ausweisen:

- automatisch;
- manueller/agentischer Seed;
- expliziter User Override;
- unklassifiziert / Review erforderlich.

## Comparison Boundary vs. General Churn

Der Read-Model-Contract trennt zwei unterschiedliche Konzepte:

- **Comparison Boundary:** geordnete Opportunity-Cost-Kandidaten für einen materiellen Add/Trade/Draft-Zugang. Die Reihenfolge wird über `boundary_priority` aus der aktuell gültigen Evaluation gespeist und kann auch `hold` oder `conditional` enthalten.
- **General Churn:** tatsächlich frei repurposable aktive Plätze. Dafür reicht `boundary_priority` ausdrücklich nicht; von der Security-Seite qualifiziert nur `roster_security = churn`, zusätzlich zu Active-/Coverage-/Specialist-Guardrails.

Ein asset-dichtes Roster kann deshalb gleichzeitig eine nicht-leere Comparison Boundary und **0 allgemeine Churn-Slots** besitzen.

Der JSON-Output muss diese Trennung sichtbar machen. `candidate_pool` ist der Comparison-Boundary-Pool; jeder Eintrag weist aus, ob er als General Churn zählt. Der Guardrail-Status des Zwei-Slot-Ziels wird ausschließlich aus echten General-Churn-Slots abgeleitet.

## Fail-visible Missing Classification

`unclassified` darf nicht als neutraler Wert behandelt werden, wenn dadurch eine Boundary- oder Churn-Aussage scheinbar vollständig würde.

- Jeder unklassifizierte Managed Player bleibt Quality-Warning / `needs_classification`.
- Bei aktiven unklassifizierten Spielern ist die Comparison-/Churn-Aussage nicht entscheidungsreif, solange deren mögliche Boundary-Relevanz nicht aufgelöst ist.
- Der Read Model darf in diesem Zustand nicht implizieren, dass eine leere `candidate_pool` eine belastbare Aussage „keine Boundary vorhanden“ ist.
- Neue Roster-Mitglieder und materielle Roster-/Reserve-/Taxi-/Usage-/Role-Änderungen müssen einen Reclassification-Bedarf sichtbar machen, bis der aktuelle Evaluation-State nachgezogen wurde.

## Taxi

Vor dem Taxi-Lock ist die technische Sleeper-Belegung nicht strategisch bindend. Der Overview-Contract zeigt sie nur als `current_technical_occupants`.

V1 automatisiert die optimale virtuelle Taxi-Zuweisung noch nicht. Deshalb bleibt die Churn-Boundary in `pre_lock` ausdrücklich provisional, bis die gemeinsame Rookie-/Taxi-Optimierung automatisiert oder manuell entschieden wurde.

## Zielarchitektur

Das Endziel ist ein vollständig erklärbarer Klassifikator, der Role, Security, Coverage und Churn-Boundary aus versionierten Kriterien und aktuellen Signalen ableitet.

Dafür gelten folgende Leitplanken:

1. Jede Einstufung muss ihre verwendeten Signale und Regeln offenlegen.
2. Harte Liga-/Roster-Fakten bleiben strikt von Bewertungsheuristiken getrennt.
3. Fehlende oder widersprüchliche Signale führen zu niedriger Confidence bzw. Review-Bedarf statt zu erfundener Sicherheit.
4. User Overrides bleiben möglich und sichtbar.
5. Neue automatische Kriterien werden erst nach Backtest/Kalibrierung und ausdrücklicher Freigabe kanonisch.
6. Eine automatische Einstufung darf keine endgültige Transaktion ausführen; sie ist Entscheidungsinput.

## Materialisierung

`build_managed_roster_overview.py` erzeugt beide Outputs. Seit Checkpoint 6U liest der Builder Membership/Buckets nicht mehr erneut aus `League.json`, sondern ausschließlich aus dem bereits canonical-active `managed-roster-signals.json`. `League.json` bleibt non-membership Enrichment für Team-Display, Lineup-/RosterSize-Regeln, Reserve-/Taxi-Slots und Phase/Status. Der bestehende Player-Signal-Materialisierungslauf ruft den Overview-Builder nach erfolgreicher Player-Signal-Erzeugung mit auf, sodass keine zweite parallele Operations-Pipeline benötigt wird.
