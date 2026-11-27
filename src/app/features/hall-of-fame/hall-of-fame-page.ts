import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { catchError, forkJoin, map, of, switchMap } from 'rxjs';

import { DataService } from '../../core/services/data.service';
import { AchievementBannerComponent } from '../../shared/components/achievement-banner/achievement-banner';
import { AllTimeOverviewComponent } from '../../shared/components/all-time-overview/all-time-overview';
import { HallOfFameComponent } from '../../shared/components/hall-of-fame/hall-of-fame';
import { HallOfFameChampionDialogComponent } from './hall-of-fame-champion-dialog';
import { TeamSeasonService } from '../../shared/services/team-season.service';
import { GENERIC_CHAMPIONSHIP_RING_SRC } from '../../shared/utils/championship.util';
import { buildHallOfFameChampions, buildHallOfFameSections, type HallOfFameChampion } from '../../shared/utils/hall-of-fame-view.util';
import { buildLeagueLegacy } from '../../shared/utils/league-standings-view.util';

/**
 * Global Hall of Fame (Issue #1621): champions of every season in the identity of their season, league legacy, all-time bests,
 * player award legends and the all-time standings. Not season dependent. Display only: every value comes from the generated
 * standings, league records, award history and team identity files; nothing is counted here.
 */
@Component({
  selector: 'app-hall-of-fame-page',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf, AchievementBannerComponent, AllTimeOverviewComponent, HallOfFameComponent],
  templateUrl: './hall-of-fame-page.html',
  styleUrl: './hall-of-fame-page.scss'
})
export class HallOfFamePageComponent {
  private readonly dataService = inject(DataService);
  private readonly dialog = inject(MatDialog);
  private readonly teamSeasons = inject(TeamSeasonService);
  private readonly failedRings = new Set<string>();

  readonly championEmblemSrc = GENERIC_CHAMPIONSHIP_RING_SRC;

  /** Unavailable optional files (team identity, league records, awards) never block the page. */
  readonly vm$ = forkJoin({
    league: this.dataService.getLeagueSummary(),
    records: this.dataService.getLeagueRecords().pipe(catchError(() => of(null))),
    playerAwards: this.dataService.getPlayerAwardHistory().pipe(
      catchError(() => of(null)),
      switchMap(awards => {
        const ids = Object.values(awards?.Leaders ?? {}).flatMap(leaders => (leaders ?? []).map(leader => leader.PlayerID));
        return this.dataService.getPlayerIdentitySummaries(ids).pipe(
          // Award facts and historical portraits remain available without current identity enrichment.
          catchError(() => of([])),
          map(players => ({ awards, players }))
        );
      })
    ),
    lookup: this.teamSeasons.getLookup().pipe(catchError(() => of(null)))
  }).pipe(
    map(({ league, records, playerAwards: { awards, players }, lookup }) => ({
      champions: buildHallOfFameChampions(league, lookup),
      sections: buildHallOfFameSections(league, league.Teams, records, awards, players, lookup),
      allTime: buildLeagueLegacy(league, league.Teams)
    }))
  );

  ringSrc(champion: HallOfFameChampion): string {
    return this.failedRings.has(champion.season) ? this.championEmblemSrc : champion.ringSrc;
  }

  /** A season without its own ring artwork falls back to the generic ring. */
  onRingError(champion: HallOfFameChampion): void {
    this.failedRings.add(champion.season);
  }

  /** Opens the detail of a past champion; the dialog traps focus and closes with Escape or the Close button. */
  openChampion(champion: HallOfFameChampion): void {
    this.dialog.open(HallOfFameChampionDialogComponent, {
      data: { champion, emblemSrc: this.championEmblemSrc, ringSrc: this.ringSrc(champion) },
      width: '320px',
      maxWidth: '92vw',
      autoFocus: 'dialog'
    });
  }

  trackSeason = (_: number, champion: HallOfFameChampion): string => champion.season;
}
