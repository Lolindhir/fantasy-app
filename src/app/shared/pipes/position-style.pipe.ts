import { Pipe, PipeTransform } from '@angular/core';

import { getPositionStyle, type PositionColorStyle } from '../utils/position-color.util';

@Pipe({
  name: 'positionStyle',
  standalone: true,
  pure: true
})
export class PositionStylePipe implements PipeTransform {
  transform(position: string | null | undefined): PositionColorStyle {
    return getPositionStyle(position);
  }
}
