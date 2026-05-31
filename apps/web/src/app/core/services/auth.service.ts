import { Injectable, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

interface AuthResponse {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
  user_id: string;
  tenant_id: string;
  role: string;
}

export interface UserProfile {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  display_name: string | null;
  title: string | null;
  status: string;
  onboarding_completed: boolean;
}

type CurrentAuthUser = Partial<UserProfile> & { id?: string; tenant_id?: string; role?: string };

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private sessionExpiryHandled = false;

  readonly user = signal<CurrentAuthUser | null>(null);
  readonly isAuthenticated = signal<boolean>(this.hasValidStoredToken());

  login(email: string, password: string): Observable<AuthResponse> {
    return this.api.post<AuthResponse>('/auth/login', { email, password }).pipe(
      tap((resp) => {
        localStorage.setItem('access_token', resp.access_token);
        this.storeRefreshToken(resp.refresh_token);
        this.sessionExpiryHandled = false;
        this.user.set({
          id: resp.user_id,
          tenant_id: resp.tenant_id,
          role: resp.role,
        });
        this.isAuthenticated.set(true);
        this.loadProfile().subscribe();
      })
    );
  }

  refreshSession(): Observable<AuthResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    return this.api.post<AuthResponse>('/auth/refresh', { refresh_token: refreshToken }).pipe(
      tap((resp) => {
        localStorage.setItem('access_token', resp.access_token);
        this.storeRefreshToken(resp.refresh_token);
        this.sessionExpiryHandled = false;
        this.user.set({
          id: resp.user_id,
          tenant_id: resp.tenant_id,
          role: resp.role,
        });
        this.isAuthenticated.set(true);
      })
    );
  }

  loadProfile(): Observable<UserProfile> {
    return this.api.get<UserProfile>('/auth/me').pipe(
      tap(profile => this.user.set(profile))
    );
  }

  updateProfile(patch: Pick<Partial<UserProfile>, 'display_name' | 'title' | 'onboarding_completed'>): Observable<UserProfile> {
    return this.api.patch<UserProfile>('/auth/me', patch).pipe(
      tap(profile => this.user.set(profile))
    );
  }

  changePassword(currentPassword: string, newPassword: string, confirmPassword: string): Observable<{ status: string }> {
    return this.api.post<{ status: string }>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
  }

  logout() {
    this.clearSession();
    this.router.navigate(['/auth/login']);
  }

  clearExpiredSession() {
    if (!this.isTokenExpired()) return;
    this.clearSession();
  }

  handleSessionExpired() {
    if (this.sessionExpiryHandled) return;
    this.sessionExpiryHandled = true;
    this.clearSession();
    this.router.navigate(['/auth/login'], { queryParams: { session: 'expired' } });
  }

  private clearSession(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.isAuthenticated.set(false);
    this.user.set(null);
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getRole(): string | null {
    if (this.isTokenExpired()) return null;
    const profileRole = this.user()?.role;
    if (profileRole) return profileRole;

    const token = this.getToken();
    if (!token) return null;

    try {
      const payload = this.tokenPayload(token);
      const metadataRole = payload?.['user_metadata'];
      if (
        metadataRole &&
        typeof metadataRole === 'object' &&
        'role' in metadataRole &&
        typeof metadataRole.role === 'string'
      ) {
        return metadataRole.role;
      }
      return typeof payload?.['role'] === 'string' ? payload['role'] : null;
    } catch {
      return null;
    }
  }

  isTokenExpired(token = this.getToken()): boolean {
    if (!token) return true;
    const exp = this.tokenPayload(token)?.['exp'];
    if (typeof exp !== 'number') return true;
    return exp <= Math.floor(Date.now() / 1000);
  }

  private hasValidStoredToken(): boolean {
    return !this.isTokenExpired(localStorage.getItem('access_token'));
  }

  private storeRefreshToken(refreshToken?: string | null): void {
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  private tokenPayload(token: string): Record<string, unknown> | null {
    try {
      const payload = token.split('.')[1] ?? '';
      const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
      const padded = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=');
      return JSON.parse(atob(padded));
    } catch {
      return null;
    }
  }
}
