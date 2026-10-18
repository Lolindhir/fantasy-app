# Podcast Extraction Rules

Purpose: central extraction rules for all podcast sources in Fantasy Management.

Use these rules for Stoned Lack, Down Set Talk, Football Bromance and future podcast sources.

The detailed source/Knowledge/Analysis separation is defined in:

`fantasy-management/_ai/PODCAST_SOURCE_MODEL.md`

## Core rule

Podcast extraction is source work, not final Fantasy Management analysis.

A podcast extraction answers:

> What did the podcast say, how did it argue, and which fantasy-relevant entities and statements appeared?

It must not answer:

> What should Mighty Giants do?

That belongs to later Knowledge derivation and Analysis.

## Canonical source configuration

Podcast source identity, weighting and profile comparison are maintained centrally in:

`fantasy-management/_ai/source-registry.json`

Podcast-specific quirks, recurring wording patterns and interpretation notes belong next to the source in:

`sources/podcasts/{source_id}/SOURCE_NOTES.md`

Do not maintain source weights in multiple places.

## Central player identity registry

Podcast-independent player identity mappings, aliases and transcript-error resolutions are maintained centrally in:

`fantasy-management/_ai/entity-resolution/player_identity_registry.json`

Use this registry before and during every podcast/source extraction that mentions players.

The registry is not a source take, Knowledge, a ranking or a recommendation.

Add confirmed reusable aliases or transcript-error mappings when discovered. Do not add speculative mappings.

## Entity aliases and transcript name resolution

Raw source text must stay unchanged. Do not rewrite transcript wording.

In `episode.md`, use canonical names only when confidence is sufficient. Do not expose raw aliases, resolution methods or confidence metadata solely for audit purposes.

In `takes.json` and `mentions.json`, preserve the raw mention and compact resolution metadata.

For every player take, `takes.json` must include:

- `raw_entity_mention`
- verified canonical `entity`, otherwise `null`
- compact `entity_resolution`

Allowed resolution methods:

- `registry`
- `external_verification`
- `context_inference`
- `manual_confirmation`
- `none`, only for unresolved entities

Allowed statuses:

- `confirmed`
- `ambiguous`
- `unresolved`

Ambiguous and unresolved entries use `entity: null` and explain the uncertainty when useful.

Do not invent or autocomplete names from memory. A plausible-looking name is still wrong when it is not verified against the raw context, registry or an appropriate identity source.

## Episode package rule

Each current processed episode is one package:

```text
fantasy-management/sources/podcasts/{source_id}/episodes/{year}/{episode_id}/
  raw/
    manifest.md
    part01.md
    part02.md
  episode.md
  takes.json
  mentions.json
  index.json
```

For small transcripts, `raw/source.md` may replace split parts.

New and fully reworked packages use `package_schema_version: 2`.

## Required outputs

A normal schema-version-2 extraction creates:

1. unchanged raw source material
2. `episode.md` as detailed German reader-facing preparation
3. `takes.json` as structured source takes
4. `mentions.json` as the complete technical entity and coverage audit
5. `index.json` as package metadata, counts and status

Do not update global indexes or active Knowledge during normal extraction.

## `episode.md` rule

`episode.md` is the primary human-readable record of the episode.

It is not a short executive summary and must not be optimized for brevity. Preserve the fantasy-relevant content as fully as practical:

- episode topic and context
- hosts' central arguments and evaluation criteria
- reasoning chains, not only conclusions
- positive, negative and uncertain statements
- agreements and disagreements
- complete safely reconstructable rankings, tiers, boards or mock-draft structures
- player, team, position, coach and scheme context needed to understand the source
- format distinctions
- strategy implications stated by the source
- source-level conclusion

For ranking, tier, mock-draft or list episodes:

- reproduce the complete safely reconstructable source order
- explain every ranked subject sufficiently
- preserve positive cases, risks, uncertainty and host differences
- preserve format dependency
- include source-derived closing views only when the episode supports them

For mixed episodes, include all substantive segments, including news, rankings and live drafts. Do not silently stop processing when the headline segment ends.

`episode.md` must not contain technical extraction metadata:

- file inventories
- raw-name or alias registers
- entity-resolution status or confidence
- complete mention or coverage tables
- take or mention IDs
- technical timestamp appendices
- package paths
- extraction, review or validator status
- machine-readable companion-file references
- Mighty Giants recommendations
- league-specific advice not stated by the source

## Reader-facing coverage rule

`episode.md` must include every ranking subject, news subject and substantive evaluation in enough detail to understand the source's argument.

Context-only entities appear naturally only when needed for the argument.

Do not append a complete technical entity or mention register. Passing references, historical comparisons, depth-chart names and unresolved transcript forms may remain exclusively in `mentions.json` when they add no substantive reader value.

## `takes.json` rule

Use one categorized `takes.json` per episode with these buckets:

- `players`
- `teams`
- `positions`
- `nfl`
- `fantasy`
- `other`

Create standalone takes for:

- every ranking or tier subject
- every explicit recommendation label
- every substantive positive, negative or uncertain evaluation
- every independent role, injury, market, strategy or format thesis
- every meaningful disagreement
- substantive segments outside the headline topic, including a live mock draft

A take must preserve the source claim, reasoning, risks, formats, sentiment, conviction and evidence. Do not collapse materially distinct claims merely to reduce file size.

Pure comparisons, teammates, depth-chart competitors, historical examples and passing references do not automatically need standalone takes. They remain in `mentions.json`.

## `mentions.json` rule

`mentions.json` is the complete technical entity and coverage audit.

Create it in an independent second pass over the entire raw source, not by rereading only `episode.md` or `takes.json`.

Include every player mention or possible player mention and every other named entity carrying fantasy-relevant context, including:

- ranking subjects
- substantive takes
- news subjects
- comparisons
- teammates and competitors
- injury and scheme context
- historical examples
- live-draft names
- passing references
- ambiguous and unresolved transcript forms
- false positives when preserving them helps auditability

A ranking, substantive or news subject requires:

- a standalone take
- `coverage.episode_md: true`
- substantive reader-facing coverage

Context-only or unresolved mentions may use `coverage.episode_md: false` when intentionally audit-only. Add `coverage.note` explaining the omission.

The technical register belongs here, never in `episode.md`.

## Coverage audit rule

Schema-version-2 packages require at least two distinct passes.

### Pass A: content extraction

Read the entire raw source and create the detailed `episode.md` and `takes.json`.

### Pass B: independent entity sweep

Read the entire raw source again with a different objective:

1. collect every player name and possible player name
2. collect other fantasy-relevant named entities
3. resolve identities or preserve uncertainty
4. classify each mention
5. compare mentions with `episode.md` and `takes.json`
6. add omitted segments, subjects, takes or unresolved forms
7. calculate counts from the finished files

The audit is complete only when:

- all required subjects have valid standalone takes
- all required subjects are substantively covered in `episode.md`
- all player takes are covered by matching mention entries
- context-only and unresolved forms remain visible
- audit-only omissions have notes
- all links resolve
- calculated counts match `index.json`
- uncovered mentions equal zero

A package is complete only when `coverage_audit.status` is `completed`.


## In-season source-first coverage and evidence QA (approved pilot refinement)

These requirements apply to weekly matchups, Start/Sit shows, Q&A and mixed episodes in addition to the independent full entity mention sweep. **Unresolved identities are acceptable intermediate work state; missing source statements are not.**

### Source-first claim and question sweep

Before marking any Content Map segment `takes_complete`:

1. Read every original SRT/raw cue in the segment **again**, independently of its draft take IDs, planned claims or generated summary.
2. Inventory every explicit start/sit, player-vs-player question and answer, weekly rank, winner/score/game-script call, materially reasoned positive/negative outlook, and source-expressed injury/usage condition.
3. Inventory standalone *non-weekly* trade/acquire/avoid/waiver-budget or other strategic statements independently, even if the player has an existing weekly take.
4. Record a traceable source obligation and matching take ID for each such statement. Passing teammate references do not automatically require new takes; however a brief explicit recommendation does.
5. Reconcile **source inventory -> authored takes**, not merely **planned takes -> authored takes**. The latter validates internal consistency but cannot prove source recall.
6. A complete segment includes its late questions, follow-up answers and sidebars; do not omit content after a nominal outro.

The source-first inventory is a separate editorial coverage check, not a replacement for the full second-pass `mentions.json` entity audit. Schema-valid packages can still fail this editorial review. Never declare a segment complete solely because its original three broad claims or IDs were covered.

### Evidence and source/QA separation

- Every substantive take must include a literal, non-placeholder source quote hint and the original raw part/cue-range. A take with several independent statements needs multiple evidence points when one cue cannot support them all.
- Anchor the evidence to the actual relevant cue; do not use the first cue of an entire several-minute discussion merely for convenience. Preserve SRT timing precision as *cue precision*, not as proof of audio accuracy.
- Quote hints must be substrings of unchanged source text. Fabricated or paraphrased hints, `TODO`, or pointers saying only 'see raw part' do not qualify.
- `risks`, `conditions`, `uncertainties` and `host_views` describe **what the source expressed**. Extraction-only concerns (ASR distortion, unverified name, absence of audio, suspicious chronology, weak attribution or missing external fact verification) belong in `entity_resolution.reason`, `notes` or a separate QA report.
- Never assign named speakers from an unverified automatic diarization label. Distinct but unattributed speaker positions may be represented with explicit neutral labels and an attribution warning.
- Classify `source_depth` by the source's actual reasoning (passing / brief / substantive / deep / structural), not by the length of JSON or topic importance. A one-sentence Q&A start decision is often `brief`; a multi-mechanism game argument may be `deep`.

### Temporal, matchup and identity boundaries

- One structured `game` subject denotes **one game**; don't join two games simply because they share a betting total or weekly rubric. Retain different source confidence between games.
- A weekly lineup preference and a longer-term buy/sell/hold/avoid thesis can be two independent takes for the same player. Preserve their time horizon and reason separately.
- A transcript-context identity hypothesis is not a confirmed canonical identity. Use `entity: null` with `ambiguous` or `unresolved` status until the claimed identity is sufficiently verified. Preserve raw mentions and plausible candidates in QA notes instead of silently resolving them.
- Identity-resolution status can remain open during a pilot. Do not discard the original source call simply because identity is unresolved; also do not publish an unsupported alias or treat source news as verified NFL fact.
- Maintain extraction fidelity separately from later source-calibration and Mighty Giants lineup decisions.

## Multi-pass extraction and entity-first preflight (approved pilot guidance)

**Primary quality goal:** maximize source-statement and mention recall before optimizing a readable synthesis. A fluent or schema-valid summary is not proof that nothing was omitted. Do not ask one generative pass to both select the "important" material and prove its own completeness.

### Preflight A: high-recall raw entity candidates

- Scan the **complete immutable raw transcript**, in short cue-bounded windows with overlap where discussion boundaries require it, for all potential player, coach, staff, host, team, league and other fantasy-relevant named entities. Include first names, surnames, partial names, ambiguous proper nouns, nicknames, phonetic ASR distortions and possible false positives.
- Preserve each **exact original text span**, raw-part/cue/time reference and occurrence, together with a *candidate* kind and uncertainty. Do not silently replace a raw form with a cleaned canonical name. A normal-looking dictionary word can be a surname, while an unusual word is not necessarily a name; use context, not merely German/English dictionary membership.
- Keep candidate detection **independent of resolution**. Only after the raw candidate register exists should the identity registry, verified league/NFL facts or external references be used to resolve entities. If unresolved or ambiguous, retain the raw candidate with a null canonical entity and appropriate status; this does not block collecting its claims.
- A mention is **not** automatically a standalone take. Ranking subjects, explicit Start/Sit recommendations, materially evaluated players, news subjects and meaningful independent theses require takes. Passing comparisons, teammates and other context-only mentions can be technical mentions without fabricated evaluations.
- This preflight candidate register complements but does **not** replace the later independent full `mentions.json` audit. The final audit must reread the raw source, including names missed in preflight.

### Preflight B: independent source-statement inventory

- In a separate task, enumerate all individually testable spoken claims, questions and answers: rankings, Start/Sit preferences, score/winner calls, direct comparisons, news, injury/usage contingencies, relevant figures, host dissent, structural team/scheme arguments and independent long-term trade or waiver theses. Do **not** collapse a contrary host view into the majority view.
- Record each obligation with exact cue/time evidence. It may refer to an unresolved name or even to a game/team/strategy with **no personal name**; no source claim may disappear because preflight A found no verified player.
- The entity inventory and claim inventory are complementary coverage axes. Link claims to candidate occurrences when supported, but do not derive the claims inventory only from a name list or derive the name list only from generated takes.

### Distinct generation, review and repair passes

1. **Pass 1 — inventory:** produce the entity candidates and source-statement inventory from raw transcript, separately from the finished takes and article.
2. **Pass 2 — extraction:** author source-faithful Content Map/takes using Golden Set dimensions and both inventories; evidence, separate time horizons and dissent remain explicit. Freeze the first-pass result for calibration before any quality fixes.
3. **Pass 3 — independent QA:** reread the raw cues with the *different* objective of discovering omissions, over-merges, invented statements, unsupported identities and misplaced evidence. Independently sweep named entities **and** claims, then reconcile raw -> inventories -> takes/article as well as takes -> raw. Preserve an audit of what was absent or partial; do not score only internal planned-take links.
4. **Pass 4 — targeted repair:** if QA finds defects, add or correct affected inventories, takes and related content without silently changing the frozen first-pass baseline. Rerun deterministic linkage, exact-span/quote checks, and a source-focused QA pass on the changed source ranges and their context. Repeat repair/review **as needed**, rather than rerunning identical broad summaries without new objectives.
5. **Final gate:** no unaddressed **required** claim/mention, invented source statement, untraceable evidence or conflated host stance. Record unresolved ASR identities, source-audio uncertainties and ambiguous passages as bounded review items; unresolved identity alone need not block an intermediate extraction, but never claim full fidelity or publication readiness with blocking uncertainties.

Different prompts, read order or independent reviewers/models may expose additional gaps. Repeated passes by the same model are **not statistically independent** and cannot establish a measured 100% recall rate for unknown, undiscovered source statements. Prefer a separate reviewer or blind/holdout segment for production-readiness evaluation; compare results to the original source, not to the model's own summary.

**Implementation boundary:** these are required *editorial* passes for new/reworked packages. Current work-package schemas, Golden Set profiles and deterministic validator do not yet implement a first-class preflight inventory or automatically detect omitted raw claims. Until tooling is explicitly designed and validated, preserve the preflight inventories and QA findings in private pilot working artifacts/process review; do not assert automated enforcement, change storage/publication targets, or upload unlicensed raw transcripts to a public repository.

## `index.json` rule

`index.json` is the local technical map. It may contain:

- package schema version
- source and episode identity
- dates
- package paths
- raw status
- take and mention counts
- identity-resolution status
- coverage-audit status
- Knowledge derivation status
- rework notes

Keep all such metadata out of `episode.md`.

Recommended status conventions:

- `needs_review`: extraction exists but a required review, second pass or validator is open
- `needs_rework`: known substantive or structural defects remain
- `active_source_package`: all completeness gates pass and the package is usable as source evidence

Do not set `active_source_package` or `coverage_audit.status: completed` merely to silence a validator.

## JSON formatting rule

Fantasy Management JSON created or manually maintained by AI must be human-readable and pretty-printed:

- UTF-8
- two-space indentation
- one property per line
- arrays on multiple lines, including single-item arrays
- one array item per line
- nested arrays and objects on separate lines
- stable key order where practical
- trailing newline

Do not commit minified JSON or an entire object on one line.

## Raw source rule

Store raw transcripts or notes unchanged.

For split transcripts:

- use ordered `partNN.md` files
- list every part in `raw/manifest.md`
- require contiguous numbering
- treat ordered concatenation as the complete raw source

A placeholder raw file is not a completed source. Mark missing raw material explicitly in `index.json`.

## Knowledge separation rule

Podcast packages are source evidence, not active Knowledge.

Knowledge may be derived later under:

```text
fantasy-management/knowledge/
  players/
  teams/
  positions/
  nfl/
  fantasy/
```

A separate derivation step decides what remains useful for the league and current context.

## Completeness gate

Before marking a schema-version-2 package complete, verify:

1. raw source is complete and referenced
2. every raw part was read in Pass A
3. every raw part was read again in Pass B
4. `episode.md` is detailed German source preparation without technical metadata
5. all substantive episode segments are represented
6. complete rankings, tiers and mock-draft structures are preserved when safely reconstructable
7. every ranked subject has sufficient explanation
8. source reasoning, risks, disagreement and format distinctions are preserved
9. `takes.json` uses all six categories
10. player takes contain inline raw mention, canonical entity and resolution
11. all ranking, substantive and news subjects have standalone takes
12. materially distinct claims are not collapsed improperly
13. `mentions.json` conforms to its schema
14. every player mention or possible player mention from Pass B is registered
15. context, comparison, historical and unresolved mentions are retained
16. every required mention links to a valid take
17. every player take has a matching subject mention
18. calculated take and mention counts match `index.json`
19. uncovered mentions equal zero
20. JSON formatting follows the repository rule
21. recurring confirmed aliases are stored in the central registry
22. `coverage_audit.status` is `completed`
23. Knowledge derivation is absent or stored separately
24. package and coverage validators pass
25. validator unit tests pass

If any required item fails, use `needs_review` or `needs_rework` and document the blocker.

Legacy schema-version-1 packages may remain historical packages without `mentions.json`; they do not provide the same coverage guarantee.

## Recommendation rule

Podcast output is source context, not a final recommendation.

Final Mighty Giants recommendations belong under `fantasy-management/analyses/` and must combine current league data, derived Knowledge, relevant source evidence and current market/news context.
