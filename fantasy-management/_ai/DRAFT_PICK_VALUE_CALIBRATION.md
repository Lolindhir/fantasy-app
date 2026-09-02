# Draft Pick Value Calibration

Purpose: maintain league-specific empirical calibration for Rookie Draft picks versus Free-Agent Draft picks without turning a small sample into a permanent conversion table.

## Core rule

Free-Agent Draft picks and Rookie Draft picks are different asset types.

Do not assume that the same displayed round means the same value.

For any live trade, draft or roster decision, the authoritative valuation method remains the Free-Agent Draft opportunity-cost guardrail in `FANTASY_MANAGEMENT_RULES.md`:

- resolve the exact overall pick;
- inspect the realistic player shelf available at that pick;
- account for the actual six-team replacement level and league format;
- compare lineup value, depth value, dynasty/liquidity value and roster fit;
- treat the result as a range, not a deterministic conversion.

Historical draft results are calibration evidence for that process, not a replacement for it.

## Evidence policy

When comparing FA-pick and Rookie-pick value across seasons:

- record the number of comparable Rookie/FA draft pairs used as evidence;
- distinguish direct observed draft results from inference;
- assign confidence qualitatively (`low`, `medium`, `high`) based on sample size, consistency and comparability;
- do not promote a round-to-round conversion into a stable heuristic from a single draft pair;
- re-evaluate earlier conclusions when roster size, league size, draft depth, player pool, cut behavior or league rules materially change;
- prefer ranges and directional statements over exact equivalences until repeated evidence supports tighter calibration.

## 2026 first calibration sample

Sample size: **1** comparable Rookie Draft / Free-Agent Draft pair.

Confidence: **low**.

Observed directional signal:

- the 2026 Free-Agent Draft has produced materially stronger player shelves in several middle and later rounds than a naive same-round Rookie Draft comparison would imply;
- this suggests that FA picks in this shallow six-team league may be systematically undervalued when managers treat `FA 4th` as automatically equivalent to `Rookie 4th`, and similarly for other same-numbered rounds;
- the signal is strongest as a warning against same-round equivalence, not as proof of a specific conversion such as `FA 4th = Rookie 3rd`;
- early Rookie first-round picks retain special ceiling and trade-liquidity characteristics and should not be collapsed into a simple one-round conversion model.

### Current provisional interpretation

Use only as a soft prior when no better exact-pick analysis is available:

- FA picks appear at least competitive with same-round Rookie picks in this league;
- middle and later FA picks may deserve a premium over same-round Rookie picks;
- the size of that premium is not yet established.

Do **not** store or apply a hard table such as:

`FA 2nd = Rookie 1st/2nd`

`FA 3rd = Rookie 2nd`

`FA 4th = Rookie 3rd`

Those relationships may be useful conversational estimates for the 2026 pool, but they are not stable league rules at Sample Size = 1.

## Longitudinal update process

After each completed Rookie Draft and Free-Agent Draft:

1. preserve the actual pick order and players selected from `public/data/Drafts.json`;
2. compare the player quality/value shelves by exact overall pick and by broader draft segment;
3. record meaningful roster cuts that changed the FA pool during the draft;
4. compare current market/dynasty evidence for the selected players while keeping source type and six-team replacement level explicit;
5. note whether the prior directional signal was confirmed, weakened or contradicted;
6. increase confidence only when multiple comparable seasons show a consistent pattern;
7. only then consider adding stable round-band heuristics to `FANTASY_MANAGEMENT_RULES.md`.

## Decision implication

Until more samples exist, future trade recommendations involving FA picks must explicitly avoid treating a same-round Rookie pick as an automatic fair return.

If an FA pick is exchanged for a Rookie pick, compare the exact expected player shelf and liquidity profile first. When the evidence is close, preserve optionality rather than relying on round labels alone.
