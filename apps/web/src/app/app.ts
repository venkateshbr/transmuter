import { Component, HostListener, inject, signal } from '@angular/core';
import { NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { ApiService } from './core/services/api.service';
import { AuthService } from './core/services/auth.service';
import { LoadingService } from './core/services/loading.service';
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
  sources?: { label: string; source_type: string; record_id?: string; url?: string }[];
  tool_trace?: { tool_name: string; status: string; summary: string; source_type: string }[];
  confidence?: number;
  proposed_actions?: ProposedAction[];
}

interface ProposedAction {
  id: string;
  action_type: string;
  title: string;
  description: string;
  payload: Record<string, unknown>;
  status: string;
}

interface GlobalSearchResult {
  id: string;
  result_type: string;
  label: string;
  name: string;
  description?: string | null;
  url: string;
  initiative_code?: string | null;
  category?: string | null;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-[var(--t-bg)] text-[var(--t-text-primary)]">

      <!-- Top Navigation Bar -->
      @if (showAppChrome()) {
      <header class="fixed top-0 left-0 right-0 z-50 h-16 border-b border-[var(--t-border)]
                     bg-[var(--t-surface)]/95 backdrop-blur-sm flex items-center px-5 gap-5 shadow-[0_2px_16px_rgba(7,31,60,0.06)]">

        <!-- Logo -->
        <a [routerLink]="homeLink()" class="flex items-center gap-3 shrink-0" aria-label="Transmuter home">
          <span class="relative flex h-9 w-9 items-center justify-center bg-[var(--t-primary)] text-white">
            <span class="absolute inset-y-1 left-3 w-1 bg-[var(--t-blue-light)]"></span>
            <span class="absolute inset-y-1 right-3 w-1 bg-[var(--t-blue-light)]"></span>
            <span class="relative text-[13px] font-black">T</span>
          </span>
          <span class="hidden 2xl:flex flex-col leading-none">
            <span class="text-[17px] font-black uppercase text-[var(--t-text-primary)]">Transmuter</span>
          </span>
        </a>

        <!-- Primary Nav -->
        <nav class="flex min-w-0 flex-1 items-center gap-0.5 overflow-visible">
          @for (item of primaryNavItems; track item.path) {
            <a [routerLink]="item.path" routerLinkActive="bg-[var(--t-accent-soft)] text-[var(--t-accent)]"
               class="nav-item whitespace-nowrap px-2 text-[11px] font-bold uppercase">
              {{ item.label }}
            </a>
          }
          @if (overflowNavItems.length) {
            <div class="relative shrink-0">
              <button
                type="button"
                class="nav-item whitespace-nowrap px-2 text-[11px] font-bold uppercase"
                [class.bg-[var(--t-accent-soft)]]="isOverflowRouteActive()"
                [class.text-[var(--t-accent)]]="isOverflowRouteActive()"
                (click)="moreMenuOpen.set(!moreMenuOpen())"
                aria-label="Open more navigation">
                More
                <span class="material-icons align-middle text-sm">expand_more</span>
              </button>
              @if (moreMenuOpen()) {
                <div class="absolute right-0 top-full mt-3 w-56 border border-[var(--t-border)] bg-[var(--t-surface)] py-2 shadow-xl">
                  @for (item of overflowNavItems; track item.path) {
                    <a
                      [routerLink]="item.path"
                      routerLinkActive="bg-[var(--t-accent-soft)] text-[var(--t-accent)]"
                      class="block px-4 py-2 text-[11px] font-black uppercase tracking-wide text-[var(--t-text-secondary)] hover:bg-[var(--t-surface-raised)] hover:text-[var(--t-accent)]"
                      (click)="moreMenuOpen.set(false)">
                      {{ item.label }}
                    </a>
                  }
                </div>
              }
            </div>
          }
        </nav>

        @if (!isPlatformAdmin()) {
          <div class="relative hidden min-w-[18rem] max-w-sm flex-1 xl:block">
            <span class="material-icons pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--t-text-tertiary)]">search</span>
            <input
              type="search"
              class="h-9 w-full border border-[var(--t-border)] bg-[var(--t-bg)] pl-9 pr-3 text-xs font-bold text-[var(--t-text-primary)] outline-none focus:border-[var(--t-accent)]"
              placeholder="Search portfolio"
              aria-label="Global portfolio search"
              data-testid="global-search-input"
              [ngModel]="globalSearchQuery()"
              (ngModelChange)="onGlobalSearchChange($event)"
              (focus)="globalSearchOpen.set(true)"
              (keyup.escape)="closeGlobalSearch()"
            />
            @if (globalSearchOpen()) {
              <div class="absolute left-0 right-0 top-full z-[60] mt-2 max-h-[70vh] overflow-auto border border-[var(--t-border)] bg-[var(--t-surface)] shadow-2xl" data-testid="global-search-results">
                @if (globalSearchLoading()) {
                  <p class="px-4 py-3 text-xs font-bold text-[var(--t-text-secondary)]">Searching...</p>
                } @else if (globalSearchQuery().trim().length < 2) {
                  <p class="px-4 py-3 text-xs font-bold text-[var(--t-text-secondary)]">Type at least two characters.</p>
                } @else if (!globalSearchResults().length) {
                  <p class="px-4 py-3 text-xs font-bold text-[var(--t-text-secondary)]">No matching portfolio records.</p>
                } @else {
                  @for (item of globalSearchResults(); track item.result_type + item.id) {
                    <button
                      type="button"
                      class="grid w-full grid-cols-[auto_1fr] gap-3 border-b border-[var(--t-border)] px-4 py-3 text-left hover:bg-[var(--t-surface-raised)]"
                      [attr.aria-label]="'Open ' + item.label"
                      (click)="openGlobalSearchResult(item)">
                      <span class="material-icons mt-0.5 text-base text-[var(--t-accent)]">{{ searchIcon(item.result_type) }}</span>
                      <span class="min-w-0">
                        <span class="block truncate text-xs font-black uppercase text-[var(--t-text-primary)]">{{ item.label }}</span>
                        <span class="mt-1 block truncate text-[11px] font-medium text-[var(--t-text-secondary)]">{{ item.description || item.category || item.result_type }}</span>
                      </span>
                    </button>
                  }
                }
              </div>
            }
          </div>
        }

        <!-- Right controls -->
        <div class="flex items-center gap-2 shrink-0">
          <!-- Theme toggle -->
          <button (click)="themeService.toggle()" class="btn-ghost flex h-9 w-9 items-center justify-center border border-[var(--t-border)] text-sm" aria-label="Toggle theme">
            <span class="material-icons text-base">{{ themeService.isDark() ? 'light_mode' : 'dark_mode' }}</span>
          </button>

          <!-- + Transmuter AI button -->
          @if (!isPlatformAdmin()) {
          <button (click)="aiPanelOpen.set(!aiPanelOpen())"
                  class="btn-primary flex items-center gap-2 text-[11px]"
                  aria-label="Open Transmuter assistant">
            <span class="material-icons text-sm">auto_awesome</span> Transmuter
          </button>
          }

          <!-- User avatar -->
          <div class="relative">
            <button (click)="accountMenuOpen.set(!accountMenuOpen())" class="w-9 h-9 text-white text-sm font-bold
                           flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity"
                    aria-label="Open user menu"
                    [attr.aria-expanded]="accountMenuOpen()"
                    style="background:var(--t-primary); box-shadow:inset 0 -3px 0 var(--t-blue-light)">
              {{ (auth.user()?.display_name || auth.user()?.email || 'U').substring(0,1) }}
            </button>
            @if (accountMenuOpen()) {
              <div class="absolute right-0 top-full mt-3 w-64 border border-[var(--t-border)] bg-[var(--t-surface)] shadow-xl">
                <div class="border-b border-[var(--t-border)] px-4 py-3">
                  <p class="truncate text-xs font-black text-[var(--t-text-primary)]">{{ auth.user()?.display_name || auth.user()?.email || 'User' }}</p>
                  <p class="mt-1 truncate text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ auth.user()?.role || 'viewer' }}</p>
                </div>
                <a
                  routerLink="/profile"
                  class="flex items-center gap-3 px-4 py-3 text-xs font-black uppercase tracking-widest text-[var(--t-text-secondary)] hover:bg-[var(--t-surface-raised)] hover:text-[var(--t-accent)]"
                  (click)="accountMenuOpen.set(false)">
                  <span class="material-icons text-sm">manage_accounts</span>
                  Profile
                </a>
                <button
                  type="button"
                  class="flex w-full items-center gap-3 border-t border-[var(--t-border)] px-4 py-3 text-left text-xs font-black uppercase tracking-widest text-[var(--t-text-secondary)] hover:bg-[var(--t-surface-raised)] hover:text-[var(--t-accent)]"
                  aria-label="Logout"
                  (click)="logoutFromMenu()">
                  <span class="material-icons text-sm">logout</span>
                  Logout
                </button>
              </div>
            }
          </div>
        </div>
      </header>
      }

      <!-- Main Content -->
      <main [class.pt-16]="showAppChrome()">
        <router-outlet />
      </main>

      @if (showAppChrome() && loading.visible()) {
        <div
          class="fixed inset-0 z-[70] flex items-center justify-center bg-[var(--t-surface)]/92 backdrop-blur-sm"
          role="status"
          aria-live="polite"
          [attr.aria-label]="loading.message()">
          <div class="w-[min(520px,calc(100vw-48px))] border border-[var(--t-border)] bg-[var(--t-bg)] p-6 shadow-2xl">
            <div class="flex items-center justify-between gap-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Workspace sync</p>
                <p class="mt-2 text-sm font-bold text-[var(--t-text-primary)]">{{ loading.message() }}</p>
              </div>
              <span class="font-mono text-xs font-black text-[var(--t-text-tertiary)]">{{ loading.progress() | number:'1.0-0' }}%</span>
            </div>
            <div class="mt-5 h-1.5 w-full overflow-hidden bg-[var(--t-surface-raised)]">
              <div
                class="h-full bg-[var(--t-accent)] transition-[width] duration-200 ease-out"
                [style.width.%]="loading.progress()">
              </div>
            </div>
          </div>
        </div>
      }

      <!-- AI Assistant Right Panel -->
      @if (aiPanelOpen()) {
        <aside class="fixed top-16 right-0 bottom-0 w-96 border-l border-[var(--t-border)]
                      bg-[var(--t-surface)] z-40 flex flex-col shadow-2xl animate-slide-in-right">
          <div class="flex items-center justify-between px-5 py-4 border-b border-[var(--t-border)]">
            <div>
              <p class="text-[13px] font-black uppercase text-[var(--t-text-primary)]">Ask Transmuter</p>
              <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)]">Portfolio assistant</p>
            </div>
            <button (click)="aiPanelOpen.set(false)" class="btn-ghost flex h-8 w-8 items-center justify-center text-lg" aria-label="Close">
              <span class="material-icons text-base">close</span>
            </button>
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
                            class="text-left text-xs px-3 py-2 border border-[var(--t-border)]
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
                <div class="max-w-[85%] p-3 text-sm border"
                     [class.bg-[var(--t-accent)]]="msg.role === 'user'"
                     [class.text-white]="msg.role === 'user'"
                     [class.border-[var(--t-accent)]]="msg.role === 'user'"
                     [class.bg-[var(--t-surface-raised)]]="msg.role === 'assistant'"
                     [class.border-[var(--t-border)]]="msg.role === 'assistant'"
                     [class.text-[var(--t-text-primary)]]="msg.role === 'assistant'">
                  {{ msg.content }}
                  @if (msg.role === 'assistant' && msg.sources?.length) {
                    <div class="mt-3 flex flex-wrap gap-1 border-t border-[var(--t-border)] pt-2">
                      @for (source of msg.sources; track source.label) {
                        <span class="rounded bg-[var(--t-surface)] px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[var(--t-text-secondary)]">
                          {{ source.label }}
                        </span>
                      }
                    </div>
                  }
                  @if (msg.role === 'assistant' && msg.tool_trace?.length) {
                    <div class="mt-2 border-t border-[var(--t-border)] pt-2">
                      @for (trace of msg.tool_trace; track trace.tool_name) {
                        <p class="text-[10px] font-bold uppercase tracking-wide text-[var(--t-text-tertiary)]">
                          {{ trace.tool_name }} · {{ trace.summary }}
                        </p>
                      }
                    </div>
                  }
                  @if (msg.role === 'assistant' && msg.proposed_actions?.length) {
                    <div class="mt-3 space-y-2 border-t border-[var(--t-border)] pt-3">
                      @for (action of msg.proposed_actions; track action.id) {
                        <div class="border border-[var(--t-border)] bg-[var(--t-bg)] p-3">
                          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Confirmation required</p>
                          <p class="mt-1 text-xs font-black text-[var(--t-text-primary)]">{{ action.title }}</p>
                          <p class="mt-1 text-[11px] text-[var(--t-text-secondary)]">{{ action.description }}</p>
                          <button
                            type="button"
                            class="btn-primary mt-3 w-full text-[10px]"
                            [disabled]="aiLoading() || action.status !== 'draft'"
                            (click)="confirmAction(action)">
                            Confirm
                          </button>
                        </div>
                      }
                    </div>
                  }
                </div>
                <span class="text-[9px] text-[var(--t-text-tertiary)] mt-1 px-2">
                  {{ msg.timestamp | date:'shortTime' }}
                  @if (msg.confidence) {
                    · {{ msg.confidence | percent:'1.0-0' }}
                  }
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
            <input [ngModel]="aiQueryText()"
                   (ngModelChange)="aiQueryText.set($event)"
                   (keyup.enter)="sendMessage()"
                   placeholder="Ask Transmuter..."
                   class="input-field flex-1 text-sm" />
            <button (click)="sendMessage()" 
                    [disabled]="aiLoading() || !aiQueryText()"
                    class="btn-primary px-3" aria-label="Send">
              <span class="material-icons text-base">arrow_forward</span>
            </button>
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
  protected readonly loading = inject(LoadingService);
  private readonly router = inject(Router);

  protected readonly aiPanelOpen = signal(false);
  protected readonly aiLoading = signal(false);
  protected readonly aiQueryText = signal('');
  protected readonly messages = signal<Message[]>([]);
  protected readonly moreMenuOpen = signal(false);
  protected readonly accountMenuOpen = signal(false);
  protected readonly globalSearchQuery = signal('');
  protected readonly globalSearchResults = signal<GlobalSearchResult[]>([]);
  protected readonly globalSearchOpen = signal(false);
  protected readonly globalSearchLoading = signal(false);
  private globalSearchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.router.events.subscribe(event => {
      if (event instanceof NavigationStart) {
        this.moreMenuOpen.set(false);
        this.accountMenuOpen.set(false);
        this.loading.beginNavigation();
      }
      if (event instanceof NavigationEnd || event instanceof NavigationCancel || event instanceof NavigationError) {
        this.loading.endNavigation();
      }
    });
  }

  protected get navItems(): NavItem[] {
    if (this.isPlatformAdmin()) {
      return [
        { label: 'Platform', path: '/platform', icon: 'admin_panel_settings' },
      ];
    }
    return [
    { label: 'Dashboard',        path: '/dashboard',          icon: 'grid' },
    { label: 'Financials',       path: '/financials',         icon: 'payments' },
    { label: 'Shared Costs',     path: '/shared-costs',       icon: 'account_balance' },
    { label: 'Initiatives',      path: '/initiatives/pipeline', icon: 'list' },
    { label: 'Progress Monitor', path: '/progress',           icon: 'bar-chart' },
    { label: 'Governance',       path: '/pmo/governance',     icon: 'shield' },
    { label: 'KPIs',             path: '/pmo/kpis',           icon: 'bar-chart' },
    { label: 'Risks',            path: '/pmo/risks',          icon: 'alert' },
    { label: 'AI Insights',      path: '/pmo/ai-insights',    icon: 'cpu' },
    { label: 'Meetings',         path: '/meetings',           icon: 'calendar' },
    { label: 'People',           path: '/people',             icon: 'users' },
    ...(this.canManageTenant() ? [{ label: 'Admin', path: '/admin', icon: 'settings' }] : []),
    ];
  }

  protected get primaryNavItems(): NavItem[] {
    const overflowPaths = new Set(['/meetings', '/people', '/admin']);
    return this.navItems.filter(item => !overflowPaths.has(item.path));
  }

  protected get overflowNavItems(): NavItem[] {
    const overflowPaths = new Set(['/meetings', '/people', '/admin']);
    return this.navItems.filter(item => overflowPaths.has(item.path));
  }

  protected readonly suggestedPrompts = [
    'Show me at-risk initiatives',
    'What milestones are due this week?',
    'Summarize the portfolio',
  ];

  protected showAppChrome(): boolean {
    const path = this.router.url.split('?')[0];
    return this.auth.isAuthenticated()
      && path !== '/'
      && path !== '/get-started'
      && path !== '/auth/login'
      && path !== '/auth/register'
      && path !== '/auth/change-password'
      && path !== '/subscription/success';
  }

  protected isPlatformAdmin(): boolean {
    return this.auth.getRole() === 'platform_admin';
  }

  protected canManageTenant(): boolean {
    return this.auth.getRole() === 'transformation_office';
  }

  protected homeLink(): string {
    return this.isPlatformAdmin() ? '/platform' : '/dashboard';
  }

  protected isOverflowRouteActive(): boolean {
    const currentPath = this.router.url.split('?')[0];
    return this.overflowNavItems.some(item => currentPath === item.path || currentPath.startsWith(`${item.path}/`));
  }

  protected logoutFromMenu(): void {
    this.accountMenuOpen.set(false);
    this.auth.logout();
  }

  @HostListener('window:keydown', ['$event'])
  protected handleGlobalShortcut(event: KeyboardEvent): void {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && this.showAppChrome()) {
      event.preventDefault();
      const input = document.querySelector<HTMLInputElement>('[data-testid="global-search-input"]');
      input?.focus();
      this.globalSearchOpen.set(true);
    }
  }

  protected onGlobalSearchChange(value: string): void {
    this.globalSearchQuery.set(value);
    this.globalSearchOpen.set(true);
    if (this.globalSearchTimer) clearTimeout(this.globalSearchTimer);
    this.globalSearchTimer = setTimeout(() => this.runGlobalSearch(), 180);
  }

  protected closeGlobalSearch(): void {
    this.globalSearchOpen.set(false);
  }

  protected openGlobalSearchResult(item: GlobalSearchResult): void {
    this.closeGlobalSearch();
    this.globalSearchQuery.set('');
    this.globalSearchResults.set([]);
    this.router.navigateByUrl(item.url);
  }

  protected searchIcon(type: string): string {
    const icons: Record<string, string> = {
      initiative: 'flag',
      milestone: 'event',
      risk: 'warning',
      user: 'person',
    };
    return icons[type] || 'search';
  }

  private runGlobalSearch(): void {
    const q = this.globalSearchQuery().trim();
    if (q.length < 2) {
      this.globalSearchResults.set([]);
      this.globalSearchLoading.set(false);
      return;
    }
    this.globalSearchLoading.set(true);
    this.api.get<{ items: GlobalSearchResult[] }>('/search', { q, limit: 8 }).subscribe({
      next: response => {
        this.globalSearchResults.set(response.items || []);
        this.globalSearchLoading.set(false);
      },
      error: () => {
        this.globalSearchResults.set([]);
        this.globalSearchLoading.set(false);
      },
    });
  }

  protected setQuery(prompt: string): void {
    this.aiQueryText.set(prompt);
    this.sendMessage();
  }

  protected sendMessage(): void {
    const currentQuery = this.aiQueryText();
    if (!currentQuery || this.aiLoading()) return;

    const userMsg: Message = {
      role: 'user',
      content: currentQuery,
      timestamp: new Date()
    };
    
    this.messages.update(msgs => [...msgs, userMsg]);
    this.aiQueryText.set('');
    this.aiLoading.set(true);

    this.api.post<any>('/ai/chat', { query: currentQuery }).subscribe({
      next: (res) => {
        const aiMsg: Message = {
          role: 'assistant',
          content: res.response,
          timestamp: new Date(),
          sources: res.sources || [],
          tool_trace: res.tool_trace || [],
          confidence: res.confidence,
          proposed_actions: res.proposed_actions || []
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

  protected confirmAction(action: ProposedAction): void {
    if (this.aiLoading() || action.status !== 'draft') return;
    this.aiLoading.set(true);
    this.api.post<any>(`/ai/actions/${action.id}/confirm`, {}).subscribe({
      next: (res) => {
        action.status = res.status || 'confirmed';
        this.messages.update(msgs => [...msgs, {
          role: 'assistant',
          content: res.message || 'Action confirmed.',
          timestamp: new Date(),
          sources: [{ label: 'Confirmed action', source_type: action.action_type }],
          tool_trace: [{
            tool_name: action.action_type,
            status: 'confirmed',
            summary: 'Executed through the underlying Transmuter API.',
            source_type: action.action_type
          }],
          confidence: 1
        }]);
        this.aiLoading.set(false);
      },
      error: () => {
        this.messages.update(msgs => [...msgs, {
          role: 'assistant',
          content: 'I could not confirm that action. Please check your permissions and the target record.',
          timestamp: new Date(),
          confidence: 0.4
        }]);
        this.aiLoading.set(false);
      }
    });
  }
}
