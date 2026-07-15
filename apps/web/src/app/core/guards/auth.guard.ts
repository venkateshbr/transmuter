import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../services/auth.service';
import type { OperatingModelPermission } from '../rbac/operating-model-permissions';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    router.navigate(['/auth/login']);
    return false;
  }

  if (authService.isTokenExpired()) {
    authService.handleSessionExpired();
    return false;
  }

  const authorize = (): boolean => {
    if (authService.user()?.must_change_password && state.url !== '/auth/change-password') {
      router.navigate(['/auth/change-password']);
      return false;
    }

    const allowedRoles = route.data?.['roles'] as string[] | undefined;
    if (allowedRoles?.length && !allowedRoles.includes(authService.getRole() ?? '')) {
      router.navigate([authService.getRole() === 'platform_admin' ? '/platform' : '/dashboard']);
      return false;
    }

    const requiredPermissions = route.data?.['permissions'] as OperatingModelPermission[] | undefined;
    if (requiredPermissions?.length && !requiredPermissions.some(item => authService.hasPermission(item))) {
      router.navigate([authService.getRole() === 'platform_admin' ? '/platform' : '/dashboard']);
      return false;
    }

    return true;
  };

  if (authService.user()) {
    return authorize();
  }

  return authService.ensureProfile().pipe(
    map(() => authorize()),
    catchError(() => {
      authService.handleSessionExpired();
      return of(false);
    }),
  );
};
