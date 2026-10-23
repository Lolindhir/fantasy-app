import { Pipe, PipeTransform } from '@angular/core';

import { sizedPlayerPicture } from '../utils/player-picture.util';

@Pipe({
  name: 'playerPicture',
  standalone: true,
  pure: true
})
export class PlayerPicturePipe implements PipeTransform {
  transform(url: string | null | undefined, width?: number): string | null {
    return sizedPlayerPicture(url, width);
  }
}
