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
  SalaryCap: number;
  SalaryCapFantasy: number;
  SalaryCapProjected: number;
  SalaryCapProjectedFantasy: number;
  SalaryRelevantTeamSize: number;
  Teams: RawFantasyTeam[]; // nur rohe Teams
}

export interface League extends Omit<RawLeague, 'Teams'> {
  Teams: FantasyTeam[]; // angereicherte Teams
  SalaryCapDisplay: string;
  SalaryCapProjectedDisplay: string;
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

export interface InjuryDetails {
  Date: string;
  ReturnDate: string;
  Description: string;
  Designation: string;
}

export interface RankingEntry {
  Type: 'Total' | 'PerGame' | 'Combined' | 'Total_Pos' | 'PerGame_Pos' | 'Combined_Pos';
  Value: number;
}

export interface PointHistorySeason {
  Season: number; //z.B. 2024, abgeleitet aus League.Season
  Total: number;
  AvgGame: number;
  AvgPotentialGame: number;
  GamesPlayed: number;
  PotentialGames: number;
}

export interface PointHistory {
  SeasonMinus1: PointHistorySeason;
  SeasonMinus2: PointHistorySeason;
  SeasonMinus3: PointHistorySeason;
}

export interface PlayerStats {
  GamesPlayed: number;
  GamesPotential: number;
  SnapsTotal: number;
  AttemptsTotal: number;
  TouchdownsTotal: number;
  TouchdownsPassing: number;
  TouchdownsReceiving: number;
  TouchdownsRushing: number;
  FantasyPointsTotal: number;
  FantasyPointsAvgGame: number;
  FantasyPointsAvgPotentialGame: number;
  FantasyPointsAvgSnap: number;
  FantasyPointsAvgAttempt: number;
  Ranking: RankingEntry[];
  PointHistory: PointHistory;
}

export interface RawPlayer {
  ID: string;
  Name: string;
  NameFirst: string;
  NameLast: string;
  NameShort: string;
  Position: string;
  SalaryDollars: number;
  SalaryDollarsFantasy: number;
  SalaryDollarsProjected: number;
  SalaryDollarsProjectedFantasy: number;
  Age: number;
  Year: number;
  Picture: string;
  Number: string;
  FantasyPros: string;
  ESPN: string;
  College: string;
  HighSchool: string;
  Injured: boolean;
  InjuryDetails: InjuryDetails;
  //nur für Verarbeitung benötigt
  TeamID: string; // Referenz, nicht das Teamobjekt
  GamesPlayed: number;
  GamesPotential: number;
  SnapsTotal: number;
  AttemptsTotal: number;
  FantasyPointsTotal: number;
  FantasyPointsAvgGame: number;
  FantasyPointsAvgPotentialGame: number;
  FantasyPointsAvgSnap: number;
  FantasyPointsAvgAttempt: number;
  TouchdownsTotal: number;
  TouchdownsPassing: number;
  TouchdownsReceiving: number;
  TouchdownsRushing: number;
  Ranking: RankingEntry[]
  PointHistory: PointHistory
}

export interface Player extends Omit<RawPlayer, 'TeamID' | 'GamesPlayed' | 'GamesPotential' | 'FantasyPointsTotal' | 'FantasyPointsAvgGame' | 'FantasyPointsAvgPotentialGame' | 'FantasyPointsAvgSnap' | 'FantasyPointsAvgAttempt' | 'TouchdownsTotal' | 'TouchdownsPassing' | 'TouchdownsReceiving' | 'TouchdownsRushing' | 'Ranking' | 'PointHistory'> {
  TeamNFL: NFLTeam; // angereichertes NFL-Team
  TeamFantasy?: FantasyTeam; // optionales Fantasy-Team (wenn zugeordnet)
  SalaryDollarsDisplay: string;
  SalaryDollarsProjectedDisplay: string;
  Stats: PlayerStats;
}

export interface RawNFLTeam {
  ID: string;
  Name: string;
  Abv: string;
  Logo: string;
}

export interface NFLTeam extends RawNFLTeam {}

export type SortField = keyof Player; // 'ID' | 'Name' | 'Position' | 'TeamID' | 'SalaryDollars' | ...

@Injectable({
  providedIn: 'root'
})
export class DataService {
  
  private http = inject(HttpClient);
  // private salarySourceMin = 0;
  // private salarySourceMax = 8000;
  // private salaryTargetMin = 250_000;
  // private salaryTargetMax = 50_000_000;
  // private salaryMappingNonLinear = true; // true = nicht-linear, false = linear

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
  //gib den neuesten Zeitstempel von allen drei Dateien zurück
  getLatestTimestamp(): Observable<string | undefined> {
    return forkJoin({
      league: this.getLeagueTimestamp(),
      players: this.getPlayersTimestamp(),
      teams: this.getTeamsTimestamp()
    }).pipe(
      map(({ league, players, teams }) => {
        return [league, players, teams].reduce((a, b) => {
          if (a === undefined) return b;
          if (b === undefined) return a;
          return a > b ? a : b;
        });
      })
    );
  }
  // private toLocalTime(utcString?: string): string | undefined {
  //   if (!utcString) return undefined;
  //   const date = new Date(utcString); // UTC-Zeit aus JSON
  //   return date.toLocaleString();     // Browser-Zeit, automatisch lokalisiert
  // }


  getFantasyTeams(sortFields: SortField[] = ['NameLast']): Observable<FantasyTeam[]> {
    return this.getLeagueWithPlayers(sortFields).pipe(
      map(res => res.teams)
    );
  }

  getAllPlayers(sortFields: SortField[] = ['NameLast']): Observable<Player[]> {
    return this.getLeagueWithPlayers(sortFields).pipe(
      map(res => res.players)
    );
  }

  getLeague(sortFields: SortField[] = ['NameLast']): Observable<League> {
    return this.getLeagueWithPlayers(sortFields).pipe(
      map(res => res.league)
    );
  }


  getLeagueWithPlayers(sortFields: SortField[] = ['NameLast']): Observable<{ league: League, players: Player[], teams: FantasyTeam[] }> {
    return forkJoin({
      leagueRaw: this.http.get<RawLeague>('data/League.json'),
      playersRaw: this.http.get<RawPlayer[]>('data/Players.json'),
      nflTeamsRaw: this.http.get<RawNFLTeam[]>('data/Teams.json')
    }).pipe(
      map(({ leagueRaw, playersRaw, nflTeamsRaw }) => {

        // 1️⃣ FantasyTeams initial aufbauen
        const teams: FantasyTeam[] = leagueRaw.Teams.map(team => ({
          ...team,
          Team: team.Team || `Team ${team.Owner}`,
          Avatar: team.TeamAvatar || team.OwnerAvatar || 'assets/default-team-avatar.png',
          Roster: [],
          Standing: 0
        }));

        // 2️⃣ Spieler aufbauen
        const seasonYear = Number(leagueRaw.Season); // z. B. "2025" -> 2025

        const players: Player[] = playersRaw.map(raw => {
          const nfl = nflTeamsRaw.find(t => t.ID === raw.TeamID)!;

          // PlayerStats korrekt aus Raw-Daten zusammensetzen
          const stats: PlayerStats = 
          {
            GamesPlayed: raw.GamesPlayed,
            GamesPotential: raw.GamesPotential,
            SnapsTotal: raw.SnapsTotal,
            AttemptsTotal: raw.AttemptsTotal,
            FantasyPointsTotal: raw.FantasyPointsTotal,
            FantasyPointsAvgGame: raw.FantasyPointsAvgGame,
            FantasyPointsAvgPotentialGame: raw.FantasyPointsAvgPotentialGame,
            FantasyPointsAvgSnap: raw.FantasyPointsAvgSnap,
            FantasyPointsAvgAttempt: raw.FantasyPointsAvgAttempt,
            TouchdownsTotal: raw.TouchdownsTotal,
            TouchdownsPassing: raw.TouchdownsPassing,
            TouchdownsReceiving: raw.TouchdownsReceiving,
            TouchdownsRushing: raw.TouchdownsRushing,
            Ranking: raw.Ranking,
            PointHistory: raw.PointHistory
          };

          //Injury Dates umwandeln (20251004 zu 2025-10-04)
          if (raw.InjuryDetails?.Date) {
            const rd = raw.InjuryDetails.Date;
            if (/^\d{8}$/.test(rd)) {
              const year = rd.slice(0, 4);
              const month = rd.slice(4, 6);
              const day = rd.slice(6, 8);
              raw.InjuryDetails.Date = `${year}-${month}-${day}`; // ✅ ISO-kompatibel
            }
          }
          if (raw.InjuryDetails?.ReturnDate) {
            const rd = raw.InjuryDetails.ReturnDate;
            if (/^\d{8}$/.test(rd)) {
              const year = rd.slice(0, 4);
              const month = rd.slice(4, 6);
              const day = rd.slice(6, 8);
              raw.InjuryDetails.ReturnDate = `${year}-${month}-${day}`; // ✅ ISO-kompatibel
            }
          }

          // SeasonYears in PointHistory ergänzen
          if (stats?.PointHistory) {
            const mapping = {
              SeasonMinus1: seasonYear - 1,
              SeasonMinus2: seasonYear - 2,
              SeasonMinus3: seasonYear - 3
            } as const;

            (Object.entries(stats.PointHistory) as [keyof typeof stats.PointHistory, PointHistorySeason | undefined][])
              .forEach(([key, season]) => {
                if (season) {
                  season.Season = mapping[key];
                }
              });
          }

          return {
            ...raw,
            TeamNFL: nfl,
            TeamFantasy: undefined,
            SalaryDollars: raw.SalaryDollarsFantasy,
            SalaryDollarsProjected: raw.SalaryDollarsProjectedFantasy,
            SalaryDollarsDisplay: this.formatSalaryDollars(raw.SalaryDollarsFantasy),
            SalaryDollarsProjectedDisplay: this.formatSalaryDollars(raw.SalaryDollarsProjectedFantasy),
            NameShort: raw.NameShort || `${raw.NameFirst[0]}. ${raw.NameLast}`,
            Stats: stats
          };
        });

        // 3️⃣ Roster füllen
        teams.forEach(team => {
          team.Roster = this.rosterIdsToPlayers(
            (leagueRaw.Teams.find(t => t.TeamID === team.TeamID)?.Roster) || [],
            players
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
        teams.forEach((team, idx) => (team.Standing = idx + 1));

        // 5️⃣ Spieler sortieren
        const playersSorted = this.sortRoster(players, sortFields);

        // 6️⃣ League angereichert
        const league: League = {
          ...leagueRaw,
          Teams: teams,
          SalaryCap: leagueRaw.SalaryCapFantasy,
          SalaryCapDisplay: this.formatSalaryDollars(leagueRaw.SalaryCapFantasy),
          SalaryCapProjected: leagueRaw.SalaryCapProjectedFantasy,
          SalaryCapProjectedDisplay: this.formatSalaryDollars(leagueRaw.SalaryCapProjectedFantasy)
        };

        return { league, players: playersSorted, teams };
      })
    );
  }

  // Hilfsmethode im Service
  private rosterIdsToPlayers(rosterIds: string[], allPlayers: Player[]): Player[] {
    return rosterIds
      .map(pid => allPlayers.find(p => p.ID === pid))
      .filter((p): p is Player => !!p);
  }

  // private mapSalaryToDollars(salary: number, year: number, age: number, position: string): number {

  //   // Salary holen
  //   const salaryFlat = this.salaryMappingNonLinear ? this.mapSalaryToDollarsNonLinear(salary) : this.mapSalaryToDollarsLinear(salary);
  //   let salaryAdjusted = salaryFlat;

  //   //Rookies kosten weniger Geld
  //   //1. Jahr nur 50%, 2. Jahr 70%, 3. Jahr 90%
  //   if (year === 1) {
  //     salaryAdjusted = salaryAdjusted * 0.5;
  //   } else if (year === 2) {
  //     salaryAdjusted = salaryAdjusted * 0.75;
  //   } else if (year === 3) {
  //     salaryAdjusted = salaryAdjusted * 0.9;
  //   }

  //   // auf die Salary noch pro Jahr 100k draufschlagen
  //   salaryAdjusted = salaryAdjusted + 100_000 * year;

  //   // von der Salary noch pro Alter über 25 Jahre 100k abziehen
  //   salaryAdjusted = salaryAdjusted - 100_000 * (age - 25);

  //   // Kicker Sonderbehandlung: pro Jahr 150k drauf
  //   if (position === 'K') {
  //     salaryAdjusted = salaryAdjusted + 150_000 * year;
  //   }

  //   // Hier runden auf ganze Dollar
  //   salaryAdjusted = Math.round(salaryAdjusted);

  //   return salaryAdjusted;
  // }

  // private mapSalaryToDollarsLinear(salary: number): number {
  //   return this.salaryTargetMin + ((salary - this.salarySourceMin) / (this.salarySourceMax - this.salarySourceMin)) * (this.salaryTargetMax - this.salaryTargetMin);
  // }

  // private mapSalaryToDollarsNonLinear(salary: number): number {
  //   const k = 2; // Quadratische Skalierung

  //   const normalized = (salary - this.salarySourceMin) / (this.salarySourceMax - this.salarySourceMin);
  //   const scaled = Math.pow(normalized, k);

  //   return this.salaryTargetMin + scaled * (this.salaryTargetMax - this.salaryTargetMin);
  // }

  private formatSalaryDollars(amount: number): string {
    if(amount === 0) return 'Rookie';
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
        if (field === 'SalaryDollars' || field === 'SalaryDollarsProjected' || field === 'Age' || field === 'Year') {
          const diff = (b[field] as number) - (a[field] as number);
          if (diff !== 0) return diff;
        } else {
          const cmp = String(a[field]).localeCompare(String(b[field]), 'en', { sensitivity: 'base' });
          if (cmp !== 0) return cmp;
        }
      }
      // Fallback: eindeutige ID zum stabilisieren, falls alles andere gleich
      return a.ID.localeCompare(b.ID);
    });
  }


}