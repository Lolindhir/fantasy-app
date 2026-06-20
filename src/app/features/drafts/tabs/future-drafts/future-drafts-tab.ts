import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { SharedMaterialImports } from '../../../../shared/shared-material-imports';
import type { DraftViewModel } from '../../models/drafts-view.models';

@Component({
  selector: 'app-future-drafts-tab',
  standalone: true,
  imports: [
    CommonModule,
    SharedMaterialImports
  ],
  templateUrl: './future-drafts-tab.html',
  styleUrl: './future-drafts-tab.scss'
})
export class FutureDraftsTabComponent {
  @Input({ required: true }) drafts: DraftViewModel[] = [];
}
