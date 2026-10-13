# Shared Derived Data

`derived-data/**` is the physical repository owner for deterministic,
reproducible, consumer-neutral **Shared Derived Data** under ADR-037/ADR-038.

It is deliberately separate from:

- `source-data/**`: provider evidence and canonical/normalized NFL or League facts;
- `public/data/**`: generated App delivery/read-model contracts;
- `fantasy-management/**`: consumer-specific Operations, analysis and decisions.

## PlayerWeekFantasy

The first product is:

`derived-data/player-week-fantasy/<CanonicalLeagueID>/<season>/<week>.json`

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

`derived-data/team-week-performance/<CanonicalLeagueID>/<season>/<week>.json`

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

**Current checkpoint:** The calculator, writer and tests exist, but no
producer job, real derived-data partition, App publisher or frontend consumer
has been activated. Real full-repository Python integration, PowerShell
slot-bridge execution and canonical scoring parity remain publication gates.
The week-scoped fantasy ownership pool is settled.
