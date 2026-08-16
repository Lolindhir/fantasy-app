# Sources

Source material for Fantasy Management.

Aktive Quelltypen sind unter anderem:

- Podcast-Source-Packages
- Article-Source-Packages
- externe Rankings
- externe Signale
- Relevant-Players-Dateien
- manuelle Notizen

Externe Rankings werden nach ihrer Messart organisiert:

```text
external-rankings/<ranking_kind>/<provider>/<format>/
```

Einzelne Artikel, News-Analysen sowie vom Nutzer bereitgestellte Camp-/Preseason-Übersichten gehören unter:

```text
articles/<publisher-or-origin>/<year>/<date>-<slug>/
```

Für jede Artikel-Auswertung oder -Persistierung sind `articles/README.md` und `../_ai/ARTICLE_SOURCE_MODEL.md` verbindlich. Sie definieren Raw-Fidelity, Provenienz, Lesefassung, strukturierte Extraktion, Materialitätsschwelle und die Write-Semantik für Befehle wie `nur auswerten`, `nur Quelle sichern` und `auswerten und persistieren`.

Die kanonischen Ranking-Arten und Speicherregeln stehen in `external-rankings/README.md`.

Ordner werden nur angelegt, wenn sie echte Inhalte erhalten. Quellen liefern Kontext und überschreiben niemals den aktuellen Ligastand unter `public/data/`.
