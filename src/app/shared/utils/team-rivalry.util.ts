import type { FantasyMatchupReadModel, MatchupsReadModel, MatchupStage } from '../../core/models/matchup.models';

/**
 * Head-to-head record of one fantasy team against every other team, counted from finalized
 * Matchups results only. Pure counting: no tiebreaks, rankings or weighting (design rule 4).
 * Team identity across seasons is the TeamID (Sleeper roster_id), like All-Time Standings.
 */
export type RivalryFilter = 'all' | 'regular' | 'playoffs';
export type RivalryOutcome = 'win' | 'loss' | 'tie';

export interface RivalryGame {
  season: string;
  week: number;
  stage: MatchupStage;
  outcome: RivalryOutcome;
  teamPoints: number | null;
  opponentPoints: number | null;
  /** Absolute point margin; null when either score is missing. */
  margin: number | null;
}

export interface RivalryRecord {
  opponentId: number;
  wins: number;
  losses: number;
  ties: number;
  pointsFor: number;
  pointsAgainst: number;
  /** All counted duels, oldest first. */
  games: RivalryGame[];
  lastGame: RivalryGame;
  biggestWin: RivalryGame | null;
  closestLoss: RivalryGame | null;
}

export interface RivalryOptions {
  filter: RivalryFilter;
  /**
   * Whether the playoffs of a season are over. The matchup data does not label consolation games, so
   * they are identified from a completed playoff (see isConsolationMatchup); playoff games of a season
   * whose playoffs are not complete are therefore not counted.
   */
  isSeasonComplete: (season: string) => boolean;
}

/** Playoffs are over for archived seasons and for the current season once the league is Completed. */
export function isPlayoffsComplete(season: string, currentSeason: number, leagueStatus: string): boolean {
  return Number(season) < currentSeason || leagueStatus === 'Completed';
}

export function formatRivalryRecord(record: Pick<RivalryRecord, 'wins' | 'losses' | 'ties'>): string {
  return record.ties > 0
    ? `${record.wins}-${record.losses}-${record.ties}`
    : `${record.wins}-${record.losses}`;
}

/**
 * Consolation games are not part of the championship bracket. The Matchups data has no bracket
 * label (Stage is only regular-season or playoffs), so a playoff matchup counts as consolation when
 * neither participant plays in the final playoff week: the championship bracket always reaches that
 * week (final and third-place game), consolation teams drop out earlier.
 * Only valid for a season whose playoffs are complete.
 */
export function isConsolationMatchup(season: MatchupsReadModel, week: number, matchup: FantasyMatchupReadModel): boolean {
  const playoffWeeks = season.Weeks.filter(candidate => candidate.Stage === 'playoffs');
  if (!playoffWeeks.length) return false;
  const lastWeek = Math.max(...playoffWeeks.map(candidate => candidate.Week));
  if (week === lastWeek) return false;
  const finalists = new Set(
    playoffWeeks
      .filter(candidate => candidate.Week === lastWeek)
      .flatMap(candidate => candidate.Matchups)
      .flatMap(candidateMatchup => candidateMatchup.Participants.map(participant => participant.TeamID))
  );
  return matchup.Participants.every(participant => !finalists.has(participant.TeamID));
}

export function collectRivalryGames(
  teamId: number,
  seasons: readonly MatchupsReadModel[],
  options: RivalryOptions
): Map<number, RivalryGame[]> {
  const byOpponent = new Map<number, RivalryGame[]>();

  for (const season of seasons) {
    const playoffsCountable = options.isSeasonComplete(season.Season);
    for (const week of season.Weeks) {
      if (week.Stage === 'playoffs' ? options.filter === 'regular' || !playoffsCountable : options.filter === 'playoffs') {
        continue;
      }
      for (const matchup of week.Matchups) {
        if (matchup.CompletionState !== 'final' || !matchup.Result) continue;
        const own = matchup.Participants.find(participant => participant.TeamID === teamId);
        const other = matchup.Participants.find(participant => participant.TeamID !== teamId);
        if (!own || !other || matchup.Participants.length !== 2) continue;
        if (week.Stage === 'playoffs' && isConsolationMatchup(season, week.Week, matchup)) continue;

        const outcome: RivalryOutcome = matchup.Result.Type === 'tie'
          ? 'tie'
          : matchup.Result.WinnerTeamID === teamId ? 'win' : 'loss';
        const bothScored = own.Points !== null && other.Points !== null;
        const game: RivalryGame = {
          season: season.Season,
          week: week.Week,
          stage: week.Stage,
          outcome,
          teamPoints: own.Points,
          opponentPoints: other.Points,
          margin: bothScored ? Math.abs((own.Points as number) - (other.Points as number)) : null
        };
        byOpponent.set(other.TeamID, [...(byOpponent.get(other.TeamID) ?? []), game]);
      }
    }
  }

  return byOpponent;
}

export function buildRivalryRecords(
  teamId: number,
  seasons: readonly MatchupsReadModel[],
  options: RivalryOptions
): RivalryRecord[] {
  const records: RivalryRecord[] = [];

  for (const [opponentId, unsorted] of collectRivalryGames(teamId, seasons, options)) {
    const games = [...unsorted].sort((a, b) => Number(a.season) - Number(b.season) || a.week - b.week);
    const margins = (outcome: RivalryOutcome) => games.filter(game => game.outcome === outcome && game.margin !== null);
    const biggestWin = [...margins('win')].sort((a, b) => (b.margin as number) - (a.margin as number))[0] ?? null;
    const closestLoss = [...margins('loss')].sort((a, b) => (a.margin as number) - (b.margin as number))[0] ?? null;

    records.push({
      opponentId,
      wins: games.filter(game => game.outcome === 'win').length,
      losses: games.filter(game => game.outcome === 'loss').length,
      ties: games.filter(game => game.outcome === 'tie').length,
      pointsFor: roundPoints(games.reduce((sum, game) => sum + (game.teamPoints ?? 0), 0)),
      pointsAgainst: roundPoints(games.reduce((sum, game) => sum + (game.opponentPoints ?? 0), 0)),
      games,
      lastGame: games[games.length - 1],
      biggestWin,
      closestLoss
    });
  }

  // Display order only (most meetings first, then TeamID); not a ranking of rivals.
  return records.sort((a, b) => b.games.length - a.games.length || a.opponentId - b.opponentId);
}

function roundPoints(value: number): number {
  return Math.round(value * 100) / 100;
}

/** All-time record of one team against one specific opponent, or null when they never played a counted game. */
export function buildHeadToHead(
  teamId: number,
  opponentId: number,
  seasons: readonly MatchupsReadModel[],
  options: RivalryOptions
): RivalryRecord | null {
  return buildRivalryRecords(teamId, seasons, options).find(record => record.opponentId === opponentId) ?? null;
}
