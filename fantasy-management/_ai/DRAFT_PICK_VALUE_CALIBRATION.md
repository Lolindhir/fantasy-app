# Draft Pick Value Calibration

Purpose: maintain league-specific empirical calibration for Rookie Draft picks versus Free-Agent Draft picks without turning a small sample into a permanent conversion table.

## Core rule

Free-Agent Draft picks and Rookie Draft picks are different asset types.

Do not assume that the same displayed round means the same value.

For any live trade, draft or roster decision, the authoritative valuation method remains the Free-Agent Draft opportunity-cost guardrail in `FANTASY_MANAGEMENT_RULES.md` together with the roster/retention guardrails in `ROSTER_ARCHITECTURE.md`:

- resolve the exact overall pick;
- inspect the realistic player shelf available at that pick;
- account for the actual six-team replacement level and league format;
- compare lineup value, depth value, dynasty/liquidity value and roster fit;
- for Mighty Giants, include the actual cut/retention boundary, roster depth, coverage/churn constraints and `SalaryProjected`/retention risk of realistic candidates;
- treat the result as a range, not a deterministic conversion.

Historical draft results are calibration evidence for that process, not a replacement for it.

## Two valuation layers

FA-vs-Rookie pick comparisons must distinguish two related but different values.

### 1. League/market asset value

This asks what the pick is worth as a transferable asset in the league, independent of whether Mighty Giants should personally exercise it.

Relevant factors include:

- exact overall pick and expected player shelf;
- draft-pool depth and quality;
- liquidity and trade demand;
- timing/optionality of the asset;
- league-wide replacement level and manager behavior.

A Mighty Giants roster squeeze does **not** by itself prove that an FA pick has low league-wide market value. A pick can be worth more to another manager with a weaker roster or a lower cut boundary.

### 2. Mighty Giants exercise value

This asks how much value Mighty Giants actually gains by using the pick instead of trading or passing it.

For an FA pick, the exercise value must include:

- expected quality of the best realistic player available at the exact selection;
- incremental value over the player who would be displaced or cut;
- current roster depth and whether the candidate materially improves the lineup, coverage or dynasty asset base;
- coverage floors and protected churn capacity;
- `SalaryProjected` and resulting next-cycle retention/cap risk of the candidate;
- cap-adjusted value of the player who would otherwise be retained;
- likely retention horizon and exit/trade options;
- immediacy of the roster cost, because exercising the FA pick consumes a roster slot now.

This makes FA-pick value especially roster-sensitive. A strong theoretical FA shelf can still have low Mighty Giants exercise value when the available candidates do not clear the current retention boundary after salary and roster displacement are considered.

Rookie picks also require roster/cap evaluation, but they preserve more deferred optionality: they do not force an immediate current-roster cut, remain tradable until a later draft, and their future player/salary profile is not yet known. This optionality must be part of the comparison.

### Practical implication

Do not collapse market value and team-specific exercise value into one number.

Example pattern:

- an FA 4th may have a higher **league market value** than a same-year/future Rookie 4th because the expected player shelf is stronger;
- the same FA 4th may have a lower **Mighty Giants exercise value** if using it would only add a marginal veteran, force the loss of a better long-term hold, and add meaningful `SalaryProjected`/retention risk;
- in that situation, trading the FA pick for a lower theoretical market return can still be positive for Mighty Giants if the alternative is effectively passing the pick or destroying more roster value through the required cut.

## Rookie-pick salary modeling

The fixed three-year Rookie Contract creates a separate salary-cost dimension for Rookie-pick valuation. Keep this dimension distinct from the pick's player-value, liquidity and optionality value.

### Do not assign false precision to an unexercised pick

A future or still-unexercised Rookie pick does not automatically own one exact salary number.

For a known Fantasy Rookie Draft position, the Fantasy-draft component of the Year-1 formula is deterministic. The remaining uncertainty is primarily which player is selected and therefore which filtered NFL Draft rank enters the NFL component.

Model pre-exercise salary as a **range / envelope** unless the selected player is already known.

Useful pre-draft or pre-pick views include:

- mechanical reference salaries for representative NFL Draft ranks;
- a minimum/maximum or percentile-style envelope when the candidate population supports it;
- after the NFL Draft, a class-specific range based on realistic candidates expected around the exact Fantasy pick.

Do not treat a round label as sufficient. Salary analysis should resolve the exact overall Fantasy pick.

### Live contract at the current pick is deterministic

During the live Rookie Draft, once an exact Fantasy pick is on the clock and NFL Draft capital is known, calculate the contract for each available candidate using the canonical Rookie Salary formula.

For candidate `c` at current Fantasy rank `r_fantasy`:

```text
LiveYear1Pct(c)
= 0.65 * FantasyDraftPct(r_fantasy, N_Fantasy)
+ 0.35 * NflDraftPct(r_nfl(c), N_NFL)

LiveYear1Salary(c)
= prior-year Salary Cap * LiveYear1Pct(c)

LiveYear2Salary(c)
= 1.25 * LiveYear1Salary(c)

LiveYear3Salary(c)
= 1.50 * LiveYear1Salary(c)

Live3YTotal(c)
= 3.75 * LiveYear1Salary(c)
```

Use the canonical undrafted treatment when the player was not selected in the NFL Draft.

This calculation is not an estimate once the current Fantasy pick, prior-year cap basis, NFL Draft pool and candidate NFL rank are known.

### Contract-view decision surface

When salary is used in Rookie Draft analysis, prefer showing:

- Year 1 salary;
- Year 2 salary;
- Year 3 salary;
- three-year total.

A candidate's salary can fall as the Fantasy Draft progresses because the Fantasy component becomes cheaper while the candidate's NFL component remains fixed. When useful, expose that change as a `salary drop` or `contract savings` comparison against an earlier pick.

Do not interpret a lower contract automatically as higher overall pick value. Salary cost is one decision dimension alongside player quality, tier scarcity, roster fit, liquidity and opportunity cost.

### Historical expected salary per pick is a later calibration layer

A historical `Expected Salary for Pick X` model is optional, not required for the live-draft feature.

If added later:

- use exact overall Fantasy picks or defensible pick bands rather than round labels alone;
- derive distributions from observed selected-player NFL Draft ranks and the salary rule that actually applied;
- report sample size and uncertainty;
- prefer ranges or percentiles over a single deterministic number;
- re-evaluate the model when Rookie Salary rules, league size, draft length or NFL-position filtering changes;
- do not promote a small historical sample into a permanent fixed pick-salary table.

The live exact-player contract calculation and the historical expected-pick model are separate layers and must not be conflated.

## Evidence policy

When comparing FA-pick and Rookie-pick value across seasons:

- record the number of comparable Rookie/FA draft pairs used as evidence;
- distinguish direct observed draft results from inference;
- distinguish league/market asset value from Mighty Giants exercise value;
- assign confidence qualitatively (`low`, `medium`, `high`) based on sample size, consistency and comparability;
- do not promote a round-to-round conversion into a stable heuristic from a single draft pair;
- re-evaluate earlier conclusions when roster size, league size, draft depth, player pool, cut behavior, salary/cap mechanics or league rules materially change;
- prefer ranges and directional statements over exact equivalences until repeated evidence supports tighter calibration.

## 2026 first calibration sample

Sample size: **1** comparable Rookie Draft / Free-Agent Draft pair.

Confidence: **low**.

Observed directional signal:

- the 2026 Free-Agent Draft has produced materially stronger player shelves in several middle and later rounds than a naive same-round Rookie Draft comparison would imply;
- this suggests that FA picks in this shallow six-team league may be systematically undervalued when managers treat `FA 4th` as automatically equivalent to `Rookie 4th`, and similarly for other same-numbered rounds;
- the signal is strongest as a warning against same-round equivalence, not as proof of a specific conversion such as `FA 4th = Rookie 3rd`;
- early Rookie first-round picks retain special ceiling and trade-liquidity characteristics and should not be collapsed into a simple one-round conversion model;
- Mighty Giants' unusually deep roster materially reduces the exercise value of later FA picks when the remaining player shelf does not clear the current cut/retention boundary;
- veteran-heavy shelves can be further discounted for Mighty Giants when projected salary and next-cycle retention risk are high relative to their likely actual lineup/coverage utility.

### Current provisional interpretation

Use only as a soft prior when no better exact-pick analysis is available:

- FA picks appear at least competitive with same-round Rookie picks in this league at the **market/player-shelf** layer;
- middle and later FA picks may deserve a market premium over same-round Rookie picks;
- the size of that premium is not yet established;
- for Mighty Giants, later FA-pick **exercise value** may be materially lower than that market premium suggests because roster displacement, salary/retention risk and limited marginal lineup utility can erase much of the theoretical shelf advantage.

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
5. for Mighty Giants, reconstruct the contemporaneous cut/retention boundary and evaluate whether realistic candidates actually cleared it after roster depth, coverage, `SalaryProjected`, retention risk and exit options;
6. separate conclusions about league market value from conclusions about Mighty Giants exercise value;
7. note whether the prior directional signal was confirmed, weakened or contradicted;
8. increase confidence only when multiple comparable seasons show a consistent pattern;
9. only then consider adding stable round-band heuristics to `FANTASY_MANAGEMENT_RULES.md`.

## Decision implication

Until more samples exist, future trade recommendations involving FA picks must explicitly avoid treating a same-round Rookie pick as an automatic fair return.

If an FA pick is exchanged for a Rookie pick, compare both:

1. the pick's league/market value based on expected player shelf and liquidity; and
2. Mighty Giants' actual exercise value after roster displacement, salary/retention risk and optionality.

When the evidence is close, preserve optionality rather than relying on round labels alone. A trade can be below theoretical FA-pick market value and still be good roster management if the alternative is a pass or a negative-value roster displacement.