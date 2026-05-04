import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./features/marketing/home/home.component').then(m => m.HomeComponent),
  },
  {
    path: 'get-started',
    loadComponent: () =>
      import('./features/marketing/get-started/get-started.component').then(m => m.GetStartedComponent),
  },
  {
    path: 'subscription/success',
    loadComponent: () =>
      import('./features/marketing/subscription-success/subscription-success.component').then(m => m.SubscriptionSuccessComponent),
  },
  {
    path: 'auth/login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: 'platform',
        canActivate: [authGuard],
        data: { roles: ['platform_admin'] },
        loadComponent: () =>
          import('./features/platform/platform-console.component').then(m => m.PlatformConsoleComponent),
      },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
      },
      {
        path: 'initiatives',
        children: [
          {
            path: 'pipeline',
            loadComponent: () =>
              import('./features/initiatives/pipeline/pipeline.component').then(m => m.PipelineComponent),
          },
          {
            path: 'matrix',
            loadComponent: () =>
              import('./features/initiatives/matrix/matrix.component').then(m => m.MatrixComponent),
          },
          {
            path: 'new',
            loadComponent: () =>
              import('./features/initiatives/create/create-initiative.component').then(m => m.CreateInitiativeComponent),
          },
          {
            path: ':id/edit',
            loadComponent: () =>
              import('./features/initiatives/create/create-initiative.component').then(m => m.CreateInitiativeComponent),
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./features/initiatives/detail/detail.component').then(m => m.InitiativeDetailComponent),
          },
          { path: '', redirectTo: 'pipeline', pathMatch: 'full' },
        ],
      },
      {
        path: 'progress',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/progress/milestones/milestones.component').then(m => m.MilestonesComponent),
          },
          {
            path: 'roadmap',
            loadComponent: () =>
              import('./features/progress/roadmap/roadmap.component').then(m => m.RoadmapComponent),
          },
          {
            path: 'action-items',
            loadComponent: () =>
              import('./features/progress/action-items/action-items.component').then(m => m.ActionItemsComponent),
          },
          {
            path: 'status-updates',
            loadComponent: () =>
              import('./features/progress/status-updates/status-updates.component').then(m => m.StatusUpdatesComponent),
          },
          {
            path: 'dependencies',
            loadComponent: () =>
              import('./features/progress/dependencies/dependencies.component').then(m => m.DependenciesComponent),
          },
        ],
      },
      {
        path: 'meetings',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./features/meetings/list/meetings-list.component').then(m => m.MeetingsListComponent),
          },
          {
            path: 'sessions/:id',
            loadComponent: () =>
              import('./features/meetings/live-session/live-session.component').then(m => m.LiveSessionComponent),
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./features/meetings/detail/meeting-detail.component').then(m => m.MeetingDetailComponent),
          },
        ],
      },
      {
        path: 'people',
        loadComponent: () =>
          import('./features/people/people.component').then(m => m.PeopleComponent),
      },
      {
        path: 'pmo',
        children: [
          {
            path: 'governance',
            loadComponent: () =>
              import('./features/pmo/governance/governance.component').then(m => m.GovernanceComponent),
          },
          {
            path: 'risks',
            loadComponent: () =>
              import('./features/pmo/risks/risks.component').then(m => m.RisksComponent),
          },
          {
            path: 'kpis',
            loadComponent: () =>
              import('./features/pmo/kpis/kpis.component').then(m => m.KPIsComponent),
          },
          {
            path: 'ai-insights',
            loadComponent: () =>
              import('./features/pmo/ai-insights/ai-insights.component').then(m => m.AIInsightsComponent),
          },
        ],
      },
      {
        path: 'admin',
        canActivate: [authGuard],
        data: { roles: ['transformation_office'] },
        loadComponent: () =>
          import('./features/admin/admin.component').then(m => m.AdminComponent),
      },
    ]
  },
  { path: '**', redirectTo: 'dashboard' },
];
