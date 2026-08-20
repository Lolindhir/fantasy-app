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

- aktuelle Roster-/Taxi-/Reserve-Mitgliedschaft;
- aktive Kapazität und Belegung;
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

`build_managed_roster_overview.py` erzeugt beide Outputs. Der bestehende Player-Signal-Materialisierungslauf ruft den Overview-Builder nach erfolgreicher Player-Signal-Erzeugung mit auf, sodass keine zweite parallele Operations-Pipeline benötigt wird.
