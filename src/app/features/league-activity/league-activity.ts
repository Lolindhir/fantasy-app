import { Component } from '@angular/core';
import { SharedMaterialImports } from '../../shared/shared-material-imports';

@Component({
  selector: 'app-league-activity',
  standalone: true,
  imports: [
    SharedMaterialImports
  ],
  templateUrl: './league-activity.html',
  styleUrl: './league-activity.scss'
})
export class LeagueActivityComponent {
}
