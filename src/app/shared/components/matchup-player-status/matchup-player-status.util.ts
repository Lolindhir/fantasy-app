import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextReadModel
} from '../../../core/models/fantasy-game-context.models';

export type MatchupPlayerProblemKind = 'out' | 'questionable';

export interface MatchupPlayerStatusPlayerInfo {
  name: string;
  picture: string | null;
  nflLogo: string | null;
}

export interface MatchupPlayerStatusLookups {
  teamName(teamID: string | number): string;
  teamAvatar(teamID: string | number): string | null;
  player(playerID: string): MatchupPlayerStatusPlayerInfo;
}

export interface MatchupPlayerStatusProblemView extends MatchupPlayerStatusPlayerInfo {
  playerID: string;
  kind: MatchupPlayerProblemKind;
  gameLabel: string | null;
}

export interface MatchupPlayerStatusTeamView {
  teamID: string | number;
  name: string;
  avatar: string | null;
  problems: MatchupPlayerStatusProblemView[];
}

function fantasyGameLabel(game: FantasyGameContextGame): string {
  return `${game.AwayTeamAbbr || game.AwayTeamID} @ ${game.HomeTeamAbbr || game.HomeTeamID}`;
}

function isFinalGame(game: FantasyGameContextGame): boolean {
  return /^Final/i.test(game.Status ?? '');
}

/** Starters of one fantasy team by player ID, with the NFL game they play in. */
function starterGames(
  context: FantasyGameContextReadModel,
  teamID: string | number
): Map<string, FantasyGameContextGame> {
  const games = new Map<string, FantasyGameContextGame>();
  for (const game of context.Games) {
    const team = game.FantasyTeams.find(candidate => String(candidate.FantasyTeamID) === String(teamID));
    for (const player of team?.Players ?? []) {
      if (player.IsStarter) games.set(String(player.PlayerID), game);
    }
  }
  return games;
}

/**
 * Presentation-only grouping of generated facts for the matchup dialog: starters flagged OUT or
 * questionable by MatchupProjections, with the NFL game they play in. Starters whose game is
 * already final are skipped; the matchup timeline shows them.
 */
export function buildMatchupPlayerStatus(
  matchup: FantasyGameContextMatchup,
  displayTeamIDs: readonly [string | number, string | number],
  context: FantasyGameContextReadModel,
  lookups: MatchupPlayerStatusLookups
): MatchupPlayerStatusTeamView[] {
  return displayTeamIDs.map(teamID => {
    const projection = matchup.Projection?.Teams.find(team => String(team.FantasyTeamID) === String(teamID));
    const games = starterGames(context, teamID);

    const problems: MatchupPlayerStatusProblemView[] = [];
    const seen = new Set<string>();
    const flagged: Array<[MatchupPlayerProblemKind, string[]]> = [
      ['out', projection?.OutStarterPlayerIDs ?? []],
      ['questionable', projection?.UncertainStarterPlayerIDs ?? []]
    ];
    for (const [kind, playerIDs] of flagged) {
      for (const rawID of playerIDs) {
        const playerID = String(rawID);
        const game = games.get(playerID);
        if (seen.has(playerID) || (game && isFinalGame(game))) continue;
        seen.add(playerID);
        problems.push({
          playerID,
          kind,
          gameLabel: game ? fantasyGameLabel(game) : null,
          ...lookups.player(playerID)
        });
      }
    }

    return { teamID, name: lookups.teamName(teamID), avatar: lookups.teamAvatar(teamID), problems };
  });
}

export function hasMatchupPlayerStatus(teams: readonly MatchupPlayerStatusTeamView[]): boolean {
  return teams.some(team => team.problems.length > 0);
}
