import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('access_token');
  const isPublicRequest = isAuthOptionalRequest(req.url);

  if (token && isTokenExpired(token) && isPublicRequest) {
    clearSession();
    return next(req);
  }

  if (token && isTokenExpired(token)) {
    handleSessionExpired();
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
          handleSessionExpired();
        }
        return throwError(() => error);
      })
    );
  }

  return next(req).pipe(
    catchError(error => {
      if (error instanceof HttpErrorResponse && error.status === 401 && !isPublicRequest) {
        handleSessionExpired();
      }
      return throwError(() => error);
    })
  );
};

function isTokenExpired(token: string): boolean {
  const exp = tokenPayload(token)?.['exp'];
  if (typeof exp !== 'number') return true;
  return exp <= Math.floor(Date.now() / 1000);
}

function tokenPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1] ?? '';
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=');
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

function clearSession(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

function handleSessionExpired(): void {
  clearSession();
  if (requestPath(window.location.href) !== '/auth/login') {
    window.location.assign('/auth/login?session=expired');
  }
}

function isAuthOptionalRequest(url: string): boolean {
  const path = requestPath(url);
  return [
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/accept-invite',
    '/billing/config',
    '/billing/checkout-session',
    '/billing/checkout-completion',
  ].some(publicPath => path.endsWith(publicPath));
}

function requestPath(url: string): string {
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url.split('?')[0] ?? url;
  }
}
