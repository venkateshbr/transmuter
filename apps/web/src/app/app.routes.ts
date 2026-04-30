import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
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
    ],
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./features/admin/admin.component').then(m => m.AdminComponent),
  },
  { path: '**', redirectTo: '' },
];
