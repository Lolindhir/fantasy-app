import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { map } from 'rxjs/operators';


export interface DataTimestamps {
  League: string;  // ISO String
  Players: string; // ISO String
  Teams: string;   // ISO String
}

export interface RawLeague {
  LeagueID: string;
  Name: string;
  Season: string;
  Teams: RawFantasyTeam[]; // nur rohe Teams
}

export interface League extends Omit<RawLeague, 'Teams'> {
  Teams: FantasyTeam[]; // angereicherte Teams
}

export interface RawFantasyTeam {
  Owner: string;
  Team: string;
  TeamID: number;
  Roster: string[]; // nur Spieler-IDs
  TeamAvatar?: string;
  OwnerAvatar: string;
  Points: number;
  PointsAgainst: number;
  Wins: number;
  Losses: number;
  Ties: number;
  Record: string;
  Streak: string;
}

export interface FantasyTeam extends Omit<RawFantasyTeam, 'Roster' | 'TeamAvatar' | 'OwnerAvatar'> {
  Roster: Player[]; // richtige Spieler
  Avatar: string;
  Standing: number; // Platzierung in der Liga
}

export interface RawPlayer {
  ID: string;
  Name: string;
  NameFirst: string;
  NameLast: string;
  NameShort: string;
  Position: string;
  TeamID: string; // Referenz, nicht das Teamobjekt
  Salary: number;
  Age: number;
  Year: number;
  Picture: string;
}

export interface Player extends Omit<RawPlayer, 'TeamID'> {
  TeamNFL: NFLTeam; // angereichertes NFL-Team
  TeamFantasy?: FantasyTeam; // optionales Fantasy-Team (wenn zugeordnet)
  SalaryDollars: number;
  SalaryDollarsDisplay: string;
}

export interface RawNFLTeam {
  ID: string;
  Name: string;
  Abv: string;
  Logo: string;
}

export interface NFLTeam extends RawNFLTeam {}

export type SortField = keyof Player; // 'ID' | 'Name' | 'Position' | 'TeamID' | 'Salary'

@Injectable({
  providedIn: 'root'
})
export class DataService {
  
  private http = inject(HttpClient);
  private salarySourceMin = 0;
  private salarySourceMax = 8000;
  private salaryTargetMin = 250_000;
  private salaryTargetMax = 50_000_000;
  private salaryMappingNonLinear = true; // true = nicht-linear, false = linear

  /* Timestamps laden */
  private timestampsUrl = 'data/Timestamps.json';
  getLeagueTimestamp(): Observable<string | undefined> {
    return this.http.get<{ League: string }>(this.timestampsUrl).pipe(
      map(ts => ts.League)
    );
  }
  getPlayersTimestamp(): Observable<string | undefined> {
    return this.http.get<{ Players: string }>(this.timestampsUrl).pipe(
      map(ts => ts.Players)
    );
  }
  getTeamsTimestamp(): Observable<string | undefined> {
    return this.http.get<{ Teams: string }>(this.timestampsUrl).pipe(
      map(ts => ts.Teams)
    );
  }
  // private toLocalTime(utcString?: string): string | undefined {
  //   if (!utcString) return undefined;
  //   const date = new Date(utcString); // UTC-Zeit aus JSON
  //   return date.toLocaleString();     // Browser-Zeit, automatisch lokalisiert
  // }
  


  getFantasyTeams(sortFields: SortField[] = ['NameLast']): Observable<FantasyTeam[]> {
    return this.getAllPlayersWithFantasyTeams(sortFields).pipe(
      map(res => res.teams)
    );
  }


  getAllPlayers(sortFields: SortField[] = ['NameLast']): Observable<Player[]> {
    return this.getAllPlayersWithFantasyTeams(sortFields).pipe(
      // Nur die Spieler extrahieren
      map(res => this.sortRoster(res.players, sortFields))
    );
  }


  /**
  * Lädt alle Spieler, verknüpft sie mit NFL-Team und optional Fantasy-Team.
  */
  getAllPlayersWithFantasyTeams(sortFields: SortField[] = ['NameLast']): Observable<{ players: Player[]; teams: FantasyTeam[] }> {
    return forkJoin({
      league: this.http.get<RawLeague>('data/League.json'),
      players: this.http.get<RawPlayer[]>('data/Players.json'),
      nflTeams: this.http.get<RawNFLTeam[]>('data/Teams.json')
    }).pipe(
      map(({ league, players, nflTeams }) => {
        // 1️⃣ FantasyTeams initial aufbauen, Roster leer lassen
        const teams: FantasyTeam[] = league.Teams.map(team => ({
          ...team,
          Team: team.Team || `Team ${team.Owner}`,
          Avatar: team.TeamAvatar || team.OwnerAvatar || 'assets/default-team-avatar.png',
          Roster: [],
          Standing: 0
        }));

        // 2️⃣ Alle Spieler bauen, ohne TeamFantasy
        const allPlayers: Player[] = players.map(raw => {
          const nfl = nflTeams.find(t => t.ID === raw.TeamID);
          const salaryDollars = this.mapSalaryToDollars(raw.Salary, raw.Year, raw.Age);          

          const player: Player = {
          ID: raw.ID,
          Name: raw.Name,
          NameFirst: raw.NameFirst,
          NameLast: raw.NameLast,
          NameShort: raw.NameShort || `${raw.NameFirst[0]}. ${raw.NameLast}`,
          Position: raw.Position,
          Salary: raw.Salary,
          TeamNFL: nfl!,
          TeamFantasy: undefined, // wird später gesetzt
          Age: raw.Age,
          Year: raw.Year,
          Picture: raw.Picture || 'assets/default-player-avatar.png',
          SalaryDollars: salaryDollars,
          SalaryDollarsDisplay: this.formatSalaryDollars(salaryDollars)
        };

        return player;
        });

        // 3️⃣ Roster der Teams füllen & Spieler TeamFantasy zuweisen
        teams.forEach(team => {
          team.Roster = this.rosterIdsToPlayers(
            (league.Teams.find(t => t.TeamID === team.TeamID)?.Roster) || [],
            allPlayers
          );
          team.Roster.forEach(player => (player.TeamFantasy = team));
        });

        // 4️⃣ Teams nach Standing sortieren
        teams.sort((a, b) => {
          if (b.Wins !== a.Wins) return b.Wins - a.Wins;
          if (b.Ties !== a.Ties) return b.Ties - a.Ties;
          if (b.Points !== a.Points) return b.Points - a.Points;
          return a.PointsAgainst - b.PointsAgainst;
        });

        teams.forEach((team, index) => (team.Standing = index + 1));

        // 5️⃣ Alle Spieler sortieren
        const playersSorted = this.sortRoster(allPlayers, sortFields);

        // Alle Spieler innerhalb eines Teams ebenfalls sortieren
        teams.forEach(team => {
          team.Roster = this.sortRoster(team.Roster, sortFields);
        });

        return { players: playersSorted, teams };
      })
    );
  }

  // Hilfsmethode im Service
  private rosterIdsToPlayers(rosterIds: string[], allPlayers: Player[]): Player[] {
    return rosterIds
      .map(pid => allPlayers.find(p => p.ID === pid))
      .filter((p): p is Player => !!p);
  }

  private mapSalaryToDollars(salary: number, year: number, age: number): number {

    // Salary holen
    const salaryFlat = this.salaryMappingNonLinear ? this.mapSalaryToDollarsNonLinear(salary) : this.mapSalaryToDollarsLinear(salary);
    let salaryAdjusted = salaryFlat;

    //Rookies kosten weniger Geld
    //1. Jahr nur 50%, 2. Jahr 70%, 3. Jahr 90%
    if (year === 1) {
      salaryAdjusted = salaryAdjusted * 0.5;
    } else if (year === 2) {
      salaryAdjusted = salaryAdjusted * 0.75;
    } else if (year === 3) {
      salaryAdjusted = salaryAdjusted * 0.9;
    }

    // auf die Salary noch pro Jahr 100k draufschlagen
    salaryAdjusted = salaryAdjusted + 100_000 * year;

    // von der Salary noch pro Alter über 25 Jahre 100k abziehen
    salaryAdjusted = salaryAdjusted - 100_000 * (age - 25);

    return salaryAdjusted;
  }

  private mapSalaryToDollarsLinear(salary: number): number {
    return this.salaryTargetMin + ((salary - this.salarySourceMin) / (this.salarySourceMax - this.salarySourceMin)) * (this.salaryTargetMax - this.salaryTargetMin);
  }

  private mapSalaryToDollarsNonLinear(salary: number): number {
    const k = 2; // Quadratische Skalierung

    const normalized = (salary - this.salarySourceMin) / (this.salarySourceMax - this.salarySourceMin);
    const scaled = Math.pow(normalized, k);

    return this.salaryTargetMin + scaled * (this.salaryTargetMax - this.salaryTargetMin);
  }

  private formatSalaryDollars(amount: number): string {
    if (amount >= 1_000_000) {
      // Millionenbereich → 1 Nachkommastelle
      return `$${(amount / 1_000_000).toFixed(1)} Mio.`;
    } else if (amount >= 1_000) {
      // Tausenderbereich → auf k mit 1 Nachkommastelle
      return `$${(amount / 1_000).toFixed(0)}k`;
    } else {
      // darunter einfach normal
      return `${amount} $`;
    }
  }



  private sortRoster(roster: Player[], sortFields: SortField[]): Player[] {
    return roster.sort((a, b) => {
      for (const field of sortFields) {
        if (field === 'Salary' || field === 'SalaryDollars') {
          const diff = (b[field] as number) - (a[field] as number);
          if (diff !== 0) return diff;
        } else {
          const cmp = String(a[field]).localeCompare(String(b[field]));
          if (cmp !== 0) return cmp;
        }
      }
      return 0;
    });
  }


}