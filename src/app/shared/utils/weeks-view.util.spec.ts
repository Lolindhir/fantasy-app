import type { FantasyTeam } from '../../core/models/league.models';
import type {
  FantasyMatchupReadModel,
  MatchupCompletionState,
  MatchupStage,
  MatchupWeekReadModel,
  MatchupsReadModel
} from '../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import type { PastSeasonsIndex } from '../../core/services/data-api.service';
import {
  buildSeasonGrid,
  buildWeekScoreboard,
  buildWeekTabs,
  buildWeeksSeasonOptions,
  parseWeekParam,
  resolveDefaultWeek,
  resolveSelectedWeek,
  resolveWeeksSeason,
  selectRecapUpsets,
  selectWeekRecap
} from './weeks-view.util';

function team(id: number): FantasyTeam {
  return { TeamID: id, Team: `Team ${id}`, Roster: [] } as unknown as FantasyTeam;
}

function matchup(
  id: string,
  home: [number, number | null],
  away: [number, number | null],
  state: MatchupCompletionState = 'final',
  winner: number | 'tie' | null = null
): FantasyMatchupReadModel {
  return {
    FantasyMatchupID: id,
    CompletionState: state,
    Participants: [
      { TeamID: home[0], Points: home[1], ScoreKind: 'standard' },
      { TeamID: away[0], Points: away[1], ScoreKind: 'standard' }
    ],
    Result: winner === null
      ? null
      : winner === 'tie'
        ? { Type: 'tie', WinnerTeamID: null }
        : { Type: 'win', WinnerTeamID: winner }
  };
}

function week(
  number: number,
  stage: MatchupStage,
  state: MatchupCompletionState,
  matchups: FantasyMatchupReadModel[]
): MatchupWeekReadModel {
  return { Week: number, Stage: stage, FirstKickoffUtc: null, CompletionState: state, Matchups: matchups };
}

function model(weeks: MatchupWeekReadModel[], lastCompleted: number | null = null): MatchupsReadModel {
  return {
    SchemaVersion: 1,
    Season: '2025',
    Weeks: weeks,
    Summary: { LastCompletedWeek: lastCompleted, ActiveOrNextWeek: null }
  };
}

describe('weeks view util', () => {
  describe('season options', () => {
    const index = {
      GeneratedAt: null,
      Seasons: [
        { Season: '2024', Resources: { Matchups: { Path: 'data/m24.json', Exists: true }, WeeklyRecaps: { Path: 'data/r24.json', Exists: true } } },
        { Season: '2025', Resources: { Matchups: { Path: 'data/m25.json', Exists: true }, WeeklyRecaps: { Path: 'data/r25.json', Exists: false } } },
        { Season: '2023', Resources: { Matchups: { Path: 'data/m23.json', Exists: false } } },
        { Season: '2026', Resources: { Matchups: { Path: 'data/m26.json', Exists: true } } }
      ]
    } as unknown as PastSeasonsIndex;

    it('lists the current season first, then archived seasons with matchups newest first', () => {
      const options = buildWeeksSeasonOptions(index, '2026');

      expect(options.map(option => option.season)).toEqual(['2026', '2025', '2024']);
      expect(options[0]).toEqual({ season: '2026', isCurrent: true, matchupsPath: null, recapsPath: null, contextPath: null });
      expect(options[1].recapsPath).toBeNull();
      expect(options[2].recapsPath).toBe('data/r24.json');
    });

    it('still offers the current season without a past seasons index', () => {
      expect(buildWeeksSeasonOptions(null, '2026').map(option => option.season)).toEqual(['2026']);
    });

    it('falls back to the current season for an unavailable requested season', () => {
      const options = buildWeeksSeasonOptions(index, '2026');

      expect(resolveWeeksSeason(options, '2025')?.season).toBe('2025');
      expect(resolveWeeksSeason(options, '1999')?.season).toBe('2026');
      expect(resolveWeeksSeason(options, null)?.season).toBe('2026');
      expect(resolveWeeksSeason([], '2025')).toBeNull();
    });
  });

  describe('week selection', () => {
    const weeks = model([
      week(1, 'regular-season', 'final', [matchup('a', [1, 100], [2, 90], 'final', 1)]),
      week(2, 'regular-season', 'unknown', [matchup('b', [1, 100], [2, 90], 'final', 1)]),
      week(3, 'regular-season', 'open', [matchup('c', [1, null], [2, null], 'open')])
    ], 1);

    it('defaults to the last settled week, including archived weeks whose matchups are all final', () => {
      expect(resolveDefaultWeek(weeks)).toBe(2);
    });

    it('does not treat a partly final open week as settled', () => {
      const live = model([
        week(1, 'regular-season', 'final', [matchup('a', [1, 1], [2, 0], 'final', 1)]),
        week(2, 'regular-season', 'open', [
          matchup('b', [1, 5], [2, 4], 'final', 1),
          matchup('c', [3, 1], [4, 2], 'open')
        ])
      ]);

      expect(resolveDefaultWeek(live)).toBe(1);
    });

    it('falls back to the summary week or the first week when nothing is settled', () => {
      const none = model([week(1, 'regular-season', 'open', [matchup('a', [1, null], [2, null], 'open')])], null);
      expect(resolveDefaultWeek(none)).toBe(1);
      expect(resolveDefaultWeek(model([]))).toBeNull();
      expect(resolveDefaultWeek(null)).toBeNull();
    });

    it('prefers the first valid candidate and otherwise the default week', () => {
      expect(resolveSelectedWeek(weeks, 3, 1)).toBe(3);
      expect(resolveSelectedWeek(weeks, 99, 1)).toBe(1);
      expect(resolveSelectedWeek(weeks, null, undefined)).toBe(2);
      expect(resolveSelectedWeek(null, 1)).toBeNull();
    });

    it('parses only whole-number week parameters', () => {
      expect(parseWeekParam('7')).toBe(7);
      expect(parseWeekParam('7x')).toBeNull();
      expect(parseWeekParam('-1')).toBeNull();
      expect(parseWeekParam(null)).toBeNull();
    });

    it('marks playoff weeks in the week tabs', () => {
      const tabs = buildWeekTabs(model([
        week(2, 'playoffs', 'final', []),
        week(1, 'regular-season', 'final', [])
      ]));

      expect(tabs.map(tab => [tab.week, tab.isPlayoff])).toEqual([[1, false], [2, true]]);
    });
  });

  describe('scoreboard', () => {
    it('keeps nullable scores, resolves teams and flags the winner only for decided matchups', () => {
      const board = buildWeekScoreboard(
        week(5, 'regular-season', 'unknown', [
          matchup('a', [1, 120.5], [2, 99], 'final', 1),
          matchup('b', [3, 10], [9, null], 'unknown'),
          matchup('c', [4, 77], [5, 77], 'final', 'tie')
        ]),
        [team(1), team(2), team(3)]
      );

      expect(board[0].participants.map(p => [p.teamID, p.isWinner, p.team?.TeamID])).toEqual([[1, true, 1], [2, false, 2]]);
      expect(board[1].participants[1]).toEqual(jasmine.objectContaining({ teamID: 9, team: null, points: null, isWinner: false }));
      expect(board[1].participants.some(p => p.isWinner)).toBeFalse();
      expect(board[2].isTie).toBeTrue();
      expect(board[2].participants.some(p => p.isWinner)).toBeFalse();
      expect(buildWeekScoreboard(null, [])).toEqual([]);
    });
  });

  describe('recap selection', () => {
    const recaps: WeeklyRecapsReadModel = {
      SchemaVersion: 1,
      Season: '2025',
      Weeks: [
        { Week: 1, KeyGames: [], KeyPlayers: [], TeamAwards: { State: 'available', BestManager: [], BestCoach: [] } },
        { Week: 2, KeyGames: [], KeyPlayers: [], TeamAwards: { State: 'unavailable', BestManager: [], BestCoach: [] } },
        { Week: 3, KeyGames: [], KeyPlayers: [] }
      ]
    };
    const final = (n: number) => week(n, 'regular-season', 'final', [matchup('x', [1, 1], [2, 0], 'final', 1)]);

    it('returns the recap content and hides unavailable or absent awards', () => {
      expect(selectWeekRecap(recaps, '2025', final(1)).content?.awards?.State).toBe('available');
      expect(selectWeekRecap(recaps, '2025', final(2)).content?.awards).toBeNull();
      expect(selectWeekRecap(recaps, '2025', final(3)).content?.awards).toBeNull();
      expect(selectWeekRecap(recaps, '2025', final(1)).status).toBe('available');
    });

    it('lists only generator-marked underdog winners, upsets first, and shows nothing when every favorite won', () => {
      const mark = (id: string, winner: number, loserChance: number, winnerChance: number, level: 'upset' | 'underdog' | null) => ({
        FantasyMatchupID: id,
        Teams: [{ FantasyTeamID: winner, PregameWinProbability: winnerChance }, { FantasyTeamID: winner + 1, PregameWinProbability: loserChance }],
        Upset: level === 'upset',
        UpsetWinnerFantasyTeamID: level === 'upset' ? winner : null,
        UpsetLevel: level,
        UnderdogWinnerFantasyTeamID: level ? winner : null
      });
      const upsets = selectRecapUpsets([
        mark('a', 1, 55, 45, 'underdog'),
        mark('b', 3, 70, 30, 'upset'),
        mark('c', 5, 20, 80, null)
      ]);
      expect(upsets.map(upset => [upset.matchupID, upset.level, upset.winnerChance, upset.loserTeamID])).toEqual([
        ['b', 'upset', 30, 4],
        ['a', 'underdog', 45, 2]
      ]);
      expect(selectRecapUpsets([mark('c', 5, 20, 80, null)])).toEqual([]);
      expect(selectRecapUpsets(undefined)).toEqual([]);
      const withUpsets: WeeklyRecapsReadModel = { SchemaVersion: 1, Season: '2025', Weeks: [{ Week: 1, KeyGames: [], KeyPlayers: [], WinProbabilities: [mark('b', 3, 70, 30, 'upset')] }] };
      expect(selectWeekRecap(withUpsets, '2025', final(1)).content?.underdog?.matchupID).toBe('b');
      expect(selectWeekRecap(withUpsets, '2025', final(1)).content?.allFavoritesWon).toBeFalse();
      const none: WeeklyRecapsReadModel = { SchemaVersion: 1, Season: '2025', Weeks: [{ Week: 1, KeyGames: [], KeyPlayers: [], WinProbabilities: [mark('c', 5, 20, 80, null)] }, { Week: 2, KeyGames: [], KeyPlayers: [] }] };
      expect(selectWeekRecap(none, '2025', final(1)).content?.allFavoritesWon).toBeTrue();
      expect(selectWeekRecap(none, '2025', final(1)).content?.underdog).toBeNull();
      expect(selectWeekRecap(none, '2025', final(2)).content?.allFavoritesWon).toBeFalse();
    });

    it('reports a missing recap for a settled week and a pending recap for an open week', () => {
      expect(selectWeekRecap(recaps, '2025', final(10))).toEqual({ status: 'missing', content: null });
      expect(selectWeekRecap(null, '2025', final(1))).toEqual({ status: 'missing', content: null });
      const open = week(9, 'regular-season', 'open', [matchup('x', [1, null], [2, null], 'open')]);
      expect(selectWeekRecap(recaps, '2025', open)).toEqual({ status: 'pending-final', content: null });
    });

    it('ignores a recap file of another season', () => {
      expect(selectWeekRecap(recaps, '2026', final(1)).status).toBe('missing');
    });
  });

  describe('season grid', () => {
    const grid = buildSeasonGrid(model([
      week(1, 'regular-season', 'final', [
        matchup('a', [1, 150.1], [2, 150.1], 'final', 'tie'),
        matchup('b', [3, 90], [4, 120], 'final', 4)
      ]),
      week(2, 'playoffs', 'unknown', [
        matchup('c', [1, 100], [2, 80], 'unknown'),
        matchup('d', [3, null], [4, null], 'open')
      ])
    ]), [team(4), team(2), team(1), team(3)]);

    it('builds one row per team and one cell per week with playoff weeks grouped', () => {
      expect(grid?.rows.length).toBe(4);
      expect(grid?.rows.every(row => row.cells.length === 2)).toBeTrue();
      expect(grid?.regularWeekCount).toBe(1);
      expect(grid?.playoffWeekCount).toBe(1);
    });

    it('shows only values from the file and keeps open or missing scores empty', () => {
      const row = (id: number) => grid!.rows.find(candidate => candidate.teamID === id)!;

      expect(row(3).cells[0]).toEqual({ week: 1, points: 90, outcome: 'loss', isWeekHigh: false });
      expect(row(4).cells[0].outcome).toBe('win');
      expect(row(1).cells[0].outcome).toBe('tie');
      expect(row(1).cells[1].points).toBe(100);
      expect(row(1).cells[1].outcome).toBeNull();
      expect(row(3).cells[1].points).toBeNull();
    });

    it('marks the highest score of a week, including shared highs, and nothing for fewer than two scores', () => {
      const row = (id: number) => grid!.rows.find(candidate => candidate.teamID === id)!;

      // Week 1: teams 1 and 2 share the high; week 2 has two scores, team 3/4 are open.
      expect(row(1).cells[0].isWeekHigh).toBeTrue();
      expect(row(2).cells[0].isWeekHigh).toBeTrue();
      expect(row(4).cells[0].isWeekHigh).toBeFalse();
      expect(row(1).cells[1].isWeekHigh).toBeTrue();
      expect(row(2).cells[1].isWeekHigh).toBeFalse();
      expect(row(3).cells[1].isWeekHigh).toBeFalse();
    });

    it('falls back to TeamID order without resolved standings and appends teams unknown to the league', () => {
      const withExtra = buildSeasonGrid(
        model([week(1, 'regular-season', 'final', [matchup('a', [1, 1], [9, 0], 'final', 1)])]),
        [team(2), team(1)]
      );

      expect(withExtra?.rows.map(row => row.teamID)).toEqual([1, 2, 9]);
      expect(withExtra?.rows[2].team).toBeNull();
      expect(buildSeasonGrid(model([]), [])).toBeNull();
    });
  });
});
