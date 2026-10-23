/**
 * Central guard for player headshots: an NFL image CDN link without a width transformation serves the
 * original (about 0.5 to 5 MB). Display sizes in the app are small, so such links get a width.
 * Links that already carry a width and links of other hosts stay unchanged.
 */
export const PLAYER_PICTURE_DEFAULT_WIDTH = 160;

const NFL_IMAGE_URL = /^(https:\/\/static\.www\.nfl\.com\/image\/(?:upload|private)\/)([^/]+)\/(.+)$/;

export function sizedPlayerPicture(
  url: string | null | undefined,
  width: number = PLAYER_PICTURE_DEFAULT_WIDTH
): string | null {
  if (!url) {
    return null;
  }
  const match = NFL_IMAGE_URL.exec(url);
  if (!match) {
    return url;
  }
  const [, head, transform, rest] = match;
  if (transform.split(',').some(part => part.startsWith('w_'))) {
    return url;
  }
  return `${head}${transform},w_${width}/${rest}`;
}
