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

Der Fetcher nutzt keinen Mirror-Fallback. Bei Netzwerk-, Schema- oder Plausibilitätsfehlern wird kein neuer `latest.json`-Stand veröffentlicht. Erfolgreiche Abrufe erzeugen oder aktualisieren den datierten Snapshot und dokumentieren Abrufzeit, Zeilenanzahl, Positionsverteilung, Feldabdeckung, fehlende Rangnummern und SHA-256.

Mit `--skip-unchanged` wird kein neuer Snapshot geschrieben, wenn sowohl der vollständige normalisierte Raw-Payload als auch das erwartete normalisierte CSV-Schema mit dem zuletzt veröffentlichten Snapshot übereinstimmen. Eine Schema-Erweiterung erzwingt damit auch bei identischem Quell-Payload eine Neugenerierung der CSV.

## Automatische Aktualisierung

Der GitHub-Actions-Workflow `Update FantasyPros Rankings` läuft täglich um `05:17 UTC` und kann zusätzlich manuell gestartet werden. Er testet zuerst den Fetcher, führt danach den direkten Abruf mit `--skip-unchanged` aus und committet nur tatsächlich geänderte Snapshot-Dateien.

Workflow-Datei:

```text
.github/workflows/update-fantasypros-rankings.yml
```

## Dateien eines Snapshots

- `ranking.csv` ist die kompakte normalisierte Analysequelle. Sie enthält Spielername, Overall-ECR, Position, NFL-Team, Positionsrang, Tier, besten und schlechtesten Expertenrang, durchschnittlichen Expertenrang, Rang-Standardabweichung und – sofern FantasyPros ihn liefert – die FantasyPros-Spieler-ID.
- `raw-ecr-data.json` enthält den vollständigen geparsten `ecrData`-Payload. Die JSON-Formatierung wird normalisiert, aber Felder werden nicht entfernt.
- `metadata.json` dokumentiert Format, Raw-Schema, Feldabdeckung, Hashes, Abruf- und Snapshot-Provenienz sowie bekannte Einschränkungen.
- `latest.json` ist nur ein Zeiger auf den zuletzt erfolgreich abgelegten Snapshot und keine eigene Ranking-Quelle.

Normalisierte CSV-Spalten:

```text
name,Rank,position,team,position_rank,tier,rank_min,rank_max,rank_ave,rank_std,source_player_id
```

## Interpretation der Konsensfelder

- `tier` ist die von FantasyPros gelieferte Wertgruppe. Tier-Grenzen sind für Draft- und Trade-Analysen meist aussagekräftiger als kleine Rangabstände innerhalb desselben Tiers.
- `rank_min` und `rank_max` sind der beste beziehungsweise schlechteste Rang unter den einbezogenen Experten. Die Differenz kann als zusätzliche Spannweite berechnet werden, wird aber nicht redundant in der CSV gespeichert.
- `rank_ave` ist der durchschnittliche Expertenrang.
- `rank_std` misst die Streuung der Expertenränge. Ein kleiner Wert steht für engeren Konsens, ein großer Wert für stärkere Abweichungen.
- Eine große Min-Max-Spanne kann durch einen einzelnen Ausreißer entstehen. Für die Konsensstärke ist `rank_std` deshalb das primäre Streuungsmaß; Min-Max bleibt eine ergänzende Extremwertprüfung.
- `rank_std` ist keine Wahrscheinlichkeit, kein Verletzungsrisiko und keine direkte Aussage über die Wahrscheinlichkeit, dass ein Spieler seinen ECR bestätigt.

Fehlende optionale Konsenswerte bleiben in der CSV leer. Nichtleere Werte werden numerisch normalisiert und fail-closed validiert: Tier und Ränge müssen positiv sein, `rank_min` darf `rank_max` nicht übersteigen, ECR und Durchschnitt müssen innerhalb der vorhandenen Min-Max-Spanne liegen und `rank_std` darf nicht negativ sein.

## Nutzungsregeln

- Die Snapshots sind externe Quellenkontexte und keine dauerhafte Wahrheit.
- Für aktuelle Spieler-, Trade-, Draft-, Roster- oder Free-Agent-Entscheidungen soll der direkte Abruf erneut ausgeführt werden, wenn der Snapshot nicht vom selben Tag stammt oder sich der Markt schnell bewegt.
- Die normalisierte CSV ist die primäre Join- und Analysequelle; die Raw-JSON dient für zusätzliche Felder, Schema-Audits und spätere Neuauswertungen.
- Tier und Konsensstreuung ergänzen den ECR, ersetzen aber weder aktuelle News noch ligaindividuelle Positionsknappheit und Roster-Kontext.
- Das FantasyPros-Superflex-Ranking wird als PPR-/Superflex-Proxy für die Liga verwendet. Bei zwei fest vorgeschriebenen QB-Startplätzen müssen Quarterbacks in der finalen Mighty-Giants-Analyse gegebenenfalls zusätzlich aufgewertet werden.

## Quellenrolle

FantasyPros Dynasty ECR bildet Expertenkonsens ab. Es ist kein ADP und kein ligaindividuelles Ranking. Die Anwendung auf Mighty Giants muss deshalb immer mit aktuellem Ligaformat, Roster, Salary/Cap, Ownership und weiteren Marktquellen abgeglichen werden.
