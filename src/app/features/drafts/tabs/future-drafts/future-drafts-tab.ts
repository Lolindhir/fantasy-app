import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatMenuModule } from '@angular/material/menu';
import { SharedMaterialImports } from '../../../../shared/shared-material-imports';
import { CurrentDraftPickPopoverComponent } from '../current-drafts/components/current-draft-pick-popover/current-draft-pick-popover';
import type { DraftViewModel } from '../../models/drafts-view.models';

@Component({
  selector: 'app-future-drafts-tab',
  standalone: true,
  imports: [
    CommonModule,
    MatMenuModule,
    SharedMaterialImports,
    CurrentDraftPickPopoverComponent
  ],
  templateUrl: './future-drafts-tab.html',
  styleUrl: './future-drafts-tab.scss'
})
export class FutureDraftsTabComponent {
  @Input({ required: true }) drafts: DraftViewModel[] = [];
}
