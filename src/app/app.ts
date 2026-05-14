import { Component, signal } from '@angular/core';
import { Router, RouterModule, RouterOutlet, NavigationEnd } from '@angular/router';
import { A11yModule } from "@angular/cdk/a11y";
import { HostListener } from "@angular/core";
import { filter } from "rxjs/operators";

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, RouterOutlet, A11yModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('fantasy-league-custom-frontend');
  menuOpen = false;
  isScrolled = false;

  @HostListener('window:scroll')
  onScroll(): void {
    this.isScrolled = window.scrollY > 10;
  }

  currentPage = 'Overview';

  constructor(private router: Router) {

    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {

        switch (this.router.url) {

          case '/':
            this.currentPage = 'Overview';
            break;

          case '/teams':
            this.currentPage = 'Teams';
            break;

          case '/trade':
            this.currentPage = 'Trade Simulator';
            break;

          case '/handbook':
            this.currentPage = 'Handbook';
            break;

          default:
            this.currentPage = 'Navigation';
        }
      });
  }
}
