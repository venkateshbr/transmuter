export type DashboardKey = 'operational' | 'financial';
export type DashboardBreakpoint = 'desktop' | 'tablet';
export type DashboardWidgetSize = 'small' | 'medium' | 'wide' | 'full';

export interface DashboardWidgetLayout {
  widget_key: string;
  order: number;
  size: DashboardWidgetSize;
  visible: boolean;
}

export interface DashboardLayoutResponse {
  dashboard_key: DashboardKey;
  breakpoint: DashboardBreakpoint;
  source: 'personal' | 'tenant' | 'system';
  layout_version: number;
  widgets: DashboardWidgetLayout[];
}

export interface DashboardLayoutUpdate {
  breakpoint: DashboardBreakpoint;
  widgets: DashboardWidgetLayout[];
  publish_as_tenant_default?: boolean;
  role_key?: string;
}
