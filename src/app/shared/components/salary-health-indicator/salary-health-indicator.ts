import { Component, Input } from '@angular/core';
import type { SalaryHealthStatus } from '../../utils/team-salary.util';

@Component({
  selector: 'app-salary-health-indicator',
  standalone: true,
  templateUrl: './salary-health-indicator.html',
  styleUrl: './salary-health-indicator.scss'
})
export class SalaryHealthIndicatorComponent {
  @Input({ required: true }) status!: SalaryHealthStatus;
  @Input() compact = false;

  get label(): string {
    switch (this.status) {
      case 'healthy': return 'Cap Healthy';
      case 'watch': return 'Cap Watch';
      case 'over': return 'Over Cap';
    }
  }
}
