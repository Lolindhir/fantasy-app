# Legacy Derived Knowledge Process

This folder is now a legacy/compatibility area for older source-derived files.

The simplified active model is documented in:

- `fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`
- `fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md`

## Current preferred pipeline

```text
podcast source package -> Knowledge derivation -> Mighty Giants analysis
```

Meaning:

1. Podcast source packages stay under `fantasy-management/sources/podcasts/{source}/episodes/{year}/{episode_id}/`.
2. Podcast source packages contain `episode.md`, `takes.json`, `index.json` and `raw/`.
3. Podcast takes remain source material and are not automatically active Knowledge.
4. Derived Knowledge belongs under `fantasy-management/knowledge/`.
5. Final recommendations belong under `fantasy-management/analyses/`.

## Legacy files

Older files under this folder may remain for compatibility:

- `takes/`
- `current/`
- `entities/`

Do not create new podcast source takes here by default.

Use this folder only when working with older material that has not yet been migrated or when an explicit legacy/index rebuild task requires it.

## Knowledge derivation

When deriving Knowledge from source packages:

1. Read the source package's `episode.md` and `takes.json`.
2. Check whether the source take applies to the user's Dynasty league, 6-team structure, 2QB/2TE/4Flex format, roster context and current market.
3. Store only relevant derived Knowledge under `fantasy-management/knowledge/`.
4. Link back to the source package and take ID as evidence.
5. Keep final Mighty Giants recommendations out of Knowledge and store them under `analyses/`.
