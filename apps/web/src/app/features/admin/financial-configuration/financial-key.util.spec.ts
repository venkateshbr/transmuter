import {
  financialKeyError,
  formulaIdentifiers,
  toFinancialKey,
  uniqueFinancialKey,
} from './financial-key.util';
import { describe, expect, it } from 'vitest';

describe('financial key utilities', () => {
  it('generates identifier-safe snake-case formula keys', () => {
    expect(toFinancialKey('Gross Margin Uplift (%)')).toBe('gross_margin_uplift');
    expect(toFinancialKey('2028 Revenue', 'metric')).toBe('metric_2028_revenue');
  });

  it('keeps uniqueness local to the supplied tenant key set', () => {
    expect(uniqueFinancialKey('Revenue Uplift', 'metric', ['revenue_uplift'])).toBe(
      'revenue_uplift_2',
    );
    expect(uniqueFinancialKey('Revenue Uplift', 'metric', [])).toBe('revenue_uplift');
  });

  it('validates formula identifiers and tenant-local duplicates', () => {
    expect(financialKeyError('Revenue Uplift', [])).toContain('lowercase');
    expect(financialKeyError('revenue_uplift', ['revenue_uplift'])).toContain('tenant');
    expect(financialKeyError('revenue_uplift', [])).toBeNull();
  });

  it('extracts unique formula dependencies including baseline aliases', () => {
    expect(formulaIdentifiers('(revenue_uplift - cost_savings) / baseline_revenue_uplift')).toEqual(
      ['baseline_revenue_uplift', 'cost_savings', 'revenue_uplift'],
    );
  });
});
