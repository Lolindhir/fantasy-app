# Draft Strategy Rules

Purpose: reusable rules for Rookie Draft, Free-Agent Draft, draft-market, postmortem and opponent-draft-tendency work.

These rules supplement `FANTASY_MANAGEMENT_RULES.md`. Dynamic league, roster, player and market facts must still be re-derived from current sources.

## 1. Keep Rookie and Free-Agent Draft markets separate

Treat Rookie Draft and Free-Agent Draft as distinct markets.

- Maintain separate historical position distributions, pick ranges, manager tendencies and player-pool assumptions for each draft type.
- A combined seasonal rollup may be used as a secondary league-style view, but it must not replace the draft-specific model.
- Do not transfer a same-numbered pick, positional run or observed scarcity from one draft type to the other without evidence.
- Do not import generic Superflex/2QB or Tight-End-Premium scarcity directly into this league. Check actual league size, fixed starters, replacement level, current player pool and observed league behavior first.
- For the Free-Agent Draft, continue to apply the dynamic mixed-pool and exact-pick opportunity-cost rules in `FANTASY_MANAGEMENT_RULES.md` and `ROSTER_ARCHITECTURE.md`.

## 2. Evidence hierarchy for owner draft behavior

Use draft behavior as probabilistic evidence, not as a deterministic personality label.

Preferred evidence order:

1. direct manager target or strategy statements tied to the current draft;
2. current pre-draft roster/need analysis from a dated source;
3. repeated behavior across multiple draft decisions of the same type;
4. repeated behavior across different draft types or seasons;
5. a single pick or single-draft position count.

Rules:

- Never infer a pre-draft need solely from the player ultimately selected.
- Keep draft tendencies separate from trade-negotiation tendencies.
- A manager's current roster, current board/target evidence and current draft pool can override older historical tendencies.
- Record `candidate`, `provisional` or `confirmed` status and a confidence level when a behavior inference is stored.
- A single new draft may strengthen or weaken an existing pattern, but should not by itself create a permanent high-confidence rule unless it directly confirms an already repeated pattern.
- Use `fantasy-management/league-context/owner-draft-behavior.md` as the cumulative draft-specific evidence map.

## 3. Position tiers and tier cliffs

Draft positions must be modeled through player tiers and expected replacement shelves, not through position labels alone.

For QB, distinguish at minimum when the available population supports it:

- premium/anchor or unusually secure desired starter;
- functional startable QB / QB2 layer;
- developmental, contingent or uncertain starter path.

The 2026 Free-Agent Draft is the first explicit calibration point:

- Brock Purdy went at 1.03;
- the next 16 selections contained no QB;
- Jared Goff went at 4.02;
- Cam Ward, C.J. Stroud, Sam Darnold and Malik Willis then went in Round 5.

Interpretation: the league can pay early for a preferred premium QB while allowing the next QB layer to fall sharply. This is a **2026 baseline to re-test**, not a permanent claim that all QBs are cheap.

For TE, do not assume systematic neglect. In 2026 four TEs were selected in the Rookie Draft and four in the Free-Agent Draft. The league's two fixed TE starters are already visible in actual draft behavior. Future TE value must therefore be based on the concrete tier, replacement shelf and current owner demand.

## 4. Need-versus-value trigger discipline

Before each Mighty Giants draft, separate:

- structural roster needs;
- preferred value/ceiling targets;
- deliberately deprioritized or excluded positions.

For every meaningful structural need, define before the relevant pick window when possible:

- preferred player tier;
- latest acceptable tier / tier cliff;
- expected replacement shelf at the next Mighty Giants pick;
- opponents between current and next Mighty Giants selection whose current evidence raises the risk of that tier disappearing;
- action when the tier collapses: select, trade up/down, pivot or pass;
- fallback plan if the need remains unresolved.

Do not let a generic BPA/upside preference silently overwrite a declared structural need. Either follow the pre-defined trigger or explicitly reclassify the need because new information changed the decision.

Conversely, if a position was deliberately excluded or deprioritized in the pre-draft plan, do not later grade the process as a failure merely because that position was not drafted.

## 5. Opponent prediction model

For each opponent, start with the current draft-day context and then adjust with historical behavior.

Use this order:

`current roster/need + direct target evidence + current pool/tier -> owner history modifier -> pick probability`

Do not use:

`owner historical tendency -> deterministic next pick`

Practical implications:

- a strong repeated tendency may move an owner up or down as a threat within a tier;
- direct target conviction is stronger than a broad positional tendency;
- a trade-up for one named target proves target conviction more strongly than generic willingness to trade up;
- an owner with a historical position preference may still take a different position when a premium tier or roster need dominates;
- owner history should affect timing, trade decisions and risk estimates, not replace the live board.

## 6. Free-Agent Draft specific rules

In addition to the general draft rules:

- Use the current FA-board readmodel for live availability when valid.
- Re-evaluate after material selections, cuts and pick trades because the pool is dynamic.
- Treat the Owner Draft Behavior Matrix as a demand forecast only. It cannot establish player availability.
- Model the exact overall pick and realistic shelf; do not value a Free-Agent Draft pick by its round label alone.
- A current live target statement may justify increasing the price of a move-up opportunity, but do not infer that every later pick held by the same owner has the same value.
- Preserve the difference between acquiring a player, acquiring optionality and avoiding an additional roster cut.

## 7. Annual Owner Draft Behavior Matrix maintenance

After the season's Rookie and Free-Agent Drafts are complete, append a new annual evidence section to:

`fantasy-management/league-context/owner-draft-behavior.md`

For each owner record at minimum:

- draft-specific pick count and position mix;
- notable early/late position timing;
- pick trades or move-ups that reveal target conviction;
- documented pre-draft needs when a dated source exists;
- whether selections aligned with or contradicted prior tendencies;
- confidence/status changes;
- one or more validation questions for the next draft season.

Maintenance rules:

- Append new annual evidence; do not rewrite prior annual evidence merely because later outcomes changed.
- Correct historical factual errors when discovered and identify the correction.
- Separate observed facts from interpretation.
- Do not promote a yearly pattern into a permanent owner profile without sufficient repeated evidence.
- When a cumulative tendency materially changes, update the matrix summary and, when warranted, the relevant draft section in `owner-profiles.md`.
- Player outcomes are reviewed separately from draft-process behavior.

## 8. Source-conflict and correction guardrail

Canonical repository draft data wins over chat summaries, remembered pick orders or manually reconstructed lists.

Before persisting a postmortem or updating the matrix:

1. resolve the exact draft in `public/data/Drafts.json`;
2. verify all picks, owners and traded-pick ownership;
3. verify owner identity through `owner-registry.json`;
4. compare any historical pre-draft need claim with a dated stored source;
5. if a prior chat or analysis summary conflicts with canonical data, correct the factual record before deriving tendencies.

Do not preserve a known factual error merely for conversational continuity. Preserve the correction note when the error materially affected an earlier conclusion.
