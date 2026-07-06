---
type: podcast_raw_manifest
scope: fantasy-management
source_id: {{source_id}}
episode_id: {{episode_id}}
episode_number: {{episode_number}}
title: "{{title}}"
published_date: {{published_date}}
processed_date: {{processed_date}}
language: de
raw_transcript_status: split_parts_imported_from_chat
parts_directory: {{raw_parts_directory}}
---

# Raw Transcript Manifest – {{source_name}} {{episode_number}} – {{title}}

The raw transcript could not be stored as one single file and was therefore split into ordered parts.

Use the following files in numeric order. The ordered concatenation is the raw transcript source for the episode.

## Parts

1. `part01_{{slug}}.md`
2. `part02_{{slug}}.md`
3. `part03_{{slug}}.md`

## Notes

- Do not clean or rewrite raw parts.
- Preserve timestamps, transcription errors, repetitions and off-topic passages.
- Episode analysis, player data and takes must reference this manifest when raw is split.
- If a better transcript is imported later, create a versioned raw source instead of overwriting this trace.
