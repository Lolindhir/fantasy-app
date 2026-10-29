# League Economy Research Instructions

Purpose: this folder is the dedicated research and design area for league-economy questions that sit above individual roster decisions or one isolated salary formula.

It exists to separate three related but distinct design layers:

1. rookie contracts, minimum salary and Dead Cap;
2. normal Performance Salary and Positional Criticality;
3. franchise/team-window strategy: Reload, Rebuild or Hybrid.

The eventual league-facing synthesis must connect these layers without turning one document into a second competing source of truth for all details.

## Required reading

For any task about league-economy redesign, long-term roster economics, franchise windows, Rebuild/Reload design, salary-system interaction or the shared Offseason paper, read:

1. `fantasy-management/AGENTS.md`
2. this file
3. `fantasy-management/league-context/league-format-notes.md`
4. `fantasy-management/league-economy/salary/salary-dead-cap-concept.md`
5. `fantasy-management/league-economy/salary/salary-system-redesign-concept.md`
6. `fantasy-management/league-economy/team-window-strategy-concept.md`
7. `fantasy-management/league-economy/league-economy-redesign-options.md` when cross-topic synthesis or league-facing presentation matters
8. current `public/data/League.json` when any conclusion depends on current team count, playoff settings, roster structure, scoring, trade deadline or other dynamic league settings

If implementation work later follows from a league decision, return to the normal root/application context before changing Runtime, generated-data, frontend or workflow behavior.

## Research principles

### Separate observed structure from desired design

Always distinguish:

- what the current league mechanics objectively create;
- what manager behavior has been observed;
- what the league wants to simulate;
- which mechanism could move behavior in that direction;
- what has actually been decided.

Do not treat "NFL-like" as a sufficient design argument. State which NFL-like behavior is desired and whether it remains appropriate in a six-team fantasy league.

### Do not assume Rebuild is inherently desirable

The core team-window question is deliberately open.

Do not begin from either of these assumptions:

- every Dynasty league should contain regular multi-year Rebuilds;
- a small league should avoid Rebuilds and stay permanently competitive.

Evaluate Reload-first, Rebuild-supportive and Hybrid structures on the same criteria before recommending a direction.

### Current format is evidence, not a permanent constant

The present format is six teams with four playoff spots, but analysis must re-read current league data when dynamic settings matter.

For the current structure, remember the mathematical baseline:

- four of six teams reaching the playoffs means an equal-strength team has a 4/6 = 66.7% playoff share before schedule-specific effects;
- a team only needs to finish ahead of two opponents to qualify;
- small league size concentrates NFL talent and raises replacement level;
- two-week playoff rounds reduce single-week variance compared with one-week elimination.

Do not silently extrapolate conclusions to a different future team count or playoff format.

### Treat Rookie order and legacy incentives as one system

The user-confirmed intended Rookie Draft order from prior-season final placement is:

- 5th place -> 1.01
- 6th place -> 1.02
- 4th place -> 1.03
- 3rd place -> 1.04
- 2nd place -> 1.05
- 1st place -> 1.06

Do not evaluate or redesign this order as an isolated anti-tanking, rebuild or competitive-balance lever.

Its intended incentive logic is coupled to long-term franchise achievements:

- finishing 5th instead of 6th remains rewarded with the earlier Rookie pick;
- finishing 3rd instead of 4th remains valuable because Third Places contribute to the intended All-Time standings;
- the user-confirmed intended All-Time achievement priority is Championships -> Runner-Ups -> Third Places -> Regular Season Kings;
- later Rookie picks for better finishes are therefore partly exchanged for durable franchise/legacy value rather than being a pure punishment for winning.

Treat this as a confirmed league-economy design intent unless the user explicitly reopens the Rookie-order or All-Time incentive design.

The current standings generator appears to diverge from the intended fourth criterion by using cumulative Regular Season wins after Third Places. That technical reconciliation is tracked separately in GitHub Issue #810. Do not silently redefine the intended design from the current implementation and do not change the runtime as part of league-economy research alone.

### Evaluate strategy as an option-value problem

In a league with late/open trading and broad playoff access, waiting can itself have value because a manager can retain championship upside and sell later if elimination becomes clear.

When comparing Reload and Rebuild incentives, explicitly consider:

- value of staying competitive;
- value of delaying a sell decision;
- cost of missing the optimal trade market;
- future pick / rookie-contract surplus;
- cap flexibility;
- persistence of contract or Dead-Cap consequences.

### Use one comparison framework for all options

Compare every major design direction across at least:

- competitive balance;
- strategic differentiation between teams;
- timing of buyer/seller separation;
- rookie-pick value;
- veteran value;
- cap and contract value;
- trade activity and liquidity;
- replacement level in a six-team league;
- turnaround time;
- tanking incentives;
- manager engagement during losing seasons;
- punishment for mistakes;
- reward for long-term planning;
- complexity and explainability;
- NFL resemblance versus fantasy-specific suitability.

Do not call an option better merely because it increases realism in one dimension.

## Canonical document roles

### Detail paper 1 — contracts and Dead Cap

Canonical source:

`fantasy-management/league-economy/salary/salary-dead-cap-concept.md`

Owns detailed Rookie Salary, Rookie Contract, Minimum Salary and Dead-Cap concepts.

### Detail paper 2 — Performance Salary and Criticality

Canonical source:

`fantasy-management/league-economy/salary/salary-system-redesign-concept.md`

Owns detailed Performance Salary research, Positional Criticality, empirical salary-market checks and future salary-formula design.

### Detail paper 3 — team windows

Canonical source:

`fantasy-management/league-economy/team-window-strategy-concept.md`

Owns the strategic question of Reload vs. Rebuild vs. Hybrid and the mechanisms required to create or suppress different franchise time horizons.

### Synthesis paper

Canonical league-facing synthesis:

`fantasy-management/league-economy/league-economy-redesign-options.md`

The synthesis paper must summarize and connect the three detail papers. It must not silently redefine their formulas or overwrite unresolved questions.

## Required synthesis structure

Keep the league-facing synthesis organized around these sections unless the user explicitly chooses another structure:

1. **What are we trying to simulate?**
   - desired NFL-like effects;
   - fantasy-specific limits of a six-team league;
   - design goals and non-goals.

2. **Team windows**
   - current structure;
   - Reload vs. Rebuild vs. Hybrid;
   - mathematical and strategic consequences.

3. **Rookie contracts and Dead Cap**
   - current proposal;
   - strategic effects;
   - unresolved choices relevant to the larger economy.

4. **Performance Salary and Positional Criticality**
   - current diagnosis;
   - dynamic Criticality architecture;
   - unresolved mathematical model.

5. **How the systems interact**
   - picks, cheap young contracts, veterans, cap pressure, cuts, trades and timing;
   - second-order incentives and possible unintended behavior.

6. **Coherent design packages**
   - present a small number of complete alternatives;
   - do not force league members to assemble a design from dozens of isolated toggles;
   - state what each package optimizes and what trade-offs it accepts.

7. **Open questions and Offseason decision path**
   - questions that still need league input;
   - evidence/backtests still needed;
   - decisions that should be made before implementation.

## Decision discipline

- Research documents may contain hypotheses, models and options.
- A mechanism is not a league rule merely because it appears in an option package.
- Mark confirmed concept decisions, preferred-but-unconfirmed directions and open questions separately.
- Do not implement a league-economy option merely because the research paper describes it.
- Material league-rule implementation requires an explicit later decision and implementation authorization.
- During the active season, prefer research, measurement and documentation unless the league explicitly chooses an in-season rule change.

## Language

Human-facing research and league discussion documents in this area are written in German unless the user explicitly asks otherwise.
