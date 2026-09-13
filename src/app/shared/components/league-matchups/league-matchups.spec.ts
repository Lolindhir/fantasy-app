import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';

import type { DecisionWindowsReadModel, FantasyRelevanceTeamState } from '../../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import type { NFLTeam } from '../../../core/models/player.models';
import { DataService } from '../../../core/services/data.service';
import { TeamDetailDialogService } from '../../services/team-detail-dialog.service';
import { LeagueMatchupsComponent } from './league-matchups';

describe('LeagueMatchupsComponent scoring overview', () => {
  let fixture: ComponentFixture<LeagueMatchupsComponent>;
  let component: LeagueMatchupsComponent;

  const relevanceTeam = (id: number): FantasyRelevanceTeamState => ({
    FantasyTeamID: id,
    ActiveRosterPlayerCount: 1,
    StarterCount: 1,
    BenchCount: 0,
    IRCount: 0,
    TaxiCount: 0,
    UnlockedStarterCount: 1,
    LockedActiveStarterCount: 0,
    CompletedStarterCount: 0,
    EligibleBenchCandidateCount: 0,
    HasRemainingScoringPath: true,
    Slots: [{
      SlotID: 'QB-1',
      SlotType: 'QB',
      SlotOrdinal: 1,
      SlotIndex: 0,
      CurrentStarterID: `p${id}`,
      State: 'unlocked',
      GameID: 'g1',
      DecisionWindowID: 'w1',
      StartsAtUtc: '2026-09-13T17:00:00Z',
      Repairability: null
    }],
    Players: []
  });

  const context: FantasyGameContextReadModel = {
    SchemaVersion: 4,
    LeagueID: 'league',
    Season: '2026',
    Week: 1,
    ScoringState: 'partial',
    DecisionWindows: [{ DecisionWindowID: 'w1', StartsAtUtc: '2026-09-13T17:00:00Z', GameIDs: ['g1'] }],
    Games: [{
      GameID: 'g1',
      DecisionWindowID: 'w1',
      StartsAtUtc: '2026-09-13T17:00:00Z',
      AwayTeamID: 'A',
      AwayTeamAbbr: 'AAA',
      HomeTeamID: 'H',
      HomeTeamAbbr: 'HHH',
      Status: null,
      Relevance: { RosteredPlayerCount: 2, StarterCount: 2, FantasyTeamCount: 2, FantasyMatchupCount: 1, UnknownAssociationCount: 0 },
      Impact: { State: 'unavailable', RosteredPoints: null, StarterPoints: null, OutcomeSwingMatchupCount: 0 },
      FantasyTeams: [],
      RemainingRelevance: {
        HasRemainingRelevance: true,
        LockedActiveStarterCount: 0,
        UnlockedStarterCount: 2,
        EligibleBenchCandidateCount: 0,
        FantasyMatchupCount: 1,
        TwoSidedFantasyMatchupCount: 1,
        FinalWindowFantasyMatchupCount: 1,
        CommittedFinalWindowMatchupCount: 0
      }
    }],
    FantasyMatchups: [{
      FantasyMatchupID: 'm1',
      TeamIDs: [1, 2],
      FinalScores: null,
      CounterfactualState: 'unavailable-not-final',
      Games: [{
        GameID: 'g1', DecisionWindowID: 'w1', StartsAtUtc: '2026-09-13T17:00:00Z',
        LeftStarterCount: 1, RightStarterCount: 1, LeftRosteredPlayerCount: 1, RightRosteredPlayerCount: 1,
        LeftStarterPoints: 0, RightStarterPoints: 0, StarterPointDelta: 0,
        OutcomeChangedWithoutGame: null, ScoreWithoutGame: null
      }],
      RemainingRelevance: {
        State: 'both-sides', HasRemainingScoringPaths: true,
        LeftRemainingPathCount: 1, RightRemainingPathCount: 1,
        LockedActiveStarterCount: 0, UnlockedStarterCount: 2, EligibleBenchCandidateCount: 0,
        NextScoringWindowID: 'w1', NextScoringGameIDs: ['g1'], NextScoringPrimaryGameID: 'g1',
        NextScoringWindowGameCount: 1, NextScoringLockedActiveStarterCount: 0,
        NextScoringUnlockedStarterCount: 2, NextScoringOptionCount: 0,
        FinalScoringWindowID: 'w1', FinalScoringGameIDs: ['g1'], IsFinalScoringWindowCommitted: false
      }
    }],
    NonGameAssociations: []
  };

  const decisionWindows = {
    SchemaVersion: 3,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 1,
    LastLineupWeek: 18,
    DecisionWindows: [],
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: [],
    FantasyRelevance: {
      Version: 2,
      SlotDefinitions: [{ SlotID: 'QB-1', SlotType: 'QB', SlotOrdinal: 1, SlotIndex: 0 }],
      Teams: [relevanceTeam(1), relevanceTeam(2)]
    }
  } satisfies DecisionWindowsReadModel;

  const matchups: MatchupsReadModel = {
    SchemaVersion: 1,
    Season: '2026',
    Weeks: [{
      Week: 1,
      Stage: 'regular-season',
      FirstKickoffUtc: '2026-09-13T17:00:00Z',
      CompletionState: 'open',
      Matchups: [{
        FantasyMatchupID: 'm1',
        CompletionState: 'open',
        Participants: [
          { TeamID: 1, Points: 37.4, ScoreKind: 'standard' },
          { TeamID: 2, Points: 13.8, ScoreKind: 'standard' }
        ],
        Result: null
      }]
    }],
    Summary: {
      LastCompletedWeek: null,
      ActiveOrNextWeek: 1
    }
  };

  const league = {
    Season: '2026',
    FinalScoredWeek: 1,
    Teams: [
      { TeamID: 1, Team: 'Left Team', TeamAbbr: 'LFT', Owner: 'Left Owner', Avatar: null },
      { TeamID: 2, Team: 'Right Team', TeamAbbr: 'RGT', Owner: 'Right Owner', Avatar: null }
    ]
  } as unknown as League;

  beforeEach(async () => {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getFantasyGameContext', 'getDecisionWindows', 'getMatchups', 'getNflTeams'
    ]);
    dataService.getFantasyGameContext.and.returnValue(of(context));
    dataService.getDecisionWindows.and.returnValue(of(decisionWindows));
    dataService.getMatchups.and.returnValue(of(matchups));
    dataService.getNflTeams.and.returnValue(of([
      { ID: 'A', Name: 'Away', Abv: 'AAA', Logo: 'away-logo' },
      { ID: 'H', Name: 'Home', Abv: 'HHH', Logo: 'home-logo' }
    ] as NFLTeam[]));

    await TestBed.configureTestingModule({
      imports: [LeagueMatchupsComponent],
      providers: [
        { provide: DataService, useValue: dataService },
        { provide: MatDialog, useValue: jasmine.createSpyObj<MatDialog>('MatDialog', ['open']) },
        { provide: TeamDetailDialogService, useValue: jasmine.createSpyObj<TeamDetailDialogService>('TeamDetailDialogService', ['open']) }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    component = fixture.componentInstance;
    component.league = league;
    fixture.detectChanges();
  });

  it('uses one coherent matchup target and keeps scoring-window previews non-interactive', () => {
    const matchupSpy = spyOn(component, 'openMatchupDetail').and.stub();
    const gameSpy = spyOn(component, 'openGameDetail').and.stub();
    fixture.detectChanges();

    const element: HTMLElement = fixture.nativeElement;
    const matchupTarget = element.querySelector<HTMLElement>('.matchup-card');
    const footer = element.querySelector<HTMLElement>('.matchup-window');
    const gamePreview = element.querySelector<HTMLElement>('.matchup-window-game');

    expect(matchupTarget).not.toBeNull();
    expect(matchupTarget!.getAttribute('role')).toBe('button');
    expect(matchupTarget!.tabIndex).toBe(0);
    expect(footer).not.toBeNull();
    expect(gamePreview).not.toBeNull();
    expect(gamePreview!.tagName).toBe('SPAN');
    expect(element.querySelector('.matchup-window button')).toBeNull();

    footer!.click();
    expect(matchupSpy).toHaveBeenCalledTimes(1);
    expect(gameSpy).not.toHaveBeenCalled();

    matchupTarget!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    expect(matchupSpy).toHaveBeenCalledTimes(2);
    expect(gameSpy).not.toHaveBeenCalled();
  });

  it('renders non-zero scores in one neutral shared score plate without inferring Final', () => {
    const element: HTMLElement = fixture.nativeElement;
    const plate = element.querySelector<HTMLElement>('.matchup-score-plate');

    expect(plate).not.toBeNull();
    expect(plate!.getAttribute('data-scoreboard-state')).toBe('neutral');
    expect(plate!.classList).toContain('matchup-score-plate--neutral');
    expect(plate!.querySelector('.matchup-score-value--left')?.textContent?.trim()).toBe('37.4');
    expect(plate!.querySelector('.matchup-vs')?.textContent?.trim()).toBe('VS');
    expect(plate!.querySelector('.matchup-score-value--right')?.textContent?.trim()).toBe('13.8');
    expect(element.querySelectorAll('.matchup-score-plate').length).toBe(1);
    expect(element.querySelectorAll('.matchup-scoreboard > .matchup-score-value').length).toBe(0);
  });

  it('renders dominant current scores, starter strips and one compact window-level summary', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.matchup-score-value--left')?.textContent?.trim()).toBe('37.4');
    expect(element.querySelector('.matchup-score-value--right')?.textContent?.trim()).toBe('13.8');
    expect(element.querySelectorAll('.matchup-progress-segment').length).toBe(2);
    expect(element.querySelectorAll('.matchup-window-time').length).toBe(1);
    expect(element.querySelector('.matchup-window-count')?.textContent?.trim()).toBe('1 NFL game');
    expect(element.querySelectorAll('.matchup-window-game').length).toBe(1);
    expect(element.querySelector('.matchup-window-overflow')).toBeNull();
  });

  it('preserves missing score versus reliable zero semantics', () => {
    expect(component.formatFantasyPoints(null)).toBe('–');
    expect(component.formatFantasyPoints(0)).toBe('0');
  });

  it('keeps long score values collision-free and the score plate within identity-row height at responsive widths', () => {
    const element: HTMLElement = fixture.nativeElement;
    const scoreboard = element.querySelector<HTMLElement>('.matchup-scoreboard')!;
    const plate = element.querySelector<HTMLElement>('.matchup-score-plate')!;
    const leftScore = plate.querySelector<HTMLElement>('.matchup-score-value--left')!;
    const rightScore = plate.querySelector<HTMLElement>('.matchup-score-value--right')!;
    const originalWidth = window.innerWidth;
    const originalHeight = window.innerHeight;

    leftScore.textContent = '123.45';
    rightScore.textContent = '987.65';

    try {
      for (const width of [360, 390, 430, 1280]) {
        window.resizeTo(width, 900);
        window.dispatchEvent(new Event('resize'));
        fixture.detectChanges();

        const leftTeam = element.querySelector<HTMLElement>('.matchup-team--left')!.getBoundingClientRect();
        const rightTeam = element.querySelector<HTMLElement>('.matchup-team--right')!.getBoundingClientRect();
        const plateRect = plate.getBoundingClientRect();
        const visibleIdentity = Array.from(element.querySelectorAll<HTMLElement>('.matchup-team-identity'))
          .find(identity => getComputedStyle(identity).display !== 'none')!;

        expect(window.innerWidth).withContext(`${width}px viewport`).toBe(width);
        expect(scoreboard.scrollWidth).withContext(`${width}px scoreboard overflow`)
          .toBeLessThanOrEqual(scoreboard.clientWidth + 1);
        expect(plateRect.left).withContext(`${width}px left identity collision`)
          .toBeGreaterThanOrEqual(leftTeam.right - 1);
        expect(plateRect.right).withContext(`${width}px right identity collision`)
          .toBeLessThanOrEqual(rightTeam.left + 1);
        expect(plateRect.height).withContext(`${width}px score plate height`)
          .toBeLessThanOrEqual(visibleIdentity.getBoundingClientRect().height + 1);
      }
    } finally {
      window.resizeTo(originalWidth, originalHeight);
      window.dispatchEvent(new Event('resize'));
    }
  });

  it('renders football-first logo previews without Overview NFL-game click targets', () => {
    const element: HTMLElement = fixture.nativeElement;
    const gamePreview = element.querySelector<HTMLElement>('.matchup-window-game');

    expect(gamePreview).not.toBeNull();
    expect(gamePreview!.getAttribute('role')).toBe('img');
    expect(gamePreview!.querySelectorAll('img').length).toBe(2);
    expect(gamePreview!.getAttribute('aria-label')).toBe('AAA at HHH');
    expect(getComputedStyle(gamePreview!).borderRadius).toBe('999px');

    const abbreviations = gamePreview!.querySelectorAll<HTMLElement>('.matchup-window-game-abbr');
    expect(abbreviations.length).toBe(2);
    abbreviations.forEach(abbreviation => expect(getComputedStyle(abbreviation).display).toBe('none'));
  });
});
