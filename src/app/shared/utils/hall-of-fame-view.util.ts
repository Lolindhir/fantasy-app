import type { FantasyTeam, League } from '../../core/models/league.models';
import type { PlayerAwardHistoryReadModel } from '../../core/models/player-award-history.models';
import type { SeasonStatisticsReadModel } from '../../core/models/season-statistics.models';
import { buildLeagueLegacy, type LeagueLegacyHighlight } from './league-standings-view.util';
import { buildPlayerAwardHighlights } from './player-award-view.util';
import { buildBiggestUpsetHighlight } from './season-statistics-view.util';

/** Hall of Fame tiles in display order: league legacy facts, the all-time biggest upset, then the player award leaders. Projection only, nothing is counted here. */
export function buildHallOfFameHighlights(
  league: League,
  teams: FantasyTeam[],
  current: SeasonStatisticsReadModel | null,
  bySeason: ReadonlyMap<string, SeasonStatisticsReadModel>,
  awards: PlayerAwardHistoryReadModel | null
): LeagueLegacyHighlight[] {
  const upset = buildBiggestUpsetHighlight(current, bySeason);
  return [...buildLeagueLegacy(league, teams).highlights, ...(upset ? [upset] : []), ...buildPlayerAwardHighlights(awards)];
}
