# Fantasy Management Workflows

Purpose: reusable agent workflows for Fantasy Management tasks.

## General workflow

1. Read `fantasy-management/AGENTS.md`.
2. Read source and rule files under `fantasy-management/_ai/`.
3. Identify whether the task needs current app data from `public/data/`.
4. Load only the required current data.
5. Load relevant source, derived, analysis or decision files under `fantasy-management/`.
6. Distinguish stable facts from dynamic values.
7. Store outputs under the correct Fantasy Management folder when the user asks for persistence.

## Player analysis workflow

1. Load current league format and scoring.
2. Identify Mighty Giants context.
3. Load the player's current internal data.
4. Check role, production, game history, age, salary and injury context.
5. Add external market context only when current value matters.
6. Add StonedLack/source context only when relevant.
7. Produce a recommendation label.
8. If storing the result, save under `fantasy-management/analyses/YYYY/players/`.

## Trade analysis workflow

1. Resolve every player and pick in the trade.
2. Load current Mighty Giants roster, picks and cap/salary context.
3. Resolve true draft-pick metadata through `Drafts.json`.
4. Compare win-now points, long-term value, roster construction and liquidity.
5. Check external market context if value calibration matters.
6. Include StonedLack/source takes only as supplementary context.
7. Give a clear recommendation.
8. If storing, save under `fantasy-management/analyses/YYYY/trades/` and optionally update `decisions/YYYY/trade-decisions.md` after the user decides.

## Roster audit workflow

1. Load current `League.json`, `Metadata.json`, roster format and scoring.
2. Identify Mighty Giants by `TeamID = 1`.
3. Map roster, reserve and taxi players to current player records.
4. Cluster by position.
5. Categorize players into role buckets.
6. Evaluate salary/cap separately from quality.
7. Review picks and trade liquidity.
8. Identify upgrade targets, package pieces, stashes and cut risks.
9. Store under `fantasy-management/analyses/YYYY/roster/` if requested.

## Free-agent board workflow

1. Load current `League.json`.
2. Build the owned-ID set from every team roster, reserve and taxi list.
3. Load `public/data/chat/players-relevant/index.json`.
4. Load required player chunks.
5. Exclude every owned ID.
6. Evaluate remaining candidates by position, production, role, age, format fit and salary.
7. Verify top candidates through player records.
8. Store boards under `fantasy-management/derived/free-agent-boards/YYYY/`.

## StonedLack transcript workflow

1. Read `fantasy-management/sources/podcasts/stonedlack/STONEDLACK_EXTRACTION_GUIDE.md`.
2. Save raw transcript under `raw_transcripts/YYYY/` without content cleanup.
3. Create readable source note under `episodes/YYYY/`.
4. Create machine-readable JSON under `episodes/YYYY/`.
5. Update local StonedLack indexes if needed.
6. Keep source statements, entity cleanup and agent interpretation separate.
7. Do not invent missing details.

## Decision logging workflow

When the user makes a decision, log it under the matching file in `fantasy-management/decisions/YYYY/`.

Use a short entry containing:

- date
- decision type
- involved assets
- context
- final decision
- reason
- source analysis link if available
- follow-up date or watch condition if relevant

## File naming

Prefer date-prefixed filenames:

```text
YYYY-MM-DD_short-slug.md
YYYY-MM-DD_short-slug.json
```

Examples:

```text
fantasy-management/analyses/2026/players/2026-07-05_jaylen-waddle.md
fantasy-management/analyses/2026/trades/2026-07-05_waddle-for-kincaid-watson.md
fantasy-management/derived/free-agent-boards/2026/2026-07-05_free-agent-board.md
```

## Analysis frontmatter

Use frontmatter for stored Markdown analyses when useful:

```yaml
---
type: player_analysis
scope: fantasy-management
created: YYYY-MM-DD
team_context: Mighty Giants
data_sources:
  - public/data/League.json
status: active
supersedes: null
validity_note: "Dynamic evaluation; re-check current data before reuse."
---
```
