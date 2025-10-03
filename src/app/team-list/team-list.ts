import { Component, OnInit } from '@angular/core';
import { DataService, Player } from '../services/data-service';
import { CommonModule } from '@angular/common';
import { ViewEncapsulation } from '@angular/core';
import { SharedMaterialImports } from '../shared/shared-material-imports';
import { forkJoin } from 'rxjs';


export interface SalaryCapResult {
  cap: number;
  topPlayers: { [key in 'QB' | 'RB' | 'WR' | 'TE' | 'Flex']: Player[] };
}

export interface SalaryCapTopXResult {
  cap: number;
  topPlayers: Player[];
}

const positions = ['QB', 'RB', 'WR', 'TE', 'Flex'] as const;
type PositionKey = typeof positions[number]; // 'QB' | 'RB' | 'WR' | 'TE' | 'Flex'

@Component({
  selector: 'app-team-list',
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './team-list.html',
  styleUrls: ['./team-list.scss'],
  encapsulation: ViewEncapsulation.None
})

export class TeamListComponent implements OnInit {
  
  isMobile: boolean = window.innerWidth <= 600;
  timestamp: string | undefined;
  fantasyTeams: any[] = [];
  allPlayers: Player[] = [];
  //salaryCap: number = 0;
  // Positions-Keys als const Array
  readonly positions = ['QB', 'RB', 'WR', 'TE', 'Flex'] as const;
  // SalaryCap Top-Players initialisieren
  // salaryCapTopPlayers: Record<PositionKey, Player[]> = {
  //   QB: [], RB: [], WR: [], TE: [], Flex: []
  // };
  salaryCapTopTeamNumber: number = 20;
  salaryCapTopTeam: number = 0;
  salaryCapTopTeamPlayers: Player[] = [];
  salaryCapTopTeamExpanded = false;

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
      team.TopSalaryTeam = this.calculateSalaryCapTopPlayers(team.Roster, 1).cap;
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
    this.salaryCapTopTeamExpanded = !this.salaryCapTopTeamExpanded;
  }

  toggleTeamPosition(index: number) {
    this.teamExpandedPosition[index] = !this.teamExpandedPosition[index];
  }

  toggleTeamTeam(index: number) {
    this.teamExpandedTeam[index] = !this.teamExpandedTeam[index];
  }

  constructor(private dataService: DataService) {}

  ngOnInit(): void {
    
    forkJoin({
      players: this.dataService.getAllPlayers(['SalaryDollars']),
      teams: this.dataService.getFantasyTeams(['SalaryDollars']),
      ts: this.dataService.getLatestTimestamp()
    }).subscribe(({ players, teams, ts }) => {
      
      // Alle Spieler setzen
      this.allPlayers = players;
      
      // Teams verarbeiten (TopPlayers pro Team)
      this.fantasyTeams = teams.map(team => this.processTeam(team));

      // Timestamp setzen
      this.timestamp = ts;

      // SalaryCap berechnen (basierend auf allen Spielern)
      const teamCount = this.fantasyTeams.length || 6;
      //const capResult = this.calculateSalaryCap(this.allPlayers, teamCount);
      //this.salaryCap = capResult.cap;
      //this.salaryCapTopPlayers = capResult.topPlayers;

      // Alternative SalaryCap Berechnung (Top X Spieler insgesamt)
      const capTopXResult = this.calculateSalaryCapTopPlayers(this.allPlayers, teamCount, this.salaryCapTopTeamNumber);
      this.salaryCapTopTeam = capTopXResult.cap;
      this.salaryCapTopTeamPlayers = capTopXResult.topPlayers;      

      // ✅ Debug hier rein!
      console.log('All players loaded:', this.allPlayers.length);
      console.log('Sample top 10:', [...this.allPlayers]
        .sort((a,b)=>b.SalaryDollars-a.SalaryDollars)
        .slice(0,10));
      //console.log('Final SalaryCap:', this.salaryCap);
      console.log('Final SalaryCapTopTeam:', this.salaryCapTopTeam);
      console.log('TeamCount:', teamCount);

    });

  }

  private processTeam(team: any, topN: number = this.salaryCapTopTeamNumber) {
    const positions = { QB: 2, WR: 2, RB: 2, TE: 2 } as const;
    const roster = [...team.Roster];
    const topPlayersPosition: { [key in keyof typeof positions | 'Flex']?: Player[] } = {};
    const topPlayersTeam: Player[] = [];
    const usedIds = new Set<string>();

    // Top Spieler pro Position innerhalb des Teams
    for (const pos of Object.keys(positions) as Array<keyof typeof positions>) {
      const top = roster.filter(p => p.Position === pos && !usedIds.has(p.ID)).slice(0, positions[pos]);
      top.forEach(p => usedIds.add(p.ID));
      topPlayersPosition[pos] = top;
    }

    // Top 4 Flex innerhalb des Teams (WR/RB/TE)
    const flex = roster.filter(p => ['WR', 'RB', 'TE'].includes(p.Position) && !usedIds.has(p.ID)).slice(0, 4);
    flex.forEach(p => usedIds.add(p.ID));
    topPlayersPosition['Flex'] = flex;

    // TopSalary aus Position-Roster
    const topSalaryPosition = Object.values(topPlayersPosition).flat().reduce((sum, p) => sum + p.SalaryDollars, 0);

    // === Alle Spieler des Teams für Anzeige ===
    const allTeamPlayers = [...roster]; // einfach alle Spieler

    // Top Spieler innerhalb des Teams
    const topTeam = roster
    .sort((a, b) => b.SalaryDollars - a.SalaryDollars)
    .slice(0, topN);
    topPlayersTeam.push(...topTeam);

    // TopSalary aus Team-Roster
    const topSalaryTeam = this.calculateSalaryCapTopPlayers(allTeamPlayers, 1, topN).cap;

    return {
      ...team,
      TopPlayersPosition: topPlayersPosition,
      TopSalaryPosition: topSalaryPosition,
      TopPlayersTeam: allTeamPlayers, //topPlayersTeam, um nur die Top N Spieler zu zeigen
      TopSalaryTeam: topSalaryTeam
    };
  }


  /**
   * Berechnet das SalaryCap für ein Team basierend auf allen Spielern
   */
  private calculateSalaryCap(allPlayers: Player[], teamCount: number): SalaryCapResult {
  const positions = { QB: 2, WR: 2, RB: 2, TE: 2 } as const;
  const usedIds = new Set<string>();
  const topPlayers: { [key in keyof typeof positions | 'Flex']: Player[] } = {
    QB: [], RB: [], WR: [], TE: [], Flex: []
  };

    // Top Spieler pro Position (für SalaryCap)
    for (const pos of Object.keys(positions) as Array<keyof typeof positions>) {
      const top = allPlayers
        .filter(p => p.Position === pos && !usedIds.has(p.ID))
        .sort((a, b) => b.SalaryDollars - a.SalaryDollars)
        .slice(0, positions[pos] * teamCount); // alle benötigten Spieler

      top.forEach(p => usedIds.add(p.ID));
      topPlayers[pos] = top;
    }

    // Top Flex-Spieler (WR, RB, TE)
    const flex = allPlayers
      .filter(p => ['WR', 'RB', 'TE'].includes(p.Position) && !usedIds.has(p.ID))
      .sort((a, b) => b.SalaryDollars - a.SalaryDollars)
      .slice(0, 4 * teamCount);

    flex.forEach(p => usedIds.add(p.ID));
    topPlayers['Flex'] = flex;

    // SalaryCap berechnen: Durchschnitt * Anzahl Spieler pro Team
    const avgQB = topPlayers.QB.reduce((sum, p) => sum + p.SalaryDollars, 0) / topPlayers.QB.length || 0;
    const avgRB = topPlayers.RB.reduce((sum, p) => sum + p.SalaryDollars, 0) / topPlayers.RB.length || 0;
    const avgWR = topPlayers.WR.reduce((sum, p) => sum + p.SalaryDollars, 0) / topPlayers.WR.length || 0;
    const avgTE = topPlayers.TE.reduce((sum, p) => sum + p.SalaryDollars, 0) / topPlayers.TE.length || 0;
    const avgFlex = topPlayers.Flex.reduce((sum, p) => sum + p.SalaryDollars, 0) / topPlayers.Flex.length || 0;

    // Anzahl Spieler pro Team
    const cap =
      avgQB * positions.QB +
      avgRB * positions.RB +
      avgWR * positions.WR +
      avgTE * positions.TE +
      avgFlex * 4; // 4 Flex-Spieler pro Team

    return { cap, topPlayers };
  }


  /**
   * Alternative Salary Cap Berechnung:
   * - Nimmt die Top 20 Spieler insgesamt (nach SalaryDollars)
   * - Multipliziert die Spielerzahl mit teamCount
   */
  private calculateSalaryCapTopPlayers(allPlayers: Player[], teamCount: number, topN: number = this.salaryCapTopTeamNumber): SalaryCapTopXResult {
    // Top N Spieler, die nicht exkludiert sind
    const allExcludedPlayers  = new Set<string>();

    for (const team of this.fantasyTeams) {
      const excluded = this.excludedPlayersByTeam[team.TeamID] ?? new Set();
      excluded.forEach(id => allExcludedPlayers.add(id));
    }

    // const sorted = [...allPlayers].sort((a,b) => b.SalaryDollars - a.SalaryDollars);
    // console.log('Top 30 Spieler nach Salary sortiert:', sorted.slice(0, 30).map(p => ({name: p.NameShort, salary: p.SalaryDollars})));

    // const topOverall: Player[] = sorted.slice(0, topN * teamCount);
    // console.log('TopOverall Slice:', topOverall.map(p => ({name: p.NameShort, salary: p.SalaryDollars})));

    const topOverall: Player[] = allPlayers
    .filter(p => !allExcludedPlayers.has(p.ID))   // <-- Excludes anwenden!
    .map(p => ({ ...p, SalaryDollars: Number(p.SalaryDollars) }))
    .sort((a,b) => b.SalaryDollars - a.SalaryDollars)
    .slice(0, topN * teamCount);

    // Durchschnitt über alle Top-Spieler
    const avgOverall = topOverall.length ? topOverall.reduce((sum, p) => sum + p.SalaryDollars, 0) / topOverall.length : 0;
    
    // Multiplikator ist topN oder topOverall.length, je nachdem was kleiner ist
    const multiplier = Math.min(topN, topOverall.length);

    const cap = avgOverall * multiplier; // Multipliziert mit multiplier (z.B. 20)

    return { cap, topPlayers: topOverall };
  }

  formatSalaryDollars(amount: number, plus: boolean = false): string {
    
    if(amount >= 0){
      if (plus) {
        return `+ $${(amount / 1_000_000).toFixed(1)} Mio.`;
      } else {
        return `$${(amount / 1_000_000).toFixed(1)} Mio.`;
      }

    } else {
      return `- $${(-amount / 1_000_000).toFixed(1)} Mio.`;
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
      .sort((a: Player, b: Player) => b.SalaryDollars - a.SalaryDollars)
      .slice(0, adjustedTopPlayersCount)
      .some((p: Player) => p.ID === player.ID);

    return isInTopN;
  }

  getAdjustedTopPlayersCount(team: any): number {
    // Excludes berücksichtigen
    const excluded = this.excludedPlayersByTeam[team.TeamID] ?? new Set();
    return this.salaryCapTopTeamNumber + excluded.size;
  }

}
