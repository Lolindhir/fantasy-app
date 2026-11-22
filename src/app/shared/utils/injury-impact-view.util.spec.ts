import type { InjuryImpactSeason } from '../../core/models/injury-impact.models';
import { buildInjuryImpactByTeam, formatImpact } from './injury-impact-view.util';

function season(overrides: Partial<InjuryImpactSeason> = {}): InjuryImpactSeason {
  return {
    Season: 2026,
    AsOf: { LeagueScoredWeek: 3 },
    Teams: [
      { CanonicalLeagueRosterID: 'r1', TeamID: 1, Owner: 'A', TeamName: 'Team A' },
      { CanonicalLeagueRosterID: 'r2', TeamID: 2, Owner: 'B', TeamName: 'Team B' }
    ],
    Weeks: [
      { Week: 1, Teams: [
        { CanonicalLeagueRosterID: 'r1', Impact: 10, IsLowerBound: false, HasUnknownEvidence: false },
        { CanonicalLeagueRosterID: 'r2', Impact: 0, IsLowerBound: false, HasUnknownEvidence: false }
      ] },
      { Week: 3, Teams: [
        { CanonicalLeagueRosterID: 'r1', Impact: 5, IsLowerBound: true, HasUnknownEvidence: true },
        { CanonicalLeagueRosterID: 'r2', Impact: 2.5, IsLowerBound: false, HasUnknownEvidence: false }
      ] }
    ],
    UnavailableWeeks: [{ Week: 2, Reason: 'no verified partition' }],
    SeasonTotals: [
      { CanonicalLeagueRosterID: 'r1', Impact: 15, ImpactPerWeek: 7.5, WeeksComputed: 2, WeeksWithImpact: 2, IsLowerBound: true, Undeterminable: 1,
        PeakWeek: { Week: 1, Impact: 10 }, TopPlayers: [{ CanonicalPlayerID: 'P1', SingleReturnImpact: 9.04, Weeks: 2 }] },
      { CanonicalLeagueRosterID: 'r2', Impact: 2.5, ImpactPerWeek: 1.25, WeeksComputed: 2, WeeksWithImpact: 1, IsLowerBound: false, Undeterminable: 0,
        PeakWeek: { Week: 3, Impact: 2.5 }, TopPlayers: [] }
    ],
    ...overrides
  };
}

describe('injury impact view utility', () => {
  it('marks lower bounds with a leading ≥ and keeps unknown values unavailable', () => {
    expect(formatImpact(12.34, true)).toBe('≥ 12.3');
    expect(formatImpact(12.34, false)).toBe('12.3');
    expect(formatImpact(null, false)).toBe('–');
  });

  it('builds one bar per week on a shared scale and never turns a missing week into zero', () => {
    const view = buildInjuryImpactByTeam(season()).get('1')!;
    expect(view.bars.map(bar => bar.week)).toEqual([1, 2, 3]);
    expect(view.bars[0].heightPercent).toBe(100);
    expect(view.bars[1]).toEqual(jasmine.objectContaining({ unavailable: true, impact: null, heightPercent: 0 }));
    expect(view.bars[2]).toEqual(jasmine.objectContaining({ lowerBound: true, unknownEvidence: true, heightPercent: 50 }));
    expect(view.hasUnknownEvidence).toBeTrue();
    expect(view.totalDisplay).toBe('≥ 15.0');
    expect(view.peakDisplay).toBe('Week 1 (10.0)');
  });

  it('gives a team without any impact an empty baseline and no peak', () => {
    const noImpact = season({
      Weeks: [{ Week: 1, Teams: [{ CanonicalLeagueRosterID: 'r2', Impact: 0, IsLowerBound: false, HasUnknownEvidence: false }, { CanonicalLeagueRosterID: 'r1', Impact: 0, IsLowerBound: false, HasUnknownEvidence: false }] }],
      UnavailableWeeks: [],
      SeasonTotals: [{ CanonicalLeagueRosterID: 'r2', Impact: 0, ImpactPerWeek: 0, WeeksComputed: 1, WeeksWithImpact: 0, IsLowerBound: false, Undeterminable: 0, PeakWeek: { Week: 1, Impact: 0 }, TopPlayers: [] }]
    });
    const view = buildInjuryImpactByTeam(noImpact).get('2')!;
    expect(view.bars[0].heightPercent).toBe(0);
    expect(view.peakDisplay).toBeNull();
    expect(view.totalDisplay).toBe('0.0');
  });

  it('resolves top players through the generator references and tolerates files without references', () => {
    const withRefs = season({ PlayerRefs: { P1: { Name: 'A Player', Position: 'WR', Picture: 'x.png' } } });
    expect(buildInjuryImpactByTeam(withRefs).get('1')!.topPlayers[0]).toEqual({
      id: 'P1', name: 'A Player', position: 'WR', picture: 'x.png', impactDisplay: '9.0', weeks: 2
    });
    expect(buildInjuryImpactByTeam(season()).get('1')!.topPlayers[0].name).toBe('Unknown player');
  });

  it('returns nothing for a missing season', () => {
    expect(buildInjuryImpactByTeam(null).size).toBe(0);
  });
});
