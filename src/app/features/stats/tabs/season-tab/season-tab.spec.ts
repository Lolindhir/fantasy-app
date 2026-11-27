import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { firstValueFrom, of } from 'rxjs';

import type { LeagueSummary } from '../../../../core/models/league.models';
import type { SeasonStatisticsReadModel, SeasonStatisticsTeam } from '../../../../core/models/season-statistics.models';
import { DataService } from '../../../../core/services/data.service';
import { TeamSeasonService } from '../../../../shared/services/team-season.service';
import { SeasonTabComponent } from './season-tab';

describe('SeasonTabComponent summary loading', () => {
  it('uses the league summary and independent statistics, with season-specific identity fallback', async () => {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getLeagueSummary', 'getLeagueWithPlayers', 'getInjuryImpact', 'getNflTeams', 'getAllSeasonStatistics'
    ]);
    const standings = (season: string, name: string) => ({
      Season: season,
      RegularSeason: [{ TeamID: 1, Place: 1, Owner: 'Owner', TeamName: name, Wins: 2, Losses: 1, Ties: 0 }],
      Playoffs: [], Awards: []
    });
    dataService.getLeagueSummary.and.returnValue(of({
      Season: '2026',
      Teams: [{ TeamID: 1, Team: 'Current team', TeamAbbr: 'CUR', Avatar: 'current.png' }],
      Standings: [standings('2026', 'Current team'), standings('2025', 'Historical team')]
    } as unknown as LeagueSummary));

    const statistics = (season: number, abbreviation?: string): SeasonStatisticsReadModel => ({
      Season: season, IsCompleted: season === 2025, BiggestUpset: null,
      Teams: [{
        TeamID: 1, Owner: 'Owner', TeamName: 'Published team',
        Games: 3, Wins: 2, Losses: 1, Ties: 0, ExpectedWins: 1.5, Luck: 0.5,
        AllPlay: { Wins: 2, Losses: 1, Ties: 0 }, OpponentTiming: null,
        UnderdogWins: 0, UpsetLosses: 0, TeamAbbr: abbreviation
      } satisfies SeasonStatisticsTeam]
    });
    dataService.getAllSeasonStatistics.and.returnValue(of({
      current: statistics(2026), bySeason: new Map([['2025', statistics(2025, 'OLD')]])
    }));
    dataService.getInjuryImpact.and.returnValue(of(null));
    dataService.getNflTeams.and.returnValue(of([{ ID: 'NYG', Abv: 'NYG', Name: 'Giants', Logo: 'nyg.png' }]));
    TestBed.configureTestingModule({
      imports: [SeasonTabComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
        { provide: TeamSeasonService, useValue: { getLookup: () => of(null) } }
      ]
    });
    const fixture = TestBed.createComponent(SeasonTabComponent);
    const vm = await firstValueFrom(fixture.componentInstance.vm$);

    expect(dataService.getLeagueSummary).toHaveBeenCalledTimes(1);
    expect(dataService.getLeagueWithPlayers).not.toHaveBeenCalled();
    expect(dataService.getNflTeams).toHaveBeenCalledTimes(1);
    expect(dataService.getAllSeasonStatistics).toHaveBeenCalledTimes(1);
    expect(dataService.getInjuryImpact).toHaveBeenCalledTimes(1);
    expect(vm.defaultSeason).toBe('2026');
    expect(vm.rows('2026')[0].identity.TeamAbbr).toBe('CUR');
    expect(vm.rows('2025')[0].identity.Team).toBe('Historical team');
    expect(vm.rows('2025')[0].identity.TeamAbbr).toBe('OLD');
    expect(vm.rows('2025')[0].stats?.ExpectedWins).toBe(1.5);
    expect(vm.rows('2025')[0].injury).toBeNull();
    expect(vm.nflLogos.get('NYG')).toBe('nyg.png');
  });
});
