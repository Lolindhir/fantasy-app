import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DataService, FantasyTeam, League, Player, TopPlayersSalaryResult } from '../services/data-service';
import { FormsModule } from '@angular/forms';
import { SharedMaterialImports } from '../shared/shared-material-imports';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-trade-simulator',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SharedMaterialImports
  ],
  templateUrl: './trade-simulator.html',
  styleUrls: ['./trade-simulator.scss']
})
export class TradeSimulatorComponent implements OnInit {

  selectedTeam?: FantasyTeam;

  outgoingPlayers: Player[] = [];
  incomingPlayers: Player[] = [];

  allPlayers: Player[] = [];
  league: League | undefined;

  SalaryCap: number = 0;
  SalaryCapProjected: number = 0;

  salaryRelevantTeamSize: number = 20; // Anzahl der Top-Spieler, die für den Salary Cap relevant sind
  newTeamTopPlayers: Player[] = [];

  constructor(private dataService: DataService, private dialog: MatDialog) {}

  ngOnInit() {
    this.dataService.getLeagueWithPlayers().subscribe(res => {
      this.allPlayers = res.players;
      this.league = res.league;
      this.SalaryCap = this.league?.SalaryCap || 0;
      this.SalaryCapProjected = this.league?.SalaryCapProjected || 0;
    });
  }

  get newTeamSalary(): number {
    if (!this.selectedTeam) return 0;

    const topN = 20; // Anzahl Top-Spieler für Salary Cap
    const newRoster = this.dataService.getRosterAfterTrade(
      this.selectedTeam.Roster,
      this.outgoingPlayers,
      this.incomingPlayers
    );

    this.newTeamTopPlayers = newRoster
      .sort((a, b) => b.Salary - a.Salary)
      .slice(0, topN);

    const result: TopPlayersSalaryResult = this.dataService.calculateTopPlayersSalary(newRoster, topN, p => p.Salary);

    return result.cap;
  }

  get newTeamSalaryProjected(): number {
    if (!this.selectedTeam) return 0;

    const topN = 20; // Anzahl Top-Spieler für Salary Cap
    const newRoster = this.dataService.getRosterAfterTrade(
      this.selectedTeam.Roster,
      this.outgoingPlayers,
      this.incomingPlayers
    );

    this.newTeamTopPlayers = newRoster
      .sort((a, b) => b.Salary - a.Salary)
      .slice(0, topN);

    const result: TopPlayersSalaryResult = this.dataService.calculateTopPlayersSalary(newRoster, topN, p => p.SalaryProjected);

    return result.cap;
  }

  get currentTeamSalary(): number {
    if (!this.selectedTeam) return 0;
    const topN = 20;
    return this.dataService.calculateTopPlayersSalary(this.selectedTeam.Roster, topN, p => p.Salary).cap;
  }

  get currentTeamSalaryProjected(): number {
    if (!this.selectedTeam) return 0;
    const topN = 20;
    return this.dataService.calculateTopPlayersSalary(this.selectedTeam.Roster, topN, p => p.SalaryProjected).cap;
  }

  get salaryDifference(): number {
    return this.newTeamSalary - this.currentTeamSalary;
  }

  get salaryDifferenceProjected(): number {
    return this.newTeamSalaryProjected - this.currentTeamSalaryProjected;
  }

  get capAfterTrade(): number {
    if (!this.league) return 0;
    return this.league.SalaryCap - this.newTeamSalary;
  }


  get availableOutgoing(): Player[] {
    if (!this.selectedTeam) return [];
    return this.selectedTeam.Roster
      .filter(p => !this.outgoingPlayers.includes(p));
  }

  get availableIncoming(): Player[] {
    if (!this.selectedTeam) return [];

    const teamIds = this.selectedTeam.Roster.map(p => p.ID);

    return this.allPlayers.filter(p =>
      !teamIds.includes(p.ID) &&
      !this.incomingPlayers.includes(p)
    );
  }

  get outgoingSalary(): number {
    return this.outgoingPlayers
      .reduce((sum, p) => sum + p.Salary, 0);
  }

  get incomingSalary(): number {
    return this.incomingPlayers
      .reduce((sum, p) => sum + p.Salary, 0);
  }

  // Spieler zur Outgoing-Liste hinzufügen
  addOutgoing(player: Player) {
    if (!this.outgoingPlayers.includes(player)) {
      this.outgoingPlayers.push(player);
    }
  }

  // Spieler aus der Outgoing-Liste entfernen
  removeOutgoing(player: Player) {
    this.outgoingPlayers = this.outgoingPlayers.filter(p => p !== player);
  }

  // Spieler zur Incoming-Liste hinzufügen
  addIncoming(player: Player) {
    if (!this.incomingPlayers.includes(player)) {
      this.incomingPlayers.push(player);
    }
  }

  // Spieler aus der Incoming-Liste entfernen
  removeIncoming(player: Player) {
    this.incomingPlayers = this.incomingPlayers.filter(p => p !== player);
  }

  // Filter-Funktion für die Suche rechts
  filteredIncoming: Player[] = [];

  filterIncoming(event: Event) {
    const input = (event.target as HTMLInputElement).value.toLowerCase();
    if (!this.selectedTeam) return;

    const teamIds = this.selectedTeam.Roster.map(p => p.ID);

    this.filteredIncoming = this.allPlayers.filter(p =>
      !teamIds.includes(p.ID) &&
      !this.incomingPlayers.includes(p) &&
      p.Name.toLowerCase().includes(input)
    );
  }



  //ab hier 1 zu 1 aus TeamListComponent, da gleiche Funktionalität benötigt wird



  openPlayerDetail(player: Player) {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      panelClass: 'player-dialog'
    });
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

}
