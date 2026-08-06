# Fantasy Operations Architecture

## Purpose

Fantasy Operations uses a provider-neutral hybrid architecture. Deterministic repository tooling prepares reusable facts and signals. Current qualitative research and interpretation happen outside the repository. Durable repository changes require explicit human approval.

The repository must not depend on a specific AI provider, AI SDK, hosted model, or paid inference API.

## Runtime layers

### 1. Source refresh

Existing source workflows refresh league, roster, transaction, player, market, ranking, ADP, schedule, game and usage inputs.

Source refreshers own acquisition and source-local normalization. They do not make roster recommendations.

### 2. Deterministic materialization

Versioned scripts join refreshed inputs into provider-neutral datasets. Materialization may calculate identifiers, percentiles, deltas, tiers, quality flags, provenance and input fingerprints.

Materialization must not:

- browse the web;
- call an AI or recommendation service;
- infer qualitative role changes from prose;
- create Hold, Shop, Cut, Add, Start or Sit recommendations;
- turn a missing source row into a negative player judgment.

The first materialized contract is:

```text
fantasy-management/generated/operations/managed-roster-signals.json
```

Its companion quality report is:

```text
fantasy-management/generated/operations/data-quality.json
```

### 3. External research and analysis

An external analyst may read the current materialized datasets, perform fresh research and interpret qualitative signals such as injury context, practice participation, role, opportunity, coaching comments and depth-chart changes.

External analysis is working output. It is not automatically repository truth.

### 4. Notification

Material changes and relevant errors may be delivered automatically. No-change runs remain silent.

A notification does not change repository state.

### 5. Human-approved persistence

A durable write to State, Knowledge, Decisions, boards, baselines or stored reviews requires explicit human approval after the proposed change and supporting evidence are visible.

The approved write is then performed interactively with the normal repository validation and publication rules.

## Injury-data rule

`public/data/Players.json` currently contains a structured secondary injury signal from the existing player refresh pipeline:

- `Injured`
- `InjuryDetails.ReturnDate`
- `InjuryDetails.Description`
- `InjuryDetails.Date`
- `InjuryDetails.Designation`

These fields are useful for candidate detection and prioritization. They are not an official-injury-report source and must not be treated as proof of health when empty. Decision-relevant positive signals require fresh external verification.

## Generated-data rule

Generated Fantasy Operations datasets are reproducible read models. They contain provenance and input fingerprints and are rewritten only when semantic input or output content changes.

They do not replace the canonical current league data under `public/data/` or the canonical source snapshots under `fantasy-management/sources/`.

## Legacy observation runner

The former autonomous State-writing observation runner is retained only as historical configuration while migration is in progress. It must operate read-only and must not attempt autonomous State publication.
