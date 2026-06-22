import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { CreateInitiativeComponent } from './create-initiative.component';

describe('CreateInitiativeComponent', () => {
  function configure(apiResponses: Record<string, unknown>) {
    TestBed.configureTestingModule({
      imports: [CreateInitiativeComponent],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: () => null,
              },
            },
          },
        },
        {
          provide: AuthService,
          useValue: {
            getRole: () => 'transformation_office',
          },
        },
        {
          provide: ApiService,
          useValue: {
            get: (path: string) => of(apiResponses[path] ?? {}),
          },
        },
      ],
    });
    return TestBed.createComponent(CreateInitiativeComponent).componentInstance;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('allows creation when new financial engine setup is complete without legacy financial configuration', () => {
    const component = configure({
      '/workstreams': { data: [{ id: 'ws-1', name: 'Automation' }] },
      '/business-units': { data: [{ id: 'bu-1', name: 'Corporate' }] },
      '/admin/settings': { settings: { strategic_parameters: {} } },
      '/users': { data: [{ id: 'user-1', display_name: 'Transformation Lead' }] },
      '/financial-configuration': { groups: [], items: [] },
      '/financial-engine-configuration': {
        definitions: [{ id: 'metric-1', key: 'revenue_uplift' }],
        scenarios: [{ id: 'scenario-1', key: 'plan_base' }],
        cost_categories: [{ id: 'cost-1', key: 'implementation' }],
        settings: {},
      },
      '/governance/stage-gates': [{ id: 'gate-1', gate_number: 1 }],
      '/admin/governance/gate-criteria': [{ id: 'criterion-1', gate_number: 1 }],
      '/admin/setup-status': { complete: true, completed: 7, total: 7, checks: [] },
    });

    expect(component.isCreationBlocked()).toBe(false);
  });

  it('blocks creation when new financial engine cost categories are missing', () => {
    const component = configure({
      '/workstreams': { data: [{ id: 'ws-1', name: 'Automation' }] },
      '/business-units': { data: [{ id: 'bu-1', name: 'Corporate' }] },
      '/admin/settings': { settings: { strategic_parameters: {} } },
      '/users': { data: [{ id: 'user-1', display_name: 'Transformation Lead' }] },
      '/financial-configuration': { groups: [], items: [] },
      '/financial-engine-configuration': {
        definitions: [{ id: 'metric-1', key: 'revenue_uplift' }],
        scenarios: [{ id: 'scenario-1', key: 'plan_base' }],
        cost_categories: [],
        settings: {},
      },
      '/governance/stage-gates': [{ id: 'gate-1', gate_number: 1 }],
      '/admin/governance/gate-criteria': [{ id: 'criterion-1', gate_number: 1 }],
      '/admin/setup-status': { complete: true, completed: 7, total: 7, checks: [] },
    });

    expect(component.isCreationBlocked()).toBe(true);
  });
});
