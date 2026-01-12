import { Component, OnInit } from '@angular/core';
import { DataService, Player, SortField } from '../services/data-service';
import { CommonModule } from '@angular/common';
import { ViewEncapsulation } from '@angular/core';
import { SharedMaterialImports } from '../shared/shared-material-imports';
import { forkJoin } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';



export interface SalaryCapResult {
  cap: number;
  capProjected: number;
  topPlayers: Player[];
  topPlayersProjected: Player[];
}


@Component({
  selector: 'app-team-list',
  imports: [
    CommonModule,
    FormsModule,
    SharedMaterialImports
  ],
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

      // TopSalaryTeam neu berechnen
      const team = this.fantasyTeams.find(t => t.TeamID === teamId);
      if (team) {
        const result = this.calculateSalaryCapTopPlayers(team.Roster);
        team.Salary = result.cap;
        team.SalaryProjected = result.capProjected;
      }
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


    private processTeam(team: any, topN: number = this.salaryRelevantTeamSize) {
      
      const roster = [...team.Roster];

      // TopSalary aus Team-Roster
      const result : SalaryCapResult = this.calculateSalaryCapTopPlayers(roster, topN);

      return {
        ...team,
        TopPlayers: this.sortPlayersBySalary(roster, false),
        Salary: result.cap,
        TopPlayersProjected: this.sortPlayersBySalary(roster, true),
        SalaryProjected: result.capProjected
      };
    }

    // Berechnet den Salary Cap basierend auf den Top-Spielern
    private calculateSalaryCapTopPlayers(allPlayers: Player[], topN: number = this.salaryRelevantTeamSize): SalaryCapResult {
      // Top N Spieler, die nicht exkludiert sind
      const allExcludedPlayers  = new Set<string>();

      for (const team of this.fantasyTeams) {
        const excluded = this.excludedPlayersByTeam[team.TeamID] ?? new Set();
        excluded.forEach(id => allExcludedPlayers.add(id));
      }

      // Spieler ohne Excludes
      const allPlayersNonExcluded = allPlayers.filter(p => !allExcludedPlayers.has(p.ID));
      // Multiplikator ist topN oder Länge der Nicht-Exkludierten, je nachdem was kleiner ist
      const playerCount = Math.min(topN, allPlayersNonExcluded.length);

      //Salary berechnen
      const topPlayers = this.sortPlayersBySalary(allPlayersNonExcluded, false).slice(0, playerCount);
      const avgOverall = playerCount > 0 ? topPlayers.reduce((sum, p) => sum + p.Salary, 0) / playerCount : 0;
      const cap = avgOverall * playerCount;

      //Projected Salary berechnen
      const topPlayersProjected = this.sortPlayersBySalary(allPlayersNonExcluded, true).slice(0, playerCount);
      const avgOverallProjected = playerCount > 0 ? topPlayersProjected.reduce((sum, p) => sum + p.SalaryProjected, 0) / playerCount : 0;
      const capProjected = avgOverallProjected * playerCount;


      return { 
        cap: cap, 
        topPlayers: topPlayers,
        capProjected: capProjected,
        topPlayersProjected: topPlayersProjected
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
      const isInTopN: boolean = team.Roster
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
        panelClass: 'player-dialog'
      });
    }

}
