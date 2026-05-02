import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { ApiService } from './core/services/api.service';
import { AuthService } from './core/services/auth.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface NavItem {
  label: string;
  path: string;
  icon: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-[var(--t-bg)]">

      <!-- Top Navigation Bar -->
      <header class="fixed top-0 left-0 right-0 z-50 h-14 border-b border-[var(--t-border)]
                     bg-[var(--t-surface)]/95 backdrop-blur-sm flex items-center px-6 gap-8">

        <!-- Logo -->
        <a routerLink="/" class="flex items-center gap-2 font-bold text-lg tracking-tight shrink-0">
          <span class="text-[var(--t-text-primary)]">Transmuter</span>
          <span class="text-[var(--t-accent)]" style="font-size:1.4em;line-height:1">.</span>
        </a>

        <!-- Primary Nav -->
        <nav class="flex items-center gap-1 flex-1">
          @for (item of navItems; track item.path) {
            <a [routerLink]="item.path" routerLinkActive="bg-[var(--t-accent-soft)] text-[var(--t-accent)]"
               class="nav-item text-sm">
              {{ item.label }}
            </a>
          }
        </nav>

        <!-- Right controls -->
        <div class="flex items-center gap-3 shrink-0">
          <!-- Theme toggle -->
          <button (click)="themeService.toggle()" class="btn-ghost text-sm" aria-label="Toggle theme">
            {{ themeService.isDark() ? '☀️' : '🌙' }}
          </button>

          <!-- + Transmuter AI button -->
          <button (click)="aiPanelOpen.set(!aiPanelOpen())"
                  class="btn-primary text-sm flex items-center gap-2">
            <span>+</span> Transmuter
          </button>

          <!-- User avatar -->
          <button (click)="auth.logout()" class="w-8 h-8 rounded-full text-white text-sm font-medium
                         flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity" 
                  aria-label="User menu"
                  title="Logout"
                  style="background:linear-gradient(135deg, var(--t-accent), #a855f7)">
            {{ (auth.user()?.display_name || 'U').substring(0,1) }}
          </button>
        </div>
      </header>

      <!-- Main Content -->
      <main class="pt-14">
        <router-outlet />
      </main>

      <!-- AI Assistant Right Panel -->
      @if (aiPanelOpen()) {
        <aside class="fixed top-14 right-0 bottom-0 w-96 border-l border-[var(--t-border)]
                      bg-[var(--t-surface)] z-40 flex flex-col shadow-2xl animate-slide-in-right">
          <div class="flex items-center justify-between px-5 py-4 border-b border-[var(--t-border)]">
            <div>
              <p class="font-semibold text-[var(--t-text-primary)]">Transmuter AI</p>
              <p class="text-xs text-[var(--t-text-secondary)]">Portfolio assistant</p>
            </div>
            <button (click)="aiPanelOpen.set(false)" class="btn-ghost text-lg" aria-label="Close">×</button>
          </div>

          <div class="flex-1 overflow-y-auto p-5 space-y-4">
            @if (messages().length === 0) {
              <div class="py-8 text-center">
                <h3 class="font-medium text-[var(--t-text-primary)] mb-2">How can I help?</h3>
                <p class="text-xs text-[var(--t-text-secondary)] mb-6">
                  Query initiatives, milestones, check risks, or generate status summaries.
                </p>

                <div class="flex flex-col gap-2">
                  @for (prompt of suggestedPrompts; track prompt) {
                    <button (click)="setQuery(prompt)"
                            class="text-left text-xs px-3 py-2 rounded-lg border border-[var(--t-border)]
                                   hover:bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]
                                   transition-colors">
                      {{ prompt }}
                    </button>
                  }
                </div>
              </div>
            }

            @for (msg of messages(); track msg.timestamp) {
              <div class="flex flex-col" [class.items-end]="msg.role === 'user'">
                <div class="max-w-[85%] p-3 rounded-2xl text-sm"
                     [class.bg-[var(--t-accent)]]="msg.role === 'user'"
                     [class.text-white]="msg.role === 'user'"
                     [class.bg-[var(--t-surface-raised)]]="msg.role === 'assistant'"
                     [class.text-[var(--t-text-primary)]]="msg.role === 'assistant'">
                  {{ msg.content }}
                </div>
                <span class="text-[9px] text-[var(--t-text-tertiary)] mt-1 px-2">
                  {{ msg.timestamp | date:'shortTime' }}
                </span>
              </div>
            }

            @if (aiLoading()) {
              <div class="flex items-center gap-2 text-xs text-[var(--t-text-tertiary)]">
                <div class="flex gap-1">
                  <div class="w-1 h-1 rounded-full bg-[var(--t-accent)] animate-bounce"></div>
                  <div class="w-1 h-1 rounded-full bg-[var(--t-accent)] animate-bounce" style="animation-delay: 0.2s"></div>
                  <div class="w-1 h-1 rounded-full bg-[var(--t-accent)] animate-bounce" style="animation-delay: 0.4s"></div>
                </div>
                Transmuter is thinking...
              </div>
            }
          </div>

          <div class="p-4 border-t border-[var(--t-border)] flex gap-2">
            <input [ngModel]="aiQuery()"
                   (ngModelChange)="aiQuery.set($event)"
                   (keyup.enter)="sendMessage()"
                   placeholder="Ask Transmuter..."
                   class="input-field flex-1 text-sm" />
            <button (click)="sendMessage()" 
                    [disabled]="aiLoading() || !aiQuery()"
                    class="btn-primary px-3" aria-label="Send">→</button>
          </div>
        </aside>
      }

    </div>
  `,
  styles: [`
    :host { display: block; }
    .animate-slide-in-right {
      animation: slide-in-right 0.3s ease-out;
    }
    @keyframes slide-in-right {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
  `]
})
export class App {
  protected readonly themeService = inject(ThemeService);
  protected readonly api = inject(ApiService);
  protected readonly auth = inject(AuthService);

  protected readonly aiPanelOpen = signal(false);
  protected readonly aiLoading = signal(false);
  protected readonly aiQuery = signal('');
  protected readonly messages = signal<Message[]>([]);

  protected readonly navItems: NavItem[] = [
    { label: 'Dashboard',        path: '/',                   icon: 'grid' },
    { label: 'Initiatives',      path: '/initiatives/pipeline', icon: 'list' },
    { label: 'Progress Monitor', path: '/progress',           icon: 'bar-chart' },
    { label: 'Roadmap Explorer', path: '/progress/roadmap',   icon: 'map' },
    { label: 'Governance',       path: '/pmo/governance',     icon: 'shield' },
    { label: 'KPIs',             path: '/pmo/kpis',           icon: 'bar-chart' },
    { label: 'Risks',            path: '/pmo/risks',          icon: 'alert' },
    { label: 'AI Insights',      path: '/pmo/ai-insights',    icon: 'cpu' },
    { label: 'Meetings',         path: '/meetings',           icon: 'calendar' },
    { label: 'People',           path: '/people',             icon: 'users' },
    { label: 'Admin',            path: '/admin',              icon: 'settings' },
  ];

  protected readonly suggestedPrompts = [
    'Show me at-risk initiatives',
    'What milestones are due this week?',
    'Summarize the portfolio',
  ];

  protected setQuery(prompt: string): void {
    this.aiQuery.set(prompt);
    this.sendMessage();
  }

  protected sendMessage(): void {
    const currentQuery = this.aiQuery();
    if (!currentQuery || this.aiLoading()) return;

    const userMsg: Message = {
      role: 'user',
      content: currentQuery,
      timestamp: new Date()
    };
    
    this.messages.update(msgs => [...msgs, userMsg]);
    this.aiQuery.set('');
    this.aiLoading.set(true);

    this.api.post<any>('/ai/chat', { query: currentQuery }).subscribe({
      next: (res) => {
        const aiMsg: Message = {
          role: 'assistant',
          content: res.response,
          timestamp: new Date()
        };
        this.messages.update(msgs => [...msgs, aiMsg]);
        this.aiLoading.set(false);
      },
      error: () => {
        this.aiLoading.set(false);
        // Error handling
      }
    });
  }
}
