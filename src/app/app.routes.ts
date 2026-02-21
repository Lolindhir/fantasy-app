import { Routes } from '@angular/router';
import { TeamListComponent } from './team-list/team-list';
import { TradeSimulatorComponent } from './trade-simulator/trade-simulator';

export const routes: Routes = [
  { path: '', component: TeamListComponent }, // aktuelle Startseite
  { path: 'trade', component: TradeSimulatorComponent }
];