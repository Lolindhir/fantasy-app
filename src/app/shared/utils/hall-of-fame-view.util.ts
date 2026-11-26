import type { Player } from '../../core/models/player.models';
import type { TeamIdentitySubject } from '../components/team-identity/team-identity';
import type { FantasyTeam, League } from '../../core/models/league.models';
import type { PlayerAwardHistoryReadModel } from '../../core/models/player-award-history.models';
import type { SeasonStatisticsReadModel } from '../../core/models/season-statistics.models';
import type { TeamSeasonLookup } from '../services/team-season.service';
import { DEFAULT_TEAM_AVATAR_SRC, getSeasonRingSrc } from './championship.util';
import { buildLeagueLegacy, buildSeasonHistory, type LeagueLegacyHighlight } from './league-standings-view.util';
import { buildPlayerAwardHighlights, PLAYER_AWARD_DISPLAY } from './player-award-view.util';
import { buildBiggestUpsetHighlight } from './season-statistics-view.util';

/** Display identities only: published award IDs and order remain authoritative. */
export interface HallOfFamePlayerIdentity {
  id: string;
  name: string;
  picture: string | null;
  teamLogo: string | null;
  teamAbbr: string | null;
  player: Player | null;
}

export interface HallOfFameUpsetSide {
  team: TeamIdentitySubject;
  points: number;
  interactive: boolean;
}

export interface HallOfFameUpset {
  season: string;
  week: number;
  winner: HallOfFameUpsetSide;
  loser: HallOfFameUpsetSide;
  pregameProbability: number;
}

export interface HallOfFameHighlight extends LeagueLegacyHighlight {
  upset?: HallOfFameUpset;
  team?: TeamIdentitySubject;
  teamInteractive?: boolean;
  players?: HallOfFamePlayerIdentity[];
}

/** Record groups of the Hall of Fame page. Projection only, nothing is counted here. */
export interface HallOfFameSections {
  /** League legacy facts: Champ of Champs, Regular Season King, Podium Machine, Award Collector. */
  legacy: HallOfFameHighlight[];
  /** All-time bests across seasons, currently the biggest upset. */
  bests: HallOfFameHighlight[];
  /** Leaders of the weekly player awards. */
  playerLegends: HallOfFameHighlight[];
}

export function buildHallOfFameSections(
  league: League,
  teams: FantasyTeam[],
  current: SeasonStatisticsReadModel | null,
  bySeason: ReadonlyMap<string, SeasonStatisticsReadModel>,
  awards: PlayerAwardHistoryReadModel | null,
  players: readonly Player[] = [],
  lookup: TeamSeasonLookup | null = null
): HallOfFameSections {
  const teamById = new Map(teams.map(team => [String(team.TeamID), team]));
  const facts = league.Standings?.find(standing => standing.Season === 'AllTime')?.LegacyHighlights ?? [];
  const legacy = buildLeagueLegacy(league, teams).highlights.map(item => {
    const fact = facts.find(candidate => candidate.Key === item.key);
    const team = fact ? teamById.get(String(fact.TeamID)) : undefined;
    const display = item.key === 'ChampOfChamps'
      ? { title: 'All-Time Overall Leader', valueDisplay: '#1 Overall standings' }
      : item.key === 'RegularSeasonKing'
        ? { valueDisplay: '#1 Regular season standings' }
        : item.key === 'PodiumMachine'
          ? { valueDisplay: item.valueDisplay.replace(/Podium(s?)$/, 'Playoff podium$1') }
          : item.key === 'AwardCollector'
            ? { valueDisplay: item.valueDisplay.replace(/Awards$/, 'Season awards') }
            : {};
    return { ...item, ...display, team, teamInteractive: !!team };
  });

  const upset = buildBiggestUpsetHighlight(current, bySeason);
  const upsetFact = current?.BiggestUpsetAllTime;
  const bests: HallOfFameHighlight[] = [];
  if (upset && upsetFact) {
    const season = String(upsetFact.Season);
    const doc = upsetFact.Season === current?.Season ? current : bySeason.get(season);
    const standings = league.Standings?.find(standing => standing.Season === season);
    const side = (teamId: number, points: number): HallOfFameUpsetSide => {
      const row = doc?.Teams.find(team => String(team.TeamID) === String(teamId));
      const playoff = standings?.Playoffs?.find(team => String(team.TeamID) === String(teamId));
      const regular = standings?.RegularSeason?.find(team => String(team.TeamID) === String(teamId));
      const team = lookup?.identity(season, teamId)
        ?? (season === String(league.Season) ? teamById.get(String(teamId)) : undefined)
        ?? { TeamID: teamId, Team: row?.TeamName || playoff?.TeamName || regular?.TeamName || `Team ${teamId}`,
             Owner: row?.Owner || playoff?.Owner || regular?.Owner || '',
             Avatar: playoff?.TeamAvatar || DEFAULT_TEAM_AVATAR_SRC };
      return { team, points, interactive: teamById.has(String(teamId)) };
    };
    const winner = side(upsetFact.WinnerTeamID, upsetFact.WinnerPoints);
    const loser = side(upsetFact.LoserTeamID, upsetFact.LoserPoints);
    bests.push({ ...upset, team: winner.team, teamInteractive: winner.interactive,
      upset: { season, week: upsetFact.Week, winner, loser,
        pregameProbability: upsetFact.WinnerPregameWinProbability } });
  }

  const currentById = new Map(players.map(player => [String(player.ID), player]));
  const historyById = new Map((awards?.Players ?? []).map(player => [String(player.PlayerID), player]));
  const playerLegends = buildPlayerAwardHighlights(awards).map(item => {
    const def = PLAYER_AWARD_DISPLAY.find(candidate => item.key === `player-award-${candidate.key}`);
    const leaders = def ? awards?.Leaders?.[def.key] ?? [] : [];
    return {
      ...item,
      players: leaders.map(leader => {
        const id = String(leader.PlayerID);
        const player = currentById.get(id) ?? null;
        const history = historyById.get(id);
        return { id, name: leader.Name, picture: player?.Picture || history?.Picture || null,
          teamLogo: player?.TeamNFL?.Logo || null, teamAbbr: player?.TeamNFL?.Abv || null, player };
      })
    };
  });
  return { legacy, bests, playerLegends };
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
