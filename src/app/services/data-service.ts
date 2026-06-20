import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { formatSalaryDollars, mapRawPlayerToPlayer } from '../core/mappers/player.mapper';
import type { DraftPick, RawDraft } from '../core/models/draft.models';
import type { Award, DataTimestamps, FantasyTeam, League, RawAward, RawLeague } from '../core/models/league.models';
import type {
  Player,
  RawNFLTeam,
  RawPlayer,
  SortField,
  TopPlayersSalaryResult
} from '../core/models/player.models';
import { FreeAgentMarketService } from '../core/services/free-agent-market.service';

@Injectable({
  providedIn: 'root'
})
export class DataService {

  private http = inject(HttpClient);
  private freeAgentMarketService = inject(FreeAgentMarketService);
  private timestampsUrl = 'data/Timestamps.json';

  getLeagueTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'League'>>(this.timestampsUrl).pipe(
      map(ts => ts.League)
    );
  }

  getPlayersTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'Players'>>(this.timestampsUrl).pipe(
      map(ts => ts.Players)
    );
  }

  getTeamsTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'Teams'>>(this.timestampsUrl).pipe(
      map(ts => ts.Teams)
    );
  }

  getDraftsTimestamp(): Observable<string | undefined> {
    return this.http.get<Pick<DataTimestamps, 'Drafts'>>(this.timestampsUrl).pipe(
      map(ts => ts.Drafts)
    );
  }

  getLatestTimestamp(): Observable<string | undefined> {
    return forkJoin({
      league: this.getLeagueTimestamp(),
      players: this.getPlayersTimestamp(),
      teams: this.getTeamsTimestamp(),
      drafts: this.getDraftsTimestamp()
    }).pipe(
      map(({ league, players, teams, drafts }) => {
        return [league, players, teams, drafts].reduce<string | undefined>((a, b) => {
          if (a === undefined) return b;
          if (b === undefined) return a;
          return a > b ? a : b;
        }, undefined);
      })
    );
  }

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

  getLeagueWithPlayers(sortFields: SortField[] = ['NameLast']): Observable<{ league: League, players: Player[], teams: FantasyTeam[], drafts: RawDraft[] }> {
    return forkJoin({
      leagueRaw: this.http.get<RawLeague>('data/League.json'),
      playersRaw: this.http.get<RawPlayer[]>('data/Players.json'),
      nflTeamsRaw: this.http.get<RawNFLTeam[]>('data/Teams.json'),
      draftsRaw: this.http.get<RawDraft[]>('data/Drafts.json')
    }).pipe(
      map(({ leagueRaw, playersRaw, nflTeamsRaw, draftsRaw }) => {

        const drafts = draftsRaw ?? [];
        const draftPickByKey = new Map<string, DraftPick>();
        for (const draft of drafts) {
          for (const pick of draft.Picks ?? []) {
            draftPickByKey.set(pick.PickKey, {
              ...pick,
              Draft: draft
            });
          }
        }

        const teams: FantasyTeam[] = leagueRaw.Teams.map(team => {
          const awards = this.ensureArray(team.Placements.Current.Awards)
            .map(a => this.mapAward(a));

          const draftPickKeys = team.DraftPicks ?? [];
          const resolvedDraftPicks = draftPickKeys
            .map(key => draftPickByKey.get(key))
            .filter((pick): pick is DraftPick => !!pick);

          return {
            ...team,
            Team: team.Team || `Team ${team.Owner}`,
            Avatar: team.TeamAvatar || team.OwnerAvatar || 'assets/default-team-avatar.png',
            Roster: [],
            Reserve: [],
            Taxi: [],
            Starter: [],
            DraftPickKeys: draftPickKeys,
            DraftPicks: resolvedDraftPicks,
            Standing: team.Placements.Current.Playoffs?.Place && team.Placements.Current.Playoffs.Place > 0
              ? team.Placements.Current.Playoffs.Place
              : team.Placements.Current.Regular.Place ?? 0,
            Wins: team.Placements.Current.Regular.Wins ?? 0,
            Losses: team.Placements.Current.Regular.Losses ?? 0,
            Ties: team.Placements.Current.Regular.Ties ?? 0,
            Points: team.Placements.Current.Regular.Points ?? 0,
            PointsAgainst: team.Placements.Current.Regular.PointsAgainst ?? 0,
            Streak: team.Placements.Current.Regular.Streak ?? '',
            Record: team.Placements.Current.Regular.Record ?? '',
            Championships: team.Placements.AllTime.Playoffs.Championships ?? 0,
            RunnerUps: team.Placements.AllTime.Playoffs.RunnerUps ?? 0,
            Thirds: team.Placements.AllTime.Playoffs.Thirds ?? 0,
            RegularSeasonWins: team.Placements.AllTime.Regular.RegularSeasonWins ?? 0,
            AwardsDisplay: awards.map(a => a.Icon).join('')
          };
        });

        const players: Player[] = playersRaw.map(raw => mapRawPlayerToPlayer(raw, {
          nflTeams: nflTeamsRaw,
          seasonYear: Number(leagueRaw.Season),
          currentWeek: leagueRaw.FinalScoredWeek,
          playoffStartWeek: leagueRaw.PlayoffStartWeek,
          lastWeek: leagueRaw.LastLeagueWeek
        }));

        teams.forEach(team => {
          const rawTeam = leagueRaw.Teams.find(t => t.TeamID === team.TeamID);

          team.Roster = this.rosterIdsToPlayers(rawTeam?.Roster ?? [], players);
          team.Reserve = this.rosterIdsToPlayers(rawTeam?.Reserve ?? [], players);
          team.Taxi = this.rosterIdsToPlayers(rawTeam?.Taxi ?? [], players);
          team.Starter = this.rosterIdsToPlayers(rawTeam?.Starter ?? [], players);

          team.Roster.forEach(player => (player.TeamFantasy = team));
        });

        this.freeAgentMarketService.enrich(players, teams, leagueRaw);
        teams.sort((a, b) => a.Standing - b.Standing);
        const playersSorted = this.sortRoster(players, sortFields);

        leagueRaw.Standings.forEach(standing => {
          standing.Awards?.forEach(award => {
            award.Icon = this.unicodeToEmoji(award.IconUnicode);
          });
        });

        const league: League = {
          ...leagueRaw,
          Teams: teams,
          SalaryCap: leagueRaw.SalaryCap,
          SalaryCapDisplay: formatSalaryDollars(leagueRaw.SalaryCap),
          SalaryCapProjected: leagueRaw.SalaryCapProjected,
          SalaryCapProjectedDisplay: formatSalaryDollars(leagueRaw.SalaryCapProjected),
          IsFinished: leagueRaw.Status == 'Finished',
          SeasonAsNumber: +leagueRaw.Season
        };

        return { league, players: playersSorted, teams, drafts };
      })
    );
  }

  private rosterIdsToPlayers(rosterIds: string[], allPlayers: Player[]): Player[] {
    return rosterIds
      .map(pid => allPlayers.find(p => p.ID === pid))
      .filter((p): p is Player => !!p);
  }

  private sortRoster(roster: Player[], sortFields: SortField[]): Player[] {
    return roster.sort((a, b) => {
      for (const field of sortFields) {
        if (field === 'Salary' || field === 'SalaryProjected' || field === 'Age' || field === 'Year') {
          const diff = (b[field] as number) - (a[field] as number);
          if (diff !== 0) return diff;
        } else {
          const cmp = String(a[field]).localeCompare(String(b[field]), 'en', { sensitivity: 'base' });
          if (cmp !== 0) return cmp;
        }
      }

      return a.ID.localeCompare(b.ID);
    });
  }

  calculateTopPlayersSalary(
    roster: Player[],
    topN: number,
    salarySelector: (player: Player) => number
  ): TopPlayersSalaryResult {
    if (!roster || roster.length === 0) {
      return { cap: 0, topPlayers: [] };
    }

    const sortedRoster = [...roster]
      .sort((a, b) => salarySelector(b) - salarySelector(a));

    const actualTopN = Math.min(topN, sortedRoster.length);
    const topPlayers = sortedRoster.slice(0, actualTopN);
    const cap = topPlayers.reduce((sum, p) => sum + salarySelector(p), 0);

    return { cap, topPlayers };
  }

  getRosterAfterTrade(
    currentRoster: Player[],
    outgoing: Player[],
    incoming: Player[]
  ): Player[] {
    let newRoster = [...currentRoster];

    outgoing.forEach(p => {
      newRoster = newRoster.filter(x => x.ID !== p.ID);
    });

    incoming.forEach(p => newRoster.push(p));
    return newRoster;
  }

  private unicodeToEmoji(unicode: string): string {
    return unicode
      .split(' ')
      .map(code => String.fromCodePoint(parseInt(code, 16)))
      .join('');
  }

  private mapAward(raw: RawAward): Award {
    return {
      Name: raw.Name,
      Type: raw.Type,
      IconUnicode: raw.IconUnicode,
      StatDisplay: raw.StatDisplay,
      Icon: this.unicodeToEmoji(raw.IconUnicode)
    };
  }

  private ensureArray<T>(value: T | T[] | null | undefined): T[] {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  }
}
