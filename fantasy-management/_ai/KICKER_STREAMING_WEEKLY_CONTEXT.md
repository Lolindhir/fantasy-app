# Kicker Streaming Weekly Context

## Purpose

The weekly Kicker Streaming context bridges the deterministic Fantasy Operations datasets and the gated Kicker recommendation engine.

It has two separate products:

1. a reproducible **research plan** that narrows the candidate population and resolves the current NFL game from repository data;
2. an ephemeral **weekly context** that adds fresh venue, weather, job-security, injury and matchup research immediately before a decision.

The research plan contains no Add/Drop recommendation. The weekly context is analysis input, not generated repository truth.

## Deterministic inputs

The research plan reads only versioned/current repository inputs:

```text
fantasy-management/generated/operations/kicker-streaming-inputs.json
fantasy-management/_ai/kicker-streaming-analysis-config.json
fantasy-management/_ai/kicker-weekly-research-config.json
public/data/Schedule.json
```

`public/data/Schedule.json` is the canonical repository schedule input. Do not fetch a second schedule feed merely to rebuild the same matchup mapping.

The builder is:

```text
fantasy-management/_ai/scripts/build_kicker_weekly_research_plan.py
```

The output contract is:

```text
fantasy-management/_ai/schemas/kicker-weekly-research-plan.schema.json
```

The builder defaults to stdout. A generated file may be written explicitly when needed, but no workflow activation is implied by this contract.

## Candidate selection

The research plan must use the same baseline functions and shortlist settings as `analyze_kicker_streaming.py`.

Population:

- every currently held Kicker for the managed team;
- the configured number of highest-ranked fantasy-free-agent Kickers with a comparable baseline score.

The current analysis configuration selects eight free-agent candidates in addition to the held Kicker.

Fantasy availability comes from the upstream Kicker Streaming input contract and ultimately from the League `Roster`/`Reserve`/`Taxi` union. `Players.json -> IsFreeAgent` is never a fantasy-league availability signal.

## Schedule mapping

For the target season/week, a shortlisted Kicker is matched by `nfl_team` against `Schedule.json -> home/away`.

Exactly one game means `scheduled`.

Zero games means `bye`; zero games is not a data-quality error.

More than one game for the same NFL team in the target week fails closed.

The research plan retains:

- game ID;
- home and away team;
- opponent;
- Kicker team side (`home` or `away`);
- game date/time and kickoff epoch;
- neutral-site flag;
- ESPN game ID/link;
- CBS game link.

## Venue and roof

`Schedule.json` currently does not carry game-venue or roof metadata. Do not infer a venue only from the home team and store it as fact.

Every scheduled shortlisted candidate therefore receives an explicit venue-research requirement.

For a normal home game, the home team may be used only as the expected venue owner and research starting point.

For a neutral-site game, the actual game venue must be verified explicitly; normal home-stadium assumptions are invalid.

Preferred evidence order:

1. official NFL/team/game information;
2. official stadium/venue information;
3. reputable game listings only when official evidence is unavailable.

The research result should capture venue name, location, roof type/state when relevant and whether outdoor weather can materially affect kicking conditions.

## Weather

Weather is fresh decision context and must not be hard-coded into the generated research plan.

For outdoor or weather-exposed games, use a fresh forecast for the verified venue location. Prefer the responsible official public weather service; for United States venues this normally means the National Weather Service. For international games use the responsible local official meteorological service when practical.

The current policy is:

- a context may become `decision_ready` no earlier than 168 hours before kickoff;
- weather evidence used for a decision should be no more than 24 hours old at the context check;
- a verified closed-roof indoor condition may neutralize external weather in the Kicker score, but the roof/venue state itself must still be evidenced.

The seven-day outer gate matches the horizon of official NWS seven-day forecasts; the 24-hour weather freshness gate intentionally requires a newer check near the actual decision.

## Job security and player injury

Kicker job security is an eligibility gate, not a small scoring bonus.

Before a Kicker can be treated as an eligible weekly alternative, verify current job status. Prefer current official roster/depth-chart/team information. If camp competition or recent reporting makes the job ambiguous, preserve that ambiguity as `competition` or `uncertain` instead of assuming a starter.

Current job-security evidence and Kicker injury evidence should normally be no more than 24 hours old at the weekly-context check.

An explicit `not_current_starter` or disqualifying injury state prevents the candidate from becoming an eligible recommended alternative.

## Matchup, offense and Field-Goal opportunity

The weekly context separately scores:

- matchup;
- offense/scoring environment;
- Field-Goal opportunity;
- weather/stadium;
- QB/injury context.

Do not collapse these dimensions into one generic projection.

Use current structured repository data when it actually supports the claim. Fresh external research remains appropriate for information that the repository does not materialize reliably yet.

Field-Goal opportunity should describe the likelihood of Kicker attempts, not simply the strength of the offense. A strong touchdown-heavy offense and a team that frequently stalls in scoring range can create different Kicker profiles.

QB/injury context should capture material changes to expected scoring environment, not reward or punish a Kicker merely because an unrelated player has an injury designation.

## Weekly context handoff

The final researched context must validate against:

```text
fantasy-management/_ai/schemas/kicker-weekly-context.schema.json
```

It must retain evidence per player and bind to the current `kicker-streaming-inputs.json -> input_fingerprint`.

The recommendation engine is then run with:

```bash
python fantasy-management/_ai/scripts/analyze_kicker_streaming.py \
  --weekly-context <weekly-context.json>
```

Without a complete current weekly context, the engine remains at `weekly_context_required` or `insufficient_context` and must not produce a forced Add/Drop recommendation.

## Persistence and automation boundary

The research plan is deterministic and reproducible.

The researched weekly context is ephemeral by default because weather, job security and injuries are time-sensitive. A dated analysis may be persisted under `fantasy-management/analyses/` only after explicit approval under the normal Fantasy Management persistence rules.

No GitHub Actions workflow is created or modified by this design. Any future automatic materialization or scheduled weekly research orchestration requires a separate explicit workflow approval.
