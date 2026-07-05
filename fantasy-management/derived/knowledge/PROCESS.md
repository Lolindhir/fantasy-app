# Knowledge Layer Process

Pipeline:

```text
raw transcript -> episode note -> source takes -> current source view -> Mighty Giants analysis
```

## Layers

1. Raw transcripts stay in `sources/podcasts/{source}/raw_transcripts/YYYY/`.
2. Episode notes and episode JSON files stay in `sources/podcasts/{source}/episodes/YYYY/`.
3. Atomic takes are stored per episode and indexed under `derived/knowledge/takes/`.
4. The current cross-source view is stored under `derived/knowledge/current/`.
5. Final recommendations stay under `analyses/`; user decisions stay under `decisions/`.

## Current view

The `current/` files are the normal starting point for later source-based evaluations. They summarize the latest source-derived view after stale, contradicted or superseded information has been separated from active information.

## Historical view

The `takes/` files keep older takes as evidence. Older takes are not deleted just because a newer source changes the evaluation.

## Default freshness

- injuries and availability: short-lived
- camp and practice reports: short-lived
- depth chart and role notes: medium-lived
- weekly redraft notes: short-lived
- rankings and market values: medium-lived
- dynasty talent notes: long-lived
- source philosophy: evergreen

## Evaluation path

For player analysis, use current app data first when dynamic facts matter, then the current player knowledge file, then player take history, then episode notes, then raw transcript evidence.

For team, injury, role and market analysis, use the matching current aggregate first, then drill into take history and source files.
