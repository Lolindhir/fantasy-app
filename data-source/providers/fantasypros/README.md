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
data-source/market/expert-consensus/fantasypros/<ranking-id>/
  latest.json
  snapshots/YYYY-MM-DD/{ranking.csv,metadata.json}

data-source/providers/fantasypros/
  README.md
  analysis-metadata.json
  <ranking-id>/raw-latest.json

data-source/market/_status/fantasypros.json   (Refresh-Heartbeat)
```

`<ranking-id>` ist `dynasty-superflex-ppr` oder `redraft-ppr-superflex`. Ältere Snapshots (bis Schema 6) enthalten zusätzlich `raw-ecr-data.json` und bleiben unverändert; seit Schema 7 liegt der Roh-Payload nur noch als `raw-latest.json` unter `providers/` (Historie über Git).

## Direkter Abruf

```bash
python -m tools.external_source.fantasypros --skip-unchanged
python -m tools.external_source.fantasypros_redraft --skip-unchanged
```

Die offiziellen öffentlichen Seiten werden direkt aus dem eingebetteten `ecrData`-Payload gelesen. Es gibt keinen Mirror-Fallback. Netzwerk-, Source-Identity-, Schema-, Format- und Plausibilitätsfehler blockieren die Veröffentlichung eines neuen `latest.json`-Stands.

Der Workflow `FM • Ranking • FantasyPros ECR` testet und aktualisiert beide Rankings täglich im selben Job. Schlägt einer der Abrufe fehl, wird kein einseitiger Vergleich committed.

## Snapshot-Dateien

- `ranking.csv`: kompakte normalisierte Analysequelle.
- `raw-latest.json` (unter `data-source/providers/fantasypros/<ranking-id>/`): vollständiger geparster `ecrData`-Payload des neuesten Snapshots.
- `metadata.json`: Format, Provenienz, Raw-Schema, Feldabdeckung, Diagnostik und Hashes.
- `latest.json`: Zeiger auf den neuesten erfolgreichen Snapshot.

Normalisierte CSV-Spalten:

```text
name,Rank,position,team,position_rank,tier,rank_min,rank_max,rank_ave,rank_std,source_player_id
```

Der gemeinsame Auswertungsvertrag liegt unter:

```text
data-source/providers/fantasypros/analysis-metadata.json
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
- Eine ligaspezifische Anwendung (Consumer, nicht die Source-Schicht) muss zusätzlich Ligaformat, Replacement Level, Lineup-Slots, Roster, Salary/Cap, Ownership, Verletzungen, Rollenänderungen und weitere Marktquellen berücksichtigen.
