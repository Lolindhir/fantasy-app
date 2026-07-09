import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import type { Player } from '../../../core/models/fantasy.models';
import { PositionStylePipe } from '../../pipes/position-style.pipe';
import { PlayerDetailDialogComponent } from '../player-detail-dialog/player-detail-dialog';

@Component({
  selector: 'app-draft-pick-player-card',
  standalone: true,
  imports: [CommonModule, MatDialogModule, PositionStylePipe],
  template: `
    <button
      class="draft-pick-player-card"
      type="button"
      [title]="player.Name"
      (click)="openPlayerDetail()"
    >
      <img
        *ngIf="player.Picture"
        class="draft-pick-player-picture"
        [src]="player.Picture"
        [alt]="player.Name"
      />
      <span
        *ngIf="!player.Picture"
        class="draft-pick-player-picture draft-pick-player-picture--fallback"
      >
        {{ player.Position }}
      </span>

      <span class="draft-pick-player-main">
        <strong>{{ player.NameShort || player.Name }}</strong>
        <span class="draft-pick-player-meta">
          <span
            class="draft-pick-player-position"
            [ngStyle]="player.Position | positionStyle"
          >
            {{ player.Position }}
          </span>
          <img
            *ngIf="player.TeamNFL?.Logo"
            class="draft-pick-player-nfl-logo"
            [src]="player.TeamNFL.Logo"
            alt=""
          />
          <span>{{ player.TeamNFL?.Abv }}</span>
        </span>
      </span>
    </button>
  `,
  styles: [`
    :host {
      display: block;
      min-width: 0;
    }

    .draft-pick-player-card {
      display: grid;
      grid-template-columns: 34px minmax(0, 1fr);
      gap: 8px;
      align-items: center;
      width: 100%;
      padding: 0;
      border: none;
      background: transparent;
      color: inherit;
      font: inherit;
      text-align: left;
      cursor: pointer;
    }

    .draft-pick-player-picture {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      object-fit: cover;
      background: #e5e7eb;
    }

    .draft-pick-player-picture--fallback {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #334155;
      font-size: 0.68rem;
      font-weight: 800;
    }

    .draft-pick-player-main {
      display: flex;
      min-width: 0;
      flex-direction: column;
      gap: 3px;
    }

    .draft-pick-player-main strong {
      overflow: hidden;
      color: #1f2937;
      font-weight: 900;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .draft-pick-player-meta {
      display: flex;
      align-items: center;
      gap: 5px;
      color: #6b7280;
      font-size: 0.74rem;
      font-weight: 800;
      line-height: 1;
      white-space: nowrap;
    }

    .draft-pick-player-position {
      padding: 2px 5px;
      border-radius: 7px;
      font-size: 0.68rem;
      font-weight: 900;
      line-height: 1.15;
    }

    .draft-pick-player-nfl-logo {
      width: 18px;
      height: 18px;
      object-fit: contain;
    }

    @media (max-width: 700px) {
      .draft-pick-player-card {
        display: flex;
        width: 100%;
        height: 100%;
        align-items: center;
        justify-content: flex-start;
        gap: 7px;
        text-align: left;
      }

      .draft-pick-player-picture {
        width: 30px;
        height: 30px;
        flex: 0 0 30px;
        order: 0;
      }

      .draft-pick-player-main {
        flex: 0 1 auto;
        min-width: 0;
        justify-content: center;
        order: 0;
      }

      .draft-pick-player-main strong {
        font-size: 0.82rem;
      }

      .draft-pick-player-meta {
        justify-content: center;
        gap: 4px;
        font-size: 0.7rem;
      }

      .draft-pick-player-position {
        padding: 1px 5px;
        font-size: 0.64rem;
      }

      .draft-pick-player-nfl-logo {
        width: 16px;
        height: 16px;
      }
    }
  `]
})
export class DraftPickPlayerCardComponent {
  private dialog = inject(MatDialog);

  @Input({ required: true }) player!: Player;

  openPlayerDetail(): void {
    this.dialog.open(PlayerDetailDialogComponent, {
      data: this.player,
      width: '800px',
      maxHeight: '90vh',
      panelClass: 'player-dialog'
    });
  }
}
