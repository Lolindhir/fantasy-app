import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DataService, FantasyTeam, League, Player, TopPlayersSalaryResult } from '../../../services/data-service';
import { FormsModule } from '@angular/forms';
import { SharedMaterialImports } from '../../../shared/shared-material-imports';
import { PlayerDetailDialogComponent } from '../../../shared/components/player-detail-dialog/player-detail-dialog';
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

  isMobile: boolean = window.innerWidth <= 600;

  selectedTeam?: FantasyTeam;
  selectedIncomingTeam?: FantasyTeam;
  availableIncomingTeams: FantasyTeam[] = [];
  selectedOutgoing: Player | null = null;
  selectedIncoming: Player | null = null;
  searchTerm: string = '';

  outgoingPlayers: Player[] = [];
  incomingPlayers: Player[] = [];

  allPlayers: Player[] = [];
  league: League | undefined;

  tradeResult?: {
    currentSalary: number;
    newSalary: number;
    currentProjected: number;
    newProjected: number;
    topPlayers: Player[];
  };

  SalaryCap: number = 0;
  SalaryCapProjected: number = 0;

  salaryRelevantTeamSize: number = 20; // Anzahl der Top-Spieler, die für den Salary Cap relevant sind
  newTeamTopPlayers: Player[] = [];

  projectedText = "Projected"
  projectedAbr = "Proj."

  constructor(private dataService: DataService, private dialog: MatDialog) {}

  ngOnInit() {
    this.dataService.getLeagueWithPlayers().subscribe(res => {
      this.allPlayers = res.players;
      this.league = res.league;
      this.SalaryCap = this.league?.SalaryCap || 0;
      this.SalaryCapProjected = this.league?.SalaryCapProjected || 0;

      // Projected Text anpassen
      this.projectedText += " " + (res.league.SeasonAsNumber + 1).toString()
      this.projectedAbr += " " + (res.league.SeasonAsNumber + 1).toString()
      if(res.league.IsFinished){
        this.projectedText = (res.league.SeasonAsNumber + 1).toString();
        this.projectedAbr = (res.league.SeasonAsNumber + 1).toString();
      }
    });
  }

  updateTradeState() {
    if (!this.selectedTeam) return;

    const roster = this.dataService.getRosterAfterTrade(
      this.selectedTeam.Roster,
      this.outgoingPlayers,
      this.incomingPlayers
    );

    const topPlayers = [...roster]
      .sort((a, b) => b.Salary - a.Salary)
      .slice(0, this.salaryRelevantTeamSize);

    this.tradeResult = {
      currentSalary:
        this.dataService.calculateTopPlayersSalary(
          this.selectedTeam.Roster,
          this.salaryRelevantTeamSize,
          p => p.Salary
        ).cap,

      newSalary:
        this.dataService.calculateTopPlayersSalary(
          roster,
          this.salaryRelevantTeamSize,
          p => p.Salary
        ).cap,

      currentProjected:
        this.dataService.calculateTopPlayersSalary(
          this.selectedTeam.Roster,
          this.salaryRelevantTeamSize,
          p => p.SalaryProjected
        ).cap,

      newProjected:
        this.dataService.calculateTopPlayersSalary(
          roster,
          this.salaryRelevantTeamSize,
          p => p.SalaryProjected
        ).cap,

      topPlayers
    };
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
      .filter(p => !this.outgoingPlayers.includes(p))
      .sort((a, b) => b.Salary - a.Salary);
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
    this.selectedOutgoing = null;
    this.updateTradeState();
  }

  // Spieler aus der Outgoing-Liste entfernen
  removeOutgoing(player: Player) {
    this.outgoingPlayers = this.outgoingPlayers.filter(p => p !== player);
    this.updateTradeState();
  }

  // Spieler zur Incoming-Liste hinzufügen
  addIncoming(player: Player) {
    if (!this.incomingPlayers.includes(player)) {
      this.incomingPlayers.push(player);
    }
    this.selectedIncoming = null;
    this.searchTerm = '';
    this.filterIncoming({ target: { value: '' } } as unknown as Event);
    this.updateTradeState();
  }

  // Spieler aus der Incoming-Liste entfernen
  removeIncoming(player: Player) {
    this.incomingPlayers = this.incomingPlayers.filter(p => p !== player);
    this.updateTradeState();
  }

  // Filter-Funktion für die Suche rechts
  filteredIncoming: Player[] = [];

  filterIncoming(event: Event) {
    
    const input = (event.target as HTMLInputElement).value.toLowerCase();

    if (!this.selectedTeam) return;

    const teamIds = this.selectedTeam.Roster.map(p => p.ID);

    var playerBase = this.allPlayers;
    //wenn ein Incoming Team ausgewählt ist, nur Spieler dieses Teams anzeigen, ansonsten alle verfügbaren Spieler
    if(this.selectedIncomingTeam){
      const incomingTeamRosterIds = this.selectedIncomingTeam.Roster.map(p => p.ID);
      playerBase = playerBase.filter(p => incomingTeamRosterIds.includes(p.ID));
    }

    this.filteredIncoming = playerBase.filter(p =>
      !teamIds.includes(p.ID) &&
      !this.incomingPlayers.includes(p)
    );

    if(input != ''){
      this.filteredIncoming = this.filteredIncoming.filter(p =>
        p.Name.toLowerCase().includes(input)
      );
    }

    //sortieren nach Salary
    this.filteredIncoming.sort((a, b) => b.Salary - a.Salary);
  }

  onTeamChange(team: FantasyTeam) {
    this.selectedTeam = team;
    this.selectedIncomingTeam = undefined;

    // Verfügbare Incoming Teams aktualisieren (alle außer dem ausgewählten Team)
    this.availableIncomingTeams = this.league?.Teams.filter(t => t.Team !== team.Team) || [];

    // Trade resetten
    this.outgoingPlayers = [];
    this.incomingPlayers = [];

    // Incoming Filter reset
    //this.filteredIncoming = this.availableIncoming;
    this.filterIncoming({ target: { value: '' } } as unknown as Event);

    this.selectedIncoming = null;

    this.updateTradeState();
  }

  onIncomingTeamChange(team: FantasyTeam) {
    this.selectedIncomingTeam = team;
    this.filterIncoming({ target: { value: '' } } as unknown as Event);
  }

  //ab hier 1 zu 1 aus TeamListComponent, da gleiche Funktionalität benötigt wird



  openPlayerDetail(player: Player) {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: player,
      width: '800px',
      maxHeight: '90vh',
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

  formatSalaryDollars(amount: number | undefined, plus: boolean, afterPoint: number): string {

    if (amount === null || amount === undefined) return "N/A";

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
