import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TradeSimulator } from './trade-simulator';

describe('TradeSimulator', () => {
  let component: TradeSimulator;
  let fixture: ComponentFixture<TradeSimulator>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TradeSimulator]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TradeSimulator);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
