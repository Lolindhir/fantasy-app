# Fantasy Management Workflows

Purpose: reusable workflows for Fantasy Management tasks.

## General workflow

1. Read `fantasy-management/AGENTS.md`.
2. Read relevant rules under `fantasy-management/_ai/`.
3. Identify current app data needed from `public/data/`.
4. Load only required source, league-context, Knowledge, analysis and decision files.
5. Separate stable facts from dynamic values.
6. Store outputs in the correct Fantasy Management folder.

## Hypothesis and validation workflow

Use this workflow when an analysis produces a plausible but not yet durable empirical conclusion.

1. Store the dated baseline under `fantasy-management/analyses/<year>/` as a human-readable Markdown file and, when structured comparison matters, a machine-readable JSON file.
2. Record the repository ref or commit, concrete input paths, league format, population filters, method version, metrics, sample sizes, limitations and validity note.
3. Give every independently testable hypothesis a stable ID and start it with status `proposed`.
4. Define the future trigger, comparison populations, validation checks, permitted result statuses and expected review paths in the baseline.
5. Keep the baseline immutable. Later validation must be written to new review files that link to the original analysis instead of rewriting the original result.
6. Track the future validation task in a GitHub Issue according to `.ai-context/manual/work-tracking.yaml`; keep Fantasy Management scope labeled/routed to Fantasy Management rather than creating a parallel Markdown todo list.
7. Use `supported`, `partially_supported`, `rejected` or `inconclusive` for the later hypothesis result and track evidence strength separately, for example `single_snapshot`, `one_season_validated` or `multi_season_validated`.
8. Keep dated numerical thresholds and current player conclusions in analyses. Promote only validated, reusable interpretations to `knowledge/` after a separate interpretation step.
9. Add a durable method to `FANTASY_MANAGEMENT_RULES.md` only after validation and explicit user approval. Store a deliberately selected operating standard under `decisions/` when appropriate.

## Player analysis workflow

1. Load current league format and scoring.
2. Identify Mighty Giants context.
3. Load current player data through the relevant player chunks.
4. Load league-format notes.
5. Load relevant player, team and position Knowledge.
6. Load source-package takes as evidence when useful.
7. Check role, production, age, salary, availability and market context.
8. Produce a clear recommendation.
9. Store under `analyses/YYYY/players/` when requested.

## Trade analysis workflow

1. Resolve owners, players and picks.
2. Load owner registry, profiles and negotiation history.
3. Load current Mighty Giants roster, picks and cap context.
4. Resolve draft-pick metadata.
5. When the counterparty holds multiple reasonably substitutable targets, compare them first and set an internal preference order plus an individual price ceiling for each target before proposing a deal.
6. In multi-target situations, do not prematurely signal that one player is a must-have unless doing so is strategically useful or the user explicitly prefers that player; use the negotiation to learn which comparable asset the counterparty is most willing to move.
7. Load relevant Knowledge and source evidence.
8. Compare points, long-term value, roster construction, salary, liquidity and counterparty fit.
9. Add current market context when needed.
10. Give a clear Mighty Giants recommendation.
11. Store under `analyses/YYYY/trades/` when requested.

## Roster audit workflow

1. Load current League and Metadata.
2. Identify Mighty Giants by TeamID 1.
3. Load league-format notes.
4. Map roster, reserve and taxi players.
5. Load relevant Knowledge.
6. Cluster by position and role.
7. Evaluate salary separately from quality.
8. Review picks and trade liquidity.
9. Identify upgrades, packages, stashes and cut risks.
10. Store under `analyses/YYYY/roster/` when requested.

## Draft analysis workflow

1. Resolve the exact draft from current or historical Drafts data.
2. Record draft key, season, type, ownership, trades, player IDs and stable pick keys.
3. Load current context for current reports.
4. Capture immutable source paths and blob SHAs.
5. Classify historical context completeness.
6. Load relevant player chunks.
7. Add dated external market or ranking snapshots only when useful.
8. Separate process, market value, team fit and outcome.
9. Do not rewrite historical process grades because of later outcomes.
10. Evaluate every team and pick for full post-draft reports.
11. Store Markdown and JSON together under `analyses/<year>/drafts/`.
12. Validate against the draft-analysis schema.
13. Keep later reviews in new files linked to the original.

## Free-agent board workflow

Use the materialized FA-board contract for live or current Free-Agent-Draft availability and roster-capacity decisions. Do not manually recreate the League/Drafts join when a valid current readmodel is available.

1. Load `fantasy-management/generated/operations/fa-board-readmodel.json` first and verify its `quality`, `sources` and `current_fa_draft.resolution_status` fields before treating any player as available.
2. Treat `availability_status` as the canonical compact availability gate for the current FA-board context: only `available` may enter an available shortlist; `rostered`, `drafted` and `unknown` are not available.
3. Use `owner_team_id`, `owner_team_name` and `roster_bucket` for current fantasy ownership; use the current-FA-draft fields for already assigned picks that may not yet be materialized in `League.json`.
4. Use `reserve_eligible_now`, `taxi_eligible_now`, current special-capacity information, `active_slot_cost_now` and `active_slot_cost_on_materialization` when comparing normal BPA with Reserve-/IR-/Taxi stash paths. `active_slot_cost_now = 0` does not imply zero future retention cost.
5. Use the compact FantasyCalc/FantasyPros views in the readmodel for initial market/value context. Load broader `player-signals.json`, source snapshots or fresh external research only when the decision needs fields or qualitative context not carried by the readmodel.
6. Perform the Mandatory Stash Sweep from `ROSTER_ARCHITECTURE.md` before every own FA-Draft pick or `PASS`: active BPA, Reserve-/IR stashes, Taxi stashes before lock and any other currently valid special-capacity pool.
7. Re-read the current readmodel after every material opponent pick/cut or before each Mighty Giants pick; do not carry an earlier availability result forward through a dynamic draft.
8. If the readmodel is missing, schema-invalid, has unresolved mandatory inputs or cannot safely establish a negative ownership/draft result, fail closed. Reconstruct from complete current `League.json` + `Drafts.json` + `player-signals.json` only when necessary; never infer availability from `Players.json -> IsFreeAgent`, external rankings or a truncated tool response.
9. Load league-format notes, relevant Knowledge and fresh role/injury/news context for the highest-value candidates after deterministic availability is established.
10. Store a dated analysis under `analyses/YYYY/free-agents/` only when requested or otherwise explicitly approved.

`free-agent-signals.json` remains the complete ownership-derived free-agent population and the basis for general discovery/movement processing. During a live Free-Agent Draft it is not sufficient by itself to prove draft availability because a newly picked player may still be absent from `League.json`; `fa-board-readmodel.json` adds the current `Drafts.json` gate and capacity view.

## Kicker Streaming analysis workflow

The Kicker Streaming engine is a positionsspezifischer decision component. It is not a standalone weekly orchestration target and must not bypass the overall roster/waiver decision.

1. Load `fantasy-management/generated/operations/kicker-streaming-inputs.json` as the canonical prepared Kicker candidate set. Do not rebuild fantasy availability from `Players.json -> IsFreeAgent`.
2. Run `fantasy-management/_ai/scripts/analyze_kicker_streaming.py` without weekly context to produce the baseline ranking and research shortlist. The default execution is stdout-only.
3. Treat the baseline as prioritization, not a waiver recommendation. It combines CBS projections recalculated into current league-scoring bounds, FFToday projection rank and FFC Kicker ADP. Sleeper add activity is only a research tiebreaker.
4. For a concrete Weekly Lineup + Waiver decision, build the deterministic Kicker research plan and research the held kicker plus shortlisted free agents for the target week.
5. Verify schedule/matchup, expected team scoring environment, field-goal opportunity, venue/roof, weather when exposed, current kicking job and relevant player/QB/injury context from fresh sources.
6. Record the researched values in a temporary weekly-context document that validates against `fantasy-management/_ai/schemas/kicker-weekly-context.schema.json` and pins both source and research-plan fingerprints.
7. Use `run_kicker_weekly_analysis.py` as the supported gated path. Job security is an eligibility gate; a player with an unconfirmed current kicking job must not win a switch recommendation merely because of preseason projections or ADP.
8. Require the configured material score advantage before recommending a switch when the held kicker remains eligible. If the held kicker is on bye, use the explicit held-bye path rather than a fake zero score or job-security failure.
9. Output either a clear `switch_recommended`, `no_switch_recommended`, or `insufficient_context`. A baseline-only run must return `weekly_context_required`.
10. Keep provider fantasy points separate. Do not average provider FPTS or silently treat them as Mighty-Giants league points.
11. Hand the Kicker result back to the overarching Weekly Lineup + Waiver workflow, which must still evaluate the drop/bench-slot opportunity cost before a final roster transaction recommendation.
12. Store a dated Kicker Streaming analysis under `analyses/YYYY/kicker-streaming/` only when explicitly approved; otherwise keep the run ephemeral.

## Daily Monitoring workflow

Canonical architecture reference:

```text
fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md
```

Purpose: identify material changes and research priorities without making the final weekly transaction or lineup decision.

1. Let the scheduled source-refresh and materialization layers prepare the latest successful current inputs.
2. Resolve the active `entity-observation` target sets and profiles.
3. Reuse provider-neutral materialized inputs rather than independently rebuilding joins in monitoring.
4. Compare current signals with the last good comparable state where one exists.
5. Keep first observations and unchanged states silent.
6. Run fresh qualitative research only when required by the profile or when a concrete change signal makes it decision-relevant.
7. Emit only material developments with the observation, evidence quality, interpretation and affected future decision class separated.
8. Do not issue Start/Sit, Add/Drop or Waiver decisions from Daily Monitoring alone.
9. Route a material event toward the later appropriate decision process: Roster Review, Free-Agent Board, Trade analysis or Weekly Lineup + Waiver.
10. Keep scheduled monitoring read-only; durable State or event writes require explicit approval under the current Architecture.

### Kicker Daily Monitoring module

Kicker is the first positionsspezifischer Daily-Monitoring module built on this boundary.

Use:

```text
fantasy-management/automation/target-sets/kicker-daily-monitoring.json
fantasy-management/automation/profiles/kicker-signal-movement.json
fantasy-management/automation/workflows/kicker-daily-monitoring.md
```

The module observes the held kicker plus all actual fantasy-free-agent kickers from the current `kicker-streaming-inputs.json` contract.

It may monitor:

- baseline score/rank and shortlist entry;
- FFC Kicker ADP;
- FFToday/CBS projections and provider-neutral percentile consensus;
- Sleeper add activity as research priority;
- nominal K1 and structured injury triggers;
- NFL-team changes;
- triggered fresh job-security verification.

It must not pull weekly matchup, weather, field-goal opportunity or concrete start/sit logic into the normal daily material state.

## Weekly Lineup + Waiver workflow

This is the future concrete weekly decision workflow for the complete managed roster, not a Kicker-specific scheduler.

Canonical architecture reference:

```text
fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md
```

Target sequence:

1. Load current league scoring, roster rules, managed roster and actual fantasy-free-agent population.
2. Resolve the target NFL week and schedule.
3. Resolve availability, bye and injury constraints before ranking startable players.
4. Load current usage/opportunity, role, matchup and projection context.
5. Apply positionsspezifische modules where they add real information.
6. Determine the best legal starting lineup before considering roster moves.
7. Evaluate free-agent upgrades against the actual current starter/bench alternatives.
8. For every potential Add, identify the player who would need to be dropped and evaluate that player's bench/upside/scarcity/injury-insurance/trade-value opportunity cost.
9. Recommend a Waiver/Add/Drop only when the overall roster benefit is positive, not merely because one position has a small isolated score advantage.
10. Recompute the final lineup after approved/recommended moves.
11. Provide starters, bench, Waiver Adds and corresponding Drops, alternatives, confidence, bye/injury risks and time-critical actions.

### Kicker special case inside Weekly Lineup + Waiver

Default: hold one kicker.

- keep a stable good kicker when no material weekly advantage exists;
- stream when a verified free agent has a material weekly advantage;
- use explicit bye/job-loss/injury special paths;
- only hold two kickers when preserving the longer-term kicker is worth more than the non-kicker bench slot that must be sacrificed.

The Kicker engine can compare kickers. The Weekly Lineup + Waiver workflow must decide whether the roster cost of the move is justified.

The concrete timing, Waiver-window cadence, late-injury rechecks and any automatic orchestration remain open work tracked in GitHub Issues and require separate approval before workflow-file changes.

## Podcast workflow

Use for Stoned Lack, Down Set Talk, Football Bromance and future sources.

Default: one local source package per episode. Do not create active Knowledge or global indexes during normal extraction.

1. Read `PODCAST_SOURCE_MODEL.md`.
2. Read `PODCAST_EXTRACTION_RULES.md`.
3. Read `PODCAST_PACKAGE_STORAGE.md`.
4. Read podcast templates as flexible building blocks.
5. Load source identity from `source-registry.json`.
6. Load the central player identity registry.
7. Load source-specific notes and guides.
8. Create or update the episode package.
9. Store the complete raw source unchanged.
10. For split raw, create a manifest with contiguous ordered parts.
11. Perform Pass A over the complete raw source.
12. Create a detailed German `episode.md`.
13. Keep `episode.md` as one continuous reader-facing file; never split it.
14. Preserve every substantive segment, including content after the headline segment.
15. Preserve complete safely reconstructable rankings, tiers and mock-draft structures.
16. Create detailed categorized takes.
17. Create standalone takes for ranking, substantive and news subjects.
18. Keep inline resolution on every player take.
19. Perform Pass B by reading the complete raw source again.
20. Create the independent mention register from Pass B.
21. Record comparisons, competitors, historical examples, live-draft names and unresolved forms.
22. Reconcile required subjects with `episode.md` and the aggregated takes.
23. Keep context-only audit entries in the mention register; do not append a technical register to `episode.md`.
24. Use inline `takes.json`/`mentions.json` for small packages or split manifests plus parts for large technical payloads.
25. Do not reduce extraction detail to avoid splitting a large JSON file.
26. Add confirmed reusable aliases to the central registry.
27. Calculate `index.json` counts from the fully aggregated finished files.
28. Keep `index.json` references stable at `takes.json` and `mentions.json`, including in split mode.
29. Set `coverage_audit.status: completed` only after the full second pass, reconciliation and zero uncovered mentions.
30. Pretty-print every Fantasy Management JSON manifest and part.
31. Run the completeness gate.
32. Run validator unit tests.
33. Run package and coverage validators.
34. Do not update Knowledge unless explicitly requested.
35. Do not invent missing details.

Validation commands:

```bash
python -m unittest discover \
  -s fantasy-management/_ai/scripts/tests \
  -p "test_*.py" \
  -v

python fantasy-management/_ai/scripts/validate_episode_package.py \
  fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}

python fantasy-management/_ai/scripts/validate_episode_coverage.py \
  fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}
```

## Podcast package validation workflow

1. Run both validators for the changed package.
2. Run validator unit tests when scripts or tests changed.
3. Run all-package validation before merge when shared rules, templates, schemas, registries or scripts changed.
4. For split packages, validate the entry-point manifest, every part and the fully aggregated payload.
5. Do not add source- or episode-specific validation bypasses; fix the schema, package or validator defect instead.
6. Treat errors as blockers.
7. Treat warnings as review prompts.
8. Legacy schema-version-1 warnings do not invalidate historical packages.
9. The repository workflow runs these checks for relevant pull requests.

## Knowledge derivation workflow

1. Read completed source packages as evidence.
2. Treat episode, takes and mentions as source material, not final truth.
3. Load current league format and Mighty Giants context.
4. Decide which takes apply to the league and current market.
5. Store derived Knowledge under the correct `knowledge/` category.
6. Link back to source package and take IDs.
7. Keep final recommendations in analyses.

## Index rebuild workflow

1. Rebuild only when explicitly requested or required by maintenance.
2. Use completed packages or Knowledge as inputs.
3. Do not hand-maintain global indexes during normal extraction.
4. Record generation status and input files.

## League-context update workflow

Use owner registry, owner profiles, negotiation history and league-format notes for durable league context. Promote tendencies only after repeated evidence.

## External ranking refresh workflow

1. Read the source-specific README and machine-readable analysis metadata.
2. Fetch the official source directly with the documented format parameters.
3. Fail closed on network, source-identity, schema, row-count, rank or format-plausibility errors.
4. Keep source Raw retention and normalized-history policy source-specific.
5. For FantasyCalc, replace `raw-latest.json` after every successful fetch and archive only changed normalized rankings plus metadata.
6. Update `latest.json` only after all required files have been written successfully.
7. Run source-specific unit tests before publishing generated data.
8. Keep independent external sources in independent workflows so one unavailable source does not block another.
9. Treat all external rankings and market values as dated context, not permanent truth.
10. Reconcile source format with the actual six-team, fixed-2QB, fixed-2TE league during analysis instead of mutating source values.

## External signal refresh workflow

1. Read `fantasy-management/sources/external-signals/README.md`, the source-specific README and machine-readable analysis metadata.
2. Fetch only the provider's documented public API with the source-specific query configuration.
3. Keep the global source snapshot independent of `League.json`; league ownership and Mighty-Giants relevance belong to a downstream materialization step.
4. Fetch and validate every required activity/profile payload before publishing any part of the new source state.
5. Fail closed on network, schema, identity, duplicate, numeric or completeness errors and retain the previous successful state.
6. Treat the first successful run and every incompatible configuration change as a silent baseline that is not eligible for a material player event.
7. Compare only snapshots with the same schema, provider and query configuration.
8. Preserve top-N semantics: absence means outside the returned list, not zero activity.
9. Treat rolling-window count deltas as differences between overlapping windows, not transactions since the prior fetch.
10. Use source deltas only as targeted research triggers; do not turn them directly into add, drop, trade, hold, shop or cut recommendations.
11. Join `sleeper_player_id` to current player and league data only after source publication; retain unresolved IDs as data-quality findings.
12. Run source-specific unit tests before publishing generated data.
13. Attribute the provider in stored metadata and user-facing analysis.

## Monitoring input freshness and orchestration

The intended production order is:

```text
league/source refreshes
→ external ranking refreshes
→ external signal refreshes
→ derived player/ownership materialization
→ scheduled monitoring
```

Ranking and signal refreshes should finish shortly before the scheduled monitoring run so monitoring reads the newest successful inputs. Keep independent source refreshes failure-isolated, preserve their last good states and let the monitoring freshness gate decide whether a missing or stale required input blocks, limits or merely annotates the run.

Actual GitHub Actions schedules, dependencies and activation require a separate explicit approval. Documentation, scripts, tests and manual baselines may be prepared before that workflow approval.