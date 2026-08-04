import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { PlatformGuidesComponent } from './platform-guides.component';

describe('PlatformGuidesComponent', () => {
  const items = [
    {
      slug: 'tenant-onboarding',
      category: 'Start here',
      title: 'Tenant Onboarding User Guide',
      summary: 'Configure a tenant and operate the portfolio.',
      reviewed_at: '2026-08-04',
    },
    {
      slug: 'acme-detailed-demo',
      category: 'Demo guides',
      title: 'ACME Detailed Demo Guide',
      summary: 'Present the complete transformation workflow.',
      reviewed_at: '2026-08-04',
    },
  ];
  let getCalls: string[];
  let navigateCalls: unknown[][];

  beforeEach(async () => {
    getCalls = [];
    navigateCalls = [];
    await TestBed.configureTestingModule({
      imports: [PlatformGuidesComponent],
      providers: [
        {
          provide: ApiService,
          useValue: {
            get: (path: string) => {
              getCalls.push(path);
              if (path === '/platform/guides') return of({ items });
              const item = items.find(candidate => path.endsWith(candidate.slug)) || items[0];
              return of({ ...item, html: '<h1>Source title</h1><h2>Workflow</h2><table><tr><td>Evidence</td></tr></table>' });
            },
          },
        },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => null } } },
        },
        {
          provide: Router,
          useValue: {
            navigate: (...args: unknown[]) => {
              navigateCalls.push(args);
              return Promise.resolve(true);
            },
          },
        },
      ],
    }).compileComponents();
  });

  it('loads and formats the canonical published guide library', () => {
    const fixture = TestBed.createComponent(PlatformGuidesComponent);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(getCalls).toEqual(['/platform/guides', '/platform/guides/tenant-onboarding']);
    expect(compiled.textContent).toContain('User guides and tutorials');
    expect(compiled.textContent).toContain('Tenant Onboarding User Guide');
    expect(compiled.querySelector('[data-testid="published-guide"] h2')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="published-guide"] table')).toBeTruthy();
  });

  it('filters guides and opens the selected canonical source', async () => {
    const fixture = TestBed.createComponent(PlatformGuidesComponent);
    fixture.detectChanges();
    const component = fixture.componentInstance as any;

    component.query.set('demo');
    fixture.detectChanges();
    expect(component.filteredGuides().map((item: any) => item.slug)).toEqual(['acme-detailed-demo']);

    component.openGuide('acme-detailed-demo');
    fixture.detectChanges();
    await fixture.whenStable();
    expect(getCalls.at(-1)).toBe('/platform/guides/acme-detailed-demo');
    expect(navigateCalls.at(-1)?.[0]).toEqual(['/platform/guides', 'acme-detailed-demo']);
    expect(component.guide().title).toBe('ACME Detailed Demo Guide');
  });
});
