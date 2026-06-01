import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

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

  if (authService.user()?.must_change_password && state.url !== '/auth/change-password') {
    router.navigate(['/auth/change-password']);
    return false;
  }

  const allowedRoles = route.data?.['roles'] as string[] | undefined;
  if (allowedRoles?.length && !allowedRoles.includes(authService.getRole() ?? '')) {
    router.navigate([authService.getRole() === 'platform_admin' ? '/platform' : '/dashboard']);
    return false;
  }

  return true;
};
