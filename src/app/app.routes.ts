import { Routes } from '@angular/router';
import { OverviewComponent } from './overview/overview';
import { TeamListComponent } from './team-list/team-list';
import { PlayersPageComponent } from './players-page/players-page';
import { TradeSimulatorComponent } from './trade-simulator/trade-simulator';
import { AboutComponent } from './about/about';

export const routes: Routes = [
  { path: '', component: OverviewComponent }, // aktuelle Startseite
  { path: 'teams', component: TeamListComponent },
  { path: 'players', component: PlayersPageComponent },
  { path: 'trade', component: TradeSimulatorComponent },
  { path: 'handbook', component: AboutComponent },

  // Angular Fallback
  { path: '**', redirectTo: '' }
];