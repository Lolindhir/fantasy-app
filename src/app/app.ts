import { Component, OnInit, signal } from '@angular/core';
import { Router, RouterModule, RouterOutlet, NavigationEnd } from '@angular/router';
import { A11yModule } from "@angular/cdk/a11y";
import { HostListener } from "@angular/core";
import { filter } from "rxjs/operators";
import { APP_BUILD_INFO, AppBuildInfo } from './core/build-info.generated';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, RouterOutlet, A11yModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  protected readonly title = signal('fantasy-league-custom-frontend');
  menuOpen = false;
  isScrolled = false;

  readonly loadedBuildInfo = APP_BUILD_INFO;
  serverBuildInfo?: AppBuildInfo;
  updateAvailable = false;

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

          case '/players':
            this.currentPage = 'Players';
            break;

          case '/league-activity':
            this.currentPage = 'Drafts & Moves';
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

  ngOnInit(): void {
    this.loadServerBuildInfo();
  }

  get buildInfoLabel(): string {
    const date = this.formatBuildDate(this.loadedBuildInfo.buildDate);
    const version = this.loadedBuildInfo.shortCommit || this.loadedBuildInfo.version;
    const updateText = this.updateAvailable ? ' · Update verfügbar' : '';

    return `Build ${date} · ${version}${updateText}`;
  }

  get buildInfoTitle(): string {
    const loaded = `Geladen: ${this.loadedBuildInfo.version} (${this.loadedBuildInfo.commit})`;
    const server = this.serverBuildInfo
      ? `Server: ${this.serverBuildInfo.version} (${this.serverBuildInfo.commit})`
      : 'Server: nicht geprüft';

    return `${loaded}\n${server}`;
  }

  private loadServerBuildInfo(): void {
    fetch(`build-info.json?t=${Date.now()}`, { cache: 'no-store' })
      .then(response => response.ok ? response.json() : undefined)
      .then((buildInfo?: AppBuildInfo) => {
        if (!buildInfo) return;

        this.serverBuildInfo = buildInfo;
        this.updateAvailable = this.isDifferentBuild(buildInfo);
      })
      .catch(() => {
        this.serverBuildInfo = undefined;
        this.updateAvailable = false;
      });
  }

  private isDifferentBuild(serverBuildInfo: AppBuildInfo): boolean {
    if (!serverBuildInfo.commit || serverBuildInfo.commit === 'local') return false;
    if (!this.loadedBuildInfo.commit || this.loadedBuildInfo.commit === 'local') return false;

    return serverBuildInfo.commit !== this.loadedBuildInfo.commit;
  }

  private formatBuildDate(buildDate: string): string {
    if (!buildDate || buildDate === 'local') return 'local';

    const date = new Date(buildDate);
    if (Number.isNaN(date.getTime())) return buildDate;

    return date.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
