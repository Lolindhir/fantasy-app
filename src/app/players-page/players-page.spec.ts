import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PlayersPage } from './players-page';

describe('PlayersPage', () => {
  let component: PlayersPage;
  let fixture: ComponentFixture<PlayersPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlayersPage]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PlayersPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
