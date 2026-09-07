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
      detail: '9 days'
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
      detail: null
    }));
  });
});
