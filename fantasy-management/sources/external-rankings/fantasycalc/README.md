# FantasyCalc Rankings

Dieser Bereich speichert aktuelle FantasyCalc-Marktwerte für die Ligaanalyse der Mighty Giants.

## Was die Quelle misst

FantasyCalc leitet Werte aus beobachteten Fantasy-Trades ab. Die Daten sind daher Markt- und Plausibilitätskontext, kein Expertenkonsens, keine Punkteprojektion und keine ligaeigene Wahrheit.

## Verwendete Formate

- `dynasty-superflex-ppr-8-team`: langfristiger Dynasty-Trade-Markt, einschließlich FantasyCalc-Draftpick-Assets
- `redraft-superflex-ppr-8-team`: aktueller saisonaler Redraft-Trade-Markt

Request-Konfiguration:

- `numQbs=2`
- `numTeams=8`
- `ppr=1`
- kein `tep`
- ADP und Roster-Prozent werden angefordert

Die reale Liga hat sechs Teams. FantasyCalc unterstützt in seiner öffentlichen Formatlogik als kleinste Teamanzahl acht Teams; deshalb ist `numTeams=8` der nächstgelegene Proxy. Diese Abweichung muss bei jeder Analyse berücksichtigt werden.

Zwei feste TE-Startplätze werden von FantasyCalc nicht modelliert. `TEP` wird bewusst nicht gesetzt, weil Tight-End-Premium-Scoring nicht dasselbe ist wie zwei feste TE-Slots.

## Speicherregeln

Für jedes Format gilt:

- `raw-latest.json` enthält ausschließlich den neuesten vollständigen API-Payload und wird bei jedem erfolgreichen Abruf ersetzt.
- `latest.json` verweist auf den neuesten normalisierten Ranking-Snapshot und dokumentiert zusätzlich den jüngsten Raw-Abruf.
- `snapshots/YYYY-MM-DD/ranking.csv` archiviert unsere normalisierte Rangliste.
- `snapshots/YYYY-MM-DD/metadata.json` archiviert Provenienz, Requestparameter, Hashes, Feldabdeckung und Interpretationsgrenzen.
- Historische Raw-Payloads werden nicht gespeichert.
- Bei unverändertem normalisiertem Ranking wird kein neuer historischer Snapshot angelegt; `raw-latest.json` und dessen Freshness-Metadaten werden dennoch aktualisiert.

Mehrere Änderungen am selben Kalendertag ersetzen den Snapshot dieses Tages. Damit bleibt die Historie täglich statt abrufweise granular.

## Rang-Semantik

FantasyCalc kann denselben `overallRank` für mehrere Assets veröffentlichen. Das Feld ist deshalb keine eindeutige ID und wird nicht als Unique Constraint validiert.

Die CSV trennt zwei Felder:

- `source_overall_rank`: der unveränderte FantasyCalc-`overallRank`; Duplikate sind zulässig.
- `Rank`: unser eindeutiger normalisierter Zeilenrang für stabile Joins und listenlängenabhängige Perzentile.

Bei gleichen Source-Rängen wird `Rank` deterministisch nach FantasyCalc-Wert absteigend und anschließend nach `source_asset_id` vergeben. Die Metadaten dokumentieren Anzahl und Beispiele aller doppelten Source-Ranggruppen.

## Normalisierte Felder

Die CSV enthält unter anderem:

- normalisierten Rang, FantasyCalc-Source-Rang, Assettyp, Position, NFL-Team und FantasyCalc-Wert
- Positionsrang, Tier und 30-Tage-Trend
- FantasyCalc-, Sleeper-, MFL- und ESPN-IDs
- Alter, Erfahrung, optionale ADP, Handelsfrequenz und Rosterquote
- FantasyCalc-Redraft-, Combined- und Dynasty-/Redraft-Differenzfelder

Optionale oder unklar dokumentierte Felder werden verlustfrei im aktuellen Raw-Payload behalten, aber nicht automatisch als Prognose oder Sicherheit interpretiert.

## Join-Regeln

Für Spieler:

1. `sleeper_id`
2. `source_asset_id`
3. normalisierter Name plus Position

FantasyCalc-Draftpick-IDs sind synthetische Quellenkennungen. Aktuelle Pick-Identität und Besitz werden weiterhin ausschließlich aus `League.json` und `Drafts.json` bestimmt.

## Analysegrenzen

- Werte verschiedener Formatabfragen dürfen nicht roh miteinander verrechnet werden.
- FantasyCalc-Werte sind nicht linear mit FantasyPros-Rängen vergleichbar.
- Quellenübergreifende Vergleiche sollen listenlängenabhängige Perzentile verwenden.
- Für reproduzierbare Perzentile wird `Rank` verwendet; `source_overall_rank` bleibt Audit- und Quellenfeld.
- Die hohe Replacement-Qualität einer 6-Team-Liga und die Knappheit durch zwei feste QB- und TE-Plätze müssen separat angewendet werden.
- FantasyCalc ergänzt aktuelle Liga- und Spielerdaten; es überschreibt sie nicht.

## Aktualisierung

Direkter Abruf:

```bash
python fantasy-management/_ai/scripts/fetch_fantasycalc_rankings.py --skip-unchanged
```

Ein eigener GitHub-Actions-Workflow aktualisiert Dynasty und Redraft täglich im selben Job. Schlägt eine Formatabfrage fehl, wird kein unvollständiges Ergebnis committed.

## Attribution und Nutzung

Bei nutzerseitiger Darstellung von FantasyCalc-Daten muss FantasyCalc als Quelle sichtbar genannt und verlinkt werden. Der Abruf erfolgt bewusst nur einmal täglich und die vollständige Raw-Historie wird nicht reproduziert.
