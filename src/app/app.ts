import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TeamListComponent } from './team-list/team-list';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, TeamListComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('fantasy-league-custom-frontend');
}
