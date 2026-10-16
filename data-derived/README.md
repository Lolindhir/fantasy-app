# Shared Derived Data

`data-derived/**` is the physical repository owner for deterministic,
reproducible, consumer-neutral **Shared Derived Data** under ADR-037/ADR-038.

It is deliberately separate from:

- `data-source/**`: provider evidence and canonical/normalized NFL or League facts;
- `public/data/**`: generated App delivery/read-model contracts;
- `fantasy-management/**`: consumer-specific Operations, analysis and decisions.

## PlayerWeekFantasy

The first product is:

`data-derived/player-week-fantasy/<CanonicalLeagueID>/<season>/<week>.json`

Canonical contract:

`.ai-context/manual/player-week-fantasy.yaml`

Materializer:

`tools/player_week_fantasy_materialize.py`

The dataset combines the canonical weekly NFL player population, explicit League
`ScoringSettings`, canonical scoring/finality evidence and leak-free historical
usage/scoring history into one league/week player state containing Actual,
V4-C Projection and the V4-C-PI1 Prediction Range.

Writers must be deterministic and preserve semantic no-op behavior. A source or
rule change that affects a documented dependency requires re-derivation; wall-clock
time alone does not.

Consumer-specific publication and identity adaptation happen downstream. The
shared layer remains keyed by `CanonicalPlayerID`; App/Sleeper identity joins
belong to the later App publisher.

## TeamWeekPerformance (in progress, not yet published)

Target dataset:

`data-derived/team-week-performance/<CanonicalLeagueID>/<season>/<week>.json`

Canonical contract:

`.ai-context/manual/team-week-performance.yaml`

Domain calculator and deterministic no-op writer:

`tools/team_week_performance.py`

It calculates all-roster hypothetical best-ball potential, actual starter points,
coaching efficiency, missed points and league-wide Best Manager/Best Coach winners
from canonical fantasy week matchups, historical positions and season-specific
slot eligibility. Starter, Bench, Taxi and IR/Reserve are all considered.
The shared result is designed for WeeklyRecaps/Overview, Team History, Season
Awards and other consumers; no consumer should recompute these domain values.

**Historical input adapter:** `tools/team_week_performance_sources.py`
validates both canonical NFL week finality and the League's scored-week
boundary, resolves week-specific player positions and delegates all starter/
FLEX slot eligibility to the existing FantasyRelevance PowerShell helpers
through `public/requests/utils/league/ExportWeeklyPerformanceSlots.ps1`.
Missing target-week positions may fall back to consistent earlier weeks
of the same season, then a finalized same-season NFL roster, then only a
**prior finalized NFL season** with a matching canonical player ID and no
conflicting older finalized season positions. Missing/contradictory historical
position evidence fails closed. Partial weekly team populations are rejected
against the historical league `Settings.num_teams`; actual starters must
fit the historical slot configuration. The fantasy
team's canonical matchup-week Players array is its complete retrospective
candidate pool under ADR-036; no intraweek transfer replay is required.
The adapter does not publish derived records.

**Controlled producer (Draft PR #993 only):**

```shell
# Single-week canonical audit; read-only by default.
python3 tools/team_week_performance_materialize.py --league nfl-reise --season 2026 --week 5 --require-pwf

# All registered leagues and seasons, all canonically scored weeks: read-only report.
python3 tools/team_week_performance_materialize.py --all-finalized

# Explicit full write only after every candidate week passes preflight.
python3 tools/team_week_performance_materialize.py --all-finalized --write
```

The historical batch discovers leagues from `data-meta` and season identities
from canonical League manifests, not App delivery or existing derived JSON.
It determines potential weeks from League `WeekStructure` and independently
validates finality, scoring, historical roster positions and PowerShell slot
rules for every selected week. With `--write`, **all selected weeks are
preflight-verified before any writes**, and a blocked week exits nonzero with
no writes. Missing PWF snapshots report `not-available` parity; existing
stale/non-final PWF is a blocker. Rebuilding PlayerWeekFantasy first is a
separate cross-product orchestration responsibility (#471/#697). Batch writes
are deterministic and second runs are no-ops.

The 2026 W03/W04/W05 partition files are currently committed **only
to Draft PR #993**, with canonical-source and PlayerWeekFantasy parity validation,
not to main. W03 was generated after #697 restored its final PWF Actual evidence;
its 202/202 canonical fantasy player scores agree with PWF, and the persisted
Award JSON is byte-identical to the existing deterministic generator output.
A historical read-only batch audit found all 39 scored weeks in 2024–2026
ready, with zero blocked weeks. A separate empty-derived-root integration test
regenerated all 39 weeks and confirmed a second full run changes zero files.
No automatic producer workflow, App publisher or Angular consumer is
activated yet.
