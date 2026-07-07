# Blocked legacy cleanup files

The cleanup attempted to remove or rewrite these files, but the GitHub connector safety checks blocked the operation repeatedly.

## Still present because deletion was blocked

```text
fantasy-management/derived/knowledge/takes/stonedlack/2026/sl_0569_t025.json
fantasy-management/derived/knowledge/takes/stonedlack/2026/sl_0569_t030.json
fantasy-management/derived/knowledge/takes/stonedlack/2026/sl_0569_was_wr.json
fantasy-management/derived/knowledge/takes/stonedlack/2026/sl_0569_mia_wr.json
fantasy-management/_ai/templates/podcast/episode_metadata_template.json
```

## Still containing legacy wording because rewrite was blocked

```text
fantasy-management/AGENTS.md
fantasy-management/_ai/PODCAST_EXTRACTION_RULES.md
fantasy-management/sources/podcasts/stonedlack/episodes/2026/sl_0569/raw/manifest.md
```

## Branch fallback

A feature branch fallback was attempted, but branch creation was also blocked by the connector safety checks.

Manual cleanup recommendation:

1. Delete the files listed above.
2. Remove remaining legacy wording from the three listed markdown/rule files.
3. Keep the active package at:

```text
fantasy-management/sources/podcasts/stonedlack/episodes/2026/sl_0569/
```
