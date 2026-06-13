# AI Context: Data Flow

Status: Manual Context
Audience: AI assistants and maintainers
Scope: Data generation, JSON ownership, and Angular consumption

## Purpose

This document explains how data moves from league-specific inputs and external APIs into generated JSON files and finally into Angular components.

It is intended to prevent AI assistants from mixing up manual configuration, generation logic, generated app data, and frontend presentation state.

## High-Level Flow

```text
Manual inputs / metadata
        |
        v
PowerShell config and utility modules
        |
        v
Remote API requests + manual enrichments
        |
        v
Normalized generated JSON files
        |
        v
Angular DataService
        |
        v
Component-specific view models
        |
        v
HTML / SCSS presentation
```

## Main Layers

### Manual Inputs

Manual inputs define league-specific rules and corrections. They are not generated output.

Examples include:

- league IDs and season settings,
- owner mappings,
- salary rules,
- manual draft or transaction corrections,
- app-specific rules that external APIs do not provide.

### Configuration Layer

`ConfigUtils.psm1` owns technical paths and generation configuration. It should answer questions like:

- where generated files are stored,
- where archives are stored,
- which file names belong to which data type,
- which league metadata values should be exposed to request scripts.

Configuration should not contain presentation logic.

### Generation Layer

PowerShell scripts and modules collect, normalize, enrich, compare, and save app data.

Generation code is responsible for:

- fetching remote data,
- applying manual corrections,
- resolving IDs into app-level references,
- creating stable generated JSON shapes,
- avoiding unnecessary file writes when semantic content did not change.

### Generated JSON Layer

Generated JSON files are app data, not source code and not manual documentation.

They should generally be changed by updating generation logic or manual input files, then running the generator again.

Generated JSON may be used by Angular directly, but Angular should not be the source of truth for domain transformations that belong in the generation pipeline.

### Angular Data Layer

`DataService` loads and combines generated JSON files for the frontend.

It may enrich raw generated objects into frontend-friendly objects, such as resolving player IDs to full player objects or adding display helpers.

### Component View Models

Components should build local view models when a display needs grouping, sorting, expansion state, chip display data, or other UI-specific formatting.

Component view models should not create new domain truth. They should only prepare existing data for display.

## Update Flow

The main league request script coordinates the current app data refresh.

Current-season data can often be refreshed incrementally. For example, current-season transactions may fetch only missing weeks, the current week, and the previous week unless a force rebuild is requested.

Historical data should generally remain stable and only be rebuilt intentionally.

## Compare-and-Save Behavior

Generated JSON should be saved only when meaningful content changed.

This keeps commits cleaner and avoids timestamp-only or ordering-only churn where possible.

When a force update is used, force should mean "re-fetch or rebuild the source data for the requested scope". It does not necessarily mean "write the target file even when content is unchanged".

## Current Important Data Files

The most relevant generated JSON concepts are:

- League data,
- team data,
- player data,
- standings data,
- draft data,
- transaction data.

Draft and transaction data are linked because transactions can transfer draft-pick ownership.

## Frontend Consumption Rules

Angular should prefer normalized generated data instead of re-deriving complex domain logic in templates.

Templates should stay presentation-focused.

If a display rule becomes reused across components, move it from the component into a shared frontend helper, pipe, or service.

Current example: Overview calculates draft-round chip colors locally for now, but the long-term target is a shared utility so all components use the same round color scale.

## Notes for AI Agents

When a data field appears in Angular, trace it back to its generated JSON source before changing its meaning.

When a generated JSON field is wrong, prefer fixing PowerShell generation or manual inputs instead of patching Angular display logic.

When updating documentation, separate data-generation rules from frontend display rules.
