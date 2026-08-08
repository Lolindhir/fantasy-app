# Fantasy Football Calculator ADP Rankings

Dieser Bereich speichert aktuelle Average-Draft-Position-Rankings von Fantasy Football Calculator für die Mighty-Giants-Analyse.

## Was die Quelle misst

Fantasy Football Calculator berechnet ADP aus menschlichen Picks in Mock Drafts. Computer-Picks werden vor der Berechnung entfernt. Die Quelle beschreibt deshalb beobachtete Draftkosten und deren Streuung – keinen Expertenkonsens, keinen Trade-Marktwert und keine Punkteprojektion.

## Verwendete Formate

| Ranking-ID | API-Format | Teamzahl | Scope | Primäre Rolle |
|---|---:|---:|---|---|
| `redraft-ppr-8-team` | `ppr` | 8 | QB/RB/WR/TE | kleiner Liga- und Full-PPR-Draftmarkt |
| `redraft-ppr-8-team-kicker` | `ppr` | 8 | K | Kicker-Draftmarkt |
| `redraft-2qb-10-team` | `2qb` | 10 | QB/RB/WR/TE | 2-QB-Draftmarkt und QB-Knappheit |

Die reale Liga hat sechs Teams, Full PPR, zwei feste QB-, zwei feste TE- und einen festen Kicker-Startplatz. Fantasy Football Calculator bietet kein einzelnes öffentliches ADP-Format, das diese Eigenschaften kombiniert.

Die offensiven PPR- und 2-QB-Feeds werden deshalb **nicht gemittelt**:

- `redraft-ppr-8-team` ist der nächstgelegene unterstützte Proxy für kleine Liga und Full PPR, bildet aber normale 1-QB-Drafts ab.
- `redraft-2qb-10-team` bildet die QB-Knappheit besser ab, verwendet aber zehn Teams und ist kein dokumentierter kombinierter PPR-Feed.
- Zwei feste TE-Startplätze werden von keinem der beiden Feeds modelliert und müssen erst in der ligaindividuellen Analyse berücksichtigt werden.

Das Kicker-Ranking wird **ohne zusätzlichen FFC-Request** aus demselben offiziellen `ppr`, 8-Team, `position=all`-Payload materialisiert, der bereits für `redraft-ppr-8-team` geladen wird. FFC kennzeichnet Kicker dort als `PK`; die normalisierte Kicker-Liste verwendet `K` passend zum internen Player-Modell.

## Ablagestruktur

```text
fantasy-football-calculator/
├── README.md
├── analysis-metadata.json
├── redraft-ppr-8-team/
│   ├── raw-latest.json
│   ├── latest.json
│   └── snapshots/YYYY-MM-DD/{ranking.csv,metadata.json}
├── redraft-ppr-8-team-kicker/
│   ├── raw-latest.json
│   ├── latest.json
│   └── snapshots/YYYY-MM-DD/{ranking.csv,metadata.json}
└── redraft-2qb-10-team/
    ├── raw-latest.json
    ├── latest.json
    └── snapshots/YYYY-MM-DD/{ranking.csv,metadata.json}
```

## Speicherregeln

Für jedes Ranking gilt:

- `raw-latest.json` enthält ausschließlich die neueste vollständige offizielle API-Antwort und wird nach jedem erfolgreichen Abruf ersetzt.
- Historische Raw-Payloads werden nicht gespeichert.
- `latest.json` verweist auf den neuesten normalisierten Ranking-Snapshot und dokumentiert zusätzlich den neuesten Raw-Abruf.
- Historisiert werden nur `ranking.csv` und `metadata.json`.
- Wenn sich die normalisierte Rankingliste nicht verändert, wird kein neuer historischer Snapshot angelegt; `raw-latest.json` und die Raw-Freshness in `latest.json` werden trotzdem aktualisiert.
- Mehrere Änderungen am selben Kalendertag ersetzen den Snapshot dieses Tages.
- Das Kicker-Verzeichnis behält denselben vollständigen PPR-Raw-Payload für direkte Provenance, obwohl der Netzwerkabruf nur einmal erfolgt.

## Normalisierte Rankingliste

`ranking.csv` enthält:

```text
name,Rank,source_rank,position,team,source_player_id,adp,adp_formatted,times_drafted,high,low,stdev,bye,source_format,source_team_count,actual_league_team_count,sample_total_drafts,sample_start_date,sample_end_date
```

Rangsemantik:

- `source_rank` ist die ursprüngliche Position im vollständigen Source-Array.
- `Rank` ist ein eindeutiger normalisierter Rang im jeweiligen Ranking-Scope.
- Offense: QB/RB/WR/TE gemeinsam nach ADP.
- Kicker: ausschließlich Kicker nach ADP.
- Sortierung: `adp` aufsteigend, danach `times_drafted` absteigend und `source_player_id`.

Die vollständige Raw-Antwort kann zusätzlich DEF enthalten. DEF bleibt verlustfrei in `raw-latest.json`, wird aber nicht als aktives Ranking materialisiert. Kicker werden nicht mehr als bloß ausgeschlossene Raw-Einträge behandelt, sondern separat gerankt.

## Sample und Unsicherheit

Die API liefert pro Spieler unter anderem:

- `adp`: durchschnittlicher Overall-Pick
- `times_drafted`: Zahl der beobachteten menschlichen Picks
- `high` und `low`: frühester und spätester beobachteter Pick
- `stdev`: Streuung der Draftposition

Zusätzlich werden aus `meta` gespeichert:

- `total_drafts`
- `start_date` und `end_date`
- `rounds`
- Format und Teamzahl

Die Metadaten klassifizieren die Stichprobe als `high_sample`, `medium_sample`, `low_sample` oder `insufficient_sample`. Ein kleiner Sample bleibt sichtbar und wird nicht als hohe Sicherheit interpretiert. Ein Datensatz mit einem mehr als 45 Tage alten Sample-Ende wird standardmäßig fail-closed abgelehnt.

Beim Kicker-Ranking bleibt `times_drafted` besonders wichtig: eine sichtbare ADP bei sehr wenigen Kicker-Picks ist ein schwächeres Marktsignal als eine ähnlich platzierte ADP mit großer Stichprobe.

## Join-Regeln

Bevorzugte Spielerzuordnung:

1. dauerhaft bestätigtes Mapping von `source_player_id`
2. normalisierter Name plus Position
3. NFL-Team als zusätzliche Plausibilitätsprüfung

Die FFC-Spieler-ID ist eine Quellenkennung und keine Sleeper-ID.

## Direkter Abruf

```bash
python fantasy-management/_ai/scripts/fetch_fantasy_football_calculator_adp.py --skip-unchanged
```

Der Befehl materialisiert die beiden bisherigen offensiven Rankings und das Kicker-Ranking. Das Kicker-Ranking verwendet dabei den bereits geladenen 8-Team-PPR-Payload und erzeugt keinen dritten API-Request.

Prüfmodi:

```bash
python fantasy-management/_ai/scripts/fetch_fantasy_football_calculator_adp.py --dry-run
python fantasy-management/_ai/scripts/fetch_fantasy_football_calculator_adp.py \
  --input ppr-8-team=/path/ppr.json \
  --input 2qb-10-team=/path/2qb.json \
  --dry-run
```

Der Fetcher lädt und validiert beide Source-Formate vollständig, bevor Dateien geschrieben werden. Netzwerk-, JSON-, Source-Identity-, Teamzahl-, Saison-, Sample-Freshness-, ID-, Positions- oder Plausibilitätsfehler beenden den Lauf ohne Veröffentlichung eines unvollständigen Vergleichs.

## Automatische Aktualisierung

Der bestehende GitHub-Actions-Workflow `Update Fantasy Football Calculator ADP` läuft täglich und kann manuell gestartet werden. Weil der Kicker-Materializer im bestehenden Fetcher hängt und der Workflow den vollständigen Provider-Bereich committed, ist kein zusätzlicher FFC-Workflow und kein zusätzlicher Netzwerkabruf erforderlich.

## Quellenübergreifende Auswertung

ADP ist ein Ranking, misst aber etwas anderes als die vorhandenen Quellen:

- FantasyPros: Expertenkonsens
- FantasyCalc: beobachteter Trade-Marktwert
- Fantasy Football Calculator: beobachtete Mock-Draftkosten

Vergleiche verwenden listenlängenabhängige Perzentile, niemals rohe Rang- oder Wertdifferenzen. Das Kicker-Ranking wird nur gegen andere Kicker-Rankings normalisiert und nicht in offensive Cross-Position-Perzentile gemischt.

## Attribution und Nutzung

Fantasy Football Calculator erlaubt die Nutzung der ADP-REST-API für persönliche und kommerzielle Zwecke, bittet um Attribution und weist darauf hin, dass die Daten nur einmal täglich aktualisiert werden. Bei nutzerseitiger Darstellung der Daten soll Fantasy Football Calculator sichtbar als Quelle genannt werden.
