import type { PlayoffOddsStatus, ScheduleOutlookReadModel } from '../../core/models/schedule-outlook.models';
import {
  formatPlayoffCell,
  formatPlayoffPercent,
  ordinal,
  playoffLockedPlace,
  playoffMarker,
  playoffPillText,
  resolvePlayoffOdds,
  resolveTeamScheduleOutlook
} from './schedule-outlook-view.util';

function outlook(overrides: Partial<ScheduleOutlookReadModel['PlayoffOdds']> = {}, season = 2026): ScheduleOutlookReadModel {
  const team = (TeamID: number, Status: PlayoffOddsStatus, p: number, places: number[]) => ({
    TeamID, Record: { Wins: 1, Losses: 1, Ties: 0 }, PlaceProbabilities: places,
    PlayoffProbability: p, EliminationProbability: 1 - p, Status
  });
  return {
    Season: season,
    RegularSeason: {
      Teams: [{
        TeamID: 1, RemainingGames: 2, RemainingSoSClass: 'harder',
        Upcoming: [
          { Week: 5, OpponentTeamID: 2, OpponentClass: 'weaker' },
          { Week: 6, OpponentTeamID: 3, OpponentClass: null }
        ]
      }]
    },
    PlayoffOdds: {
      Model: 'm', Available: true, Reason: null,
      Provenance: { PlayoffTeams: 1, RegularSeasonComplete: false },
      Teams: [
        team(1, 'clinched', 1, [1, 0, 0]),
        team(2, 'alive', 0.004, [0, 0.004, 0.996]),
        team(3, 'eliminated', 0, [0, 0, 1])
      ],
      ...overrides
    }
  };
}

describe('schedule outlook view', () => {
  it('formats alive percentages as whole numbers with <1% and >99% bounds', () => {
    expect(formatPlayoffPercent(0.004)).toBe('<1%');
    expect(formatPlayoffPercent(0.4632)).toBe('46%');
    expect(formatPlayoffPercent(0.996)).toBe('>99%');
    expect(formatPlayoffPercent(0.9999)).toBe('>99%');
    expect(formatPlayoffPercent(1)).toBe('100%');
    expect(formatPlayoffPercent(0)).toBe('0%');
    expect(formatPlayoffCell(0.9972)).toBe('>99');
    expect(formatPlayoffCell(1)).toBe('100');
    expect(formatPlayoffCell(0)).toBe('');
  });

  it('maps status to pill text and Overview markers', () => {
    const odds = resolvePlayoffOdds(outlook(), 2026)!;
    expect(playoffPillText(odds.teams.get(1)!)).toBe('Clinched 1st');
    expect(playoffPillText(odds.teams.get(2)!)).toBe('<1%');
    expect(playoffPillText(odds.teams.get(3)!)).toBe('Eliminated');
    expect(playoffPillText({ teamId: 9, status: 'clinched', probability: 1, places: [1, 0, 0, 0] })).toBe('Clinched 1st');
    expect(playoffPillText({ teamId: 9, status: 'clinched', probability: 1, places: [0, 0, 1, 0] })).toBe('Clinched 3rd');
    expect(playoffPillText({ teamId: 9, status: 'clinched', probability: 1, places: [0, 0.5, 0.5, 0] })).toBe('Clinched');
    expect(ordinal(1)).toBe('1st');
    expect([2, 3, 4, 11, 12, 22].map(ordinal)).toEqual(['2nd', '3rd', '4th', '11th', '12th', '22nd']);
    expect(playoffLockedPlace(odds, 1)).toBe(1);
    expect(playoffLockedPlace(odds, 2)).toBeNull();
    expect(playoffMarker(odds, 1)).toBe('x');
    expect(playoffMarker(odds, '3')).toBe('e');
    expect(playoffMarker(odds, 2)).toBeNull();
    expect(odds.hasDecidedTeam).toBeTrue();
    expect(odds.playoffTeams).toBe(1);
  });

  it('shows nothing when unavailable, from another season or after the regular season', () => {
    expect(resolvePlayoffOdds(null, 2026)).toBeNull();
    expect(resolvePlayoffOdds(outlook({ Available: false }), 2026)).toBeNull();
    expect(resolvePlayoffOdds(outlook(), 2027)).toBeNull();
    expect(resolvePlayoffOdds(outlook({ Provenance: { PlayoffTeams: 1, RegularSeasonComplete: true } }), 2026)).toBeNull();
    expect(resolvePlayoffOdds({ ...outlook(), PlayoffOdds: undefined }, 2026)).toBeNull();
  });

  it('exposes strength classes per upcoming week and skips unknown ones', () => {
    const view = resolveTeamScheduleOutlook(outlook(), 2026, 1)!;
    expect(view.remaining).toBe('harder');
    expect(view.opponentByWeek.get(5)).toBe('weaker');
    expect(view.opponentByWeek.has(6)).toBeFalse();
    expect(resolveTeamScheduleOutlook(outlook(), 2025, 1)).toBeNull();
    expect(resolveTeamScheduleOutlook(outlook(), 2026, 9)).toBeNull();
  });
});
