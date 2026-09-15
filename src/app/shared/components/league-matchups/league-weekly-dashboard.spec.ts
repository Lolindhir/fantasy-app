import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../../core/models/weekly-recap.models';
import { DataService } from '../../../core/services/data.service';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { LeagueMatchupsComponent } from './league-matchups';

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
      Roster: [],
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
  const matchups = [];
  for (let index = 0; index < teamCount; index += 2) {
    matchups.push({
      FantasyMatchupID: `m-${index / 2 + 1}`,
      CompletionState: 'final' as const,
      Participants: [
        { TeamID: index + 1, Points: 120 + index, ScoreKind: 'standard' as const },
        { TeamID: index + 2, Points: 110 + index, ScoreKind: 'standard' as const }
      ],
      Result: { Type: 'win' as const, WinnerTeamID: index + 1 }
    });
  }

  return {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [{
      Week: 1,
      Stage: 'regular-season',
      FirstKickoffUtc: '2026-09-10T00:00:00Z',
      CompletionState: 'final',
      Matchups: matchups
    }],
    Summary: { LastCompletedWeek: 1, ActiveOrNextWeek: null }
  };
}

const emptyRecap: WeeklyRecapsReadModel = {
  SchemaVersion: 1,
  Season: '2026',
  Weeks: [{ Week: 1, KeyGames: [], KeyPlayers: [] }]
};

describe('LeagueMatchupsComponent #500 responsive dashboard', () => {
  let fixture: ComponentFixture<LeagueMatchupsComponent>;

  beforeEach(async () => {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
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
    dataService.getWeeklyRecaps.and.returnValue(of(emptyRecap));

    await TestBed.configureTestingModule({
      imports: [LeagueMatchupsComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
        { provide: MatDialog, useValue: jasmine.createSpyObj<MatDialog>('MatDialog', ['open']) },
        { provide: TeamDetailDialogService, useValue: jasmine.createSpyObj<TeamDetailDialogService>('TeamDetailDialogService', ['open']) }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague();
    fixture.detectChanges();
  });

  for (const width of [360, 390, 430, 1280]) {
    it(`renders the intended top-context density without horizontal overflow at ${width}px`, () => {
      const host: HTMLElement = fixture.nativeElement;
      host.style.display = 'block';
      host.style.width = `${width}px`;
      fixture.detectChanges();

      const shell = host.querySelector<HTMLElement>('.weekly-context-shell');
      expect(shell).not.toBeNull();
      expect(shell!.scrollWidth).toBeLessThanOrEqual(shell!.clientWidth + 1);
      expect(shell!.querySelectorAll('.weekly-standing-row').length).toBe(8);
      expect(shell!.querySelectorAll('.weekly-last-row').length).toBe(8);

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

  it('keeps the complete top-context halves as the only navigation targets', () => {
    const host: HTMLElement = fixture.nativeElement;
    const halves = host.querySelectorAll<HTMLAnchorElement>('.weekly-context-half');

    expect(halves.length).toBe(2);
    expect(halves[0].getAttribute('href')).toContain('/standings');
    expect(halves[1].getAttribute('href')).toBe('#week-recap');
    expect(host.querySelector('.weekly-context-row a, .weekly-context-row button')).toBeNull();
  });
});
