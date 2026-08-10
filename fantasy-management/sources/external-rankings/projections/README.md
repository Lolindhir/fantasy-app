# Projection Rankings

`projections` ist eine aktive `ranking_kind` unter `external-rankings`.

Die Reihenfolge entsteht aus erwarteter statistischer oder Fantasy-Produktion für einen definierten Horizont. Projection Rankings sind damit Rankings, messen aber etwas anderes als Expert Consensus, Market Value oder ADP.

## Regeln

- Provider und Format bleiben getrennt unter `projections/<provider>/<format>/`.
- Nach Möglichkeit werden die zugrunde liegenden Stat-Projections zusammen mit dem Ranking gespeichert.
- Provider-Fantasy-Punkte sind nicht automatisch Mighty-Giants-Ligapunkte; Scoring-Kontext muss in den Metadaten sichtbar bleiben.
- Für QB/RB/WR/TE werden aus den gespeicherten Rohstats zusätzlich liga-spezifische `core_points` im Derived Layer berechnet. Dabei werden ausschließlich von den aktiven Providern vergleichbar projizierte und im aktuellen `League.json -> ScoringType` bewertbare Komponenten verwendet.
- Nicht vergleichbar projizierte Scoring-Komponenten werden nicht imputiert. Deshalb sind `core_points` bewusst keine vollständige exakte Liga-Projektion.
- Positionsspezifische Rankings werden nur innerhalb derselben Position per listenlängenabhängigem Perzentil verglichen.
- Projection-Werte sind dynamisch und werden vor entscheidungsrelevanten Analysen frisch geladen.
- Ein Projection Ranking ist kein Expert Consensus, kein ADP und kein Trade-Marktwert.
- Direkte Provider-Projections und ein späterer Projection-Consensus dürfen nicht als unabhängige Stimmen doppelt gewichtet werden, wenn der Consensus denselben Provider bereits enthält.
- Kicker behalten ihren eigenen liga-spezifischen Scoring-/Streaming-Contract; offensive `core_points` ersetzen diesen nicht.

## Aktive Provider und Ranking IDs

### FFToday

Aktiv:

- `redraft-qb-preseason`
- `redraft-rb-preseason`
- `redraft-wr-preseason`
- `redraft-te-preseason`
- `redraft-kicker-preseason`

Der offensive Fetcher verarbeitet die öffentliche FFToday-Pagination vollständig. Alle Seiten müssen dieselbe Saison und dasselbe sichtbare Updated-Datum ausweisen; Schleifen, doppelte Source-Spieler-IDs, zu kleine Populationen oder inkonsistente Seitenzustände führen zu einem fail-closed Fehler. Das aktuelle Raw-Artefakt der offensiven Feeds enthält alle erfolgreich abgerufenen öffentlichen Seiten in einem zusammengesetzten `raw-latest.html`, getrennt durch Source-Page-Kommentare.

### CBS Sports

Aktiv:

- `redraft-qb-preseason`
- `redraft-rb-preseason`
- `redraft-wr-preseason`
- `redraft-te-preseason`
- `redraft-kicker-preseason`

Die offensiven CBS-Feeds verwenden weiterhin ausschließlich die öffentliche Non-PPR-Tabelle. Provider-FPTS/FPPG werden als Source-Werte erhalten; die liga-spezifische Rekalkulation erfolgt nur aus den separat gespeicherten Rohstats.

DST bleibt auditiert, aber außerhalb des aktuellen aktiven Liga-Lineup-Scopes.

## Derived Operations Layer

`fantasy-management/generated/operations/player-signals.json` vereinigt die positionsspezifischen Projection-Quellen provider-neutral:

- Provider-Rank und positionsbezogenes Perzentil bleiben getrennt;
- `summary.consensus_percentile` ist nur der Mittelwert der gelisteten Provider-Perzentile;
- `summary.percentile_spread` beschreibt Provider-Abweichung;
- Provider-Fantasy-Punkte werden nicht gemittelt;
- `providers.<provider>.league_scoring.core_points` wendet aktuelles Mighty-Giants-Scoring nur auf die vergleichbaren projizierten Core-Stats an;
- fehlende erste Source-Materialisierungen werden beim Bootstrap als explizite Qualitätswarnung behandelt und nicht als Null-Projektion interpretiert.

Das Monitoring nutzt Projection-Bewegungen als Research- und Recalculation-Trigger. Finale Start/Sit-, Add/Drop-, Waiver- oder Trade-Entscheidungen bleiben einem übergeordneten Entscheidungsworkflow vorbehalten.
