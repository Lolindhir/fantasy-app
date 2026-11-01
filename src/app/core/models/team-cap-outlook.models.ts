/** L10 versioned App delivery contract; never an authoritative Salary/roster source. */
import type { RawLeague } from './league.models';
import type { RawPlayer } from './player.models';

export interface TeamCapCut {
  PlayerID: string;
  CutOrder: number;
  SalaryRank: number;
  SalaryUsed: number;
  CapBeforeCut: number;
  CapAfterCut: number;
}

export interface TeamCapLens {
  Usage: number;
  TopPlayerIDs: string[];
  Cuts: TeamCapCut[];
}

export interface TeamCapOutlookReadyTeam {
  TeamID: number;
  Status: 'ready';
  InputRoster: Array<{ PlayerID: string; Salary: number; SalaryProjected: number }>;
  Current: TeamCapLens;
  Projected: TeamCapLens;
}

export interface TeamCapOutlookUnavailableTeam {
  TeamID: number;
  Status: 'unavailable';
  Reason: string;
  MissingPlayerIDs?: string[];
}

export interface TeamCapOutlookReadModel {
  ContractVersion: number;
  CanonicalLeagueID: string;
  ProviderLeagueID: string;
  Season: number;
  AsOfFinalScoredWeek: number;
  Models: { RosterCap: string; AutoCut: string };
  SalaryRelevantTeamSize: number;
  SalaryCap: number;
  SalaryCapProjected: number;
  Teams: Array<TeamCapOutlookReadyTeam | TeamCapOutlookUnavailableTeam>;
}

function validLens(lens: TeamCapLens | undefined, rosterIDs: Set<string>): boolean {
  return !!lens && Number.isFinite(lens.Usage) && lens.Usage >= 0 &&
    Array.isArray(lens.TopPlayerIDs) && Array.isArray(lens.Cuts) &&
    lens.TopPlayerIDs.every(id => typeof id === 'string' && rosterIDs.has(id)) &&
    new Set(lens.TopPlayerIDs).size === lens.TopPlayerIDs.length &&
    lens.Cuts.every((cut, i) =>
      typeof cut.PlayerID === 'string' && rosterIDs.has(cut.PlayerID) &&
      cut.CutOrder === i + 1 && cut.SalaryRank === 6 &&
      [cut.SalaryUsed, cut.CapBeforeCut, cut.CapAfterCut].every(Number.isFinite)
    ) && new Set(lens.Cuts.map(c => c.PlayerID)).size === lens.Cuts.length;
}

/** Pure revision check: compare the central calculation's input witness, never recompute a cap. */
export function verifyTeamCapOutlook(
  readModel: TeamCapOutlookReadModel | null | undefined,
  league: RawLeague,
  players: RawPlayer[]
): Map<number, TeamCapOutlookReadyTeam> {
  const verified = new Map<number, TeamCapOutlookReadyTeam>();
  if (!readModel || readModel.ContractVersion !== 1 ||
      !readModel.CanonicalLeagueID || readModel.ProviderLeagueID !== String(league.LeagueID) ||
      readModel.Season !== Number(league.Season) ||
      readModel.AsOfFinalScoredWeek !== league.FinalScoredWeek ||
      readModel.SalaryRelevantTeamSize !== league.SalaryRelevantTeamSize ||
      readModel.SalaryCap !== league.SalaryCap ||
      readModel.SalaryCapProjected !== league.SalaryCapProjected ||
      typeof readModel.Models?.RosterCap !== 'string' || !readModel.Models.RosterCap.trim() ||
      typeof readModel.Models?.AutoCut !== 'string' || !readModel.Models.AutoCut.trim() ||
      !Array.isArray(readModel.Teams) || readModel.Teams.length !== league.Teams.length) {
    return verified;
  }
  const playerMap = new Map<string, RawPlayer>();
  for (const player of players) {
    if (!player.ID || playerMap.has(player.ID)) return new Map();
    playerMap.set(player.ID, player);
  }
  const outlooks = new Map<number, TeamCapOutlookReadModel['Teams'][number]>();
  for (const team of readModel.Teams) {
    if (outlooks.has(team.TeamID)) return new Map();
    outlooks.set(team.TeamID, team);
  }
  for (const sourceTeam of league.Teams) {
    const team = outlooks.get(sourceTeam.TeamID);
    if (!team || team.Status !== 'ready') continue;
    const ids = sourceTeam.Roster ?? [];
    if (!Array.isArray(team.InputRoster) || ids.length !== team.InputRoster.length ||
        ids.length !== new Set(ids).size) continue;
    const rosterIDs = new Set(ids);
    const witnessMatches = ids.every((pid, index) => {
      const witness = team.InputRoster[index];
      const player = playerMap.get(pid);
      return !!player && !!witness && witness.PlayerID === pid &&
        Number.isFinite(player.Salary) && Number.isFinite(player.SalaryProjected) &&
        witness.Salary === player.Salary && witness.SalaryProjected === player.SalaryProjected;
    });
    if (!witnessMatches || !validLens(team.Current, rosterIDs) ||
        !validLens(team.Projected, rosterIDs)) continue;
    verified.set(team.TeamID, team);
  }
  return verified;
}
