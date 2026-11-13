import type { AwardInStanding, FantasyTeam, League } from '../../core/models/fantasy.models';
import type { LegacyHighlightFact } from '../../core/models/league.models';

export interface CurrentStandingRow {
  team: FantasyTeam;
  displayPlace: number;
}

export interface SeasonResultAwardVisual {
  key: string;
  label: string;
  imageSrc?: string;
  text?: string;
}

export interface SeasonResultTeam {
  team: Pick<FantasyTeam, 'Owner'>;
  teamName: string | null;
  teamId?: string | number;
  place: number;
  isRegularSeasonChampion?: boolean;
  awardVisuals?: SeasonResultAwardVisual[];
  ownerAvatar?: string | null;
  teamAvatar?: string | null;
}

export interface RegularSeasonAchievementSubject {
  teamId: string | number;
  owner: string;
  teamName: string | null;
  ownerAvatar?: string | null;
  teamAvatar?: string | null;
  record: string | null;
  points: number | null;
}

export interface SeasonResultsViewModel {
  teams: SeasonResultTeam[];
  champion?: SeasonResultTeam;
  runnerUp?: SeasonResultTeam;
  thirdPlace?: SeasonResultTeam;
  remainingTeams: SeasonResultTeam[];
  regularSeasonChampion?: RegularSeasonAchievementSubject;
}

export interface AllTimeStandingRow {
  team: FantasyTeam;
  place: number;
  owner: string;
  championships: number;
  runnerUps: number;
  thirds: number;
  regularSeasonWins: number;
  placeAverage: number;
}

export interface AllTimeRegularSeasonStandingRow {
  team: FantasyTeam;
  place: number;
  owner: string;
  wins: number;
  losses: number;
  ties: number;
  record: string;
  points: number;
  pointsAgainst: number;
  winPercentageDisplay: string;
  regularSeasonWins: number;
}

export interface AwardLegendItem {
  key: string;
  icon: string;
  name: string;
  displayText: string;
  tooltip: string;
  order: number;
  occurrences: number;
}

export interface LeagueLegacyHighlight {
  key: string;
  icon: string;
  title: string;
  owner: string;
  valueDisplay: string;
  reason: string;
}

export interface LeagueLegacyViewModel {
  highlights: LeagueLegacyHighlight[];
  overallStandings: AllTimeStandingRow[];
  regularSeasonStandings: AllTimeRegularSeasonStandingRow[];
  awardLegend: AwardLegendItem[];
}

export interface SeasonHistoryPlayoffRow {
  teamId: string | number;
  place: number;
  placeOrdinal: string;
  owner: string;
  teamName: string | null;
  ownerAvatar?: string | null;
  teamAvatar?: string | null;
}

export interface SeasonHistoryRegularSeasonRow {
  teamId: string | number;
  place: number;
  placeOrdinal: string;
  owner: string;
  teamName: string | null;
  record: string | null;
  points: number | null;
  pointsAgainst: number | null;
  winPercentageDisplay: string;
  ownerAvatar?: string | null;
  teamAvatar?: string | null;
}

export interface SeasonHistoryAwardItem {
  key: string;
  icon: string;
  name: string;
  displayText: string;
  owner: string;
  teamName: string | null;
  teamAvatar: string;
  ownerAvatar: string | null;
  statDisplay: string;
  tooltip: string;
  order: number;
}

export interface SeasonHistorySeasonViewModel {
  season: string;
  champion?: SeasonHistoryPlayoffRow;
  regularSeasonWinner?: SeasonHistoryRegularSeasonRow;
  playoffResults: SeasonHistoryPlayoffRow[];
  regularSeasonStandings: SeasonHistoryRegularSeasonRow[];
  awards: SeasonHistoryAwardItem[];
}

export interface SeasonHistoryViewModel {
  seasons: SeasonHistorySeasonViewModel[];
}

export function buildCurrentStandings(league: League, teams: FantasyTeam[]): CurrentStandingRow[] {
  const currentStanding = league.Standings.find(standing => standing.Season === league.Season);
  const placeByTeamId = new Map(
    currentStanding?.RegularSeason.map(row => [String(row.TeamID), row.Place]) ?? []
  );

  const rankedTeams = teams
    .map(team => ({
      team,
      currentPlace: normalizeStandingPlace(
        placeByTeamId.get(String(team.TeamID)) ?? team.Placements.Current.Regular.Place
      ),
      previousPlace: normalizeStandingPlace(team.Placements.Previous.Playoffs?.Place)
    }))
    .sort((a, b) =>
      a.currentPlace - b.currentPlace
      || a.previousPlace - b.previousPlace
      || a.team.TeamID - b.team.TeamID
    );

  return rankedTeams.map((row, index) => ({
    team: row.team,
    // Preserve shared standings places (including ties); unranked pre-season rows
    // keep their existing neutral display order rather than claiming a result.
    displayPlace: Number.isFinite(row.currentPlace) && row.currentPlace > 0
      ? row.currentPlace
      : index + 1
  }));
}

/**
 * "Best Record" is the official regular-season table leader of the shared
 * standings product (standings-v1); the frontend does not sort records itself.
 */
export function findBestRecordTeam(league: League, teams: FantasyTeam[]): FantasyTeam | undefined {
  return buildCurrentStandings(league, teams)[0]?.team;
}

export function buildSeasonResults(teams: FantasyTeam[], league?: League): SeasonResultsViewModel {
  const seasonStanding = league?.Standings?.find(standing => standing.Season === league.Season);
  // A completed playoff result is required before a seasonal achievement is awarded.
  const winner = league?.IsFinished && seasonStanding?.Playoffs?.some(row => row.Place === 1)
    ? seasonStanding.RegularSeason.find(row => row.Place === 1)
    : undefined;
  const winningTeam = winner
    ? teams.find(team => String(team.TeamID) === String(winner.TeamID))
    : undefined;

  const allResults = teams
    .map(team => ({
      team,
      teamName: team.Team,
      teamId: team.TeamID,
      place: team.Placements.Previous.Playoffs?.Place ?? 999,
      isRegularSeasonChampion: !!winner && String(team.TeamID) === String(winner.TeamID),
      ownerAvatar: team.OwnerAvatar?.trim() || null,
      teamAvatar: team.Avatar?.trim() || 'assets/default-team-avatar.png'
    }))
    .sort((a, b) => a.place - b.place);

  return {
    teams: allResults,
    champion: allResults.find(row => row.place === 1),
    runnerUp: allResults.find(row => row.place === 2),
    thirdPlace: allResults.find(row => row.place === 3),
    remainingTeams: allResults.filter(row => row.place > 3),
    regularSeasonChampion: winner ? {
      teamId: winner.TeamID,
      owner: winner.Owner,
      teamName: winner.TeamName,
      ownerAvatar: winningTeam?.OwnerAvatar?.trim() || null,
      teamAvatar: winningTeam?.Avatar?.trim() || null,
      record: formatRecord(winner.Wins ?? 0, winner.Losses ?? 0, winner.Ties ?? 0),
      points: winner.Points ?? 0
    } : undefined
  };
}

export function buildAllTimeStandings(teams: FantasyTeam[]): AllTimeStandingRow[] {
  return teams
    .filter(team => team.Placements.AllTime.Playoffs.Place < 999)
    .map(team => ({
      team,
      place: team.Placements.AllTime.Playoffs.Place,
      owner: team.Owner,
      championships: team.Placements.AllTime.Playoffs.Championships,
      runnerUps: team.Placements.AllTime.Playoffs.RunnerUps,
      thirds: team.Placements.AllTime.Playoffs.Thirds,
      regularSeasonWins: team.Placements.AllTime.Regular.RegularSeasonWins,
      placeAverage: team.Placements.AllTime.Playoffs.PlaceAverage
    }))
    .sort((a, b) => a.place - b.place);
}

export function buildAllTimeRegularSeasonStandings(teams: FantasyTeam[]): AllTimeRegularSeasonStandingRow[] {
  return teams
    .filter(team => team.Placements.AllTime.Regular.Place < 999)
    .map(team => {
      const regular = team.Placements.AllTime.Regular;

      return {
        team,
        place: regular.Place,
        owner: team.Owner,
        wins: regular.Wins,
        losses: regular.Losses,
        ties: regular.Ties,
        record: formatRecord(regular.Wins, regular.Losses, regular.Ties),
        points: regular.Points,
        pointsAgainst: regular.PointsAgainst,
        winPercentageDisplay: regular.WinPercentageDisplay ?? '',
        regularSeasonWins: regular.RegularSeasonWins
      };
    })
    .sort((a, b) => a.place - b.place);
}

/** UI-only projection of the generator-owned legend; no aggregation of season awards. */
export function buildAwardLegend(league: League): AwardLegendItem[] {
  const facts = league.Standings?.find(standing => standing.Season === 'AllTime')?.AwardLegend ?? [];
  return facts.map(fact => ({
    key: fact.Key,
    icon: unicodeToEmoji(fact.IconUnicode),
    name: fact.DisplayText,
    displayText: fact.DisplayText,
    tooltip: buildAwardTooltip(fact.DisplayText, fact.Occurrences),
    order: fact.Order,
    occurrences: fact.Occurrences
  }));
}

export function buildLeagueLegacy(league: League, teams: FantasyTeam[]): LeagueLegacyViewModel {
  const overallStandings = buildAllTimeStandings(teams);
  const regularSeasonStandings = buildAllTimeRegularSeasonStandings(teams);
  const awardLegend = buildAwardLegend(league);
  const teamById = new Map(teams.map(team => [String(team.TeamID), team]));
  const facts = league.Standings?.find(standing => standing.Season === 'AllTime')?.LegacyHighlights ?? [];

  return {
    highlights: facts
      .map(fact => projectLegacyHighlight(fact, teamById))
      .filter((highlight): highlight is LeagueLegacyHighlight => highlight !== null),
    overallStandings,
    regularSeasonStandings,
    awardLegend
  };
}

export function buildSeasonHistory(league: League): SeasonHistoryViewModel {
  const seasons = [...(league.Standings ?? [])]
    .map(standing => {
      const playoffSnapshots = new Map(
        (standing.Playoffs ?? []).map(row => [String(row.TeamID), row])
      );
      const playoffResults = [...(standing.Playoffs ?? [])]
        .sort((a, b) => a.Place - b.Place)
        .map(row => ({
          teamId: row.TeamID,
          place: row.Place,
          placeOrdinal: row.PlaceOrdinal,
          owner: row.Owner,
          teamName: row.TeamName,
          ownerAvatar: row.OwnerAvatar?.trim() || null,
          teamAvatar: row.TeamAvatar?.trim() || 'assets/default-team-avatar.png'
        }));

      const regularSeasonStandings = [...(standing.RegularSeason ?? [])]
        .sort((a, b) => a.Place - b.Place)
        .map(row => {
          const historicIdentity = playoffSnapshots.get(String(row.TeamID));
          return {
            teamId: row.TeamID,
            place: row.Place,
            placeOrdinal: row.PlaceOrdinal,
            owner: row.Owner,
            teamName: row.TeamName,
            record: row.Wins != null && row.Losses != null && row.Ties != null
              ? formatRecord(row.Wins, row.Losses, row.Ties)
              : null,
            points: row.Points ?? null,
            pointsAgainst: row.PointsAgainst ?? null,
            winPercentageDisplay: row.WinPercentageDisplay ?? '',
            ownerAvatar: historicIdentity?.OwnerAvatar?.trim() || null,
            teamAvatar: historicIdentity?.TeamAvatar?.trim() || null
          };
        });

      const awards = buildSeasonAwardItems(standing.Awards ?? [], standing.Playoffs);

      return {
        season: standing.Season,
        champion: playoffResults.find(row => row.place === 1),
        regularSeasonWinner: regularSeasonStandings.find(row => row.place === 1),
        playoffResults,
        regularSeasonStandings,
        awards
      };
    })
    .sort((a, b) => Number(b.season) - Number(a.season));

  return { seasons };
}

export function getPreviousChampion(teams: FantasyTeam[]): FantasyTeam | undefined {
  return teams.find(team => team.Placements.Previous.Playoffs?.Place === 1);
}

/** Maps any list of generated awards to uniform, data-driven award cards (no per-award-name logic). */
export function buildSeasonAwardItems(
  awards: AwardInStanding[],
  seasonIdentities: { TeamID: string | number; OwnerAvatar?: string | null; TeamAvatar?: string | null }[] | null | undefined = []
): SeasonHistoryAwardItem[] {
  // Identity snapshot of the same season (via TeamID); never the current team identity.
  const identities = new Map((seasonIdentities ?? []).map(row => [String(row.TeamID), row]));
  return awards
    .filter(isDynamicSeasonAward)
    .sort((a, b) =>
      (a.Type?.Order ?? 999) - (b.Type?.Order ?? 999)
      || a.Name.localeCompare(b.Name)
    )
    .map(award => mapSeasonHistoryAward(award, identities.get(String(award.TeamID))));
}

export function getCurrentSeasonAwards(league: League): AwardInStanding[] {
  const currentStanding = league.Standings.find(standing => standing.Season === league.Season);

  return currentStanding?.Awards
    ? currentStanding.Awards.filter(isDynamicSeasonAward).map(award => ({ ...award }))
    : [];
}

/** The source publishes winner identity and counts; Angular owns labels and visual styling only. */
function projectLegacyHighlight(
  fact: LegacyHighlightFact,
  teamById: Map<string, FantasyTeam>
): LeagueLegacyHighlight | null {
  const owner = teamById.get(String(fact.TeamID))?.Owner ?? `Team ${fact.TeamID}`;
  switch (fact.Key) {
    case 'ChampOfChamps':
      return { key: fact.Key, icon: '🏆', title: 'Champ of Champs', owner,
        valueDisplay: '#1 Overall', reason: 'Best all-time overall placement' };
    case 'RegularSeasonKing':
      return { key: fact.Key, icon: '👑', title: 'Regular Season King', owner,
        valueDisplay: '#1 Regular Season', reason: 'Best all-time regular-season table' };
    case 'PodiumMachine':
      return typeof fact.Count === 'number' && Number.isInteger(fact.Count) && fact.Count >= 0
        ? { key: fact.Key, icon: '🥇', title: 'Podium Machine', owner,
            valueDisplay: `${fact.Count} Podium${fact.Count === 1 ? '' : 's'}`,
            reason: 'Most top-3 playoff finishes' }
        : null;
    case 'AwardCollector':
      return typeof fact.Count === 'number' && Number.isInteger(fact.Count) && fact.Count >= 0
        ? { key: fact.Key, icon: '🎖️', title: 'Award Collector', owner,
            valueDisplay: `${fact.Count} Awards`, reason: 'Most historical season awards' }
        : null;
    default:
      return null;
  }
}

function mapSeasonHistoryAward(
  award: AwardInStanding,
  identity?: { OwnerAvatar?: string | null; TeamAvatar?: string | null }
): SeasonHistoryAwardItem {
  const displayText = award.Name;
  const typeText = award.Type?.DisplayText || award.Type?.Name;
  const tooltipParts = [displayText, typeText, award.TeamName, award.Owner, award.StatDisplay].filter(Boolean);

  return {
    key: award.Name,
    icon: award.Icon || unicodeToEmoji(award.IconUnicode),
    name: award.Name,
    displayText,
    owner: award.Owner,
    teamName: award.TeamName,
    teamAvatar: identity?.TeamAvatar?.trim() || 'assets/default-team-avatar.png',
    ownerAvatar: identity?.OwnerAvatar?.trim() || null,
    statDisplay: award.StatDisplay,
    tooltip: tooltipParts.join(' • '),
    order: award.Type?.Order ?? 999
  };
}

function normalizeStandingPlace(place: number | null | undefined): number {
  return Number.isFinite(place) && Number(place) > 0
    ? Number(place)
    : Number.MAX_SAFE_INTEGER;
}

function buildAwardTooltip(displayText: string, occurrences: number): string {
  return `${displayText} • Awarded ${occurrences}x`;
}

function formatRecord(wins: number, losses: number, ties: number): string {
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
}


function unicodeToEmoji(unicode: string): string {
  return unicode
    .split(' ')
    .map(code => String.fromCodePoint(parseInt(code, 16)))
    .join('');
}

// Legacy snapshot adapter only: winner detection always uses RegularSeason.Place === 1.
// Newly generated season awards no longer contain this historic display-name entry.
function isDynamicSeasonAward(award: { Name: string }): boolean {
  return award.Name !== 'Regular Season King';
}
