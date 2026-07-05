# Fantasy Management

Dieser Ordner ist der getrennte Fantasy-Management-Arbeitsbereich des Repositories.

Er ist bewusst getrennt von der App-Logik, dem Angular-Frontend, der PowerShell-Datengenerierung und dem zentralen App-AI-Kontext.

## Zweck

Hier liegen Quellen, Regeln, Podcastdaten, Relevant-Players-Dateien, abgeleitete Boards, Analysen und Entscheidungen für NFL Dynasty / Fantasy Football rund um Mighty Giants.

## Für Menschen

Diese README erklärt den Bereich auf menschlich lesbare Weise.

Für Agents und Maschinen ist `fantasy-management/AGENTS.md` maßgeblich.

## Struktur

- `_ai/` enthält Agent-Regeln, Quellenlogik, Workflows, Templates und Schemas.
- `sources/` enthält Rohquellen und strukturierte Quellen.
- `derived/` enthält abgeleitete Boards, Listen und Source-Zusammenfassungen.
- `analyses/` enthält konkrete Auswertungen und Empfehlungen.
- `decisions/` enthält getroffene Entscheidungen und Entscheidungsverlauf.
- `indexes/` enthält Such- und Mapping-Dateien.
- `archive/` enthält ersetzte oder veraltete Artefakte.

## Wichtige Trennung

Aktuelle App- und Liga-Daten bleiben unter `public/data/`.

Fantasy-Management-Artefakte sind Arbeits- und Analyseartefakte. Dynamische Einschätzungen müssen bei neuen Analysen aus den aktuellen Repo-Daten und bei Bedarf aktuellen externen Quellen neu abgeleitet werden.
