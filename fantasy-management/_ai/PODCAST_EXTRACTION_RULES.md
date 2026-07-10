# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for Stoned Lack, Down Set Talk, Football Bromance and future podcast sources.

The detailed source/knowledge/analysis separation is defined in:

`fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`

## Core rule

Podcast extraction is source work, not final Fantasy Management analysis.

A podcast extraction answers:

> What did the podcast say, how did it argue, and which fantasy-relevant entities and statements appeared?

It must not answer:

> What should Mighty Giants do?

That belongs to later Knowledge derivation and Analysis.

## Canonical source configuration

Podcast source identity, weighting and profile comparison are maintained centrally in:

`fantasy-management/_ai/source-registry.json`

Podcast-specific quirks, recurring wording patterns and interpretation notes belong next to the source in:

`sources/podcasts/{source_id}/SOURCE_NOTES.md`

Do not maintain source weights in multiple places.

## Central player identity registry

Podcast-independent player identity mappings, aliases and transcript-error resolutions are maintained centrally in:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Use this registry before and during every podcast/source extraction that mentions players.

The registry is not a source take, not Knowledge, not a ranking and not a recommendation. It is a reusable entity-resolution aid.

Add confirmed reusable aliases or transcript-error mappings to the registry when they are discovered. Do not add speculative mappings.

## Entity aliases and transcript name resolution

During podcast extraction, actively watch for recurring aliases, nicknames, transcript errors and phonetic name variants for players, teams, coaches, colleges and other decision-relevant entities.

Examples:

- German transcripts may distort English player names phonetically.
- English sources may use nicknames, initials, shortened names or college-only references.
- Automatic transcripts may split suffixes such as `Jr.`, confuse similar names or mistranscribe uncommon rookie names.

Raw source text must stay unchanged. Do not rewrite raw transcript wording.

In `episode.md`, `takes.json` and `mentions.json`, use the best canonical entity name only when confidence is sufficient. Preserve uncertainty when the mapping is not fully resolved.

If a recurring player alias or transcript error is confirmed, store it in the central podcast-independent player identity registry above, not in a podcast-local alias file.

Use source-specific `SOURCE_NOTES.md` only for source quirks, pronunciation patterns and unresolved recurring issues. Use the central registry for confirmed mappings that may help future extraction across multiple sources.

Do not create or apply an alias mapping when the identity is uncertain. Leave the entity unresolved and mark the uncertainty explicitly.

## Canonical player identity rule

Player identity resolution is a required extraction step, not a best-effort cleanup step.

For every player take, `takes.json` must include:

- `raw_entity_mention`: the name, nickname, surname or transcript phrase as heard/read in the raw source.
- `entity`: the canonical full player name, only when verified with sufficient confidence; otherwise `null`.
- `entity_resolution`: compact inline status metadata for the mapping.

`raw_entity_mention` is required even when the canonical name is obvious. It preserves the connection to the raw source.

For confirmed player identities, keep `entity_resolution` compact by default:

```json
"entity_resolution": {
  "status": "confirmed",
  "method": "registry",
  "confidence": "high"
}
```

Allowed `method` values:

- `registry`: resolved through `player_identity_registry.json`
- `external_verification`: resolved through external identity verification during extraction
- `context_inference`: resolved from strong source context when a registry entry is not yet present
- `manual_confirmation`: user or maintainer explicitly confirmed the mapping
- `none`: used only for `unresolved`

Only add optional detail fields such as `reason`, `candidates` or `verified_sources` when they add useful information, especially for ambiguous, unresolved or newly verified identities.

Do not use a surname-only value such as `Price` as a finished player entity unless the take is explicitly about a one-name public entity and this is verified. For normal NFL player takes, a surname-only mention must be resolved to a canonical full name or marked unresolved.

Do not invent or auto-complete first names from memory. A plausible-looking full name is still wrong if it has not been verified against the episode context, registry or external identity sources.

For each high-signal player take, use source context before accepting a canonical player name:

- NFL team or landing spot
- position
- college
- draft round or pick range
- depth chart context
- teammates or competitors mentioned nearby
- episode section and timestamp

Then verify decision-relevant identities against current external identity sources when available. Preferred order:

1. official NFL or team pages
2. NFL.com Draft Tracker or official draft material
3. official college/athletics pages
4. Pro Football Reference / Sports Reference
5. ESPN, Sleeper, FantasyPros, KeepTradeCut or similar fantasy sources only as supporting context, not primary identity proof

Use `entity_resolution.status`:

- `confirmed`: canonical full name is verified and matches podcast/source context.
- `ambiguous`: likely candidates exist, but the transcript/source context is not enough to choose safely.
- `unresolved`: no reliable mapping has been found.

If status is `ambiguous` or `unresolved`, do not write a confident canonical `entity`. Use `entity: null` and include useful candidate or reason notes in `entity_resolution`.

A companion `entity_resolution.json` file is not a valid substitute for inline player resolution in `takes.json` or `mentions.json` for new or fully reworked packages.

## Episode package rule

Each new processed podcast episode should be stored as one local package using the current package schema:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  mentions.json
  index.json
```

For small transcripts, `raw/source.md` may replace split raw parts.

New and fully reworked packages use `package_schema_version: 2` in `index.json`. Older packages may remain on the legacy structure until explicitly reworked.

## Required default outputs

A normal schema-version-2 podcast extraction creates:

1. raw source material under the episode package
2. `episode.md` as a detailed German human-readable preparation of the fantasy-relevant podcast content
3. `takes.json` as structured source takes grouped by category, including compact inline player identity resolution for every player take
4. `mentions.json` as the complete entity-mention and coverage register
5. `index.json` as local technical metadata, counts and audit status

Do not update global indexes during normal podcast extraction.

Do not write source takes to any separate derived take area by default. Podcast takes are not Knowledge yet.

## `episode.md` rule

`episode.md` is the detailed reader-facing podcast preparation.

It is not a short executive summary and must not be optimized for brevity. The user should be able to read it as the main human-facing record of the episode without opening the JSON files for substantive understanding.

Preserve the fantasy-relevant content as fully as practical, including:

- the episode topic and current context
- the hosts' central arguments and evaluation criteria
- reasoning chains, not only conclusions
- important positive, negative and uncertain statements
- host agreements and disagreements
- rankings, tiers, boards, buckets or categories when present
- players, teams, positions, coaches and scheme context when fantasy-relevant
- redraft, dynasty, rookie-draft, bestball, scoring or market distinctions
- strategy implications stated by the source
- source-level conclusion
- a complete entity and mention register at the end

The structure must adapt to the content of the episode. Do not force a news episode, interview, mock draft, ranking show and strategy discussion into the same rigid set of headings.

For ranking, tier, mock-draft or list episodes:

- reproduce the complete source ordering or tier structure when it can be reconstructed safely
- give every ranked subject enough explanation to preserve the source case and risk
- preserve host disagreements and alternative orders
- include source-derived closing views by different criteria when the material supports them, for example highest conviction, best opportunity, best talent/upside, best immediate role, strongest dynasty profile, strongest redraft profile, sleepers, format-dependent profiles, fades or major uncertainty
- do not manufacture category rankings that the episode does not support

For other episode formats, organize around the actual themes, news blocks, debates, teams, positions, strategy questions or interview topics.

Repetition may be reduced, but not at the cost of losing distinct arguments, caveats, rankings, comparisons or dissenting host opinions.

It must not contain internal extraction metadata, such as:

- file inventories
- take IDs
- source package paths
- extraction status flags
- machine-readable companion file references
- Mighty Giants recommendations
- league-specific advice not stated by the source

Keep it inside the source perspective.

## Complete mention register in `episode.md`

End every schema-version-2 `episode.md` with a complete, human-readable entity and mention register.

The register must include every non-false-positive player mention found during the coverage sweep, including:

- ranking subjects
- players with substantive takes
- news subjects
- player comparisons
- teammates and depth-chart competitors
- injury or scheme context
- historical or passing references
- unresolved transcript names

The register should explain the role of the mention, for example:

- `ranking subject`
- `substantive evaluation`
- `comparison for Player X`
- `depth-chart context`
- `injury context`
- `passing reference`
- `unresolved transcript mention`

Other fantasy-relevant named entities such as coaches, teams or colleges may also be included when useful.

The mention register is an audit aid, not a substitute for detailed sections or takes.

## `takes.json` rule

`takes.json` contains structured podcast statements from the episode.

Use these top-level categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Category meanings:

- `players`: specific player statements.
- `teams`: NFL team, depth chart, team environment or team position-group statements.
- `positions`: position-group statements such as WR, RB, TE or QB.
- `nfl`: general NFL, draft, coaching, scheme or league-context statements.
- `fantasy`: fantasy strategy, scoring, redraft, dynasty, rookie draft, bestball, market or format statements.
- `other`: source statements that do not fit cleanly elsewhere.

Every player take object must include `raw_entity_mention`, `entity` and compact `entity_resolution` inline. If a player identity is not confirmed, `entity` must be `null` and `entity_resolution.status` must be `ambiguous` or `unresolved`.

Create a standalone take for:

- every ranking or tier subject
- every explicit sleeper, fade, buy, sell, hold or watchlist subject
- every player or entity with a substantive positive, negative or uncertain evaluation
- every independent role, injury, market, strategy or format thesis
- every meaningful host disagreement when it changes the evaluation

A player or entity may have multiple takes when the episode makes materially different claims. Do not collapse ranking, role, injury, market and format claims into one overly short take when they are independently useful.

Pure comparisons, depth-chart names, historical references and passing mentions do not automatically need standalone takes. They must still be recorded in `mentions.json` and may link to the surrounding take.

Do not split every take into a separate JSON file by default.

Use one `takes.json` per episode unless there is a clear practical reason to split it.

## `mentions.json` rule

`mentions.json` is required for schema-version-2 packages.

It is created from a separate second pass over the raw transcript after the main content extraction.

Record every unique player mention, even when the player appears only as:

- a comparison
- a teammate
- a depth-chart competitor
- injury context
- scheme context
- historical reference
- passing reference
- an unresolved possible player name

Also record other named entities when they carry fantasy-relevant source content.

Each mention must include:

- one or more raw transcript forms
- canonical entity or `null`
- entity type
- compact entity resolution
- one or more mention types
- one or more occurrences with timestamp or section context
- coverage in `episode.md`
- whether a standalone take is required
- linked take IDs when applicable

Use these mention types:

- `ranking_subject`
- `substantive_take`
- `news_subject`
- `player_comparison`
- `depth_chart_context`
- `injury_context`
- `scheme_context`
- `historical_reference`
- `passing_reference`
- `unresolved`
- `false_positive`

A `ranking_subject`, `substantive_take` or `news_subject` requires a standalone take.

A `false_positive` should be used only when the second pass identifies a transcript token as a likely name that is not actually an entity. It should not be combined with normal mention types.

Every non-false-positive mention must appear in the complete mention register in `episode.md`.

## Two-pass extraction and coverage audit

Every schema-version-2 extraction uses at least two distinct passes over the raw source.

### Pass A: content extraction

Create the detailed `episode.md` and structured `takes.json` from the fantasy-relevant content.

### Pass B: independent entity-mention sweep

Read the raw source again with a different objective:

1. collect every player name and possible player name
2. collect other named entities carrying fantasy-relevant content
3. resolve or preserve uncertainty
4. classify each mention's role
5. compare the mention register with `episode.md` and `takes.json`
6. add missing subjects, takes, sections or unresolved entries

Do not perform Pass B only by re-reading the already produced summary. It must use the raw transcript.

The audit is complete only when:

- all non-false-positive mentions appear in `episode.md`
- all required standalone subjects have linked takes
- all player takes are represented in `mentions.json`
- unresolved possible player names remain visible
- `index.json` records `coverage_audit.status: completed`
- `mention_counts.uncovered` and `coverage_audit.uncovered_mentions` are both zero

## `index.json` rule

`index.json` is the local technical package map.

It may contain:

- package schema version
- source id
- episode id
- episode number
- title
- dates
- local package paths
- raw status
- take counts by category
- mention coverage counts
- identity-resolution status
- coverage-audit status
- extraction status

For schema-version-2 packages it must reference `mentions.json` and record:

- total mentions
- resolved, ambiguous and unresolved counts
- ranking-subject count
- substantive-subject count
- context-only count
- mentions with take links
- uncovered count
- coverage-audit method and status

Keep this metadata out of `episode.md`.

## JSON formatting rule

Fantasy Management JSON artifacts that are created or manually maintained by AI must be human-readable and pretty-printed.

Use:

- UTF-8 text
- two-space indentation
- one property per line
- arrays on multiple lines, including single-item arrays
- exactly one array item per line
- nested arrays and objects on separate lines
- stable key order within the same file type when practical
- trailing newline at end of file

Do not use inline arrays in Fantasy Management JSON when practical.

Compact one-line JSON is only acceptable for generated application/runtime data outside Fantasy Management when the generator owns the format.

## Raw source rule

Store raw transcripts or raw notes unchanged under the episode package.

Do not clean, rewrite or normalize the raw source file.

If a single large raw file cannot be committed, split the raw transcript into ordered parts and create `raw/manifest.md`. The ordered concatenation of the parts is the raw source for that episode.

A placeholder raw file is not a completed raw source. If the full raw source is missing, mark the package as incomplete in `index.json`.

## Knowledge separation rule

Do not treat podcast takes as active Knowledge just because they exist.

After extraction, a separate Knowledge derivation step may decide which takes matter for:

- players
- NFL teams
- positions
- NFL context
- fantasy strategy

Knowledge belongs under:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

A redraft-only take may stay only in the episode package if it does not matter for our Dynasty league.

If a redraft take affects market value, it may become fantasy-market knowledge rather than player-quality knowledge.

## Completeness gate

Before marking a schema-version-2 episode extraction as complete, verify:

1. raw source is present or clearly marked in `index.json`
2. `episode.md` is a detailed German podcast preparation without internal metadata or Mighty Giants recommendations
3. `episode.md` preserves the episode's fantasy-relevant reasoning, caveats, disagreements, rankings and format distinctions without an artificial brevity target
4. ranking, tier, mock-draft or list episodes contain the complete safely reconstructable source order and enough explanation for every ranked subject
5. source-derived category rankings or favorite lists are included when supported by the episode, but are not invented when unsupported
6. `takes.json` exists and uses the six standard categories
7. every player take in `takes.json` has inline `raw_entity_mention`, `entity` and compact `entity_resolution`
8. every ranking subject, substantive evaluation and news subject has a standalone take
9. independent claims are not collapsed into an unusably short take merely for compactness
10. team/depth-chart statements are represented under `teams`
11. position-group statements are represented under `positions`
12. fantasy strategy and format statements are represented under `fantasy`
13. cautious, negative, uncertainty and host-disagreement takes are extracted, not only positive takes
14. `mentions.json` exists and conforms to the mention schema
15. a second raw-transcript entity-mention sweep was completed independently from the main extraction
16. every player mention is recorded, including comparisons, competitors, teammates, passing references and unresolved possible names
17. every non-false-positive mention appears in the complete mention register in `episode.md`
18. every required standalone mention links to an existing take
19. every player take is covered by at least one mention entry
20. transcript aliases, nicknames and unresolved entity names were reviewed
21. all important player takes either use verified canonical full names or have explicit `ambiguous`/`unresolved` entity resolution inline
22. confirmed recurring player aliases were added to `fantasy-management/_ai/entity-resolution/player_identity_registry.json`, if any exist
23. `index.json` records take counts, mention counts, identity-resolution status and coverage-audit status
24. `coverage_audit.status` is `completed`
25. `mention_counts.uncovered` and `coverage_audit.uncovered_mentions` are zero
26. JSON files are pretty-printed with the formatting rule above
27. any Knowledge derivation is either not started or explicitly stored separately under `knowledge/`
28. the package validator and coverage validator pass

If any required item fails, mark the package as `incomplete` or `needs_rework` in `index.json` and explain what is missing.

Legacy schema-version-1 packages may remain valid historical packages without `mentions.json`, but they do not provide the same coverage guarantee and should be reworked before being treated as fully audited.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, source context, derived Knowledge and current market/news context when relevant.
