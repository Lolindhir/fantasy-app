import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { DraftPickTriggerComponent } from '../../components/draft-pick-trigger/draft-pick-trigger';
import { DraftShellComponent } from '../../components/draft-shell/draft-shell';
import type { DraftViewModel } from '../../models/drafts-view.models';

@Component({
  selector: 'app-future-drafts-tab',
  standalone: true,
  imports: [
    CommonModule,
    DraftPickTriggerComponent,
    DraftShellComponent
  ],
  templateUrl: './future-drafts-tab.html',
  styleUrl: './future-drafts-tab.scss'
})
export class FutureDraftsTabComponent {
  @Input({ required: true }) drafts: DraftViewModel[] = [];
}
