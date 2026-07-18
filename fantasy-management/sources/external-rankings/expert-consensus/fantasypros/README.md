# FantasyPros Expert-Consensus Rankings

Dieser Ordner enthält datierte, maschinenlesbare FantasyPros-ECR-Snapshots innerhalb der Ranking-Art `expert-consensus`.

## Ranking-Familie

| Ranking-ID | Horizont | Primäre Auswertungsrolle |
|---|---|---|
| `dynasty-superflex-ppr` | mehrere Saisons | langfristiger Asset- und Expertenkonsens |
| `redraft-ppr-superflex` | aktuelle Saison | Lineup-, Produktions- und Win-now-Kontext |

Beide Rankings besitzen dasselbe normalisierte CSV-Schema und dieselben Konsensfelder. Redraft ist weder Dynasty-Trade-Value noch eine Projektion; Dynasty ist kein aktuelles Start/Sit-Ranking.

## Ablagestruktur

```text
expert-consensus/fantasypros/
  README.md
  analysis-metadata.json
  dynasty-superflex-ppr/
    latest.json
    snapshots/YYYY-MM-DD/
      ranking.csv
      raw-ecr-data.json
      metadata.json
  redraft-ppr-superflex/
    latest.json
    snapshots/YYYY-MM-DD/
      ranking.csv
      raw-ecr-data.json
      metadata.json
```

## Direkter Abruf

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py --skip-unchanged
python fantasy-management/_ai/scripts/fetch_fantasypros_redraft_ppr_superflex.py --skip-unchanged
```

Die offiziellen öffentlichen Seiten werden direkt aus dem eingebetteten `ecrData`-Payload gelesen. Es gibt keinen Mirror-Fallback. Netzwerk-, Source-Identity-, Schema-, Format- und Plausibilitätsfehler blockieren die Veröffentlichung eines neuen `latest.json`-Stands.

Der Workflow `Update FantasyPros Rankings` testet und aktualisiert beide Rankings täglich im selben Job. Schlägt einer der Abrufe fehl, wird kein einseitiger Vergleich committed.

## Snapshot-Dateien

- `ranking.csv`: kompakte normalisierte Analysequelle.
- `raw-ecr-data.json`: vollständiger geparster `ecrData`-Payload des Snapshots.
- `metadata.json`: Format, Provenienz, Raw-Schema, Feldabdeckung, Diagnostik und Hashes.
- `latest.json`: Zeiger auf den neuesten erfolgreichen Snapshot.

Normalisierte CSV-Spalten:

```text
name,Rank,position,team,position_rank,tier,rank_min,rank_max,rank_ave,rank_std,source_player_id
```

Der gemeinsame Auswertungsvertrag liegt unter:

```text
fantasy-management/sources/external-rankings/expert-consensus/fantasypros/analysis-metadata.json
```

## Konsensfelder

- `rank_ecr` beziehungsweise `Rank` ist die finale veröffentlichte FantasyPros-Reihenfolge.
- `tier` ist die von FantasyPros gelieferte Wertgruppe.
- `rank_min` und `rank_max` sind beste und schlechteste gelieferte Expertenplatzierung.
- `rank_ave` ist der gelieferte Durchschnittsrang.
- `rank_std` ist die Streuung der gelieferten Expertenrangwerte, keine Erfolgswahrscheinlichkeit.

`rank_ecr` kann außerhalb von `rank_min` bis `rank_max` liegen. Diese Fälle bleiben unverändert erhalten und werden diagnostiziert. Die genaue FantasyPros-Aggregationsformel und die tatsächliche Expertenabdeckung pro Spieler sind im Payload nicht dokumentiert; Erklärungen über ungerankte Spieler, Gewichtung oder Cache-Ausrichtung bleiben daher unbestätigt.

## Vergleich und Nutzung

- Dynasty und Redraft primär über `source_player_id` verbinden; Fallback ist normalisierter Name plus Position.
- Möglichst Snapshots desselben Tages verwenden.
- Listenlängenabhängige Perzentile statt roher Rangdifferenzen bilden.
- FantasyPros ECR ist Expertenkonsens, kein ADP, keine Projektion und keine ligaindividuelle Wahrheit.
- Die Anwendung auf Mighty Giants muss zusätzlich Ligaformat, Replacement Level, zwei feste QB- und TE-Plätze, Roster, Salary/Cap, Ownership, Verletzungen, Rollenänderungen und weitere Marktquellen berücksichtigen.
