import { Routes } from '@angular/router';
import { OverviewComponent } from './features/overview/overview';
import { PlayersPageComponent } from './features/players/players-page';
import { TeamsPageComponent } from './features/teams/teams-page/teams-page';
import { TeamListComponent } from './features/teams/team-list/team-list';
import { TradeSimulatorComponent } from './features/trade/trade-simulator/trade-simulator';
import { LeagueActivityComponent } from './features/league-activity/league-activity';
import { AboutComponent } from './features/handbook/about';
import { DraftsPageComponent } from './features/drafts/drafts-page';
import { StandingsPageComponent } from './features/standings/standings-page';

export const routes: Routes = [
  { path: '', component: OverviewComponent },
  { path: 'players', component: PlayersPageComponent },
  { path: 'teams', component: TeamsPageComponent },
  { path: 'teams/legacy', component: TeamListComponent },
  { path: 'standings', component: StandingsPageComponent },
  { path: 'trade', component: TradeSimulatorComponent },
  { path: 'drafts', component: DraftsPageComponent },
  { path: 'moves', component: LeagueActivityComponent },
  { path: 'league-activity', redirectTo: 'moves', pathMatch: 'full' },
  { path: 'about', component: AboutComponent },
  { path: '**', redirectTo: '' }
];
