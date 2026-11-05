# G5 · Independent read-only Draft content witness

Date: 2026-11-05. Owner: #1263. Mode: **offline-only**, no live skip, no persisted attestation or new workflow.

## Goal

The previous G5 shadow observer checked only the existence of `data-derived/league-drafts` and `public/data/Drafts.json`. A directory can exist while a configured future-year product is missing or a traded PickKey has a stale owner. This step provides a **separately invoked read-only content witness** without reimplementing the canonical Draft rules.

## Canonical method

`python3 tools/league_live_shadow_gate.py --audit-draft-content --league nfl-reise`

The new option is **not** called from League Live. It uses existing functions from `tools/league_history_app_publish.py`:

1. `load_inputs` and `build_history` derive the dynamically configured current + future (and historical) draft seasons from the existing Source/metadata/provider rules. No hard-coded 2027/2028/2029 horizon.
2. `verified_product_history` fails closed when any expected persisted `data-derived/league-drafts/<league>/<year>.json` or transaction partition is missing, invalid, or differs from canonical history, including prior seasons. This is the same strict Shared Derived contract used before App publication.
3. `render` constructs the expected App `Drafts.json` from the **verified persisted Derived** data. The existing semantic `_difference` detects drift against the published App file.
4. A separate **structural comparison only** checks that every expected `PickKey` occurs exactly once in `League.json::Teams[*].DraftPicks` under its `CurrentOwnerRosterID`. It catches missing, duplicate, extra and misassigned keys without recomputing draft order, trades, or display fields.

The evidence result includes draft years and counts, errors, `contentParityVerified`, `safeToSkip:false` and `enforced:false`. A `verified` content result does **not** prove prior successful publication, time/finality freshness, concurrent writer isolation, or fail-soft recovery. No live observer behavior changes: the extra audit runs **only** via its explicit CLI option and does not write a file.

## Negative / regression proof

The existing registered Fast test module `tools/tests/test_league_live_shadow_gate.py` receives positive multiyear / traded-pick cases (including remote 2031+ seasons), missing/extra/wrong-owner/duplicate/malformed keys, missing future-year Derived product (mocked canonical verifier failure), and CLI-isolation assertions. Actual repository CI, not synthetic fixtures alone, is the merge gate.

## Safety and limits

- No new output owner, domain calculation, external API call, source sync, publication writer or workflow trigger.
- The offline audit reads full canonical history and may be more expensive than a normal current-only League Live tick. It is **deliberately not invoked in the 10-minute chain**.
- It validates **content parity for one selected league** at the checked-out repository revision. It is not a multi-league global no-op attestation and does not prove that another workflow cannot change data immediately afterward.
- A failed witness returns an error and nonzero exit status, never a skip.
- Next separate G5 proof: independently verified completed-run provenance + temporal/finality validity + race/recovery evidence. Do not enable a live Early Exit based on this report.

**Rollback:** revert the scoped read-only CLI/test/report PR. Existing production behavior remains unchanged.
