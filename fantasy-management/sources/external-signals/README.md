# External Signals

Dieser Bereich speichert externe, zeitabhängige Signale, die keine geordneten Spieler- oder Assetbewertungen sind.

## Abgrenzung zu externen Rankings

`external-rankings/` enthält Expertenkonsens, Marktwerte und ADP. Ein Signal gehört stattdessen hierher, wenn es eine Aktivität, ein Ereignis, Aufmerksamkeit oder einen anderen beobachteten Zustand beschreibt, ohne selbst Spielerqualität oder Assetwert zu bewerten.

Beispiele:

- Plattformweite Add-/Drop-Aktivität
- Verletzungs- oder Verfügbarkeitsereignisse
- Rollen- und Usage-Ereignisse
- andere zeitabhängige Trigger, die erst durch spätere Analyse entscheidungsrelevant werden

## Kanonische Hierarchie

```text
external-signals/
└── <signal_kind>/
    └── <provider>/
```

Die Ebenen bedeuten:

1. `signal_kind`: Welche beobachtete Aktivität oder welches Ereignis wird beschrieben?
2. `provider`: Wer veröffentlicht das Signal?

## Quellen- und Interpretationsregel

Der Quellensnapshot bleibt global und providergetreu. Ligarelevanz entsteht erst in einer getrennten Materialisierungs- oder Analyseschicht durch den Join mit aktuellen Repository-Daten.

Insbesondere dürfen globale externe Signale nicht bereits beim Abruf mit folgenden Aussagen vermischt werden:

- Mighty-Giants-Zugehörigkeit
- gegnerische Ownership
- Fantasy-Free-Agent-Status
- Hold-, Shop-, Add-, Drop- oder Cut-Empfehlungen

Fantasy-Free-Agent-Status wird weiterhin ausschließlich aus allen `Roster`-, `Reserve`- und `Taxi`-Listen in `public/data/League.json` abgeleitet.

## Speicherung

Source-spezifische Dokumentation legt fest:

- Abrufkonfiguration und Freshness
- Raw- und Normalized-Retention
- Schema-Version
- Join-Schlüssel
- Fehlverhalten
- Attribution
- Baseline- und Delta-Semantik

Externe Signale sind datierter Quellenkontext und keine dauerhafte Spielerwahrheit.
