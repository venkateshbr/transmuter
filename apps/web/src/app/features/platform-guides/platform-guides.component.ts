import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

interface GuideSummary {
  slug: string;
  category: string;
  title: string;
  summary: string;
  reviewed_at: string | null;
}

interface PublishedGuide extends GuideSummary {
  html: string;
}

@Component({
  selector: 'app-platform-guides',
  standalone: true,
  imports: [CommonModule],
  template: `
    <main class="min-h-[calc(100vh-4rem)] bg-[var(--t-bg)]" data-testid="platform-guide-library">
      <header class="border-b border-[var(--t-border)] bg-[var(--t-primary)] text-white">
        <div class="mx-auto max-w-[1680px] px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-end">
            <div>
              <p class="text-[10px] font-black uppercase tracking-[0.3em] text-[var(--t-blue-light)]">Transmuter knowledge library</p>
              <h1 class="mt-3 text-3xl font-black leading-tight sm:text-4xl">User guides and tutorials</h1>
              <p class="mt-4 max-w-3xl text-sm leading-6 text-white/75">
                Three maintained guides cover administration, day-to-day operations, and dashboard interpretation with one consistent worked example.
              </p>
            </div>
            <div class="grid grid-cols-2 border border-white/20 bg-white/5">
              <div class="border-r border-white/20 p-4">
                <p class="text-3xl font-black">{{ guides().length }}</p>
                <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-white/60">Published guides</p>
              </div>
              <div class="p-4">
                <p class="text-3xl font-black">{{ categories().length }}</p>
                <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-white/60">Guide collections</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div class="mx-auto max-w-[1680px] px-5 py-6 sm:px-8 lg:px-10 lg:py-8">
        @if (error()) {
          <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500" role="alert">{{ error() }}</div>
        }

        <section class="grid gap-4 border border-[var(--t-border)] bg-[var(--t-surface)] p-4 lg:grid-cols-[minmax(0,1fr)_auto]" aria-label="Guide filters">
          <label class="relative block">
            <span class="material-icons pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lg text-[var(--t-text-tertiary)]">search</span>
            <input
              type="search"
              class="input-field h-11 w-full pl-11 text-sm"
              placeholder="Search published guides"
              aria-label="Search published user guides"
              data-testid="guide-search"
              [value]="query()"
              (input)="setQuery($event)" />
          </label>
          <div class="flex flex-wrap gap-2" role="group" aria-label="Filter guides by collection">
            @for (category of categoryOptions(); track category) {
              <button
                type="button"
                class="border px-3 py-2 text-[10px] font-black uppercase tracking-widest transition-colors"
                [class.border-[var(--t-accent)]]="selectedCategory() === category"
                [class.bg-[var(--t-accent)]]="selectedCategory() === category"
                [class.text-white]="selectedCategory() === category"
                [class.border-[var(--t-border)]]="selectedCategory() !== category"
                [class.text-[var(--t-text-secondary)]]="selectedCategory() !== category"
                (click)="selectCategory(category)"
                [attr.aria-pressed]="selectedCategory() === category">
                {{ category }}
              </button>
            }
          </div>
        </section>

        <div class="mt-6 grid gap-6 xl:grid-cols-[390px_minmax(0,1fr)]">
          <aside class="border border-[var(--t-border)] bg-[var(--t-surface)] xl:sticky xl:top-20 xl:max-h-[calc(100vh-6rem)] xl:overflow-y-auto" aria-label="Published guide index">
            <div class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                {{ filteredGuides().length }} guides in view
              </p>
            </div>
            @for (item of filteredGuides(); track item.slug; let index = $index) {
              <button
                type="button"
                class="grid w-full grid-cols-[42px_minmax(0,1fr)] gap-3 border-b border-[var(--t-border)] px-4 py-4 text-left last:border-0 hover:bg-[var(--t-surface-raised)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--t-accent)]"
                [class.bg-[var(--t-accent-soft)]]="selectedSlug() === item.slug"
                (click)="openGuide(item.slug)"
                [attr.aria-current]="selectedSlug() === item.slug ? 'page' : null"
                [attr.data-testid]="'guide-index-' + item.slug">
                <span class="flex h-10 w-10 items-center justify-center border border-[var(--t-border)] bg-[var(--t-bg)] font-mono text-xs font-black text-[var(--t-accent)]">
                  {{ (index + 1).toString().padStart(2, '0') }}
                </span>
                <span>
                  <span class="block text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ item.category }}</span>
                  <span class="mt-1 block text-sm font-black leading-5 text-[var(--t-text-primary)]">{{ item.title }}</span>
                  <span class="mt-2 line-clamp-2 block text-[11px] leading-4 text-[var(--t-text-secondary)]">{{ item.summary }}</span>
                </span>
              </button>
            } @empty {
              <div class="p-6">
                <p class="text-sm font-black">No published guides match this search.</p>
                <button type="button" class="btn-ghost mt-4 text-xs" (click)="clearFilters()">Clear filters</button>
              </div>
            }
          </aside>

          <article class="min-w-0 border border-[var(--t-border)] bg-[var(--t-surface)]" data-testid="published-guide">
            @if (loading()) {
              <div class="flex min-h-[420px] items-center justify-center" role="status">
                <p class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Loading published guide…</p>
              </div>
            } @else if (guide(); as currentGuide) {
              <header class="border-b border-[var(--t-border)] p-5 sm:p-7 lg:p-8">
                <div class="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                  <div class="max-w-4xl">
                    <p class="text-[10px] font-black uppercase tracking-[0.24em] text-[var(--t-accent)]">{{ currentGuide.category }}</p>
                    <h2 class="mt-3 text-2xl font-black leading-tight sm:text-3xl">{{ currentGuide.title }}</h2>
                    <p class="mt-4 text-sm leading-6 text-[var(--t-text-secondary)]">{{ currentGuide.summary }}</p>
                  </div>
                  <div class="shrink-0 border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3 text-right">
                    <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Source review</p>
                    <p class="mt-1 text-xs font-black">{{ currentGuide.reviewed_at || 'Maintained source' }}</p>
                  </div>
                </div>
              </header>
              <div class="guide-content p-5 sm:p-7 lg:p-10" [innerHTML]="currentGuide.html"></div>
            } @else {
              <div class="flex min-h-[420px] items-center justify-center p-8 text-center">
                <div>
                  <span class="material-icons text-3xl text-[var(--t-text-tertiary)]">menu_book</span>
                  <p class="mt-3 text-sm font-black">Choose a published guide.</p>
                </div>
              </div>
            }
          </article>
        </div>
      </div>
    </main>
  `,
  styles: [`
    :host { display: block; }
    :host ::ng-deep .guide-content { overflow-x: auto; color: var(--t-text-primary); font-size: 0.875rem; line-height: 1.75; }
    :host ::ng-deep .guide-content > h1:first-child { display: none; }
    :host ::ng-deep .guide-content h2 { margin: 2.5rem 0 1rem; border-top: 1px solid var(--t-border); padding-top: 1.5rem; font-size: 1.35rem; font-weight: 900; line-height: 1.3; }
    :host ::ng-deep .guide-content h3 { margin: 2rem 0 0.75rem; color: var(--t-accent); font-size: 1rem; font-weight: 900; line-height: 1.4; }
    :host ::ng-deep .guide-content h4 { margin: 1.5rem 0 0.5rem; font-size: 0.9rem; font-weight: 900; }
    :host ::ng-deep .guide-content p { margin: 0.75rem 0; color: var(--t-text-secondary); }
    :host ::ng-deep .guide-content strong { color: var(--t-text-primary); font-weight: 800; }
    :host ::ng-deep .guide-content ul, :host ::ng-deep .guide-content ol { margin: 0.75rem 0 1rem 1.4rem; color: var(--t-text-secondary); }
    :host ::ng-deep .guide-content ul { list-style: square; }
    :host ::ng-deep .guide-content ol { list-style: decimal; }
    :host ::ng-deep .guide-content li { margin: 0.35rem 0; padding-left: 0.25rem; }
    :host ::ng-deep .guide-content a { color: var(--t-accent); font-weight: 800; text-decoration: underline; text-underline-offset: 3px; }
    :host ::ng-deep .guide-content blockquote { margin: 1.25rem 0; border-left: 4px solid var(--t-blue-light); background: var(--t-surface-raised); padding: 1rem 1.25rem; }
    :host ::ng-deep .guide-content blockquote p { margin: 0.25rem 0; }
    :host ::ng-deep .guide-content code { border: 1px solid var(--t-border); background: var(--t-bg); padding: 0.1rem 0.3rem; color: var(--t-accent); font-size: 0.78rem; }
    :host ::ng-deep .guide-content pre { margin: 1rem 0; overflow-x: auto; border: 1px solid var(--t-border); background: var(--t-primary); padding: 1rem; color: white; }
    :host ::ng-deep .guide-content pre code { border: 0; background: transparent; padding: 0; color: inherit; }
    :host ::ng-deep .guide-content table { margin: 1.25rem 0 1.75rem; width: 100%; min-width: 720px; border-collapse: collapse; font-size: 0.75rem; }
    :host ::ng-deep .guide-content table { display: table; }
    :host ::ng-deep .guide-content th { border: 1px solid var(--t-border); background: var(--t-primary); padding: 0.7rem; color: white; text-align: left; font-size: 0.65rem; font-weight: 900; text-transform: uppercase; letter-spacing: 0.06em; }
    :host ::ng-deep .guide-content td { border: 1px solid var(--t-border); padding: 0.7rem; vertical-align: top; color: var(--t-text-secondary); }
    :host ::ng-deep .guide-content hr { margin: 2rem 0; border: 0; border-top: 1px solid var(--t-border); }
  `],
})
export class PlatformGuidesComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly guides = signal<GuideSummary[]>([]);
  protected readonly guide = signal<PublishedGuide | null>(null);
  protected readonly selectedSlug = signal<string | null>(null);
  protected readonly selectedCategory = signal('All');
  protected readonly query = signal('');
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly categories = computed(() => [...new Set(this.guides().map(item => item.category))]);
  protected readonly categoryOptions = computed(() => ['All', ...this.categories()]);
  protected readonly filteredGuides = computed(() => {
    const query = this.query().trim().toLowerCase();
    return this.guides().filter(item => {
      if (this.selectedCategory() !== 'All' && item.category !== this.selectedCategory()) return false;
      return !query || `${item.title} ${item.summary} ${item.category}`.toLowerCase().includes(query);
    });
  });

  ngOnInit(): void {
    this.api.get<{ items: GuideSummary[] }>('/guides').subscribe({
      next: response => {
        const items = response.items || [];
        this.guides.set(items);
        const requestedSlug = this.route.snapshot.paramMap.get('slug');
        const selected = items.find(item => item.slug === requestedSlug) || items[0];
        if (selected) this.loadGuide(selected.slug, false);
        else this.loading.set(false);
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err.error?.detail || 'Could not load published guides.');
      },
    });
  }

  protected setQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
  }

  protected selectCategory(category: string): void {
    this.selectedCategory.set(category);
  }

  protected clearFilters(): void {
    this.query.set('');
    this.selectedCategory.set('All');
  }

  protected openGuide(slug: string): void {
    this.loadGuide(slug, true);
  }

  private loadGuide(slug: string, updateUrl: boolean): void {
    this.loading.set(true);
    this.error.set(null);
    this.selectedSlug.set(slug);
    this.api.get<PublishedGuide>(`/guides/${slug}`).subscribe({
      next: response => {
        this.guide.set(response);
        this.loading.set(false);
        if (updateUrl) void this.router.navigate(['/guides', slug]);
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err.error?.detail || 'Could not load the selected guide.');
      },
    });
  }
}
