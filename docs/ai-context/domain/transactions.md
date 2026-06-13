# AI Context: Transaction Domain

Status: Manual Context
Audience: AI assistants and maintainers
Scope: Current-season transactions, historical transactions, manual enrichments, and draft-pick ownership changes

## Purpose

This document describes how transactions are modeled and why they matter for other domain areas such as rosters, draft picks, and team assets.

Transactions are not only a list of moves. They are also one source of truth for changes to draft-pick ownership.

## Core Concepts

A transaction represents a completed league move.

Important transaction-level concepts include:

- source,
- transaction ID,
- transaction type,
- status,
- season,
- week,
- created timestamp,
- created date,
- involved roster IDs,
- player adds,
- player drops,
- draft picks,
- notes or manual enrichments.

## Data Sources

Transactions may come from:

- Sleeper transaction API data,
- manual transaction input,
- manual enrichment of matching Sleeper transactions.

Sleeper currently appears to return only completed transactions through the relevant transaction endpoint. Therefore, pending transactions are not currently modeled as a separate generated app file.

## Manual Enrichment

Manual transactions can enrich or correct remote transaction data.

When a manual transaction references a Sleeper transaction ID, it should be matched to that remote transaction and used to add or correct app-specific information.

Manual transactions may also exist independently when no external transaction represents the required domain event.

## Status Rules

Current generated app data should primarily contain completed transactions.

If external data later starts returning non-completed statuses, the status field should be preserved so the app can detect and handle the change intentionally.

Do not introduce a `TransactionsPending.json` file unless there is a reliable source for pending transaction data.

## Current-Season Update Rules

Current-season transactions can be refreshed incrementally.

The normal update should fetch the required active window, such as:

- missing weeks,
- current week,
- previous week.

A force update should rebuild the current-season transaction data for the requested available weeks.

Force means re-fetching or rebuilding source data. It does not necessarily mean writing the output file if the semantic content is unchanged.

## Historical Transaction Rules

Historical transactions should generally remain stable.

Historical transaction files should be rebuilt only when explicitly requested or when the generation logic changes in a way that requires a backfill.

Historical data should not be rewritten unnecessarily.

## Merge Rules

Incremental updates should replace transactions for the weeks that were fetched and keep transactions for other weeks.

After merging, transactions should use the canonical transaction sort order.

The app currently expects transactions to be sorted from newest to oldest using season, week, timestamp, and transaction ID as relevant sort keys.

## Draft-Pick Rules

Transactions can transfer draft-pick ownership.

A transaction that contains draft-pick movement should update the current owner of the affected draft pick while preserving the original owner.

Draft-pick transaction history should allow the app to understand how and when ownership changed.

Draft and transaction logic should therefore be reviewed together when changing either side.

## Generated Output Ownership

`Transactions.json` is generated app data.

It should generally be changed by updating transaction generation logic or manual transaction input and then running the request/generation flow again.

Do not manually patch generated transaction output unless it is a temporary debugging step and will not be committed as source of truth.

## Important Decisions

- Sleeper transaction data is treated as remote source data, but manual enrichments can add app-specific correctness.
- Current-season transactions can be updated incrementally.
- Force rebuilds the fetched transaction scope but should still allow compare-and-skip behavior when output did not change.
- Pending transactions are not generated right now because the current remote source does not reliably provide them.
- Draft-pick ownership depends on transaction history.
- Transaction sort order should remain consistent across normal and force updates.

## Notes for AI Agents

Do not assume a transaction affects only players. It may affect draft picks.

Do not add pending transaction output unless there is a reliable pending transaction source.

When a generated transaction file appears wrong, inspect the transaction generation flow and manual transaction input before changing Angular.

When changing transaction sort order, ensure both normal incremental updates and force rebuilds use the same canonical sort function.

When changing draft-pick ownership logic, also update `docs/ai-context/domain/drafts.md` if the domain rule changes.
