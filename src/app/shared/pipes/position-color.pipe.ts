import { Pipe, PipeTransform } from '@angular/core';

import { getPositionColor } from '../utils/position-color.util';

@Pipe({
  name: 'positionColor',
  standalone: true,
  pure: true
})
export class PositionColorPipe implements PipeTransform {
  transform(position: string | null | undefined): string {
    return getPositionColor(position);
  }
}
