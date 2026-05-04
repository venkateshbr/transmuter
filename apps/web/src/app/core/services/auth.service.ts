import { Injectable, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  tenant_id: string;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  readonly user = signal<any | null>(null);
  readonly isAuthenticated = signal<boolean>(!!localStorage.getItem('access_token'));

  login(email: string, password: string): Observable<AuthResponse> {
    return this.api.post<AuthResponse>('/auth/login', { email, password }).pipe(
      tap((resp) => {
        localStorage.setItem('access_token', resp.access_token);
        this.isAuthenticated.set(true);
        this.loadProfile().subscribe();
      })
    );
  }

  loadProfile(): Observable<any> {
    return this.api.get<any>('/auth/me').pipe(
      tap(profile => this.user.set(profile))
    );
  }

  logout() {
    localStorage.removeItem('access_token');
    this.isAuthenticated.set(false);
    this.user.set(null);
    this.router.navigate(['/auth/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getRole(): string | null {
    const profileRole = this.user()?.role;
    if (profileRole) return profileRole;

    const token = this.getToken();
    if (!token) return null;

    try {
      const payload = JSON.parse(atob(token.split('.')[1] ?? ''));
      return typeof payload.role === 'string' ? payload.role : null;
    } catch {
      return null;
    }
  }
}
