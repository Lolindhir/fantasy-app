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
```

Der Fetcher nutzt keinen Mirror-Fallback. Bei Netzwerk-, Schema- oder Plausibilitätsfehlern wird kein neuer `latest.json`-Stand veröffentlicht. Erfolgreiche Abrufe erzeugen oder aktualisieren den datierten Snapshot und dokumentieren Abrufzeit, Zeilenanzahl, Positionsverteilung, fehlende Rangnummern und SHA-256.

## Nutzungsregeln

- Die Snapshots sind externe Quellenkontexte und keine dauerhafte Wahrheit.
- Für aktuelle Spieler-, Trade-, Draft-, Roster- oder Free-Agent-Entscheidungen soll der direkte Abruf erneut ausgeführt werden, wenn der Snapshot nicht vom selben Tag stammt oder sich der Markt schnell bewegt.
- `ranking.csv` enthält das externe Overall-Ranking mit Rank, Spielername, Position und NFL-Team.
- `metadata.json` dokumentiert Format, Abruf- und Snapshot-Provenienz sowie bekannte Einschränkungen.
- `latest.json` ist nur ein Zeiger auf den zuletzt erfolgreich abgelegten Snapshot und keine eigene Ranking-Quelle.
- Das FantasyPros-Superflex-Ranking wird als PPR-/Superflex-Proxy für die Liga verwendet. Bei zwei fest vorgeschriebenen QB-Startplätzen müssen Quarterbacks in der finalen Mighty-Giants-Analyse gegebenenfalls zusätzlich aufgewertet werden.

## Quellenrolle

FantasyPros Dynasty ECR bildet Expertenkonsens ab. Es ist kein ADP und kein ligaindividuelles Ranking. Die Anwendung auf Mighty Giants muss deshalb immer mit aktuellem Ligaformat, Roster, Salary/Cap, Ownership und weiteren Marktquellen abgeglichen werden.
