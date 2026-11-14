import { NgFor } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { MarkdownModule } from 'ngx-markdown';
import { catchError, distinctUntilChanged, map, of, switchMap } from 'rxjs';
import { SharedMaterialImports } from '../../shared/shared-material-imports';
import { publicPhilosophyMarkdown } from './handbook-content.util';

const HANDBOOK_TABS = [
  { id: 'Overview', label: 'Übersicht' },
  { id: 'league-philosophy', label: 'Liga-Philosophie' },
  { id: 'Salary_Explanation', label: 'Salary & Salary Cap' },
  { id: 'Projections_Explanation', label: 'Prognosen & Siegchancen' },
  { id: 'Offseason_Flow', label: 'Offseason Infografik' },
  { id: 'Offseason_Schedule', label: 'Offseason Regeln' },
  { id: 'Draft_Waiver_Order', label: 'Draft & Waiver Regeln' }
] as const;

@Component({
  selector: 'app-about',
  imports: [NgFor, MarkdownModule, SharedMaterialImports],
  standalone: true,
  templateUrl: './about.html',
  styleUrl: './about.scss'
})
export class AboutComponent implements OnInit {
  readonly tabs = HANDBOOK_TABS;
  markdownText = '';
  selectedTab = 'Overview';
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private readonly http: HttpClient,
    private readonly route: ActivatedRoute,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.route.queryParamMap.pipe(
      map(params => params.get('section') ?? 'Overview'),
      map(section => this.tabs.some(tab => tab.id === section) ? section : 'Overview'),
      distinctUntilChanged(),
      switchMap(section => {
        this.selectedTab = section;
        this.markdownText = '';
        return this.http.get(`docs/${section}.md`, { responseType: 'text' }).pipe(
          map(content => section === 'league-philosophy' ? publicPhilosophyMarkdown(content) : content),
          catchError(() => of('# Inhalt nicht verfügbar\n\nDie Erklärung konnte nicht geladen werden.'))
        );
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(content => this.markdownText = content);
  }

  selectTab(section: string): void {
    if (!this.tabs.some(tab => tab.id === section)) return;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { section: section === 'Overview' ? null : section },
      queryParamsHandling: 'merge'
    });
  }
}
