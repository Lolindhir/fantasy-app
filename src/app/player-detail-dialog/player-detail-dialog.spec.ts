import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PlayerDetailDialog } from './player-detail-dialog';

describe('PlayerDetailDialog', () => {
  let component: PlayerDetailDialog;
  let fixture: ComponentFixture<PlayerDetailDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlayerDetailDialog]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PlayerDetailDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
