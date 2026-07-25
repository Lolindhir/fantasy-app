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
- a live rookie draft may use `mock-draft`, `ranking`, `market-strategy` and selected player profiles.

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

## Controlled extension

Every completed extraction performs a process review and may propose:

- a new profile dimension
- a new segment, subject or relation type
- a new profile
- a reference case
- a rule, schema, storage or workflow change

Proposals must include episode evidence. They do not become active automatically.

Canonical profile or profile-list changes require explicit user approval.
