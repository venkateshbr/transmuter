import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface CompactFilterOption {
  id: string;
  name: string;
}

export interface CompactFilterGroup {
  key: string;
  label: string;
  options: CompactFilterOption[];
  selected: string[];
  mode?: 'multi' | 'single';
  testId?: string;
}

@Component({
  selector: 'app-compact-filter-toolbar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="compact-filter-toolbar" [attr.data-testid]="toolbarTestId || null" aria-label="Page filters">
      @if (showSearch) {
        <label class="relative min-w-[220px] flex-1 lg:max-w-[320px]">
          <span class="material-icons pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--t-text-tertiary)]">search</span>
          <input
            class="input-field h-10 pl-9 text-sm"
            [ngModel]="searchValue"
            (ngModelChange)="searchValueChange.emit($event)"
            [placeholder]="searchPlaceholder"
            aria-label="Search">
        </label>
      }

      <div class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        @for (group of groups; track group.key) {
          <div class="relative" [attr.data-testid]="group.testId">
            <button
              type="button"
              class="filter-button"
              [class.filter-button-active]="group.selected.length"
              [attr.aria-expanded]="openKey() === group.key"
              [attr.aria-label]="'Open ' + group.label + ' filter'"
              (click)="toggleOpen(group.key)">
              <span>{{ group.label }}</span>
              @if (group.selected.length) {
                <span class="filter-count">{{ group.selected.length }}</span>
              }
              <span class="material-icons text-sm">expand_more</span>
            </button>

            @if (openKey() === group.key) {
              <div class="filter-popover">
                <div class="border-b border-[var(--t-border)] px-3 py-2">
                  <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ group.label }}</p>
                  <p class="mt-1 text-xs font-bold text-[var(--t-text-secondary)]">{{ selectedSummary(group) }}</p>
                </div>
                <div class="max-h-64 overflow-y-auto p-2">
                  @for (option of group.options; track option.id) {
                    <label class="filter-option">
                      <input
                        [type]="group.mode === 'single' ? 'radio' : 'checkbox'"
                        [name]="group.key"
                        [checked]="group.selected.includes(option.id)"
                        (change)="toggleOption(group, option.id, $event)"
                        [attr.aria-label]="group.label + ': ' + option.name">
                      <span>{{ option.name }}</span>
                    </label>
                  }
                  @if (!group.options.length) {
                    <p class="px-2 py-6 text-center text-xs font-bold text-[var(--t-text-tertiary)]">No options</p>
                  }
                </div>
              </div>
            }
          </div>
        }
      </div>

      @if (hasFilters) {
        <button
          type="button"
          class="btn-secondary h-10 px-3 text-[10px]"
          [attr.data-testid]="clearTestId || null"
          aria-label="Clear filters"
          (click)="clearFilters.emit()">
          Clear
        </button>
      }
    </section>
  `,
  styles: [`
    :host { display: block; }
    .compact-filter-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.75rem;
      border: 1px solid var(--t-border);
      background: var(--t-surface);
      padding: 0.75rem;
      box-shadow: var(--t-shadow);
    }
    .filter-button {
      display: inline-flex;
      height: 2.5rem;
      min-width: 8.75rem;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      border: 1px solid var(--t-border);
      background: var(--t-surface-raised);
      color: var(--t-text-secondary);
      padding: 0 0.75rem;
      font-size: 0.625rem;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      transition: border-color 160ms ease, color 160ms ease, background 160ms ease;
    }
    .filter-button:hover,
    .filter-button-active {
      border-color: var(--t-accent);
      background: var(--t-accent-soft);
      color: var(--t-accent);
    }
    .filter-count {
      min-width: 1.25rem;
      border: 1px solid var(--t-accent);
      background: var(--t-surface);
      padding: 0.125rem 0.25rem;
      text-align: center;
      font-size: 0.625rem;
      line-height: 1;
    }
    .filter-popover {
      position: absolute;
      left: 0;
      top: calc(100% + 0.5rem);
      z-index: 60;
      width: min(18rem, calc(100vw - 2rem));
      border: 1px solid var(--t-border);
      background: var(--t-surface);
      box-shadow: 0 18px 42px rgba(7,31,60,0.18);
    }
    .filter-option {
      display: flex;
      min-height: 2rem;
      align-items: center;
      gap: 0.625rem;
      border: 1px solid transparent;
      padding: 0.375rem 0.5rem;
      color: var(--t-text-secondary);
      font-size: 0.75rem;
      font-weight: 700;
    }
    .filter-option:hover {
      border-color: var(--t-border);
      background: var(--t-surface-raised);
      color: var(--t-text-primary);
    }
    .filter-option input {
      accent-color: var(--t-accent);
    }
  `],
})
export class CompactFilterToolbarComponent {
  @Input() showSearch = true;
  @Input() searchValue = '';
  @Input() searchPlaceholder = 'Search...';
  @Input() groups: CompactFilterGroup[] = [];
  @Input() hasFilters = false;
  @Input() clearTestId = '';
  @Input() toolbarTestId = '';

  @Output() readonly searchValueChange = new EventEmitter<string>();
  @Output() readonly groupSelectionChange = new EventEmitter<{ key: string; selected: string[] }>();
  @Output() readonly clearFilters = new EventEmitter<void>();

  readonly openKey = signal<string | null>(null);

  toggleOpen(key: string): void {
    this.openKey.set(this.openKey() === key ? null : key);
  }

  toggleOption(group: CompactFilterGroup, optionId: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const current = group.selected || [];
    const selected = group.mode === 'single'
      ? (checked ? [optionId] : [])
      : checked
        ? Array.from(new Set([...current, optionId]))
        : current.filter(item => item !== optionId);
    this.groupSelectionChange.emit({ key: group.key, selected });
    if (group.mode === 'single') this.openKey.set(null);
  }

  selectedSummary(group: CompactFilterGroup): string {
    if (!group.selected.length) return 'All';
    const names = group.options
      .filter(option => group.selected.includes(option.id))
      .map(option => option.name);
    if (names.length <= 2) return names.join(', ');
    return `${names.slice(0, 2).join(', ')} +${names.length - 2}`;
  }
}
