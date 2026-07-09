# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for Stoned Lack, Down Set Talk, Football Bromance and future podcast sources.

The detailed source/knowledge/analysis separation is defined in:

`fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`

## Core rule

Podcast extraction is source work, not final Fantasy Management analysis.

A podcast extraction answers:

> What did the podcast say?

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

In `episode.md` and `takes.json`, use the best canonical entity name only when confidence is sufficient. Preserve uncertainty in notes, tags, evidence or wording when the mapping is not fully resolved.

If a recurring player alias or transcript error is confirmed, store it in the central podcast-independent player identity registry above, not in a podcast-local alias file.

Use source-specific `SOURCE_NOTES.md` only for source quirks, pronunciation patterns and unresolved recurring issues. Use the central registry for confirmed mappings that may help future extraction across multiple sources.

Do not create or apply an alias mapping when the identity is uncertain. Leave the entity unresolved and mark the uncertainty in `takes.json`.

## Canonical player identity rule

Player identity resolution is a required extraction step, not a best-effort cleanup step.

For every player take, `takes.json` must include:

- `raw_entity_mention`: the name, nickname, surname or transcript phrase as heard/read in the raw source.
- `entity`: the canonical full player name, only when verified with sufficient confidence; otherwise `null`.
- `entity_resolution`: the resolution status, evidence and candidate reasoning.

Do not use a surname-only value such as `Price` as a finished player entity unless the take is explicitly about a one-name public entity and this is verified. For normal NFL player takes, a surname-only mention must be resolved to a canonical full name or marked unresolved.

Do not invent or auto-complete first names from memory. A plausible-looking full name is still wrong if it has not been verified against the episode context and external identity sources.

For each high-signal player take, use the podcast context before accepting a canonical player name:

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

If status is `ambiguous` or `unresolved`, do not write a confident canonical `entity`. Use `entity: null` and include candidate notes in `entity_resolution.candidates`.

A companion `entity_resolution.json` file is not a valid substitute for inline player resolution in `takes.json` for new or fully reworked packages. Companion files may exist only as temporary migration overlays for legacy packages, and such packages must not be marked fully complete until the player takes are fixed inline.

## Episode package rule

Each new processed podcast episode should be stored as one local package:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  index.json
```

For small transcripts, `raw/source.md` may replace split raw parts.

## Required default outputs

A normal podcast extraction creates:

1. raw source material under the episode package
2. `episode.md` as a clean German human-readable podcast summary
3. `takes.json` as structured source takes grouped by category, including inline player identity resolution for every player take
4. `index.json` as local technical metadata and package map

Do not update global indexes during normal podcast extraction.

Do not write source takes to any separate derived take area by default. Podcast takes are not Knowledge yet.

## `episode.md` rule

`episode.md` is the clean reader-facing podcast summary.

It should be good enough that the user could read it directly or publish it privately.

It must not contain internal extraction metadata, such as:

- file inventories
- take IDs
- source package paths
- extraction status flags
- machine-readable companion file references
- Mighty Giants recommendations

It may contain:

- episode topic and context
- the hosts' main arguments
- rankings, tiers, boards or categories from the podcast
- player/team/position sections
- podcast-level positives and risks
- source conclusion

Keep it inside the source perspective.

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

Every player take object must include `raw_entity_mention`, `entity` and `entity_resolution` inline. If a player identity is not confirmed, `entity` must be `null` and `entity_resolution.status` must be `ambiguous` or `unresolved`.

Do not split every take into a separate JSON file by default.

Use one `takes.json` per episode unless there is a clear practical reason to split it.

## `index.json` rule

`index.json` is the local technical package map.

It may contain:

- source id
- episode id
- episode number
- title
- dates
- local package paths
- raw status
- take counts by category
- identity-resolution status
- extraction status

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

Before marking an episode extraction as complete, verify:

1. raw source is present or clearly marked in `index.json`
2. `episode.md` is a clean German podcast summary without internal metadata
3. `takes.json` exists and uses the six standard categories
4. every player take in `takes.json` has inline `raw_entity_mention`, `entity` and `entity_resolution`
5. high-signal player statements are represented under `players`
6. team/depth-chart statements are represented under `teams`
7. position-group statements are represented under `positions`
8. fantasy strategy and format statements are represented under `fantasy`
9. cautious, negative and uncertainty takes are extracted, not only positive takes
10. transcript aliases, nicknames and unresolved entity names were reviewed
11. all important player takes either use verified canonical full names or have explicit `ambiguous`/`unresolved` entity resolution inline in `takes.json`
12. confirmed recurring player aliases were added to `fantasy-management/_ai/entity-resolution/player_identity_registry.json`, if any exist
13. `index.json` records counts by take category and identity-resolution status
14. JSON files are pretty-printed with the formatting rule above
15. any Knowledge derivation is either not started or explicitly stored separately under `knowledge/`

If any required item fails, mark the package as `incomplete` or `needs_rework` in `index.json` and explain what is missing.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, source context, derived Knowledge and current market/news context when relevant.
