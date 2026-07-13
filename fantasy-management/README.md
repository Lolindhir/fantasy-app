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

## Draft-Analysen

Draftanalysen werden als zusammengehöriges Analysepaket gespeichert:

```text
analyses/{analysis-year}/drafts/
  YYYY-MM-DD_{draft-key-slug}_{analysis-kind}.md
  YYYY-MM-DD_{draft-key-slug}_{analysis-kind}.json
```

- Die Markdown-Datei ist die ausführliche, menschenlesbare Auswertung.
- Die JSON-Datei enthält dieselbe Analyse strukturiert für spätere Vergleiche, Manager-Tendenzen und Year-1-/Year-2-/Year-3-Reviews.
- Aktuelle Post-Draft-Analysen frieren den damaligen Team-, Liga- und Markt-Kontext über Quellenpfade, Zeitstände und Blob-SHAs ein.
- Historische Analysen kennzeichnen ausdrücklich, ob der damalige Teamkontext vollständig, teilweise oder nur minimal rekonstruierbar ist.
- Process-, Market-Value- und Team-Fit-Grades bleiben von späteren Outcome-Grades getrennt.
- Eine ursprüngliche Post-Draft-Analyse wird nicht mit Rückschauwissen überschrieben. Spätere Reviews werden als neue Dateien gespeichert und verweisen über `review_of` auf die Ausgangsanalyse.
- Einzelne Managerbeobachtungen bleiben zunächst `candidate` oder `provisional`. Erst wiederholte Belege gehören in `league-context/owner-profiles.md`.

Die technischen Regeln stehen in:

- `_ai/WORKFLOWS.md`
- `_ai/schemas/draft-analysis.schema.json`
- `_ai/templates/draft-analysis/`

Konkrete Mighty-Giants-Entscheidungen werden nicht in der Liga-Gesamtanalyse dupliziert, sondern zusätzlich kompakt unter `decisions/{year}/` dokumentiert.

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
