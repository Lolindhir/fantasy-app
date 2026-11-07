import { TestBed } from '@angular/core/testing';

import { SeasonAwardsComponent } from './season-awards';
import type { SeasonHistoryAwardItem } from '../../utils/league-standings-view.util';

function award(name: string, icon: string): SeasonHistoryAwardItem {
  return { key: name, icon, name, displayText: name, owner: `Owner ${name}`, teamName: null, teamAvatar: 'x.png', ownerAvatar: null, statDisplay: `${name} stat`, tooltip: name, order: 1 };
}

describe('SeasonAwardsComponent', () => {
  function render(awards: SeasonHistoryAwardItem[] | null) {
    const fixture = TestBed.createComponent(SeasonAwardsComponent);
    fixture.componentInstance.awards = awards;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [SeasonAwardsComponent] }));

  it('renders one uniform card per supplied award, whatever the names are', () => {
    const el = render([award('Alpha', 'A'), award('Beta', 'B'), award('Gamma', 'C')]);
    const cards = el.querySelectorAll('.season-award');
    expect(cards.length).toBe(3);
    expect(cards[1].textContent).toContain('Beta');
    expect(cards[1].textContent).toContain('Owner Beta');
    expect(cards[1].textContent).toContain('Beta stat');
  });

  it('renders nothing for an empty or missing list', () => {
    expect(render([]).querySelector('.season-awards')).toBeNull();
    expect(render(null).querySelector('.season-awards')).toBeNull();
  });
});
