export type PositionColorKey = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'DEF';

export interface PositionColorStyle {
  readonly 'background-color': string;
  readonly color: string;
}

export const DEFAULT_POSITION_COLOR = '#555555';
export const DEFAULT_POSITION_TEXT_COLOR = '#FFFFFF';

export const DEFAULT_POSITION_COLOR_STYLE: PositionColorStyle = {
  'background-color': DEFAULT_POSITION_COLOR,
  color: DEFAULT_POSITION_TEXT_COLOR
};

export const POSITION_COLOR_STYLES: Readonly<Record<PositionColorKey, PositionColorStyle>> = {
  QB: { 'background-color': '#EC5F95', color: '#101A33' },
  RB: { 'background-color': '#70E8B8', color: '#101A33' },
  WR: { 'background-color': '#28BDF3', color: '#101A33' },
  TE: { 'background-color': '#F99C3E', color: '#101A33' },
  K: { 'background-color': '#9FA4FF', color: '#101A33' },
  DEF: { 'background-color': '#999999', color: '#FFFFFF' }
};

export const POSITION_COLORS = Object.fromEntries(
  Object.entries(POSITION_COLOR_STYLES).map(([position, style]) => [position, style['background-color']])
) as Readonly<Record<PositionColorKey, string>>;

export function isPositionColorKey(position: string): position is PositionColorKey {
  return Object.prototype.hasOwnProperty.call(POSITION_COLOR_STYLES, position);
}

export function getPositionStyle(position: string | null | undefined): PositionColorStyle {
  const normalizedPosition = position?.trim().toUpperCase();

  if (!normalizedPosition || !isPositionColorKey(normalizedPosition)) {
    return DEFAULT_POSITION_COLOR_STYLE;
  }

  return POSITION_COLOR_STYLES[normalizedPosition];
}

export function getPositionColor(position: string | null | undefined): string {
  return getPositionStyle(position)['background-color'];
}

export function getPositionTextColor(position: string | null | undefined): string {
  return getPositionStyle(position).color;
}
