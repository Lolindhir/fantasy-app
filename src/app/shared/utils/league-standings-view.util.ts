import type { AwardInStanding, FantasyTeam, League } from '../../core/models/fantasy.models';

export interface CurrentStandingRow {
  team: FantasyTeam;
  displayPlace: number;
}

export interface SeasonResultTeam {
  team: FantasyTeam;
  place: number;
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
      place: team.Placements.Previous.Playoffs?.Place ?? team.Placements.Previous.Regular.Place
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

export function getPreviousChampion(teams: FantasyTeam[]): FantasyTeam | undefined {
  return teams.find(team => team.Placements.Previous.Playoffs?.Place === 1);
}

export function getCurrentSeasonAwards(league: League): AwardInStanding[] {
  const currentStanding = league.Standings.find(standing => standing.Season === league.Season);

  return currentStanding?.Awards
    ? currentStanding.Awards.map(award => ({ ...award }))
    : [];
}
