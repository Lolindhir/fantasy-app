# External Rankings

Dieser Bereich speichert externe geordnete Spieler- und Assetbewertungen. ADP, Expertenkonsens und Marktwerte sind dabei unterschiedliche Ranking-Signale innerhalb desselben Oberbegriffs.

## Kanonische Hierarchie

```text
external-rankings/
├── expert-consensus/
│   └── <provider>/
│       └── <format>/
├── market-value/
│   └── <provider>/
│       └── <format>/
└── adp/
    └── <provider>/
        └── <format>/
```

Die Ebenen bedeuten:

1. `ranking_kind`: Wie entsteht die Reihenfolge?
2. `provider`: Wer veröffentlicht das Signal?
3. `format`: Für welchen Horizont, Scoring- und Ligakontext gilt es?

## Aktive Ranking-Arten

- `expert-consensus`: Reihenfolge aus Experteneinschätzungen; aktuell FantasyPros.
- `market-value`: Reihenfolge oder Werte aus beobachtetem Trade-/Marktverhalten; aktuell FantasyCalc. KeepTradeCut ist nur manuelle Referenz.
- `adp`: Reihenfolge aus beobachteten Draftpositionen; aktuell Fantasy Football Calculator mit getrennten PPR-8-Team- und 2QB-10-Team-Feeds sowie FantasyPros mit getrennten PPR-Overall- und Half-PPR-Superflex-Composites.

## Gemeinsamer Kern

Jedes normalisierte Ranking soll mindestens Ranking-Art, Anbieter, Ranking-ID, Format, Abrufzeit, eindeutigen normalisierten Rang und stabile Quellidentität dokumentieren. Quellenspezifische Felder wie Expertenstreuung, Marktwert, Trend oder ADP-Sample bleiben zusätzlich erhalten.

Ranking-Arten dürfen nicht so behandelt werden, als würden sie dasselbe messen. Quellenübergreifende Vergleiche verwenden listenlängenabhängige Perzentile statt roher Rang- oder Wertdifferenzen.

Mehrere Formate desselben Anbieters dürfen ebenfalls nicht ohne Prüfung gemittelt werden. Bei Fantasy Football Calculator unterscheiden sich der PPR- und der 2-QB-Feed gleichzeitig in Teamzahl, Scoringkontext und Quarterback-Anforderung. Bei FantasyPros unterscheiden sich PPR Overall und Half-PPR Superflex in Scoring, Lineup-Anforderung und aktueller Plattformzusammensetzung.

Aggregierte Rankings müssen neben dem veröffentlichten Konsenswert die zugrunde liegende Quellenkomposition, sichtbare Aktualitätsstände, fehlende Einzelwerte und mögliche Überschneidungen mit anderen gespeicherten Quellen erhalten.

## Speicherregel

Die Source-spezifische README bestimmt, ob Raw-Daten historisiert oder nur als letzter Stand gespeichert werden. Normalisierte Snapshots und Metadaten bleiben datierter Quellenkontext und keine dauerhafte Wahrheit.
