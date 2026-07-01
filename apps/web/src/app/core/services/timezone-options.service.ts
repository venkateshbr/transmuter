import { Injectable, inject, signal } from '@angular/core';
import { ApiService } from './api.service';

export interface TimezoneOption {
  value: string;
  label: string;
}

@Injectable({ providedIn: 'root' })
export class TimezoneOptionsService {
  private readonly api = inject(ApiService);
  private readonly loaded = signal(false);
  private readonly optionsState = signal<TimezoneOption[]>([
    this.toOption(this.browserTimezone()),
  ]);

  readonly options = this.optionsState.asReadonly();

  load(): void {
    if (this.loaded()) return;
    this.loaded.set(true);
    this.api.get<{ items: TimezoneOption[] }>('/meetings/timezones').subscribe({
      next: response => {
        const options = this.normalizedOptions(response.items || []);
        if (options.length) this.optionsState.set(options);
      },
      error: () => {
        this.optionsState.set(this.normalizedOptions(this.optionsState()));
      },
    });
  }

  browserTimezone(): string {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  }

  optionsWithCurrent(currentValue?: string | null): TimezoneOption[] {
    const current = String(currentValue || '').trim();
    const options = this.optionsState();
    if (!current || options.some(option => option.value === current)) {
      return options;
    }
    return [this.toOption(current), ...options];
  }

  private normalizedOptions(options: TimezoneOption[]): TimezoneOption[] {
    const byValue = new Map<string, TimezoneOption>();
    [this.toOption(this.browserTimezone()), this.toOption('UTC'), ...options]
      .filter(option => option.value)
      .forEach(option => {
        byValue.set(option.value, {
          value: option.value,
          label: option.label || option.value.replace(/_/g, ' '),
        });
      });
    return Array.from(byValue.values()).sort((a, b) => {
      if (a.value === this.browserTimezone()) return -1;
      if (b.value === this.browserTimezone()) return 1;
      if (a.value === 'UTC') return -1;
      if (b.value === 'UTC') return 1;
      return a.value.localeCompare(b.value);
    });
  }

  private toOption(value: string): TimezoneOption {
    return { value, label: value.replace(/_/g, ' ') };
  }
}
