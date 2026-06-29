import type { Award, AwardInStanding, FantasyTeam, League } from '../../core/models/fantasy.models';

export interface CurrentStandingRow {
  team: FantasyTeam;
  displayPlace: number;
}

export interface SeasonResultTeam {
  team: FantasyTeam;
  place: number;
  awardsDisplay: string;
}

export interface SeasonResultsViewModel {
  teams: SeasonResultTeam[];
  champion?: SeasonResultTeam;
  runnerUp?: SeasonResultTeam;
  thirdPlace?: SeasonResultTeam;
  remainingTeams: SeasonResultTeam[];
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
  place: number;
  placeOrdinal: string;
  owner: string;
  teamName: string | null;
}

export interface SeasonHistoryRegularSeasonRow {
  place: number;
  placeOrdinal: string;
  owner: string;
  teamName: string | null;
  record: string;
  points: number;
  pointsAgainst: number;
  winPercentageDisplay: string;
}

export interface SeasonHistoryAwardItem {
  key: string;
  icon: string;
  name: string;
  displayText: string;
  owner: string;
  teamName: string | null;
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

export function buildCurrentStandings(
  league: League,
  teams: FantasyTeam[]
): CurrentStandingRow[] {
  return [...teams]
    .map(team => ({
      team,
      displayPlace: league.IsFinished
        ? team.Placements.Previous.Playoffs?.Place ?? team.Placements.Previous.Regular.Place
        : team.Standing
    }))
    .sort((a, b) => a.displayPlace - b.displayPlace);
}

export function buildSeasonResults(teams: FantasyTeam[]): SeasonResultsViewModel {
  const resultTeams = [...teams]
    .map(team => ({
      team,
      place: team.Placements.Previous.Playoffs?.Place ?? team.Placements.Previous.Regular.Place,
      awardsDisplay: formatAwardsDisplay(team.Placements.Previous.Awards)
    }))
    .sort((a, b) => a.place - b.place);

  return {
    teams: resultTeams,
    champion: resultTeams[0],
    runnerUp: resultTeams[1],
    thirdPlace: resultTeams[2],
    remainingTeams: resultTeams.slice(3)
  };
}

export function buildAllTimeStandings(teams: FantasyTeam[]): AllTimeStandingRow[] {
  return [...teams]
    .sort((a, b) =>
      a.Placements.AllTime.Playoffs.Place - b.Placements.AllTime.Playoffs.Place
    )
    .map(team => ({
      team,
      place: team.Placements.AllTime.Playoffs.Place,
      owner: team.Owner,
      championships: team.Championships,
      runnerUps: team.RunnerUps,
      thirds: team.Thirds,
      regularSeasonWins: team.RegularSeasonWins,
      placeAverage: team.Placements.AllTime.Playoffs.PlaceAverage
    }));
}

export function buildAllTimeRegularSeasonStandings(
  teams: FantasyTeam[]
): AllTimeRegularSeasonStandingRow[] {
  return [...teams]
    .sort((a, b) =>
      a.Placements.AllTime.Regular.Place - b.Placements.AllTime.Regular.Place
    )
    .map(team => {
      const regular = team.Placements.AllTime.Regular;
      const wins = regular.Wins ?? 0;
      const losses = regular.Losses ?? 0;
      const ties = regular.Ties ?? 0;

      return {
        team,
        place: regular.Place,
        owner: team.Owner,
        wins,
        losses,
        ties,
        record: formatRecord(wins, losses, ties),
        points: regular.Points ?? 0,
        pointsAgainst: regular.PointsAgainst ?? 0,
        winPercentageDisplay: regular.WinPercentageDisplay ?? '',
        regularSeasonWins: regular.RegularSeasonWins ?? 0
      };
    });
}

export function buildAwardLegend(league: League): AwardLegendItem[] {
  const legendByKey = new Map<string, AwardLegendItem>();

  for (const standing of league.Standings ?? []) {
    for (const award of standing.Awards ?? []) {
      const key = award.Type?.Name || award.Name;
      const displayText = award.Type?.DisplayText || award.Name;
      const existing = legendByKey.get(key);

      if (existing) {
        existing.occurrences += 1;
        existing.tooltip = buildAwardTooltip(existing.displayText, existing.occurrences);
        continue;
      }

      legendByKey.set(key, {
        key,
        icon: award.Icon || unicodeToEmoji(award.IconUnicode),
        name: award.Name,
        displayText,
        tooltip: buildAwardTooltip(displayText, 1),
        order: award.Type?.Order ?? 999,
        occurrences: 1
      });
    }
  }

  return [...legendByKey.values()]
    .sort((a, b) => a.order - b.order || a.displayText.localeCompare(b.displayText));
}

export function buildLeagueLegacy(
  league: League,
  teams: FantasyTeam[]
): LeagueLegacyViewModel {
  const overallStandings = buildAllTimeStandings(teams);
  const regularSeasonStandings = buildAllTimeRegularSeasonStandings(teams);
  const awardLegend = buildAwardLegend(league);
  const teamById = new Map(teams.map(team => [String(team.TeamID), team]));

  return {
    highlights: buildLegacyHighlights(
      league,
      overallStandings,
      regularSeasonStandings,
      teamById
    ),
    overallStandings,
    regularSeasonStandings,
    awardLegend
  };
}

export function buildSeasonHistory(league: League): SeasonHistoryViewModel {
  const seasons = [...(league.Standings ?? [])]
    .map(standing => {
      const playoffResults = [...(standing.Playoffs ?? [])]
        .sort((a, b) => a.Place - b.Place)
        .map(row => ({
          place: row.Place,
          placeOrdinal: row.PlaceOrdinal,
          owner: row.Owner,
          teamName: row.TeamName
        }));

      const regularSeasonStandings = [...(standing.RegularSeason ?? [])]
        .sort((a, b) => a.Place - b.Place)
        .map(row => ({
          place: row.Place,
          placeOrdinal: row.PlaceOrdinal,
          owner: row.Owner,
          teamName: row.TeamName,
          record: row.Record ?? formatRecord(row.Wins ?? 0, row.Losses ?? 0, row.Ties ?? 0),
          points: row.Points ?? 0,
          pointsAgainst: row.PointsAgainst ?? 0,
          winPercentageDisplay: row.WinPercentageDisplay ?? ''
        }));

      const awards = [...(standing.Awards ?? [])]
        .sort((a, b) =>
          (a.Type?.Order ?? 999) - (b.Type?.Order ?? 999)
          || a.Name.localeCompare(b.Name)
        )
        .map(award => mapSeasonHistoryAward(award));

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

export function getCurrentSeasonAwards(league: League): AwardInStanding[] {
  const currentStanding = league.Standings.find(standing => standing.Season === league.Season);

  return currentStanding?.Awards
    ? currentStanding.Awards.map(award => ({ ...award }))
    : [];
}

function buildLegacyHighlights(
  league: League,
  overallStandings: AllTimeStandingRow[],
  regularSeasonStandings: AllTimeRegularSeasonStandingRow[],
  teamById: Map<string, FantasyTeam>
): LeagueLegacyHighlight[] {
  const champOfChamps = overallStandings[0];
  const regularSeasonKing = regularSeasonStandings[0];
  const podiumMachine = [...overallStandings].sort(comparePodiums)[0];
  const awardCollector = buildAwardCollectorHighlight(league, teamById, overallStandings);
  const highlights: LeagueLegacyHighlight[] = [];

  if (champOfChamps) {
    highlights.push({
      key: 'ChampOfChamps',
      icon: '🏆',
      title: 'Champ of Champs',
      owner: champOfChamps.owner,
      valueDisplay: '#1 Overall',
      reason: 'Best all-time overall placement'
    });
  }

  if (regularSeasonKing) {
    highlights.push({
      key: 'RegularSeasonKing',
      icon: '👑',
      title: 'Regular Season King',
      owner: regularSeasonKing.owner,
      valueDisplay: '#1 Regular Season',
      reason: 'Best all-time regular-season table'
    });
  }

  if (podiumMachine) {
    const podiums = podiumMachine.championships + podiumMachine.runnerUps + podiumMachine.thirds;

    highlights.push({
      key: 'PodiumMachine',
      icon: '🥇',
      title: 'Podium Machine',
      owner: podiumMachine.owner,
      valueDisplay: `${podiums} Podium${podiums === 1 ? '' : 's'}`,
      reason: 'Most top-3 playoff finishes'
    });
  }

  if (awardCollector) highlights.push(awardCollector);

  return highlights;
}

function buildAwardCollectorHighlight(
  league: League,
  teamById: Map<string, FantasyTeam>,
  overallStandings: AllTimeStandingRow[]
): LeagueLegacyHighlight | undefined {
  const awardCounts = new Map<string, { count: number; types: Set<string> }>();

  for (const standing of league.Standings ?? []) {
    for (const award of standing.Awards ?? []) {
      const teamId = String(award.TeamID);
      const count = awardCounts.get(teamId) ?? { count: 0, types: new Set<string>() };

      count.count += 1;
      count.types.add(award.Type?.Name || award.Name);
      awardCounts.set(teamId, count);
    }
  }

  const winner = [...awardCounts.entries()]
    .sort(([teamA, statsA], [teamB, statsB]) => {
      const awardDiff = statsB.count - statsA.count;
      if (awardDiff !== 0) return awardDiff;

      const typeDiff = statsB.types.size - statsA.types.size;
      if (typeDiff !== 0) return typeDiff;

      return getOverallPlace(teamA, overallStandings) - getOverallPlace(teamB, overallStandings);
    })[0];

  if (!winner) return undefined;

  const [teamId, stats] = winner;
  const team = teamById.get(teamId);

  return {
    key: 'AwardCollector',
    icon: '🎖️',
    title: 'Award Collector',
    owner: team?.Owner ?? `Team ${teamId}`,
    valueDisplay: `${stats.count} Awards`,
    reason: 'Most historical season awards'
  };
}

function mapSeasonHistoryAward(award: AwardInStanding): SeasonHistoryAwardItem {
  const displayText = award.Type?.DisplayText || award.Name;
  const tooltipParts = [displayText, award.Owner, award.StatDisplay].filter(Boolean);

  return {
    key: award.Type?.Name || award.Name,
    icon: award.Icon || unicodeToEmoji(award.IconUnicode),
    name: award.Name,
    displayText,
    owner: award.Owner,
    teamName: award.TeamName,
    statDisplay: award.StatDisplay,
    tooltip: tooltipParts.join(' • '),
    order: award.Type?.Order ?? 999
  };
}

function comparePodiums(a: AllTimeStandingRow, b: AllTimeStandingRow): number {
  const podiumsA = a.championships + a.runnerUps + a.thirds;
  const podiumsB = b.championships + b.runnerUps + b.thirds;

  return podiumsB - podiumsA
    || b.championships - a.championships
    || b.runnerUps - a.runnerUps
    || b.thirds - a.thirds
    || a.place - b.place;
}

function getOverallPlace(teamId: string, standings: AllTimeStandingRow[]): number {
  return standings.find(row => String(row.team.TeamID) === teamId)?.place ?? 999;
}

function formatAwardsDisplay(awards: Award | Award[] | null | undefined): string {
  return ensureArray(awards)
    .map(award => award.Icon || unicodeToEmoji(award.IconUnicode))
    .join('');
}

function buildAwardTooltip(displayText: string, occurrences: number): string {
  return `${displayText} • Awarded ${occurrences}x`;
}

function formatRecord(wins: number, losses: number, ties: number): string {
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
}

function ensureArray<T>(value: T | T[] | null | undefined): T[] {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function unicodeToEmoji(unicode: string): string {
  return unicode
    .split(' ')
    .map(code => String.fromCodePoint(parseInt(code, 16)))
    .join('');
}
