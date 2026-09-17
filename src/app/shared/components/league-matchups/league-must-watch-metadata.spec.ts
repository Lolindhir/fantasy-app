import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import type { NFLTeam } from '../../../core/models/player.models';
import { DataService } from '../../../core/services/data.service';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { LeagueMatchupsComponent } from './league-matchups';

function makeLeague(): League {
  return {
    Season: '2026',
    Status: 'In-Season',
    FinalScoredWeek: 1,
    Teams: Array.from({ length: 9 }, (_, index) => {
      const teamID = index + 1;
      return {
        TeamID: teamID,
        Team: `Fantasy Team ${teamID}`,
        TeamAbbr: `T${teamID}`,
        Owner: `Owner ${teamID}`,
        Avatar: `/team-${teamID}.png`,
        Roster: []
      };
    })
  } as unknown as League;
}

function makeMatchups(): MatchupsReadModel {
  return {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [{
      Week: 2,
      Stage: 'regular-season',
      FirstKickoffUtc: '2099-09-17T17:00:00Z',
      CompletionState: 'open',
      Matchups: []
    }],
    Summary: {
      LastCompletedWeek: 1,
      ActiveOrNextWeek: 2
    }
  };
}

function makeContext(): FantasyGameContextReadModel {
  const directStarterTeams = Array.from({ length: 8 }, (_, index) => {
    const teamID = index + 1;
    return {
      FantasyTeamID: teamID,
      FantasyMatchupID: `m-${Math.ceil(teamID / 2)}`,
      RosteredPlayerCount: 1,
      StarterCount: 1,
      RosteredPoints: 0,
      StarterPoints: 0,
      Players: []
    };
  });

  return {
    SchemaVersion: 5,
    LeagueID: 'league',
    Season: '2026',
    Week: 2,
    ScoringState: 'pending',
    DecisionWindows: [{
      DecisionWindowID: 'w1',
      StartsAtUtc: '2099-09-17T17:00:00Z',
      GameIDs: ['g1']
    }],
    Games: [{
      GameID: 'g1',
      DecisionWindowID: 'w1',
      StartsAtUtc: '2099-09-17T17:00:00Z',
      AwayTeamID: 'A',
      AwayTeamAbbr: 'AAA',
      HomeTeamID: 'H',
      HomeTeamAbbr: 'HHH',
      Status: null,
      Relevance: {
        RosteredPlayerCount: 9,
        StarterCount: 8,
        FantasyTeamCount: 9,
        FantasyMatchupCount: 4,
        UnknownAssociationCount: 0
      },
      Impact: {
        State: 'unavailable',
        RosteredPoints: null,
        StarterPoints: null,
        OutcomeSwingMatchupCount: 0
      },
      FantasyTeams: [
        ...directStarterTeams,
        {
          FantasyTeamID: 9,
          FantasyMatchupID: 'm-5',
          RosteredPlayerCount: 1,
          StarterCount: 0,
          RosteredPoints: 0,
          StarterPoints: 0,
          Players: []
        }
      ],
      RemainingRelevance: {
        HasRemainingRelevance: true,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 8,
        EligibleBenchCandidateCount: 1,
        DirectStarterFantasyTeamCount: 8,
        DirectStarterFantasyTeamIDs: [1, 2, 3, 4, 5, 6, 7, 8],
        FantasyMatchupCount: 4,
        TwoSidedFantasyMatchupCount: 4,
        FinalWindowFantasyMatchupCount: 4,
        CommittedFinalWindowMatchupCount: 0,
        MustWatchRank: 1
      }
    }],
    FantasyMatchups: [],
    NonGameAssociations: [],
    MustWatchGames: [{
      Rank: 1,
      GameID: 'g1',
      DecisionWindowID: 'w1',
      StartsAtUtc: '2099-09-17T17:00:00Z',
      CommittedFinalWindowMatchupCount: 0,
      LockedActiveStarterCount: 0,
      DirectStarterFantasyTeamCount: 8,
      DirectStarterFantasyTeamIDs: [1, 2, 3, 4, 5, 6, 7, 8],
      UnlockedStarterCount: 8,
      TwoSidedFantasyMatchupCount: 4,
      FantasyMatchupCount: 4,
      FinalWindowFantasyMatchupCount: 4,
      EligibleBenchCandidateCount: 1
    }]
  };
}

describe('LeagueMatchupsComponent #572 compact Must Watch metadata', () => {
  let fixture: ComponentFixture<LeagueMatchupsComponent>;
  let teamDialog: jasmine.SpyObj<TeamDetailDialogService>;
  let gameDialog: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getFantasyGameContext',
      'getDecisionWindows',
      'getMatchups',
      'getNflTeams',
      'getWeeklyRecaps'
    ]);
    dataService.getFantasyGameContext.and.returnValue(of(makeContext()));
    dataService.getDecisionWindows.and.returnValue(of(null as unknown as DecisionWindowsReadModel));
    dataService.getMatchups.and.returnValue(of(makeMatchups()));
    dataService.getNflTeams.and.returnValue(of([
      { ID: 'A', Name: 'Away', Abv: 'AAA', Logo: '/away.svg' },
      { ID: 'H', Name: 'Home', Abv: 'HHH', Logo: '/home.svg' }
    ] as NFLTeam[]));
    dataService.getWeeklyRecaps.and.returnValue(of({ SchemaVersion: 1 as const, Season: '2026', Weeks: [] }));

    teamDialog = jasmine.createSpyObj<TeamDetailDialogService>('TeamDetailDialogService', ['open']);
    gameDialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

    await TestBed.configureTestingModule({
      imports: [LeagueMatchupsComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
        { provide: TeamDetailDialogService, useValue: teamDialog },
        { provide: MatDialog, useValue: gameDialog }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague();
    fixture.detectChanges();
  });

  it('keeps unchanged counts and direct-Starter team exposure in one compact visual row', () => {
    const host: HTMLElement = fixture.nativeElement;
    const card = host.querySelector<HTMLElement>('.fantasy-pulse-card--remaining');
    const metrics = card?.querySelector<HTMLElement>('.fantasy-pulse-metrics');
    const strip = card?.querySelector<HTMLElement>('.fantasy-pulse-team-strip');
    const chips = Array.from(metrics?.querySelectorAll<HTMLElement>('.fantasy-pulse-metric-chip') ?? []);
    const avatars = Array.from(strip?.querySelectorAll<HTMLButtonElement>('.fantasy-pulse-team-avatar') ?? []);

    expect(card).not.toBeNull();
    expect(metrics).not.toBeNull();
    expect(strip).not.toBeNull();
    expect(chips.map(chip => chip.textContent?.trim())).toEqual(['8 starters', '4 matchups']);
    expect(strip!.querySelector('.fantasy-pulse-team-strip-label')?.textContent?.trim()).toBe('Starter teams');
    expect(strip!.querySelector(':scope > strong')?.textContent?.trim()).toBe('8');
    expect(avatars.length).toBe(8);
    expect(avatars.map(avatar => avatar.title)).toEqual(['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8']);
    expect(host.querySelector<HTMLButtonElement>('[title="T9"]')).toBeNull();
    expect(getComputedStyle(metrics!).flexWrap).toBe('nowrap');
    expect(getComputedStyle(strip!).position).toBe('absolute');

    const metricsRect = metrics!.getBoundingClientRect();
    const stripRect = strip!.getBoundingClientRect();
    const metricsCenter = metricsRect.top + metricsRect.height / 2;
    const stripCenter = stripRect.top + stripRect.height / 2;
    expect(Math.abs(metricsCenter - stripCenter)).toBeLessThanOrEqual(4);
  });

  it('keeps the existing Team Detail interaction separate from the NFL game-detail target', () => {
    const host: HTMLElement = fixture.nativeElement;
    const firstAvatar = host.querySelector<HTMLButtonElement>('.fantasy-pulse-team-avatar');
    const gameTarget = host.querySelector<HTMLButtonElement>('.fantasy-pulse-card-main');

    expect(firstAvatar).not.toBeNull();
    expect(gameTarget).not.toBeNull();

    firstAvatar!.click();
    expect(teamDialog.open).toHaveBeenCalledOnceWith(1);
    expect(gameDialog.open).not.toHaveBeenCalled();

    gameTarget!.click();
    expect(gameDialog.open).toHaveBeenCalledTimes(1);
    expect(teamDialog.open).toHaveBeenCalledTimes(1);
  });

  for (const width of [360, 390, 430, 1280]) {
    it(`keeps the compact Must Watch metadata contained on one row at ${width}px`, () => {
      const sourceCard = (fixture.nativeElement as HTMLElement)
        .querySelector<HTMLElement>('.fantasy-pulse-card--remaining')!;
      const frame = document.createElement('iframe');
      frame.style.position = 'absolute';
      frame.style.left = '-2000px';
      frame.style.top = '0';
      frame.style.width = `${width}px`;
      frame.style.height = '400px';
      frame.style.border = '0';
      document.body.appendChild(frame);

      try {
        const frameDocument = frame.contentDocument!;
        const frameWindow = frame.contentWindow!;
        for (const style of Array.from(document.head.querySelectorAll('style'))) {
          frameDocument.head.appendChild(style.cloneNode(true));
        }

        const reset = frameDocument.createElement('style');
        reset.textContent = 'html,body{box-sizing:border-box;width:100%;min-width:0;margin:0;overflow:hidden;}';
        frameDocument.head.appendChild(reset);
        frameDocument.body.appendChild(sourceCard.cloneNode(true));

        const card = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-card--remaining')!;
        const metrics = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-metrics')!;
        const strip = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-team-strip')!;
        const metricChips = metrics.querySelectorAll<HTMLElement>('.fantasy-pulse-metric-chip');
        const count = strip.querySelector<HTMLElement>(':scope > strong')!;
        const cardRect = card.getBoundingClientRect();
        const metricsRect = metrics.getBoundingClientRect();
        const stripRect = strip.getBoundingClientRect();
        const lastMetricRect = metricChips[metricChips.length - 1].getBoundingClientRect();
        const countRect = count.getBoundingClientRect();
        const metricsCenter = metricsRect.top + metricsRect.height / 2;
        const stripCenter = stripRect.top + stripRect.height / 2;

        expect(frameWindow.innerWidth).withContext(`${width}px iframe viewport`).toBe(width);
        expect(cardRect.right).withContext(`${width}px card containment`).toBeLessThanOrEqual(width + 1);
        expect(card.scrollWidth).withContext(`${width}px card horizontal overflow`).toBeLessThanOrEqual(card.clientWidth + 1);
        expect(getComputedStyle(metrics).flexWrap).withContext(`${width}px metadata wrapping`).toBe('nowrap');
        expect(lastMetricRect.right).withContext(`${width}px counts/avatar overlap`).toBeLessThanOrEqual(stripRect.left + 1);
        expect(stripRect.right).withContext(`${width}px strip containment`).toBeLessThanOrEqual(cardRect.right + 1);
        expect(countRect.right).withContext(`${width}px affected-team count visibility`).toBeLessThanOrEqual(stripRect.right + 1);
        expect(countRect.width).withContext(`${width}px affected-team count width`).toBeGreaterThan(0);
        expect(Math.abs(metricsCenter - stripCenter)).withContext(`${width}px shared metadata row`).toBeLessThanOrEqual(4);
        expect(cardRect.height).withContext(`${width}px compact card height`).toBeLessThanOrEqual(90);
      } finally {
        frame.remove();
      }
    });
  }
});
