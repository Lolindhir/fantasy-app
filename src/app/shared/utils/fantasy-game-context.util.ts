import type {
  FantasyGameContextGame,
  FantasyGameContextMatchup,
  FantasyGameContextMatchupGame,
  FantasyGameContextReadModel
} from '../../core/models/fantasy-game-context.models';

export function compareFantasyGameRelevance(
  left: FantasyGameContextGame,
  right: FantasyGameContextGame
): number {
  return right.Relevance.StarterCount - left.Relevance.StarterCount
    || right.Relevance.FantasyMatchupCount - left.Relevance.FantasyMatchupCount
    || right.Relevance.FantasyTeamCount - left.Relevance.FantasyTeamCount
    || right.Relevance.RosteredPlayerCount - left.Relevance.RosteredPlayerCount
    || Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc)
    || left.GameID.localeCompare(right.GameID);
}

export function compareFantasyGameImpact(
  left: FantasyGameContextGame,
  right: FantasyGameContextGame
): number {
  return (right.Impact.StarterPoints ?? Number.NEGATIVE_INFINITY)
    - (left.Impact.StarterPoints ?? Number.NEGATIVE_INFINITY)
    || compareFantasyGameRelevance(left, right);
}

export function isFantasyGameContextForLeagueWeek(
  context: FantasyGameContextReadModel | null | undefined,
  season: string,
  week: number | null
): context is FantasyGameContextReadModel {
  return !!context && week !== null && context.Season === season && context.Week === week;
}

export function isFantasyGameImpactVisible(
  game: FantasyGameContextGame,
  now: Date = new Date()
): boolean {
  if (game.Impact.State === 'unavailable') return false;
  if (/^Final/i.test(game.Status ?? '')) return true;

  const kickoffMs = Date.parse(game.StartsAtUtc);
  return Number.isFinite(kickoffMs) && kickoffMs <= now.getTime();
}

export function getUpcomingRelevantGames(
  context: FantasyGameContextReadModel,
  now: Date = new Date()
): FantasyGameContextGame[] {
  const nowMs = now.getTime();
  return context.Games
    .filter(game => Date.parse(game.StartsAtUtc) > nowMs)
    .filter(game => game.Relevance.RosteredPlayerCount > 0 || game.Relevance.UnknownAssociationCount > 0)
    .sort(compareFantasyGameRelevance);
}

export function getCompletedImpactGames(
  context: FantasyGameContextReadModel
): FantasyGameContextGame[] {
  return context.Games
    .filter(game => game.Impact.State === 'final' || /^Final/i.test(game.Status ?? ''))
    .filter(game => game.Relevance.RosteredPlayerCount > 0 || game.Relevance.UnknownAssociationCount > 0)
    .sort(compareFantasyGameImpact);
}

export function getFantasyMatchupContext(
  context: FantasyGameContextReadModel,
  teamIDs: Array<string | number>
): FantasyGameContextMatchup | null {
  const wanted = teamIDs.map(String).sort().join('|');
  return context.FantasyMatchups.find(matchup =>
    matchup.TeamIDs.map(String).sort().join('|') === wanted
  ) ?? null;
}

export function getNextFantasyMatchupGame(
  matchup: FantasyGameContextMatchup,
  now: Date = new Date()
): FantasyGameContextMatchupGame | null {
  const nowMs = now.getTime();
  return [...matchup.Games]
    .filter(game => Date.parse(game.StartsAtUtc) > nowMs)
    .filter(game => game.LeftStarterCount + game.RightStarterCount > 0)
    .sort((left, right) => Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc) || left.GameID.localeCompare(right.GameID))[0]
    ?? null;
}
