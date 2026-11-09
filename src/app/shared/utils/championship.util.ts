import type { FantasyTeam, League, Standing } from '../../core/models/fantasy.models';

/** Generic championship ring used until a season-specific artwork exists (#662, F14/F15). */
/** Same fallback the Standings season results use when a season has no stored team logo. */
export const DEFAULT_TEAM_AVATAR_SRC = 'assets/default-team-avatar.png';

export const GENERIC_CHAMPIONSHIP_RING_SRC = 'assets/awards/ui/award-championship-ring.png';

/** Storage contract for season-specific rings (#662, F15). A missing file falls back to the generic ring. */
export function getSeasonRingSrc(season: string | number): string {
  return `assets/awards/rings/${season}.png`;
}

type StandingsLike = Pick<Standing, 'Season' | 'Playoffs'>;

function hasPlayoffWinner(standing: StandingsLike): boolean {
  return !!standing.Playoffs?.some(row => row.Place === 1);
}

/**
 * Season of the most recent decided championship, or null when none exists.
 * The current season only counts once the league is finished, so a running
 * playoff bracket never crowns a new champion early (F16: the previous
 * champion stays defending until a new one is decided, also in the Off-Season).
 */
export function getLatestChampionSeason(
  standings: readonly StandingsLike[],
  currentSeason: string | number,
  isFinished: boolean
): string | null {
  const decided = standings
    .filter(standing => /^\d+$/.test(String(standing.Season)))
    .filter(standing => Number(standing.Season) < Number(currentSeason) || isFinished)
    .filter(hasPlayoffWinner)
    .sort((a, b) => Number(b.Season) - Number(a.Season));

  return decided.length ? String(decided[0].Season) : null;
}

/** TeamID of the defending champion from standings data (no name or emoji matching). */
export function getDefendingChampionTeamId(
  standings: readonly StandingsLike[],
  currentSeason: string | number,
  isFinished: boolean
): string | null {
  const season = getLatestChampionSeason(standings, currentSeason, isFinished);
  if (!season) return null;
  const champion = standings
    .find(standing => String(standing.Season) === season)
    ?.Playoffs?.find(row => row.Place === 1);
  return champion ? String(champion.TeamID) : null;
}

export interface TrophyRoomRing {
  season: string;
  teamName: string | null;
  teamAvatar: string | null;
  ringSrc: string;
}

export interface TrophyRoomSeasonEntry {
  season: string;
  /** Historical identity of that season (never the current team name or avatar). */
  teamName: string | null;
  teamAvatar: string | null;
  ownerAvatar: string | null;
  owner: string;
}

export interface TrophyRoomBanner extends TrophyRoomSeasonEntry {
  place: 1 | 2 | 3;
  label: 'Champion' | 'Runner Up' | '3rd Place';
  accent: 'gold' | 'silver' | 'bronze';
  emblemSrc: string;
  isRegularSeasonChampion: boolean;
}

export interface TrophyRoomViewModel {
  rings: TrophyRoomRing[];
  banners: TrophyRoomBanner[];
  plaques: TrophyRoomSeasonEntry[];
}

const PODIUM = {
  1: { label: 'Champion', accent: 'gold', emblemSrc: GENERIC_CHAMPIONSHIP_RING_SRC },
  2: { label: 'Runner Up', accent: 'silver', emblemSrc: 'assets/awards/ui/award-runner-up.png' },
  3: { label: '3rd Place', accent: 'bronze', emblemSrc: 'assets/awards/ui/award-third-place.png' }
} as const;

/**
 * Titles of one team from the generated standings. A season only counts once
 * its playoffs are decided (past seasons, or the current season when finished).
 */
export function buildTrophyRoom(
  league: Pick<League, 'Standings' | 'Season' | 'IsFinished'>,
  team: Pick<FantasyTeam, 'TeamID'>
): TrophyRoomViewModel {
  const teamId = String(team.TeamID);
  const rings: TrophyRoomRing[] = [];
  const banners: TrophyRoomBanner[] = [];
  const plaques: TrophyRoomSeasonEntry[] = [];

  const seasons = league.Standings
    .filter(standing => /^\d+$/.test(String(standing.Season)))
    .filter(standing => Number(standing.Season) < Number(league.Season) || league.IsFinished)
    .filter(hasPlayoffWinner)
    .sort((a, b) => Number(b.Season) - Number(a.Season));

  for (const standing of seasons) {
    const season = String(standing.Season);
    const playoff = standing.Playoffs?.find(row => String(row.TeamID) === teamId);
    const regularWinner = standing.RegularSeason.find(row => row.Place === 1);
    const isRegularSeasonChampion = !!regularWinner && String(regularWinner.TeamID) === teamId;

    if (playoff && (playoff.Place === 1 || playoff.Place === 2 || playoff.Place === 3)) {
      const place = playoff.Place as 1 | 2 | 3;
      const entry: TrophyRoomSeasonEntry = {
        season,
        teamName: playoff.TeamName,
        teamAvatar: playoff.TeamAvatar?.trim() || DEFAULT_TEAM_AVATAR_SRC,
        ownerAvatar: playoff.OwnerAvatar?.trim() || null,
        owner: playoff.Owner
      };
      banners.push({ ...entry, place, ...PODIUM[place], isRegularSeasonChampion });
      if (place === 1) {
        rings.push({
          season,
          teamName: entry.teamName,
          teamAvatar: entry.teamAvatar,
          ringSrc: getSeasonRingSrc(season)
        });
      }
    }

    if (isRegularSeasonChampion && regularWinner) {
      plaques.push({
        season,
        teamName: regularWinner.TeamName ?? playoff?.TeamName ?? null,
        teamAvatar: playoff?.TeamAvatar?.trim() || DEFAULT_TEAM_AVATAR_SRC,
        ownerAvatar: playoff?.OwnerAvatar?.trim() || null,
        owner: regularWinner.Owner
      });
    }
  }

  return { rings, banners, plaques };
}
