import { ComponentFixture, TestBed } from '@angular/core/testing';

import type { DecisionWindowGame } from '../../../core/models/decision-window.models';
import type { NFLTeam } from '../../../core/models/player.models';
import { TeamLineupMatchupComponent } from './team-lineup-matchup';

describe('TeamLineupMatchupComponent', () => {
  let fixture: ComponentFixture<TeamLineupMatchupComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TeamLineupMatchupComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TeamLineupMatchupComponent);
  });

  it('renders NFL abbreviations with both logos around a centered at-sign', () => {
    const game = {
      GameID: 'chi-car',
      Week: 1,
      AwayTeamID: '6',
      AwayTeamAbbr: 'CHI',
      HomeTeamID: '5',
      HomeTeamAbbr: 'CAR'
    } satisfies DecisionWindowGame;
    const teams = [
      { ID: '6', Name: 'Bears', Abv: 'CHI', Logo: 'chi-logo' },
      { ID: '5', Name: 'Panthers', Abv: 'CAR', Logo: 'car-logo' }
    ] as NFLTeam[];

    fixture.componentRef.setInput('game', game);
    fixture.componentRef.setInput('nflTeams', teams);
    fixture.detectChanges();

    const element: HTMLElement = fixture.nativeElement;
    expect(element.textContent).toContain('CHI');
    expect(element.textContent).toContain('@');
    expect(element.textContent).toContain('CAR');
    expect(element.textContent).not.toContain('Chicago Bears');
    expect(element.textContent).not.toContain('Carolina Panthers');
    expect(element.querySelectorAll('.team-lineup-matchup-logo img').length).toBe(2);
  });
});
