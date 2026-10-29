import { sizedPlayerPicture } from './player-picture.util';

describe('sizedPlayerPicture', () => {
  const unsized = 'https://static.www.nfl.com/image/upload/f_auto,q_auto/league/abc123';

  it('adds a width to an NFL image link without one', () => {
    expect(sizedPlayerPicture(unsized)).toBe('https://static.www.nfl.com/image/upload/f_auto,q_auto,w_160/league/abc123');
    expect(sizedPlayerPicture(unsized, 320)).toContain(',w_320/');
  });

  it('handles the private delivery type', () => {
    expect(sizedPlayerPicture(unsized.replace('/upload/', '/private/'))).toContain('/private/f_auto,q_auto,w_160/');
  });

  it('keeps sized links, other hosts and empty values unchanged', () => {
    const sized = 'https://static.www.nfl.com/image/upload/f_auto,q_auto,w_480/league/abc123';
    expect(sizedPlayerPicture(sized)).toBe(sized);
    expect(sizedPlayerPicture('https://a.espncdn.com/i/headshots/nfl/players/full/1.png')).toBe('https://a.espncdn.com/i/headshots/nfl/players/full/1.png');
    expect(sizedPlayerPicture(null)).toBeNull();
    expect(sizedPlayerPicture('')).toBeNull();
  });
});
