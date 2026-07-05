import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { map } from 'rxjs/operators';

import type { DraftPick, FantasyTeam, League, RawDraft } from '../../../core/models/fantasy.models';
import { DataService } from '../../../core/services/data.service';
import {
  compareDraftPickCollectionsByStrength,
  getBestDraftPick,
  getDraftCapitalAbbreviation
} from '../../utils/draft-capital.util';

interface DraftCapitalColumn {
  draftKey: string;
  label: string;
  fullLabel: string;
}

interface DraftCapitalCount {
  draftKey: string;
  count: number;
}

interface DraftCapitalRow {
  team: FantasyTeam;
  teamName: string;
  teamAbbr: string;
  draftCounts: DraftCapitalCount[];
  bestPick: string;
  bestAvailablePick: string;
  hasBestAvailablePick: boolean;
  sortPicks: DraftPick[];
}

interface DraftCapitalViewModel {
  columns: DraftCapitalColumn[];
  gridTemplate: string;
  rows: DraftCapitalRow[];
}

@Component({
  selector: 'app-draft-capital-overview',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section *ngIf="vm$ | async as vm" class="draft-dashboard-card">
      <h2>Draft Capital</h2>

      <div
        class="draft-capital-header"
        [style.grid-template-columns]="vm.gridTemplate"
      >
        <span class="draft-capital-cell draft-capital-cell--team">Team</span>
        <span
          *ngFor="let column of vm.columns"
          class="draft-capital-cell draft-capital-cell--numeric"
          [title]="column.fullLabel"
        >{{ column.label }}</span>
        <span class="draft-capital-cell draft-capital-cell--pick">
          <span class="draft-capital-header-full">Best Pick</span>
          <span class="draft-capital-header-short">Best</span>
        </span>
        <span class="draft-capital-cell draft-capital-cell--pick">
          <span class="draft-capital-header-full">Best Available</span>
          <span class="draft-capital-header-short">Avail.</span>
        </span>
      </div>

      <div
        *ngFor="let row of vm.rows"
        class="draft-capital-row"
        [style.grid-template-columns]="vm.gridTemplate"
      >
        <div class="draft-capital-cell draft-capital-team">
          <img *ngIf="row.team.Avatar" [src]="row.team.Avatar" alt="" />
          <span class="draft-capital-team-name">{{ row.teamName }}</span>
          <span class="draft-capital-team-abbr">{{ row.teamAbbr }}</span>
        </div>
        <div
          *ngFor="let draftCount of row.draftCounts"
          class="draft-capital-cell draft-capital-cell--numeric draft-capital-count"
        >{{ draftCount.count }}</div>
        <div class="draft-capital-cell draft-capital-cell--pick draft-capital-pick-chip draft-capital-pick-chip--best">{{ row.bestPick }}</div>
        <div
          class="draft-capital-cell draft-capital-cell--pick draft-capital-pick-chip draft-capital-pick-chip--available"
          [class.draft-capital-pick-chip--empty]="!row.hasBestAvailablePick"
        >{{ row.bestAvailablePick }}</div>
      </div>
    </section>
  `,
  styles: [`
    :host {
      display: contents;
    }

    .draft-dashboard-card {
      padding: 13px 14px;
      margin: 0 5px 12px;
      border: 1px solid rgba(148, 163, 184, 0.35);
      border-radius: 16px;
      background: #fff;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    }

    .draft-dashboard-card h2 {
      margin: 0 0 10px;
      font-size: 1.05rem;
      font-weight: 800;
    }

    .draft-capital-header,
    .draft-capital-row {
      display: grid;
      align-items: center;
      gap: 4px;
    }

    .draft-capital-header {
      padding-bottom: 6px;
      color: #64748b;
      font-size: 0.62rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }

    .draft-capital-cell {
      min-width: 0;
    }

    .draft-capital-cell--numeric {
      justify-self: end;
      text-align: right;
    }

    .draft-capital-cell--pick {
      justify-self: stretch;
      text-align: center;
    }

    .draft-capital-header-full {
      display: none;
    }

    .draft-capital-header-short {
      display: inline;
    }

    .draft-capital-row {
      min-height: 34px;
      padding: 4px 0;
      border-top: 1px solid rgba(148, 163, 184, 0.18);
    }

    .draft-capital-team {
      display: flex;
      align-items: center;
      gap: 7px;
      font-weight: 700;
    }

    .draft-capital-team img {
      width: 24px;
      height: 24px;
      border-radius: 8px;
      flex: 0 0 auto;
    }

    .draft-capital-team-name,
    .draft-capital-team-abbr {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .draft-capital-team-name {
      display: none;
    }

    .draft-capital-team-abbr {
      display: inline;
    }

    .draft-capital-count {
      font-variant-numeric: tabular-nums;
      font-weight: 700;
      white-space: nowrap;
    }

    .draft-capital-pick-chip {
      display: flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
      padding: 1px 5px;
      border-radius: 999px;
      background: #f1f5f9;
      font-weight: 800;
      font-size: 0.78rem;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    .draft-capital-pick-chip--best {
      color: #4f46e5;
    }

    .draft-capital-pick-chip--available {
      color: #15803d;
    }

    .draft-capital-pick-chip--empty {
      color: #94a3b8;
    }

    @media (min-width: 520px) {
      .draft-capital-header,
      .draft-capital-row {
        gap: 8px;
      }

      .draft-capital-header {
        font-size: 0.72rem;
        letter-spacing: 0.03em;
      }

      .draft-capital-header-full {
        display: inline;
      }

      .draft-capital-header-short {
        display: none;
      }

      .draft-capital-team-name {
        display: inline;
      }

      .draft-capital-team-abbr {
        display: none;
      }

      .draft-capital-pick-chip {
        padding: 2px 8px;
        font-size: 0.82rem;
      }
    }
  `]
})
export class DraftCapitalOverviewComponent {
  private dataService = inject(DataService);

  vm$ = this.dataService.getLeagueWithPlayers().pipe(
    map(({ league, teams, drafts }: { league: League; teams: FantasyTeam[]; drafts: RawDraft[] }) => {
      if (league.Status !== 'Draft-Season') return null;

      const seasonDrafts = this.getSeasonDrafts(drafts, league.Season);
      if (seasonDrafts.length === 0) return null;

      const columns = seasonDrafts.map(draft => ({
        draftKey: draft.DraftKey,
        label: getDraftCapitalAbbreviation(draft),
        fullLabel: draft.DisplayDraftKey
      }));
      const rows = this.buildRows(teams, seasonDrafts, columns);

      return {
        columns,
        gridTemplate: this.buildGridTemplate(columns.length),
        rows
      } satisfies DraftCapitalViewModel;
    })
  );

  private getSeasonDrafts(drafts: RawDraft[], season: string): RawDraft[] {
    return drafts
      .filter(draft => draft.Season === season)
      .sort((a, b) => a.DraftNo - b.DraftNo);
  }

  private buildRows(
    teams: FantasyTeam[],
    drafts: RawDraft[],
    columns: DraftCapitalColumn[]
  ): DraftCapitalRow[] {
    const season = drafts[0]?.Season ?? '';
    const draftByKey = new Map(drafts.map(draft => [draft.DraftKey, draft]));
    const draftKeys = new Set(columns.map(column => column.draftKey));
    const maxRound = this.getMaxRound(teams, season);

    return teams
      .map(team => {
        const sortPicks = (team.DraftPicks ?? [])
          .filter(pick => pick.Season === season && draftKeys.has(pick.DraftKey));
        const bestPick = getBestDraftPick(sortPicks);
        const bestAvailablePick = getBestDraftPick(
          sortPicks.filter(pick => this.isDraftPickAvailable(pick))
        );

        return {
          team,
          teamName: team.Team ?? team.Owner,
          teamAbbr: this.getTeamAbbreviation(team),
          draftCounts: columns.map(column => ({
            draftKey: column.draftKey,
            count: sortPicks.filter(pick => pick.DraftKey === column.draftKey).length
          })),
          bestPick: bestPick ? this.formatBestPick(bestPick, draftByKey) : '—',
          bestAvailablePick: bestAvailablePick ? this.formatBestPick(bestAvailablePick, draftByKey) : '—',
          hasBestAvailablePick: !!bestAvailablePick,
          sortPicks
        };
      })
      .sort((a, b) => {
        const strengthDiff = compareDraftPickCollectionsByStrength(a.sortPicks, b.sortPicks, maxRound);
        if (strengthDiff !== 0) return strengthDiff;
        return a.teamName.localeCompare(b.teamName, 'en', { sensitivity: 'base' });
      });
  }

  private buildGridTemplate(columnCount: number): string {
    const draftColumns = columnCount > 0
      ? `repeat(${columnCount}, minmax(34px, max-content))`
      : '';

    return ['minmax(0, 1fr)', draftColumns, '70px', 'minmax(72px, max-content)']
      .filter(Boolean)
      .join(' ');
  }

  private formatBestPick(pick: DraftPick, draftByKey: Map<string, RawDraft>): string {
    const draft = pick.Draft ?? draftByKey.get(pick.DraftKey);
    const draftLabel = draft ? getDraftCapitalAbbreviation(draft) : pick.DraftKey;

    return `${draftLabel} ${pick.DisplayPick}`;
  }

  private isDraftPickAvailable(pick: DraftPick): boolean {
    return pick.Status !== 'Picked'
      && !pick.PlayerID
      && !pick.PlayerName
      && pick.SleeperPickNo === null;
  }

  private getTeamAbbreviation(team: FantasyTeam): string {
    const abbreviation = team.TeamAbbr?.trim();
    if (abbreviation) return abbreviation;

    const displayName = (team.Team ?? team.Owner).trim();
    return displayName
      .split(/\s+/)
      .map(part => part.charAt(0).toUpperCase())
      .join('')
      .slice(0, 3) || '?';
  }

  private getMaxRound(teams: FantasyTeam[], season: string): number {
    const rounds = teams
      .flatMap(team => team.DraftPicks ?? [])
      .filter(pick => pick.Season === season)
      .map(pick => Number(pick.Round) || 0)
      .filter(round => round > 0);

    return rounds.length ? Math.max(...rounds) : 1;
  }
}
