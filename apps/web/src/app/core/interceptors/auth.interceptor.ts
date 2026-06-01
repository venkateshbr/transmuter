import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();
  const isPublicRequest = isAuthOptionalRequest(req.url);

  if (token && authService.isTokenExpired() && isPublicRequest) {
    authService.clearExpiredSession();
    return next(req);
  }

  if (token && authService.isTokenExpired()) {
    authService.handleSessionExpired();
    return throwError(() => new HttpErrorResponse({
      status: 401,
      statusText: 'Session expired',
      url: req.url,
    }));
  }

  if (token) {
    const authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(authReq).pipe(
      catchError(error => {
        if (error instanceof HttpErrorResponse && error.status === 401 && !isPublicRequest) {
          authService.handleSessionExpired();
        }
        return throwError(() => error);
      })
    );
  }

  return next(req).pipe(
    catchError(error => {
      if (error instanceof HttpErrorResponse && error.status === 401 && !isPublicRequest) {
        authService.handleSessionExpired();
      }
      return throwError(() => error);
    })
  );
};

function isAuthOptionalRequest(url: string): boolean {
  const path = requestPath(url);
  return [
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/billing/config',
    '/billing/checkout-session',
  ].some(publicPath => path.endsWith(publicPath));
}

function requestPath(url: string): string {
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url.split('?')[0] ?? url;
  }
}
