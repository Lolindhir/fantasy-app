import { Component, OnInit } from '@angular/core';
import { DataService, Player } from '../services/data-service';
import { CommonModule } from '@angular/common';
import { SharedMaterialImports } from '../shared/shared-material-imports';


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
  styleUrls: ['./team-list.scss']
})

export class TeamListComponent implements OnInit {
  
  fantasyTeams: any[] = [];
  allPlayers: Player[] = [];
  salaryCap: number = 0;
  // Positions-Keys als const Array
  readonly positions = ['QB', 'RB', 'WR', 'TE', 'Flex'] as const;
  // SalaryCap Top-Players initialisieren
  salaryCapTopPlayers: Record<PositionKey, Player[]> = {
    QB: [], RB: [], WR: [], TE: [], Flex: []
  };
  salaryCapTopTeamNumber: number = 20;
  salaryCapTopTeam: number = 0;
  salaryCapTopTeamPlayers: Player[] = [];
  salaryCapTopTeamExpanded = false;

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
    
    // 1️⃣ Alle Spieler holen
    this.dataService.getAllPlayers(['SalaryDollars']).subscribe(players => {
      this.allPlayers = players;

      // 2️⃣ FantasyTeams holen
      this.dataService.getFantasyTeams(['SalaryDollars']).subscribe(teams => {
        // Teams verarbeiten (TopPlayers pro Team)
        this.fantasyTeams = teams.map(team => this.processTeam(team));

        // 3️⃣ SalaryCap berechnen (basierend auf allen Spielern)
        const teamCount = this.fantasyTeams.length || 10;
        const capResult = this.calculateSalaryCap(this.allPlayers, teamCount);

        this.salaryCap = capResult.cap;
        this.salaryCapTopPlayers = capResult.topPlayers; // jetzt gefüllt

        // 4️⃣ Alternative SalaryCap Berechnung (Top X Spieler insgesamt)
        const capTopXResult = this.calculateSalaryCapTopPlayers(this.allPlayers, teamCount, this.salaryCapTopTeamNumber);
        this.salaryCapTopTeam = capTopXResult.cap;
        this.salaryCapTopTeamPlayers = capTopXResult.topPlayers;
      });
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


    // Top Spieler innerhalb des Teams
    const topTeam = roster.slice(0, topN);
    topPlayersTeam.push(...topTeam);

    // TopSalary aus Team-Roster
    const topSalaryTeam = Object.values(topPlayersTeam).flat().reduce((sum, p) => sum + p.SalaryDollars, 0);

    return {
      ...team,
      TopPlayersPosition: topPlayersPosition,
      TopSalaryPosition: topSalaryPosition,
      TopPlayersTeam: topPlayersTeam,
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
    // Top N Spieler insgesamt
    const topOverall: Player[] = allPlayers
      .sort((a, b) => b.SalaryDollars - a.SalaryDollars)
      .slice(0, topN * teamCount);

    // Durchschnitt über alle Top-Spieler
    const avgOverall = topOverall.length ? topOverall.reduce((sum, p) => sum + p.SalaryDollars, 0) / topOverall.length : 0;
    
    const cap = avgOverall * topN; // Multipliziert mit topN (z.B. 20)

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

}
