import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';

interface NavItem {
  label: string;
  path: string;
  icon: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-[var(--t-bg)]">

      <!-- Top Navigation Bar -->
      <header class="fixed top-0 left-0 right-0 z-50 h-14 border-b border-[var(--t-border)]
                     bg-[var(--t-surface)]/95 backdrop-blur-sm flex items-center px-6 gap-8">

        <!-- Logo -->
        <a routerLink="/" class="flex items-center gap-2 font-bold text-lg tracking-tight shrink-0">
          <span class="text-[var(--t-text-primary)]">Transmuter</span>
          <span class="text-[var(--t-accent)]">.</span>
        </a>

        <!-- Primary Nav -->
        <nav class="flex items-center gap-1 flex-1">
          @for (item of navItems; track item.path) {
            <a [routerLink]="item.path" routerLinkActive="bg-[var(--t-surface-raised)] text-[var(--t-text-primary)]"
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
          <button class="w-8 h-8 rounded-full bg-[var(--t-accent)] text-white text-sm font-medium
                         flex items-center justify-center" aria-label="User menu">
            U
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
                      bg-[var(--t-surface)] z-40 flex flex-col shadow-2xl">
          <div class="flex items-center justify-between px-5 py-4 border-b border-[var(--t-border)]">
            <div>
              <p class="font-semibold text-[var(--t-text-primary)]">Transmuter</p>
              <p class="text-xs text-[var(--t-text-secondary)]">Portfolio assistant</p>
            </div>
            <button (click)="aiPanelOpen.set(false)" class="btn-ghost text-lg" aria-label="Close">×</button>
          </div>

          <div class="flex-1 overflow-y-auto p-5">
            <h3 class="font-medium text-[var(--t-text-primary)] mb-2">Ask Transmuter</h3>
            <p class="text-sm text-[var(--t-text-secondary)] mb-4">
              Query initiatives, milestones, check risks, generate reports.
            </p>

            <div class="flex flex-col gap-2 mb-6">
              @for (prompt of suggestedPrompts; track prompt) {
                <button (click)="setQuery(prompt)"
                        class="text-left text-sm px-3 py-2 rounded-lg border border-[var(--t-border)]
                               hover:bg-[var(--t-surface-raised)] text-[var(--t-text-secondary)]
                               transition-colors">
                  {{ prompt }}
                </button>
              }
            </div>
          </div>

          <div class="p-4 border-t border-[var(--t-border)] flex gap-2">
            <input [value]="aiQuery()" (input)="aiQuery.set($any($event.target).value)"
                   placeholder="Ask Transmuter..."
                   class="input-field flex-1 text-sm" />
            <button class="btn-primary px-3" aria-label="Send">→</button>
          </div>
        </aside>
      }

    </div>
  `,
})
export class App {
  protected readonly themeService = inject(ThemeService);
  protected readonly aiPanelOpen = signal(false);
  protected readonly aiQuery = signal('');

  protected readonly navItems: NavItem[] = [
    { label: 'Dashboard',        path: '/',                   icon: 'grid' },
    { label: 'Initiatives',      path: '/initiatives/pipeline', icon: 'list' },
    { label: 'Progress Monitor', path: '/progress',           icon: 'bar-chart' },
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
  }
}
