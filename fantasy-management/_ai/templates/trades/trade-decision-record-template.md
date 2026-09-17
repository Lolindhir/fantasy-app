# Trade Decision Record – Vorlage

> Diese Markdown-Datei ist die lesbare Begleitfassung zu `decision-record.json`. Gemeinsame Fakten, Thesis-IDs und Skalenwerte müssen mit dem JSON übereinstimmen. Bei einem versiegelten Record werden spätere Outcomes ausschließlich in separaten Reviews dokumentiert.

## Metadaten

- Record-ID:
- Trade-ID:
- Trade-Datum:
- Erstellungsdatum:
- Record-Ursprung: `contemporaneous` / `reconstructed`
- Status: `draft` / `sealed`

### Nur bei Rekonstruktion

- Rekonstruktionsdatum:
- Rekonstruktions-Confidence (1–5):
- Outcome-Firewall bestätigt: ja
- Grenzen / Unsicherheiten der Rekonstruktion:

## 1. Exakte Transaktion

### Mighty Giants erhalten

- ...

### Mighty Giants geben ab

- ...

### Counterparty

- Team / Owner:

### Kanonische Referenzen

- Transaction-/Draft-Referenz:
- Weitere Datenreferenzen:

## 2. Evidenzbasis für den Ex-ante-Zustand

Für jede wesentliche Quelle:

- Evidence-ID:
- Typ: `canonical_transaction` / `contemporary_chat` / `stored_negotiation_history` / `contemporary_analysis` / `market_snapshot` / `repository_snapshot` / `user_recollection` / `later_inference`
- Quelle / Referenz:
- Stand:
- Ex ante relevant: ja / nein
- Evidenz-Confidence (1–5):
- Aussage:

## 3. Entscheidungskontext

- Primäres Ziel:
- Saisonphase:
- Roster-Kontext:
- Cap-/Salary-Kontext:
- Team-Window:
- Markt-Kontext:
- Warum gerade jetzt:
- Relevante Constraints:

## 4. Decision Thesis

| Thesis-ID | Erwartung | Confidence 1–5 | Horizont | Was würde die Thesis schwächen/widerlegen? |
|---|---|---:|---|---|
| T1 |  |  |  |  |

Bei komplexen Trades bevorzugt ca. drei bis sieben wirklich materielle Thesen statt vieler Kleinstannahmen.

## 5. Alternativen

### Erwogene Alternativen

- Alternative:
- Warum nicht gewählt:

### Bewusst geschützte Assets

- Asset:
- Warum geschützt:

## 6. Price Ceiling / Walk-away

- War ein Ceiling bekannt?:
- Beschreibung:
- Ausgeführter Deal relativ zum Ceiling: `below` / `at` / `above` / `unknown`
- Falls oberhalb: Warum wurde bewusst darüber gegangen?:

## 7. Bekannte Risiken

| Risk-ID | Risiko | Wahrscheinlichkeit | Auswirkung |
|---|---|---|---|
| R1 |  |  |  |

## 8. Decision State at Execution

### Decision confidence

- Wert 1–5:
- Begründung:
- Primärer Confidence-Treiber:
- Primäre Quelle der Zweifel:

### Outcome uncertainty

- Wert 1–5:
- Warum ist die erwartete Ergebnisspanne eng oder breit?:

### Gut feeling

- `very_negative` / `negative` / `mixed` / `positive` / `very_positive`
- Kurze intuitive Reaktion:

### Decision margin

- `clear` / `moderate` / `close`

### Bekannte persönliche Bias-Risiken

- ...

### Provenienz dieses Zustands

- `direct_contemporaneous` / `reconstructed_contemporary_evidence` / `reconstructed_user_recollection` / `mixed_reconstruction` / `unknown`

## 9. Linked Decisions / Portfolio

- Linked Trade-ID:
- Beziehung: `predecessor` / `successor` / `same_strategy` / `cap_chain` / `position_rebalance` / `pick_chain` / `other`
- Zusammenhang:

## 10. Review-Plan

Nur sinnvolle Trigger aufnehmen; keine automatische Terminierung ableiten.

| Review-Typ | Trigger | Zweck |
|---|---|---|
| early_signal | z. B. nach 4–6 aussagekräftigen Spielen | Rollen-/Usage-Evidenz prüfen |
| season_end | Saisonende | vollständiger Saisonreview |

Bei Pick-Trades stattdessen bzw. zusätzlich `asset_resolution`; `year_2`/`year_3` nur bei echter Mehrjahres-Thesis oder weiter ungelösten Thesen.

## 11. Seal

Vor dem Versiegeln prüfen:

- [ ] Exakte Assets und Picks geprüft.
- [ ] Ex-ante-Evidenz von späteren Outcomes getrennt.
- [ ] Thesen testbar formuliert.
- [ ] Confidence, Outcome Uncertainty und Gut Feeling festgehalten.
- [ ] Risiken, Alternativen, geschützte Assets und Ceiling soweit rekonstruierbar dokumentiert.
- [ ] User hat die dauerhafte Speicherung / Versiegelung bestätigt.

- Sealed at:
- User confirmation:

## 12. Corrections

Nach Seal keine stillen Änderungen. Faktische/Provenienz-Korrekturen hier und in `decision-record.json` mit Correction-ID protokollieren.

- Correction-ID:
- Datum:
- Feld:
- Vorher:
- Korrektur:
- Grund:
- Evidenz:
- Judgment impact: `none` / `requires_review`
