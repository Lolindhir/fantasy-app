import { Component, HostListener, OnInit, signal } from '@angular/core';
import { Router, RouterModule, RouterOutlet, NavigationEnd } from '@angular/router';
import { A11yModule } from "@angular/cdk/a11y";
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
  buildInfoDetailsOpen = false;

  readonly loadedBuildInfo = APP_BUILD_INFO;
  readonly loadedBundleId = this.getLoadedBundleId();
  serverBundleId?: string;
  serverBuildInfo?: AppBuildInfo;
  updateAvailable = false;

  @HostListener('window:scroll')
  onScroll(): void {
    if (document.documentElement.classList.contains('cdk-global-scrollblock')) {
      return;
    }

    this.isScrolled = window.scrollY > 10;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.menuOpen) return;

    const target = event.target as HTMLElement | null;
    if (!target) return;

    const clickedBurger = target.closest('.floating-burger');
    const clickedMenu = target.closest('.mobile-menu');

    if (clickedBurger || clickedMenu) return;

    this.closeMobileMenu();
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

          case '/standings':
            this.currentPage = 'Standings';
            break;

          case '/players':
            this.currentPage = 'Players';
            break;

          case '/drafts':
            this.currentPage = 'Drafts';
            break;

          case '/moves':
          case '/league-activity':
            this.currentPage = 'Moves';
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
    const loadedVersion = this.loadedBundleId || this.loadedBuildInfo.shortCommit || this.loadedBuildInfo.version;
    const buildDate = this.formatBuildDate(this.loadedBuildInfo.buildDate);
    const dateText = buildDate ? ` · ${buildDate}` : '';

    return `${loadedVersion}${dateText}`;
  }

  get buildInfoStatusLabel(): string {
    return this.updateAvailable ? 'Update verfügbar' : 'Aktuell / Server nicht neuer';
  }

  get loadedBundleLabel(): string {
    return this.loadedBundleId || 'unbekannt';
  }

  get loadedBuildDateLabel(): string {
    return this.formatBuildDate(this.loadedBuildInfo.buildDate) || 'unbekannt';
  }

  get serverBundleLabel(): string {
    return this.serverBundleId || 'nicht geprüft';
  }

  get serverBuildDateLabel(): string {
    return this.formatBuildDate(this.serverBuildInfo?.buildDate || '') || 'nicht geprüft';
  }

  get buildInfoTitle(): string {
    return [
      `Status: ${this.buildInfoStatusLabel}`,
      `Geladener Bundle: ${this.loadedBundleLabel}`,
      `Geladene Build-Zeit: ${this.loadedBuildDateLabel}`,
      `Server-Bundle: ${this.serverBundleLabel}`,
      `Server-Build-Zeit: ${this.serverBuildDateLabel}`
    ].join('\n');
  }

  toggleMobileMenu(event: Event): void {
    event.stopPropagation();
    this.menuOpen = !this.menuOpen;

    if (!this.menuOpen) {
      this.buildInfoDetailsOpen = false;
    }
  }

  closeMobileMenu(): void {
    this.menuOpen = false;
    this.buildInfoDetailsOpen = false;
  }

  toggleBuildInfoDetails(event: Event): void {
    event.stopPropagation();
    this.buildInfoDetailsOpen = !this.buildInfoDetailsOpen;
  }

  private loadServerBuildInfo(): void {
    const cacheBuster = Date.now();
    const indexRequest = fetch(`index.html?t=${cacheBuster}`, { cache: 'no-store' })
      .then(response => response.ok ? response.text() : undefined)
      .catch(() => undefined);

    const buildInfoRequest = fetch(`build-info.json?t=${cacheBuster}`, { cache: 'no-store' })
      .then(response => response.ok ? response.json() as Promise<AppBuildInfo> : undefined)
      .catch(() => undefined);

    Promise.all([indexRequest, buildInfoRequest])
      .then(([html, buildInfo]) => {
        if (html) {
          this.serverBundleId = this.extractMainBundleId(html);
        }

        if (buildInfo) {
          this.serverBuildInfo = buildInfo;
        }

        this.updateAvailable = this.hasServerUpdate();
      });
  }

  private hasServerUpdate(): boolean {
    const bundleChanged = !!this.loadedBundleId && !!this.serverBundleId && this.loadedBundleId !== this.serverBundleId;
    const buildDateChanged = !!this.loadedBuildInfo.buildDate
      && !!this.serverBuildInfo?.buildDate
      && this.loadedBuildInfo.buildDate !== this.serverBuildInfo.buildDate;

    return bundleChanged || buildDateChanged;
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
