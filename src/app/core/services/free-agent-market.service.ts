import { Injectable } from '@angular/core';

import { formatSalaryDollars } from '../mappers/player.mapper';
import type { FantasyTeam, RawLeague } from '../models/league.models';
import type {
  FreeAgentMarketInfo,
  FreeAgentPredictionModel,
  FreeAgentSalaryMode,
  Player
} from '../models/player.models';
import { calculateTopPlayersSalary } from '../../shared/utils/trade-calculator.util';

@Injectable({
  providedIn: 'root'
})
export class FreeAgentMarketService {

  enrich(players: Player[], teams: FantasyTeam[], league: RawLeague): void {
    this.applyFreeAgentPredictionModel(
      players,
      teams,
      league,
      'RuleBasedAutoCut',
      'Current'
    );

    this.applyFreeAgentPredictionModel(
      players,
      teams,
      league,
      'RuleBasedAutoCut',
      'Projected'
    );
  }

  private applyFreeAgentPredictionModel(
    players: Player[],
    teams: FantasyTeam[],
    league: RawLeague,
    model: FreeAgentPredictionModel,
    salaryMode: FreeAgentSalaryMode
  ): void {
    players.forEach(player => {
      const isFantasyFreeAgent = !player.TeamFantasy;

      if (salaryMode === 'Current') {
        player.IsFantasyFreeAgent = isFantasyFreeAgent;
      }

      const info = isFantasyFreeAgent
        ? this.createFreeAgentMarketInfo(
            'FreeAgent',
            'Free Agent',
            'CurrentOnly',
            salaryMode,
            1,
            'Player is currently not assigned to any fantasy team.'
          )
        : this.createFreeAgentMarketInfo(
            'Rostered',
            'Rostered',
            model,
            salaryMode,
            0,
            'Player is currently rostered by a fantasy team.'
          );

      this.setFreeAgentMarketInfo(player, info, salaryMode);
    });

    if (model === 'CurrentOnly') {
      return;
    }

    if (model === 'RuleBasedAutoCut') {
      this.applyRuleBasedAutoCutModel(players, teams, league, salaryMode);
    }
  }

  private applyRuleBasedAutoCutModel(
    players: Player[],
    teams: FantasyTeam[],
    league: RawLeague,
    salaryMode: FreeAgentSalaryMode
  ): void {
    const salaryRelevantTeamSize = league.SalaryRelevantTeamSize;
    const capLimit = salaryMode === 'Projected'
      ? (league.SalaryCapProjected ?? league.SalaryCap)
      : league.SalaryCap;

    const salarySelector = salaryMode === 'Projected'
      ? (player: Player) => player.SalaryProjected ?? player.Salary
      : (player: Player) => player.Salary;

    teams.forEach(team => {
      let simulatedRoster = [...team.Roster];

      let currentCap = calculateTopPlayersSalary(
        simulatedRoster,
        salaryRelevantTeamSize,
        salarySelector
      ).cap;

      if (currentCap <= capLimit) {
        return;
      }

      let cutOrder = 1;

      while (currentCap > capLimit) {
        const sortedRoster = [...simulatedRoster].sort(
          (a, b) => salarySelector(b) - salarySelector(a)
        );

        const nextCutCandidate = sortedRoster[5];

        if (!nextCutCandidate) {
          break;
        }

        const capBeforeCut = currentCap;
        const salaryUsed = salarySelector(nextCutCandidate);

        simulatedRoster = simulatedRoster.filter(
          player => player.ID !== nextCutCandidate.ID
        );

        currentCap = calculateTopPlayersSalary(
          simulatedRoster,
          salaryRelevantTeamSize,
          salarySelector
        ).cap;

        const info = this.createFreeAgentMarketInfo(
          'ProjectedCapCut',
          'Projected Cap Cut',
          'RuleBasedAutoCut',
          salaryMode,
          1,
          'Team is over the salary cap. Rule-based model cuts the current 6th highest salary player until the team is under the cap.',
          {
            TeamID: team.TeamID,
            TeamName: team.Team ?? `Team ${team.Owner}`,
            Owner: team.Owner,
            CutOrder: cutOrder,
            SalaryRank: 6,
            SalaryUsed: salaryUsed,
            SalaryUsedDisplay: formatSalaryDollars(salaryUsed),
            CapLimit: capLimit,
            CapLimitDisplay: formatSalaryDollars(capLimit),
            CapBeforeCut: capBeforeCut,
            CapBeforeCutDisplay: formatSalaryDollars(capBeforeCut),
            CapAfterCut: currentCap,
            CapAfterCutDisplay: formatSalaryDollars(currentCap)
          }
        );

        this.setFreeAgentMarketInfo(nextCutCandidate, info, salaryMode);
        cutOrder++;
      }
    });
  }

  private createFreeAgentMarketInfo(
    status: FreeAgentMarketInfo['Status'],
    statusDisplay: string,
    model: FreeAgentPredictionModel,
    salaryMode: FreeAgentSalaryMode,
    probability: number,
    reason: string,
    extra?: Partial<FreeAgentMarketInfo>
  ): FreeAgentMarketInfo {
    return {
      Status: status,
      StatusDisplay: statusDisplay,
      PredictionModel: model,
      SalaryMode: salaryMode,
      Probability: probability,
      Reason: reason,
      ...extra
    };
  }

  private setFreeAgentMarketInfo(
    player: Player,
    info: FreeAgentMarketInfo,
    salaryMode: FreeAgentSalaryMode
  ): void {
    const isAvailable =
      info.Status === 'FreeAgent' ||
      info.Status === 'ProjectedCapCut' ||
      info.Status === 'PossibleCapCut';

    if (salaryMode === 'Projected') {
      player.FreeAgentMarketInfoProjected = info;
      player.IsFreeAgentDraftAvailableProjected = isAvailable;
      return;
    }

    player.FreeAgentMarketInfo = info;
    player.IsFreeAgentDraftAvailable = isAvailable;
  }
}
