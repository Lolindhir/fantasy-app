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
- `metadata.json` dokumentiert Format, Raw-Schema, Feldabdeckung, Beziehungen zwischen Konsensfeldern, Hashes, Abruf- und Snapshot-Provenienz sowie bekannte Einschränkungen.
- `latest.json` ist nur ein Zeiger auf den zuletzt erfolgreich abgelegten Snapshot und keine eigene Ranking-Quelle.

Normalisierte CSV-Spalten:

```text
name,Rank,position,team,position_rank,tier,rank_min,rank_max,rank_ave,rank_std,source_player_id
```

## Interpretation der Konsensfelder

- `tier` ist die von FantasyPros gelieferte Wertgruppe. Tier-Grenzen sind für Draft- und Trade-Analysen meist aussagekräftiger als kleine Rangabstände innerhalb desselben Tiers.
- `rank_min` und `rank_max` sind der beste beziehungsweise schlechteste von FantasyPros gelieferte Expertenrang. Die Differenz kann als zusätzliche Spannweite berechnet werden, wird aber nicht redundant in der CSV gespeichert.
- `rank_ave` ist der von FantasyPros gelieferte durchschnittliche Expertenrang.
- `rank_std` misst die Streuung der von FantasyPros gelieferten Expertenrangwerte. Ein kleiner Wert steht für engere, ein großer Wert für stärkere Abweichungen innerhalb dieser Werte.
- Eine große Min-Max-Spanne kann durch einen einzelnen Ausreißer entstehen. Für die Konsensstärke ist `rank_std` deshalb das primäre Streuungsmaß; Min-Max bleibt eine ergänzende Extremwertprüfung.
- `rank_ecr` ist die von FantasyPros veröffentlichte finale Konsensreihenfolge. Sie ist nicht garantiert innerhalb von `rank_min` und `rank_max`, weil diese Felder die eingereichten Expertenränge beschreiben. Solche Fälle werden als Diagnose in `metadata.json` dokumentiert und nicht als fehlerhafter Payload verworfen.
- `rank_std` ist keine Wahrscheinlichkeit, kein Verletzungsrisiko und keine direkte Aussage über die Wahrscheinlichkeit, dass ein Spieler seinen ECR bestätigt.

Fehlende optionale Konsenswerte bleiben in der CSV leer. Nichtleere Werte werden numerisch normalisiert und fail-closed validiert: Tier und Ränge müssen positiv sein, `rank_min` darf `rank_max` nicht übersteigen, `rank_ave` muss innerhalb der vorhandenen Min-Max-Spanne liegen und `rank_std` darf nicht negativ sein. Ein ECR außerhalb der Experten-Spanne bleibt als originaler Quellwert erhalten.

### Verhältnis von `rank_ecr` zu den Expertenstatistiken

#### Gesichert beobachtet

- `rank_ecr` ist die finale von FantasyPros veröffentlichte Overall-Reihenfolge; `rank_min`, `rank_max`, `rank_ave` und `rank_std` sind davon getrennte Statistikfelder im selben Quell-Payload.
- `rank_ecr` kann außerhalb von `rank_min` bis `rank_max` liegen. Das ist ein beobachtetes Quellenverhalten und kein Parser- oder CSV-Fehler.
- Im Live-Snapshot vom 15.07.2026 lagen 148 von 541 ECR-Werten außerhalb der jeweiligen Min-Max-Spanne. Die aktuelle Anzahl steht maschinenlesbar in `metadata.json -> snapshot.consensus_relationship_diagnostics`.
- Beispiel aus diesem Snapshot: Geno Smith hatte `rank_ecr = 230`, `rank_min = 135`, `rank_max = 188`, `rank_ave = 155.70` und `rank_std = 15.52`.
- Die exakte FantasyPros-Aggregationsformel und die Zahl der pro Spieler tatsächlich berücksichtigten Experten sind im gespeicherten Payload nicht enthalten.

#### Plausible, aber unbestätigte Erklärung

Eine mögliche Erklärung sind unterschiedlich tiefe Expertenlisten: Einige Experten können einen tief gerankten Spieler aufführen, während andere ihn nicht mehr listen. Die Statistikfelder könnten dann nur vorhandene Rangwerte beschreiben, während die finale ECR-Reihenfolge fehlende Rankings oder weitere Aggregationsregeln berücksichtigt. Ebenfalls denkbar sind Expertengewichtung, Aktualitätsgewichtung oder getrennte Berechnungs- beziehungsweise Cache-Schritte.

Diese Erklärung ist **nicht von FantasyPros bestätigt** und darf nicht als dokumentierte Methodik ausgegeben werden. Die Snapshot-Metadaten kennzeichnen den Methodikstatus und die offenen Punkte deshalb ausdrücklich als unbekannt beziehungsweise unbestätigt.

#### Operative Auswertung

- `rank_ecr` bleibt die maßgebliche FantasyPros-Gesamtposition.
- `rank_std` wird als Streuung der von der Quelle gelieferten Expertenrangwerte gelesen, nicht als Messung der vollständigen Expertenabdeckung und nicht als Erfolgswahrscheinlichkeit.
- Eine niedrige `rank_std` bei gleichzeitig großer Differenz zwischen `rank_ecr` und `rank_ave` bedeutet nur, dass die vorhandenen Statistikwerte eng beieinanderliegen; sie beweist keinen breiten Konsens aller verfügbaren Experten.
- Ein großer Abstand zwischen `rank_ecr` und `rank_ave` ist ein Hinweis auf eine Aggregations- oder Coverage-Einschränkung. Bei wertrelevanten Entscheidungen sollen dann aktuelle News, weitere Marktquellen und der Liga-Kontext zusätzlich geprüft werden.

## Nutzungsregeln

- Die Snapshots sind externe Quellenkontexte und keine dauerhafte Wahrheit.
- Für aktuelle Spieler-, Trade-, Draft-, Roster- oder Free-Agent-Entscheidungen soll der direkte Abruf erneut ausgeführt werden, wenn der Snapshot nicht vom selben Tag stammt oder sich der Markt schnell bewegt.
- Die normalisierte CSV ist die primäre Join- und Analysequelle; die Raw-JSON dient für zusätzliche Felder, Schema-Audits und spätere Neuauswertungen.
- Tier und Konsensstreuung ergänzen den ECR, ersetzen aber weder aktuelle News noch ligaindividuelle Positionsknappheit und Roster-Kontext.
- Das FantasyPros-Superflex-Ranking wird als PPR-/Superflex-Proxy für die Liga verwendet. Bei zwei fest vorgeschriebenen QB-Startplätzen müssen Quarterbacks in der finalen Mighty-Giants-Analyse gegebenenfalls zusätzlich aufgewertet werden.

## Quellenrolle

FantasyPros Dynasty ECR bildet Expertenkonsens ab. Es ist kein ADP und kein ligaindividuelles Ranking. Die Anwendung auf Mighty Giants muss deshalb immer mit aktuellem Ligaformat, Roster, Salary/Cap, Ownership und weiteren Marktquellen abgeglichen werden.
