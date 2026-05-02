# Transmuter Design System

**Owner**: UI Team (Chitra — Frontend Designer)
**Last Updated**: 2026-04-30
**Status**: Living Document — **Purple Theme**

---

## Design Philosophy

Transmuter is a portfolio transformation management platform. The design philosophy centers on five principles:

1. **Purple-first brand identity** — A cohesive purple/white/lavender color system conveys trust, premium quality, and clarity. The `Violet-600` accent (`#7c3aed`) is the hero color across both light and dark modes, with lighter variants for dark surfaces.
2. **Information density done right** — Users need data (initiatives, milestones, statuses), but it must be scannable. We use visual hierarchy, muted labels, and bold values to guide the eye.
3. **Light + Dark theme parity** — Every component works equally well in both themes. CSS variable tokens adapt automatically; no hardcoded colors.
4. **Consistency over novelty** — Every component follows the design system. Cards, the `.btn-*` classes, `.badge-*` badges, and the `--t-*` CSS variable tokens ensure visual uniformity.
5. **Mobile-aware, desktop-first** — The top nav and content use responsive breakpoints. Content uses `max-w-[1400px]` centering with responsive padding.

---

## Color System

### CSS Variable Tokens (Theme-Aware)

All theme tokens are defined in `apps/web/src/styles.css` and extended via `apps/web/tailwind.config.js`.

#### Light Theme (Default `:root`)

| Token | Value | Usage |
|-------|-------|-------|
| `--t-bg` | `#f8f7fc` | Page background (lavender tint) |
| `--t-surface` | `#ffffff` | Primary panel/card surface |
| `--t-surface-raised` | `#f0eef5` | Inputs, filter bars, raised surfaces |
| `--t-border` | `#e4e0ee` | Borders (purple-gray) |
| `--t-text-primary` | `#1a1035` | High-contrast text (deep purple-black) |
| `--t-text-secondary` | `#6b6280` | Secondary text (purple-tinted gray) |
| `--t-accent` | `#7c3aed` | **Violet-600** — primary CTA, active states, links |
| `--t-accent-hover` | `#6d28d9` | Violet-700 — button/link hover |
| `--t-accent-soft` | `rgba(124,58,237,0.08)` | Subtle purple wash (nav active bg, badge bg) |
| `--t-accent-ring` | `rgba(124,58,237,0.25)` | Focus ring color |
| `--t-accent-gradient` | `linear-gradient(135deg, #7c3aed, #a855f7)` | CTA button gradient |

#### Dark Theme (`.dark`)

| Token | Value | Usage |
|-------|-------|-------|
| `--t-bg` | `#0c0a14` | Deep purple-black background |
| `--t-surface` | `#16132a` | Dark purple panel surface |
| `--t-surface-raised` | `#1e1a35` | Slightly lifted purple surface |
| `--t-border` | `#2a2545` | Purple-tinted dark borders |
| `--t-text-primary` | `#ece8f5` | Lavender off-white text |
| `--t-text-secondary` | `#a099b4` | Muted lavender text |
| `--t-accent` | `#a78bfa` | **Violet-400** — lighter purple for dark surfaces |
| `--t-accent-hover` | `#c4b5fd` | Violet-300 — even lighter on hover |
| `--t-accent-soft` | `rgba(167,139,250,0.12)` | Dark-mode purple wash |
| `--t-accent-ring` | `rgba(167,139,250,0.30)` | Dark-mode focus ring |
| `--t-accent-gradient` | `linear-gradient(135deg, #a78bfa, #c084fc)` | Dark-mode CTA gradient |

### Semantic Status Colors (Static)

| Status | Light BG | Light Text | Dark BG | Dark Text |
|--------|----------|-----------|---------|-----------|
| Green (on track) | `#dcfce7` | `#166534` | `rgba(16,185,129,0.15)` | `#86efac` |
| Amber (at risk) | `#fef3c7` | `#92400e` | `rgba(245,158,11,0.15)` | `#fcd34d` |
| Red (blocked) | `#fee2e2` | `#991b1b` | `rgba(239,68,68,0.15)` | `#fca5a5` |
| Purple (active) | `#ede9fe` | `#6d28d9` | `rgba(167,139,250,0.15)` | `#c4b5fd` |
| Teal (info) | `#ccfbf1` | `#134e4a` | `rgba(20,184,166,0.15)` | `#5eead4` |
| Gray (neutral) | `#f3f4f6` | `#374151` | `rgba(107,114,128,0.15)` | `#d1d5db` |

### Tailwind Brand Colors (Extended)

Defined in `tailwind.config.js`:

| Name | Hex | Usage |
|------|-----|-------|
| `brand-primary` | `#7c3aed` | Violet-600 — primary actions |
| `brand-hover` | `#6d28d9` | Violet-700 — hover states |
| `brand-light` | `#a78bfa` | Violet-400 — dark mode accent |
| `brand-muted` | `#ede9fe` | Violet-100 — light badge fills |
| `brand-subtle` | `#f5f3ff` | Violet-50 — ultra-light wash |
| `brand-accent` | `#a855f7` | Purple-500 — gradient endpoints |
| `brand-success` | `#10b981` | Emerald-500 — positive values |
| `brand-warning` | `#f59e0b` | Amber-500 — warnings |
| `brand-danger` | `#ef4444` | Red-500 — errors |

### Gradient Patterns

| Pattern | Value | Usage |
|---------|-------|-------|
| **Primary CTA** | `linear-gradient(135deg, #7c3aed, #a855f7)` | Main action buttons |
| **CTA Shadow** | `box-shadow: 0 2px 8px rgba(124,58,237,0.25)` | Button elevation |
| **CTA Hover Shadow** | `box-shadow: 0 4px 14px rgba(124,58,237,0.35)` | Button hover elevation |
| **User Avatar** | `linear-gradient(135deg, var(--t-accent), #a855f7)` | Profile circle |
| **Card Accent Border** | `linear-gradient(180deg, #7c3aed, #a855f7)` | Optional left-border |

---

## Typography Scale

**Font Family**: `Inter` (300/400/500/600/700 weights), loaded via Google Fonts.

Configured in Tailwind as `fontFamily.sans: ['Inter', 'sans-serif']`.

| Element | Class/Size | Weight | Color Token |
|---------|-----------|--------|-------------|
| Page heading | `text-3xl font-bold tracking-tight` | 700 | `--t-text-primary` |
| Section heading | `text-lg font-semibold` (1.125rem) | 600 | `--t-text-primary` |
| Brand dot | `text-[var(--t-accent)]` | — | `--t-accent` |
| Table header | `text-[10px] font-semibold uppercase` | 600 | `--t-text-secondary` |
| Table cell | `text-sm` (0.875rem) | 400 | `--t-text-primary` or `--t-text-secondary` |
| Form label | `text-sm font-medium` (0.875rem) | 500 | `--t-text-secondary` |
| Body text | `text-sm` (0.875rem) | 400 | `--t-text-secondary` |
| Muted / timestamps | `text-xs` (0.75rem) | 400 | `--t-text-secondary` |
| Badge / pill | `text-xs font-semibold` or `font-medium` | 600 | Contextual |
| Monospace values | `text-xs font-mono` | 400 | `--t-text-secondary` |

---

## Component Inventory

### Buttons

#### `.btn-primary`
- **Background**: `var(--t-accent-gradient)` — purple gradient
- **Shadow**: `0 2px 8px var(--t-accent-ring)`
- **Hover**: Deeper gradient + elevated shadow + subtle lift (`translateY(-1px)`)
- **Active**: Pressed down, reduced shadow
- **Text**: White, always
- **Border-radius**: `rounded-lg` (8px)

#### `.btn-secondary`
- **Background**: `var(--t-surface-raised)`
- **Border**: `1px solid var(--t-border)`, hover to `var(--t-accent)`
- **Text**: `var(--t-text-primary)`

#### `.btn-ghost`
- **Background**: Transparent
- **Hover**: `var(--t-accent-soft)` background, `var(--t-accent)` text
- **Use for**: Theme toggle, close buttons, tertiary actions

### Cards

#### `.card`
- **Background**: `var(--t-surface)`
- **Border**: `1px solid var(--t-border)`
- **Hover**: Border to `var(--t-accent)`, shadow to `0 4px 16px var(--t-accent-ring)`
- **Border-radius**: `rounded-xl` (12px)

#### `.glass-panel`
- **Background**: `rgba(255,255,255,0.85)` (light) / `rgba(22,19,42,0.85)` (dark)
- **Border**: `1px solid var(--t-border)`
- **Backdrop blur**: `blur(4px)` via `backdrop-blur-sm`

### Inputs

#### `.input-field`
- **Background**: `var(--t-surface-raised)`
- **Border**: `1px solid var(--t-border)`
- **Focus**: Border to `var(--t-accent)`, ring `0 0 0 2px var(--t-accent-ring)`
- **Placeholder**: `var(--t-text-secondary)`
- **Border-radius**: `rounded-lg` (8px)

### Badges

All badges: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium`

| Class | Light BG | Light Text | Dark BG | Dark Text |
|-------|----------|-----------|---------|-----------|
| `.badge-green` | `#dcfce7` | `#166534` | `rgba(16,185,129,0.15)` | `#86efac` |
| `.badge-amber` | `#fef3c7` | `#92400e` | `rgba(245,158,11,0.15)` | `#fcd34d` |
| `.badge-red` | `#fee2e2` | `#991b1b` | `rgba(239,68,68,0.15)` | `#fca5a5` |
| `.badge-teal` | `#ccfbf1` | `#134e4a` | `rgba(20,184,166,0.15)` | `#5eead4` |
| `.badge-gray` | `#f3f4f6` | `#374151` | `rgba(107,114,128,0.15)` | `#d1d5db` |
| `.badge-purple` | `#ede9fe` | `#6d28d9` | `rgba(167,139,250,0.15)` | `#c4b5fd` |

### Navigation

#### `.nav-item`
- **Default**: `var(--t-text-secondary)` text, transparent background
- **Hover**: `var(--t-accent-soft)` background, `var(--t-accent)` text
- **Active**: Same as hover + `font-medium`
- **Border-radius**: `rounded-lg` (8px)

---

## Layout Patterns

### Top Navigation Bar (Header)
- **Height**: `h-14` (56px), fixed `top-0`, `z-50`
- **Background**: `var(--t-surface)/95` with `backdrop-blur-sm`
- **Border**: Bottom border `var(--t-border)`
- **Contains**: Logo with purple dot, nav items, theme toggle, CTA button, avatar

### Standard Page Layout
```
Header: Title + Subtitle with purple dot | Action Button (btn-primary)
Filters: Search + select dropdowns (input-field)
Content: Cards or tables with glass-panel or card class
```

### Brand Dot Pattern
The trailing dot after brand names (e.g., "Transmuter**.**", "Initiatives**.**") uses `color: var(--t-accent)` (purple).

---

## Dark Theme Implementation

### Toggle Mechanism
- `ThemeService` uses Angular `signal<boolean>` to toggle `.dark` class on `<html>`
- Persisted to `localStorage` key `theme`
- Falls back to `prefers-color-scheme: dark` media query
- Tailwind `darkMode: 'class'` configuration

### CSS Variable Architecture
- All theme-sensitive values are CSS custom properties in `:root` and `.dark` selectors
- Tailwind config extends colors with `brand-*` names mapping to hex values
- Components use:
  1. CSS variable inline styles: `style="color: var(--t-text-primary);"`
  2. Tailwind with CSS vars: `class="text-[var(--t-accent)]"`
  3. Component classes: `.btn-primary`, `.card`, `.input-field`, etc.

### Transition
- Body: `transition: background-color 0.2s ease, color 0.2s ease`
- Cards: `transition: border-color 0.2s ease, box-shadow 0.2s ease`

---

## Rules for New Components

> **MANDATORY**: Every new component MUST follow these rules.

### 1. Always Use CSS Variable Tokens
- **NEVER** hardcode hex colors for theme-sensitive properties
- Use `var(--t-*)` tokens for all backgrounds, text, borders, and accents
- Exception: Semantic status colors (green/amber/red) may use Tailwind brand utilities

### 2. Support Both Themes
- Every component must be tested in both light and dark mode
- Light backgrounds: Use `var(--t-surface)` or `var(--t-surface-raised)`
- Dark backgrounds: Automatically handled by CSS variables

### 3. Use the Purple Accent
- CTA buttons: `var(--t-accent-gradient)` with `var(--t-accent-ring)` shadow
- Focus rings: `var(--t-accent-ring)` 
- Active/hover states: `var(--t-accent-soft)` background, `var(--t-accent)` text
- Brand dot: `var(--t-accent)` color
- Links: Hover to `var(--t-accent)`

### 4. Use Established Classes
- Buttons: `.btn-primary`, `.btn-secondary`, `.btn-ghost`
- Cards: `.card` or `.glass-panel`
- Inputs: `.input-field`
- Badges: `.badge-green`, `.badge-amber`, `.badge-red`, `.badge-purple`, `.badge-gray`, `.badge-teal`
- Nav: `.nav-item`

### 5. Spacing and Layout
- Page padding: `px-8 pt-8`
- Card padding: `p-5`
- Grid gaps: `gap-4` (16px) standard, `gap-6` (24px) for sections
- Border radius: `rounded-xl` (12px) for cards, `rounded-lg` (8px) for inputs/buttons, `rounded-full` for badges/avatars

### 6. Typography
- Font: `Inter` (already configured)
- Headings: `font-bold` or `font-semibold` with `--t-text-primary`
- Body: `text-sm` with `--t-text-secondary`
- Muted: `text-xs` with `--t-text-secondary`
- Brand dot: `var(--t-accent)` with slightly larger size

---

*This document is the authoritative design reference for the Transmuter frontend. All new components must follow the patterns and tokens described here. When in doubt, use the CSS variable tokens from `styles.css` and the utility classes defined in the `@layer components` block.*
