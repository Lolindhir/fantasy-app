# Article Source Packages

Dieser Ordner enthält persistierte Einzelartikel und vergleichbare textbasierte externe Quellen für Fantasy Management.

Der verbindliche fachliche Vertrag ist:

`fantasy-management/_ai/ARTICLE_SOURCE_MODEL.md`

Vor jeder Artikel-Auswertung oder -Persistierung ist dieser Vertrag anzuwenden.

## Struktur

```text
articles/
  <publisher-or-origin>/
    <year>/
      <date>-<slug>/
        SOURCE.md
        raw.txt
        article.md
        extraction.json
        snapshots/                 # optional bei fortgeschriebenen Living Articles
          <capture-id>/
            raw.txt
            article.md
            extraction.json
```

`user-provided` wird als Origin verwendet, wenn der Nutzer den Inhalt liefert und Publisher/Originalquelle nicht sicher identifiziert sind.

## Dateibedeutung

- `SOURCE.md`: Provenienz, Capture-Status, Materialität, Capture-Historie und bekannte dauerhafte Ableitungen.
- `raw.txt`: exakt bereitgestellter Rohtext des Erst-/Legacy-Captures, sofern zuverlässig verfügbar. Niemals aus Zusammenfassungen rekonstruieren.
- `article.md`: lesefreundlich strukturierte Fassung des Erst-/Legacy-Captures; bei fehlendem Raw sichtbar als Rekonstruktion/Source Digest kennzeichnen.
- `extraction.json`: strukturierte Source Claims und historische Fantasy-Relevanz des Erst-/Legacy-Captures; keine aktuelle Wahrheit.
- `snapshots/<capture-id>/`: unveränderliche spätere Captures desselben Living Article. Ein vollständiger nutzerbereitgestellter neuer Text wird hier als eigenes Raw-Fidelity-Artefakt gesichert, statt einen älteren Snapshot zu überschreiben.

## Living Articles

Wenn derselbe Artikel später erweitert oder aktualisiert erneut bereitgestellt wird, gilt er bei belastbar gleicher Quellenidentität als **Living Article** und nicht als neue unabhängige Quelle.

Für spätere Snapshots gelten die kanonischen Regeln aus `ARTICLE_SOURCE_MODEL.md`:

- ältere Raw-Captures bleiben unverändert;
- `SOURCE.md` dokumentiert die Capture-Historie und den neuesten Snapshot;
- materielle Claims erhalten stabile `claim_id`-Werte;
- Snapshot-Deltas werden als `new`, `repeated`, `changed` oder `retracted` markiert;
- `repeated` erhöht weder Source Count noch Confidence wie eine unabhängige Bestätigung;
- nur neue oder materiell geänderte Claims werden erneut auf Watch-/Baseline-/Board-/Decision-Auswirkungen geprüft.

## Kurzbefehl-Semantik

- `Artikel auswerten` / `nur auswerten`: read-only Analyse und gegebenenfalls Persistenzvorschlag.
- `nur Quelle sichern`: Source Package schreiben, aber keine neue Fantasy-Knowledge/Watch/Decision-Ableitung kanonisieren.
- `Artikel auswerten und persistieren`: Source Package plus die klar ausgewiesenen und freigegebenen Ableitungen persistieren.
- `Freigabe`: bezieht sich auf den unmittelbar zuvor konkret beschriebenen Write-Scope.

## Grundsatz

Quelle, Extraktion und Mighty-Giants-Interpretation bleiben getrennt. Ein gespeicherter Artikel ist ein historischer Evidenz-Snapshot und überschreibt weder `public/data/` noch aktuelle Rollen-, Injury-, Markt- oder Ownership-Fakten.
