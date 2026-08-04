import { TestBed } from '@angular/core/testing';
import type { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Router } from '@angular/router';
import { firstValueFrom, isObservable, of, type Observable } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService, type UserProfile } from '../services/auth.service';
import { authGuard } from './auth.guard';

describe('authGuard', () => {
  const profile: UserProfile = {
    id: 'user-1',
    tenant_id: 'tenant-1',
    email: 'admin@example.com',
    role: 'tenant_admin',
    display_name: 'Tenant Admin',
    title: null,
    status: 'active',
    onboarding_completed: true,
    must_change_password: false,
  };
  let currentUser: UserProfile | null;
  let auth: {
    isAuthenticated: ReturnType<typeof vi.fn>;
    isTokenExpired: ReturnType<typeof vi.fn>;
    user: ReturnType<typeof vi.fn>;
    ensureProfile: ReturnType<typeof vi.fn>;
    getRole: ReturnType<typeof vi.fn>;
    hasPermission: ReturnType<typeof vi.fn>;
    handleSessionExpired: ReturnType<typeof vi.fn>;
  };
  let router: { navigate: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    currentUser = null;
    auth = {
      isAuthenticated: vi.fn(() => true),
      isTokenExpired: vi.fn(() => false),
      user: vi.fn(() => currentUser),
      ensureProfile: vi.fn(() => {
        currentUser = profile;
        return of(profile);
      }),
      getRole: vi.fn(() => currentUser?.role ?? 'authenticated'),
      hasPermission: vi.fn(() => currentUser?.role === 'tenant_admin'),
      handleSessionExpired: vi.fn(),
    };
    router = { navigate: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
  });

  it('waits for the canonical profile before evaluating a cold-load permission', async () => {
    const route = {
      data: { permissions: ['users.manage'] },
    } as unknown as ActivatedRouteSnapshot;
    const state = { url: '/people' } as RouterStateSnapshot;

    const result = TestBed.runInInjectionContext(() => authGuard(route, state));
    expect(isObservable(result)).toBe(true);
    await expect(firstValueFrom(result as Observable<boolean>)).resolves.toBe(true);
    expect(auth.ensureProfile).toHaveBeenCalledOnce();
    expect(auth.hasPermission).toHaveBeenCalledWith('users.manage');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('redirects only after the hydrated profile lacks the required permission', async () => {
    const viewer = { ...profile, role: 'viewer' };
    auth.ensureProfile.mockImplementation(() => {
      currentUser = viewer;
      return of(viewer);
    });
    auth.hasPermission.mockReturnValue(false);
    const route = {
      data: { permissions: ['users.manage'] },
    } as unknown as ActivatedRouteSnapshot;
    const state = { url: '/people' } as RouterStateSnapshot;

    const result = TestBed.runInInjectionContext(() => authGuard(route, state));
    await expect(firstValueFrom(result as Observable<boolean>)).resolves.toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });

  it('denies the platform guide library to hydrated tenant users', async () => {
    currentUser = profile;
    const route = {
      data: { roles: ['platform_admin'] },
    } as unknown as ActivatedRouteSnapshot;
    const state = { url: '/platform/guides' } as RouterStateSnapshot;

    const result = TestBed.runInInjectionContext(() => authGuard(route, state));

    expect(result).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });

  it('allows the platform guide library for platform administrators', async () => {
    currentUser = { ...profile, role: 'platform_admin' };
    const route = {
      data: { roles: ['platform_admin'] },
    } as unknown as ActivatedRouteSnapshot;
    const state = { url: '/platform/guides' } as RouterStateSnapshot;

    const result = TestBed.runInInjectionContext(() => authGuard(route, state));

    expect(result).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });
});
