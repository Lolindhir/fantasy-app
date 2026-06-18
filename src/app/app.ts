import { Component, OnInit, signal } from '@angular/core';
import { Router, RouterModule, RouterOutlet, NavigationEnd } from '@angular/router';
import { A11yModule } from "@angular/cdk/a11y";
import { HostListener } from "@angular/core";
import { filter } from "rxjs/operators";
import { APP_BUILD_INFO } from './core/build-info.generated';

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
  readonly loadedBundleId = this.getLoadedBundleId();
  serverBundleId?: string;
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
    this.loadServerBundleInfo();
  }

  get buildInfoLabel(): string {
    const loadedVersion = this.loadedBundleId || this.loadedBuildInfo.shortCommit || this.loadedBuildInfo.version;
    const buildDate = this.formatBuildDate(this.loadedBuildInfo.buildDate);
    const dateText = buildDate ? ` · ${buildDate}` : '';
    const updateText = this.updateAvailable ? ' · Update verfügbar' : '';

    return `Build ${loadedVersion}${dateText}${updateText}`;
  }

  get buildInfoTitle(): string {
    const loadedBundle = `Geladener Bundle: ${this.loadedBundleId || 'unbekannt'}`;
    const loadedBuildDate = `Build-Zeit: ${this.formatBuildDate(this.loadedBuildInfo.buildDate) || 'unbekannt'}`;
    const serverBundle = `Server-Bundle: ${this.serverBundleId || 'nicht geprüft'}`;
    const fallbackInfo = `Fallback-Info: ${this.loadedBuildInfo.version} (${this.loadedBuildInfo.source})`;

    return `${loadedBundle}\n${loadedBuildDate}\n${serverBundle}\n${fallbackInfo}`;
  }

  private loadServerBundleInfo(): void {
    fetch(`index.html?t=${Date.now()}`, { cache: 'no-store' })
      .then(response => response.ok ? response.text() : undefined)
      .then((html?: string) => {
        if (!html) return;

        this.serverBundleId = this.extractMainBundleId(html);
        this.updateAvailable = !!this.loadedBundleId && !!this.serverBundleId && this.loadedBundleId !== this.serverBundleId;
      })
      .catch(() => {
        this.serverBundleId = undefined;
        this.updateAvailable = false;
      });
  }

  private getLoadedBundleId(): string | undefined {
    const scriptSources = Array.from(document.scripts)
      .map(script => script.src || script.getAttribute('src') || '')
      .filter(Boolean);

    for (const source of scriptSources) {
      const bundleId = this.extractMainBundleId(source);
      if (bundleId) return bundleId;
    }

    return undefined;
  }

  private extractMainBundleId(source: string): string | undefined {
    const startMarker = 'main-';
    const start = source.indexOf(startMarker);
    if (start < 0) return undefined;

    const afterStart = source.slice(start + startMarker.length);
    const end = afterStart.indexOf('.js');
    if (end <= 0) return undefined;

    return afterStart.slice(0, end).slice(0, 12);
  }

  private formatBuildDate(buildDate: string): string {
    if (!buildDate || buildDate === 'local') return '';

    const date = new Date(buildDate);
    if (Number.isNaN(date.getTime())) return buildDate;

    return date.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
