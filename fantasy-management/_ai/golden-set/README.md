# Podcast Golden Set

Purpose: define how approved podcast extraction quality profiles are selected, combined and extended.

## Active profiles

`profile-list.json` is the canonical list of approved profiles.

Only profiles with `status: "active"` may be used as canonical extraction requirements. A profile file that is not registered in the list is a draft or proposal, not an active rule.

## Profile selection

Select profiles after the complete raw source has been read and the Content Map segments have been identified.

A segment may use multiple profiles. Examples:

- a detailed rookie ranking may use `player-evaluation`, `position-group`, `ranking` and `market-strategy`;
- a team preview may use `team-evaluation`, `coaching-staff`, `scheme-analysis` and `news-segment`;
- a live rookie draft may use `mock-draft`, `ranking`, `market-strategy` and selected player profiles;
- a game-by-game in-season preview may use `game-matchup-preview`, `team-evaluation`, `coaching-staff` and `scheme-analysis`;
- an in-season start/sit or weekly ranking segment may use `weekly-fantasy-start-sit`, `player-evaluation`, `ranking` and `game-matchup-preview`.

For a concrete weekly forecast, preserve **NFL season and week** in the structured `weekly_context`; the home/away pairing is included when known, and a canonical game ID only when verified. Never turn a week-specific podcast take into an evergreen opinion or final fantasy-management lineup choice.

Record selected profile IDs in the Content Map manifest, each relevant Content Map segment and every authored take.

## Triggered dimensions

Profile dimensions are conditional preservation checks.

They mean:

> If the source materially discusses this dimension, preserve it at the depth supported by the source.

They do not mean:

> Invent or research this dimension when the source does not discuss it.

The Content Map records which dimensions were detected and therefore expected. Authored takes record which dimensions were actually preserved.

## Depth

Use the source-depth levels defined in `PODCAST_EXTRACTION_PIPELINE.md`:

- `passing`
- `brief`
- `substantive`
- `deep`
- `structural`

Storage size does not determine depth. A one-file take may remain detailed. Deep and structural material must preserve its major reasoning chain, conditions, uncertainty and materially discussed positive and negative cases.

## Evaluation use

Golden Set evaluation checks the extraction process and new pipeline packages. It does not retroactively invalidate the historical episode archive.

Evaluation should review at least:

- source fidelity
- content recall
- reasoning preservation
- nuance preservation
- structural fidelity
- entity breadth
- downstream usability
- compression control

Schema validation alone cannot prove editorial quality.


## Weekly pilot coverage review

For `game-matchup-preview` and `weekly-fantasy-start-sit`, selection of the right profile is necessary but not sufficient. Independently enumerate each *source-spoken* game call, Start/Sit answer, player-vs-player ranking, injury contingency, streaming/waiver strategy and longer-horizon trade recommendation before accepting authored takes as complete. Preserve the distinct source confidence behind each game; never merge games because both have the same O/U. Short explicit Q&A answers require a reusable take even when source depth is `brief`.

Golden Set dimensions are conditional; they do not require the source to support invented details. Transcription identity uncertainty may remain unresolved with `entity: null` and must not suppress a source claim. Cue-level literal evidence and neutral labels for unconfirmed speaker differences are required for meaningful editorial review. Follow `PODCAST_EXTRACTION_RULES.md` for source-first coverage and evidence QA.

### Multiple review objectives

The Golden Set guides **depth and content fidelity after source coverage inventory**, not whether a source-spoken name or short explicit recommendation deserves to be remembered. For new/reworked podcast packages, retain an early high-recall entity-candidate inventory and a separate claim/question inventory, then cross-check both independently against the final takes/article. QA findings should trigger targeted extraction and re-review; the preserved first-pass snapshot must remain available for honest quality measurement. An unresolved identity does not excuse an omitted source claim, and a passing mention does not justify inventing a standalone evaluation.

## Controlled extension

Every completed extraction performs a process review and may propose:

- a new profile dimension
- a new segment, subject or relation type
- a new profile
- a reference case
- a rule, schema, storage or workflow change

Proposals must include episode evidence. They do not become active automatically.

Canonical profile or profile-list changes require explicit user approval.
