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
        localStorage.setItem('user_role', resp.role);
        this.isAuthenticated.set(true);
      })
    );
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    this.isAuthenticated.set(false);
    this.user.set(null);
    this.router.navigate(['/auth/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getRole(): string | null {
    return localStorage.getItem('user_role');
  }
}
