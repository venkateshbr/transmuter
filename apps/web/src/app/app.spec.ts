import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { App } from './app';
import { ApiService } from './core/services/api.service';
import { AuthService } from './core/services/auth.service';
import { LoadingService } from './core/services/loading.service';
import { ThemeService } from './core/services/theme.service';

@Component({ standalone: true, template: '' })
class EmptyRouteComponent {}

describe('App', () => {
  const authUser = signal<any | null>({ display_name: 'Test User', role: 'transformation_office' });
  const isAuthenticated = signal(true);
  const loadingVisible = signal(false);
  const loadingProgress = signal(0);
  const loadingMessage = signal('Coffee-compatible loading in progress.');
  let role = 'transformation_office';
  let apiPostCalls: unknown[] = [];
  let logoutCalled = false;
  let themeToggleCalled = false;

  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }),
    });
  });

  beforeEach(() => {
    localStorage.clear();
    role = 'transformation_office';
    apiPostCalls = [];
    logoutCalled = false;
    themeToggleCalled = false;
    authUser.set({ display_name: 'Test User', role: 'transformation_office' });
    isAuthenticated.set(true);
    loadingVisible.set(false);
    loadingProgress.set(0);
    loadingMessage.set('Coffee-compatible loading in progress.');
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideRouter([
          { path: 'dashboard', component: EmptyRouteComponent },
          { path: 'meetings', component: EmptyRouteComponent },
          { path: 'platform', component: EmptyRouteComponent },
          { path: 'profile', component: EmptyRouteComponent },
          { path: 'auth/login', component: EmptyRouteComponent },
        ]),
        {
          provide: AuthService,
          useValue: {
            user: authUser,
            isAuthenticated,
            getRole: () => role,
            logout: () => {
              logoutCalled = true;
            },
          },
        },
        {
          provide: ThemeService,
          useValue: {
            isDark: signal(false),
            toggle: () => {
              themeToggleCalled = true;
            },
          },
        },
        {
          provide: LoadingService,
          useValue: {
            visible: loadingVisible,
            progress: loadingProgress,
            message: loadingMessage,
            beginNavigation: () => undefined,
            endNavigation: () => undefined,
          },
        },
        {
          provide: ApiService,
          useValue: {
            post: (...args: unknown[]) => {
              apiPostCalls.push(args);
              return of({
                response: 'Two initiatives are at risk.',
                sources: [{ label: 'Portfolio', source_type: 'initiatives' }],
              });
            },
          },
        },
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render the application shell', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('main')).toBeTruthy();
  });

  it('should render tenant chrome, navigation, and loading state', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/dashboard');
    loadingVisible.set(true);
    loadingProgress.set(42);

    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('header')).toBeTruthy();
    expect(compiled.textContent).toContain('Dashboard');
    expect(compiled.textContent).not.toContain('Control Tower');
    expect(compiled.textContent).toContain('Financials');
    expect(compiled.textContent).toContain('Workspace sync');
    expect(compiled.textContent).toContain('Coffee-compatible loading in progress.');
    expect((fixture.componentInstance as any).homeLink()).toBe('/dashboard');
    expect((fixture.componentInstance as any).canManageTenant()).toBe(true);
  });

  it('should expose financial and report submenu paths in the shell nav model', () => {
    const fixture = TestBed.createComponent(App);
    const navItems = (fixture.componentInstance as any).navItems;

    const financials = navItems.find((item: any) => item.label === 'Financials');
    expect(financials.children?.map((child: any) => child.path)).toEqual([
      '/financials',
      '/financials/bankable-plan',
      '/financials/benefit-tracking',
      '/financials/waterline',
    ]);

    const reports = navItems.find((item: any) => item.label === 'Reports');
    expect(reports.children?.map((child: any) => child.path)).toEqual([
      '/reports/control-tower',
    ]);
  });

  it('should render platform-only navigation for platform admins', async () => {
    const router = TestBed.inject(Router);
    role = 'platform_admin';
    authUser.set({ display_name: 'Platform Admin', role });
    await router.navigateByUrl('/platform');

    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Platform');
    expect(compiled.textContent).not.toContain('Financials');
    expect((fixture.componentInstance as any).homeLink()).toBe('/platform');
    expect((fixture.componentInstance as any).isPlatformAdmin()).toBe(true);
  });

  it('should detect overflow routes and hide chrome on public pages', async () => {
    const router = TestBed.inject(Router);
    const fixture = TestBed.createComponent(App);

    await router.navigateByUrl('/meetings');
    expect((fixture.componentInstance as any).isOverflowRouteActive()).toBe(true);
    expect((fixture.componentInstance as any).showAppChrome()).toBe(true);

    await router.navigateByUrl('/auth/login');
    expect((fixture.componentInstance as any).showAppChrome()).toBe(false);
  });

  it('should send assistant messages and append sourced responses', () => {
    const fixture = TestBed.createComponent(App);
    const component = fixture.componentInstance as any;

    component.aiQueryText.set('Show me at-risk initiatives');
    component.sendMessage();

    expect(apiPostCalls).toEqual([['/ai/chat', { query: 'Show me at-risk initiatives' }]]);
    expect(component.aiQueryText()).toBe('');
    expect(component.aiLoading()).toBe(false);
    expect(component.messages().length).toBe(2);
    expect(component.messages()[1].sources[0].label).toBe('Portfolio');
  });

  it('should ignore empty assistant submissions and busy submissions', () => {
    const fixture = TestBed.createComponent(App);
    const component = fixture.componentInstance as any;

    component.sendMessage();
    component.aiQueryText.set('Summarize the portfolio');
    component.aiLoading.set(true);
    component.sendMessage();

    expect(apiPostCalls).toEqual([]);
    expect(component.messages()).toEqual([]);
  });

  it('should open account menu and call logout from shell controls', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/dashboard');

    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    compiled.querySelector<HTMLButtonElement>('button[aria-label="Toggle theme"]')?.click();
    compiled.querySelector<HTMLButtonElement>('button[aria-label="Open user menu"]')?.click();
    fixture.detectChanges();
    expect(compiled.textContent).toContain('Profile');
    compiled.querySelector<HTMLButtonElement>('button[aria-label="Logout"]')?.click();

    expect(themeToggleCalled).toBe(true);
    expect(logoutCalled).toBe(true);
  });
});
