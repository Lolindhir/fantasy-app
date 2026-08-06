# Dynasty Data Lab Source Audit

Audit date: 2026-08-06

## Decision

Dynasty Data Lab is approved only as a manual research and plausibility source.

It must not be used as an automated ranking provider, stored snapshot source or production dependency under the current access conditions.

```yaml
provider: dynasty-data-lab
ranking_kind: adp
ranking_scope: dynasty-startup
source_population: quality-filtered Sleeper drafts
status: manual_reference_only
automated_fetching: rejected
snapshot_storage: rejected
production_dependency: rejected
```

## What the source measures

Dynasty Data Lab describes its startup ADP as being calculated from real Sleeper dynasty drafts rather than mock drafts or expert consensus. The source therefore represents observed dynasty startup draft behavior.

This signal is distinct from:

- FantasyPros expert consensus
- FantasyCalc trade-market values
- Fantasy Football Calculator redraft mock-draft ADP

It must be interpreted as draft cost, not as a projection, expert ranking, trade value or league-specific recommendation.

## Publicly documented strengths

The provider publicly states that it offers:

- dynasty startup and rookie ADP
- real Sleeper draft observations
- hourly ADP refreshes
- historical ADP depth
- quality filtering for source drafts
- filters for startup or rookie drafts, date ranges, team count, passing-touchdown scoring, PPR, tight-end premium, starter count, roster size and best-ball status
- a free basic plan for browser use

These characteristics make the source useful for manual cross-checks, trend inspection and format comparisons.

## League-format limitations

The observed public filter range supports conventional dynasty league sizes rather than the actual six-team league.

The source does not directly model the complete Mighty Giants format:

- six teams
- two fixed quarterbacks
- two fixed tight ends
- league-specific scoring
- salary and cap rules
- the resulting unusually high replacement level at running back and wide receiver

Any manual use therefore requires a separate league-format interpretation. Source ADP must never be copied directly into a Mighty Giants player ranking.

## Access and automation audit

The audit found a free browser-facing basic tier, but did not find an officially documented public API or a documented complete CSV or JSON export for the ADP dataset.

The ranking and comparison tools are delivered through a dynamic web application. Internal browser requests, undocumented endpoints or session-dependent calls are not a stable source contract.

No automated integration will therefore be created that relies on:

- scraping rendered pages
- reverse engineering internal application endpoints
- storing account credentials or browser sessions
- regularly copying complete ranking tables into the repository

The absence of a discovered official interface is recorded as an audit result, not as a claim that no private or future interface can exist.

## Operational rules

- Use Dynasty Data Lab only for manual research when an additional dynasty-startup market perspective is useful.
- Cite the provider when conclusions rely on its displayed ADP or trend data.
- Record the concrete observation date and selected filters in any saved analysis.
- Do not treat headline site-wide draft counts as the sample size of a specific filtered ranking.
- Prefer the sample count displayed for the exact filter combination when available.
- Do not add a fetcher, scheduled workflow, login secret or stored snapshot directory for this provider.
- Re-audit only if the provider later publishes a complete official machine-readable export or API that is free and usable without additional permission or cost.

## Audit sources

- https://dynastydatalab.com/
- https://dynastydatalab.com/adp
- https://dynastydatalab.com/adp/compare
- https://dynastydatalab.com/adp/diff/

## Rationale summary

Dynasty Data Lab is a strong manual source because its observed startup ADP adds a perspective not supplied by the active automated providers. It is rejected as an automated provider because the audit did not establish a complete, documented and stable machine-readable interface under the user's constraints of no additional cost and no provider permission request.
