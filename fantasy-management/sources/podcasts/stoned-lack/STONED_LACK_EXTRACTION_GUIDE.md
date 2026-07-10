# Stoned Lack Extraction Guide

Purpose: source-specific notes for extracting Stoned Lack podcast episodes.

The shared podcast structure is defined centrally in:

- `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`
- `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`
- `fantasy-management/_ai/templates/podcast/`

This guide only adds Stoned Lack-specific extraction notes.

## Core principle

Stoned Lack extraction creates a podcast source package, not active Knowledge and not a Mighty Giants recommendation.

Current source package:

```text
sources/podcasts/stoned-lack/episodes/YYYY/sl_XXXX/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  mentions.json
  index.json
```

Legacy packages may not contain `mentions.json` until they are fully reworked.

## `episode.md`

`episode.md` must be a detailed German preparation of the fantasy-relevant podcast content.

It should be the primary human-readable record of the episode, not a short executive summary. Preserve enough explanation that the user can understand the arguments, rankings, caveats and host differences without reading `takes.json`.

Do not impose a fixed length or one rigid structure. Stoned Lack episodes can be rankings, news shows, team-by-team draft reviews, strategy discussions, mocks or mixed formats. Organize the Markdown around the actual episode.

It must not contain:

- internal extraction metadata
- take IDs
- file inventories
- technical package paths
- `global_index_update`
- Mighty Giants recommendations
- 6-team or league-specific recommendations not stated by the hosts

It may and usually should contain:

- episode topic and current context
- hosts' central arguments and evaluation criteria
- all fantasy-relevant news blocks
- complete board, tier or ranking logic when present
- detailed player sections
- team and depth-chart context
- position-group context
- fantasy strategy from the source perspective
- format distinctions
- host agreements and disagreements
- positives, risks and uncertainty
- source-derived rankings by different criteria when supported by the episode
- source-level conclusion
- complete entity and mention register

For ranking or tier episodes, include every safely reconstructable ranked player. Give important players detailed profiles and lower-tier players enough explanation to preserve why they were placed there. Do not silently omit a low-ranked or negative player because the take seems unimportant.

When the source supports them, close with alternative source-derived views such as:

- highest host conviction
- best opportunity
- best talent or upside
- strongest immediate role
- strongest dynasty or redraft signal
- best sleepers or dart throws
- return- or scoring-dependent profiles
- biggest fades or risks
- strongest host disagreements

Do not force these lists into episodes that do not provide enough material.

## `takes.json`

Store all structured Stoned Lack source takes for the episode in one categorized `takes.json`.

Use the shared categories:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Do not create one JSON file per take by default.

For every player take, include these fields inline in the take object:

- `raw_entity_mention`
- `entity`
- `team`
- `position`
- compact `entity_resolution`

Create a take for every ranked subject, substantive player evaluation, news subject, sleeper, fade, buy/sell/hold/watchlist call and independent role, injury, market or format thesis.

A player may need multiple takes when Stoned Lack makes separate claims about ranking, role, immediate value, long-term value or format dependence. Takes can remain concise, but they must not become so compressed that distinct arguments or host disagreement disappear.

Pure comparison names, teammates, competitors and passing references do not automatically need their own take. They still belong in `mentions.json`.

Do not use a separate companion `entity_resolution.json` file as the target pattern for new Stoned Lack extractions.

## `mentions.json`

Create `mentions.json` in a second pass over the raw Stoned Lack transcript.

Record every player name or possible player name, including:

- every player in a ranking, tier, board or mock
- every player with a positive, negative or uncertain evaluation
- news subjects
- player comparisons
- teammates and depth-chart competitors
- injury or scheme context
- historical references
- passing mentions
- transcript forms that remain ambiguous or unresolved

Also include coaches, teams, colleges or other entities when they carry fantasy-relevant source context.

Stoned Lack's automatic German transcripts frequently distort English names. The mention sweep must therefore search for phonetic name-like phrases, not only correctly spelled names.

Classify each occurrence so that a low-value comparison is not mistaken for a full player recommendation.

A ranking subject, substantive take or news subject must link to a standalone take. Context-only mentions may link to the surrounding take or remain register-only.

Every non-false-positive player mention must appear in the complete mention register at the end of `episode.md`.

## Stoned Lack extraction focus

When processing a Stoned Lack transcript, extract:

1. player evaluations
2. full rankings, tiers, boards and mock-draft orders when present
3. team/depth-chart context
4. position-group takes
5. rookie draft strategy
6. redraft vs dynasty splits
7. buy/sell/hold/fade/watchlist language
8. format-dependent notes
9. caution and uncertainty buckets
10. host disagreements and changing opinions
11. all fantasy-relevant news segments
12. unresolved transcript names
13. source-level conviction and sentiment
14. category-specific source rankings when supported

## Entity resolution

Automatic German transcripts often break English NFL player names, and German hosts may also use only last names, shortened names, college references or informal phrasing.

Before processing the episode, load the podcast-independent player identity registry:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Use context to resolve names:

- position
- NFL team
- college
- draft round
- landing spot
- teammates
- competition
- episode section
- surrounding ranking tier
- comparison player

Verify decision-relevant names before using them as canonical entities.

Recommended identity-verification priority:

1. official NFL/team pages
2. NFL.com Draft Tracker
3. official college/athletics pages
4. Pro Football Reference / Sports Reference
5. ESPN / Sleeper / FantasyPros / KeepTradeCut for fantasy context, not primary identity

## Compact player-name quality gate

Do not treat a Stoned Lack player take or mention as complete when the player name is only a surname, a likely mistranscription or a guessed full name.

Bad final entities include examples like:

- `Price` when the take is about a Seattle RB and the full player identity must be resolved.
- `Jeremy Love` when the context indicates a similar but different canonical player name.

In these cases, either verify the canonical full player name from context, registry and external identity sources, or keep the entity unresolved.

A normal resolved player take or mention should use compact resolution:

```json
"raw_entity_mention": "Price",
"entity": "Jadarian Price",
"team": "SEA",
"position": "RB",
"entity_resolution": {
  "status": "confirmed",
  "method": "registry",
  "confidence": "high"
}
```

Use optional detail fields such as `reason`, `candidates` and `verified_sources` only when the mapping is ambiguous, unresolved, newly verified or otherwise not self-explanatory.

An unresolved mention should not pretend certainty:

```json
"raw_entity_mentions": [
  "Price"
],
"entity": null,
"entity_resolution": {
  "status": "unresolved",
  "method": "none",
  "confidence": "low",
  "reason": "Surname-only transcript mention; context was insufficient or verification was not completed."
}
```

## Alias handling

Stoned Lack is German-language fantasy content about mostly English player, team and college names. Watch especially for:

- phonetic German transcript variants of English names
- missing suffixes such as `Jr.`
- confused similar first/last names
- college-only references in rookie discussions
- nicknames, shortened names and host-specific wording
- multiple distorted variants of the same player across one episode

Do not change raw transcript wording.

If a mapping is likely but not certain, keep the entity unresolved or mark confidence as low.

If a recurring player alias or transcript error is confirmed, store it in:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Do not maintain a separate Stoned Lack-only alias index unless the user explicitly asks for source-local aliases.

## Two-pass Stoned Lack workflow

### Pass A: detailed content extraction

Read the complete raw transcript and create:

- detailed `episode.md`
- complete `takes.json`
- initial entity resolution

### Pass B: independent name and coverage sweep

Read the raw transcript again from beginning to end and focus only on:

- every name-like player mention
- recurring transcript distortions
- ranking membership
- comparison and depth-chart context
- mentions missing from `episode.md`
- required takes missing from `takes.json`
- unresolved names that were accidentally discarded

Create `mentions.json`, reconcile all missing coverage and only then mark the audit complete.

Do not use the already-written `episode.md` as the sole input for Pass B.

## Completeness gate

A schema-version-2 Stoned Lack episode package is complete when:

1. raw source is present in `raw/` and referenced in `raw/manifest.md` and `index.json`
2. `episode.md` is a detailed German source preparation without internal metadata or league-specific recommendations
3. the Markdown structure fits the actual episode format rather than a rigid universal outline
4. ranking/list episodes include every safely reconstructable ranked player and preserve the source order or tiers
5. important players receive detailed source cases, risks and host differences
6. source-supported closing rankings by different criteria are included when applicable
7. all fantasy-relevant news and strategy blocks are represented
8. `takes.json` exists and uses all six shared categories
9. every player take has inline `raw_entity_mention`, `entity` and compact `entity_resolution`
10. every ranked subject, substantive evaluation and news subject has a suitable take
11. distinct ranking, role, injury, market and format claims are not improperly collapsed
12. team/depth-chart statements are represented under `teams`
13. position-group statements are represented under `positions`
14. fantasy strategy and format statements are represented under `fantasy`
15. cautious, negative, uncertainty and disagreement takes are included, not only positive takes
16. `mentions.json` exists and contains every player mention or possible player mention from the independent second pass
17. comparisons, teammates, competitors and passing references are classified rather than silently dropped
18. every non-false-positive mention appears in the complete mention register in `episode.md`
19. every mention requiring a standalone take links to an existing take
20. every player take is covered by a mention entry
21. unresolved or low-confidence identities remain visible
22. recurring transcript aliases were reviewed and confirmed mappings were stored centrally, if any exist
23. `index.json` records package paths, raw status, take counts, mention counts, identity-resolution status and coverage-audit status
24. `coverage_audit.status` is `completed`
25. uncovered mention count is zero
26. no active Knowledge or Mighty Giants recommendations are mixed into the source package
27. package and coverage validators pass

Legacy packages without `mentions.json` do not have the same completeness guarantee and should be reworked before being treated as fully audited.

## Knowledge handoff

After extraction, a separate Knowledge derivation step may read the episode package and decide what applies to:

- `fantasy-management/knowledge/players/`
- `fantasy-management/knowledge/teams/`
- `fantasy-management/knowledge/positions/`
- `fantasy-management/knowledge/nfl/`
- `fantasy-management/knowledge/fantasy/`

Do not copy every Stoned Lack take or mention into Knowledge. Redraft-only, comparison-only or otherwise irrelevant material may stay only in the source package.
