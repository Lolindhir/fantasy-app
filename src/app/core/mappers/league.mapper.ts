import { formatSalaryDollars } from './player.mapper';
import type { DraftPick, RawDraft } from '../models/draft.models';
import type {
  Award,
  AwardInStanding,
  FantasyTeam,
  League,
  RawAward,
  RawFantasyTeam,
  RawLeague
} from '../models/league.models';
import type { Player } from '../models/player.models';

export interface LeagueMappingContext {
  leagueRaw: RawLeague;
  draftsRaw: RawDraft[];
  players: Player[];
}

export interface LeagueMappingResult {
  league: League;
  teams: FantasyTeam[];
  drafts: RawDraft[];
}

export function mapRawLeagueData(context: LeagueMappingContext): LeagueMappingResult {
  const { leagueRaw, draftsRaw, players } = context;
  const drafts = draftsRaw ?? [];
  const draftPickByKey = buildDraftPickByKey(drafts);

  const teams = leagueRaw.Teams.map(team => mapRawFantasyTeamToFantasyTeam(team, draftPickByKey));
  assignTeamRosters(teams, leagueRaw.Teams, players);
  teams.sort((a, b) => a.Standing - b.Standing);

  const league: League = {
    ...leagueRaw,
    Standings: leagueRaw.Standings.map(standing => ({
      ...standing,
      Awards: standing.Awards?.map(award => mapStandingAward(award))
    })),
    Teams: teams,
    SalaryCap: leagueRaw.SalaryCap,
    SalaryCapDisplay: formatSalaryDollars(leagueRaw.SalaryCap),
    SalaryCapProjected: leagueRaw.SalaryCapProjected,
    SalaryCapProjectedDisplay: formatSalaryDollars(leagueRaw.SalaryCapProjected),
    IsFinished: ['Finished', 'Completed'].includes(leagueRaw.Status),
    SeasonAsNumber: +leagueRaw.Season
  };

  return { league, teams, drafts };
}

function buildDraftPickByKey(drafts: RawDraft[]): Map<string, DraftPick> {
  const draftPickByKey = new Map<string, DraftPick>();

  for (const draft of drafts) {
    for (const pick of draft.Picks ?? []) {
      draftPickByKey.set(pick.PickKey, {
        ...pick,
        Draft: draft
      });
    }
  }

  return draftPickByKey;
}

function mapRawFantasyTeamToFantasyTeam(
  team: RawFantasyTeam,
  draftPickByKey: Map<string, DraftPick>
): FantasyTeam {
  const currentAwards = ensureArray(team.Placements.Current.Awards)
    .map(award => mapAward(award));

  const draftPickKeys = team.DraftPicks ?? [];
  const resolvedDraftPicks = draftPickKeys
    .map(key => draftPickByKey.get(key))
    .filter((pick): pick is DraftPick => !!pick);

  return {
    ...team,
    Team: team.Team || `Team ${team.Owner}`,
    Avatar: team.TeamAvatar || team.OwnerAvatar || 'assets/default-team-avatar.png',
    Roster: [],
    Reserve: [],
    Taxi: [],
    Starter: [],
    DraftPickKeys: draftPickKeys,
    DraftPicks: resolvedDraftPicks,
    Standing: team.Placements.Current.Playoffs?.Place && team.Placements.Current.Playoffs.Place > 0
      ? team.Placements.Current.Playoffs.Place
      : team.Placements.Current.Regular.Place ?? 0,
    Wins: team.Placements.Current.Regular.Wins ?? 0,
    Losses: team.Placements.Current.Regular.Losses ?? 0,
    Ties: team.Placements.Current.Regular.Ties ?? 0,
    Points: team.Placements.Current.Regular.Points ?? 0,
    PointsAgainst: team.Placements.Current.Regular.PointsAgainst ?? 0,
    Streak: team.Placements.Current.Regular.Streak ?? '',
    Record: team.Placements.Current.Regular.Record ?? '',
    Championships: team.Placements.AllTime.Playoffs.Championships ?? 0,
    RunnerUps: team.Placements.AllTime.Playoffs.RunnerUps ?? 0,
    Thirds: team.Placements.AllTime.Playoffs.Thirds ?? 0,
    RegularSeasonWins: team.Placements.AllTime.Regular.RegularSeasonWins ?? 0,
    CurrentAwardsDisplay: currentAwards.map(award => award.Icon).join('')
  };
}

function assignTeamRosters(
  teams: FantasyTeam[],
  rawTeams: RawFantasyTeam[],
  players: Player[]
): void {
  teams.forEach(team => {
    const rawTeam = rawTeams.find(raw => raw.TeamID === team.TeamID);

    team.Roster = rosterIdsToPlayers(rawTeam?.Roster ?? [], players);
    team.Reserve = rosterIdsToPlayers(rawTeam?.Reserve ?? [], players);
    team.Taxi = rosterIdsToPlayers(rawTeam?.Taxi ?? [], players);
    team.Starter = rosterIdsToPlayers(rawTeam?.Starter ?? [], players);

    team.Roster.forEach(player => (player.TeamFantasy = team));
  });
}

function rosterIdsToPlayers(rosterIds: string[], allPlayers: Player[]): Player[] {
  return rosterIds
    .map(playerId => allPlayers.find(player => player.ID === playerId))
    .filter((player): player is Player => !!player);
}

function mapAward(raw: RawAward): Award {
  return {
    Name: raw.Name,
    Type: raw.Type,
    IconUnicode: raw.IconUnicode,
    StatDisplay: raw.StatDisplay,
    Icon: unicodeToEmoji(raw.IconUnicode)
  };
}

function mapStandingAward(raw: AwardInStanding): AwardInStanding {
  return {
    ...raw,
    Icon: unicodeToEmoji(raw.IconUnicode)
  };
}

function unicodeToEmoji(unicode: string): string {
  return unicode
    .split(' ')
    .map(code => String.fromCodePoint(parseInt(code, 16)))
    .join('');
}

function ensureArray<T>(value: T | T[] | null | undefined): T[] {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}
