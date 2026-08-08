import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import type {
  DashboardBreakpoint,
  DashboardKey,
  DashboardLayoutResponse,
  DashboardLayoutUpdate,
} from './dashboard-layout.models';

@Injectable({ providedIn: 'root' })
export class DashboardLayoutService {
  private readonly api = inject(ApiService);

  getLayout(
    dashboardKey: DashboardKey,
    breakpoint: DashboardBreakpoint = 'desktop',
  ): Observable<DashboardLayoutResponse> {
    return this.api.get<DashboardLayoutResponse>(`/dashboard/${dashboardKey}/layout`, { breakpoint });
  }

  saveLayout(
    dashboardKey: DashboardKey,
    update: DashboardLayoutUpdate,
  ): Observable<DashboardLayoutResponse> {
    return this.api.put<DashboardLayoutResponse>(`/dashboard/${dashboardKey}/layout`, update);
  }

  resetLayout(
    dashboardKey: DashboardKey,
    breakpoint: DashboardBreakpoint = 'desktop',
  ): Observable<DashboardLayoutResponse> {
    return this.api.delete<DashboardLayoutResponse>(
      `/dashboard/${dashboardKey}/layout?breakpoint=${breakpoint}`,
    );
  }
}
