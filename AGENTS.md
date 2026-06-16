# AGENTS.md

## Project

This repository is a static fantasy football web app.

Frontend:

- Angular app in `src/app`

Data generation:

- PowerShell scripts in `public/requests`
- Generated app data in `public/data`

## Required context

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

- `AGENTS.md` is the first file agents must read before making repository changes.
- `.ai-context` is the canonical root for AI context documentation.
- Human-maintained AI context belongs in `.ai-context/manual`.
- Generated AI context belongs in `.ai-context/generated` and must not be edited manually.
- Do not create `docs/ai-context/**` or any parallel AI context documentation unless explicitly requested.
- When updating documentation:
  - AI working guidance goes to `.ai-context/manual/ai-guidance.yaml`
  - architecture decisions go to `.ai-context/manual/architecture.yaml` or `.ai-context/manual/decisions.yaml`
  - domain rules go to `.ai-context/manual/domain.yaml`
  - data sources and data flow go to `.ai-context/manual/data-sources.yaml`
  - file-local documentation goes to file headers or sidecar `.ai-doc.yaml` files

## Todo guidance

- Open project todos are maintained in `TODO.md` at the repository root.
- Todos must be written in German.
- Do not create additional todo lists in `.ai-context` or `docs`.
- Move information from `TODO.md` into `.ai-context/manual` only when it becomes a durable architecture, domain or source-of-truth decision.

## Generated files

Do not manually edit generated context files under:

- `.ai-context/generated`

Generated app data lives under:

- `public/data`

Exception:

- `public/data/Metadata.json` is manual input.
- `public/data/Metadata.ai-doc.yaml` documents `Metadata.json`.

## Current preference

Do not add file-header `AI-DOC` comments unless explicitly requested.

## Change guidance

- Keep `AGENTS.md` short and use it as a pointer to `.ai-context`.
- Put durable architecture and domain decisions into `.ai-context/manual`.
- Prefer small, focused commits.
- Do not change the data generation pipeline, Angular data model or generated JSON contracts without checking the AI context first.
