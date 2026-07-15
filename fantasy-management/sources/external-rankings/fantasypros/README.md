# FantasyPros External Rankings

Dieser Ordner enthält datierte, maschinenlesbare Snapshots externer FantasyPros-Rankings für Fantasy-Management-Analysen.

## Ablagestruktur

```text
fantasypros/
  README.md
  dynasty-superflex-ppr/
    latest.json
    snapshots/
      YYYY-MM-DD/
        ranking.csv
        raw-ecr-data.json
        metadata.json
```

## Direkter Abruf

Der offizielle FantasyPros-Dynasty-Superflex-ECR wird direkt aus dem in der öffentlichen HTML-Seite eingebetteten `ecrData`-Payload gelesen:

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py
```

Nützliche Prüfmodi:

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py --dry-run
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py --from-file path/to/saved-page.html --dry-run
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py --skip-unchanged
```

Der Fetcher nutzt keinen Mirror-Fallback. Bei Netzwerk-, Schema- oder Plausibilitätsfehlern wird kein neuer `latest.json`-Stand veröffentlicht. Erfolgreiche Abrufe erzeugen oder aktualisieren den datierten Snapshot und dokumentieren Abrufzeit, Zeilenanzahl, Positionsverteilung, fehlende Rangnummern und SHA-256.

Mit `--skip-unchanged` wird kein neuer Snapshot geschrieben, wenn der vollständige normalisierte Raw-Payload denselben SHA-256 wie der zuletzt veröffentlichte Snapshot hat.

## Automatische Aktualisierung

Der GitHub-Actions-Workflow `Update FantasyPros Rankings` läuft täglich um `05:17 UTC` und kann zusätzlich manuell gestartet werden. Er testet zuerst den Fetcher, führt danach den direkten Abruf mit `--skip-unchanged` aus und committet nur tatsächlich geänderte Snapshot-Dateien.

Workflow-Datei:

```text
.github/workflows/update-fantasypros-rankings.yml
```

## Dateien eines Snapshots

- `ranking.csv` ist die kompakte normalisierte Analysequelle. Sie enthält Overall-Rang, Positionsrang, Position, NFL-Team und – sofern FantasyPros ihn liefert – die FantasyPros-Spieler-ID.
- `raw-ecr-data.json` enthält den vollständigen geparsten `ecrData`-Payload. Die JSON-Formatierung wird normalisiert, aber Felder werden nicht entfernt.
- `metadata.json` dokumentiert Format, Raw-Schema, Hashes, Abruf- und Snapshot-Provenienz sowie bekannte Einschränkungen.
- `latest.json` ist nur ein Zeiger auf den zuletzt erfolgreich abgelegten Snapshot und keine eigene Ranking-Quelle.

Der bestehende Snapshot vom 15.07.2026 wurde ursprünglich nur als normalisierte CSV übernommen. Sein Positionsrang wurde aus der Reihenfolge innerhalb jeder Position abgeleitet. Ein Raw-Payload wird dafür bewusst nicht rekonstruiert oder als Originalquelle ausgegeben. Der nächste erfolgreiche Direktabruf erzeugt `raw-ecr-data.json` automatisch und übernimmt `pos_rank` direkt aus FantasyPros, soweit vorhanden.

## Nutzungsregeln

- Die Snapshots sind externe Quellenkontexte und keine dauerhafte Wahrheit.
- Für aktuelle Spieler-, Trade-, Draft-, Roster- oder Free-Agent-Entscheidungen soll der direkte Abruf erneut ausgeführt werden, wenn der Snapshot nicht vom selben Tag stammt oder sich der Markt schnell bewegt.
- Die normalisierte CSV ist die primäre Join- und Analysequelle; die Raw-JSON dient für zusätzliche Felder, Schema-Audits und spätere Neuauswertungen.
- Das FantasyPros-Superflex-Ranking wird als PPR-/Superflex-Proxy für die Liga verwendet. Bei zwei fest vorgeschriebenen QB-Startplätzen müssen Quarterbacks in der finalen Mighty-Giants-Analyse gegebenenfalls zusätzlich aufgewertet werden.

## Quellenrolle

FantasyPros Dynasty ECR bildet Expertenkonsens ab. Es ist kein ADP und kein ligaindividuelles Ranking. Die Anwendung auf Mighty Giants muss deshalb immer mit aktuellem Ligaformat, Roster, Salary/Cap, Ownership und weiteren Marktquellen abgeglichen werden.
