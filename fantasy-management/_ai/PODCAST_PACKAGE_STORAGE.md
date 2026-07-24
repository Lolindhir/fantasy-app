# Podcast Package Storage

Purpose: define the backward-compatible storage model for large podcast source packages.

This file complements `PODCAST_SOURCE_MODEL.md` and `PODCAST_EXTRACTION_RULES.md`. It changes only technical storage. Extraction depth, evidence quality, the independent mention sweep and the separation between source, Knowledge and analysis remain unchanged.

## Stable entry points

Every schema-version-2 episode package keeps these stable entry points:

```text
index.json
episode.md
takes.json
mentions.json
raw/
```

`episode.md` is always one continuous reader-facing German document. Do not split it.

`takes.json` and `mentions.json` support two storage modes:

1. `inline`: the historical payload remains directly in the entry-point file.
2. `split`: the entry-point file is a small manifest and ordered payload files live below `takes/` or `mentions/`.

Existing inline packages remain valid and do not need migration.

## When to split

Use split mode when a technical JSON file is difficult to review, transfer or maintain as one artifact. Split before a connector or editor limit becomes a blocker. The decision is based on maintainability rather than a hard byte threshold.

Prefer:

- inline mode for small episodes;
- category parts for takes;
- contiguous numbered parts for mentions;
- canonical pretty JSON for manifests and every part.

Do not reduce extraction detail merely to keep one JSON file small.

## Split takes

`takes.json` becomes a manifest containing:

- episode/source identity;
- `storage_mode: "split"`;
- complete `take_counts`;
- one or more ordered descriptors per category; large categories may use numbered parts.

Each take part contains exactly one category and its `takes` array. Large categories may be divided into numbered files such as `takes/players-part01.json`; empty categories remain explicit parts with count `0`, so the six-category contract stays visible.

Validators aggregate all parts into the historical `take_categories` shape before running semantic and cross-file checks.

## Split mentions

`mentions.json` becomes a manifest containing:

- episode/source identity;
- `storage_mode: "split"`;
- the total `mention_count`;
- an ordered `parts` list.

Each `mentions/partNN.json` contains a contiguous `part_number` and a `mentions` array. Part numbering starts at `1` and has no gaps.

Validators aggregate all parts into the historical `mentions` shape before calculating counts and coverage. The part schema validates only the split-file envelope; the aggregated mention payload is validated once against the canonical episode mention schema so inline and split storage cannot drift apart.

## Integrity rules

For every split package:

1. Entry-point identity and every part identity must match.
2. Part paths must remain inside the package and below the expected folder.
3. Paths may not be duplicated; take categories may repeat only across ordered parts.
4. Descriptor counts must match actual part lengths.
5. Manifest totals must match aggregated totals.
6. Mention part numbers must be contiguous from `1`.
7. Take and mention IDs must remain unique across all parts.
8. `index.json` continues to reference `takes.json` and `mentions.json`, never individual parts.
9. Coverage and count validation runs on the fully aggregated data.
10. Every manifest and part must be UTF-8 canonical pretty JSON with a trailing newline.
11. Validators may not add episode-specific bypasses for schema, formatting or completeness checks.

## Validation

Run the normal commands. The validators detect inline or split storage automatically:

```bash
python fantasy-management/_ai/scripts/validate_episode_package.py \
  fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}

python fantasy-management/_ai/scripts/validate_episode_coverage.py \
  fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}
```

When schemas or validator code change, also run validator unit tests and all-package validation before merge.
