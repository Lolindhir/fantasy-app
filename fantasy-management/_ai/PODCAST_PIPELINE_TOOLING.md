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


## Private SRT preflight prototype (local, manual)

The bounded CLI below produces **candidate proposals** for the two independent pre-extraction inventories. It does **not** use an LLM and cannot claim full entity detection, semantic claim recall, verified player identities or autonomous multiple extraction runs. Its regex hints intentionally over-include German nouns and may miss lowercase/garbled ASR names. A human or model reviewing the complete source must complete both inventories. Raw SRT must remain in a rights-appropriate private workspace, never automatically committed to public GitHub.

```bash
python fantasy-management/_ai/scripts/podcast_preflight.py propose \
  "/private/episode.srt" --output "/private/episode-preflight"
```

To limit a dry-run to specific cue numbers, add `--start-cue 165 --end-cue 208`. This produces `manifest.json`, `entities.json` and `claims.json` in an empty output directory. The original SRT stays unchanged and is identified via SHA256.

**Required review:** verify each exact raw span/cue, manually mark `review_status`; in `claims.json`, set `required` true/false, split joined questions/claims into atomic cue-grounded entries as needed, and populate `linked_take_ids` for each required claim. Do not mark a proposal as reviewed only because a heuristic matched. For every real source-spoken claim missed by the hints, add a cue-grounded entry with a unique ID. Context-only mentions do not mandate standalone takes. Unverified canonical IDs stay null.

```bash
python fantasy-management/_ai/scripts/podcast_preflight.py check \
  "/private/episode.srt" --input "/private/episode-preflight" \
  --takes "/private/episode/takes/items" --require-reviewed
```

The `check` command checks byte-level transcript provenance, literal offsets, unique candidate IDs, mandatory review classification and reciprocal links `claim_ids` in authored take files. It does **not** automatically compare every unobserved source claim with the take set. It is a pre-extraction **prototype** and is not wired into `validate_podcast_work.py`, the publication builder, CI writers or the repository's canonical work-package schemas. Existing package behavior and historical artifacts stay unchanged. Keep a frozen first-pass take set before source-first QA, then repair and recheck using the approved multi-pass editorial rules.

## Semantic claim inventory: frozen first pass and independent audit

The local, **non-publishing** CLI provides a stable JSON intake contract for independently authored semantic source claims. This is the next technical checkpoint following the manual 45/53-claim Commanders–49ers pilot; **the script does not itself run a language model or infer missing claims**.

First ask an authorized model/human to read the raw SRT (cue by cue, not summary-first) and emit a `podcast-semantic-claim-inventory.schema.json` document with exact cue IDs, character offsets, literal `quote_hint`, one atomic `claim` per assertion, and `review_state: "unreviewed"`. Never normalize unsure names or convert suspicious ASR figures into verified NFL facts. Keep the raw source private.

```bash
python fantasy-management/_ai/scripts/podcast_semantic_claims.py freeze \
  "/private/episode.srt" "/private/claim-first-pass.json" --output "/private/frozen"
```

Read every source cue **again** with a different QA objective. Save an audit JSON containing `base_frozen_sha256`, `review_method`, `corrections` (each with `id`, `reason`, optionally `review_state`, `corrected_claim`, `review_note` and `linked_take_ids`) and `new_claims` (complete claim objects). An existing quote/cue may not be silently rewritten via a correction: use a traceable replacement claim. The frozen original is preserved.

```bash
python fantasy-management/_ai/scripts/podcast_semantic_claims.py reconcile \
  "/private/episode.srt" "/private/frozen" "/private/audit.json" --output "/private/reconciled"

python fantasy-management/_ai/scripts/podcast_semantic_claims.py check \
  "/private/episode.srt" "/private/reconciled/reconciled.json" --require-reviewed \
  --takes "/private/episode/takes/items"
```

The last check requires an editorially reviewed status plus, for substantive verified claims, an existing take with reciprocal `claim_ids`. Intermediate `check` without `--require-reviewed` is **source-span and structure only**. It **cannot establish that every source claim exists**. The existing `validate_podcast_work.py` and publication builder are not altered; do not report these preflight checks as a publication-ready verdict or an independent recall score. No model provider, automatic scheduling, raw upload, identity registry modification or novel GitHub writer is enabled.

## Operational tracking

This file documents implemented commands and tool behavior only. It does not maintain the mutable rollout roadmap.

Current production-readiness progress, the real end-to-end pilot, manual quality review, Stoned Lack 571 comparison and any later publication-workflow handoff are tracked in GitHub Issue #621.
