import { Injectable } from '@angular/core';
import { formatSalaryDollars } from '../mappers/player.mapper';
import type { FantasyTeam, RawLeague } from '../models/league.models';
import type { FreeAgentMarketInfo, FreeAgentSalaryMode, Player } from '../models/player.models';
import type { TeamCapOutlookReadyTeam, TeamCapCut } from '../models/team-cap-outlook.models';

@Injectable({ providedIn: 'root' })
export class FreeAgentMarketService {
  /** Display verified central predictions; never recalculate or fall back to Angular cut rules. */
  enrich(
    players: Player[], teams: FantasyTeam[], league: RawLeague,
    verified: Map<number, TeamCapOutlookReadyTeam> = new Map()
  ): void {
    for (const lens of ['Current', 'Projected'] as const) {
      for (const player of players) {
        const isFree = !player.TeamFantasy;
        if (lens === 'Current') player.IsFantasyFreeAgent = isFree;
        this.setInfo(player, {
          Status: isFree ? 'FreeAgent' : 'Rostered',
          StatusDisplay: isFree ? 'Free Agent' : 'Rostered',
          PredictionModel: 'CurrentOnly',
          SalaryMode: lens,
          Probability: isFree ? 1 : 0,
          Reason: isFree
            ? 'Player is currently not assigned to any fantasy team.'
            : 'Player is currently rostered by a fantasy team.'
        }, lens);
      }
      for (const team of teams) {
        const outlook = verified.get(team.TeamID);
        if (!outlook) continue;
        for (const cut of outlook[lens].Cuts) {
          const player = team.Roster.find(p => p.ID === cut.PlayerID);
          if (!player) continue;
          const limit = lens === 'Projected' ? league.SalaryCapProjected : league.SalaryCap;
          this.setInfo(player, this.cutInfo(team, cut, lens, limit), lens);
        }
      }
    }
  }

  private cutInfo(team: FantasyTeam, cut: TeamCapCut, lens: FreeAgentSalaryMode, limit: number): FreeAgentMarketInfo {
    return {
      Status: 'ProjectedCapCut', StatusDisplay: 'Projected Cap Cut',
      PredictionModel: 'RuleBasedAutoCut', SalaryMode: lens, Probability: 1,
      Reason: 'Team is over the salary cap. Rule-based model cuts the current 6th highest salary player until the team is under the cap.',
      TeamID: team.TeamID, TeamName: team.Team ?? `Team ${team.Owner}`, Owner: team.Owner,
      CutOrder: cut.CutOrder, SalaryRank: cut.SalaryRank, SalaryUsed: cut.SalaryUsed,
      SalaryUsedDisplay: formatSalaryDollars(cut.SalaryUsed),
      CapLimit: limit, CapLimitDisplay: formatSalaryDollars(limit),
      CapBeforeCut: cut.CapBeforeCut, CapBeforeCutDisplay: formatSalaryDollars(cut.CapBeforeCut),
      CapAfterCut: cut.CapAfterCut, CapAfterCutDisplay: formatSalaryDollars(cut.CapAfterCut)
    };
  }

  private setInfo(player: Player, info: FreeAgentMarketInfo, lens: FreeAgentSalaryMode): void {
    const available = info.Status === 'FreeAgent' ||
      info.Status === 'ProjectedCapCut' || info.Status === 'PossibleCapCut';
    if (lens === 'Projected') {
      player.FreeAgentMarketInfoProjected = info;
      player.IsFreeAgentDraftAvailableProjected = available;
    } else {
      player.FreeAgentMarketInfo = info;
      player.IsFreeAgentDraftAvailable = available;
    }
  }
}
