import type { League } from '../../../core/models/league.models';
import { LeagueTimelineComponent } from './league-timeline';

describe('LeagueTimelineComponent', () => {
  let component: LeagueTimelineComponent;

  beforeEach(() => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date('2026-09-04T10:00:00Z'));
    component = new LeagueTimelineComponent();
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('prioritizes the next waiver run during the season', () => {
    component.league = createLeague({
      NextWaiverRun: '2026-09-06T10:00:00Z',
      TradeDeadlineWeek: 99
    });

    expect(component.timeline?.primary.label).toBe('Next waiver run');
    expect(component.timeline?.secondary?.label).toBe('Playoffs start');
  });

  it('keeps a real future trade deadline as the secondary in-season milestone', () => {
    component.league = createLeague({
      NextWaiverRun: '2026-09-06T10:00:00Z',
      TradeDeadlineWeek: 8
    });

    expect(component.timeline?.primary.label).toBe('Next waiver run');
    expect(component.timeline?.secondary?.label).toBe('Trade deadline');
  });

  it('falls back to the existing in-season milestone order when no waiver run is available', () => {
    component.league = createLeague({
      NextWaiverRun: null,
      TradeDeadlineWeek: 8
    });

    expect(component.timeline?.primary.label).toBe('Trade deadline');
    expect(component.timeline?.secondary?.label).toBe('Playoffs start');
  });

  it('ignores a stale waiver timestamp', () => {
    component.league = createLeague({
      NextWaiverRun: '2026-09-03T10:00:00Z',
      TradeDeadlineWeek: 99
    });

    expect(component.timeline?.primary.label).toBe('Playoffs start');
    expect(component.timeline?.secondary).toBeNull();
  });
});

function createLeague(overrides: Partial<League> = {}): League {
  return {
    Status: 'In-Season',
    Phase: '',
    CurrentWeek: 1,
    FinalScoredWeek: 0,
    LastLeagueWeek: 17,
    PlayoffStartWeek: 14,
    TradeDeadlineWeek: 99,
    SeasonKickoff: null,
    CapDeadline: '',
    LeagueTimeZone: 'UTC',
    ...overrides
  } as League;
}
