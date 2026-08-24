import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import type { FantasyTeam, League } from '../../../core/models/fantasy.models';
import { DataService } from '../../../core/services/data.service';
import { CapUsageBarComponent } from '../../../shared/components/cap-usage-bar/cap-usage-bar';
import { SalaryHealthIndicatorComponent } from '../../../shared/components/salary-health-indicator/salary-health-indicator';
import { TeamDetailDialogService } from '../../../shared/services/team-detail-dialog.service';
import { SharedMaterialImports } from '../../../shared/shared-material-imports';
import {
  buildTeamSalarySummary,
  getEarliestOpenPicks,
  getTeamRosterLimits,
  getTeamSeasonSummary,
  splitTeamRoster,
  type TeamOpenPicksSummary,
  type TeamRosterLimits,
  type TeamSalarySummary,
  type TeamSeasonSummary
} from '../../../shared/utils/team-salary.util';

interface TeamCardViewModel {
  team: FantasyTeam;
  salary: TeamSalarySummary;
  roster: ReturnType<typeof splitTeamRoster>;
  limits: TeamRosterLimits;
  season: TeamSeasonSummary;
  openPicks?: TeamOpenPicksSummary;
}

@Component({
  selector: 'app-teams-page',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatProgressSpinnerModule,
    SharedMaterialImports,
    CapUsageBarComponent,
    SalaryHealthIndicatorComponent
  ],
  templateUrl: './teams-page.html',
  styleUrl: './teams-page.scss'
})
export class TeamsPageComponent implements OnInit {
  league?: League;
  cards: TeamCardViewModel[] = [];
  loading = true;

  constructor(
    private dataService: DataService,
    private teamDetailDialog: TeamDetailDialogService
  ) {}

  ngOnInit(): void {
    this.dataService.getLeagueWithPlayers(['Salary']).subscribe(({ league, teams }) => {
      this.league = league;
      this.cards = [...teams]
        .sort((a, b) => a.TeamID - b.TeamID)
        .map(team => ({
          team,
          salary: buildTeamSalarySummary(team, league),
          roster: splitTeamRoster(team),
          limits: getTeamRosterLimits(league),
          season: getTeamSeasonSummary(team, league),
          openPicks: getEarliestOpenPicks(team, league.SeasonAsNumber)
        }));
      this.loading = false;
    });
  }

  openTeam(team: FantasyTeam): void {
    this.teamDetailDialog.open(team.TeamID);
  }

  onCardKeydown(event: KeyboardEvent, team: FantasyTeam): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.openTeam(team);
    }
  }

  displayTeamName(team: FantasyTeam): string {
    return team.Team || `Team ${team.TeamID}`;
  }

  displayLimit(value: number, limit?: number): string {
    return limit ? `${value} / ${limit}` : `${value}`;
  }
}
