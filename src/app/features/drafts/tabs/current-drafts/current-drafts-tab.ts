import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { SharedMaterialImports } from '../../../../shared/shared-material-imports';
import { DraftShellComponent } from '../../components/draft-shell/draft-shell';
import type { DraftViewModel } from '../../models/drafts-view.models';

@Component({
  selector: 'app-current-drafts-tab',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports, DraftShellComponent],
  templateUrl: './current-drafts-tab.html',
  styleUrl: './current-drafts-tab.scss'
})
export class CurrentDraftsTabComponent {
  @Input({ required: true }) drafts: DraftViewModel[] = [];
}
