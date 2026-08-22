# AGENTS.md

## Project

This repository is a static fantasy football web app.

Frontend:

- Angular app in `src/app`

Data generation:

- PowerShell scripts in `public/requests`
- Generated app data in `public/data`

## Context routing

This repository contains two separated agent working contexts:

1. Application / frontend / generated app data context
2. Fantasy Management context

For application, frontend, data generation, generated JSON contract, routing or app architecture work, use the existing `.ai-context` reading order below.

For any NFL Dynasty, Fantasy Football, Mighty Giants, roster, trade, draft, player evaluation, podcast, StonedLack, Relevant Players, free-agent analysis or source-processing task, agents must use:

`fantasy-management/AGENTS.md`

The Fantasy Management context is isolated from the application context. Do not store Fantasy Management analysis outputs, podcast extractions, player boards, source summaries or decisions in the central app AI context.

Do not duplicate detailed Fantasy Management rules or source documentation in global project instructions. The canonical instructions for Fantasy Management live inside `fantasy-management/`.

## Required app context

Before making architecture, data model, generation or frontend changes, read:

1. `.ai-context/ai-context.yaml`
2. `.ai-context/manual/ai-guidance.yaml`
3. `.ai-context/manual/architecture.yaml`
4. `.ai-context/manual/domain.yaml`
5. `.ai-context/manual/data-sources.yaml`
6. `.ai-context/manual/decisions.yaml`

## Source-of-truth rules

- `public/data/Metadata.json` owns league-specific inputs and rules.
- `public/requests/utils/ConfigUtils.psm1` owns technical paths and generation configuration.
- `public/data/*.json` files are generated app data.
- `src/app/**` owns Angular display and frontend interaction.
- Do not treat generated JSON as manually editable source-of-truth data.
- Do not put league-specific rules into Angular unless they are frontend-only display enrichment.

## Documentation routing

- `CHAT_START.md` is a static external/project entry pointer. Do not modify it as part of normal rule, workflow, routing or documentation changes; update it only when the user explicitly requests a change to that entry pointer itself.
- `AGENTS.md` is the first file agents must read before making repository changes.
- `.ai-context` is the canonical root for application AI context documentation.
- `fantasy-management/AGENTS.md` is the canonical root for isolated Fantasy Management agent documentation.
- Human-maintained application AI context belongs in `.ai-context/manual`.
- Generated application AI context belongs in `.ai-context/generated` and must not be edited manually.
- Fantasy Management rules, sources, workflows, stored analyses, decisions and todos belong under `fantasy-management/`.
- Do not create `docs/ai-context/**` or any parallel AI context documentation unless explicitly requested.
- When updating application documentation:
  - AI working guidance goes to `.ai-context/manual/ai-guidance.yaml`
  - architecture decisions go to `.ai-context/manual/architecture.yaml` or `.ai-context/manual/decisions.yaml`
  - domain rules go to `.ai-context/manual/domain.yaml`
  - data sources and data flow go to `.ai-context/manual/data-sources.yaml`
  - file-local documentation goes to file headers or sidecar `.ai-doc.yaml` files

## Todo guidance

- Application, frontend, generated-data and shared technical-platform todos are maintained in `TODO.md` at the repository root.
- Fantasy Management and Fantasy Operations todos are maintained in `fantasy-management/TODO.md`.
- Classify a todo by its purpose and owning context, not merely by its implementation mechanism. A script or GitHub Action whose purpose is to prepare Fantasy Management data belongs in `fantasy-management/TODO.md`.
- Todos must be written in German.
- Do not create additional todo lists in `.ai-context` or `docs`.
- Move durable application decisions from `TODO.md` into `.ai-context/manual` when appropriate.
- Move durable Fantasy Management decisions from `fantasy-management/TODO.md` into the canonical rules, source maps or workflow documentation under `fantasy-management/_ai` when appropriate.

## Generated files

Do not manually edit generated context files under:

- `.ai-context/generated`

Generated app data lives under:

- `public/data`

Exception:

- `public/data/Metadata.json` is manual input.
- `public/data/Metadata.ai-doc.yaml` documents `Metadata.json`.

## GitHub Actions approval

- Do not create, modify, enable or commit GitHub Actions workflow files unless the user has explicitly approved the specific workflow change.
- Topic-specific, one-off, migration, upload, recovery or branch-manipulation workflows are prohibited by default.
- For one-off tasks, use existing repository tooling, local scripts, connector actions or temporary uncommitted files. If no safe alternative exists, ask for explicit approval before touching `.github/workflows/`.

## Current preference

- Do not add file-header `AI-DOC` comments unless explicitly requested.
- Agent-facing instruction files should be written in English.
- Human-facing documentation may be written in German or bilingual.

## Change guidance

- Keep root `AGENTS.md` short and use it as a pointer to `.ai-context` and `fantasy-management/AGENTS.md`.
- Put durable application architecture and domain decisions into `.ai-context/manual`.
- Put durable Fantasy Management rules, source maps, workflows and analysis-storage conventions into `fantasy-management/_ai`.
- Prefer small, focused commits.
- When retiring, renaming or migrating a canonical artifact, audit both exact code/path references and semantic instructions in active canonical agent, source and workflow documentation; update or remove stale procedural guidance in the same change while preserving intentionally historical provenance.
- Do not change the data generation pipeline, Angular data model or generated JSON contracts without checking the AI context first.
