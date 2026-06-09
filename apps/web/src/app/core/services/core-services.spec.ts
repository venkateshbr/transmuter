import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { firstValueFrom, of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { LoadingService } from './loading.service';
import { ThemeService } from './theme.service';

describe('ApiService', () => {
  let http: {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    put: ReturnType<typeof vi.fn>;
    patch: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    http = {
      get: vi.fn(() => of({ ok: true })),
      post: vi.fn(() => of({ ok: true })),
      put: vi.fn(() => of({ ok: true })),
      patch: vi.fn(() => of({ ok: true })),
      delete: vi.fn(() => of({ ok: true })),
    };

    TestBed.configureTestingModule({
      providers: [ApiService, { provide: HttpClient, useValue: http }],
    });
  });

  it('should call each HTTP verb with the configured API path', () => {
    const service = TestBed.inject(ApiService);
    const form = new FormData();

    service.get('/items', { page: 2, active: true }).subscribe();
    service.getBlob('/export').subscribe();
    service.post('/items', { name: 'One' }).subscribe();
    service.postForm('/upload', form).subscribe();
    service.put('/items/1', { name: 'Two' }).subscribe();
    service.patch('/items/1', { name: 'Three' }).subscribe();
    service.delete('/items/1', { reason: 'test' }).subscribe();
    service.delete('/items/2').subscribe();

    expect(http.get).toHaveBeenCalledTimes(2);
    expect(http.post).toHaveBeenCalledWith(expect.stringContaining('/items'), { name: 'One' });
    expect(http.post).toHaveBeenCalledWith(expect.stringContaining('/upload'), form);
    expect(http.put).toHaveBeenCalledWith(expect.stringContaining('/items/1'), { name: 'Two' });
    expect(http.patch).toHaveBeenCalledWith(expect.stringContaining('/items/1'), { name: 'Three' });
    expect(http.delete).toHaveBeenCalledWith(expect.stringContaining('/items/1'), {
      body: { reason: 'test' },
    });
    expect(http.delete).toHaveBeenCalledWith(expect.stringContaining('/items/2'), undefined);
  });
});

describe('AuthService', () => {
  let api: {
    post: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
    patch: ReturnType<typeof vi.fn>;
  };
  let router: { navigate: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    localStorage.clear();
    api = {
      post: vi.fn(),
      get: vi.fn(() => of({ id: 'user-1', role: 'viewer', display_name: 'Viewer', must_change_password: false })),
      patch: vi.fn(() => of({ id: 'user-1', role: 'viewer', display_name: 'Updated', must_change_password: false })),
    };
    router = { navigate: vi.fn() };

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        { provide: ApiService, useValue: api },
        { provide: Router, useValue: router },
      ],
    });
  });

  it('should store access and refresh tokens on login and load profile', async () => {
    api.post.mockReturnValue(
      of({
        access_token: token({ exp: future(), user_metadata: { role: 'transformation_office' } }),
        refresh_token: 'refresh-1',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-1',
        tenant_id: 'tenant-1',
        role: 'transformation_office',
      })
    );

    const service = TestBed.inject(AuthService);
    await firstValueFrom(service.login('owner@example.com', 'Password123'));

    expect(localStorage.getItem('access_token')).toBeTruthy();
    expect(localStorage.getItem('refresh_token')).toBe('refresh-1');
    expect(service.isAuthenticated()).toBe(true);
    expect(service.user()?.display_name).toBe('Viewer');
    expect(api.get).toHaveBeenCalledWith('/auth/me');
  });

  it('should rotate sessions through the refresh endpoint', async () => {
    localStorage.setItem('refresh_token', 'refresh-1');
    api.post.mockReturnValue(
      of({
        access_token: token({ exp: future(), role: 'viewer' }),
        refresh_token: 'refresh-2',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-1',
        tenant_id: 'tenant-1',
        role: 'viewer',
      })
    );

    const service = TestBed.inject(AuthService);
    await firstValueFrom(service.refreshSession());

    expect(api.post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: 'refresh-1' });
    expect(localStorage.getItem('refresh_token')).toBe('refresh-2');
    expect(service.getRole()).toBe('viewer');
  });

  it('should update profile and submit password changes through auth endpoints', async () => {
    api.post.mockReturnValue(
      of({
        access_token: token({ exp: future(), role: 'viewer' }),
        refresh_token: 'refresh-after-password',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-1',
        tenant_id: 'tenant-1',
        role: 'viewer',
        status: 'active',
        must_change_password: false,
      })
    );
    const service = TestBed.inject(AuthService);

    await firstValueFrom(service.updateProfile({ display_name: 'Updated' }));
    expect(api.patch).toHaveBeenCalledWith('/auth/me', { display_name: 'Updated' });
    expect(service.user()?.display_name).toBe('Updated');

    await firstValueFrom(service.changePassword('CurrentPassword1!', 'NewPassword2026!', 'NewPassword2026!'));
    expect(api.post).toHaveBeenCalledWith('/auth/change-password', {
      current_password: 'CurrentPassword1!',
      new_password: 'NewPassword2026!',
      confirm_password: 'NewPassword2026!',
    });
    expect(localStorage.getItem('refresh_token')).toBe('refresh-after-password');
    expect(service.user()?.must_change_password).toBe(false);
  });

  it('should derive roles from JWT metadata and clear expired sessions', () => {
    const service = TestBed.inject(AuthService);
    service.user.set(null);
    localStorage.setItem('access_token', token({ exp: future(), user_metadata: { role: 'viewer' } }));

    expect(service.getRole()).toBe('viewer');
    expect(service.isTokenExpired()).toBe(false);

    localStorage.setItem('access_token', token({ exp: past(), role: 'transformation_office' }));
    service.clearExpiredSession();

    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('should navigate on logout and expired-session handling', () => {
    const service = TestBed.inject(AuthService);
    localStorage.setItem('access_token', token({ exp: future(), role: 'viewer' }));
    localStorage.setItem('refresh_token', 'refresh-1');

    service.logout();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);

    localStorage.setItem('access_token', token({ exp: future(), role: 'viewer' }));
    service.handleSessionExpired();
    service.handleSessionExpired();

    expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
      queryParams: { session: 'expired' },
    });
  });
});

describe('LoadingService', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    TestBed.configureTestingModule({ providers: [LoadingService] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should reveal, progress, and finish loading for requests', () => {
    const service = TestBed.inject(LoadingService);

    service.beginRequest();
    expect(service.active()).toBe(true);
    expect(service.visible()).toBe(false);
    expect(service.progress()).toBe(12);

    vi.advanceTimersByTime(160);
    expect(service.visible()).toBe(true);
    vi.advanceTimersByTime(220);
    expect(service.progress()).toBeGreaterThan(12);

    service.endRequest();
    expect(service.progress()).toBe(100);
    vi.advanceTimersByTime(180);

    expect(service.active()).toBe(false);
    expect(service.visible()).toBe(false);
    expect(service.progress()).toBe(0);
  });

  it('should cancel delayed reveal when navigation finishes quickly', () => {
    const service = TestBed.inject(LoadingService);

    service.beginNavigation();
    service.endNavigation();
    vi.advanceTimersByTime(200);

    expect(service.active()).toBe(false);
    expect(service.visible()).toBe(false);
    expect(service.progress()).toBe(0);
  });

  it('should choose and rotate creative loading messages', () => {
    const randomSpy = vi.spyOn(Math, 'random')
      .mockReturnValueOnce(0)
      .mockReturnValueOnce(0.99);
    const service = TestBed.inject(LoadingService);

    service.beginRequest();
    expect(service.message()).toBe('Preparing your workspace view...');

    vi.advanceTimersByTime(160);
    expect(service.visible()).toBe(true);

    vi.advanceTimersByTime(6500);
    expect(service.message()).toBe('Almost there. Aligning the moving parts...');

    service.endRequest();
    randomSpy.mockRestore();
  });
});

describe('ThemeService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: () => ({ matches: true }),
    });
    TestBed.configureTestingModule({ providers: [ThemeService] });
  });

  it('should initialize from system preference and persist toggles', () => {
    const service = TestBed.inject(ThemeService);

    expect(service.isDark()).toBe(true);
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    service.toggle();

    expect(service.isDark()).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});

function token(payload: Record<string, unknown>): string {
  return `header.${base64Url(JSON.stringify(payload))}.signature`;
}

function base64Url(value: string): string {
  return btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function future(): number {
  return Math.floor(Date.now() / 1000) + 3600;
}

function past(): number {
  return Math.floor(Date.now() / 1000) - 60;
}
