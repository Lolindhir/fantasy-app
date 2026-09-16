import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import type { Player } from '../../../core/models/player.models';
import type { WeeklyRecapsReadModel } from '../../../core/models/weekly-recap.models';
import { DataService } from '../../../core/services/data.service';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';
import { LeagueMatchupsComponent } from './league-matchups';

function makePlayer(teamID: number): Player {
  return {
    ID: `player-${teamID}`,
    Name: `Player ${teamID}`,
    NameShort: `P${teamID}`,
    Position: 'WR',
    Picture: `/player-${teamID}.png`,
    TeamNFL: {
      ID: `NFL-${teamID}`,
      Name: `NFL Team ${teamID}`,
      Abv: `N${teamID}`,
      Logo: `/nfl-${teamID}.svg`
    }
  } as unknown as Player;
}

function makeLeague(teamCount = 8): League {
  const teams = Array.from({ length: teamCount }, (_, index) => {
    const place = index + 1;
    const regular = {
      Place: place,
      PlaceOrdinal: `${place}.`,
      Wins: 1,
      Losses: 0,
      Ties: 0,
      Points: 100 + place,
      PointsAgainst: 90,
      WinPercentage: 1,
      WinPercentageDisplay: '1.000',
      Record: '1-0',
      Streak: 'W1'
    };

    return {
      TeamID: place,
      Team: `Long Fantasy Team ${place}`,
      TeamAbbr: `T${place}`,
      Owner: `Owner ${place}`,
      Avatar: '',
      Roster: [makePlayer(place)],
      Placements: {
        Current: { Regular: regular, Awards: [] },
        Previous: { Regular: regular, Playoffs: { Place: place, PlaceOrdinal: `${place}.` }, Awards: [] },
        AllTime: {
          Regular: { ...regular, RegularSeasonWins: place },
          Playoffs: {
            Place: place,
            PlaceOrdinal: `${place}.`,
            Championships: 0,
            RunnerUps: 0,
            Thirds: 0,
            PlaceCumulative: place,
            PlaceAverage: place,
            Placements: [place]
          }
        }
      }
    };
  });

  return {
    Season: '2026',
    Status: 'In-Season',
    FinalScoredWeek: 1,
    Teams: teams,
    Standings: [{
      Season: '2026',
      Playoffs: null,
      RegularSeason: teams.map(team => ({
        TeamID: team.TeamID,
        Place: team.TeamID,
        PlaceOrdinal: `${team.TeamID}.`,
        Owner: team.Owner,
        TeamName: team.Team
      }))
    }]
  } as unknown as League;
}

function makeMatchups(teamCount = 8): MatchupsReadModel {
  const completedMatchups = [];
  const currentMatchups = [];
  for (let index = 0; index < teamCount; index += 2) {
    completedMatchups.push({
      FantasyMatchupID: `m-${index / 2 + 1}`,
      CompletionState: 'final' as const,
      Participants: [
        { TeamID: index + 1, Points: 120 + index, ScoreKind: 'standard' as const },
        { TeamID: index + 2, Points: 110 + index, ScoreKind: 'standard' as const }
      ],
      Result: { Type: 'win' as const, WinnerTeamID: index + 1 }
    });
    currentMatchups.push({
      FantasyMatchupID: `next-${index / 2 + 1}`,
      CompletionState: 'open' as const,
      Participants: [
        { TeamID: index + 1, Points: null, ScoreKind: 'standard' as const },
        { TeamID: index + 2, Points: null, ScoreKind: 'standard' as const }
      ],
      Result: null
    });
  }

  return {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [
      {
        Week: 1,
        Stage: 'regular-season',
        FirstKickoffUtc: '2026-09-10T00:00:00Z',
        CompletionState: 'final',
        Matchups: completedMatchups
      },
      {
        Week: 2,
        Stage: 'regular-season',
        FirstKickoffUtc: '2099-09-17T00:00:00Z',
        CompletionState: 'open',
        Matchups: currentMatchups
      }
    ],
    Summary: { LastCompletedWeek: 1, ActiveOrNextWeek: 2 }
  };
}

const recap: WeeklyRecapsReadModel = {
  SchemaVersion: 1,
  Season: '2026',
  Weeks: [{
    Week: 1,
    KeyGames: [],
    KeyPlayers: [
      { PlayerID: 'player-2', FantasyTeamID: 2, NFLTeamID: 'NFL-2', Position: 'WR', Points: 15 },
      { PlayerID: 'player-1', FantasyTeamID: 1, NFLTeamID: 'NFL-1', Position: 'WR', Points: 30 },
      { PlayerID: 'player-3', FantasyTeamID: 3, NFLTeamID: 'NFL-3', Position: 'WR', Points: 10 }
    ]
  }]
};

describe('LeagueMatchupsComponent #558 weekly overview polish', () => {
  let fixture: ComponentFixture<LeagueMatchupsComponent>;
  let dataService: jasmine.SpyObj<DataService>;
  let dialog: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getFantasyGameContext',
      'getDecisionWindows',
      'getMatchups',
      'getNflTeams',
      'getWeeklyRecaps'
    ]);
    dataService.getFantasyGameContext.and.returnValue(of(null as unknown as FantasyGameContextReadModel));
    dataService.getDecisionWindows.and.returnValue(of(null as unknown as DecisionWindowsReadModel));
    dataService.getMatchups.and.returnValue(of(makeMatchups()));
    dataService.getNflTeams.and.returnValue(of([]));
    dataService.getWeeklyRecaps.and.returnValue(of(recap));
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

    await TestBed.configureTestingModule({
      imports: [LeagueMatchupsComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
        { provide: MatDialog, useValue: dialog },
        { provide: TeamDetailDialogService, useValue: jasmine.createSpyObj<TeamDetailDialogService>('TeamDetailDialogService', ['open']) }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague();
    fixture.detectChanges();
  });

  for (const width of [360, 390, 430, 1280]) {
    it(`keeps standings, mini-matchups and recap rows contained at ${width}px`, () => {
      const host: HTMLElement = fixture.nativeElement;
      host.style.display = 'block';
      host.style.containerType = 'inline-size';
      host.style.width = `${width}px`;
      fixture.detectChanges();

      const shell = host.querySelector<HTMLElement>('.weekly-context-shell');
      expect(shell).not.toBeNull();
      expect(shell!.scrollWidth).toBeLessThanOrEqual(shell!.clientWidth + 1);
      expect(shell!.querySelectorAll('.weekly-standing-row').length).toBe(8);
      expect(shell!.querySelectorAll('.weekly-standing-record').length).toBe(8);
      expect(Array.from(shell!.querySelectorAll('.weekly-standing-record')).every(row => row.textContent?.trim() === '1-0')).toBeTrue();
      expect(shell!.querySelectorAll('.weekly-last-matchup').length).toBe(4);
      expect(shell!.querySelectorAll('.weekly-last-side').length).toBe(8);
      expect(shell!.querySelector('.weekly-last-row')).toBeNull();

      const standingRows = shell!.querySelector<HTMLElement>('.weekly-context-half--standings .weekly-context-rows');
      const lastRows = shell!.querySelector<HTMLElement>('.weekly-last-matchups');
      expect(lastRows!.scrollHeight).toBeLessThanOrEqual(standingRows!.scrollHeight + 1);

      for (const matchup of Array.from(shell!.querySelectorAll<HTMLElement>('.weekly-last-matchup'))) {
        expect(matchup.querySelectorAll('.weekly-last-side').length).toBe(2);
        expect(matchup.scrollWidth).toBeLessThanOrEqual(matchup.clientWidth + 1);
      }

      for (const playerRow of Array.from(host.querySelectorAll<HTMLElement>('.weekly-recap-player'))) {
        expect(playerRow.scrollWidth).toBeLessThanOrEqual(playerRow.clientWidth + 1);
      }

      const columns = getComputedStyle(shell!).gridTemplateColumns
        .split(' ')
        .map(value => Number.parseFloat(value))
        .filter(Number.isFinite);
      expect(columns.length).toBe(2);

      const rightShare = columns[1] / (columns[0] + columns[1]);
      if (width === 360) {
        expect(rightShare).toBeGreaterThan(0.51);
        expect(rightShare).toBeLessThan(0.55);
      } else {
        expect(rightShare).toBeGreaterThan(0.49);
        expect(rightShare).toBeLessThan(0.51);
      }
    });
  }

  it('keeps dynamic league size for standings and completed mini-matchups', () => {
    dataService.getMatchups.and.returnValue(of(makeMatchups(10)));
    fixture.destroy();
    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague(10);
    fixture.detectChanges();

    const host: HTMLElement = fixture.nativeElement;
    expect(host.querySelectorAll('.weekly-standing-row').length).toBe(10);
    expect(host.querySelectorAll('.weekly-standing-record').length).toBe(10);
    expect(host.querySelectorAll('.weekly-last-matchup').length).toBe(5);
    expect(host.querySelectorAll('.weekly-last-side').length).toBe(10);
  });

  it('renders each Last Week result as one explicit two-sided matchup with the correct team-score association', () => {
    const host: HTMLElement = fixture.nativeElement;
    const matchups = host.querySelectorAll<HTMLElement>('.weekly-last-matchup');
    expect(matchups.length).toBe(4);

    const firstSides = matchups[0].querySelectorAll<HTMLElement>('.weekly-last-side');
    expect(firstSides.length).toBe(2);
    expect(firstSides[0].textContent).toContain('T1');
    expect(firstSides[0].textContent).toContain('120');
    expect(firstSides[1].textContent).toContain('T2');
    expect(firstSides[1].textContent).toContain('110');
    expect(matchups[0].textContent).not.toContain('WIN');
    expect(matchups[0].textContent).not.toContain('LOSS');
    expect(matchups[0].textContent).not.toContain('VS');
  });

  it('keeps the complete top-context halves as the only navigation targets', () => {
    const host: HTMLElement = fixture.nativeElement;
    const halves = host.querySelectorAll<HTMLAnchorElement>('.weekly-context-half');

    expect(halves.length).toBe(2);
    expect(halves[0].getAttribute('href')).toContain('/standings');
    expect(halves[1].getAttribute('href')).toBe('#week-recap');
    expect(host.querySelector('.weekly-context-half .weekly-context-row a, .weekly-context-half .weekly-context-row button')).toBeNull();
    expect(host.querySelector('.weekly-last-matchup a, .weekly-last-matchup button')).toBeNull();
  });

  it('uses integrated NFL-team identity for recap players and preserves WeeklyRecaps order', () => {
    const host: HTMLElement = fixture.nativeElement;
    const rows = Array.from(host.querySelectorAll<HTMLButtonElement>('.weekly-recap-player'));

    expect(rows.length).toBe(3);
    expect(rows.map(row => row.querySelector('.weekly-recap-player-copy strong')?.textContent?.trim())).toEqual(['P2', 'P1', 'P3']);
    expect(rows.map(row => row.querySelector('.weekly-recap-player-points')?.textContent?.trim())).toEqual(['15', '30', '10']);
    expect(rows[0].querySelector<HTMLImageElement>('.weekly-recap-player-nfl-logo')?.getAttribute('src')).toContain('/nfl-2.svg');
    expect(rows[1].querySelector<HTMLImageElement>('.weekly-recap-player-nfl-logo')?.getAttribute('src')).toContain('/nfl-1.svg');
    expect(rows[2].querySelector<HTMLImageElement>('.weekly-recap-player-nfl-logo')?.getAttribute('src')).toContain('/nfl-3.svg');
  });

  it('opens the established Player Detail dialog from the whole recap player row', () => {
    const host: HTMLElement = fixture.nativeElement;
    const row = host.querySelector<HTMLButtonElement>('.weekly-recap-player');
    const expectedPlayer = fixture.componentInstance.league.Teams[1].Roster[0];

    expect(row).not.toBeNull();
    expect(row!.disabled).toBeFalse();
    expect(row!.getAttribute('aria-label')).toBe('Open P2 player details');
    row!.click();

    expect(dialog.open).toHaveBeenCalledWith(
      PlayerDetailDialogComponent,
      jasmine.objectContaining({
        data: expectedPlayer,
        width: '800px',
        maxHeight: '90vh',
        panelClass: 'player-dialog'
      })
    );
  });

  it('simplifies redundant Weekly Overview headers without removing meaningful two-level headings globally', () => {
    const host: HTMLElement = fixture.nativeElement;
    const matchupHeading = host.querySelector('.matchups-heading h2')?.textContent?.trim();
    const recapHeading = host.querySelector('.weekly-recap-heading h2')?.textContent?.trim();

    expect(matchupHeading).toBe('Week 2 Matchups');
    expect(recapHeading).toBe('Week 1 Recap');
    expect(host.textContent).not.toContain('Current fantasy matchups');
    expect(host.textContent).not.toContain('Last completed fantasy week');
    expect(host.querySelector('.weekly-recap-density')).toBeNull();
  });
});
