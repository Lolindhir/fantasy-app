# Fantasy Management

Dieser Ordner ist der getrennte Fantasy-Management-Arbeitsbereich des Repositories.

Er ist bewusst getrennt von der App-Logik, dem Angular-Frontend, der PowerShell-Datengenerierung und dem zentralen App-AI-Kontext.

## Zweck

Hier liegen Quellen, Regeln, Podcastdaten, Liga-Kontext, abgeleitetes Knowledge und konkrete Analysen/Entscheidungen für NFL Dynasty / Fantasy Football rund um Mighty Giants.

## Für Menschen

Diese README erklärt den Bereich auf menschlich lesbare Weise.

Für Agents und Maschinen ist `fantasy-management/AGENTS.md` maßgeblich.

## Struktur

Aktive Kernbereiche:

- `_ai/` enthält Agent-Regeln, Quellenlogik, Workflows, Templates und Schemas.
- `league-context/` enthält Liga-, Owner-, Format- und Verhandlungskontext.
- `sources/` enthält Rohquellen und strukturierte Quellenpakete.
- `knowledge/` enthält abgeleitetes, liga-relevantes Knowledge, sobald es echte Knowledge-Dateien gibt.
- `analyses/` enthält konkrete Auswertungen und Empfehlungen, sobald Analysen gespeichert werden.
- `decisions/` enthält getroffene Entscheidungen und Entscheidungsverlauf, sobald Entscheidungen gespeichert werden.

Optionale Bereiche wie `knowledge/players/`, `analyses/`, `decisions/`, `sources/relevant-players/`, `sources/external-rankings/` oder `sources/manual-notes/` werden erst angelegt, wenn dort echte Dateien liegen.

Keine leeren Platzhalterordner und keine README-only-Kategorieordner committen.

## Podcast-Struktur

Podcast-Folgen werden als zusammenhängende Quellenpakete gespeichert:

```text
sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
  episode.md
  takes.json
  index.json
```

`episode.md` ist die lesbare Podcast-Zusammenfassung.

`takes.json` enthält strukturierte Podcast-Takes nach Kategorien.

`index.json` enthält nur technische Paket-Metadaten.

## Wichtige Trennung

```text
Podcast source package = was der Podcast gesagt hat
Knowledge = was davon für unsere Liga relevant bleibt
Analysis = was Mighty Giants tun sollte
```

Aktuelle App- und Liga-Daten bleiben unter `public/data/`.

Fantasy-Management-Artefakte sind Arbeits- und Analyseartefakte. Dynamische Einschätzungen müssen bei neuen Analysen aus den aktuellen Repo-Daten und bei Bedarf aktuellen externen Quellen neu abgeleitet werden.
