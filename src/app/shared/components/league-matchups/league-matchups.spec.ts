import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';

import type {
  DecisionWindowsReadModel,
  FantasyRelevanceSlotState,
  FantasyRelevanceTeamState
} from '../../../core/models/decision-window.models';
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
    SchemaVersion: 5,
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
        ActiveScoringWindowID: null, ActiveScoringGameIDs: [],
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

  it('renders dominant current scores, starter strips and one compact no-live next-scoring summary', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.matchup-score-value--left')?.textContent?.trim()).toBe('37.4');
    expect(element.querySelector('.matchup-score-value--right')?.textContent?.trim()).toBe('13.8');
    expect(element.querySelectorAll('.matchup-progress-segment').length).toBe(2);
    expect(element.querySelectorAll('.matchup-window-time').length).toBe(1);
    expect(element.querySelector('.matchup-window-kicker')?.textContent?.trim()).toBe('Next scoring window');
    expect(element.querySelector('.matchup-window-count')?.textContent?.trim()).toBe('1 NFL game');
    expect(element.querySelectorAll('.matchup-window-game').length).toBe(1);
    expect(element.querySelector('.matchup-window-overflow')).toBeNull();
  });

  it('preserves missing score versus reliable zero semantics', () => {
    expect(component.formatFantasyPoints(null)).toBe('–');
    expect(component.formatFantasyPoints(0)).toBe('0');
  });

  it('keeps 0-0 and long decimal scores collision-free without growing the identity row at responsive widths', () => {
    const element: HTMLElement = fixture.nativeElement;
    const sourceCard = element.querySelector<HTMLElement>('.matchup-card')!;
    const sourceLeftScore = sourceCard.querySelector<HTMLElement>('.matchup-score-value--left')!;
    const sourceRightScore = sourceCard.querySelector<HTMLElement>('.matchup-score-value--right')!;

    for (const [leftScore, rightScore] of [['0', '0'], ['123.45', '987.65']]) {
      sourceLeftScore.textContent = leftScore;
      sourceRightScore.textContent = rightScore;

      for (const width of [360, 390, 430, 1280]) {
        const frame = document.createElement('iframe');
        frame.style.position = 'absolute';
        frame.style.left = '-2000px';
        frame.style.top = '0';
        frame.style.width = `${width}px`;
        frame.style.height = '900px';
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

          const scoreboard = frameDocument.querySelector<HTMLElement>('.matchup-scoreboard')!;
          const plate = frameDocument.querySelector<HTMLElement>('.matchup-score-plate')!;
          const scoreboardRect = scoreboard.getBoundingClientRect();
          const leftTeam = frameDocument.querySelector<HTMLElement>('.matchup-team--left')!.getBoundingClientRect();
          const rightTeam = frameDocument.querySelector<HTMLElement>('.matchup-team--right')!.getBoundingClientRect();
          const plateRect = plate.getBoundingClientRect();
          const visibleIdentity = Array.from(frameDocument.querySelectorAll<HTMLElement>('.matchup-team-identity'))
            .find(identity => frameWindow.getComputedStyle(identity).display !== 'none')!;
          const scoreFontSize = Number.parseFloat(frameWindow.getComputedStyle(
            plate.querySelector<HTMLElement>('.matchup-score-value--left')!
          ).fontSize);

          expect(frameWindow.innerWidth).withContext(`${width}px iframe viewport`).toBe(width);
          expect(plateRect.left).withContext(`${width}px ${leftScore}-${rightScore} plate inside scoreboard`)
            .toBeGreaterThanOrEqual(scoreboardRect.left - 1);
          expect(plateRect.right).withContext(`${width}px ${leftScore}-${rightScore} plate inside scoreboard`)
            .toBeLessThanOrEqual(scoreboardRect.right + 1);
          expect(plateRect.left).withContext(`${width}px ${leftScore}-${rightScore} left identity collision`)
            .toBeGreaterThanOrEqual(leftTeam.right - 1);
          expect(plateRect.right).withContext(`${width}px ${leftScore}-${rightScore} right identity collision`)
            .toBeLessThanOrEqual(rightTeam.left + 1);
          expect(plateRect.height).withContext(`${width}px ${leftScore}-${rightScore} score plate height`)
            .toBeLessThanOrEqual(visibleIdentity.getBoundingClientRect().height + 1);

          if (width === 360) {
            expect(scoreFontSize).withContext('360px compact score typography').toBeLessThan(18);
          } else if (width === 1280) {
            expect(scoreFontSize).withContext('1280px desktop score typography').toBeGreaterThan(20);
          }
        } finally {
          frame.remove();
        }
      }
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

  it('shows Final, Live, Next and Later concurrently and renders LIVE NOW plus NEXT in the compact footer', () => {
    const snapshot = snapshotFixtureState();
    try {
      configureLiveAndNextFixture();
      fixture.detectChanges();

      const element: HTMLElement = fixture.nativeElement;
      const progressKinds = Array.from(element.querySelectorAll<HTMLElement>('.matchup-progress-strip--left .matchup-progress-segment'))
        .map(segment => Array.from(segment.classList).find(name => name.startsWith('matchup-progress-segment--')));
      const kickers = Array.from(element.querySelectorAll<HTMLElement>('.matchup-window-kicker'))
        .map(kicker => kicker.textContent?.trim());

      expect(progressKinds).toEqual([
        'matchup-progress-segment--final',
        'matchup-progress-segment--locked',
        'matchup-progress-segment--next',
        'matchup-progress-segment--future'
      ]);
      expect(kickers).toEqual(['Live now', 'Next']);
      expect(element.querySelectorAll('.matchup-window-time').length).toBe(2);
      expect(element.querySelectorAll('.matchup-window-count').length).toBe(2);
      expect(element.querySelector('.matchup-window-live')).toBeNull();
      expect(element.querySelector('.matchup-window button')).toBeNull();
    } finally {
      restoreFixtureState(snapshot);
      fixture.detectChanges();
    }
  });

  it('shows FINAL SCORING WINDOW when the active direct-Starter window has no future next', () => {
    const snapshot = snapshotFixtureState();
    try {
      configureLiveAndNextFixture();
      const remaining = context.FantasyMatchups[0].RemainingRelevance!;
      remaining.NextScoringWindowID = null;
      remaining.NextScoringGameIDs = [];
      fixture.detectChanges();

      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector('.matchup-window-kicker')?.textContent?.trim()).toBe('Live now');
      expect(element.querySelector('.matchup-window-live')?.textContent?.trim()).toBe('FINAL SCORING WINDOW');
      expect(element.querySelectorAll('.matchup-window-time').length).toBe(1);
    } finally {
      restoreFixtureState(snapshot);
      fixture.detectChanges();
    }
  });

  it('lets authoritative Matchups.json finality replace temporal scoring-window presentation', () => {
    const snapshot = snapshotFixtureState();
    try {
      configureLiveAndNextFixture();
      matchups.Weeks[0].Matchups[0].CompletionState = 'final';
      fixture.detectChanges();

      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector('.matchup-score-plate')?.getAttribute('data-scoreboard-state')).toBe('final');
      expect(element.querySelector('.matchup-window')).toBeNull();
    } finally {
      restoreFixtureState(snapshot);
      fixture.detectChanges();
    }
  });

  it('keeps live-plus-next compact and horizontally contained at 360, 390, 430 and desktop widths', () => {
    const snapshot = snapshotFixtureState();
    try {
      configureLiveAndNextFixture();
      fixture.detectChanges();
      const sourceCard = (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.matchup-card')!;

      for (const width of [360, 390, 430, 1280]) {
        const frame = document.createElement('iframe');
        frame.style.position = 'absolute';
        frame.style.left = '-2000px';
        frame.style.top = '0';
        frame.style.width = `${width}px`;
        frame.style.height = '900px';
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

          const card = frameDocument.querySelector<HTMLElement>('.matchup-card')!;
          const footer = frameDocument.querySelector<HTMLElement>('.matchup-window')!;
          expect(frameWindow.innerWidth).withContext(`${width}px iframe viewport`).toBe(width);
          expect(card.getBoundingClientRect().right).withContext(`${width}px card containment`).toBeLessThanOrEqual(width + 1);
          expect(footer.scrollWidth).withContext(`${width}px footer horizontal overflow`).toBeLessThanOrEqual(footer.clientWidth + 1);
          expect(footer.getBoundingClientRect().height).withContext(`${width}px live+next footer density`)
            .toBeLessThanOrEqual(width < 768 ? 92 : 48);
        } finally {
          frame.remove();
        }
      }
    } finally {
      restoreFixtureState(snapshot);
      fixture.detectChanges();
    }
  });

  function snapshotFixtureState(): { context: FantasyGameContextReadModel; decisionWindows: DecisionWindowsReadModel; matchups: MatchupsReadModel } {
    return {
      context: structuredClone(context),
      decisionWindows: structuredClone(decisionWindows),
      matchups: structuredClone(matchups)
    };
  }

  function restoreFixtureState(snapshot: { context: FantasyGameContextReadModel; decisionWindows: DecisionWindowsReadModel; matchups: MatchupsReadModel }): void {
    Object.assign(context, snapshot.context);
    Object.assign(decisionWindows, snapshot.decisionWindows);
    Object.assign(matchups, snapshot.matchups);
  }

  function configureLiveAndNextFixture(): void {
    const liveWindow = '2026-09-13T17:00:00Z';
    const nextWindow = '2026-09-13T20:25:00Z';
    const laterWindow = '2026-09-14T00:20:00Z';
    const baseContextGame = structuredClone(context.Games[0]);
    const baseMatchupGame = structuredClone(context.FantasyMatchups[0].Games[0]);

    const contextGame = (gameID: string, windowID: string, lockedActiveStarterCount: number) => ({
      ...structuredClone(baseContextGame),
      GameID: gameID,
      DecisionWindowID: windowID,
      StartsAtUtc: windowID,
      AwayTeamAbbr: `A-${gameID}`,
      HomeTeamAbbr: `H-${gameID}`,
      RemainingRelevance: {
        ...structuredClone(baseContextGame.RemainingRelevance!),
        LockedActiveStarterCount: lockedActiveStarterCount,
        UnlockedStarterCount: lockedActiveStarterCount > 0 ? 0 : 1
      }
    });

    context.SchemaVersion = 5;
    context.Games = [
      contextGame('g-live', liveWindow, 1),
      contextGame('g-next', nextWindow, 0),
      contextGame('g-later', laterWindow, 0)
    ];
    context.FantasyMatchups[0].Games = context.Games.map(candidate => ({
      ...structuredClone(baseMatchupGame),
      GameID: candidate.GameID,
      DecisionWindowID: candidate.DecisionWindowID,
      StartsAtUtc: candidate.StartsAtUtc
    }));
    Object.assign(context.FantasyMatchups[0].RemainingRelevance!, {
      LockedActiveStarterCount: 1,
      UnlockedStarterCount: 2,
      ActiveScoringWindowID: liveWindow,
      ActiveScoringGameIDs: ['g-live'],
      NextScoringWindowID: nextWindow,
      NextScoringGameIDs: ['g-next'],
      NextScoringPrimaryGameID: 'g-next',
      NextScoringWindowGameCount: 1,
      NextScoringLockedActiveStarterCount: 0,
      NextScoringUnlockedStarterCount: 1,
      FinalScoringWindowID: laterWindow,
      FinalScoringGameIDs: ['g-later']
    });

    const relevanceSlot = (
      slotID: string,
      state: FantasyRelevanceSlotState['State'],
      windowID: string | null
    ): FantasyRelevanceSlotState => ({
      SlotID: slotID,
      SlotType: slotID.split('-')[0],
      SlotOrdinal: Number(slotID.split('-').at(-1)) || 1,
      SlotIndex: Number(slotID.split('-').at(-1)) || 1,
      CurrentStarterID: `p-${slotID}`,
      State: state,
      GameID: windowID ? `g-${state}` : null,
      DecisionWindowID: windowID,
      StartsAtUtc: windowID,
      Repairability: null
    });

    const left = decisionWindows.FantasyRelevance!.Teams[0];
    left.Slots = [
      relevanceSlot('QB-1', 'completed', '2026-09-12T00:00:00Z'),
      relevanceSlot('RB-2', 'locked-active', liveWindow),
      relevanceSlot('WR-3', 'unlocked', nextWindow),
      relevanceSlot('TE-4', 'unlocked', laterWindow)
    ];
    left.StarterCount = 4;
    left.ActiveRosterPlayerCount = 4;
    left.CompletedStarterCount = 1;
    left.LockedActiveStarterCount = 1;
    left.UnlockedStarterCount = 2;
  }
});
