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

export function compareFantasyGameRemainingRelevance(
  left: FantasyGameContextGame,
  right: FantasyGameContextGame
): number {
  const leftRemaining = left.RemainingRelevance;
  const rightRemaining = right.RemainingRelevance;

  if (leftRemaining && rightRemaining) {
    return rightRemaining.CommittedFinalWindowMatchupCount - leftRemaining.CommittedFinalWindowMatchupCount
      || rightRemaining.LockedActiveStarterCount - leftRemaining.LockedActiveStarterCount
      || (rightRemaining.DirectStarterFantasyTeamCount ?? 0) - (leftRemaining.DirectStarterFantasyTeamCount ?? 0)
      || rightRemaining.UnlockedStarterCount - leftRemaining.UnlockedStarterCount
      || rightRemaining.TwoSidedFantasyMatchupCount - leftRemaining.TwoSidedFantasyMatchupCount
      || rightRemaining.FantasyMatchupCount - leftRemaining.FantasyMatchupCount
      || rightRemaining.FinalWindowFantasyMatchupCount - leftRemaining.FinalWindowFantasyMatchupCount
      || rightRemaining.EligibleBenchCandidateCount - leftRemaining.EligibleBenchCandidateCount
      || Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc)
      || left.GameID.localeCompare(right.GameID);
  }

  if (leftRemaining?.HasRemainingRelevance !== rightRemaining?.HasRemainingRelevance) {
    return leftRemaining?.HasRemainingRelevance ? -1 : 1;
  }

  return compareFantasyGameRelevance(left, right);
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

export function getMustWatchGames(
  context: FantasyGameContextReadModel
): FantasyGameContextGame[] {
  const gameByID = new Map(context.Games.map(game => [game.GameID, game]));
  const ranked = [...(context.MustWatchGames ?? [])]
    .sort((left, right) => left.Rank - right.Rank)
    .map(item => gameByID.get(item.GameID) ?? null)
    .filter((game): game is FantasyGameContextGame => !!game && game.RemainingRelevance?.HasRemainingRelevance !== false);

  if (ranked.length > 0) return ranked;

  return context.Games
    .filter(game => game.RemainingRelevance?.HasRemainingRelevance === true)
    .sort(compareFantasyGameRemainingRelevance)
    .concat(
      context.Games
        .filter(game => !game.RemainingRelevance)
        .filter(game => game.Relevance.StarterCount > 0 || game.Relevance.UnknownAssociationCount > 0)
        .sort(compareFantasyGameRelevance)
    );
}

export function getUpcomingRelevantGames(
  context: FantasyGameContextReadModel,
  now: Date = new Date()
): FantasyGameContextGame[] {
  const nowMs = now.getTime();
  return context.Games
    .filter(game => Date.parse(game.StartsAtUtc) > nowMs)
    .filter(game => game.RemainingRelevance
      ? game.RemainingRelevance.HasRemainingRelevance
      : game.Relevance.RosteredPlayerCount > 0 || game.Relevance.UnknownAssociationCount > 0)
    .sort(compareFantasyGameRemainingRelevance);
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

function normalizeGeneratedGameIDs(value: string[] | string | null | undefined): string[] {
  if (Array.isArray(value)) return value;
  return typeof value === 'string' && value.length > 0 ? [value] : [];
}

export function getNextFantasyMatchupGame(
  matchup: FantasyGameContextMatchup,
  now: Date = new Date()
): FantasyGameContextMatchupGame | null {
  const remaining = matchup.RemainingRelevance;
  const primaryGameID = remaining?.NextScoringPrimaryGameID;
  if (primaryGameID) {
    const primary = matchup.Games.find(game => game.GameID === primaryGameID);
    if (primary) return primary;
  }

  const generatedGameIDs = normalizeGeneratedGameIDs(
    remaining?.NextScoringGameIDs as string[] | string | null | undefined
  );

  if ((remaining?.LockedActiveStarterCount ?? 0) > 0 && generatedGameIDs.length > 0) {
    const lockedFallback = matchup.Games
      .filter(game => generatedGameIDs.includes(game.GameID))
      .sort((left, right) => Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc) || left.GameID.localeCompare(right.GameID))[0];
    if (lockedFallback) return lockedFallback;
  }

  // Compatibility while older schema-v2 JSON is still circulating: prefer the
  // earliest direct starter game over an earlier option-only generated window.
  // New materializations provide NextScoringPrimaryGameID and remain authoritative.
  const nowMs = now.getTime();
  const directStarterFallback = [...matchup.Games]
    .filter(game => Date.parse(game.StartsAtUtc) > nowMs)
    .filter(game => game.LeftStarterCount + game.RightStarterCount > 0)
    .sort((left, right) => Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc)
      || (right.LeftStarterCount + right.RightStarterCount) - (left.LeftStarterCount + left.RightStarterCount)
      || left.GameID.localeCompare(right.GameID))[0];
  if (directStarterFallback) return directStarterFallback;

  if (generatedGameIDs.length > 0) {
    const generated = matchup.Games
      .filter(game => generatedGameIDs.includes(game.GameID))
      .sort((left, right) => Date.parse(left.StartsAtUtc) - Date.parse(right.StartsAtUtc) || left.GameID.localeCompare(right.GameID))[0];
    if (generated) return generated;
  }

  return null;
}

export function isFantasyMatchupFinalWindowGame(
  matchup: FantasyGameContextMatchup,
  gameID: string
): boolean {
  return normalizeGeneratedGameIDs(
    matchup.RemainingRelevance?.FinalScoringGameIDs as string[] | string | null | undefined
  ).includes(gameID);
}
