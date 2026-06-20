import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';
import { DataService } from '../../core/services/data.service';
import { CurrentDraftsTabComponent } from './tabs/current-drafts/current-drafts-tab';
import { FutureDraftsTabComponent } from './tabs/future-drafts/future-drafts-tab';
import { createDraftsViewModel } from './utils/drafts-view-model.mapper';

type DraftsTab = 'current' | 'future';

@Component({
  selector: 'app-drafts-page',
  standalone: true,
  imports: [
    CommonModule,
    CurrentDraftsTabComponent,
    FutureDraftsTabComponent
  ],
  templateUrl: './drafts-page.html',
  styleUrl: './drafts-page.scss'
})
export class DraftsPageComponent {
  private dataService = inject(DataService);

  activeTab: DraftsTab = 'current';

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, drafts, teams }) => createDraftsViewModel(league, drafts, teams))
  );

  selectTab(tab: DraftsTab): void {
    this.activeTab = tab;
  }
}
