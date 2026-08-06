const IDENTIFIER_PATTERN = /^[a-z][a-z0-9_]*$/;
const IDENTIFIER_TOKEN_PATTERN = /\b[a-zA-Z_][a-zA-Z0-9_]*\b/g;

export function toFinancialKey(label: string, fallback = 'metric'): string {
  const normalized = String(label || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  const startsWithLetter = /^[a-z]/.test(normalized) ? normalized : `${fallback}_${normalized}`;
  return startsWithLetter.replace(/_+/g, '_').slice(0, 120).replace(/_+$/g, '') || fallback;
}

export function uniqueFinancialKey(
  label: string,
  fallback: string,
  existingKeys: string[],
): string {
  const base = toFinancialKey(label, fallback);
  const existing = new Set(existingKeys);
  if (!existing.has(base)) return base;
  let suffix = 2;
  while (existing.has(`${base}_${suffix}`)) suffix += 1;
  return `${base}_${suffix}`;
}

export function financialKeyError(key: string, existingKeys: string[]): string | null {
  if (!key.trim()) return 'Enter a formula key.';
  if (!IDENTIFIER_PATTERN.test(key))
    return 'Use lowercase letters, numbers, and underscores; start with a letter.';
  if (key.length > 120) return 'Formula keys cannot exceed 120 characters.';
  if (existingKeys.includes(key)) return 'This key is already used in this tenant.';
  return null;
}

export function formulaIdentifiers(formula: string | null | undefined): string[] {
  const tokens = String(formula || '').match(IDENTIFIER_TOKEN_PATTERN) || [];
  return [...new Set(tokens)].sort();
}
