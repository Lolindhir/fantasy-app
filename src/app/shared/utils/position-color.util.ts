export type PositionColorKey = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';

export const DEFAULT_POSITION_COLOR = '#555555';

export const POSITION_COLORS: Readonly<Record<PositionColorKey, string>> = {
  QB: '#EC5F95',
  RB: '#70E8B8',
  WR: '#28BDF3',
  TE: '#F99C3E',
  K: '#9FA4FF',
  DEF: '#999999'
};

export function isPositionColorKey(position: string): position is PositionColorKey {
  return Object.prototype.hasOwnProperty.call(POSITION_COLORS, position);
}

export function getPositionColor(position: string | null | undefined): string {
  const normalizedPosition = position?.trim().toUpperCase();

  if (!normalizedPosition || !isPositionColorKey(normalizedPosition)) {
    return DEFAULT_POSITION_COLOR;
  }

  return POSITION_COLORS[normalizedPosition];
}
