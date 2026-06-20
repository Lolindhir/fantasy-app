import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { SharedMaterialImports } from '../../../../shared/shared-material-imports';
import { DraftShellComponent } from '../../components/draft-shell/draft-shell';
import type { DraftViewModel } from '../../models/drafts-view.models';
import { CurrentDraftListViewComponent } from './views/current-draft-list-view/current-draft-list-view';
import { CurrentDraftOverviewViewComponent } from './views/current-draft-overview-view/current-draft-overview-view';
import { CurrentDraftTeamViewComponent } from './views/current-draft-team-view/current-draft-team-view';

type CurrentDraftView = 'overview' | 'teams' | 'list';

@Component({
  selector: 'app-current-drafts-tab',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports,
    DraftShellComponent,
    CurrentDraftOverviewViewComponent,
    CurrentDraftTeamViewComponent,
    CurrentDraftListViewComponent
  ],
  templateUrl: './current-drafts-tab.html',
  styleUrl: './current-drafts-tab.scss'
})
export class CurrentDraftsTabComponent {
  @Input({ required: true }) drafts: DraftViewModel[] = [];

  activeViewByDraftKey: { [draftKey: string]: CurrentDraftView } = {};

  getActiveView(draftKey: string): CurrentDraftView {
    return this.activeViewByDraftKey[draftKey] ?? 'overview';
  }

  selectView(draftKey: string, view: CurrentDraftView): void {
    this.activeViewByDraftKey[draftKey] = view;
  }
}
