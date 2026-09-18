# Trade Decision Review – Vorlage

> Diese Markdown-Datei ist die lesbare Begleitfassung zum jeweiligen Review-JSON. Gemeinsame Fakten, Record-/Thesis-IDs, Klassifikationen und Skalenwerte müssen mit dem JSON übereinstimmen. Der versiegelte Decision Record bleibt unverändert; neue Evidenz und spätere Bewertungen gehören ausschließlich in diesen Review.

## Metadaten

- Review-ID:
- Review-Datum:
- Review-Typ: `early_signal` / `season_end` / `year_1` / `year_2` / `year_3` / `asset_resolution` / `ad_hoc` / `portfolio_review`
- Review-Scope: `single_trade` / `portfolio`

### Referenzierte Decision Records

| Trade-ID | Decision-Record-Referenz |
|---|---|
|  |  |

Bei `portfolio_review` müssen mindestens zwei Decision Records referenziert werden. Die Einzelbewertungen der zugrunde liegenden Trades bleiben erhalten.

## 1. Neue Evidenz seit dem Decision Record

Für jede materielle neue Evidenz:

| Evidence-ID | Stand | Quelle | Beobachtung | Ex-ante-Verfügbarkeit | Trade-ID(s) | Thesis-ID(s) |
|---|---|---|---|---|---|---|
| E1 |  |  |  | `available_and_missed` / `partially_available` / `not_available` / `unknown` |  |  |

Wichtig:

- Neue Evidenz beschreibt, was seit der Entscheidung bekannt wurde.
- `available_and_missed` ist ein möglicher Process-Hinweis; `not_available` ist kein rückwirkender Fehler.
- Outcome-Evidenz darf den versiegelten Ex-ante-Zustand nicht umschreiben.

## 2. Thesis Review

Jede ursprüngliche Thesis wird gegen die neue Evidenz geprüft.

| Trade-ID | Thesis-ID | Status | Evidenz-Zusammenfassung | Process-Implikation |
|---|---|---|---|---|
|  | T1 | `supported` / `weakened` / `rejected` / `unresolved` / `not_testable` |  |  |

Eine abgelehnte Thesis beweist nicht automatisch einen schlechten Process. Probabilistisch vernünftige Annahmen können ungünstig realisiert werden.

## 3. Process Assessment

- Overall: `strong` / `sound` / `mixed` / `weak` / `insufficient_evidence`
- Cause Tags:
  - `process_error`
  - `information_missed`
  - `valuation_error`
  - `projection_error`
  - `roster_construction_error`
  - `negotiation_error`
  - `bias_error`
  - `reasonable_uncertainty`
  - `external_shock`
  - `variance`
  - `no_error`
- Zusammenfassung:

`no_error` darf nicht zusammen mit einem Error-Tag verwendet werden. `reasonable_uncertainty`, `external_shock` und `variance` erklären Ergebnisse, sind aber für sich kein Process-Fehler.

## 4. Outcome Assessment

- Overall: `strong_positive` / `positive` / `mixed` / `negative` / `strong_negative` / `unresolved`
- Zusammenfassung:

### Asset Outcomes

| Trade-ID | Asset | Status | Zusammenfassung |
|---|---|---|---|
|  |  | `favorable` / `neutral` / `unfavorable` / `unresolved` |  |

Outcome bewertet das realisierte Ergebnis am Review-Horizont. Es ersetzt nicht das Process Assessment.

## 5. Re-Decision

### Same-information re-decision

> Wenn wir wieder am ursprünglichen Entscheidungsdatum wären und nur die damals vernünftigerweise verfügbaren Informationen verwenden dürften: Würden wir dieselbe Entscheidung treffen?

- Antwort: `yes` / `lean_yes` / `uncertain` / `lean_no` / `no`
- Begründung:

### Current-information re-decision

> Wenn uns derselbe exakte Trade am Review-Datum mit heutigem Wissen angeboten würde: Würden wir ihn machen?

- Antwort: `yes` / `lean_yes` / `uncertain` / `lean_no` / `no`
- Begründung:

Die erste Frage kalibriert primär den damaligen Process. Die zweite beschreibt die heutige Value-/Outcome-Sicht.

## 6. Confidence Calibration

- Assessment: `well_calibrated` / `overconfident` / `underconfident` / `inconclusive`
- Zusammenfassung:

Beziehe die ursprüngliche Decision Confidence, Outcome Uncertainty und das Gut Feeling ein. Aus einem einzelnen Trade darf keine dauerhafte persönliche Process-Regel abgeleitet werden.

## 7. Lessons

| Kategorie | Aussage | Promotion Status |
|---|---|---|
| `process_candidate` / `personal_calibration_candidate` / `negotiation_candidate` / `no_change` |  | `observed` / `proposed_for_promotion` |

Ein Review kann eine wiederverwendbare Regel nur vorschlagen. Änderungen an kanonischen Regeln, Owner-Profilen oder Knowledge bleiben separate, ausdrücklich zu genehmigende Promotion-Schritte.

## 8. Nächster Review

Wenn kein weiterer Review sinnvoll ist:

- Next Review: `null`

Andernfalls:

- Review-Typ:
- Trigger:
- Grund:

Nutze weitere Reviews nur, wenn der ursprüngliche Horizont oder eine weiterhin ungelöste Thesis sie rechtfertigt.

## 9. Review-Check

Vor Veröffentlichung/ Speicherung prüfen:

- [ ] Der versiegelte Decision Record wurde nicht verändert.
- [ ] Neue Evidenz ist vom Ex-ante-Zustand getrennt.
- [ ] Ex-ante-Verfügbarkeit jeder materiellen Evidenz ist klassifiziert.
- [ ] Jede relevante ursprüngliche Thesis wurde geprüft.
- [ ] Process und Outcome wurden getrennt bewertet.
- [ ] Same-information und Current-information Re-Decision wurden getrennt beantwortet.
- [ ] Confidence Calibration leitet aus einem einzelnen Trade keine dauerhafte Regel ab.
- [ ] Bei Portfolio-Reviews bleiben die Einzeltrade-Referenzen und Einzelbewertungen nachvollziehbar.
- [ ] Das Review-JSON validiert gegen `fantasy-management/_ai/schemas/trade-decision-review.schema.json`.
