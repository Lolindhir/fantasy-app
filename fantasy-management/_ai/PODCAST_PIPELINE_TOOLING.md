# Podcast Pipeline Tooling

Purpose: document the implemented local validator and deterministic builder for incremental podcast extraction work packages.

This tooling implements the local phases defined in `PODCAST_EXTRACTION_PIPELINE.md`. It does not create or modify GitHub Actions workflows.

## Commands

Validate one incremental work package at its current phase:

```bash
python fantasy-management/_ai/scripts/validate_podcast_work.py \
  fantasy-management/podcast-work/{source_id}/{year}/{episode_id}
```

Require every publication gate and a valid `publish-request.json`:

```bash
python fantasy-management/_ai/scripts/validate_podcast_work.py \
  fantasy-management/podcast-work/{source_id}/{year}/{episode_id} \
  --require-ready
```

Validate every work package currently stored under `fantasy-management/podcast-work/`:

```bash
python fantasy-management/_ai/scripts/validate_podcast_work.py --all
```

Build the canonical published package at the path declared by `publish-request.json`:

```bash
python fantasy-management/_ai/scripts/build_podcast_package.py \
  fantasy-management/podcast-work/{source_id}/{year}/{episode_id}
```

Use `--output` only for a local staging or test build. The generated `index.json` continues to describe the canonical target path declared by the publish request.

Replacing an existing published package is blocked by default. It requires the explicit option:

```bash
python fantasy-management/_ai/scripts/build_podcast_package.py \
  fantasy-management/podcast-work/{source_id}/{year}/{episode_id} \
  --replace-existing
```

Run the complete Fantasy Management script test suite after changing pipeline schemas, validators, builder code or fixtures:

```bash
python -m unittest discover \
  -s fantasy-management/_ai/scripts/tests \
  -p "test_*.py" \
  -v
```

## Validator scope

The work-package validator checks:

- schema validity and consistent episode/source identity;
- complete raw source and raw-part references;
- Content Map manifest, ordered segments and safe internal paths;
- active Golden Set profile references;
- required claims, reasoning obligations and dimensions for deep or structural material;
- one-file-per-take storage and unique take IDs;
- planned-take, claim and preserved-dimension reconciliation;
- ordered article sections and their segment/take links;
- independent mention-audit segments, unique mention IDs and valid coverage links;
- complete process review and absence of blocking findings;
- exact canonical publish target and ready-state gates.

Warnings are review prompts. Errors block publication.

## Builder behavior

The builder is deterministic and performs no editorial rewriting. It:

1. validates the work package with `require_ready=True`;
2. copies the authored raw, Content Map, take-item, mention-segment, article-section and process-review files into a temporary package;
3. concatenates ordered article sections into `episode.md`;
4. aggregates individual take files into `takes.json`;
5. aggregates mention segments in Content Map order into `mentions.json`;
6. calculates `index.json` and mention/take counts;
7. runs the existing episode-package and mention-coverage validators against the temporary generated package;
8. publishes only after every blocking check passes;
9. atomically replaces the target only when `--replace-existing` was explicitly supplied;
10. removes temporary output after any failure.

The authored take item retains all evidence points. For compatibility with the stable episode entry-point schema, the generated take keeps the first evidence point in `evidence` and the complete list in `evidence_points`.

## Synthetic regression tests

The current synthetic test package covers:

- a valid deep player-analysis segment;
- Content Map claim and expected-dimension reconciliation;
- rejection of unapproved Golden Set profiles;
- deterministic byte-identical rebuilds;
- absence of partial output after validation failure;
- protection of existing output unless replacement is explicit.

Synthetic fixtures test the process without imposing new rules on historical episodes.

## Remaining implementation phases

Before normal production use:

1. run one deliberate manual end-to-end pilot with a new or throwaway episode;
2. inspect the authored Content Map, take depth, article quality and generated package manually;
3. adjust schemas, profiles or tooling only through explicit approved changes;
4. only then define and approve the narrowly scoped GitHub Actions publication workflow;
5. after the complete process is stable, regenerate Stoned Lack episode 571 and compare it with the previous extract.
