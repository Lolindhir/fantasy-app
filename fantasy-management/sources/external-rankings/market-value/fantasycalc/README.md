# FantasyCalc Market-Value Rankings

Dieser Bereich speichert FantasyCalc-Marktwerte innerhalb der Ranking-Art `market-value`.

## Was die Quelle misst

FantasyCalc leitet Werte aus beobachteten Fantasy-Trades ab. Die Daten sind Markt- und Plausibilitätskontext, kein Expertenkonsens, keine Punkteprojektion und keine ligaeigene Wahrheit.

## Verwendete Formate

- `dynasty-superflex-ppr-8-team`: langfristiger Dynasty-Trade-Markt einschließlich FantasyCalc-Draftpick-Assets
- `redraft-superflex-ppr-8-team`: aktueller saisonaler Redraft-Trade-Markt

Request-Konfiguration:

- `numQbs=2`
- `numTeams=8`
- `ppr=1`
- kein `tep`
- ADP und Roster-Prozent werden angefordert

Die reale Liga hat sechs Teams. Acht Teams sind der nächstgelegene unterstützte Proxy. Zwei feste TE-Startplätze werden nicht modelliert; TEP wird bewusst nicht als Ersatz verwendet.

## Ablagestruktur und Speicherregeln

```text
market-value/fantasycalc/
  README.md
  analysis-metadata.json
  dynasty-superflex-ppr-8-team/
    raw-latest.json
    latest.json
    snapshots/YYYY-MM-DD/
      ranking.csv
      metadata.json
  redraft-superflex-ppr-8-team/
    raw-latest.json
    latest.json
    snapshots/YYYY-MM-DD/
      ranking.csv
      metadata.json
```

Für jedes Format gilt:

- `raw-latest.json` enthält ausschließlich den neuesten vollständigen API-Payload und wird ersetzt.
- Historische Raw-Payloads werden nicht gespeichert.
- `ranking.csv` und `metadata.json` werden nur bei verändertem normalisiertem Ranking historisiert.
- `latest.json` verweist auf den neuesten Ranking-Snapshot und dokumentiert zusätzlich den jüngsten Raw-Abruf.
- Mehrere Änderungen am selben Kalendertag ersetzen den Snapshot dieses Tages.

## Rang-Semantik

FantasyCalc kann denselben `overallRank` für mehrere Assets veröffentlichen.

- `source_overall_rank`: unveränderter FantasyCalc-Rang; Duplikate sind zulässig.
- `Rank`: eindeutiger normalisierter Zeilenrang für stabile Joins und Perzentile.

Bei gleichen Source-Rängen wird nach FantasyCalc-Wert absteigend und anschließend nach `source_asset_id` sortiert. Die Metadaten dokumentieren doppelte Source-Ranggruppen.

## Normalisierte Felder und Joins

Die CSV enthält Rang, Source-Rang, Assettyp, Position, NFL-Team, Wert, Positionsrang, Tier, 30-Tage-Trend, Plattform-IDs, Alter, Erfahrung, optionale ADP, Handelsfrequenz, Rosterquote und weitere FantasyCalc-Differenzfelder.

Join-Reihenfolge für Spieler:

1. `sleeper_id`
2. `source_asset_id`
3. normalisierter Name plus Position

FantasyCalc-Draftpick-IDs sind synthetische Quellenkennungen. Aktuelle Pick-Identität und Besitz kommen ausschließlich aus `League.json` und `Drafts.json`.

## Aktualisierung

```bash
python fantasy-management/_ai/scripts/fetch_fantasycalc_rankings.py --skip-unchanged
```

Der eigene GitHub-Actions-Workflow aktualisiert Dynasty und Redraft täglich im selben Job und veröffentlicht bei einem fehlgeschlagenen Teilabruf kein unvollständiges Ergebnis.

Der maschinenlesbare Auswertungsvertrag liegt unter:

```text
fantasy-management/sources/external-rankings/market-value/fantasycalc/analysis-metadata.json
```

## Analysegrenzen

- Verschiedene Formatabfragen nicht roh miteinander verrechnen.
- FantasyCalc-Werte nicht linear mit FantasyPros-Rängen vergleichen.
- Quellenübergreifend listenlängenabhängige Perzentile verwenden.
- Für reproduzierbare Perzentile `Rank` nutzen; `source_overall_rank` bleibt Auditfeld.
- Sechs-Team-Replacement-Level sowie zwei feste QB- und TE-Plätze separat anwenden.
- FantasyCalc sichtbar als Quelle nennen, wenn Werte nutzerseitig dargestellt werden.
