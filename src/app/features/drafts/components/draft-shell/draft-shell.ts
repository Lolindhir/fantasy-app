import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { SharedMaterialImports } from '../../../../shared/shared-material-imports';
import type { DraftViewModel } from '../../models/drafts-view.models';

@Component({
  selector: 'app-draft-shell',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './draft-shell.html',
  styleUrl: './draft-shell.scss'
})
export class DraftShellComponent {
  @Input({ required: true }) draftVm!: DraftViewModel;
  @Input() showAvatar = true;
  @Input() showStatus = true;
}
