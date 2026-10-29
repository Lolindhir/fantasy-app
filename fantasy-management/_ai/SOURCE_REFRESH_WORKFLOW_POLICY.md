# Source-Refresh-Workflow-Policy

Status: kanonisch

Diese Regel gilt für die sechs automatisierten Fantasy-Management-Source-Producer. Seit Issue #947 laufen sie als Matrix-Jobs `Provider • <id>` im gemeinsamen Workflow `FM • Pipeline • Daily` (`.github/workflows/fm-daily.yml`); ihre Heartbeat-Labels bleiben unverändert:

- `FM • Ranking • FantasyPros ECR`
- `FM • Ranking • FantasyCalc Market`
- `FM • Ranking • FFC ADP`
- `FM • Projection • FFToday`
- `FM • Projection • CBS Sports`
- `FM • Signal • Sleeper Trending`

## Trigger-Regel

Der Workflow wird vom zentralen Scheduler (Ziel `fm-daily`, täglich 05:20 Europe/Berlin) per `repository_dispatch` gestartet und bleibt per `workflow_dispatch` manuell startbar.

1. Die Provider-Jobs laufen mit `fail-fast: false`; ein fehlgeschlagener Provider stoppt die anderen nicht. Danach läuft der Materializer auch dann, wenn ein Provider fehlschlug, und nutzt den letzten guten Source-Stand. Der Lauf bleibt rot, die Job Summary nennt die fehlgeschlagenen Provider.
2. Ein Pull Request, der einen Fetcher, einen Fetcher-Test oder die Workflow-YAML ändert, führt nur die Fetcher-Tests aus. Er veröffentlicht weder Heartbeat noch Source-Commit.
3. Ein Merge von Fetcher-Code löst keinen sofortigen Source-Refresh mehr aus (entfallen mit Issue #947); der nächste tägliche Lauf führt den geänderten Fetcher produktiv aus.
4. Generierte Source-Daten unter `fantasy-management/sources/` sind ausdrücklich keine Push-Trigger. Die Pipeline materialisiert nach den Providern selbst; ein Source-Commit startet keinen zweiten Lauf.
5. Der Workflow verwendet einen `run-name` im Schema `FM • Pipeline • Daily • <Commit-/PR-Titel/Event>`.
6. PR-Läufe müssen von allen schreibenden Schritten durch `github.event_name != 'pull_request'` getrennt bleiben.

## Abgrenzung

Diese Policy ändert weder die Fetch- noch die Materialisierungslogik. Sie betrifft Trigger, Reihenfolge und PR-Validierung der Source-Producer.

Die Invarianten werden in `fantasy-management/_ai/scripts/tests/test_source_refresh_freshness_workflows.py` geprüft.
