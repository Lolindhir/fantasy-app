# NFL Games — observed Source → Derived → App publication (2026-11-03)

**Scope:** G1/G6 read-only post-publication trace for [Issue #1263](https://github.com/Lolindhir/fantasy-app/issues/1263). Historical evidence, not a new Source owner, monitor, contract or acceptance of future freshness. Times below are Git commit timestamps, **CET (UTC+1)**.

## Exact commit chain

| Step | CET | Immutable main commit | Effect |
| --- | --- | --- | --- |
| Canonical NFL Source | 17:52:24 | [e74621d](https://github.com/Lolindhir/fantasy-app/commit/e74621d39ce9cfe136f7911e16cb8281aecb8252) | Updated `data-source/nfl/schedule-odds/2026.json` (and other canonical Source products) |
| Global NFL Games Derived | 17:54:43 | [6463f1c](https://github.com/Lolindhir/fantasy-app/commit/6463f1c7cf13669e320b958ef7b926cc9b75df79) | Updated **only** `data-derived/nfl-games/2026.json` |
| League Live App delivery | 17:55:44 | [640854f](https://github.com/Lolindhir/fantasy-app/commit/640854f716a98898d592a75c612323f0886f91d1) | Updated `public/data/FantasyGameContext.json` together with other League Live outputs |

Git compare confirmed Source→Derived and Derived→App are each one commit ahead on the same main ancestry; no intervening commit in either step. Observed commit distances: **139 s** Source→Derived, **61 s** Derived→App, **200 s** Source→App. These are **not** workflow SLA values, per-publisher execution times, a maximum lag, or a guarantee about future events.

## Content provenance and exact before/after Git blob hashes

| Payload | Before source commit | After corresponding commit |
| --- | --- | --- |
| `data-source/nfl/schedule-odds/2026.json` | `1d680e73cad83869dfee83c045a3307d06e65ee5` | `efe1735f8a7589e29cf9a5a1b8296d665f617bfa` |
| `data-derived/nfl-games/2026.json` | `2b727069533ca2e653fc4f498e2ab720a8652d1b` | `02df483f2d8b3091a1d9da7b4003226bc4f2da0a` |
| `public/data/FantasyGameContext.json` | `d30220c6c8144bc0ac4c310bea7c9742142e8af8` | `bc3ce2b160d07b2f972ff4307d3d9ed5963cd7d7` |
| App GameID→canonical GameID bridge `public/data/Schedule.json` | `7fe026c249f8fe65f1867237b6f4057a0b3b962d` | unchanged |

At Source commit `e74621d`, the Derived and App blobs were still their *before* versions. At Derived commit `6463f1c`, App was still the *before* version. After `640854f`, all three were updated. This demonstrates a real, bounded eventual-consistency interval rather than a revision-atomic three-product publication.

Seven Source line-field changes affected **six** canonical Week-9 games, and all seven propagated into both the Derived and App data; the Derived computed market points also changed, yielding 19 changed fields in each of Derived and App. Joined by `Schedule.gameID`→`CanonicalGameID`→Derived `GameID`.

| Game | Observed Source line change | Post-change implied Away / Home points |
| --- | --- | --- |
| ARI @ SEA | Spread 11.5→10.5; Total 44.5→42.5 | 16 / 26.5 |
| BUF @ MIN | Total 46.5→45.5 | 24.5 / 21 |
| DEN @ CAR | Spread -3→-2.5 | 23 / 20.5 |
| GB @ NE | Spread 3→2.5 | 22 / 24.5 |
| JAX @ BAL | Spread -8.5→-9.5 | 26 / 16.5 |
| NYG @ PHI | Total 40.5→39.5 | 21.5 / 18 |

The **post-App commit** `FantasyGameContext.json` is Season 2026 Week 9 and has 15 games; **15/15** markets match the corresponding Derived market fields with zero missing App/Canonical joins or value differences. No alteration to NFL game scores or standings was inferred from the market changes.

## Live workflow execution, no-op, race handling

- [NFL Source Sync run #41674653245](https://github.com/Lolindhir/fantasy-app/actions/runs/41674653245) finished successfully. Its dependent `Publish global NFL Game Shared Derived` job ([job 126065931376](https://github.com/Lolindhir/fantasy-app/actions/runs/41674653245/job/126065931376)) ran the real-source clean-root restore test: **2 tests succeeded**. The materializer reported **28** season partitions (1999–2026), of which **27** were `Unchanged=true, Written=false` and **only 2026** was `Unchanged=false, Written=true`. The only Derived file in the publication commit was `data-derived/nfl-games/2026.json`; publish attempt **1** succeeded. This is **per-partition no-op behavior during a run with a changed current partition**, not evidence of a wholly no-op NFL Games job.
- [League Live run #41677851701](https://github.com/Lolindhir/fantasy-app/actions/runs/41677851701) finished successfully. Its `league` job ([job 126066258799](https://github.com/Lolindhir/fantasy-app/actions/runs/41677851701/job/126066258799)) reported that the target branch advanced during publication, discarded the old generated commit, rebuilt from latest `main`, and published successfully on **attempt 2**. The final log explicitly records writing `public/data/FantasyGameContext.json`. This is direct evidence that the existing rebuild-and-retry logic handled this particular race; it does not prove that all possible races are recoverable.
- This Source publication was a **full Source Sync** run. This specific event does not test the independent `odds-refresh.yml` observer or scoped-odds delegation path, despite those routes being supported by the workflow contract.

## Remaining G1/G5/G6 gaps

- A consumer-side current source-revision/content fingerprint is still absent. A downstream reader may see an older, structurally valid market snapshot during the observed 200-second publication sequence. This is a **verified temporal gap**, not a claim that the final observed App market content was stale.
- No end-to-end bound, full historical reproducibility, mandatory restore drill, rights/ownership approval, G5 cost accounting, or independent G6 review is implied. Do not create a parallel publisher or change missing-market semantics from this evidence alone.
