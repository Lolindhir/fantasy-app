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

Before making architecture, data model, generation or frontend changes, these files must be read completely, in this order (they are listed as `@` imports so that tools which support imports load them automatically; other tools must open the paths):

1. @.ai-context/ai-context.yaml
2. @.ai-context/manual/ai-guidance.yaml
3. @.ai-context/manual/architecture-review.yaml
4. @.ai-context/manual/work-tracking.yaml
5. @.ai-context/manual/workflow-monitoring.yaml
6. @.ai-context/manual/workflow-publication.yaml
7. @.ai-context/manual/architecture.yaml
8. @.ai-context/manual/domain.yaml
9. @.ai-context/manual/data-sources.yaml
10. @.ai-context/manual/decisions.yaml

For frontend/UI/UX or design-system work, additionally read `.ai-context/manual/frontend-design/index.yaml` and follow its internal reading order before analysis or mutation.

## Source-of-truth rules

- `data-meta/<CanonicalLeagueID>/metadata.json` owns hand-maintained league metadata (owners, drafts, Cap Deadline, model choice per season); contract `.ai-context/manual/league-metadata.yaml`.
- `public/requests/utils/ConfigUtils.psm1` owns technical paths and generation configuration.
- `public/data/*.json` files are generated app data.
- `src/app/**` owns Angular display and frontend interaction.
- Do not treat generated JSON as manually editable source-of-truth data.
- Do not put league-specific rules into Angular unless they are frontend-only display enrichment.

## Documentation routing

- `CHAT_START.md` is a static external/project entry pointer. Do not modify it as part of normal rule, workflow, routing or documentation changes; update it only when the user explicitly requests a change to that entry pointer itself.
- `AGENTS.md` is the first file agents must read before making repository changes.
- `.ai-context` is the canonical root for application AI context documentation.
- `.ai-context/manual/frontend-design/index.yaml` is the canonical entry point for app-wide frontend design governance and routes design principles, architecture, standards and decisions.
- `fantasy-management/AGENTS.md` is the canonical root for isolated Fantasy Management agent documentation.
- Human-maintained application AI context belongs in `.ai-context/manual`.
- Generated application AI context belongs in `.ai-context/generated` and must not be edited manually.
- Fantasy Management rules, sources, workflows, stored analyses and decisions belong under `fantasy-management/`.
- Cross-consumer empirical research and model audits belong under `research/<data-product>/<year>/` (e.g. `research/player-week-fantasy/2026/`); this is historical evidence, not a production model source of truth. Shared data-product contracts stay in `.ai-context/manual`, algorithms in `tools`, consumer-specific Fantasy Management analysis in `fantasy-management/analyses`.
- Repository work tracking belongs in GitHub Issues according to `.ai-context/manual/work-tracking.yaml`; do not create parallel Markdown todo lists.
- Workflow publication/race-safety classification belongs in `.ai-context/manual/workflow-publication.yaml`.
- Do not create `docs/ai-context/**` or any parallel AI context documentation unless explicitly requested.
- When updating application documentation:
  - AI working guidance goes to `.ai-context/manual/ai-guidance.yaml`
  - architecture self-review and independent reviewer governance goes to `.ai-context/manual/architecture-review.yaml`
  - work-tracking and label semantics go to `.ai-context/manual/work-tracking.yaml`
  - workflow publication and branch-writer race-safety rules go to `.ai-context/manual/workflow-publication.yaml`
  - architecture decisions go to `.ai-context/manual/architecture.yaml` or `.ai-context/manual/decisions.yaml`
  - frontend design principles, architecture, standards and design decisions go under `.ai-context/manual/frontend-design/`
  - domain rules go to `.ai-context/manual/domain.yaml`
  - data sources and data flow go to `.ai-context/manual/data-sources.yaml`
  - file-local documentation goes to file headers or sidecar `.ai-doc.yaml` files

## Work tracking

- GitHub Issues are the canonical operative source of truth for repository work, including backlog, progress, handoff and historical work records.
- The current Issue body is the canonical mutable work state. Comments are supplemental history/communication and must not be required to reconstruct the current state.
- Follow `.ai-context/manual/work-tracking.yaml` for issue lifecycle, granularity, labels, priorities and drift checks.
- Questions and analysis alone do not authorize repository mutation. Once the user explicitly authorizes concrete repository work, the administrative Issue maintenance required to track that authorized work is implicitly authorized.
- Prefer one coherent Issue with an internal checklist for a multi-step deliverable. Do not create child Issues merely for implementation steps, commits, PRs or chat-sized units.
- Durable application decisions belong in `.ai-context/manual`; durable Fantasy Management decisions belong in the canonical documents under `fantasy-management/_ai` and are not replaced by Issues.

## Generated files

Do not manually edit generated context files under:

- `.ai-context/generated`

Generated app data lives under:

- `public/data`

Manual input lives in `data-meta/**`; no workflow or generator writes into it.

## Scope-based authorization and GitHub Actions safety

- Follow the agent-independent risk/authorization contract in `.ai-context/manual/ai-guidance.yaml` (`guidance.authorizationAndRisk`) for all code, workflow and repository mutations; authorization depends on scope and effects, not whether a file lives under `.github/workflows/`.
- An explicitly authorized end-to-end Issue or work package includes its routine in-scope workflow changes, validation, commits, pull requests and merges; do not ask again for each YAML edit or normal lifecycle transition. Approval of a single bounded step is not approval of the next substantive step.
- Elevated effects need a concrete impact and rollback assessment and targeted approval when they were not specifically authorized. Critical/destructive effects always need separate targeted authorization; stop on uncertain risk boundaries.
- Every GitHub Actions workflow that is created, renamed or materially repurposed must be classified in `.ai-context/manual/workflow-monitoring.yaml` in the same authorized change; unclassified workflows are a fail-closed monitoring configuration error.
- Every repository branch writer must follow the publication class assigned in `.ai-context/manual/workflow-publication.yaml`. Validation, CI, branch protection, write-scope and source-of-truth restrictions are never bypassed by authorization.
- Topic-specific, one-off, migration, upload, recovery or branch-manipulation workflows remain prohibited by default. Prefer existing repository tooling, local scripts, connector actions or temporary uncommitted files; an exception needs explicit scoped approval and the applicable elevated/critical review.

## Current preference

- Do not add file-header `AI-DOC` comments unless explicitly requested.
- Agent-facing instruction files should be written in English.
- Human-facing documentation may be written in German or bilingual.

## Execution checkpoints

- For complex or longer-running authorized work, use checkpointed execution: split the work into small, independently verifiable and reversible steps that leave a stable persisted state whenever practical.
- Prefer several small commits, pull requests or merges over a large monolithic change when the work can be separated cleanly.
- A specifically authorized single step ends at its checkpoint; an explicitly authorized complete Issue or work package permits continuous in-scope execution through validated steps, PRs and merges. Report meaningful checkpoints without requiring routine re-approval, and stop on completion, scope expansion, unsafe risk escalation or an unresolved blocker.
- The detailed execution-checkpoint rules live in `.ai-context/manual/ai-guidance.yaml`.

## Change guidance

- Keep root `AGENTS.md` short and use it as a pointer to `.ai-context` and `fantasy-management/AGENTS.md`.
- Put durable application architecture and domain decisions into `.ai-context/manual`.
- Put durable app-wide frontend design governance into `.ai-context/manual/frontend-design/`.
- Put durable Fantasy Management rules, source maps, workflows and analysis-storage conventions into `fantasy-management/_ai`.
- Prefer small, focused commits.
- Before updating an existing file, compare the intended complete content with the current file content or blob. If they are identical, skip the write and do not create a commit whose only effect would be a no-op file update.
- When retiring, renaming or migrating a canonical artifact, audit both exact code/path references and semantic instructions in active canonical agent, source and workflow documentation; update or remove stale procedural guidance in the same change while preserving intentionally historical provenance.
- Do not change the data generation pipeline, Angular data model or generated JSON contracts without checking the AI context first.
