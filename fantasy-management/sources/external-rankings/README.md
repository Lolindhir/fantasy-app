# External Rankings

Dieser Bereich speichert externe geordnete Spieler- und Assetbewertungen. ADP, Expertenkonsens, Marktwerte und Projections sind unterschiedliche Ranking-Arten innerhalb desselben Oberbegriffs.

## Kanonische Hierarchie

```text
external-rankings/
├── expert-consensus/
│   └── <provider>/
│       └── <format>/
├── market-value/
│   └── <provider>/
│       └── <format>/
├── adp/
│   └── <provider>/
│       └── <format>/
└── projections/
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
- `adp`: Reihenfolge aus beobachteten Draftpositionen; aktuell Fantasy Football Calculator mit getrennten offensiven PPR-8-Team-/2QB-10-Team-Feeds sowie einem separaten Kicker-Ranking aus dem PPR-8-Team-Payload.
- `projections`: Reihenfolge aus erwarteter statistischer oder Fantasy-Produktion; aktuell FFToday mit Preseason-Kicker-Projections.

## Gemeinsamer Kern

Jedes normalisierte Ranking soll mindestens Ranking-Art, Anbieter, Ranking-ID, Format, Abrufzeit, eindeutigen normalisierten Rang und stabile Quellidentität dokumentieren. Quellenspezifische Felder wie Expertenstreuung, Marktwert, Projection-Stats oder ADP-Sample bleiben zusätzlich erhalten.

Ranking-Arten dürfen nicht so behandelt werden, als würden sie dasselbe messen. Quellenübergreifende Vergleiche verwenden listenlängenabhängige Perzentile statt roher Rang- oder Wertdifferenzen.

Positionsspezifische Rankings wie Kicker müssen innerhalb ihrer Position normalisiert werden. Ein Kicker-Rang darf nicht in einen offensiven QB/RB/WR/TE-Cross-Position-Perzentilbestand gemischt werden.

Mehrere Formate desselben Anbieters dürfen ebenfalls nicht ohne Prüfung gemittelt werden. Bei Fantasy Football Calculator unterscheiden sich der PPR- und der 2-QB-Feed gleichzeitig in Teamzahl, Scoringkontext und Quarterback-Anforderung.

Projection-Rankings behalten nach Möglichkeit die zugrunde liegenden statistischen Projections neben dem abgeleiteten oder source-seitigen Fantasy-Points-Rang. Provider-Fantasy-Punkte sind nicht automatisch liga-spezifische Fantasy-Punkte.

Aggregierte Rankings müssen neben dem veröffentlichten Konsenswert die zugrunde liegende Quellenkomposition, sichtbare Aktualitätsstände, fehlende Einzelwerte und mögliche Überschneidungen mit anderen gespeicherten Quellen erhalten.

## Quellen-Audits

Audits für geprüfte, aber nicht aktive Rankingquellen liegen zentral unter:

`fantasy-management/sources/external-rankings/audits/`

Aktive Provider können zusätzlich einen Source-spezifischen Audit im Provider-Verzeichnis behalten, wenn der Produktionsvertrag davon abhängt, etwa bei einer öffentlichen HTML-Quelle ohne dokumentierte API.

Provider-Verzeichnisse unter `expert-consensus/`, `market-value/`, `adp/` und `projections/` sind aktiven oder tatsächlich gespeicherten Quellen vorbehalten.

## Geprüfte, aber nicht aktive Quelle: Dynasty Data Lab

Dynasty Data Lab wurde am 6. August 2026 als mögliche kostenlose Dynasty-Startup-ADP-Quelle geprüft.

Die Quelle ist fachlich wertvoll, weil sie nach eigener Beschreibung ADP aus echten, qualitätsgefilterten Sleeper-Drafts statt aus Expertenrankings oder Mock-Drafts ableitet. Die kostenlose Browseroberfläche bietet außerdem umfangreiche Format- und Zeitraumfilter.

Der Audit fand jedoch keine offiziell dokumentierte vollständige API und keinen dokumentierten vollständigen CSV- oder JSON-Export. Die dynamische Webanwendung und mögliche interne Browser-Endpunkte bilden keinen stabilen Produktionsvertrag. Unter den Vorgaben ohne Zusatzkosten und ohne separate Anbieterfreigabe gilt daher:

- Status: `manual_reference_only`
- keine automatisierten Abrufe
- keine gespeicherten vollständigen Snapshots
- keine Login-Secrets oder Browser-Sessions im Runner
- keine Produktionsabhängigkeit

Der vollständige Audit und die Regeln für eine spätere Neubewertung stehen unter:

`fantasy-management/sources/external-rankings/audits/dynasty-data-lab.md`

## Geprüfte, aber nicht aktive Quelle: FantasyPros ADP

Der anonyme FantasyPros-ADP-Report ist seit der Live-Prüfung vom 4. August 2026 keine vollständige automatisierbare Quelle:

- Die kanonischen ADP-Seiten liefern anonym nur fünf Spielerzeilen.
- Der eingebettete Report-Payload enthält ebenfalls nur diese fünf Zeilen.
- Die Seite zeigt anschließend ausdrücklich eine Account-Sperre mit dem Hinweis, dass ein kostenloses Konto den Report freischaltet.
- Die frühere `export=xls`-Ansicht liefert dem GitHub-Runner keinen vollständigen Export.
- Es gibt im anonymen Browserzustand keine Pagination, keinen versteckten Vollbestand und keinen öffentlichen XHR-Datensatz mit der vollständigen Tabelle.

Ein Top-5-Ausschnitt darf weder gespeichert noch als vollständiges Ranking interpretiert werden. Ohne ausdrücklich freigegebene Login- oder API-Secrets wird daher kein FantasyPros-ADP-Fetcher oder Workflow betrieben. Für den automatisierten ADP-Kontext bleibt Fantasy Football Calculator die aktive Quelle.

Der vollständige Audit steht unter:

`fantasy-management/sources/external-rankings/audits/fantasypros-adp.md`

Eine erneute Integration ist erst zu prüfen, wenn FantasyPros wieder einen vollständigen anonymen Report veröffentlicht oder der Nutzer den Einsatz eines authentifizierten offiziellen Zugangs ausdrücklich freigibt.

## Speicherregel

Die Source-spezifische README bestimmt, ob Raw-Daten historisiert oder nur als letzter Stand gespeichert werden. Normalisierte Snapshots und Metadaten bleiben datierter Quellenkontext und keine dauerhafte Wahrheit.
