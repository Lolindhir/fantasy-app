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

Raw source text must stay unchanged. Do not rewrite raw transcript wording.

In `episode.md`, use the best canonical entity name only when confidence is sufficient. Do not expose raw transcript aliases, resolution methods or confidence metadata merely for audit purposes.

In `takes.json` and `mentions.json`, preserve the raw mention and compact entity-resolution metadata.

If a recurring player alias or transcript error is confirmed, store it in the central podcast-independent player identity registry. Use source-specific `SOURCE_NOTES.md` only for source quirks, pronunciation patterns and unresolved recurring issues.

Do not create or apply an alias mapping when the identity is uncertain. Leave the entity unresolved and mark the uncertainty explicitly in the machine-readable audit artifacts.

## Canonical player identity rule

Player identity resolution is a required extraction step, not a best-effort cleanup step.

For every player take, `takes.json` must include:

- `raw_entity_mention`: the name, nickname, surname or transcript phrase as heard or read in the raw source
- `entity`: the canonical full player name only when verified with sufficient confidence; otherwise `null`
- `entity_resolution`: compact inline status metadata for the mapping

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

Do not use a surname-only value as a finished player entity unless this is genuinely the verified public identity. For normal NFL player takes, a surname-only mention must be resolved to a canonical full name or marked unresolved.

Do not invent or auto-complete first names from memory. A plausible-looking full name is still wrong if it has not been verified against the episode context, registry or external identity sources.

For each high-signal player take, use source context before accepting a canonical player name:

- NFL team or landing spot
- position
- college
- draft round or pick range
- depth-chart context
- teammates or competitors mentioned nearby
- episode section and timestamp

Then verify decision-relevant identities against current external identity sources when available. Preferred order:

1. official NFL or team pages
2. NFL.com Draft Tracker or official draft material
3. official college or athletics pages
4. Pro Football Reference or Sports Reference
5. ESPN, Sleeper, FantasyPros, KeepTradeCut or similar fantasy sources only as supporting context, not primary identity proof

Use `entity_resolution.status`:

- `confirmed`: canonical full name is verified and matches podcast/source context
- `ambiguous`: likely candidates exist, but the source context is not enough to choose safely
- `unresolved`: no reliable mapping has been found

If status is `ambiguous` or `unresolved`, use `entity: null` and include useful candidate or reason notes in `entity_resolution`.

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

The structure must adapt to the content of the episode. Do not force a news episode, interview, mock draft, ranking show and strategy discussion into the same rigid set of headings.

For ranking, tier, mock-draft or list episodes:

- reproduce the complete source ordering or tier structure when it can be reconstructed safely
- give every ranked subject enough explanation to preserve the source case and risk
- include a positive case when the source provides one
- preserve host disagreements and alternative orders
- preserve format dependency and uncertainty
- include source-derived closing views by different criteria when the material supports them, such as highest conviction, best opportunity, best talent/upside, best immediate role, strongest dynasty profile, strongest redraft profile, sleepers, format-dependent profiles, fades or major uncertainty
- do not manufacture category rankings that the episode does not support

Repetition may be reduced, but not at the cost of losing distinct arguments, caveats, rankings, comparisons or dissenting host opinions.

It must not contain technical extraction metadata, including:

- file inventories
- raw-name or alias registers
- entity-resolution status or confidence
- complete mention or coverage tables
- take or mention IDs
- timestamps as a technical evidence appendix
- source package paths
- extraction, review or validator status flags
- machine-readable companion-file references
- Mighty Giants recommendations
- league-specific advice not stated by the source

Keep it inside the source perspective.

## Reader-facing coverage rule

`episode.md` must contain every ranking subject, substantive evaluation and news subject in sufficient detail to understand the source's argument.

Context-only entities should appear naturally when they are needed for that argument, for example a teammate, competitor, coach or team environment.

Do not append a complete technical entity or mention register to `episode.md`.

Passing references, historical references, context-only names and unresolved transcript forms may remain exclusively in `mentions.json` when they do not add substantive reader value.

## `takes.json` rule

`takes.json` contains structured podcast statements from the episode.

Use these top-level categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Create standalone takes for all ranking subjects, explicit recommendations or labels, substantive positive/negative/uncertain evaluations, independent role or injury theses, strategy or format theses, and meaningful disagreements.

Keep each take source-focused. Preserve the claim, reasoning, risks, sentiment, conviction, formats and evidence without adding Mighty Giants recommendations.

## `mentions.json` rule

`mentions.json` is the complete technical mention and coverage audit.

Create it in a second pass over the raw transcript, separate from the main content extraction.

It must include every player mention and other fantasy-relevant named entity, including:

- ranking subjects
- players with substantive takes
- news subjects
- player comparisons
- teammates and depth-chart competitors
- injury or scheme context
- historical or passing references
- unresolved transcript names

Every ranking subject, substantive take or news subject requires:

- a matching standalone take
- `coverage.episode_md: true`
- reader-facing substantive coverage in `episode.md`

Context-only or unresolved mentions may use `coverage.episode_md: false` when they are intentionally audit-only. Add a short `coverage.note` explaining that the reference is preserved in the technical audit but omitted from the reader-facing note because it adds no substantive content.

The complete technical register belongs here, not in `episode.md`.

## Coverage audit rule

Schema-version-2 packages require an independent second raw-transcript pass.

The audit must verify:

1. every possible player or relevant named entity was considered
2. every ranking, substantive or news subject has a matching standalone take
3. every required subject is substantively covered in `episode.md`
4. context-only and unresolved references remain visible in `mentions.json`
5. intentionally audit-only mentions are documented with a coverage note
6. false positives are marked and do not link to takes
7. calculated counts match `index.json`

A context-only mention is not uncovered merely because it is absent from `episode.md`, provided it is correctly represented in `mentions.json` and its intentional reader-facing omission is documented.

A package using schema version 2 is complete only when the audit status is `completed` and uncovered mentions equal zero.

## `index.json` rule

`index.json` is the local technical map for the episode package.

It may contain package schema version, source and episode identity, dates, file paths, take and mention counts, entity-resolution status, coverage-audit status, extraction status and rework notes.

Keep all such technical metadata out of `episode.md`.
