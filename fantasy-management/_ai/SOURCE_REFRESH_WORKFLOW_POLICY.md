# Source-Refresh-Workflow-Policy

Status: kanonisch

Diese Regel gilt für die sechs automatisierten Fantasy-Management-Source-Producer:

- `FM • Ranking • FantasyPros ECR`
- `FM • Ranking • FantasyCalc Market`
- `FM • Ranking • FFC ADP`
- `FM • Projection • FFToday`
- `FM • Projection • CBS Sports`
- `FM • Signal • Sleeper Trending`

## Trigger-Regel

Jeder Source-Producer behält seinen regulären zeitgesteuerten Refresh und `workflow_dispatch`.

Zusätzlich gilt für alle sechs Workflows ein identischer Code-Change-Contract:

1. Ein Merge nach `main`, der den jeweiligen Fetcher, eine unmittelbar verwendete Fetcher-Implementierung bzw. Helper-Datei, einen zugehörigen Fetcher-Test oder die Workflow-YAML selbst ändert, löst unmittelbar einen Source-Refresh aus.
2. Ein Pull Request mit denselben Pfadänderungen führt den Fetch- und Validierungspfad aus, veröffentlicht aber weder Heartbeat noch Source-Commit nach `main`.
3. Generierte Source-Daten unter `fantasy-management/sources/` sind ausdrücklich keine Push-Trigger. Dadurch darf ein erfolgreicher Source-Commit keinen erneuten Source-Refresh desselben Workflows auslösen.
4. Push- und Pull-Request-Pfade eines Source-Workflows müssen denselben Code-/Test-/Workflow-Contract abdecken.
5. Source-Workflows mit Push-/PR-Trigger verwenden einen `run-name` im Schema `<Workflow-Name> • <Commit-/PR-Titel/Event>`, damit die Actions-Übersicht den Workflow-Kontext sichtbar erhält.
6. PR-Läufe müssen von allen schreibenden Schritten durch `github.event_name != 'pull_request'` getrennt bleiben.

## Abgrenzung

Diese Policy ändert weder die regulären Source-Refresh-Zeitpläne noch die Fetch- oder Materialisierungslogik. Sie betrifft ausschließlich den zusätzlichen Refresh nach Änderungen am ausführbaren Source-Contract sowie dessen sichere PR-Validierung und Actions-Nomenklatur.

Die Invarianten werden in `fantasy-management/_ai/scripts/tests/test_source_refresh_freshness_workflows.py` geprüft.
