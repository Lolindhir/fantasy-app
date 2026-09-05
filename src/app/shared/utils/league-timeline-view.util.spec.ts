import type { DecisionWindow, DecisionWindowsReadModel } from '../../core/models/decision-window.models';
import type { FantasyTeam, League } from '../../core/models/league.models';
import { buildLeagueTimelineView } from './league-timeline-view.util';

describe('league-timeline-view util', () => {
  const now = new Date('2026-09-04T10:00:00Z');

  it('keeps remaining timeline content when no Decision Window exists', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ NextWaiverRun: '2026-09-06T10:00:00Z', TradeDeadlineWeek: 8 }),
      drafts: [],
      decisionWindows: createModel([]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.operational.map(item => item.label)).toEqual(['Next Waiver Run']);
    expect(view?.milestones.map(item => item.label)).toEqual(['Trade deadline', 'Playoffs']);
  });

  it('shows lineup and waiver as co-equal operational deadlines', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ NextWaiverRun: '2026-09-06T10:00:00Z' }),
      drafts: [],
      decisionWindows: createModel([createWindow('2026-09-05T17:00:00Z')]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.operational.map(item => item.label)).toEqual(['Next Lineup Lock', 'Next Waiver Run']);
  });

  it('renders lineup cleanly when waiver is missing', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ NextWaiverRun: null }),
      drafts: [],
      decisionWindows: createModel([createWindow('2026-09-05T17:00:00Z')]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.operational.map(item => item.label)).toEqual(['Next Lineup Lock']);
  });

  it('does not let operational clocks suppress both future season milestones', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({
        CurrentWeek: 3,
        TradeDeadlineWeek: 8,
        PlayoffStartWeek: 14,
        NextWaiverRun: '2026-09-06T10:00:00Z'
      }),
      drafts: [],
      decisionWindows: createModel([createWindow('2026-09-05T17:00:00Z')]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.milestones.map(item => `${item.label}:${item.value}`)).toEqual([
      'Trade deadline:Week 8',
      'Playoffs:Week 14'
    ]);
  });

  it('removes a passed trade milestone without removing future playoffs', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ CurrentWeek: 9, TradeDeadlineWeek: 8, PlayoffStartWeek: 14 }),
      drafts: [],
      decisionWindows: createModel([]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.milestones.map(item => item.label)).toEqual(['Playoffs']);
  });

  it('shows a Playoffs lineup lock with League final as the season milestone', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ Status: 'Playoffs', CurrentWeek: 15, NextWaiverRun: null }),
      drafts: [],
      decisionWindows: createModel([createWindow('2026-09-05T17:00:00Z', 15)]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.operational.map(item => item.label)).toEqual(['Next Lineup Lock']);
    expect(view?.milestones.map(item => `${item.label}:${item.value}`)).toEqual(['League final:Week 17']);
  });

  it('omits lineup lock when no future fantasy window remains', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ Status: 'Playoffs', CurrentWeek: 17, NextWaiverRun: null }),
      drafts: [],
      decisionWindows: createModel([createWindow('2026-09-03T17:00:00Z', 17)]),
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.operational).toEqual([]);
    expect(view?.milestones.map(item => item.label)).toEqual(['League final']);
  });

  it('shows a neutral unavailable lineup tile without hiding other Overview timeline data', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({ NextWaiverRun: '2026-09-06T10:00:00Z', TradeDeadlineWeek: 8 }),
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: true,
      now
    });

    expect(view?.operational.map(item => item.kind)).toEqual(['lineup-unavailable', 'waiver']);
    expect(view?.operational[0].tone).toBe('unknown');
    expect(view?.milestones.map(item => item.label)).toEqual(['Trade deadline', 'Playoffs']);
  });

  it('preserves Pre-Season Season kickoff behavior', () => {
    const view = buildLeagueTimelineView({
      league: createLeague({
        Status: 'Pre-Season',
        SeasonKickoff: '2026-09-10T00:20:00Z',
        TradeDeadlineWeek: 8
      }),
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now
    });

    expect(view?.activeMode).toBeFalse();
    expect(view?.primary?.label).toBe('Season kickoff');
    expect(view?.secondary?.label).toBe('Trade deadline');
  });

  it('preserves Draft-Season and Off-Season draft milestones', () => {
    const upcomingDraft = [{
      name: 'Rookie Draft',
      statusClass: 'upcoming' as const,
      startDisplay: 'Sep 8, 18:00'
    }];

    const draftSeason = buildLeagueTimelineView({
      league: createLeague({ Status: 'Draft-Season' }),
      drafts: upcomingDraft,
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now
    });
    const offSeason = buildLeagueTimelineView({
      league: createLeague({ Status: 'Off-Season', CapDeadline: '' }),
      drafts: upcomingDraft,
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now
    });

    expect(draftSeason?.primary?.label).toBe('Rookie Draft');
    expect(offSeason?.primary?.label).toBe('Rookie Draft');
  });
});

function createLeague(overrides: Partial<League> = {}): League {
  return {
    Status: 'In-Season',
    Phase: '',
    Season: '2026',
    CurrentWeek: 1,
    FinalScoredWeek: 0,
    LastLeagueWeek: 17,
    PlayoffStartWeek: 14,
    TradeDeadlineWeek: 99,
    SeasonKickoff: null,
    CapDeadline: '',
    LeagueTimeZone: 'UTC',
    NextWaiverRun: null,
    Teams: [createTeam(1, 'Alpha'), createTeam(2, 'Bravo')],
    ...overrides
  } as League;
}

function createModel(windows: DecisionWindow[]): DecisionWindowsReadModel {
  return {
    SchemaVersion: 1,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 17,
    DecisionWindows: windows,
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: [
      {
        FantasyTeamID: 1,
        State: 'ready',
        ExpectedStarterCount: 13,
        StarterCount: 13,
        OpenStarterSlots: 0,
        Issues: []
      },
      {
        FantasyTeamID: 2,
        State: 'ready',
        ExpectedStarterCount: 13,
        StarterCount: 13,
        OpenStarterSlots: 0,
        Issues: []
      }
    ]
  };
}

function createWindow(startsAtUtc: string, week = 1): DecisionWindow {
  return {
    DecisionWindowID: startsAtUtc,
    Week: week,
    StartsAtUtc: startsAtUtc,
    Games: [{
      GameID: `game-${startsAtUtc}`,
      Week: week,
      AwayTeamID: 'NE',
      AwayTeamAbbr: 'NE',
      HomeTeamID: 'SEA',
      HomeTeamAbbr: 'SEA'
    }],
    ParticipatingNFLTeamIDs: ['NE', 'SEA'],
    FantasyContextState: 'available',
    AffectedFantasyTeams: []
  };
}

function createTeam(teamId: number, name: string): FantasyTeam {
  return {
    TeamID: teamId,
    Team: name,
    Owner: `${name} Owner`,
    OwnerAvatar: '',
    Avatar: ''
  } as FantasyTeam;
}
