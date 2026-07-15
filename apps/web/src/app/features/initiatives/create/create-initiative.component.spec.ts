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
            hasPermission: (permission: string) => permission === 'initiatives.manage_all',
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
    return TestBed.createComponent(CreateInitiativeComponent);
  }

  afterEach(() => TestBed.resetTestingModule());

  it('allows creation when operational setup is complete without financial engine configuration', () => {
    const fixture = configure({
      '/workstreams': { data: [{ id: 'ws-1', name: 'Automation' }] },
      '/business-units': { data: [{ id: 'bu-1', name: 'Corporate' }] },
      '/admin/settings': { settings: { strategic_parameters: {} } },
      '/users': { data: [{ id: 'user-1', display_name: 'Transformation Lead' }] },
      '/governance/stage-gates': [{ id: 'gate-1', gate_number: 1 }],
      '/admin/governance/gate-criteria': [{ id: 'criterion-1', gate_number: 1 }],
      '/admin/setup-status': {
        complete: false,
        completed: 6,
        total: 7,
        checks: [
          { key: 'organization', complete: true },
          { key: 'business_units', complete: true },
          { key: 'workstreams', complete: true },
          { key: 'financial_config', complete: false },
          { key: 'stage_gates', complete: true },
          { key: 'gate_criteria', complete: true },
          { key: 'users', complete: true },
        ],
      },
    });

    expect(fixture.componentInstance.isCreationBlocked()).toBe(false);
  });

  it('blocks creation when stage gate criteria are missing', () => {
    const fixture = configure({
      '/workstreams': { data: [{ id: 'ws-1', name: 'Automation' }] },
      '/business-units': { data: [{ id: 'bu-1', name: 'Corporate' }] },
      '/admin/settings': { settings: { strategic_parameters: {} } },
      '/users': { data: [{ id: 'user-1', display_name: 'Transformation Lead' }] },
      '/governance/stage-gates': [{ id: 'gate-1', gate_number: 1 }],
      '/admin/governance/gate-criteria': [],
      '/admin/setup-status': {
        complete: false,
        completed: 6,
        total: 7,
        checks: [
          { key: 'organization', complete: true },
          { key: 'business_units', complete: true },
          { key: 'workstreams', complete: true },
          { key: 'financial_config', complete: true },
          { key: 'stage_gates', complete: true },
          { key: 'gate_criteria', complete: false },
          { key: 'users', complete: true },
        ],
      },
    });

    expect(fixture.componentInstance.isCreationBlocked()).toBe(true);
  });

  it('renders upload and template download as independent controls', () => {
    const fixture = configure({
      '/workstreams': { data: [] },
      '/business-units': { data: [] },
      '/admin/settings': { settings: { strategic_parameters: {} } },
      '/users': { data: [] },
      '/governance/stage-gates': [],
      '/admin/governance/gate-criteria': [],
      '/admin/setup-status': { complete: true, checks: [] },
    });

    fixture.detectChanges();
    const upload = fixture.nativeElement.querySelector(
      'button[aria-label="Choose Excel upload"]',
    );
    const download = fixture.nativeElement.querySelector(
      'button[aria-label="Download blank initiative template"]',
    );

    expect(upload).toBeTruthy();
    expect(download).toBeTruthy();
    expect(download.closest('[role="button"]')).toBeNull();
  });
});
