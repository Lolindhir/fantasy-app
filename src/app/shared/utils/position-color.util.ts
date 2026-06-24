export type PositionColorKey = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';

export const DEFAULT_POSITION_COLOR = '#555555';

export const POSITION_COLORS: Readonly<Record<PositionColorKey, string>> = {
  QB: '#EF74A2',
  RB: '#90F2CB',
  WR: '#56C9F8',
  TE: '#FEAE59',
  K: '#B6B9FF',
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
