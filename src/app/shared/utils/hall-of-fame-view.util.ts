import type { FantasyTeam, League } from '../../core/models/league.models';
import type { PlayerAwardHistoryReadModel } from '../../core/models/player-award-history.models';
import type { SeasonStatisticsReadModel } from '../../core/models/season-statistics.models';
import type { TeamSeasonLookup } from '../services/team-season.service';
import { DEFAULT_TEAM_AVATAR_SRC, getSeasonRingSrc } from './championship.util';
import { buildLeagueLegacy, buildSeasonHistory, type LeagueLegacyHighlight } from './league-standings-view.util';
import { buildPlayerAwardHighlights } from './player-award-view.util';
import { buildBiggestUpsetHighlight } from './season-statistics-view.util';

/** Record tiles of the Hall of Fame page, grouped in display order. Projection only, nothing is counted here (Issue #1621). */
export interface HallOfFameSections {
  /** League legacy facts: Champ of Champs, Regular Season King, Podium Machine, Award Collector. */
  legacy: LeagueLegacyHighlight[];
  /** All-time bests across seasons, currently the biggest upset. */
  bests: LeagueLegacyHighlight[];
  /** Leaders of the weekly player awards. */
  playerLegends: LeagueLegacyHighlight[];
}

export function buildHallOfFameSections(
  league: League,
  teams: FantasyTeam[],
  current: SeasonStatisticsReadModel | null,
  bySeason: ReadonlyMap<string, SeasonStatisticsReadModel>,
  awards: PlayerAwardHistoryReadModel | null
): HallOfFameSections {
  const upset = buildBiggestUpsetHighlight(current, bySeason);
  return {
    legacy: buildLeagueLegacy(league, teams).highlights,
    bests: upset ? [upset] : [],
    playerLegends: buildPlayerAwardHighlights(awards)
  };
}

/** One decided league championship in the identity of its own season. */
export interface HallOfFameChampion {
  season: string;
  teamName: string;
  owner: string;
  /** Team logo of that season; the neutral default logo when the season had none, never a later or current logo. */
  teamAvatar: string;
  ownerAvatar: string | null;
  ringSrc: string;
  isRegularSeasonChampion: boolean;
}

/**
 * Champions of every decided season, newest first. A season only counts once its playoffs are decided (past seasons, or the current
 * season when the league is finished). Name and logo come from the season's own team identity (league-teams, Issue #774); the
 * champion of the standings is only looked up there, never derived. Without a lookup entry the season snapshot of the standings is shown.
 */
export function buildHallOfFameChampions(league: League, lookup: TeamSeasonLookup | null): HallOfFameChampion[] {
  return buildSeasonHistory(league).seasons
    .filter(season => /^\d{4}$/.test(season.season) && !!season.champion)
    .filter(season => Number(season.season) < Number(league.Season) || league.IsFinished)
    .map(season => {
      const champion = season.champion!;
      const identity = lookup?.identity(season.season, champion.teamId) ?? null;
      return {
        season: season.season,
        teamName: identity?.Team || champion.teamName || champion.owner,
        owner: identity?.Owner || champion.owner,
        teamAvatar: identity?.Avatar || champion.teamAvatar || DEFAULT_TEAM_AVATAR_SRC,
        ownerAvatar: (identity ? identity.OwnerAvatar : champion.ownerAvatar) ?? null,
        ringSrc: getSeasonRingSrc(season.season),
        isRegularSeasonChampion: !!season.regularSeasonWinner && String(season.regularSeasonWinner.teamId) === String(champion.teamId)
      };
    });
}
