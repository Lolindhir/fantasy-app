import { Component, OnInit } from '@angular/core';
import { DataService } from '../../../core/services/data.service';
import type { Player } from '../../../core/models/fantasy.models';
import { CommonModule } from '@angular/common';
import { ViewEncapsulation } from '@angular/core';
import { SharedMaterialImports } from '../../../shared/shared-material-imports';
import { forkJoin } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { PlayerDetailDialogComponent } from '../../../shared/components/player-detail-dialog/player-detail-dialog';



@Component({
  selector: 'app-team-list',
  imports: [
    CommonModule,
    FormsModule,
    SharedMaterialImports
  ],
  standalone: true,
  templateUrl: './team-list.html',
  styleUrls: ['./team-list.scss'],
  encapsulation: ViewEncapsulation.None
})

export class TeamListComponent implements OnInit {
  
  isMobile: boolean = window.innerWidth <= 600;
  showProjected: boolean = false;
  timestamp: string | undefined;
  fantasyTeams: any[] = [];
  allPlayers: Player[] = [];
  salaryRelevantTeamSize: number = 0;
  salaryCap: number = 0;
  salaryCapProjected: number = 0;
  salaryCapTopPlayers: Player[] = [];
  salaryCapProjectedTopPlayers: Player[] = [];
  salaryCapTopPlayersExpanded = false;
  projectedText = "Projected"
  projectedAbr = "Proj."

  constructor(private dataService: DataService, private dialog: MatDialog) {}

  ngOnInit(): void {
    
    forkJoin({
      players: this.dataService.getAllPlayers(['Salary']),
      teams: this.dataService.getFantasyTeams(['Salary']),
      league: this.dataService.getLeague(['Salary']),
      ts: this.dataService.getLatestTimestamp()
    }).subscribe(({ players, teams, league, ts }) => {
      // TopPlayers pro Team aus League-Daten
      this.salaryRelevantTeamSize = league.SalaryRelevantTeamSize || 20;

      // Alle Spieler setzen
      this.allPlayers = [...players]
      .map(p => ({ ...p, Salary: Number(p.Salary) }))
      .sort((a, b) => b.Salary - a.Salary);

      // Teams verarbeiten (TopPlayers pro Team)
      this.fantasyTeams = teams.map(team => this.processTeam(team));

      // Timestamp setzen
      this.timestamp = ts;

      // Anzahl Teams
      const teamCount = this.fantasyTeams.length || 6;

      // SalaryCap (basierend auf allen Spielern)
      this.salaryCap = league.SalaryCap || 0;
      this.salaryCapProjected = league.SalaryCapProjected || 0;
      
      //sortiere allPlayers nach Salary absteigend
      this.allPlayers = this.sortPlayersBySalary(this.allPlayers, false);
      this.salaryCapTopPlayers = this.sortPlayersBySalary(this.allPlayers, false).slice(0, this.salaryRelevantTeamSize * teamCount);
      this.salaryCapProjectedTopPlayers = this.sortPlayersBySalary(this.allPlayers, true).slice(0, this.salaryRelevantTeamSize * teamCount);

      // Projected Text anpassen
      this.projectedText += " " + (league.SeasonAsNumber + 1).toString()
      this.projectedAbr += " " + (league.SeasonAsNumber + 1).toString()
      if(league.IsFinished){
        this.projectedText = (league.SeasonAsNumber + 1).toString();
        this.projectedAbr = (league.SeasonAsNumber + 1).toString();
      }

    });

  }


  // Temporäre Excludes pro Team
  excludedPlayersByTeam: { [teamId: string]: Set<string> } = {};
  isExcluded(teamId: string, playerId: string): boolean {
    if(teamId === null) return false; // Kein Team, also keine Excludes
    return this.excludedPlayersByTeam[teamId]?.has(playerId) ?? false;
  }
  toggleExclude(teamId: string, playerId: string): void {
    if (!this.excludedPlayersByTeam[teamId]) {
      this.excludedPlayersByTeam[teamId] = new Set();
    }

    const set = this.excludedPlayersByTeam[teamId];
    if (set.has(playerId)) {
      set.delete(playerId);
    } else {
      set.add(playerId);
    }

    // An excluded roster is an explicit, non-authoritative what-if state.
    const team = this.fantasyTeams.find(t => t.TeamID === teamId);
    if (team) Object.assign(team, this.processTeam(team));
  }

  // Toggles
  salaryCapExpanded = false;
  teamExpandedPosition: Record<number, boolean> = {}; // teamIndex → geöffnet/geschlossen
  teamExpandedTeam: Record<number, boolean> = {}; // teamIndex → geöffnet/geschlossen
  toggleSalaryCap() {
    this.salaryCapExpanded = !this.salaryCapExpanded;
  }
  toggleSalaryCapTopX() {
    this.salaryCapTopPlayersExpanded = !this.salaryCapTopPlayersExpanded;
  }
  toggleTeamPosition(index: number) {
    this.teamExpandedPosition[index] = !this.teamExpandedPosition[index];
  }
  toggleTeamTeam(index: number) {
    this.teamExpandedTeam[index] = !this.teamExpandedTeam[index];
  }


  private processTeam(team: any) {
    const roster = [...team.Roster] as Player[];
    const excluded = this.excludedPlayersByTeam[team.TeamID] ?? new Set<string>();
    const isWhatIf = excluded.size > 0;
    // Real roster usage is never calculated by Angular. The only permitted
    // local calculation is the user's explicitly modified excluded-roster scenario.
    const available = !!team.CapOutlook;
    let salary: number | null = team.CapOutlook?.Current.Usage ?? null;
    let projected: number | null = team.CapOutlook?.Projected.Usage ?? null;
    if (available && isWhatIf) {
      const simulated = roster.filter(p => !excluded.has(p.ID));
      salary = this.dataService.calculateTopPlayersSalary(
        simulated, this.salaryRelevantTeamSize, p => p.Salary
      ).cap;
      projected = this.dataService.calculateTopPlayersSalary(
        simulated, this.salaryRelevantTeamSize, p => p.SalaryProjected
      ).cap;
    }
    return {
      ...team,
      TopPlayers: this.sortPlayersBySalary(roster, false),
      TopPlayersProjected: this.sortPlayersBySalary(roster, true),
      IsSalaryAvailable: available,
      IsWhatIf: isWhatIf,
      Salary: salary,
      SalaryProjected: projected
    };
  }


  formatSalaryDollars(amount: number, plus: boolean, afterPoint: number): string {

    if(amount >= 0){
      if (plus) {
        return `+ $${(amount / 1_000_000).toFixed(afterPoint)} Mio.`;
      } else {
        return `$${(amount / 1_000_000).toFixed(afterPoint)} Mio.`;
      }
    } else {
      return `- $${(-amount / 1_000_000).toFixed(afterPoint)} Mio.`;
    }
  }

  getPositionColor(position: string): string {
    switch (position) {
      case 'WR': return '#337ccaff';
      case 'QB': return '#e24a4dff';
      case 'TE': return '#f28e2c';
      case 'K': return '#ab46bbff';
      case 'RB': return '#27998fff';
      case 'DEF': return '#999999';
      default: return '#555555';
    }
  }

  isPlayerExcludable(player: Player, team: any): boolean {

    if (team === null) {
      return false; // Kein Team, also keine Excludes
    }

    //hole die angepassten Top Players Count für das Team
    const adjustedTopPlayersCount = this.getAdjustedTopPlayersCount(team);

    // Überprüfe, ob der Spieler in den Top N des Teams ist
    const isInTopN: boolean = [...team.Roster]
      .sort((a: Player, b: Player) => b.Salary - a.Salary)
      .slice(0, adjustedTopPlayersCount)
      .some((p: Player) => p.ID === player.ID);

    return isInTopN;
  }

  getAdjustedTopPlayersCount(team: any): number {
    // Excludes berücksichtigen
    const excluded = this.excludedPlayersByTeam[team.TeamID] ?? new Set();
    return this.salaryRelevantTeamSize + excluded.size;
  }

  sortPlayersBySalary(players: Player[], useProjected: boolean): Player[] {
    const sorted = [...players].sort((a, b) => {
      if (useProjected) {
        // Primär: SalaryProjected, Sekundär: Salary
        const diff = (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);
        if (diff !== 0) return diff;
        return (b.Salary ?? 0) - (a.Salary ?? 0);
      } else {
        // Primär: Salary, Sekundär: SalaryProjected
        const diff = (b.Salary ?? 0) - (a.Salary ?? 0);
        if (diff !== 0) return diff;
        return (b.SalaryProjected ?? 0) - (a.SalaryProjected ?? 0);
      }
    });
    return sorted;
  }

  openPlayerDetail(player: Player) {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }

}