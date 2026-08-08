# Projection Rankings

`projections` ist eine aktive `ranking_kind` unter `external-rankings`.

Die Reihenfolge entsteht aus erwarteter statistischer oder Fantasy-Produktion für einen definierten Horizont. Projection Rankings sind damit Rankings, messen aber etwas anderes als Expert Consensus, Market Value oder ADP.

## Regeln

- Provider und Format bleiben getrennt unter `projections/<provider>/<format>/`.
- Nach Möglichkeit werden die zugrunde liegenden Stat-Projections zusammen mit dem Ranking gespeichert.
- Provider-Fantasy-Punkte sind nicht automatisch Mighty-Giants-Ligapunkte; Scoring-Kontext muss in den Metadaten sichtbar bleiben.
- Positionsspezifische Rankings werden nur innerhalb derselben Position per listenlängenabhängigem Perzentil verglichen.
- Projection-Werte sind dynamisch und werden vor entscheidungsrelevanten Analysen frisch geladen.
- Ein Projection Ranking ist kein Expert Consensus, kein ADP und kein Trade-Marktwert.

## Aktive Provider

- `fftoday`: aktuell `redraft-kicker-preseason`; weitere öffentlich verfügbare FFToday-Positionen sind auditiert, aber noch nicht aktiv materialisiert.
