"""LeagueTransactions / LeagueDrafts materialization pipeline (league-history.yaml, ADR-026, ADR-057).

Pure functions over a `LeagueHistoryInputs` value: no file access, no clock. The stages run in the
ADR-026 order in memory and hand the same objects to each other, exactly as the PowerShell rebuild
(DraftTransactionPipelineUtils.psm1::Invoke-DraftTransactionRebuild) does through files:

  1. transactions base  - canonical transactions merged with the manual overlay, per season
  2. pick identity      - Update-AllTransactionDraftPickTypesFromSleeper (all seasons, configured drafts), then
                          Update-HistoricalTransactionDraftPickTypesFromCompletedDrafts (past seasons)
  3. drafts             - completed history, current and open future drafts (league_drafts.py)
  4. pick results back  - Update-AllTransactionDraftPickDetailsFromLocalDrafts (enrich_pick_details)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .league_draft_identity import (
    DraftIdentityError,
    assert_draft_type_configs,
    completed_draft_definitions,
    identity_from_key,
    ps_string,
    provider_draft_map,
    sorted_configs,
)
from .league_drafts import DraftBuildError, build_drafts
from .league_transactions import (
    TransactionHistoryError,
    assert_unique_transaction_ids,
    enrich_pick_details,
    merge_manual_overlay,
    resolve_pick_identities,
)


@dataclass
class LeagueHistoryInputs:
    """Everything the materialization reads, already loaded from canonical sources."""

    league_id: str                                   # CanonicalLeagueID
    league_year: int                                 # current season (league manifest)
    seasons: list[int]                               # manifest seasons, ascending
    provider_league_ids: dict[int, str]              # season -> provider league ID
    draft_configs: list[dict[str, Any]]              # data-meta Drafts.Types
    open_draft_count: int                            # data-meta Drafts.UpcomingDraftCount (PerDraftType)
    owners: dict[str, int]                           # data-meta Owners: name -> RosterID
    canonical_transactions: dict[int, list[dict[str, Any]]]  # season -> adapted provider transactions
    payloads: dict[int, dict[str, Any]]              # season -> draft_canonical_consumer payload
    manual_rows: list[dict[str, Any]]                # hand-maintained overlay rows
    team_ids: list[int] = field(default_factory=list)  # current RosterIDs (TeamIDs), ascending
    standings_loader: Callable[[], list[dict[str, Any]]] | None = None  # transitional (Issue #987)


@dataclass
class TransactionStage:
    transactions: dict[int, list[dict[str, Any]]]
    unresolved: list[dict[str, Any]]


def _payload_drafts(inputs: LeagueHistoryInputs, season: int) -> list[dict[str, Any]]:
    return list((inputs.payloads.get(season) or {}).get("Drafts") or [])


def _traded_picks(inputs: LeagueHistoryInputs, season: int, draft_id: str) -> list[dict[str, Any]]:
    container = (inputs.payloads.get(season) or {}).get("TradedPicksByDraftID") or {}
    if draft_id not in container:
        raise TransactionHistoryError(f"Canonical draft payload 'TradedPicksByDraftID' has no entry for draft '{draft_id}'.")
    return list(container[draft_id])


def configured_contexts(inputs: LeagueHistoryInputs, season: int) -> list[dict[str, Any]]:
    """Get-TransactionDraftPickSleeperDraftContexts: configured/bound drafts of one season."""
    draft_map = provider_draft_map(inputs.draft_configs, _payload_drafts(inputs, season))
    contexts = []
    for key in sorted(draft_map):
        draft = draft_map[key]
        identity = identity_from_key(key, inputs.draft_configs)
        draft_id = ps_string(draft.get("draft_id"))
        traded = _traded_picks(inputs, season, draft_id) if draft_id.strip() else []
        contexts.append({
            "Season": identity["Season"],
            "DraftType": identity["DraftType"],
            "DraftInstance": identity["DraftInstance"],
            "DraftCode": identity["DraftCode"],
            "DraftKey": identity["DraftKey"],
            "SleeperDraftID": draft_id,
            "TradedPicks": traded,
        })
    return contexts


def historical_contexts(inputs: LeagueHistoryInputs) -> list[dict[str, Any]]:
    """Get-HistoricalTransactionDraftPickSleeperContexts: completed drafts of every season."""
    contexts: dict[str, dict[str, Any]] = {}
    for season in sorted(inputs.seasons):
        definitions = completed_draft_definitions(
            str(season), _payload_drafts(inputs, season), inputs.draft_configs, inputs.provider_league_ids.get(season)
        )
        for definition in definitions:
            draft_id = ps_string(definition["ProviderDraft"].get("draft_id"))
            if not draft_id.strip():
                raise TransactionHistoryError(
                    f"Completed historical draft '{definition['DraftKey']}' has no Sleeper draft_id. "
                    "Historical transaction identity resolution requires a concrete provider identity."
                )
            context = {
                "Season": ps_string(definition["Season"]),
                "DraftType": definition["DraftType"],
                "DraftInstance": int(definition["DraftInstance"]),
                "DraftCode": definition["DraftCode"],
                "DraftKey": definition["DraftKey"],
                "SleeperDraftID": draft_id,
                "TradedPicks": _traded_picks(inputs, int(definition["Season"]), draft_id),
            }
            identity = f"{context['DraftKey']}|{context['SleeperDraftID']}"
            if identity in contexts:
                raise TransactionHistoryError(
                    f"Duplicate historical draft context '{identity}'. Existing season '{contexts[identity]['Season']}' "
                    f"and duplicate season '{context['Season']}' would otherwise overwrite one another."
                )
            contexts[identity] = context
    return sorted(contexts.values(), key=lambda c: (int(c["Season"]), c["DraftKey"], c["SleeperDraftID"]))


def build_transaction_stage(inputs: LeagueHistoryInputs) -> TransactionStage:
    """Stages 1 and 2: transactions base with manual overlay, then pick identity resolution."""
    assert_draft_type_configs(inputs.draft_configs)
    configs = sorted_configs(inputs.draft_configs)
    transactions: dict[int, list[dict[str, Any]]] = {}
    for season in sorted(inputs.seasons):
        base = [dict(item) for item in inputs.canonical_transactions[season]]
        transactions[season] = merge_manual_overlay(base, inputs.manual_rows, str(season), inputs.owners, configs)
    assert_unique_transaction_ids(
        [item for season in sorted(transactions) for item in transactions[season]], "all season transactions"
    )

    # Stage 2a: every season against its configured/bound drafts.
    for season in sorted(transactions):
        if transactions[season]:
            resolve_pick_identities(
                transactions[season], configured_contexts(inputs, season), configs, inputs.league_year
            )

    # Stage 2b: past seasons against the completed-draft definitions of all seasons (same classification
    # as the historical draft generation, so the following draft stage sees identical identities).
    contexts = historical_contexts(inputs)
    if contexts:
        for season in sorted(transactions):
            if season != inputs.league_year and transactions[season]:
                resolve_pick_identities(transactions[season], contexts, configs, inputs.league_year)

    # The PowerShell stages only warn per stage; a provider pick that no stage identified is the real gap.
    unresolved = [
        {
            "Season": season,
            "TransactionID": transaction["TransactionID"],
            "PickSeason": pick["Season"],
            "Round": pick["Round"],
            "OriginalOwnerRosterID": pick["OriginalOwnerRosterID"],
        }
        for season in sorted(transactions)
        for transaction in transactions[season]
        for pick in transaction["DraftPicks"]
        if ps_string(pick.get("DraftSource")) == "Sleeper" and not ps_string(pick.get("DraftKey")).strip()
    ]
    return TransactionStage(transactions=transactions, unresolved=unresolved)


@dataclass
class HistoryResult:
    transactions: dict[int, list[dict[str, Any]]]
    drafts: dict[int, list[dict[str, Any]]]
    unresolved: list[dict[str, Any]]


def build_history(inputs: LeagueHistoryInputs) -> HistoryResult:
    """All four ADR-026 stages in memory."""
    stage = build_transaction_stage(inputs)
    all_transactions = [item for season in sorted(stage.transactions) for item in stage.transactions[season]]
    drafts = build_drafts(
        league_year=inputs.league_year,
        seasons=inputs.seasons,
        provider_league_ids=inputs.provider_league_ids,
        configs=inputs.draft_configs,
        open_count=inputs.open_draft_count,
        team_ids=inputs.team_ids,
        standings_loader=inputs.standings_loader,
        payloads=inputs.payloads,
        transactions=all_transactions,
    )
    enrich_pick_details(all_transactions, drafts)
    by_season: dict[int, list[dict[str, Any]]] = {}
    for draft in drafts:
        by_season.setdefault(int(draft["Season"]), []).append(draft)
    return HistoryResult(transactions=stage.transactions, drafts=by_season, unresolved=stage.unresolved)


def drafts_document(
    league_id: str,
    season: int,
    drafts: list[dict[str, Any]],
    resolve_reference: Callable[[str, int, str | None], dict[str, Any]],
    event_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Shared-derived draft product with references for picked Sleeper players."""
    from .league_player_refs import player_refs, provider_draft_names

    ids = [
        ps_string(pick["PlayerID"]) for draft in drafts for pick in draft["Picks"]
        if pick.get("PlayerID") is not None and ps_string(pick["PlayerID"]).strip()
    ]
    refs = player_refs(ids, season, resolve_reference, event_names or provider_draft_names(drafts))
    return {
        "ContractVersion": CONTRACT_VERSION,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "PlayerRefs": refs,
        "Drafts": drafts,
    }


CONTRACT_VERSION = 2  # LeagueDrafts: historical PlayerRefs.
TRANSACTION_CONTRACT_VERSION = 2  # LeagueTransactions: EffectiveAt and PlayerRefs.


def _player_ids(transactions: list[dict[str, Any]]) -> list[str]:
    found: set[str] = set()
    for transaction in transactions:
        found.update(ps_string(key) for key in transaction["Adds"])
        found.update(ps_string(key) for key in transaction["Drops"])
        for pick in transaction["DraftPicks"]:
            if pick.get("PlayerID") is not None and ps_string(pick["PlayerID"]).strip():
                found.add(ps_string(pick["PlayerID"]))
    return sorted(found)


def transactions_document(
    league_id: str,
    season: int,
    transactions: list[dict[str, Any]],
    resolve_reference: Callable[[str, int, str | None], dict[str, Any]],
    event_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Root object of shared-derived league-transactions for one league/season.

    PlayerIdentities is retained for existing consumers and is projected from
    exactly the same resolved references, not a second independent identity join.
    """
    from .league_player_refs import player_refs

    refs = player_refs(_player_ids(transactions), season, resolve_reference, event_names)
    return {
        "ContractVersion": TRANSACTION_CONTRACT_VERSION,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "PlayerIdentities": {player: ref["CanonicalPlayerID"] for player, ref in refs.items()},
        "PlayerRefs": refs,
        "Transactions": transactions,
    }


__all__ = [
    "CONTRACT_VERSION",
    "DraftBuildError",
    "HistoryResult",
    "build_history",
    "drafts_document",
    "transactions_document",
    "DraftIdentityError",
    "LeagueHistoryInputs",
    "TransactionHistoryError",
    "TransactionStage",
    "build_transaction_stage",
    "configured_contexts",
    "historical_contexts",
]
