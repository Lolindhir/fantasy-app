# StonedLack Extraction Guide

Purpose: define a stable extraction format for StonedLack podcast transcripts.

The goal is to create reusable source data for Dynasty/Fantasy Football analysis, meta-rankings and AI-assisted evaluations.

## 1. Core principle

Document every episode in five layers:

1. Raw transcript
2. German ai-input-style Markdown episode analysis
3. Player/entity data JSON
4. Machine-readable episode JSON
5. Atomic source take files plus German take index

The central user-facing object is the German episode analysis: it should be readable and useful on its own.

The central machine-readable objects are:

- player/entity data JSON for aggregation
- atomic takes for evidence and knowledge-layer updates

## 2. Standard episode paths

```text
raw_transcripts/YYYY/YYYY-MM-DD_sl_EPISODE_slug.raw.md
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug.md
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug.json
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug_player_data.json
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug_take_index.md
```

Example:

```text
raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.md
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.json
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking_player_data.json
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking_take_index.md
```

Short legacy names such as `sl_0569.md`, `sl_0569.json` and `sl_0569_player_data.json` are acceptable if already used for the episode.

## 3. Slug rules

Use short, stable slugs:

- lowercase
- words separated by `_`
- no umlauts
- no special characters
- descriptive topic

Examples:

- `rookie_wr_ranking`
- `rookie_rb_ranking`
- `startup_mock`
- `nfl_news_adp`
- `redraft_preview`
- `week_1_reactions`

## 4. Raw transcript rules

The raw transcript is the primary audit trace and must not be cleaned.

Preserve:

- chapter headings
- timestamps
- transcription errors
- repetitions
- filler words
- off-topic passages
- speaker changes when available

Allowed addition: a YAML frontmatter block at the start.

```yaml
---
episode_id: sl_0571
episode_number: 571
source_name: StonedLack
source_type: youtube_transcript
published_date: YYYY-MM-DD
processed_date: YYYY-MM-DD
language: de
raw_transcript_status: verbatim_user_paste
notes:
  - "Automatic transcript; names may be wrong."
---
```

Do not overwrite raw files. If a better transcript appears later, create a versioned file such as:

```text
raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.v2.md
```

A placeholder raw transcript is not a completed extraction. If the full raw transcript is missing, mark the episode extraction as incomplete and do not treat notes, takes or current views as complete.

If a single large raw transcript cannot be written through the connector, split it into ordered part files and create a raw manifest. The manifest must make clear that the ordered parts together are the raw source.

## 5. Extraction tasks

For a new transcript, the agent should:

1. identify or infer episode metadata from the provided context
2. save the raw transcript unchanged, either as one file or as ordered raw parts plus manifest
3. identify chapters and topic blocks
4. extract player, team, coach, format and strategy mentions
5. clean and map broken transcript names
6. verify names when decision-relevant
7. extract rankings, tiers, sleepers, buy/sell/fade/watchlist takes
8. mark implicit takes only when clearly supported
9. store arguments, risks, context and uncertainty
10. separate source statement from agent interpretation
11. create the German ai-input-style Markdown episode analysis
12. create the player/entity data JSON when the episode has reusable player, team, ranking, board or tier content
13. create the episode JSON and link companion files
14. create atomic take files
15. create a German take index when there are many takes
16. update current source views when requested or when the extraction should feed reusable knowledge
17. update alias and index files when needed
18. run the completeness gate before marking the extraction as complete

## 6. German ai-input-style Markdown standard

For StonedLack, the Markdown episode analysis should follow the quality level of the older `ai-input` episode writeups.

It must be written in German and should usually include:

1. Quellenhinweis und Bereinigung
2. Interpretation der Folge
3. zentrale Podcast-Philosophie / Bewertungslogik
4. bereinigte Board-, Ranking- oder Tierlogik
5. Podcast-Favoriten nach Kategorie, when supported
6. Sleepers / Buy / Sell / Hold / Fade / Watchlist / Caution Buckets
7. detailed player or entity profiles
8. strategic rookie-draft, trade, redraft, dynasty or format notes
9. league-format reuse notes, especially 6-team / 2QB / 2TE / 4Flex when relevant
10. short source conclusion
11. linked machine-readable files

Detailed player profiles should normally use this pattern:

```markdown
## Player Name

**Tier:** ...  
**Podcast-Rolle:** ...  
**Sentiment:** ...

### Begründung aus Podcast-Kontext

- ...

### Positiv

- ...

### Negativ / Risiko

- ...

### Analyse-Tags

`tag`, `tag`, `tag`
```

Do not replace this with only short tables when the transcript contains enough substance for profile sections.

## 7. Player/entity data JSON standard

For full ranking, draft-review, rookie-board, landing-spot or player-preview episodes, create a companion file such as:

`episodes/YYYY/sl_0569_player_data.json`

It should contain:

- `metadata`
- `schema`
- `players` or `entities`
- optional `category_rankings`

Recommended player/entity fields:

- `rank`
- `name`
- `position`
- `team`
- `stonedlack_tier`
- `source_conviction`
- `sentiment`
- `main_argument`
- `opportunity`
- `short_term_value`
- `long_term_value`
- `risk`
- `format_dependency`
- `take_ids`
- `tags`
- `notes`
- `identity_confidence` or `verification_status` when needed

The player data JSON is not a replacement for atomic takes. It is an aggregation-friendly profile layer.

## 8. Completeness gate

A StonedLack extraction is not complete until these checks pass:

1. Raw transcript is present and not a placeholder.
2. If raw is split, the manifest lists all parts in order and the episode JSON states the split raw status.
3. Episode note is a German ai-input-style analysis, not just a short summary.
4. Episode note contains source-note/cleanup, overview, source philosophy, explicit rankings/tiers when present, sleepers/buy/sell/fade/watchlist, player profiles, strategy takes, format-dependent notes, uncertainties and Mighty Giants reuse notes where applicable.
5. Every player listed as high-signal in the episode note has one or more atomic take files, or a clear explanation why no take was created.
6. Every high-signal player/entity is represented in the player/entity data JSON when such a file is required.
7. Negative, cautious, fade, avoid and uncertainty takes are extracted, not only positive takes.
8. Broad strategy points are extracted as dedicated takes when reusable.
9. Episode JSON includes all take IDs, companion files and the player/entity data path when present.
10. The take count is plausible for the transcript scope. Full draft-review, ranking or rookie-board episodes normally require many more than three takes.
11. Important unresolved names are listed with original transcript form, guessed canonical name and confidence.
12. Current knowledge views are updated when the extraction is intended to feed later analysis.

If any check fails, set status to `needs_rework` or `incomplete` and document missing work in the episode note.

## 9. No hallucination rule

Do not invent missing details.

Use:

- `unknown`
- `unresolved`
- `unverified`
- `low confidence`

Add unresolved issues to the Markdown source note or entity companion file.

Do not add prominent players from other episodes merely because they are important. If they are not clearly mentioned in the current transcript, leave them out unless the user asks for a non-mention note.

## 10. Entity resolution

Automatic transcripts often break player names.

For each important entity:

1. store original transcript form
2. identify phonetic variants
3. use context: position, team, college, draft round, landing spot, teammates and competition
4. verify through current sources when important
5. store canonical name
6. set confidence

Recommended identity-verification priority:

1. official NFL/team pages
2. NFL.com Draft Tracker
3. official college/athletics pages
4. Pro Football Reference / Sports Reference
5. ESPN / Sleeper / FantasyPros / KeepTradeCut for fantasy context, not primary identity

## 11. Take model

A take may be:

- player evaluation
- ranking
- tier
- sleeper
- buy
- sell
- hold
- fade
- watchlist
- trade strategy
- draft strategy
- rookie draft value
- redraft value
- bestball value
- dynasty value
- injury reaction
- depth chart projection
- role projection
- coaching scheme
- news reaction
- market/ADP note
- format note
- league settings note
- meta strategy
- uncertainty note

Take files should use stable IDs and file names such as `sl_0569_t001.json`, `sl_0569_t002.json`, etc.

## 12. Fantasy context values

Allowed values include:

- `dynasty`
- `rookie_draft`
- `startup`
- `redraft`
- `bestball`
- `waiver`
- `trade`
- `devy`
- `general_fantasy`
- `real_football`
- `unknown`

## 13. Evaluation scales

Sentiment:

- `very_positive`
- `positive`
- `mixed`
- `cautious`
- `negative`
- `very_negative`
- `neutral`

Conviction:

- `very_high`
- `high`
- `medium`
- `low`
- `very_low`
- `unknown`

Action:

- `draft`
- `reach`
- `buy`
- `sell`
- `hold`
- `fade`
- `avoid`
- `watch`
- `stash`
- `handcuff`
- `trade_for`
- `trade_away`
- `do_not_overpay`
- `no_action`
- `unknown`

Time horizon:

- `immediate`
- `early_season`
- `full_season`
- `long_term`
- `multi_year`
- `unknown`

## 14. Evidence rule

Every important take should include evidence.

Evidence may be:

1. a short transcript excerpt
2. a paraphrased statement with timestamp
3. a chapter or time range

Avoid long quotes. Prefer short paraphrases.
