import {
  AfterViewInit,
  Directive,
  ElementRef,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  inject
} from '@angular/core';

@Directive({
  selector: '[appFitText]',
  standalone: true
})
export class FitTextDirective implements AfterViewInit, OnChanges, OnDestroy {
  private readonly elementRef = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly ngZone = inject(NgZone);

  private resizeObserver: ResizeObserver | null = null;
  private animationFrameId: number | null = null;
  private initialized = false;

  @Input({ required: true }) appFitText = '';
  @Input() fitTextMinSize = 12;
  @Input() fitTextMaxSize = 16;

  ngAfterViewInit(): void {
    this.initialized = true;

    this.ngZone.runOutsideAngular(() => {
      const resizeTarget = this.elementRef.nativeElement.parentElement
        ?? this.elementRef.nativeElement;

      if (typeof ResizeObserver !== 'undefined') {
        this.resizeObserver = new ResizeObserver(() => this.scheduleFit());
        this.resizeObserver.observe(resizeTarget);
      } else {
        window.addEventListener('resize', this.handleWindowResize);
      }

      this.scheduleFit();

      if (document.fonts) {
        void document.fonts.ready.then(() => this.scheduleFit());
      }
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.initialized) return;

    if (
      changes['appFitText']
      || changes['fitTextMinSize']
      || changes['fitTextMaxSize']
    ) {
      this.scheduleFit();
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    window.removeEventListener('resize', this.handleWindowResize);

    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
    }
  }

  private readonly handleWindowResize = (): void => {
    this.scheduleFit();
  };

  private scheduleFit(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
    }

    this.animationFrameId = requestAnimationFrame(() => {
      this.animationFrameId = null;
      this.fitText();
    });
  }

  private fitText(): void {
    const element = this.elementRef.nativeElement;
    const minSize = Math.min(this.fitTextMinSize, this.fitTextMaxSize);
    const maxSize = Math.max(this.fitTextMinSize, this.fitTextMaxSize);

    if (!element.isConnected || element.clientWidth <= 0 || element.clientHeight <= 0) {
      return;
    }

    element.style.fontSize = `${maxSize}px`;

    if (this.fits(element)) {
      return;
    }

    let lowerBound = minSize;
    let upperBound = maxSize;

    for (let index = 0; index < 8; index += 1) {
      const candidate = (lowerBound + upperBound) / 2;
      element.style.fontSize = `${candidate}px`;

      if (this.fits(element)) {
        lowerBound = candidate;
      } else {
        upperBound = candidate;
      }
    }

    element.style.fontSize = `${lowerBound.toFixed(2)}px`;
  }

  private fits(element: HTMLElement): boolean {
    const tolerance = 0.5;

    return element.scrollWidth <= element.clientWidth + tolerance
      && element.scrollHeight <= element.clientHeight + tolerance;
  }
}
