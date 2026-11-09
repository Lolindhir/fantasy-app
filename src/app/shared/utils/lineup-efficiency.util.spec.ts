import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import type { Player } from '../../core/models/player.models';
import {
  buildLineupEfficiencyLookup,
  buildOptimalLineupView,
  formatEfficiency,
  hasLineupEfficiency,
  slotLabel
} from './lineup-efficiency.util';

const recaps: WeeklyRecapsReadModel = {
  SchemaVersion: 1,
  Season: '2030',
  Weeks: [
    {
      Week: 1, KeyGames: [], KeyPlayers: [],
      TeamPerformance: [{
        FantasyTeamID: 7, ActualStarterPoints: 90, PotentialPoints: 100, MissedPoints: 10, EfficiencyPercent: 90,
        OptimalLineup: [
          { SlotID: 'FLEX-2', PlayerID: 'p1', CanonicalPlayerID: 'c1', Points: 12 },
          { SlotID: 'QB-1', PlayerID: null, CanonicalPlayerID: 'c2', Points: 20 }
        ]
      }]
    },
    { Week: 2, KeyGames: [], KeyPlayers: [], TeamPerformance: null }
  ],
  SeasonEfficiency: [{ FantasyTeamID: 7, ActualStarterPoints: 90, PotentialPoints: 100, MissedPoints: 10, EfficiencyPercent: 90, Weeks: 1 }]
};

describe('lineup efficiency util', () => {
  it('looks up generator values and keeps unknown as null', () => {
    const lookup = buildLineupEfficiencyLookup(recaps, '2030');
    expect(lookup.week(7, 1)?.EfficiencyPercent).toBe(90);
    expect(lookup.week(7, 2)).toBeNull();
    expect(lookup.week(8, 1)).toBeNull();
    expect(lookup.season('7')?.Weeks).toBe(1);
    expect(hasLineupEfficiency(lookup, [7], [1, 2])).toBeTrue();
  });

  it('ignores recaps of another season or files without the fields', () => {
    expect(buildLineupEfficiencyLookup(recaps, '2029').season(7)).toBeNull();
    const old: WeeklyRecapsReadModel = { SchemaVersion: 1, Season: '2030', Weeks: [{ Week: 1, KeyGames: [], KeyPlayers: [] }] };
    expect(hasLineupEfficiency(buildLineupEfficiencyLookup(old, '2030'), [7], [1])).toBeFalse();
  });

  it('formats unknown as an en dash, never as zero', () => {
    expect(formatEfficiency(null)).toBe('–');
    expect(formatEfficiency(82.3416)).toBe('82.3%');
    expect(formatEfficiency(0)).toBe('0.0%');
  });

  it('maps optimal slots to players and falls back for unknown players', () => {
    const player = { ID: 'p1', Name: 'Test Player', Position: 'WR', Picture: 'x.png' } as Player;
    const view = buildOptimalLineupView(buildLineupEfficiencyLookup(recaps, '2030').week(7, 1)!, [player]);
    expect(view.slots[0]).toEqual(jasmine.objectContaining({ name: 'Test Player', position: 'WR', points: 12 }));
    expect(view.slots[1].name).toBe('Unknown player');
    expect(slotLabel('FLEX-2')).toBe('FLEX');
  });
});
