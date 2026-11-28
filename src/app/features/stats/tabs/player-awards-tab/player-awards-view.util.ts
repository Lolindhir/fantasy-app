import type { PlayerAwardHistoryPlayer, PlayerAwardHistoryReadModel, PlayerAwardKey } from '../../../../core/models/player-award-history.models';
import type { PlayerIdentitySummary } from '../../../../core/models/player.models';
import { PLAYER_AWARD_DISPLAY } from '../../../../shared/utils/player-award-view.util';

export const ALL_TIME = 'all-time';

export interface PlayerAwardRow {
  playerId: string;
  rank: number;
  name: string;
  position: string | null;
  picture: string | null;
  /** NFL team logo of the current Players.json record; null for players the app no longer lists or without a team. */
  teamLogo: string | null;
  teamAbbr: string | null;
  counts: Record<PlayerAwardKey, number>;
  total: number;
  /** Current identity exists; full details are resolved only on an explicit click. */
  interactive: boolean;
}

export interface PlayerAwardsView {
  /** Season ids in the file, newest first; the all-time view is separate. */
  seasons: string[];
  rows(season: string): PlayerAwardRow[];
}

/**
 * Joins the generator's rankings (all-time Players, per-season Seasons[].Players) with the current player records.
 * Nothing is counted or ranked here: order and counts come from the generator; ties share a rank number by equal totals.
 */
export function buildPlayerAwardsView(history: PlayerAwardHistoryReadModel | null | undefined, players: readonly PlayerIdentitySummary[]): PlayerAwardsView {
  const currentById = new Map(players.map(player => [String(player.ID), player]));
  const refById = new Map<string, PlayerAwardHistoryPlayer>((history?.Players ?? []).map(player => [String(player.PlayerID), player]));

  const toRows = (items: ReadonlyArray<{ PlayerID: string; Counts: Record<PlayerAwardKey, number>; Total: number }>): PlayerAwardRow[] => {
    let rank = 0;
    let previousTotal: number | null = null;
    return items.flatMap((item, index) => {
      const ref = refById.get(String(item.PlayerID));
      const current = currentById.get(String(item.PlayerID)) ?? null;
      if (!ref && !current) return [];
      if (item.Total !== previousTotal) {
        rank = index + 1;
        previousTotal = item.Total;
      }
      return [{
        playerId: String(item.PlayerID),
        rank,
        name: current?.Name || ref?.Name || `Player ${item.PlayerID}`,
        position: current?.Position || ref?.Position || null,
        picture: current?.Picture || ref?.Picture || null,
        teamLogo: current?.TeamNFL?.Logo || null,
        teamAbbr: current?.TeamNFL?.ID || null,
        counts: item.Counts,
        total: item.Total,
        interactive: current !== null
      }];
    });
  };

  const bySeason = new Map<string, PlayerAwardRow[]>();
  for (const season of history?.Seasons ?? []) {
    if (season.Players) bySeason.set(String(season.Season), toRows(season.Players));
  }
  const allTime = toRows((history?.Players ?? []).filter(player => player.Total > 0));

  return {
    seasons: [...bySeason.keys()].sort((a, b) => Number(b) - Number(a)),
    rows: season => (season === ALL_TIME ? allTime : bySeason.get(season) ?? [])
  };
}

export const AWARD_COLUMNS = PLAYER_AWARD_DISPLAY;
