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
6. Add the future validation task to the root `TODO.md`; do not create a separate todo list under `fantasy-management/`.
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
5. Load relevant Knowledge and source evidence.
6. Compare points, long-term value, roster construction, salary, liquidity and counterparty fit.
7. Add current market context when needed.
8. Give a clear Mighty Giants recommendation.
9. Store under `analyses/YYYY/trades/` when requested.

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

1. Load current League data.
2. Build the owned-player ID set from roster, reserve and taxi.
3. Load relevant player chunks.
4. Exclude all owned IDs.
5. Load league-format notes and relevant Knowledge.
6. Evaluate role, production, age, format fit and salary.
7. Verify top candidates.
8. Store under `analyses/YYYY/free-agent-boards/` when requested.

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
