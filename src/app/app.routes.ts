import { Routes } from '@angular/router';
import { OverviewComponent } from './overview/overview';
import { TeamListComponent } from './team-list/team-list';
import { TradeSimulatorComponent } from './trade-simulator/trade-simulator';
import { AboutComponent } from './about/about';

export const routes: Routes = [
  { path: '', component: OverviewComponent }, // aktuelle Startseite
  { path: 'teams', component: TeamListComponent },
  { path: 'trade', component: TradeSimulatorComponent },
  { path: 'handbook', component: AboutComponent },

  // Angular Fallback
  { path: '**', redirectTo: '' }
];