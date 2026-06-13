# AI Context: Project Overview

Status: Manual Context
Audience: AI assistants and maintainers
Scope: High-level architecture, data ownership, and documentation conventions

## Purpose

This document gives AI assistants a stable entry point into the fantasy app architecture.

The project separates manual domain and architecture decisions from generated structure documentation. Manual context explains why the app works the way it does. Generated documentation may describe files, functions, JSON shapes, or module structure, but it must not override manual decisions documented here.

## Architecture Summary

The app is a static Angular frontend backed by generated JSON data.

The main layers are:

- `Metadata.json`: league-specific manual inputs and rules.
- `ConfigUtils.psm1`: technical paths, file locations, and generation configuration.
- PowerShell request/generation scripts: collect, normalize, enrich, compare, and save generated app data.
- Generated JSON files: application data consumed by Angular.
- Angular services and components: presentation layer and UI-specific view models.

## Source-of-Truth Rules

Manual domain decisions should live in `docs/ai-context/domain/`.

Frontend presentation decisions should live in `docs/ai-context/frontend/` or in component-specific documentation when needed.

Generated data structures should be described in generated documentation only after the generator is available. Until then, manually maintained JSON shape notes may be used, but they should be clearly marked as manual context.

## Documentation Model

Use this distinction when adding or updating documentation:

- Manual context documents decisions, invariants, ownership, and workflows.
- Generated context documents discovered structure, such as files, functions, exported types, and JSON schema-like details.
- File headers may contain compact `AI-DOC` blocks that can later be extracted into generated documentation.

## Current Domain Areas

The app currently has several important domain areas:

- League metadata and settings.
- Teams, rosters, owners, standings, and awards.
- Players, salaries, projected salaries, and free-agent status.
- Drafts and draft picks.
- Transactions and draft-pick ownership changes.
- Frontend views such as Overview, Teams, Players, Trade Simulator, and Handbook.

## Current Data Flow

The typical data path is:

1. Manual league configuration is read from metadata/config files.
2. Remote data is fetched from external APIs where applicable.
3. Manual corrections or enrichments are merged into remote data.
4. Normalized JSON files are saved only when their semantic content changed.
5. Angular loads the generated JSON files through `DataService`.
6. Components build local view models for display.

## Important Current Decisions

- Drafts are treated as first-class app data.
- Draft picks keep both original and current ownership information.
- Transactions can affect draft-pick ownership.
- Current-season transactions can be updated incrementally.
- Force updates rebuild data from the authoritative source for the requested scope.
- Overview currently owns draft-pick chip color calculation locally; this should later be moved into a shared frontend utility or pipe.

## Notes for AI Agents

Do not infer domain rules only from Angular templates. Templates usually show a presentation decision, not the full data model.

Do not assume generated JSON files are manually edited. In general, generated JSON is output data and should be changed through PowerShell generation logic.

When changing a domain concept, update the matching manual context document and then update any generated docs or file headers if they exist.

Prefer small, focused documentation files over one large document.
