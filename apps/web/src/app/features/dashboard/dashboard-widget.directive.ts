import { Directive, Input, TemplateRef, inject } from '@angular/core';
import type { DashboardWidgetSize } from './dashboard-layout.models';

@Directive({
  selector: 'ng-template[dashboardWidget]',
  standalone: true,
})
export class DashboardWidgetDirective {
  readonly template = inject(TemplateRef<unknown>);

  @Input({ required: true, alias: 'dashboardWidget' }) key = '';
  @Input() widgetTitle = '';
  @Input() widgetDescription = '';
  @Input() widgetRequired = false;
  @Input() widgetDefaultSize: DashboardWidgetSize = 'medium';
}
