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
```

`user-provided` wird als Origin verwendet, wenn der Nutzer den Inhalt liefert und Publisher/Originalquelle nicht sicher identifiziert sind.

## Dateibedeutung

- `SOURCE.md`: Provenienz, Capture-Status, Materialität und bekannte dauerhafte Ableitungen.
- `raw.txt`: exakt bereitgestellter Rohtext, sofern zuverlässig verfügbar. Niemals aus Zusammenfassungen rekonstruieren.
- `article.md`: lesefreundlich strukturierte Fassung; bei fehlendem Raw sichtbar als Rekonstruktion/Source Digest kennzeichnen.
- `extraction.json`: strukturierte Source Claims und historische Fantasy-Relevanz; keine aktuelle Wahrheit.

## Kurzbefehl-Semantik

- `Artikel auswerten` / `nur auswerten`: read-only Analyse und gegebenenfalls Persistenzvorschlag.
- `nur Quelle sichern`: Source Package schreiben, aber keine neue Fantasy-Knowledge/Watch/Decision-Ableitung kanonisieren.
- `Artikel auswerten und persistieren`: Source Package plus die klar ausgewiesenen und freigegebenen Ableitungen persistieren.
- `Freigabe`: bezieht sich auf den unmittelbar zuvor konkret beschriebenen Write-Scope.

## Grundsatz

Quelle, Extraktion und Mighty-Giants-Interpretation bleiben getrennt. Ein gespeicherter Artikel ist ein historischer Evidenz-Snapshot und überschreibt weder `public/data/` noch aktuelle Rollen-, Injury-, Markt- oder Ownership-Fakten.
