import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';
import { DataService } from '../../core/services/data.service';
import { CurrentDraftsTabComponent } from './tabs/current-drafts/current-drafts-tab';
import { FutureDraftsTabComponent } from './tabs/future-drafts/future-drafts-tab';
import { PastDraftsTabComponent } from './tabs/past-drafts/past-drafts-tab';
import { createDraftsViewModel } from './utils/drafts-view-model.mapper';

type DraftsTab = 'current' | 'future' | 'past';

@Component({
  selector: 'app-drafts-page',
  standalone: true,
  imports: [
    CommonModule,
    CurrentDraftsTabComponent,
    FutureDraftsTabComponent,
    PastDraftsTabComponent
  ],
  templateUrl: './drafts-page.html',
  styleUrl: './drafts.scss'
})
export class DraftsPageComponent {
  private dataService = inject(DataService);

  activeTab: DraftsTab = 'current';

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, drafts, teams, players }) => {
      const draftVm = createDraftsViewModel(league, drafts, teams, players);
      return {
        currentSeason: draftVm.currentSeason,
        currentSeasonDrafts: draftVm.currentSeasonDrafts,
        futureDrafts: draftVm.futureDrafts,
        draftCount: draftVm.draftCount,
        tradedPickCount: draftVm.tradedPickCount,
        pickCount: draftVm.pickCount,
        pickedCount: draftVm.pickedCount,
        league,
        teams,
        players
      };
    })
  );

  selectTab(tab: DraftsTab): void {
    this.activeTab = tab;
  }
}
