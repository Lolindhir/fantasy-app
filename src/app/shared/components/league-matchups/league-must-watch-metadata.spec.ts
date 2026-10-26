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
    PlayoffStartWeek: 14,
    Teams: Array.from({ length: 9 }, (_, index) => {
      const teamID = index + 1;
      return {
        TeamID: teamID,
        Team: `Fantasy Team ${teamID}`,
        TeamAbbr: `T${teamID}`,
        Owner: `Owner ${teamID}`,
        Avatar: `/team-${teamID}.png`,
        Roster: [],
        Placements: {
          Current: {
            Regular: {
              Place: teamID,
              PlaceOrdinal: `${teamID}.`,
              Wins: 1,
              Losses: 0,
              Ties: 0,
              Points: 100 + teamID,
              PointsAgainst: 90,
              WinPercentage: 1,
              WinPercentageDisplay: '1.000',
              Record: '1-0',
              Streak: '1W'
            },
            Awards: []
          }
        }
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

function makeDecisionWindows(): DecisionWindowsReadModel {
  return {
    SchemaVersion: 3,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: 2,
    LastLineupWeek: 17,
    DecisionWindows: [],
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: []
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
    ScoringState: 'partial',
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

function makeFinalContext(): FantasyGameContextReadModel {
  const context = makeContext();
  return {
    ...context,
    ScoringState: 'final',
    Games: context.Games.map(game => ({ ...game, Status: 'Final' }))
  };
}

function makeMarketContext(final: boolean): FantasyGameContextReadModel {
  const context = makeContext();
  return {
    ...context,
    SchemaVersion: 6,
    Games: context.Games.map(game => ({
      ...game,
      Status: final ? 'Final' : 'Scheduled',
      AwayScore: final ? 24 : null,
      HomeScore: final ? 30 : null,
      AwayTeamID: 'PIT',
      AwayTeamAbbr: 'PIT',
      HomeTeamID: 'NO',
      HomeTeamAbbr: 'NO',
      Market: {
        SpreadLine: -3,
        TotalLine: 44.5,
        ImpliedAwayPoints: 23.75,
        ImpliedHomePoints: 20.75
      }
    }))
  };
}

describe('LeagueMatchupsComponent #578/#581 Must Watch presentation', () => {
  let fixture: ComponentFixture<LeagueMatchupsComponent>;
  let dataService: jasmine.SpyObj<DataService>;
  let teamDialog: jasmine.SpyObj<TeamDetailDialogService>;

  beforeEach(async () => {
    dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getFantasyGameContext',
      'getDecisionWindows',
      'getMatchups',
      'getNflTeams',
      'getWeeklyRecaps'
    ]);
    dataService.getFantasyGameContext.and.returnValue(of(makeContext()));
    dataService.getDecisionWindows.and.returnValue(of(makeDecisionWindows()));
    dataService.getMatchups.and.returnValue(of(makeMatchups()));
    dataService.getNflTeams.and.returnValue(of([
      { ID: 'A', Name: 'Away', Abv: 'AAA', Logo: '/away.svg' },
      { ID: 'H', Name: 'Home', Abv: 'HHH', Logo: '/home.svg' }
    ] as NFLTeam[]));
    dataService.getWeeklyRecaps.and.returnValue(of({ SchemaVersion: 1 as const, Season: '2026', Weeks: [] }));

    teamDialog = jasmine.createSpyObj<TeamDetailDialogService>('TeamDetailDialogService', ['open']);

    await TestBed.configureTestingModule({
      imports: [LeagueMatchupsComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
        { provide: TeamDetailDialogService, useValue: teamDialog }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague();
    fixture.detectChanges();
  });

  it('keeps unchanged counts and direct-Starter team exposure without redundant global or strip labels', () => {
    const host: HTMLElement = fixture.nativeElement;
    const card = host.querySelector<HTMLElement>('.fantasy-pulse-card--remaining');
    const metrics = card?.querySelector<HTMLElement>('.fantasy-pulse-metrics');
    const strip = card?.querySelector<HTMLElement>('.fantasy-pulse-team-strip');
    const avatarGroup = strip?.querySelector<HTMLElement>('.fantasy-pulse-team-avatars');
    const chips = Array.from(metrics?.querySelectorAll<HTMLElement>('.fantasy-pulse-metric-chip') ?? []);
    const avatars = Array.from(strip?.querySelectorAll<HTMLButtonElement>('.fantasy-pulse-team-avatar') ?? []);

    expect(card).not.toBeNull();
    expect(metrics).not.toBeNull();
    expect(strip).not.toBeNull();
    expect(avatarGroup).not.toBeNull();
    expect(chips.map(chip => chip.textContent?.trim())).toEqual(['8 starters', '4 matchups']);
    expect(strip!.querySelector('.fantasy-pulse-team-strip-label')).toBeNull();
    expect(strip!.querySelector(':scope > strong')?.textContent?.trim()).toBe('8');
    expect(avatars.length).toBe(8);
    expect(avatars.map(avatar => avatar.title)).toEqual(['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8']);
    expect(host.querySelector<HTMLButtonElement>('[title="T9"]')).toBeNull();
    expect(host.querySelector('.fantasy-pulse-state')).toBeNull();
    expect(host.querySelector('.fantasy-pulse-heading')?.textContent?.toUpperCase()).not.toContain('PARTIAL');
    expect(card!.querySelector('[role="img"][aria-label="Final"]')).toBeNull();
    expect(getComputedStyle(metrics!).flexWrap).toBe('nowrap');
    expect(getComputedStyle(strip!).position).toBe('absolute');
    expect(getComputedStyle(strip!).justifyContent).toBe('flex-end');
    expect(getComputedStyle(avatarGroup!).flexGrow).toBe('0');

    const metricsRect = metrics!.getBoundingClientRect();
    const stripRect = strip!.getBoundingClientRect();
    const metricsCenter = metricsRect.top + metricsRect.height / 2;
    const stripCenter = stripRect.top + stripRect.height / 2;
    expect(Math.abs(metricsCenter - stripCenter)).toBeLessThanOrEqual(4);
  });

  it('shows only the accessible checkered flag when existing game finality is true', () => {
    dataService.getFantasyGameContext.and.returnValue(of(makeFinalContext()));
    const finalFixture = TestBed.createComponent(LeagueMatchupsComponent);
    finalFixture.componentInstance.league = makeLeague();
    finalFixture.detectChanges();

    try {
      const host: HTMLElement = finalFixture.nativeElement;
      const lockup = host.querySelector<HTMLElement>('.fantasy-pulse-game-lockup');
      const finalMarker = lockup?.querySelector<HTMLElement>('[role="img"][aria-label="Final"]');

      expect(finalMarker).not.toBeNull();
      expect(finalMarker!.textContent?.trim()).toBe('🏁');
      expect(lockup?.querySelector('.fantasy-pulse-score-label--final')?.textContent?.trim()).toBe('🏁 Final');
      expect(Array.from(lockup?.querySelectorAll('.fantasy-pulse-score-value') ?? []).map(score => score.textContent?.trim())).toEqual(['–', '–']);
      expect(host.querySelector('.fantasy-pulse-side-live')).toBeNull();
      expect(host.querySelector('.fantasy-pulse-state')).toBeNull();
    } finally {
      finalFixture.destroy();
    }
  });

  it('shows rounded Vegas-implied NFL points beneath their teams without O/U or spread', () => {
    dataService.getFantasyGameContext.and.returnValue(of(makeMarketContext(false)));
    const marketFixture = TestBed.createComponent(LeagueMatchupsComponent);
    marketFixture.componentInstance.league = makeLeague();
    marketFixture.detectChanges();

    try {
      const host: HTMLElement = marketFixture.nativeElement;
      const lockup = host.querySelector<HTMLElement>('.fantasy-pulse-game-lockup')!;
      const scores = lockup.querySelectorAll<HTMLElement>('.fantasy-pulse-score-value');
      expect(Array.from(scores).map(score => score.textContent?.trim())).toEqual(['≈24', '≈21']);
      expect(lockup.querySelector('.fantasy-pulse-score-label--market')?.textContent?.trim()).toBe('🎰 Proj.');
      expect(lockup.querySelectorAll('.fantasy-pulse-nfl-team').length).toBe(2);
      expect(lockup.querySelectorAll('.fantasy-pulse-score-value--projected').length).toBe(2);
      expect(lockup.querySelector('.fantasy-pulse-status-emoji')?.getAttribute('aria-label')).toBe('Betting market');
      expect(host.querySelector('.fantasy-pulse-side-meta .fantasy-pulse-rank')?.textContent?.trim()).toBe('#1');
      expect(host.querySelector('.fantasy-pulse-game-kickoff')).not.toBeNull();
      expect(host.querySelector('.fantasy-pulse-game-meta')).toBeNull();
      expect(lockup.textContent).not.toContain('O/U');
      expect(lockup.textContent).not.toContain('44.5');
      expect(lockup.textContent).not.toContain('−3');
      expect(marketFixture.componentInstance.formatImpliedNflScore(24.5)).toBe('≈25');
      expect(marketFixture.componentInstance.formatImpliedNflScore(null)).toBe('–');
    } finally {
      marketFixture.destroy();
    }
  });

  it('keeps gray rounded market estimates during Live and moves the blue radio cue beside kickoff', () => {
    const current = makeMarketContext(false);
    dataService.getFantasyGameContext.and.returnValue(of({
      ...current,
      Games: current.Games.map(game => ({
        ...game,
        Status: 'In Progress',
        RemainingRelevance: { ...game.RemainingRelevance!, LockedActiveStarterCount: 2 }
      }))
    }));
    const liveFixture = TestBed.createComponent(LeagueMatchupsComponent);
    liveFixture.componentInstance.league = makeLeague();
    liveFixture.detectChanges();
    try {
      const host: HTMLElement = liveFixture.nativeElement;
      const lockup = host.querySelector<HTMLElement>('.fantasy-pulse-game-lockup')!;
      expect(host.querySelector('.fantasy-pulse-card--live')).not.toBeNull();
      const right = host.querySelector<HTMLElement>('.fantasy-pulse-side-meta')!;
      const live = right.querySelector<HTMLElement>('.fantasy-pulse-side-live');
      expect(live?.textContent?.trim()).toBe('Live');
      expect(live?.querySelector('.fantasy-pulse-live-icon circle')).not.toBeNull();
      expect(right.querySelector('.fantasy-pulse-game-kickoff')).not.toBeNull();
      expect(Array.from(lockup.querySelectorAll('.fantasy-pulse-score-value')).map(value => value.textContent?.trim())).toEqual(['≈24', '≈21']);
      expect(lockup.querySelectorAll('.fantasy-pulse-score-value--projected').length).toBe(2);
      expect(lockup.querySelector('.fantasy-pulse-score-label--market')?.textContent?.trim()).toBe('🎰 Proj.');
      expect(lockup.querySelector('.fantasy-pulse-score-label--final')).toBeNull();
    } finally {
      liveFixture.destroy();
    }
  });

  it('keeps the Live cue without inventing projected values when market evidence is unavailable', () => {
    const current = makeMarketContext(false);
    dataService.getFantasyGameContext.and.returnValue(of({
      ...current,
      Games: current.Games.map(game => ({
        ...game,
        Status: 'In Progress',
        Market: null,
        RemainingRelevance: { ...game.RemainingRelevance!, LockedActiveStarterCount: 2 }
      }))
    }));
    const liveFixture = TestBed.createComponent(LeagueMatchupsComponent);
    liveFixture.componentInstance.league = makeLeague();
    liveFixture.detectChanges();
    try {
      const host: HTMLElement = liveFixture.nativeElement;
      expect(host.querySelector('.fantasy-pulse-card--live')).not.toBeNull();
      expect(host.querySelector('.fantasy-pulse-side-live')?.textContent?.trim()).toBe('Live');
      expect(host.querySelector('.fantasy-pulse-score-value')).toBeNull();
      expect(host.querySelector('.fantasy-pulse-score-label--market')).toBeNull();
    } finally {
      liveFixture.destroy();
    }
  });

  it('prioritizes canonical Final over stale locked-active starter evidence', () => {
    const current = makeMarketContext(true);
    const finalGame = {
      ...current.Games[0],
      RemainingRelevance: { ...current.Games[0].RemainingRelevance!, LockedActiveStarterCount: 3 }
    };
    expect(fixture.componentInstance.gameIsLiveForFantasy(finalGame)).toBeFalse();
    expect(fixture.componentInstance.gameIsFinal(finalGame)).toBeTrue();
  });

  it('switches to the real NFL final score and hides market expectations for a final game', () => {
    dataService.getFantasyGameContext.and.returnValue(of(makeMarketContext(true)));
    const finalFixture = TestBed.createComponent(LeagueMatchupsComponent);
    finalFixture.componentInstance.league = makeLeague();
    finalFixture.detectChanges();
    try {
      const host: HTMLElement = finalFixture.nativeElement;
      const lockup = host.querySelector<HTMLElement>('.fantasy-pulse-game-lockup')!;
      expect(Array.from(lockup.querySelectorAll('.fantasy-pulse-score-value')).map(score => score.textContent?.trim())).toEqual(['24', '30']);
      expect(lockup.querySelector('.fantasy-pulse-score-label--final')?.textContent?.trim()).toBe('🏁 Final');
      expect(lockup.querySelector('.fantasy-pulse-score-label--market')).toBeNull();
      expect(host.querySelector('.fantasy-pulse-side-live')).toBeNull();
      expect(host.querySelector('[aria-label="Final"]')).not.toBeNull();
      expect(host.querySelector('.fantasy-pulse-card--final')).not.toBeNull();
    } finally {
      finalFixture.destroy();
    }
  });

  it('keeps scheduled and final games side by side in the same Must Watch ranking', () => {
    const scheduled = makeMarketContext(false);
    const final = makeMarketContext(true);
    dataService.getFantasyGameContext.and.returnValue(of({
      ...scheduled,
      Games: [scheduled.Games[0], { ...final.Games[0], GameID: 'g2' }],
      MustWatchGames: [scheduled.MustWatchGames![0], { ...scheduled.MustWatchGames![0], GameID: 'g2', Rank: 2 }]
    }));
    const mixedFixture = TestBed.createComponent(LeagueMatchupsComponent);
    mixedFixture.componentInstance.league = makeLeague();
    mixedFixture.detectChanges();
    try {
      const cards = (mixedFixture.nativeElement as HTMLElement).querySelectorAll<HTMLElement>('.fantasy-pulse-card--remaining');
      expect(cards.length).toBe(2);
      expect(cards[0].querySelector('.fantasy-pulse-score-label--market')?.textContent?.trim()).toBe('🎰 Proj.');
      expect(cards[0].querySelectorAll('.fantasy-pulse-score-value').length).toBe(2);
      expect(cards[1].querySelector('.fantasy-pulse-score-label--final')?.textContent?.trim()).toBe('🏁 Final');
      expect(cards[1].querySelectorAll('.fantasy-pulse-score-value').length).toBe(2);
      expect(cards[1].querySelector('.fantasy-pulse-score-label--market')).toBeNull();
      expect(cards[0].querySelector('.fantasy-pulse-metrics')?.textContent).toContain('starter');
      expect(cards[1].querySelector('.fantasy-pulse-metrics')?.textContent).toContain('starter');
    } finally {
      mixedFixture.destroy();
    }
  });

  it('omits the score row when no canonical market data is available', () => {
    const host: HTMLElement = fixture.nativeElement;
    expect(host.querySelector('.fantasy-pulse-score-value')).toBeNull();
    expect(host.querySelector('.fantasy-pulse-score-label')).toBeNull();
    expect(host.querySelector('.fantasy-pulse-game-lockup')).not.toBeNull();
  });

  for (const width of [360, 390, 430, 1280]) {
    for (const isLive of [false, true]) {
    it(`keeps team-aligned estimates and right-hand status compact at ${width}px (${isLive ? 'Live' : 'Pregame'})`, () => {
      const current = makeMarketContext(false);
      dataService.getFantasyGameContext.and.returnValue(of(isLive ? {
        ...current,
        Games: current.Games.map(game => ({
          ...game,
          Status: 'In Progress',
          RemainingRelevance: { ...game.RemainingRelevance!, LockedActiveStarterCount: 2 }
        }))
      } : current));
      const marketFixture = TestBed.createComponent(LeagueMatchupsComponent);
      marketFixture.componentInstance.league = makeLeague();
      marketFixture.detectChanges();
      const sourceCard = (marketFixture.nativeElement as HTMLElement)
        .querySelector<HTMLElement>('.fantasy-pulse-card--remaining')!;
      const frame = document.createElement('iframe');
      frame.style.position = 'absolute';
      frame.style.left = '-2000px';
      frame.style.width = `${width}px`;
      frame.style.height = '400px';
      document.body.appendChild(frame);

      try {
        const frameDocument = frame.contentDocument!;
        for (const style of Array.from(document.head.querySelectorAll('style'))) {
          frameDocument.head.appendChild(style.cloneNode(true));
        }
        const reset = frameDocument.createElement('style');
        reset.textContent = 'html,body{box-sizing:border-box;width:100%;min-width:0;margin:0;overflow:hidden;}*,*::before,*::after{box-sizing:border-box;}';
        frameDocument.head.appendChild(reset);
        frameDocument.body.appendChild(sourceCard.cloneNode(true));

        const card = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-card--remaining')!;
        const lockup = card.querySelector<HTMLElement>('.fantasy-pulse-game-lockup')!;
        const teams = lockup.querySelectorAll<HTMLElement>('.fantasy-pulse-nfl-team');
        const scores = lockup.querySelectorAll<HTMLElement>('.fantasy-pulse-score-value');
        const cardRect = card.getBoundingClientRect();
        const lockupRect = lockup.getBoundingClientRect();
        const side = card.querySelector<HTMLElement>('.fantasy-pulse-side-meta')!;
        expect(side.querySelector('.fantasy-pulse-side-live') !== null).toBe(isLive);
        if (isLive) {
          expect(side.querySelector('.fantasy-pulse-side-live .fantasy-pulse-live-icon')).not.toBeNull();
          expect(lockup.querySelector('.fantasy-pulse-score-label--market')?.textContent?.trim()).toBe('🎰 Proj.');
        }
        const rankRect = side.querySelector<HTMLElement>('.fantasy-pulse-rank')!.getBoundingClientRect();
        const kickoffRect = side.querySelector<HTMLElement>('.fantasy-pulse-game-kickoff')!.getBoundingClientRect();
        const metricsRect = card.querySelector<HTMLElement>('.fantasy-pulse-metrics')!.getBoundingClientRect();
        expect(rankRect.bottom).withContext(`${width}px rank above kickoff`).toBeLessThanOrEqual(kickoffRect.top + 1);
        expect(side.getBoundingClientRect().left).withContext(`${width}px side-meta overlap`).toBeGreaterThanOrEqual(lockupRect.right + 3);
        expect(kickoffRect.bottom).withContext(`${width}px kickoff above fantasy metrics`).toBeLessThanOrEqual(metricsRect.top + 2);
        expect(card.scrollWidth).withContext(`${width}px card overflow`).toBeLessThanOrEqual(card.clientWidth + 1);
        expect(lockup.scrollWidth).withContext(`${width}px score overflow`).toBeLessThanOrEqual(lockup.clientWidth + 1);
        expect(lockupRect.right).withContext(`${width}px score containment`).toBeLessThanOrEqual(cardRect.right + 1);
        expect(getComputedStyle(lockup).display).toBe('grid');
        for (let index = 0; index < 2; index++) {
          const teamRect = teams[index].getBoundingClientRect();
          const scoreRect = scores[index].getBoundingClientRect();
          expect(Math.abs((teamRect.left + teamRect.right) / 2 - (scoreRect.left + scoreRect.right) / 2))
            .withContext(`${width}px team ${index} score alignment`).toBeLessThanOrEqual(2);
        }
        expect(cardRect.height).withContext(`${width}px compact card`).toBeLessThanOrEqual(100);
      } finally {
        frame.remove();
        marketFixture.destroy();
      }
    });
    }
  }

  it('keeps the existing Team Detail interaction separate from the NFL game-detail target', () => {
    const host: HTMLElement = fixture.nativeElement;
    const firstAvatar = host.querySelector<HTMLButtonElement>('.fantasy-pulse-team-avatar');
    const gameTarget = host.querySelector<HTMLButtonElement>('.fantasy-pulse-card-main');
    const resolvedDialog = fixture.debugElement.injector.get(MatDialog);
    const openSpy = spyOn(resolvedDialog, 'open');

    expect(firstAvatar).not.toBeNull();
    expect(gameTarget).not.toBeNull();

    firstAvatar!.click();
    expect(teamDialog.open).toHaveBeenCalledOnceWith(1);
    expect(openSpy).not.toHaveBeenCalled();

    gameTarget!.click();
    expect(openSpy).toHaveBeenCalledTimes(1);
    expect(teamDialog.open).toHaveBeenCalledTimes(1);
  });

  for (const width of [360, 390, 430, 1280]) {
    it(`keeps the compact Must Watch metadata contained and right-clustered at ${width}px`, () => {
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
        reset.textContent = 'html,body{box-sizing:border-box;width:100%;min-width:0;margin:0;overflow:hidden;}*,*::before,*::after{box-sizing:border-box;}';
        frameDocument.head.appendChild(reset);
        frameDocument.body.appendChild(sourceCard.cloneNode(true));

        const card = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-card--remaining')!;
        const metrics = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-metrics')!;
        const strip = frameDocument.querySelector<HTMLElement>('.fantasy-pulse-team-strip')!;
        const avatarGroup = strip.querySelector<HTMLElement>('.fantasy-pulse-team-avatars')!;
        const metricChips = metrics.querySelectorAll<HTMLElement>('.fantasy-pulse-metric-chip');
        const count = strip.querySelector<HTMLElement>(':scope > strong')!;
        const cardRect = card.getBoundingClientRect();
        const metricsRect = metrics.getBoundingClientRect();
        const stripRect = strip.getBoundingClientRect();
        const avatarGroupRect = avatarGroup.getBoundingClientRect();
        const lastMetricRect = metricChips[metricChips.length - 1].getBoundingClientRect();
        const countRect = count.getBoundingClientRect();
        const metricsCenter = metricsRect.top + metricsRect.height / 2;
        const stripCenter = stripRect.top + stripRect.height / 2;
        const avatarCountGap = countRect.left - avatarGroupRect.right;

        expect(frameWindow.innerWidth).withContext(`${width}px iframe viewport`).toBe(width);
        expect(cardRect.right).withContext(`${width}px card containment`).toBeLessThanOrEqual(width + 1);
        expect(card.scrollWidth).withContext(`${width}px card horizontal overflow`).toBeLessThanOrEqual(card.clientWidth + 1);
        expect(getComputedStyle(metrics).flexWrap).withContext(`${width}px metadata wrapping`).toBe('nowrap');
        expect(getComputedStyle(strip).justifyContent).withContext(`${width}px right cluster alignment`).toBe('flex-end');
        expect(getComputedStyle(avatarGroup).flexGrow).withContext(`${width}px avatar group must not consume metadata row`).toBe('0');
        expect(strip.querySelector('.fantasy-pulse-team-strip-label')).withContext(`${width}px redundant strip label`).toBeNull();
        expect(lastMetricRect.right).withContext(`${width}px counts/avatar overlap`).toBeLessThanOrEqual(stripRect.left + 1);
        expect(stripRect.right).withContext(`${width}px strip containment`).toBeLessThanOrEqual(cardRect.right + 1);
        expect(Math.abs(stripRect.right - countRect.right)).withContext(`${width}px affected-team count right alignment`).toBeLessThanOrEqual(1);
        expect(avatarCountGap).withContext(`${width}px avatar/count separation`).toBeGreaterThanOrEqual(-1);
        expect(avatarCountGap).withContext(`${width}px avatar/count compact adjacency`).toBeLessThanOrEqual(6);
        expect(countRect.width).withContext(`${width}px affected-team count width`).toBeGreaterThan(0);
        expect(Math.abs(metricsCenter - stripCenter)).withContext(`${width}px shared metadata row`).toBeLessThanOrEqual(4);
        expect(cardRect.height).withContext(`${width}px compact card height`).toBeLessThanOrEqual(90);
      } finally {
        frame.remove();
      }
    });
  }
});
