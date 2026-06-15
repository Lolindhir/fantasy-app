import { Routes } from '@angular/router';
import { OverviewComponent } from './features/overview/overview';
import { TeamListComponent } from './features/teams/team-list/team-list';
import { PlayersPageComponent } from './features/players/players-page/players-page';
import { LeagueActivityComponent } from './features/league-activity/league-activity';
import { TradeSimulatorComponent } from './features/trade/trade-simulator/trade-simulator';
import { AboutComponent } from './features/handbook/about';

export const routes: Routes = [
  { path: '', component: OverviewComponent }, // aktuelle Startseite
  { path: 'teams', component: TeamListComponent },
  { path: 'players', component: PlayersPageComponent },
  { path: 'league-activity', component: LeagueActivityComponent },
  { path: 'trade', component: TradeSimulatorComponent },
  { path: 'handbook', component: AboutComponent },

  // Angular Fallback
  { path: '**', redirectTo: '' }
];
