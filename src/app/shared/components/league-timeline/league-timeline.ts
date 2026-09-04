import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { League } from '../../../core/models/league.models';

interface LeagueTimelineDraft {
  name: string;
  statusClass: 'live' | 'upcoming' | 'completed';
  startDisplay: string | null;
}

interface LeagueTimelineItem {
  icon: string;
  label: string;
  value: string;
  detail: string | null;
}

interface LeagueTimelineView {
  primary: LeagueTimelineItem;
  secondary: LeagueTimelineItem | null;
}

@Component({
  selector: 'app-league-timeline',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './league-timeline.html',
  styleUrl: './league-timeline.scss'
})
export class LeagueTimelineComponent {
  @Input({ required: true }) league!: League;
  @Input() drafts: LeagueTimelineDraft[] = [];

  get timeline(): LeagueTimelineView | null {
    const now = new Date();
    const kickoff = this.parseDate(this.league.SeasonKickoff);
    const capDeadline = this.parseDate(this.league.CapDeadline);
    const nextWaiverRun = this.parseDate(this.league.NextWaiverRun);
    const currentWeek = this.getCurrentWeek();
    const playoffItem = this.league.PlayoffStartWeek > 0
      ? this.buildWeekItem('Playoffs start', this.league.PlayoffStartWeek, '🏆')
      : null;
    const tradeDeadlineItem = this.league.TradeDeadlineWeek !== null
      && this.league.TradeDeadlineWeek <= this.league.LastLeagueWeek
      && this.league.TradeDeadlineWeek > currentWeek
      ? this.buildWeekItem('Trade deadline', this.league.TradeDeadlineWeek, '🤝')
      : null;
    const waiverItem = nextWaiverRun && nextWaiverRun.getTime() > now.getTime()
      ? this.buildDateItem('Next waiver run', nextWaiverRun, '🔄', now, true)
      : null;

    if (this.league.Status === 'Off-Season') {
      if (capDeadline && capDeadline.getTime() > now.getTime()) {
        return {
          primary: this.buildDateItem('Cap deadline', capDeadline, '⏱️', now),
          secondary: this.getScheduledDraftItem() ?? this.getKickoffItem(kickoff, now)
        };
      }

      const scheduledDraft = this.getScheduledDraftItem();
      if (scheduledDraft) {
        return { primary: scheduledDraft, secondary: this.getKickoffItem(kickoff, now) };
      }

      const kickoffItem = this.getKickoffItem(kickoff, now);
      return kickoffItem ? { primary: kickoffItem, secondary: null } : null;
    }

    if (this.league.Status === 'Draft-Season') {
      const liveDraft = this.getLiveDraftItem();
      if (liveDraft) {
        return { primary: liveDraft, secondary: this.getKickoffItem(kickoff, now) };
      }

      const scheduledDraft = this.getScheduledDraftItem();
      if (scheduledDraft) {
        return { primary: scheduledDraft, secondary: this.getKickoffItem(kickoff, now) };
      }

      const kickoffItem = this.getKickoffItem(kickoff, now);
      return kickoffItem ? { primary: kickoffItem, secondary: null } : null;
    }

    if (this.league.Status === 'Pre-Season') {
      const kickoffItem = this.getKickoffItem(kickoff, now);
      return kickoffItem ? { primary: kickoffItem, secondary: tradeDeadlineItem ?? playoffItem } : null;
    }

    if (this.league.Status === 'In-Season') {
      if (waiverItem) {
        return { primary: waiverItem, secondary: tradeDeadlineItem ?? playoffItem };
      }

      if (tradeDeadlineItem) {
        return { primary: tradeDeadlineItem, secondary: playoffItem };
      }

      return playoffItem ? { primary: playoffItem, secondary: null } : null;
    }

    if (this.league.Status === 'Playoffs') {
      return {
        primary: this.buildWeekItem('League final', this.league.LastLeagueWeek, '🏆'),
        secondary: null
      };
    }

    return null;
  }

  private getCurrentWeek(): number {
    return this.league.CurrentWeek
      ?? Math.min(Math.max(this.league.FinalScoredWeek + 1, 1), this.league.LastLeagueWeek);
  }

  private getLiveDraftItem(): LeagueTimelineItem | null {
    const draft = this.drafts.find(candidate => candidate.statusClass === 'live');
    if (!draft) return null;

    return {
      icon: '🟣',
      label: draft.name,
      value: 'Live now',
      detail: 'Draft in progress'
    };
  }

  private getScheduledDraftItem(): LeagueTimelineItem | null {
    const draft = this.drafts.find(candidate =>
      candidate.statusClass === 'upcoming'
      && !!candidate.startDisplay
      && candidate.startDisplay !== 'not scheduled'
    );
    if (!draft?.startDisplay) return null;

    return {
      icon: '📋',
      label: draft.name,
      value: draft.startDisplay,
      detail: 'Scheduled draft'
    };
  }

  private getKickoffItem(kickoff: Date | null, now: Date): LeagueTimelineItem | null {
    if (!kickoff || kickoff.getTime() <= now.getTime()) return null;
    return this.buildDateItem('Season kickoff', kickoff, '🏈', now);
  }

  private buildDateItem(
    label: string,
    date: Date,
    icon: string,
    now: Date,
    includeLocalTime = false
  ): LeagueTimelineItem {
    return {
      icon,
      label,
      value: this.formatCountdown(date.getTime() - now.getTime()),
      detail: includeLocalTime ? this.formatLocalDateTime(date) : this.formatDate(date)
    };
  }

  private buildWeekItem(label: string, week: number, icon: string): LeagueTimelineItem {
    return {
      icon,
      label,
      value: `Week ${week}`,
      detail: null
    };
  }

  private parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;

    const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? `${value}T23:59:59Z`
      : value;
    const date = new Date(normalized);

    return Number.isNaN(date.getTime()) ? null : date;
  }

  private formatDate(date: Date): string {
    try {
      return new Intl.DateTimeFormat(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        timeZone: this.league.LeagueTimeZone || 'UTC'
      }).format(date);
    } catch {
      return new Intl.DateTimeFormat(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        timeZone: 'UTC'
      }).format(date);
    }
  }

  private formatLocalDateTime(date: Date): string {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
    }).format(date);
  }

  private formatCountdown(msLeft: number): string {
    const minuteMs = 60_000;
    const hourMs = 60 * minuteMs;
    const dayMs = 24 * hourMs;

    if (msLeft >= dayMs) {
      const totalHours = Math.floor(msLeft / hourMs);
      const days = Math.floor(totalHours / 24);
      const hours = totalHours % 24;
      return days < 4
        ? `${days} ${days === 1 ? 'day' : 'days'} ${hours} h`
        : `${days} ${days === 1 ? 'day' : 'days'}`;
    }

    const totalMinutes = Math.max(1, Math.floor(msLeft / minuteMs));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours === 0) return `${minutes} min`;
    if (minutes === 0) return `${hours} h`;
    return `${hours} h ${minutes} min`;
  }
}