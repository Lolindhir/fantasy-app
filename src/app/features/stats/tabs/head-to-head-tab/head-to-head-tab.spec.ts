import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import type { FantasyTeam } from '../../../../core/models/league.models';
import type { RawRivalryGame, RawRivalryRecord, RivalryReadModel } from '../../../../core/models/rivalry.models';
import { DataService, type LeagueWithPlayers } from '../../../../core/services/data.service';
import { TeamSeasonLookup, TeamSeasonService } from '../../../../shared/services/team-season.service';
import { RivalryLookup, TeamRivalryService } from '../../../../shared/services/team-rivalry.service';
import { TeamDetailDialogService } from '../../../../shared/services/team-detail-dialog.service';
import { HeadToHeadTabComponent } from './head-to-head-tab';

function team(id: number): FantasyTeam {
  return { TeamID: id, Team: `Team ${id}`, TeamAbbr: `T${id}`, Owner: `Owner ${id}`, Avatar: '', OwnerAvatar: '', Roster: [] } as unknown as FantasyTeam;
}

const game = (id: string, outcome: 'win' | 'loss'): RawRivalryGame => ({
  Season: '2025', Week: 1, FantasyMatchupID: id, Stage: 'regular-season', Bracket: null, Outcome: outcome,
  TeamPoints: 100, OpponentPoints: 90, Margin: 10
});

const record = (teamId: number, opponentId: number, filter: RawRivalryRecord['Filter'], wins: number, losses: number): RawRivalryRecord => ({
  TeamID: teamId, OpponentID: opponentId, Filter: filter, Wins: wins, Losses: losses, Ties: 0, PointsFor: 1, PointsAgainst: 1,
  BiggestWinMatchupID: null, ClosestLossMatchupID: null, Games: [game(`${teamId}-${opponentId}-${filter}`, 'win')]
});

const model: RivalryReadModel = {
  SchemaVersion: 1, Product: 'league-rivalry', CanonicalLeagueID: 'test',
  Seasons: [{ Season: '2024' }, { Season: '2025' }],
  Records: [
    record(1, 2, 'all', 3, 1), record(2, 1, 'all', 1, 3),
    record(1, 2, 'playoffs', 0, 1)
  ],
  SeasonRecords: [
    { Season: '2024', TeamID: 1, OpponentID: 2, Filter: 'all', Wins: 2, Losses: 0, Ties: 0, PointsFor: 1, PointsAgainst: 1 },
    { Season: '2024', TeamID: 2, OpponentID: 1, Filter: 'all', Wins: 0, Losses: 2, Ties: 0, PointsFor: 1, PointsAgainst: 1 },
    { Season: '2025', TeamID: 1, OpponentID: 2, Filter: 'all', Wins: 1, Losses: 1, Ties: 0, PointsFor: 1, PointsAgainst: 1 },
    { Season: '2025', TeamID: 2, OpponentID: 1, Filter: 'all', Wins: 1, Losses: 1, Ties: 0, PointsFor: 1, PointsAgainst: 1 }
  ]
};

const teamSeasons = new TeamSeasonLookup({
  SchemaVersion: 1, Product: 'league-teams', CanonicalLeagueID: 'test', CurrentSeason: '2025',
  Seasons: [{ Season: '2024', Teams: [1, 2].map(id => ({
    TeamID: id, CanonicalLeagueRosterID: '', CanonicalLeagueMemberID: '', OwnerID: '', Owner: `Old Owner ${id}`, OwnerAvatar: null,
    TeamName: `Old Team ${id}`, TeamNameSource: 'provider' as const, TeamAbbr: `O${id}`, TeamAvatar: null
  })) }]
});

describe('HeadToHeadTabComponent', () => {
  function create(m: RivalryReadModel = model, query: Record<string, string> = {}): { fixture: ComponentFixture<HeadToHeadTabComponent>; root: HTMLElement; open: jasmine.Spy } {
    const dataService = jasmine.createSpyObj<DataService>('DataService', ['getLeagueWithPlayers']);
    dataService.getLeagueWithPlayers.and.returnValue(of({ league: { Season: '2025' }, teams: [team(1), team(2)] } as unknown as LeagueWithPlayers));
    const open = jasmine.createSpy('open');
    TestBed.configureTestingModule({
      imports: [HeadToHeadTabComponent],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
        { provide: TeamSeasonService, useValue: { getLookup: () => of(teamSeasons) } },
        { provide: DataService, useValue: dataService },
        { provide: TeamRivalryService, useValue: { getLookup: () => of(new RivalryLookup(m)) } },
        { provide: TeamDetailDialogService, useValue: { open } }
      ]
    });
    const fixture = TestBed.createComponent(HeadToHeadTabComponent);
    fixture.detectChanges();
    return { fixture, root: fixture.nativeElement as HTMLElement, open };
  }

  const records = (root: HTMLElement) => Array.from(root.querySelectorAll('.h2h-record')).map(node => node.textContent?.trim());

  it('shows the generated record per team pair and leaves the diagonal empty', () => {
    const { root } = create();
    expect(root.querySelectorAll('.h2h-self').length).toBe(2);
    expect(records(root)).toEqual(['3-1', '1-3']);
  });

  it('switches the filter to the generated playoff records', () => {
    const { fixture, root } = create();
    (Array.from(root.querySelectorAll('.stats-chip')).find(node => node.textContent?.trim() === 'Playoffs') as HTMLElement).click();
    fixture.detectChanges();
    expect(records(root)).toEqual(['0-1', '–']);
  });

  it('opens the rivals tab of the row team', () => {
    const { root, open } = create();
    (root.querySelector('.h2h-record') as HTMLElement).click();
    expect(open).toHaveBeenCalledOnceWith(1, { initialTab: 'rivals' });
  });

  it('offers All-Time as default plus every season of the generated season records', () => {
    const { root } = create();
    const options = Array.from(root.querySelectorAll('select option')).map(node => node.textContent?.trim());
    expect(options).toEqual(['All-Time', '2025', '2024']);
    expect((root.querySelector('select') as HTMLSelectElement).value).toBe('all-time');
  });

  it('shows the generated season record and the identity of that season', () => {
    const { fixture, root } = create();
    const select = root.querySelector('select') as HTMLSelectElement;
    select.value = '2024';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(records(root)).toEqual(['2-0', '0-2']);
    expect(root.textContent).toContain('O1');
  });

  it('opens the season from the season query parameter', () => {
    expect(records(create(model, { season: '2025' }).root)).toEqual(['1-1', '1-1']);
  });

  it('ignores an unknown season query parameter', () => {
    expect(records(create(model, { season: '1999' }).root)).toEqual(['3-1', '1-3']);
  });

  it('hides the season selector for a product without season records', () => {
    const { root } = create({ ...model, SeasonRecords: undefined });
    expect(root.querySelector('select')).toBeNull();
  });
});
