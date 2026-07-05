# StonedLack Extraction Guide

Purpose: define a stable extraction format for StonedLack podcast transcripts.

The goal is to create reusable source data for Dynasty/Fantasy Football analysis, meta-rankings and AI-assisted evaluations.

## 1. Core principle

Document every episode in three layers:

1. Raw transcript
2. Readable Markdown source note
3. Machine-readable JSON take file

The central object is the take: a concrete Fantasy/Dynasty statement from the episode.

## 2. Standard episode paths

```text
raw_transcripts/YYYY/YYYY-MM-DD_sl_EPISODE_slug.raw.md
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug.md
episodes/YYYY/YYYY-MM-DD_sl_EPISODE_slug.json
```

Example:

```text
raw_transcripts/2026/2026-05-11_sl_0571_rookie_rb_ranking.raw.md
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.md
episodes/2026/2026-05-11_sl_0571_rookie_rb_ranking.json
```

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

## 5. Extraction tasks

For a new transcript, the agent should:

1. identify or infer episode metadata from the provided context
2. save the raw transcript unchanged
3. identify chapters and topic blocks
4. extract player, team, coach, format and strategy mentions
5. clean and map broken transcript names
6. verify names when decision-relevant
7. extract rankings, tiers, sleepers, buy/sell/fade/watchlist takes
8. mark implicit takes only when clearly supported
9. store arguments, risks, context and uncertainty
10. separate source statement from agent interpretation
11. create the Markdown source note
12. create the JSON take file
13. update alias and index files when needed
14. run the completeness gate before marking the extraction as complete

## 6. Completeness gate

A StonedLack extraction is not complete until these checks pass:

1. Raw transcript is present and not a placeholder.
2. Episode note contains source-note/cleanup, verified entity mappings, overview, source philosophy, explicit rankings/tiers, sleepers/buy/sell/fade/watchlist, player profiles, strategy takes, format-dependent notes, uncertainties and Mighty Giants reuse notes where applicable.
3. Every player listed as high-signal in the episode note has one or more atomic take files, or a clear explanation why no take was created.
4. Negative, cautious, fade, avoid and uncertainty takes are extracted, not only positive takes.
5. Broad strategy points are extracted as dedicated takes when reusable.
6. Episode JSON includes all take IDs and relevant entities.
7. The take count is plausible for the transcript scope. Full draft-review, ranking or rookie-board episodes normally require many more than three takes.
8. Important unresolved names are listed with original transcript form, guessed canonical name and confidence.
9. Current knowledge views are updated when the extraction is intended to feed later analysis.

If any check fails, set status to `needs_rework` or `incomplete` and document missing work in the episode note.

## 7. No hallucination rule

Do not invent missing details.

Use:

- `unknown`
- `unresolved`
- `unverified`
- `low confidence`

Add unresolved issues to the Markdown source note.

## 8. Entity resolution

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

## 9. Take model

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

## 10. Fantasy context values

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

## 11. Evaluation scales

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

## 12. Evidence rule

Every important take should include evidence.

Evidence may be:

1. a short transcript excerpt
2. a paraphrased statement with timestamp
3. a chapter or time range

Avoid long quotes. Prefer short paraphrases.

## 13. Markdown source-note structure

Use this structure when appropriate:

```markdown
# StonedLack Podcast [Episode] – [Topic]

## 1. Source note and cleanup
## 2. Verified entity mappings
## 3. Episode overview
## 4. Source philosophy / evaluation logic
## 5. Explicit rankings / tiers
## 6. Sleepers / Buy / Sell / Fade / Watchlist
## 7. Player profiles
## 8. Strategy takes
## 9. Format-dependent notes
## 10. Uncertainties
## 11. Reuse notes for Mighty Giants
```

For draft-review, ranking, rookie-board and player-preview episodes, this structure should be treated as the default, not optional.
