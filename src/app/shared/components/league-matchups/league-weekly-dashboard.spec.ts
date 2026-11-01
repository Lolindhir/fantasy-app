import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { FantasyGameContextReadModel } from '../../../core/models/fantasy-game-context.models';
import type { League } from '../../../core/models/league.models';
import type { MatchupsReadModel } from '../../../core/models/matchup.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
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
      Logo: `/player-attached-nfl-${teamID}.png`
    }
  } as unknown as Player;
}

function makeNflTeams(teamCount = 10): NFLTeam[] {
  return Array.from({ length: teamCount }, (_, index) => {
    const teamID = index + 1;
    return {
      ID: `NFL-${teamID}`,
      Name: `NFL Team ${teamID}`,
      Abv: `N${teamID}`,
      Logo: `/transparent-nfl-${teamID}.svg`
    } as unknown as NFLTeam;
  });
}

function makeDecisionWindows(week = 2): DecisionWindowsReadModel {
  return {
    SchemaVersion: 3,
    LeagueID: 'league',
    Season: '2026',
    LineupWeek: week,
    LastLineupWeek: 17,
    DecisionWindows: [],
    LookaheadDecisionWindow: null,
    PlayerLockFacts: [],
    TeamLineupEvaluations: []
  };
}

function makeFantasyGameContext(week = 2): FantasyGameContextReadModel {
  return {
    SchemaVersion: 5,
    LeagueID: 'league',
    Season: '2026',
    Week: week,
    ScoringState: 'pending',
    DecisionWindows: [],
    Games: [],
    FantasyMatchups: [],
    NonGameAssociations: [],
    MustWatchGames: []
  };
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
      OwnerAvatar: place === 2 ? '' : `/owner-${place}.png`,
      TeamAvatar: `/team-${place}.png`,
      Avatar: `/team-${place}.png`,
      Roster: [makePlayer(place)],
      Placements: {
        Current: { Regular: regular },
        Previous: { Regular: regular, Playoffs: { Place: place, PlaceOrdinal: `${place}.` } },
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
    PlayoffStartWeek: 14,
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
      })),
      // Fixture of the canonical league-standings product after completed W1.
      // Display does not reconstruct rank, scores or streaks from Matchups.
      Weeks: [{
        Week: 1,
        Teams: teams.map(team => {
          const id = team.TeamID;
          const win = id % 2 === 1;
          const pairOffset = win ? id - 1 : id - 2;
          return {
            TeamID: id,
            Place: win ? (teamCount - id + 1) / 2 : teamCount / 2 + (teamCount - id + 2) / 2,
            Wins: win ? 1 : 0,
            Losses: win ? 0 : 1,
            Ties: 0,
            Points: (win ? 120 : 110) + pairOffset,
            PointsAgainst: (win ? 110 : 120) + pairOffset,
            Streak: win ? '1W' : '1L'
          };
        })
      }]
    }]
  } as unknown as League;
}

function makeMatchups(
  teamCount = 8,
  activeWeekKickoffUtc = '2099-09-17T00:00:00Z'
): MatchupsReadModel {
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
        FirstKickoffUtc: activeWeekKickoffUtc,
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
    KeyGames: [
      {
        GameID: 'g1',
        KickoffUtc: '2026-09-10T00:00:00Z',
        AwayNFLTeamID: 'NFL-1',
        HomeNFLTeamID: 'NFL-2',
        AwayScore: 24,
        HomeScore: 17,
        StarterPoints: 91.2,
        StarterCount: 5,
        FantasyTeamIDs: [1, 2],
        FantasyMatchupIDs: ['m-1']
      },
      {
        GameID: 'g2',
        KickoffUtc: '2026-09-11T00:00:00Z',
        AwayNFLTeamID: 'NFL-3',
        HomeNFLTeamID: 'NFL-4',
        AwayScore: 31,
        HomeScore: 28,
        StarterPoints: 78.4,
        StarterCount: 4,
        FantasyTeamIDs: [3, 4],
        FantasyMatchupIDs: ['m-2']
      },
      {
        GameID: 'g3',
        KickoffUtc: '2026-09-12T00:00:00Z',
        AwayNFLTeamID: 'NFL-5',
        HomeNFLTeamID: 'NFL-6',
        AwayScore: 20,
        HomeScore: 19,
        StarterPoints: 64.1,
        StarterCount: 3,
        FantasyTeamIDs: [5, 6],
        FantasyMatchupIDs: ['m-3']
      }
    ],
    TeamAwards: {
      State: 'available',
      BestCoach: [
        { CanonicalLeagueRosterID: 'coach-2', FantasyTeamID: 2, EfficiencyPercent: 89.4911, ActualStarterPoints: 179, PotentialPoints: 200.02, MissedPoints: 21.02 }
      ],
      BestManager: [
        { CanonicalLeagueRosterID: 'manager-1', FantasyTeamID: 1, PotentialPoints: 229.16 }
      ]
    },
    KeyPlayers: [
      { PlayerID: 'player-2', FantasyTeamID: 2, NFLTeamID: 'NFL-2', Position: 'WR', Points: 15 },
      { PlayerID: 'player-1', FantasyTeamID: 1, NFLTeamID: 'NFL-1', Position: 'WR', Points: 30 },
      { PlayerID: 'player-3', FantasyTeamID: 3, NFLTeamID: 'NFL-3', Position: 'WR', Points: 10 },
      { PlayerID: 'player-4', FantasyTeamID: 4, NFLTeamID: 'NFL-4', Position: 'WR', Points: 9 }
    ]
  }]
};

describe('LeagueMatchupsComponent #558 weekly overview polish', () => {
  let fixture: ComponentFixture<LeagueMatchupsComponent>;
  let dataService: jasmine.SpyObj<DataService>;

  beforeEach(async () => {
    dataService = jasmine.createSpyObj<DataService>('DataService', [
      'getFantasyGameContext',
      'getDecisionWindows',
      'getMatchups',
      'getNflTeams',
      'getWeeklyRecaps'
    ]);
    dataService.getFantasyGameContext.and.returnValue(of(makeFantasyGameContext()));
    dataService.getDecisionWindows.and.returnValue(of(makeDecisionWindows()));
    dataService.getMatchups.and.returnValue(of(makeMatchups()));
    dataService.getNflTeams.and.returnValue(of(makeNflTeams()));
    dataService.getWeeklyRecaps.and.returnValue(of(recap));

    await TestBed.configureTestingModule({
      imports: [LeagueMatchupsComponent],
      providers: [
        provideRouter([]),
        { provide: DataService, useValue: dataService },
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
      const standingRecords = Array.from(shell!.querySelectorAll('.weekly-standing-record')).map(row => row.textContent?.trim());
      expect(standingRecords.filter(record => record === '1-0').length).toBe(4);
      expect(standingRecords.filter(record => record === '0-1').length).toBe(4);
      expect(shell!.querySelectorAll('.weekly-last-matchup').length).toBe(4);
      expect(shell!.querySelectorAll('.weekly-last-side').length).toBe(8);
      expect(shell!.querySelector('.weekly-last-row')).toBeNull();

      const standingRows = shell!.querySelector<HTMLElement>('.weekly-context-half--standings .weekly-context-rows');
      const lastRows = shell!.querySelector<HTMLElement>('.weekly-last-matchups');
      expect(Math.abs(lastRows!.scrollHeight - standingRows!.scrollHeight)).toBeLessThanOrEqual(1);
      expect(Number.parseFloat(getComputedStyle(standingRows!).paddingBottom)).toBeGreaterThanOrEqual(8);

      const matchups = Array.from(shell!.querySelectorAll<HTMLElement>('.weekly-last-matchup'));
      for (const matchup of matchups) {
        expect(matchup.querySelectorAll('.weekly-last-side').length).toBe(2);
        expect(matchup.scrollWidth).toBeLessThanOrEqual(matchup.clientWidth + 1);
        expect(matchup.getBoundingClientRect().height).toBeGreaterThanOrEqual(width >= 768 ? 76 : 66);
      }
      expect(getComputedStyle(matchups[0]).backgroundColor).toBe('rgba(0, 0, 0, 0)');
      expect(getComputedStyle(matchups[1]).borderTopWidth).toBe('1px');

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

  for (const width of [320, 360, 390, 430]) {
    it(`keeps the compact 2-game / 3-player / 2-award recap dense and contained at ${width}px`, () => {
      dataService.getMatchups.and.returnValue(of(makeMatchups(8, '2000-09-17T00:00:00Z')));
      fixture.destroy();
      fixture = TestBed.createComponent(LeagueMatchupsComponent);
      fixture.componentInstance.league = makeLeague();
      fixture.detectChanges();

      const host: HTMLElement = fixture.nativeElement;
      host.style.display = 'block';
      host.style.containerType = 'inline-size';
      host.style.width = `${width}px`;
      fixture.detectChanges();

      const shell = host.querySelector<HTMLElement>('.weekly-recap-shell--compact');
      const gameList = shell?.querySelector<HTMLElement>('.weekly-recap-list--games');
      const playerList = shell?.querySelector<HTMLElement>('.weekly-recap-list--players');
      const games = Array.from(shell?.querySelectorAll<HTMLElement>('.weekly-recap-game') ?? []);
      const players = Array.from(shell?.querySelectorAll<HTMLElement>('.weekly-recap-player') ?? []);
      const awardGrid = shell?.querySelector<HTMLElement>('.weekly-recap-awards');
      const awards = Array.from(shell?.querySelectorAll<HTMLElement>('.weekly-recap-award') ?? []);

      expect(shell).not.toBeNull();
      expect(gameList).not.toBeNull();
      expect(playerList).not.toBeNull();
      expect(games.length).toBe(2);
      expect(players.length).toBe(3);
      expect(awards.length).toBe(2);
      expect(awardGrid).not.toBeNull();
      expect(awards[0].textContent).toContain('Best Coach');
      expect(awards[0].textContent).toContain('89.5%');
      expect(awards[1].textContent).toContain('Best Manager');
      expect(awards[1].textContent).toContain('229.16');
      expect(awards[0].textContent).toContain('Owner 2');
      expect(awards[1].querySelector('img')?.getAttribute('src')).toBe('/owner-1.png');
      expect(awards[1].querySelector('img')?.getAttribute('src')).not.toBe('/team-1.png');
      expect(shell!.querySelector('.weekly-recap-meta')).toBeNull();
      expect(shell!.textContent).not.toContain('starter pts');
      expect(shell!.textContent).not.toContain('starter');
      expect(shell!.scrollWidth).toBeLessThanOrEqual(shell!.clientWidth + 1);
      expect(gameList!.scrollWidth).toBeLessThanOrEqual(gameList!.clientWidth + 1);
      expect(playerList!.scrollWidth).toBeLessThanOrEqual(playerList!.clientWidth + 1);
      expect(shell!.getBoundingClientRect().height).toBeLessThan(305);
      expect(awardGrid!.scrollWidth).toBeLessThanOrEqual(awardGrid!.clientWidth + 1);
      expect(getComputedStyle(awardGrid!).gridTemplateColumns.split(' ').filter(Boolean).length).toBe(2);
      for (const award of awards) {
        expect(award.scrollWidth).toBeLessThanOrEqual(award.clientWidth + 1);
        const winner = award.querySelector<HTMLElement>('.weekly-recap-award-winner')!;
        const owner = winner.querySelector<HTMLElement>('.weekly-recap-award-owner')!;
        const value = winner.querySelector<HTMLElement>('.weekly-recap-award-value')!;
        const ownerRect = owner.getBoundingClientRect();
        const valueRect = value.getBoundingClientRect();
        const ownerCenterY = (ownerRect.top + ownerRect.bottom) / 2;
        const valueCenterY = (valueRect.top + valueRect.bottom) / 2;
        expect(Math.abs(ownerCenterY - valueCenterY)).toBeLessThan(2);
        expect(valueRect.right).toBeLessThanOrEqual(winner.getBoundingClientRect().right + 1);
        expect(getComputedStyle(value).whiteSpace).toBe('nowrap');
      }
      expect(getComputedStyle(awards[0].querySelector<HTMLElement>('.weekly-recap-award-extra')!).display).toBe('none');
      const unit = awards[1].querySelector<HTMLElement>('.weekly-recap-award-unit')!;
      expect(getComputedStyle(unit).position).toBe('absolute');
      expect(unit.textContent).toContain('pts');

      const gameColumns = getComputedStyle(gameList!).gridTemplateColumns.split(' ').filter(Boolean);
      const playerColumns = getComputedStyle(playerList!).gridTemplateColumns.split(' ').filter(Boolean);
      expect(gameColumns.length).toBe(2);
      expect(playerColumns.length).toBe(3);

      for (const game of games) {
        expect(game.scrollWidth).toBeLessThanOrEqual(game.clientWidth + 1);
        const score = game.querySelector<HTMLElement>('.weekly-recap-nfl-score');
        expect(score).not.toBeNull();
        expect(score!.scrollWidth).toBeLessThanOrEqual(score!.clientWidth + 1);
      }

      for (const player of players) {
        expect(player.scrollWidth).toBeLessThanOrEqual(player.clientWidth + 1);
        const name = player.querySelector<HTMLElement>('.weekly-recap-player-copy strong');
        expect(name).not.toBeNull();
        expect(getComputedStyle(name!).textOverflow).toBe('ellipsis');
        expect(getComputedStyle(name!).whiteSpace).toBe('nowrap');
      }
    });
  }

  it('shows richer Owner identity in the prominent recap and opens the correct team', () => {
    const host: HTMLElement = fixture.nativeElement;
    const shell = host.querySelector<HTMLElement>('.weekly-recap-shell--prominent');
    expect(shell).not.toBeNull();
    const awards = Array.from(shell!.querySelectorAll<HTMLElement>('.weekly-recap-award'));
    expect(awards.length).toBe(2);
    expect(awards[0].textContent).toContain('Best Coach');
    expect(awards[0].textContent).toContain('Long Fantasy Team 2');
    expect(awards[0].textContent).toContain('179 / 200.02 possible pts');
    expect(awards[1].textContent).toContain('Best Manager');
    expect(awards[1].textContent).toContain('Long Fantasy Team 1');
    // Prominent awards must not overwhelm the adjacent Key Fantasy Players.
    // Keep the already-accepted Compact variant on its own CSS overrides.
    const playerPoints = shell!.querySelector<HTMLElement>('.weekly-recap-player-points')!;
    const playerName = shell!.querySelector<HTMLElement>('.weekly-recap-player-copy strong')!;
    const awardPoints = awards[0].querySelector<HTMLElement>('.weekly-recap-award-value')!;
    const awardName = awards[0].querySelector<HTMLElement>('.weekly-recap-award-identity strong')!;
    const awardAvatar = awards[0].querySelector<HTMLElement>('.weekly-recap-award-avatar')!;
    expect(getComputedStyle(awardPoints).fontSize).toBe(getComputedStyle(playerPoints).fontSize);
    expect(getComputedStyle(awardName).fontSize).toBe(getComputedStyle(playerName).fontSize);
    expect(getComputedStyle(awardAvatar).width).toBe('28px');
    expect(getComputedStyle(awards[0]).paddingTop).toBe('7px');
    // Score and muted explanation are centered; title and identity remain left-aligned.
    for (const award of awards) {
      const value = award.querySelector<HTMLElement>('.weekly-recap-award-value')!;
      const extra = award.querySelector<HTMLElement>('.weekly-recap-award-extra')!;
      const owner = award.querySelector<HTMLElement>('.weekly-recap-award-owner')!;
      expect(getComputedStyle(value).textAlign).toBe('center');
      expect(getComputedStyle(extra).textAlign).toBe('center');
      expect(getComputedStyle(owner).textAlign).toBe('left');
    }
    const ownerButton = awards[1].querySelector<HTMLButtonElement>('.weekly-recap-award-owner')!;
    ownerButton.click();
    const dialog = TestBed.inject(TeamDetailDialogService) as jasmine.SpyObj<TeamDetailDialogService>;
    expect(dialog.open).toHaveBeenCalledWith(1);
  });

  it('does not show award cards when weekly recap awards are unavailable', () => {
    const withoutAwards: WeeklyRecapsReadModel = {
      ...recap,
      Weeks: [{ ...recap.Weeks[0], TeamAwards: { State: 'unavailable', BestCoach: [], BestManager: [] } }]
    };
    dataService.getWeeklyRecaps.and.returnValue(of(withoutAwards));
    fixture.destroy();
    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('.weekly-recap-awards')).toBeNull();
  });

  it('retains the prior matchup week instead of hiding the surface while standings are stale', () => {
    const staleLeague = makeLeague();
    for (const team of staleLeague.Teams) {
      team.Placements.Current.Regular.Wins = 0;
      team.Placements.Current.Regular.Losses = 0;
      team.Placements.Current.Regular.Ties = 0;
      team.Placements.Current.Regular.Record = '0-0';
    }

    fixture.destroy();
    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = staleLeague;
    fixture.detectChanges();

    const host: HTMLElement = fixture.nativeElement;
    expect(fixture.componentInstance.week).toBe(1);
    expect(fixture.componentInstance.currentWeekSurfaceReady).toBeTrue();
    expect(host.querySelector('.weekly-context-shell')).not.toBeNull();
    expect(host.querySelector('.matchups-shell')).not.toBeNull();
    expect(host.querySelector('.matchups-heading')?.textContent).toContain('Week 1 Matchups');
  });

  it('retains the completed context week while Matchups has already advanced', () => {
    dataService.getFantasyGameContext.and.returnValue(of(makeFantasyGameContext(1)));
    dataService.getDecisionWindows.and.returnValue(of(makeDecisionWindows(1)));

    fixture.destroy();
    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = makeLeague();
    fixture.detectChanges();

    const host: HTMLElement = fixture.nativeElement;
    expect(fixture.componentInstance.week).toBe(1);
    expect(fixture.componentInstance.currentWeekSurfaceReady).toBeTrue();
    expect(host.querySelector('.weekly-context-shell')).not.toBeNull();
    expect(host.querySelector('.matchups-shell')).not.toBeNull();
    expect(host.querySelector('.matchups-heading')?.textContent).toContain('Week 1 Matchups');
  });

  it('shows Week 2, Week-1 history and Week-1 standings while Week 3 context is not coherent', () => {
    const rolloverLeague = makeLeague();
    rolloverLeague.FinalScoredWeek = 2;
    for (const team of rolloverLeague.Teams) {
      team.Placements.Current.Regular.Wins = 2;
      team.Placements.Current.Regular.Losses = 0;
      team.Placements.Current.Regular.Ties = 0;
      team.Placements.Current.Regular.Record = '2-0';
    }

    const rolloverMatchups = makeMatchups();
    rolloverMatchups.Weeks[1] = {
      ...rolloverMatchups.Weeks[1],
      CompletionState: 'final',
      Matchups: rolloverMatchups.Weeks[1].Matchups.map(matchup => ({
        ...matchup,
        CompletionState: 'final' as const,
        Participants: matchup.Participants.map((participant, index) => ({
          ...participant,
          Points: 150 + Number(participant.TeamID) + index
        })),
        Result: { Type: 'win' as const, WinnerTeamID: matchup.Participants[0].TeamID }
      }))
    };
    rolloverMatchups.Weeks.push({
      Week: 3,
      Stage: 'regular-season',
      FirstKickoffUtc: '2099-09-24T00:00:00Z',
      CompletionState: 'open',
      Matchups: rolloverMatchups.Weeks[1].Matchups.map((matchup, index) => ({
        FantasyMatchupID: `w3-${index + 1}`,
        CompletionState: 'open' as const,
        Participants: matchup.Participants.map(participant => ({
          TeamID: participant.TeamID,
          Points: 0,
          ScoreKind: 'standard' as const
        })),
        Result: null
      }))
    });
    rolloverMatchups.Summary = { LastCompletedWeek: 2, ActiveOrNextWeek: 3 };

    dataService.getMatchups.and.returnValue(of(rolloverMatchups));
    dataService.getFantasyGameContext.and.returnValue(of(makeFantasyGameContext(2)));
    dataService.getDecisionWindows.and.returnValue(of(makeDecisionWindows(2)));

    fixture.destroy();
    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    fixture.componentInstance.league = rolloverLeague;
    fixture.detectChanges();

    const host: HTMLElement = fixture.nativeElement;
    expect(fixture.componentInstance.week).toBe(2);
    expect(host.querySelector('.matchups-heading')?.textContent).toContain('Week 2 Matchups');
    expect(host.querySelector('.weekly-context-half--last .weekly-context-heading')?.textContent).toContain('Last Week · W1');
    const records = Array.from(host.querySelectorAll('.weekly-standing-record')).map(row => row.textContent?.trim());
    expect(records.filter(record => record === '1-0').length).toBe(4);
    expect(records.filter(record => record === '0-1').length).toBe(4);
  });

  it('releases the current matchup surface when standings and week context are coherent', () => {
    const host: HTMLElement = fixture.nativeElement;
    expect(fixture.componentInstance.currentWeekSurfaceReady).toBeTrue();
    expect(host.querySelector('.matchups-shell')).not.toBeNull();
    expect(host.querySelector('.matchup-card')).not.toBeNull();
  });

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

  it('positions the playoff cutline from league settings and hides it when not applicable', () => {
    dataService.getMatchups.and.returnValue(of(makeMatchups(6)));
    fixture.destroy();
    fixture = TestBed.createComponent(LeagueMatchupsComponent);
    const league = makeLeague(6);
    league.Settings = { playoff_teams: 4 };
    fixture.componentInstance.league = league;
    fixture.detectChanges();

    const cutlineRanks = () => Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLElement>(
        '.weekly-standing-row--playoff-cutline .weekly-standing-rank'
      )
    ).map(rank => rank.textContent?.trim());

    expect(cutlineRanks()).toEqual(['5']);

    league.Settings = { playoff_teams: 2 };
    fixture.detectChanges();
    expect(cutlineRanks()).toEqual(['3']);

    league.Settings = { playoff_teams: 6 };
    fixture.detectChanges();
    expect(cutlineRanks()).toEqual([]);

    league.Settings = {};
    fixture.detectChanges();
    expect(cutlineRanks()).toEqual([]);

    league.Settings = { playoff_teams: 'invalid' };
    fixture.detectChanges();
    expect(cutlineRanks()).toEqual([]);
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

  it('renders only the first two KeyGames as scoreboard tiles without ranking diagnostics', () => {
    const host: HTMLElement = fixture.nativeElement;
    const games = Array.from(host.querySelectorAll<HTMLElement>('.weekly-recap-game'));

    expect(games.length).toBe(2);
    expect(games[0].textContent).toContain('N1');
    expect(games[0].textContent).toContain('24–17');
    expect(games[0].textContent).toContain('N2');
    expect(games[1].textContent).toContain('N3');
    expect(games[1].textContent).toContain('31–28');
    expect(games[1].textContent).toContain('N4');
    expect(host.textContent).not.toContain('N5');
    expect(host.querySelector('.weekly-recap-meta')).toBeNull();
  });

  it('uses NFL-team abbreviations in dense recap player metadata and preserves WeeklyRecaps order', () => {
    const host: HTMLElement = fixture.nativeElement;
    const rows = Array.from(host.querySelectorAll<HTMLButtonElement>('.weekly-recap-player'));

    expect(rows.length).toBe(3);
    expect(rows.map(row => row.querySelector('.weekly-recap-player-copy strong')?.textContent?.trim())).toEqual(['P2', 'P1', 'P3']);
    expect(rows.map(row => row.querySelector('.weekly-recap-player-copy span')?.textContent?.trim())).toEqual(['WR · N2', 'WR · N1', 'WR · N3']);
    expect(rows.map(row => row.querySelector('.weekly-recap-player-points')?.textContent?.trim())).toEqual(['15', '30', '10']);
    expect(rows.every(row => row.querySelector('.weekly-recap-player-nfl-logo') === null)).toBeTrue();

    const picture = rows[0].querySelector<HTMLElement>('.weekly-recap-player-picture');
    expect(picture).not.toBeNull();
    expect(picture!.getBoundingClientRect().width).toBeLessThanOrEqual(28.5);
    expect(picture!.getBoundingClientRect().height).toBeLessThanOrEqual(28.5);
  });

  it('opens the established Player Detail dialog from the whole recap player row', () => {
    const host: HTMLElement = fixture.nativeElement;
    const row = host.querySelector<HTMLButtonElement>('.weekly-recap-player');
    const expectedPlayer = fixture.componentInstance.league.Teams[1].Roster[0];
    const resolvedDialog = fixture.debugElement.injector.get(MatDialog);
    const openSpy = spyOn(resolvedDialog, 'open');

    expect(row).not.toBeNull();
    expect(row!.disabled).toBeFalse();
    expect(row!.getAttribute('aria-label')).toBe('Open P2 player details');
    row!.click();

    expect(openSpy).toHaveBeenCalledWith(
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
