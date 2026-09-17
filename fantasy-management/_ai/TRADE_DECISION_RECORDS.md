# Trade Decision Records and Reviews

Purpose: define the canonical Fantasy Management contract for preserving trade decisions at execution time and reviewing them later without hindsight bias.

This file applies to player trades, pick-only trades, mixed player/pick trades, draft-day trade-ups or trade-downs, and linked trade sequences involving Mighty Giants.

It supplements `FANTASY_MANAGEMENT_RULES.md`, `TRADE_NEGOTIATION_RULES.md`, `DRAFT_STRATEGY_RULES.md` and `WORKFLOWS.md`. It does not replace current roster, player, market, salary, draft or negotiation analysis.

## 1. Core separation

Treat the following as separate artifacts and separate questions:

- **Negotiation history** records the path, counterparties, offers, counters and communication evidence.
- **Trade Decision Record** freezes what Mighty Giants knew, intended, believed and felt when the trade decision was made.
- **Trade review** adds later evidence and evaluates thesis support, process quality and actual outcome without rewriting the original decision state.
- **Durable decision log** may summarize the final user decision under `fantasy-management/decisions/<year>/`, but it must not replace the full Trade Decision Record.

Never collapse these layers into a single retrospective narrative.

The core principle is:

> Later outcomes may change our view of the result. They must not rewrite what was known or believed at decision time.

## 2. Storage contract

For a persisted trade decision, use:

```text
fantasy-management/analyses/<year>/trades/<yyyy-mm-dd-short-slug>/
  decision-record.json
  decision-record.md
  reviews/
    <yyyy-mm-dd>-<review-kind>.json
    <yyyy-mm-dd>-<review-kind>.md
```

For a portfolio-level review spanning several linked trades, use:

```text
fantasy-management/analyses/<year>/trades/portfolio-reviews/
  <yyyy-mm-dd>-<short-slug>.json
  <yyyy-mm-dd>-<short-slug>.md
```

The JSON file is the canonical structured artifact for queryable fields such as confidence, uncertainty, thesis status, provenance and review classifications.

The Markdown file is the human-readable narrative companion. It may explain the record in more detail but must not silently contradict the JSON. Shared transaction facts, confidence values, thesis IDs and review classifications must match the JSON.

A short final decision may additionally be logged in `fantasy-management/decisions/<year>/trade-decisions.md` when durable decision logging is explicitly approved. Create that file only when an actual decision is being persisted.

## 3. Record origin and reconstruction

Every Trade Decision Record must declare one of:

- `contemporaneous`: created from the decision state at or immediately around execution, before meaningful outcome evidence exists;
- `reconstructed`: created later from historical sources.

A reconstructed record must include:

- reconstruction date;
- reconstruction confidence from 1 to 5;
- explicit acknowledgement of the outcome firewall;
- reconstruction limitations;
- evidence provenance for every material reconstructed conclusion.

Preferred evidence order for reconstruction:

1. canonical transaction/draft data;
2. contemporary direct chat or negotiation evidence;
3. stored negotiation history created from contemporary material;
4. contemporary analyses, boards or market snapshots;
5. repository snapshots and dated league context;
6. Robert's current recollection;
7. later inference.

Later outcome evidence may be used to identify what happened after the trade, but it must not be used to invent the original thesis, confidence, risk perception or decision rationale.

When contemporary evidence and later recollection conflict, preserve the conflict and prefer the contemporary evidence for the ex-ante record unless there is a documented factual correction.

## 4. Exact transaction facts and pick lifecycle

Record the exact transaction rather than a memory-compressed version of it.

For each side capture every material asset:

- player;
- Rookie Draft pick;
- Free-Agent Draft pick;
- Startup or other draft pick;
- future pick;
- other explicit trade consideration.

Use exact pick identity when canonical data can resolve it. Do not reduce a resolved pick to a round label when the exact slot is known.

Do not retroactively describe a pick trade as a direct player-for-player trade merely because the pick later became a named player.

Example principle:

> Trading Pick 2.03 is a decision about the value and opportunity cost of Pick 2.03 at that time. The player later selected at 2.03 is outcome evidence, not the original traded asset.

If a pick is later exercised, traded again or changes identity through a draft-position swap, represent that as an asset-resolution or linked-decision event.

## 5. Decision context

The Decision Record must explain the problem the trade was intended to solve.

Capture as relevant:

- Mighty Giants objective;
- season phase;
- roster construction;
- contender/rebuild or other team-window context;
- salary/cap context;
- market opportunity;
- why the trade was actionable at that moment;
- constraints;
- protected assets;
- substitutable targets;
- alternatives considered;
- price ceiling or walk-away boundary;
- known risks.

Do not judge a historical decision against a problem it was never intended to solve.

## 6. Decision thesis

Every sealed record must contain at least one explicit, testable thesis. Prefer roughly three to seven material theses for complex trades.

Each thesis should state:

- what was expected;
- confidence from 1 to 5 when reconstructable;
- relevant horizon;
- conditions or evidence that would weaken or falsify it.

A thesis should be specific enough that a later review can classify it without moving the goalposts.

Examples of thesis dimensions include:

- expected starting-lineup gain;
- depth or injury-insurance value;
- dynasty/market/liquidity value;
- salary/cap benefit;
- positional portfolio balance;
- pick-shelf or opportunity-cost expectation;
- expected counterparty constraint;
- value of retained optionality.

Do not rewrite a thesis after later results arrive. A later review changes the thesis status, not the original thesis text.

## 7. Alternatives, protected assets and price ceiling

Preserve process information that would otherwise disappear after the deal closes.

Record:

- meaningful alternatives considered;
- why each alternative was not chosen;
- assets deliberately protected;
- the intended price ceiling when one existed;
- whether the executed deal was below, at, above or unknown relative to that ceiling;
- any reason for knowingly exceeding the prior ceiling.

A successful outcome does not erase a negotiation or process mistake. A poor outcome does not prove that a reasonable ceiling was wrong.

## 8. Decision state at execution

The sealed Decision Record must preserve Robert's decision state independently from later outcomes.

### Decision confidence

`decision_confidence` measures:

> How convinced was Robert at execution that this was the right Mighty Giants decision?

Use the 1–5 scale:

1. **Very low** — mostly speculative; major unresolved doubt.
2. **Low** — leaning toward the trade, but substantial doubt remains.
3. **Moderate** — more likely right than wrong, with meaningful uncertainty.
4. **High** — strong conviction; remaining doubts are secondary.
5. **Very high** — unusually strong conviction that the decision is correct.

This is not a prediction that the acquired assets will outperform every outgoing asset.

### Outcome uncertainty

`outcome_uncertainty` measures the expected width or variance of plausible future results even if the process is sound.

Use the 1–5 scale:

1. **Very low** — relatively narrow expected range.
2. **Low** — some uncertainty, but limited plausible spread.
3. **Moderate** — meaningful range of plausible outcomes.
4. **High** — wide range; several materially different outcomes are plausible.
5. **Very high** — extremely wide/high-variance outcome distribution.

Decision confidence and outcome uncertainty are independent. A trade can have high decision confidence and high outcome uncertainty.

### Gut feeling

Record the intuitive reaction separately as:

- `very_negative`
- `negative`
- `mixed`
- `positive`
- `very_positive`
- `unknown` only when a historical record cannot reconstruct it responsibly.

Also preserve:

- confidence rationale;
- primary confidence driver;
- primary source of doubt;
- known personal biases;
- provenance of the reconstructed decision state when applicable.

The purpose is later calibration, not to treat intuition as automatically correct.

## 9. Sealing and immutability

A Decision Record can be `draft` or `sealed`.

Seal a record only after the final trade decision is known and the user has approved durable persistence.

After sealing, do not rewrite:

- original theses;
- decision confidence;
- outcome uncertainty;
- gut feeling;
- rationale;
- known risks;
- alternatives;
- protected assets;
- price ceiling;
- original evidence interpretation.

Factual or provenance errors may be corrected when discovered, but every correction must be recorded in the structured correction log with:

- timestamp;
- field path;
- old and corrected summary;
- reason;
- evidence reference;
- whether the correction requires a new process review.

If a factual correction materially changes how the original decision should be evaluated, preserve the correction and create a new review. Do not silently rewrite the historical judgment.

## 10. Linked decisions and portfolio chains

A trade may be locally sensible only as part of a broader asset transformation.

Use explicit links for relationships such as:

- predecessor;
- successor;
- same strategy;
- cap chain;
- position rebalance;
- pick chain;
- other documented relationship.

Do not use a linked sequence to erase the process quality of an individual trade. Evaluate:

1. each transaction on its own ex-ante logic;
2. the combined portfolio transformation when the trades were strategically connected.

Portfolio reviews may span several Trade Decision Records.

## 11. Review cadence and triggers

Do not use Week 1 or another tiny sample as a conclusive winner/loser review.

Default review triggers depend on asset type and original horizon.

### Player-involving trades

Default:

- `early_signal`: after enough role/usage evidence exists, normally after roughly 4–6 completed regular-season games in which the relevant player could reasonably participate;
- `season_end`: standard full-season review;
- `year_1`: add when the original thesis was materially dynasty-oriented or unresolved after season end.

The early review is primarily about role, usage and thesis evidence, not final outcome.

### Pick-only or pick-heavy trades

Default:

- `asset_resolution`: when the traded pick becomes an exact selection, is traded again, or otherwise materially resolves;
- `season_end` or `year_1` only when the original thesis requires evaluating the realized shelf, retained optionality or longer-horizon asset value.

Do not grade the original pick trade solely by the later NFL/fantasy career of the player selected with that pick.

### Long-horizon trades

Use `year_2` or `year_3` only when:

- the original thesis was explicitly multi-year; or
- a material thesis remains unresolved.

Do not create reviews merely because another anniversary passed.

### Ad hoc review

Create an `ad_hoc` review when a material event directly changes a thesis, for example:

- major injury;
- major NFL trade/release;
- permanent role change;
- pick resolution;
- unexpected retirement;
- material format/rule change affecting the original thesis.

Avoid noise. A material event is a review trigger, not permission to rewrite the Decision Record.

This contract defines review checkpoints. It does not authorize a scheduler, automation or GitHub Action.

## 12. Review evidence discipline

Every review must distinguish:

- what happened after execution;
- whether the new evidence was available, partially available or unavailable at decision time;
- whether the evidence affects the original process or only the later outcome.

For each thesis use one status:

- `supported`
- `weakened`
- `rejected`
- `unresolved`
- `not_testable`

A thesis can be rejected without proving that the overall process was bad. A good probabilistic thesis can produce a bad realized outcome.

## 13. Process assessment and outcome assessment

Every substantive review must assess process and outcome separately.

### Process assessment

Use one overall status:

- `strong`
- `sound`
- `mixed`
- `weak`
- `insufficient_evidence`

Use cause tags when relevant:

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

`no_error` must not coexist with an error tag. `reasonable_uncertainty`, `external_shock` and `variance` are explanatory categories, not proof of a process failure.

### Outcome assessment

Use one overall status:

- `strong_positive`
- `positive`
- `mixed`
- `negative`
- `strong_negative`
- `unresolved`

Outcome status describes what the transaction produced for Mighty Giants at the review horizon. It must not be substituted for the process assessment.

## 14. Re-decision questions

Every substantive review should answer two separate questions.

### Same-information re-decision

> If we were back at the original decision date and were allowed to use only the information reasonably available then, would we make the same decision?

Allowed answers:

- `yes`
- `lean_yes`
- `uncertain`
- `lean_no`
- `no`

This is the primary process-calibration question.

### Current-information re-decision

> If the same exact trade were offered at the review date with current information, would we make it?

Use the same answer scale.

This is a current value/outcome question. It does not rewrite the historical process grade.

## 15. Confidence calibration and learning

Reviews should explicitly assess whether the original decision confidence and gut feeling were informative.

Use:

- `well_calibrated`
- `overconfident`
- `underconfident`
- `inconclusive`

Do not infer a durable rule from one trade.

Examples of later testable portfolio-level questions:

- Do low-confidence trades produce more process errors?
- Does low confidence merely identify high outcome variance?
- Are we systematically uncomfortable when moving premium outgoing assets even when the trade process is sound?
- Does strong personal conviction improve decisions or increase bias risk?
- Are particular uncertainty signals more diagnostic than the final outcome?

Promote a reusable process rule only after repeated evidence or a separate validated review and explicit user approval.

## 16. Review artifact rules

A review is always a new artifact. Never append review conclusions into the sealed Decision Record.

A review may cover:

- one trade;
- several linked trades in a portfolio review.

For a portfolio review, preserve references to every underlying record and evaluate both individual and combined consequences.

A review can propose:

- process lessons;
- confidence-calibration hypotheses;
- negotiation lessons;
- no change.

A review does not automatically modify:

- `FANTASY_MANAGEMENT_RULES.md`;
- `TRADE_NEGOTIATION_RULES.md`;
- owner profiles;
- Knowledge;
- another sealed Decision Record.

Those promotions remain separate durable changes and require the normal evidence and approval rules.

## 17. Historical backfill workflow

When historical backfill is explicitly authorized:

1. resolve the exact canonical transaction or draft-pick movement;
2. identify every traded asset as it existed at the time;
3. gather contemporary chat, negotiation history, analyses, market snapshots and repository context;
4. reconstruct the decision context and theses using only ex-ante evidence;
5. use Robert's recollection to fill gaps while marking that provenance explicitly;
6. assign reconstruction confidence;
7. record unresolved conflicts or gaps instead of inventing certainty;
8. seal the reconstructed record only after review/approval;
9. create later review artifacts separately;
10. do not collapse pick trades into the later players selected.

Backfill may include the complete Mighty Giants history, including player trades, pick-only trades and draft-day trade-ups/downs, but it is a separate work package from defining this contract.

## 18. Validation

Structured files must validate against:

- `fantasy-management/_ai/schemas/trade-decision-record.schema.json`
- `fantasy-management/_ai/schemas/trade-decision-review.schema.json`

Use the templates under:

- `fantasy-management/_ai/templates/trades/`

Core question for a Decision Record:

> What did we know, what were we trying to accomplish, what did we believe, and how confident were we when we chose the trade?

Core question for a review:

> Given what was knowable then and what happened later, what does this teach us about the decision process without confusing process with outcome?
