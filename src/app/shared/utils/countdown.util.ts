export const SECOND_MS = 1_000;
export const MINUTE_MS = 60 * SECOND_MS;
export const HOUR_MS = 60 * MINUTE_MS;
export const DAY_MS = 24 * HOUR_MS;

export function formatCountdownDuration(msLeft: number): string {
  const remainingMs = Number.isFinite(msLeft) ? Math.max(0, msLeft) : 0;

  if (remainingMs >= 7 * DAY_MS) {
    const days = Math.floor(remainingMs / DAY_MS);
    return formatDays(days);
  }

  if (remainingMs >= DAY_MS) {
    const days = Math.floor(remainingMs / DAY_MS);
    const hours = Math.floor((remainingMs % DAY_MS) / HOUR_MS);
    return `${formatDays(days)} ${hours} h`;
  }

  if (remainingMs >= HOUR_MS) {
    const hours = Math.floor(remainingMs / HOUR_MS);
    const minutes = Math.floor((remainingMs % HOUR_MS) / MINUTE_MS);
    return `${hours} h ${minutes} min`;
  }

  if (remainingMs >= MINUTE_MS) {
    const minutes = Math.floor(remainingMs / MINUTE_MS);
    const seconds = Math.floor((remainingMs % MINUTE_MS) / SECOND_MS);
    return `${minutes} min ${seconds} s`;
  }

  return `${Math.floor(remainingMs / SECOND_MS)} s`;
}

function formatDays(days: number): string {
  return `${days} ${days === 1 ? 'day' : 'days'}`;
}
