import { NgFor, NgIf } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { MarkdownModule } from 'ngx-markdown';
import { catchError, distinctUntilChanged, map, of, switchMap } from 'rxjs';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { publicPhilosophyMarkdown } from './handbook-content.util';

interface HandbookPage {
  id: string;
  label: string;
}

interface HandbookGroup {
  title: string;
  pages: readonly HandbookPage[];
}

const HANDBOOK_GROUPS: readonly HandbookGroup[] = [
  {
    title: 'Einstieg',
    pages: [
      { id: 'Overview', label: 'Übersicht' },
      { id: 'league-philosophy', label: 'Liga-Philosophie' }
    ]
  },
  {
    title: 'Liga-Regeln',
    pages: [
      { id: 'Salary_Explanation', label: 'Salary & Salary Cap' },
      { id: 'Offseason_Flow', label: 'Offseason Infografik' },
      { id: 'Offseason_Schedule', label: 'Offseason Regeln' },
      { id: 'Draft_Waiver_Order', label: 'Draft & Waiver Regeln' }
    ]
  },
  {
    title: 'Daten & Analysen',
    pages: [
      { id: 'Projections_Explanation', label: 'Prognosen & Siegchancen' }
    ]
  }
];

@Component({
  selector: 'app-about',
  imports: [NgFor, NgIf, MarkdownModule, SharedMaterialImports],
  standalone: true,
  templateUrl: './about.html',
  styleUrl: './about.scss'
})
export class AboutComponent implements OnInit {
  readonly groups = HANDBOOK_GROUPS;
  readonly tabs = HANDBOOK_GROUPS.flatMap(group => group.pages);
  markdownText = '';
  selectedTab = 'Overview';
  menuOpen = false;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private readonly http: HttpClient,
    private readonly route: ActivatedRoute,
    private readonly router: Router
  ) {}

  get mobileSelectionLabel(): string {
    if (this.selectedTab === 'Overview') return 'Themen wählen';
    return this.tabs.find(tab => tab.id === this.selectedTab)?.label ?? 'Themen wählen';
  }

  ngOnInit(): void {
    this.route.queryParamMap.pipe(
      map(params => params.get('section') ?? 'Overview'),
      map(section => this.tabs.some(tab => tab.id === section) ? section : 'Overview'),
      distinctUntilChanged(),
      switchMap(section => {
        this.selectedTab = section;
        this.menuOpen = false;
        this.markdownText = '';
        return this.http.get(`docs/${section}.md`, { responseType: 'text' }).pipe(
          map(content => section === 'league-philosophy' ? publicPhilosophyMarkdown(content) : content),
          catchError(() => of('# Inhalt nicht verfügbar\n\nDie Erklärung konnte nicht geladen werden.'))
        );
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(content => this.markdownText = content);
  }

  toggleMenu(): void {
    this.menuOpen = !this.menuOpen;
  }

  closeMenu(): void {
    this.menuOpen = false;
  }

  selectTab(section: string): void {
    if (!this.tabs.some(tab => tab.id === section)) return;
    this.closeMenu();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { section: section === 'Overview' ? null : section },
      queryParamsHandling: 'merge'
    });
  }
}
