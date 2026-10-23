# CP03 restore safety probe (Issue #471)

The immediate restore acceptance target is to recreate the **existing** Shared Derived
products from canonical `data-source` and `data-meta`, independently of old
`data-derived` or generated `public/data`. This file is a scoped diagnostic,
not a new publisher, scheduler, product contract or authorization to backfill.

Run `python3 tools/derived_clean_root_audit.py` in a full local checkout.
It regenerates PlayerValuation and the existing LeagueTransactions/LeagueDrafts
models into an ephemeral root with only `data-source` and `data-meta` visible.
Each product gets a second pass, a byte parity comparison against currently
published snapshots and a machine-readable status. Exit 2 means **not ready**.
No repository data or App content is written.

Expected open owner decisions until proven otherwise:

- PlayerValuation may require existing older/same-week persisted Inputs for
  Identity Holds. The probe must report any clean-root byte difference rather
  than quietly accepting null/zero or seeding from published App Players.
  Fix belongs to the valuation model/owner contract; no silent model change.
- LeagueHistory may require `public/data/Standings.json` for placement-based
  draft order. That is an App-derived circular dependency, and the source-owned
  predecessor must be established by #987 or another explicit owner decision.
  Do not treat temporarily copying Standings as source-only restoration.

Separately, `tools/historical_derived_orchestrate.py --mode full` already
stages finalized PlayerWeekFantasy then strict TeamWeekPerformance parity and
second-pass no-op. `nfl-games` already has an all-seasons source-only publisher.
This probe **does not** claim that those products or the full weekly end-to-end
restore have passed or that production writers may be activated.

Next gate after this diagnostic: resolve demonstrated owner-specific blockers,
run all-product empty-root parity + second no-op, then separately approve
the race-safe published full and incremental cadence. No App/UI work.
