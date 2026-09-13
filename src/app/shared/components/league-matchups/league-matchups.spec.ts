import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';

import type { DecisionWindowsReadModel, FantasyRelevanceTeamState } from '../../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
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

  const league = {
    Season: '2026',
    FinalScoredWeek: 1,
    Teams: [
      { TeamID: 1, Team: 'Left Team', TeamAbbr: 'LFT', Owner: 'Left Owner', Avatar: null },
      { TeamID: 2, Team: 'Right Team', TeamAbbr: 'RGT', Owner: 'Right Owner', Avatar: null }
    ],
    Matchups: {
      Season: '2026',
      Week: 1,
      Matchups: [{
        MatchupID: 1,
        Participants: [
          { TeamID: 1, Points: 37.4 },
          { TeamID: 2, Points: 13.8 }
        ]
      }]
    }
  } as unknown as League;

  beforeEach(async () => {
    const dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getFantasyGameContext', 'getDecisionWindows', 'getNflTeams'
    ]);
    dataService.getFantasyGameContext.and.returnValue(of(context));
    dataService.getDecisionWindows.and.returnValue(of(decisionWindows));
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

  it('makes the upper fantasy zone the matchup target while an NFL pill remains its own game target', () => {
    const matchupSpy = spyOn(component, 'openMatchupDetail').and.stub();
    const gameSpy = spyOn(component, 'openGameDetail').and.stub();
    fixture.detectChanges();

    const element: HTMLElement = fixture.nativeElement;
    const matchupTarget = element.querySelector<HTMLElement>('.matchup-primary');
    const gameTarget = element.querySelector<HTMLButtonElement>('.matchup-window-game');

    expect(matchupTarget).not.toBeNull();
    expect(gameTarget).not.toBeNull();

    matchupTarget!.click();
    expect(matchupSpy).toHaveBeenCalledTimes(1);
    expect(gameSpy).not.toHaveBeenCalled();

    gameTarget!.click();
    expect(gameSpy).toHaveBeenCalledTimes(1);
    expect(matchupSpy).toHaveBeenCalledTimes(1);
  });

  it('renders dominant current scores, starter strips and one window-level kickoff label', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.matchup-score-value--left')?.textContent?.trim()).toBe('37.4');
    expect(element.querySelector('.matchup-score-value--right')?.textContent?.trim()).toBe('13.8');
    expect(element.querySelectorAll('.matchup-progress-segment').length).toBe(2);
    expect(element.querySelectorAll('.matchup-window-time').length).toBe(1);
    expect(element.querySelectorAll('.matchup-window-game').length).toBeGreaterThan(0);
  });

  it('renders scoring-window game pills with compact logo-only visuals and accessible game identity', () => {
    const element: HTMLElement = fixture.nativeElement;
    const gameTarget = element.querySelector<HTMLButtonElement>('.matchup-window-game');

    expect(gameTarget).not.toBeNull();
    expect(gameTarget!.querySelectorAll('img').length).toBe(2);
    expect(gameTarget!.getAttribute('aria-label')).toBe('Open AAA at HHH game details');
    expect(getComputedStyle(gameTarget!).borderRadius).toBe('999px');

    const abbreviations = gameTarget!.querySelectorAll<HTMLElement>('.matchup-window-game-abbr');
    expect(abbreviations.length).toBe(2);
    abbreviations.forEach(abbreviation => expect(getComputedStyle(abbreviation).display).toBe('none'));
  });
});
