# G5 – Real League Live samples and immutable Git blob decoding

Date: 2026-11-07. Parent [Issue #1263](https://github.com/Lolindhir/fantasy-app/issues/1263). Read-only research and a narrowly scoped **offline auditor compatibility correction**, not permission to activate an early exit.

## Actual public API / authenticated-connector evidence observed

The following GitHub Actions runs, individual job logs and Git commits were directly inspected through the connected GitHub API. **The combined \`league_live_run_receipt_audit.py\` CLI itself was not run against live GitHub with an independent PAT**, so these are source-grounded manual observations, not claims that the standalone Python runtime returned a success status.

### No-op control: 2026-11-06, Run 42270109163

[League Live run #42270109163](https://github.com/Lolindhir/fantasy-app/actions/runs/42270109163): created 18:22:28 UTC; completed 18:26:21 UTC; first attempt, success. Its start commit is \`dac0182ec5bb200e50ab12f4b80f0f0a217b4fb3\` (the workflow start SHA, **not** a generated output commit).

| Job | Evidence in original job log |
| --- | --- |
| Source sync | \`League source publish attempt 1/3\`; \`RawFilesChanged: 0\`; \`No canonical League data-source changes detected.\`; no actual source push receipt |
| Standings | \`Rebuild/publish attempt 1/3 for standings.\`; \`Generator produced no repository changes. Nothing to publish.\` |
| League | \`Rebuild/publish attempt 1/3 for league.\`; same no-op message. Derived producer statuses unchanged for 2026 league-transactions and league-drafts, and team-week-performance Week 8 with \`PlayerWeekFantasyParity.State=verified\` |

No fresh Stage publication SHA exists for this successful no-op. **Never substitute a previous commit as a run output receipt.** Neither current provider freshness nor historic PWF/TWP recovery is independently attested.

### Actual publication: 2026-11-07, Run 42343876022

[League Live run #42343876022](https://github.com/Lolindhir/fantasy-app/actions/runs/42343876022): created 05:42:38 UTC; completed 05:46:32 UTC; first attempt, success. Run starts on \`a9f05e452c789945ac14c5099e862d3cbbca30a5\`.

| UTC | Job | Immutable Git receipt |
| --- | --- | --- |
| 05:43:49 | Source raw | [\`2d2d65e7ce2b56e571d04bd994703c386fac6881\`](https://github.com/Lolindhir/fantasy-app/commit/2d2d65e7ce2b56e571d04bd994703c386fac6881), parent is run start, raw matchups Week 9 and rosters (+metadata) |
| 05:43:56 | Source canonical | [\`fc722e64939472830e835743e978342eda71f0c4\`](https://github.com/Lolindhir/fantasy-app/commit/fc722e64939472830e835743e978342eda71f0c4), parent is exactly raw commit, canonical matchups Week 9 and rosters |
| 05:44:43 | Standings | \`Generator produced no repository changes. Nothing to publish.\`; no new Standings commit |
| 05:46:29 | League | [\`5944bfff0e402b7ea5407133741aa6884470c7e5\`](https://github.com/Lolindhir/fantasy-app/commit/5944bfff0e402b7ea5407133741aa6884470c7e5), parent is exactly canonical commit, job log shows \`fc722e6..5944bff HEAD -> main\` and \`Rebuilt generated-data publish succeeded on attempt 1.\` |

The League commit changes exactly six paths: \`public/data/DecisionWindows.json\`, \`FantasyGameContext.json\`, \`League.json\`, \`MatchupProjections.json\`, \`Timestamps.json\`, and a \`public/data/backup/League_20261107_054625.json\`. It does **not** prove that the complete Derived products were re-created; the job's report identifies transactions/drafts as unchanged, TWP Week 8 unchanged with PWF parity verified.

At this immutable League commit, the selected App JSON files \`League\`, \`DecisionWindows\`, \`Matchups\`, \`FantasyGameContext\`, \`PlayerWeekFantasy\`, \`WeeklyRecaps\`, \`Timestamps\`, \`Drafts\`, \`Transactions\` each exist with Git blob SHA. The canonical league is \`nfl-reise\`, CurrentProviderLeagueID \`1354177383984267264\` (metadata/manifest consistent); \`UpcomingDraftCount=3\`, \`UpcomingDraftCountMode=PerDraftType\`, so minimum configured 2026–2029 draft files are present, as are 2024/2025 drafts. \`league-transactions\` has 2024–2026, team-week-performance Week 01–08 (2026), player-week-fantasy Week 01–09 (2026). This is Git identity/presence **not** semantic equality or independent provider freshness.

The League output commit is an ancestor of the later observed \`main\` tip; a later main revision does not, by itself, undermine the historical commit correlation. It does, however, invalidate any claim that this historical comparison could atomically authorize a *new* skip.

## Concrete offline tool failure mode and correction

\`tools/league_live_output_revision_audit.py:Snapshot.json\` previously called \`base64.b64decode(blob["content"], validate=True)\`. GitHub's \`git/blobs/{sha}\` API commonly returns an RFC-style Base64 payload with embedded \`LF\` line folds. Python strict base64 decoding rejects those line folds despite the Git blob content being valid. This caused a **false blocked audit** on real GitHub responses while existing synthetic test fixtures used one-line Base64.

The correction normalizes **only** \`CRLF\` and \`LF\` separators before strict Base64 decoding. Unexpected spaces/tabs/lone carriage returns/non-Base64 characters still fail closed. The size guard and independent \`sha1("blob " + byteLength + "\0" + bytes)\` integrity match remain unmodified. Two new deterministic test methods cover LF/CRLF success and malformed whitespace, content corruption and hash mismatch rejection. This is a GET-only **reader compatibility repair**; no new permissive freshness or publication decision.

## Recovery, freshness and race conclusions (bounded)

- A green League job and a successful individual \`PlayerWeekFantasyParity\` report **do not certify recovery of every historical or previously fail-soft Derived product**. The existing historical preflight is an independent read-only check when invoked, not a whole-pipeline recovery certificate.
- Current NFL finality is published by separate jobs. \`standings\` is correctly unconditional because its scored-week basis can change without a League Source commit. A no-op Source phase alone does not imply Standings/League is skippable.
- Source, NFL, odds, Derived and App publishers share \`main\` under several concurrency groups. The current rebuild-and-retry protections prevent stale committed outputs but **do not create an atomic proof that there is no upcoming invalidation**. A GET-only \`main\` comparison cannot establish such a critical section.
- As observed, the 2026-11-07 run spent roughly 64 seconds in Source sync, 45 in Standings, 104 in League. These are approximate job elapsed proxies, not proven net savings. A separately scheduled read-only preflight doing multiple API and Git-object fetches could itself consume more than it saves.

**Activation remains NO-GO:** \`safeToSkip=false\`, \`enforced=false\`, no production workflow changes. Next safe focus: empirical concurrent-writer/clock invalidation examples and bounded recovery-gap matrix; then compare a lightweight in-writer no-op optimization against whole-job early exit, with explicit risk and rollback before any elevated effect.

## Validation and rollback

No new test file, CI suite, workflow, scheduler, writer, data-source/derived/App output or permission. The two new tests run in the pre-existing League/PWF/TWP and Shared Derived/Consumer Fast suites; Core and Merge Gate remain mandatory. **Rollback** by reverting the scoped reader/tests/research change, with no production data to restore.
