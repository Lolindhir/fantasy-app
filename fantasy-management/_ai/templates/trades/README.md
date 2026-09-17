# Trade Decision Record Templates

Diese Vorlagen gehören zum Contract in:

`fantasy-management/_ai/TRADE_DECISION_RECORDS.md`

## Ziel

Ein Trade wird in zwei strikt getrennten Phasen dokumentiert:

1. `decision-record.*` friert den Ex-ante-Entscheidungszustand ein.
2. spätere `reviews/*` ergänzen neue Evidenz und bewerten Process und Outcome getrennt.

Die Templates sind für Spieler-Trades, Pick-only-Trades, gemischte Trades sowie Draft-Day-Trade-ups/-downs gedacht.

## Zielstruktur

```text
fantasy-management/analyses/<year>/trades/<yyyy-mm-dd-short-slug>/
  decision-record.json
  decision-record.md
  reviews/
    <yyyy-mm-dd>-<review-kind>.json
    <yyyy-mm-dd>-<review-kind>.md
```

Portfolio-Reviews mehrerer verknüpfter Trades:

```text
fantasy-management/analyses/<year>/trades/portfolio-reviews/
  <yyyy-mm-dd>-<short-slug>.json
  <yyyy-mm-dd>-<short-slug>.md
```

## Ownership

- `decision-record.json` ist die kanonische strukturierte Fassung.
- `decision-record.md` ist die lesbare narrative Begleitfassung.
- Review-JSON ist die kanonische strukturierte Review-Fassung.
- Review-Markdown erklärt den Review lesbar.
- Gemeinsame Fakten, IDs und Klassifikationen dürfen sich nicht widersprechen.

Schemas:

- `fantasy-management/_ai/schemas/trade-decision-record.schema.json`
- `fantasy-management/_ai/schemas/trade-decision-review.schema.json`

## Vorlagen

- `trade-decision-record-template.md`
- `trade-decision-review-template.md`

Die JSON-Struktur wird absichtlich nicht als Dummy-Datei dupliziert; das jeweilige JSON muss direkt gegen das kanonische Schema gebaut und validiert werden.

## Decision Log

Wenn eine tatsächliche Trade-Entscheidung zusätzlich als kurze dauerhafte Nutzerentscheidung geloggt werden soll, kann analog zum Draft-Decision-Log bei Bedarf erstellt werden:

`fantasy-management/decisions/<year>/trade-decisions.md`

Empfohlenes Kurzformat:

```md
## YYYY-MM-DD – Short title

- Type: trade
- Trade ID:
- Decision:
- Primary reason:
- Related decision record:
- Follow-up:
```

Der Decision Log ersetzt niemals den vollständigen Decision Record.

## Rekonstruktion

Historische Records müssen `record_origin: reconstructed` verwenden und die Rekonstruktions-Confidence sowie die Outcome-Firewall ausweisen. Die komplette historische Backfill-Arbeit ist ein eigener Workstream; diese Vorlagen allein autorisieren keine Rekonstruktion oder Speicherung alter Trades.
