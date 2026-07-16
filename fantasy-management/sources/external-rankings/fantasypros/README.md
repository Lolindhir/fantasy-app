# FantasyPros External Rankings

Dieser Ordner enthält datierte, maschinenlesbare Snapshots externer FantasyPros-Rankings für Fantasy-Management-Analysen.

## Ranking-Familie

Aktuell werden zwei öffentliche FantasyPros-PPR-Superflex-ECRs verwendet:

| Ranking-ID | Horizont | Primäre Auswertungsrolle |
|---|---|---|
| `dynasty-superflex-ppr` | mehrere Saisons | langfristiger Asset- und Marktwert |
| `redraft-ppr-superflex` | aktuelle Saison | Lineup-, Produktion- und Win-now-Kontext |

Beide Rankings besitzen dasselbe normalisierte CSV-Schema und dieselben Konsensfelder. Sie messen dennoch unterschiedliche Dinge: Redraft ist weder Dynasty-Trade-Value noch eine Projektion; Dynasty ist kein aktuelles Start/Sit-Ranking.

## Ablagestruktur

```text
fantasypros/
  README.md
  analysis-metadata.json
  dynasty-superflex-ppr/
    latest.json
    snapshots/
      YYYY-MM-DD/
        ranking.csv
        raw-ecr-data.json
        metadata.json
  redraft-ppr-superflex/
    latest.json
    snapshots/
      YYYY-MM-DD/
        ranking.csv
        raw-ecr-data.json
        metadata.json
```

## Direkter Abruf

Die offiziellen FantasyPros-Rankings werden direkt aus dem in den öffentlichen HTML-Seiten eingebetteten `ecrData`-Payload gelesen:

```bash
python fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py
python fantasy-management/_ai/scripts/fetch_fantasypros_redraft_ppr_superflex.py
```

Nützliche Prüfmodi funktionieren für beide Fetcher:

```bash
python <fetcher.py> --dry-run
python <fetcher.py> --from-file path/to/saved-page.html --dry-run
python <fetcher.py> --skip-unchanged
```

Der Redraft-Fetcher verwendet Parser, Konsensvalidierung, CSV-Rendering und gemeinsame Feldsemantik des Dynasty-Fetchers wieder. Er ergänzt nur Redraft-Source-Identity, eigenen Snapshot-Pfad und horizontspezifische Metadaten.

Die Fetcher nutzen keinen Mirror-Fallback. Bei Netzwerk-, Schema-, Format- oder Plausibilitätsfehlern wird kein neuer `latest.json`-Stand veröffentlicht. Erfolgreiche Abrufe dokumentieren Abrufzeit, Zeilenanzahl, Positionsverteilung, Feldabdeckung, fehlende Rangnummern und SHA-256.

Mit `--skip-unchanged` wird kein neuer Snapshot geschrieben, wenn sowohl der vollständige normalisierte Raw-Payload als auch das erwartete normalisierte Snapshot-Schema mit dem zuletzt veröffentlichten Stand übereinstimmen.

## Automatische Aktualisierung

Der GitHub-Actions-Workflow `Update FantasyPros Rankings` läuft täglich um `05:17 UTC` und kann zusätzlich manuell gestartet werden. Er testet beide Fetcher und ruft Dynasty und Redraft anschließend im selben Job nacheinander mit `--skip-unchanged` ab.

Dadurch werden beide Rankings möglichst eng zeitlich ausgerichtet. Schlägt einer der Abrufe fehl, endet der Job vor dem Commit-Schritt, damit kein einseitig aktualisierter Vergleich veröffentlicht wird.

Workflow-Datei:

```text
.github/workflows/update-fantasypros-rankings.yml
```

## Dateien eines Snapshots

- `ranking.csv` ist die kompakte normalisierte Analysequelle. Sie enthält Spielername, Overall-ECR, Position, NFL-Team, Positionsrang, Tier, besten und schlechtesten Expertenrang, durchschnittlichen Expertenrang, Rang-Standardabweichung und – sofern FantasyPros ihn liefert – die FantasyPros-Spieler-ID.
- `raw-ecr-data.json` enthält den vollständigen geparsten `ecrData`-Payload. Die JSON-Formatierung wird normalisiert, aber Felder werden nicht entfernt.
- `metadata.json` dokumentiert Ranking-Kontext, Format, Raw-Schema, Feldabdeckung, Beziehungen zwischen Konsensfeldern, Hashes, Abruf- und Snapshot-Provenienz sowie bekannte Einschränkungen.
- `latest.json` ist nur ein Zeiger auf den zuletzt erfolgreich abgelegten Snapshot und keine eigene Ranking-Quelle.

Normalisierte CSV-Spalten:

```text
name,Rank,position,team,position_rank,tier,rank_min,rank_max,rank_ave,rank_std,source_player_id
```

## Gemeinsamer Auswertungsvertrag

Die maschinenlesbare Anleitung für die gemeinsame Dynasty-/Redraft-Auswertung liegt in:

```text
fantasy-management/sources/external-rankings/fantasypros/analysis-metadata.json
```

Sie gilt für beide Ranking-IDs und dokumentiert:

- die unterschiedliche Rolle beider Rankings,
- den bevorzugten Join über `source_player_id`,
- den vorsichtigen Fallback über normalisierten Namen plus Position,
- die bevorzugte Verwendung von Snapshots desselben Tages,
- die notwendige Normalisierung auf listenlängenabhängige Perzentile,
- die Ableitungen `dynasty_percentile`, `redraft_percentile` und `win_now_gap`,
- die Grenzen der gemeinsamen Interpretation.

Rohe Rangdifferenzen dürfen nicht direkt als Value-Gap interpretiert werden, weil Listenlängen, Spielerpools und Expertenbasis abweichen können.

Interpretation des `win_now_gap`:

- relativ stärkeres Redraft-Perzentil: möglicher Win-now-Produzent oder Veteranen-Discount,
- relativ stärkeres Dynasty-Perzentil: langfristiger Asset-Wert, der noch nicht vollständig durch die aktuelle Saisonerwartung gestützt wird,
- beide stark: langfristiger Kernspieler mit aktueller Produktion,
- beide schwach: niedriger externer Konsens in beiden Horizonten.

Der Gap ist ein Kontextsignal und keine automatische Trade-Empfehlung. Anschließend müssen Ligaformat, Roster, Salary/Cap, Ownership, Verletzungen, Rollenänderungen und weitere Marktquellen berücksichtigt werden.

## Interpretation der Konsensfelder

- `tier` ist die von FantasyPros gelieferte Wertgruppe. Tier-Grenzen sind meist aussagekräftiger als kleine Rangabstände innerhalb desselben Tiers.
- `rank_min` und `rank_max` sind der beste beziehungsweise schlechteste von FantasyPros gelieferte Expertenrang.
- `rank_ave` ist der von FantasyPros gelieferte durchschnittliche Expertenrang.
- `rank_std` misst die Streuung der von FantasyPros gelieferten Expertenrangwerte. Ein kleiner Wert steht für engere, ein großer Wert für stärkere Abweichungen innerhalb dieser Werte.
- Eine große Min-Max-Spanne kann durch einen einzelnen Ausreißer entstehen. `rank_std` ist deshalb das primäre Streuungsmaß; Min-Max bleibt eine ergänzende Extremwertprüfung.
- `rank_ecr` ist die von FantasyPros veröffentlichte finale Konsensreihenfolge. Sie ist nicht garantiert innerhalb von `rank_min` und `rank_max`, weil FantasyPros diese Werte als getrennte Expertenstatistiken liefert und die genaue Beziehung im Payload nicht dokumentiert ist.
- `rank_std` ist keine Wahrscheinlichkeit, kein Verletzungsrisiko und keine direkte Erfolgswahrscheinlichkeit.

Fehlende optionale Konsenswerte bleiben in der CSV leer. Nichtleere Werte werden fail-closed validiert: Tier und Ränge müssen positiv sein, `rank_min` darf `rank_max` nicht übersteigen, `rank_ave` muss innerhalb der vorhandenen Min-Max-Spanne liegen und `rank_std` darf nicht negativ sein. Ein ECR außerhalb der Experten-Spanne bleibt als originaler Quellwert erhalten und wird in den Metadaten diagnostiziert.

### Verhältnis von `rank_ecr` zu den Expertenstatistiken

#### Gesichert beobachtet

- `rank_ecr` ist die finale veröffentlichte Overall-Reihenfolge; `rank_min`, `rank_max`, `rank_ave` und `rank_std` sind getrennte Statistikfelder im selben Quell-Payload.
- `rank_ecr` kann außerhalb von `rank_min` bis `rank_max` liegen. Das ist ein beobachtetes Quellenverhalten und kein Parser- oder CSV-Fehler.
- Im Dynasty-Live-Snapshot vom 15.07.2026 lagen 148 von 541 ECR-Werten außerhalb der jeweiligen Min-Max-Spanne. Die aktuelle Zahl steht je Ranking unter `metadata.json -> snapshot.consensus_relationship_diagnostics`.
- Beispiel aus diesem Dynasty-Snapshot: Geno Smith hatte `rank_ecr = 230`, `rank_min = 135`, `rank_max = 188`, `rank_ave = 155.70` und `rank_std = 15.52`.
- Die exakte FantasyPros-Aggregationsformel und die Zahl der pro Spieler tatsächlich berücksichtigten Experten sind im gespeicherten Payload nicht enthalten.

#### Plausible, aber unbestätigte Erklärung

Eine mögliche Erklärung sind unterschiedlich tiefe Expertenlisten: Einige Experten können einen tief gerankten Spieler aufführen, während andere ihn nicht mehr listen. Die Statistikfelder könnten dann nur vorhandene Rangwerte beschreiben, während die finale ECR-Reihenfolge fehlende Rankings oder weitere Aggregationsregeln berücksichtigt. Ebenfalls denkbar sind Expertengewichtung, Aktualitätsgewichtung oder getrennte Berechnungs- beziehungsweise Cache-Schritte.

Diese Erklärung ist **nicht von FantasyPros bestätigt** und darf nicht als dokumentierte Methodik ausgegeben werden.

#### Operative Auswertung

- `rank_ecr` bleibt die maßgebliche FantasyPros-Gesamtposition des jeweiligen Rankings.
- `rank_std` wird als Streuung der von der Quelle gelieferten Expertenrangwerte gelesen, nicht als Messung vollständiger Expertenabdeckung und nicht als Erfolgswahrscheinlichkeit.
- Eine niedrige `rank_std` bei gleichzeitig großer Differenz zwischen `rank_ecr` und `rank_ave` beweist keinen breiten Konsens aller verfügbaren Experten.
- Ein großer Abstand zwischen `rank_ecr` und `rank_ave` ist ein Hinweis auf eine Aggregations- oder Coverage-Einschränkung. Bei wertrelevanten Entscheidungen sollen aktuelle News, weitere Marktquellen und der Liga-Kontext zusätzlich geprüft werden.

## Nutzungsregeln

- Die Snapshots sind externe Quellenkontexte und keine dauerhafte Wahrheit.
- Für aktuelle Entscheidungen soll der direkte Abruf erneut ausgeführt werden, wenn der Snapshot nicht vom selben Tag stammt oder sich der Markt schnell bewegt.
- Die normalisierte CSV ist die primäre Join- und Analysequelle; die Raw-JSON dient für zusätzliche Felder, Schema-Audits und spätere Neuauswertungen.
- Dynasty ECR bleibt die primäre FantasyPros-Quelle für Asset-/Trade-Kontext.
- Redraft ECR ergänzt ihn um aktuelle Saison- und Win-now-Relevanz, ersetzt ihn aber nicht.
- Beide Superflex-Rankings sind Proxys für die Mighty-Giants-Liga. Bei zwei fest vorgeschriebenen QB- und TE-Startplätzen können zusätzliche ligaindividuelle Knappheitsanpassungen nötig sein.

## Quellenrolle

FantasyPros ECR bildet Expertenkonsens ab. Es ist kein ADP, keine Projektion und kein ligaindividuelles Ranking. Die Anwendung auf Mighty Giants muss immer mit aktuellem Ligaformat, Roster, Salary/Cap, Ownership und weiteren Marktquellen abgeglichen werden.
