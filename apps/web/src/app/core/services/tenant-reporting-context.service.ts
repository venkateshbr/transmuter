import { Injectable, inject, signal } from '@angular/core';
import { Observable, finalize, map, shareReplay, tap } from 'rxjs';
import { ApiService } from './api.service';

export interface TenantReportingContext {
  reportingCurrency: string;
  fiscalYearStartMonth: number;
}

@Injectable({ providedIn: 'root' })
export class TenantReportingContextService {
  private readonly api = inject(ApiService);
  private inFlight: Observable<TenantReportingContext> | null = null;

  readonly currency = signal<string | null>(null);
  readonly fiscalYearStartMonth = signal<number | null>(null);

  ensureLoaded(): void {
    this.load().subscribe({ error: () => undefined });
  }

  load(): Observable<TenantReportingContext> {
    if (this.inFlight) return this.inFlight;
    this.currency.set(null);
    this.fiscalYearStartMonth.set(null);
    this.inFlight = this.api.get<any>('/financial-engine-configuration').pipe(
      map(response => ({
        reportingCurrency: this.normalizeCurrency(response?.settings?.reporting_currency),
        fiscalYearStartMonth: this.normalizeFiscalMonth(response?.settings?.fiscal_year_start_month),
      })),
      tap(context => {
        this.currency.set(context.reportingCurrency);
        this.fiscalYearStartMonth.set(context.fiscalYearStartMonth);
      }),
      finalize(() => { this.inFlight = null; }),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.inFlight;
  }

  setContext(currency: string | null | undefined, fiscalYearStartMonth?: number | null): void {
    this.currency.set(this.normalizeCurrency(currency));
    if (fiscalYearStartMonth !== undefined) {
      this.fiscalYearStartMonth.set(this.normalizeFiscalMonth(fiscalYearStartMonth));
    }
  }

  formatMoney(
    value: string | number | null | undefined,
    options: Intl.NumberFormatOptions = {},
  ): string {
    const amount = Number(value || 0);
    const currency = this.currency();
    return new Intl.NumberFormat('en-US', {
      ...(currency ? { style: 'currency', currency } : { style: 'decimal' }),
      maximumFractionDigits: 0,
      ...options,
    }).format(Number.isFinite(amount) ? amount : 0);
  }

  private normalizeCurrency(value: unknown): string {
    const currency = String(value || '').trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(currency)) {
      throw new Error('Tenant reporting currency is unavailable or invalid');
    }
    return currency;
  }

  private normalizeFiscalMonth(value: unknown): number {
    const month = Number(value);
    if (!Number.isInteger(month) || month < 1 || month > 12) {
      throw new Error('Tenant fiscal year start month is unavailable or invalid');
    }
    return month;
  }
}
