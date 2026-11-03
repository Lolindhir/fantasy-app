# G5: League Live checkout variability and cross-run shadow observations

Date: 2026-11-03 UTC. Umbrella: [#1263](https://github.com/Lolindhir/fantasy-app/issues/1263).
Scope: read-only GitHub job timings and log observations, plus a non-gating offline comparison of the already-emitted shadow records. No writer, scheduler, deploy, permissions, producer, or job skips.

## Ten observed completed successful runs

The table covers ten selected successful League Live runs, nine from 2026-11-03 and one earlier reference from 2026-11-02. All have four completed successful execution jobs; the optional historical preflight was skipped. Values are **sums of executed job seconds**, not end-to-end run elapsed, billed minutes, or estimated future savings. Checkout seconds sum the four GitHub job *Checkout repository* / *Checkout main* step durations and include fetch plus working-tree materialization.

| Actions run | Four job seconds | Four checkout seconds | Checkout share |
|---|---:|---:|---:|
| [41389288792](https://github.com/Lolindhir/fantasy-app/actions/runs/41389288792) | 229 | 142 | 62% |
| [41697176568](https://github.com/Lolindhir/fantasy-app/actions/runs/41697176568) | 533 | 393 | 74% |
| [41698885362](https://github.com/Lolindhir/fantasy-app/actions/runs/41698885362) | 354 | 241 | 68% |
| [41700807350](https://github.com/Lolindhir/fantasy-app/actions/runs/41700807350) | 567 | 422 | 74% |
| [41702745475](https://github.com/Lolindhir/fantasy-app/actions/runs/41702745475) | 560 | 420 | 75% |
| [41705135996](https://github.com/Lolindhir/fantasy-app/actions/runs/41705135996) | 314 | 203 | 65% |
| [41707437559](https://github.com/Lolindhir/fantasy-app/actions/runs/41707437559) | 469 | 347 | 74% |
| [41709714044](https://github.com/Lolindhir/fantasy-app/actions/runs/41709714044) | 628 | 512 | 82% |
| [41712156849](https://github.com/Lolindhir/fantasy-app/actions/runs/41712156849) | 512 | 390 | 76% |
| [41713719862](https://github.com/Lolindhir/fantasy-app/actions/runs/41713719862) | 472 | 339 | 72% |
| **Observed total** | **4,638** | **3,409** | **73.5%** |

Checkout seconds: minimum 142, median 368.5, maximum 512 across these ten runs. The unusually long [run 41709714044](https://github.com/Lolindhir/fantasy-app/actions/runs/41709714044) spent ~8:32 of ~10:28 executed job seconds in checkout steps; its end-to-end run duration was 10:40 including non-job time. Its four `git fetch` spans total approximately 7:48 (timestamps of Fetching repository and Determining checkout info). This variation is substantial, not solely attributable to the new tiny shadow observer (each observer step was <=1 sec). The sample cannot isolate whether GitHub network throughput, repository size, runner variability, or other factors caused the slow fetches.

All four jobs currently perform separate full-tree, shallow Git checkouts with `fetch-depth: 1` (LFS disabled). Two of the jobs are repository branch writers via the publication/rebuild contract; they require the coherent latest target tree and existing retry semantics. Reusing workspace across independent hosted runners is not automatic. Do **not** blindly remove checkout/fetch or add sparse paths to productive publishers: working-tree reset and complete input/output coverage are safety-critical.

## Current repository tree volume: direct Git tree evidence

A read-only `git/trees/<tree-sha>?recursive=1` census of current `main` at `b2a010d` returned **5,125 tracked blobs under `data-source/` totaling about 3,755 MB uncompressed**. GitHub's repository metadata `size=1,519,138` KiB is a separate, compressed/storage-oriented indicator, **not** the bytes fetched by an Actions checkout. All seven queried subtrees returned `truncated=false`.

Major tracked current-tree `data-source/` segments by summed blob bytes (rounded decimal MB):

| Path | Files | Blob bytes, MB |
|---|---:|---:|
| `nfl/player-stats` | 580 | 2,129 |
| `nfl/weekly-rosters` | 517 | 557 |
| `providers/nflverse/weekly-rosters` | 50 | 277 |
| `providers/nflverse/player-stats` | 56 | 214 |
| `nfl/snap-counts` | 286 | 171 |
| `nfl/identities` | 6 | 108 |

Those first four directories alone represent ~3.18 GB of uncompressed tracked current blobs. This strongly supports investigating narrower **read-only validation** checkouts first; it is **not** proof of actual transferred bytes, cache state, provider rights, or suitability of sparse checkouts for live publishers. It also suggests a broader future data-volume/storage review, separately authorized from this G5 observational checkpoint. Do not delete/move canonical files or change data owners as a byproduct of timing optimization.

## Three consecutive live shadow runs and observed no-ops

The first three post-merge runs, [41709714044](https://github.com/Lolindhir/fantasy-app/actions/runs/41709714044), [41712156849](https://github.com/Lolindhir/fantasy-app/actions/runs/41712156849), and [41713719862](https://github.com/Lolindhir/fantasy-app/actions/runs/41713719862), all completed successfully with original branch writers executed. Their exact job logs show:

- League Source: `CanonicalFilesChanged: 0`, followed by no canonical League data-source changes; no Source commit.
- Standings: one `LEAGUE_LIVE_SHADOW` record per run; input fingerprint **`5f9891ce442d313f`** in all three; `Generator produced no repository changes. Nothing to publish.`
- League: one shadow record per run; input fingerprint **`745790f3204afed9`** in all three; `AppChanged: false`, `DerivedChanged: false`, `Generator produced no repository changes. Nothing to publish.`
- Both stages reported `would-run`, `enforced: false`, and the same three proof gaps: `missing-previous-successful-attestation`, `race-free-not-proven`, `fail-soft-recovery-not-proven-clean`. This is the intended safe behavior.

Thus **two consecutive pairs of real runs** demonstrated unchanged *observed* repository input trees and no-op publisher logs for both downstream stages. This is **not** a measurement of positive safe-to-skip decisions, nor proof that all external/finality/time dependencies are covered. No stage has been skipped. The first run used the newly merged `b2a010d` code, and the latter two used the same head.

## Offline cross-run comparison (read-only)

Extend the existing shadow reader `tools/league_live_shadow_gate.py`, rather than inventing a new data product, persistent attestation, workflow, or writer. A user may download the **full raw logs** for the **same stage** from two completed GitHub job executions and run:

```bash
python3 tools/league_live_shadow_gate.py --compare-log-files earlier-standings.log later-standings.log
python3 tools/league_live_shadow_gate.py --compare-log-files earlier-league.log later-league.log
```

The output reports `same-observed-inputs`, `changed-input-revision`, or `unverifiable`, changed dependency groups, and whether each job log contains the literal no-publish marker. Missing/duplicate/malformed shadow records, mismatched stages, incomplete/mismatched fingerprints, missing outputs, and nonmonotonic times fail closed. The comparer always returns `safeToSkip: false` and `enforced: false`; a no-publish **log marker is not proof of successful job completion**. Existing normal `--stage` runtime behavior, workflow YAML, and all publishers remain untouched. Future parity audits should independently check GitHub job success and all other upstream workflows rather than using logs alone as an attestation.

## Proposed optimization sequence, not enacted

1. **Separate checkout and calculation costs** in repeated normal scheduled runs using the already-existing `tools/audit_workflow_job_costs.py` and GitHub job/step timing; avoid new scheduled cost scrapers and do not confuse checkout time with billed minutes. Sample enough runs across time windows and include an occasional full publish.
2. **Investigate a validation-job-only sparse/partial checkout** with an explicit dependency and fixture closure (all League validation tests plus required canonical registry, metadata, NFL identity/season inputs). This might reduce blob transfer on that read-only job but requires a measured before/after PR and correct failure/negative fixtures. It is **not yet proven safe or effective**, and action version/defaults need a controlled test.
3. **Leave source sync, Standings, and League publishing checkouts full and independent** until rebuild-and-retry, late main advances, multi-league coverage, generated-data correctness, and cross-writer race safety are proven under any proposed checkout refactor. Do not merge jobs or reduce data reads on the basis of these ten observations.
4. **Build stronger cross-run proofs** for previous successful output materialization, monotonic source/product revisions, clock boundaries (kickoff/waivers/finality), recovery and failure handling, and other workflows. Only after positive and negative shadow parity exists would a real gate be a separately reviewable production proposal.

## Limits and rollback

Selected observational sample, not a randomized estimate or 30-day census. Repository status/public visibility and standard hosted runners are not a general billable-cost forecast. Shadow tree equality alone is not semantic output equality or safe skip authorization. No current runtime instrument can certify previous successfully processed revision, fail-soft recovery, race freedom, or time horizon. Existing workflow job logs have no durable source revision attestation.

This checkpoint adds a historical research report and an **offline-only** comparer with Fast negative tests. CI impact: existing registered `tools/tests/test_league_live_shadow_gate.py` extends its Fast regressions in `league-pwf-twp` and `consumer-restore`; `tools/league_live_shadow_gate.py` already routes to those families. No new test paths, selector changes, workflow changes, permissions, production data, or writers. Rollback: revert the small PR. Issue #1263 remains open for next evidence and any later checkout optimization.
