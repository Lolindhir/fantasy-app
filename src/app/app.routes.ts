import { Routes } from '@angular/router';
import { OverviewComponent } from './features/overview/overview';
import { TeamsPageComponent } from './features/teams/teams-page/teams-page';
import { TeamListComponent } from './features/teams/team-list/team-list';
import { StandingsPageComponent } from './features/standings/standings-page';
import { PlayersPageComponent } from './features/players/players-page/players-page';
import { DraftsPageComponent } from './features/drafts/drafts-page';
import { LeagueActivityComponent } from './features/league-activity/league-activity';
import { TradeSimulatorComponent } from './features/trade/trade-simulator/trade-simulator';
import { AboutComponent } from './features/handbook/about';

export const routes: Routes = [
  { path: '', component: OverviewComponent },
  { path: 'teams', component: TeamsPageComponent },
  { path: 'teams/legacy', component: TeamListComponent },
  { path: 'standings', component: StandingsPageComponent },
  { path: 'players', component: PlayersPageComponent },
  { path: 'drafts', component: DraftsPageComponent },
  { path: 'moves', component: LeagueActivityComponent },
  { path: 'league-activity', redirectTo: 'moves', pathMatch: 'full' },
  { path: 'trade', component: TradeSimulatorComponent },
  { path: 'handbook', component: AboutComponent },
  { path: '**', redirectTo: '' }
];
