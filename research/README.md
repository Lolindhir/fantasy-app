# Research – gemeinsame Datenprodukte

Dieser Repository-Rootbereich bewahrt **historische, empirische Untersuchungen und Audits** gemeinsamer Datenprodukte auf. Er ist weder eine produktive Datenquelle noch ein alternativer Vertrag, kein Arbeits-Backlog und kein Consumer.

## Struktur und Regeln

- `research/<data-product>/<analysis-year>/`: Nach dem **zentralen Datenprodukt** gruppieren, nicht nach Einzel-Feature (Vegas, Defense, Usage) oder Consumer.
- Datierte Berichte mit Forschungsfrage, Hypothese, Vergleichsgrundlage, Quelle/Commit/Blob, Filterpopulation, Methode und Parameter, Messwerten, Unsicherheit und Ergebnisstatus.
- Historische Experimente werden **nicht nachträglich** mit neuer Evidenz überschrieben. Ein späterer Recheck erhält eine neue datierte Datei mit Rückverweis.
- Validierungsstatus unterscheiden: `supported`, `partially_supported`, `rejected`, `inconclusive`; Explorationssignal ist keine Produktfreigabe.
- Fachlicher Produktvertrag: `.ai-context/manual/`. Modellimplementierung / Reproduktionswerkzeug: `tools/`. Source-/Derived-Fakten: `data-source/` und `data-derived/`. Verbraucher-spezifische Player-/Roster-/Manager-Einschätzungen: `fantasy-management/analyses/`.
- GitHub Issues bleiben Arbeitstracking mit Link auf den **dauerhaften Research-Bericht** und kurzem Ergebnis. Offene Forschungshypothesen müssen nicht als immer offene Issues bestehen bleiben.

## PlayerWeekFantasy (Punktprognosen und Scoring)

Die Shared Derived Data Produkt-Spezifikation ist [PlayerWeekFantasy](../.ai-context/manual/player-week-fantasy.yaml). Das Produkt umfasst finale Fantasy-Punkte, erwartete Punktprognosen (V4-C), Prediction-Ranges (PI1) und Liga-Scoring; App und Fantasy Management können es konsumieren.

Archiv für 2026:
- [RB-Production × Defense](player-week-fantasy/2026/2026-10-14-rb-production-defense-matchup-pilot.md)
- [RB-Usage × Defense](player-week-fantasy/2026/2026-10-14-rb-usage-opportunity-defense-pilot.md)
- [Vegas-V5 Forschungs-Audit und Einordnung](player-week-fantasy/2026/2026-10-31-vegas-v5-research-audit.md)
- [Vollständige zeitgenössische Research-Checkpoints 3–9](player-week-fantasy/2026/2026-10-31-vegas-v5-checkpoints.md)

Frühere Dateilinks im Fantasy-Management-Ordner werden nur noch als kurze Verweise erhalten, ohne doppelte Pflege.
- [Sleeper-Projections / Availability / Shadow-Test – archiviertes Audit (pausiert)](player-week-fantasy/2026/2026-10-31-sleeper-projections-availability-shadow-audit.md)
