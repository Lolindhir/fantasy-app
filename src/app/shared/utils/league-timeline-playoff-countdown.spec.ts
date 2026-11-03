import type { League } from '../../core/models/league.models';
import { buildLeagueTimelineView } from './league-timeline-view.util';

describe('league timeline playoff countdown', () => {
  it('keeps Playoffs visible by absolute kickoff and adds a live countdown', () => {
    const league = {
      Status: 'In-Season',
      CurrentWeek: 14,
      FinalScoredWeek: 13,
      LastLeagueWeek: 17,
      PlayoffStartWeek: 14,
      PlayoffStart: '2026-12-10T20:15:00Z',
      TradeDeadlineWeek: null,
      NextWaiverRun: null,
      SeasonKickoff: '2026-09-10T00:20:00Z',
      CapDeadline: '2026-06-30T23:59:59Z',
      Teams: []
    } as unknown as League;

    const view = buildLeagueTimelineView({
      league,
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now: new Date('2026-12-01T20:15:00Z')
    });

    expect(view?.milestones).toContain(jasmine.objectContaining({
      label: 'Playoffs',
      value: 'Week 14',
      detail: '9 days',
      gameweeksDetail: '0 gameweeks left'
    }));
  });

  it('falls back to the week-only milestone when no absolute kickoff is available', () => {
    const league = {
      Status: 'In-Season',
      CurrentWeek: 1,
      FinalScoredWeek: 0,
      LastLeagueWeek: 17,
      PlayoffStartWeek: 14,
      TradeDeadlineWeek: null,
      NextWaiverRun: null,
      SeasonKickoff: '2026-09-10T00:20:00Z',
      CapDeadline: '2026-06-30T23:59:59Z',
      Teams: []
    } as unknown as League;

    const view = buildLeagueTimelineView({
      league,
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now: new Date('2026-09-07T00:00:00Z')
    });

    expect(view?.milestones).toContain(jasmine.objectContaining({
      label: 'Playoffs',
      value: 'Week 14',
      detail: null,
      gameweeksDetail: '13 gameweeks left'
    }));
  });

  it('counts the current unfinished regular-season week, then drops it after completion', () => {
    const league = {
      Status: 'In-Season',
      CurrentWeek: 9,
      FinalScoredWeek: 8,
      LastLeagueWeek: 17,
      PlayoffStartWeek: 14,
      PlayoffStart: '2026-12-10T20:15:00Z',
      TradeDeadlineWeek: null,
      NextWaiverRun: null,
      Teams: []
    } as unknown as League;
    const milestoneForWeek = (currentWeek: number) => buildLeagueTimelineView({
      league: { ...league, CurrentWeek: currentWeek },
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now: new Date('2026-11-03T10:00:00Z')
    })?.milestones.find(item => item.label === 'Playoffs');

    expect(milestoneForWeek(9)?.gameweeksDetail).toBe('5 gameweeks left');
    expect(milestoneForWeek(10)?.gameweeksDetail).toBe('4 gameweeks left');
    expect(milestoneForWeek(13)?.gameweeksDetail).toBe('1 gameweek left');
    expect(milestoneForWeek(14)?.gameweeksDetail).toBe('0 gameweeks left');
  });

  it('uses scored-week evidence when CurrentWeek is zero because no regular-season games remain', () => {
    const league = {
      Status: 'In-Season',
      CurrentWeek: 0,
      FinalScoredWeek: 13,
      LastLeagueWeek: 17,
      PlayoffStartWeek: 14,
      PlayoffStart: '2026-12-10T20:15:00Z',
      TradeDeadlineWeek: null,
      NextWaiverRun: null,
      Teams: []
    } as unknown as League;

    const view = buildLeagueTimelineView({
      league,
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now: new Date('2026-12-09T20:15:00Z')
    });

    expect(view?.milestones).toContain(jasmine.objectContaining({
      label: 'Playoffs',
      value: 'Week 14',
      detail: '1 day 0 h',
      gameweeksDetail: '0 gameweeks left'
    }));
  });

  it('suppresses both playoff countdowns when the configured playoff week is invalid', () => {
    const league = {
      Status: 'In-Season',
      CurrentWeek: 9,
      FinalScoredWeek: 8,
      LastLeagueWeek: 17,
      PlayoffStartWeek: 18,
      PlayoffStart: '2026-12-10T20:15:00Z',
      TradeDeadlineWeek: null,
      NextWaiverRun: null,
      Teams: []
    } as unknown as League;

    const view = buildLeagueTimelineView({
      league,
      drafts: [],
      decisionWindows: null,
      decisionWindowsUnavailable: false,
      now: new Date('2026-11-03T10:00:00Z')
    });

    // With no other upcoming milestones or operational items, the timeline is absent.
    expect(view).toBeNull();
  });
});
