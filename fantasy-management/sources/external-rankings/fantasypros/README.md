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

## Nutzungsregeln

- Die Snapshots sind externe Quellenkontexte und keine dauerhafte Wahrheit.
- Für aktuelle Spieler-, Trade-, Draft-, Roster- oder Free-Agent-Entscheidungen muss die Quelle frisch geprüft werden.
- `ranking.csv` enthält das unveränderte externe Overall-Ranking mit Rank, Spielername, Position und NFL-Team.
- `metadata.json` dokumentiert Format, Abruf- und Snapshot-Provenienz sowie bekannte Einschränkungen.
- `latest.json` ist nur ein Zeiger auf den zuletzt abgelegten Snapshot und keine eigene Ranking-Quelle.
- Das FantasyPros-Superflex-Ranking wird als PPR-/Superflex-Proxy für die Liga verwendet. Bei zwei fest vorgeschriebenen QB-Startplätzen müssen Quarterbacks in der finalen Mighty-Giants-Analyse gegebenenfalls zusätzlich aufgewertet werden.

## Quellenrolle

FantasyPros Dynasty ECR bildet Expertenkonsens ab. Es ist kein ADP und kein ligaindividuelles Ranking. Die Anwendung auf Mighty Giants muss deshalb immer mit aktuellem Ligaformat, Roster, Salary/Cap, Ownership und weiteren Marktquellen abgeglichen werden.
