# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for Stoned Lack, Down Set Talk, Football Bromance and future podcast sources.

The detailed source/Knowledge/Analysis separation is defined in:

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

The registry is not a source take, Knowledge, a ranking or a recommendation.

Add confirmed reusable aliases or transcript-error mappings when discovered. Do not add speculative mappings.

## Entity aliases and transcript name resolution

Raw source text must stay unchanged. Do not rewrite transcript wording.

In `episode.md`, use canonical names only when confidence is sufficient. Do not expose raw aliases, resolution methods or confidence metadata solely for audit purposes.

In `takes.json` and `mentions.json`, preserve the raw mention and compact resolution metadata.

For every player take, `takes.json` must include:

- `raw_entity_mention`
- verified canonical `entity`, otherwise `null`
- compact `entity_resolution`

Allowed resolution methods:

- `registry`
- `external_verification`
- `context_inference`
- `manual_confirmation`
- `none`, only for unresolved entities

Allowed statuses:

- `confirmed`
- `ambiguous`
- `unresolved`

Ambiguous and unresolved entries use `entity: null` and explain the uncertainty when useful.

Do not invent or autocomplete names from memory. A plausible-looking name is still wrong when it is not verified against the raw context, registry or an appropriate identity source.

## Episode package rule

Each current processed episode is one package:

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

For small transcripts, `raw/source.md` may replace split parts.

New and fully reworked packages use `package_schema_version: 2`.

## Required outputs

A normal schema-version-2 extraction creates:

1. unchanged raw source material
2. `episode.md` as detailed German reader-facing preparation
3. `takes.json` as structured source takes
4. `mentions.json` as the complete technical entity and coverage audit
5. `index.json` as package metadata, counts and status

Do not update global indexes or active Knowledge during normal extraction.

## `episode.md` rule

`episode.md` is the primary human-readable record of the episode.

It is not a short executive summary and must not be optimized for brevity. Preserve the fantasy-relevant content as fully as practical:

- episode topic and context
- hosts' central arguments and evaluation criteria
- reasoning chains, not only conclusions
- positive, negative and uncertain statements
- agreements and disagreements
- complete safely reconstructable rankings, tiers, boards or mock-draft structures
- player, team, position, coach and scheme context needed to understand the source
- format distinctions
- strategy implications stated by the source
- source-level conclusion

For ranking, tier, mock-draft or list episodes:

- reproduce the complete safely reconstructable source order
- explain every ranked subject sufficiently
- preserve positive cases, risks, uncertainty and host differences
- preserve format dependency
- include source-derived closing views only when the episode supports them

For mixed episodes, include all substantive segments, including news, rankings and live drafts. Do not silently stop processing when the headline segment ends.

`episode.md` must not contain technical extraction metadata:

- file inventories
- raw-name or alias registers
- entity-resolution status or confidence
- complete mention or coverage tables
- take or mention IDs
- technical timestamp appendices
- package paths
- extraction, review or validator status
- machine-readable companion-file references
- Mighty Giants recommendations
- league-specific advice not stated by the source

## Reader-facing coverage rule

`episode.md` must include every ranking subject, news subject and substantive evaluation in enough detail to understand the source's argument.

Context-only entities appear naturally only when needed for the argument.

Do not append a complete technical entity or mention register. Passing references, historical comparisons, depth-chart names and unresolved transcript forms may remain exclusively in `mentions.json` when they add no substantive reader value.

## `takes.json` rule

Use one categorized `takes.json` per episode with these buckets:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Create standalone takes for:

- every ranking or tier subject
- every explicit recommendation label
- every substantive positive, negative or uncertain evaluation
- every independent role, injury, market, strategy or format thesis
- every meaningful disagreement
- substantive segments outside the headline topic, including a live mock draft

A take must preserve the source claim, reasoning, risks, formats, sentiment, conviction and evidence. Do not collapse materially distinct claims merely to reduce file size.

Pure comparisons, teammates, depth-chart competitors, historical examples and passing references do not automatically need standalone takes. They remain in `mentions.json`.

## `mentions.json` rule

`mentions.json` is the complete technical entity and coverage audit.

Create it in an independent second pass over the entire raw source, not by rereading only `episode.md` or `takes.json`.

Include every player mention or possible player mention and every other named entity carrying fantasy-relevant context, including:

- ranking subjects
- substantive takes
- news subjects
- comparisons
- teammates and competitors
- injury and scheme context
- historical examples
- live-draft names
- passing references
- ambiguous and unresolved transcript forms
- false positives when preserving them helps auditability

A ranking, substantive or news subject requires:

- a standalone take
- `coverage.episode_md: true`
- substantive reader-facing coverage

Context-only or unresolved mentions may use `coverage.episode_md: false` when intentionally audit-only. Add `coverage.note` explaining the omission.

The technical register belongs here, never in `episode.md`.

## Coverage audit rule

Schema-version-2 packages require at least two distinct passes.

### Pass A: content extraction

Read the entire raw source and create the detailed `episode.md` and `takes.json`.

### Pass B: independent entity sweep

Read the entire raw source again with a different objective:

1. collect every player name and possible player name
2. collect other fantasy-relevant named entities
3. resolve identities or preserve uncertainty
4. classify each mention
5. compare mentions with `episode.md` and `takes.json`
6. add omitted segments, subjects, takes or unresolved forms
7. calculate counts from the finished files

The audit is complete only when:

- all required subjects have valid standalone takes
- all required subjects are substantively covered in `episode.md`
- all player takes are covered by matching mention entries
- context-only and unresolved forms remain visible
- audit-only omissions have notes
- all links resolve
- calculated counts match `index.json`
- uncovered mentions equal zero

A package is complete only when `coverage_audit.status` is `completed`.

## `index.json` rule

`index.json` is the local technical map. It may contain:

- package schema version
- source and episode identity
- dates
- package paths
- raw status
- take and mention counts
- identity-resolution status
- coverage-audit status
- Knowledge derivation status
- rework notes

Keep all such metadata out of `episode.md`.

Recommended status conventions:

- `needs_review`: extraction exists but a required review, second pass or validator is open
- `needs_rework`: known substantive or structural defects remain
- `active_source_package`: all completeness gates pass and the package is usable as source evidence

Do not set `active_source_package` or `coverage_audit.status: completed` merely to silence a validator.

## JSON formatting rule

Fantasy Management JSON created or manually maintained by AI must be human-readable and pretty-printed:

- UTF-8
- two-space indentation
- one property per line
- arrays on multiple lines, including single-item arrays
- one array item per line
- nested arrays and objects on separate lines
- stable key order where practical
- trailing newline

Do not commit minified JSON or an entire object on one line.

## Raw source rule

Store raw transcripts or notes unchanged.

For split transcripts:

- use ordered `partNN.md` files
- list every part in `raw/manifest.md`
- require contiguous numbering
- treat ordered concatenation as the complete raw source

A placeholder raw file is not a completed source. Mark missing raw material explicitly in `index.json`.

## Knowledge separation rule

Podcast packages are source evidence, not active Knowledge.

Knowledge may be derived later under:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

A separate derivation step decides what remains useful for the league and current context.

## Completeness gate

Before marking a schema-version-2 package complete, verify:

1. raw source is complete and referenced
2. every raw part was read in Pass A
3. every raw part was read again in Pass B
4. `episode.md` is detailed German source preparation without technical metadata
5. all substantive episode segments are represented
6. complete rankings, tiers and mock-draft structures are preserved when safely reconstructable
7. every ranked subject has sufficient explanation
8. source reasoning, risks, disagreement and format distinctions are preserved
9. `takes.json` uses all six categories
10. player takes contain inline raw mention, canonical entity and resolution
11. all ranking, substantive and news subjects have standalone takes
12. materially distinct claims are not collapsed improperly
13. `mentions.json` conforms to its schema
14. every player mention or possible player mention from Pass B is registered
15. context, comparison, historical and unresolved mentions are retained
16. every required mention links to a valid take
17. every player take has a matching subject mention
18. calculated take and mention counts match `index.json`
19. uncovered mentions equal zero
20. JSON formatting follows the repository rule
21. recurring confirmed aliases are stored in the central registry
22. `coverage_audit.status` is `completed`
23. Knowledge derivation is absent or stored separately
24. package and coverage validators pass
25. validator unit tests pass

If any required item fails, use `needs_review` or `needs_rework` and document the blocker.

Legacy schema-version-1 packages may remain historical packages without `mentions.json`; they do not provide the same coverage guarantee.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, derived Knowledge, relevant source evidence and current market/news context.
