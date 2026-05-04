# Transmuter Design System

**Owner**: UI Team (Chitra / Rupa)  
**Last Updated**: 2026-05-04  
**Status**: Living Document — A&M-Inspired Consulting Theme

This document is the authoritative design reference for Transmuter frontend work.
Every new page, component, dashboard, modal, and control must follow this system.

## Design Direction

Transmuter now uses an Alvarez & Marsal-inspired professional services aesthetic:
fact-driven, direct, structural, and executive. The UI should feel like a serious
consulting operating room, not a SaaS marketing surface.

Core principles:

1. **Deep navy authority** — Use the navy/steel-blue system in `apps/web/src/styles.css`.
2. **Fact-driven clarity** — Favor dense, scannable layouts with clear hierarchy.
3. **Structural geometry** — Prefer square edges, thin dividers, left rules, and precise alignment.
4. **Editorial restraint** — Avoid decorative blobs, pastel washes, purple gradients, and playful softness.
5. **Theme parity** — Light and dark themes must be implemented through CSS variables.

## Source Of Truth

Use these files before styling any frontend work:

- `apps/web/src/styles.css` — CSS variables and shared component classes.
- `apps/web/tailwind.config.js` — font and brand color mappings.
- `apps/web/src/app/app.ts` — top navigation and app shell reference.
- `apps/web/src/app/features/dashboard/dashboard.component.ts` — first-screen reference.

## Color Tokens

All theme-sensitive colors must use CSS variables. Do not hardcode hex values in
new components unless the value is a semantic chart/status color that cannot be
expressed through existing tokens.

Light theme:

| Token | Value | Usage |
|---|---:|---|
| `--t-bg` / `--t-bg-page` | `#f4f6f8` | Page background |
| `--t-surface` / `--t-bg-card` | `#ffffff` | Cards, panels, modals |
| `--t-surface-raised` | `#edf2f6` | Raised bands, filter bars |
| `--t-border` | `#cfd8e2` | Default border |
| `--t-border-strong` | `#9aaabe` | Hover/active border |
| `--t-text-primary` | `#071f3c` | Primary copy and headings |
| `--t-text-secondary` | `#4c6178` | Secondary copy |
| `--t-text-tertiary` | `#77879a` | Labels and metadata |
| `--t-primary` | `#071f3c` | Brand navy and executive blocks |
| `--t-accent` | `#0c4f86` | Links, active states, CTAs |
| `--t-blue-light` | `#63a9d8` | Accent rules and structural marks |

Dark theme uses the same token names with navy surfaces and light-blue accents.
Never branch styling with separate light/dark hardcoded palettes when a token exists.

## Typography

Font family is `Libre Franklin`, falling back to Franklin/Arial-style sans-serif.

Rules:

- Headings: bold or black weight, no negative tracking, no oversized marketing hero type inside app surfaces.
- Labels: uppercase, small, bold, and moderately tracked.
- Body: compact, readable, usually `text-sm` or `text-xs` in dense panels.
- Buttons/nav: uppercase, bold, direct language.

Avoid generic soft SaaS typography, exaggerated gradients, or decorative script/display fonts.

## Components

Use shared classes first:

- Buttons: `.btn-primary`, `.btn-secondary`, `.btn-ghost`
- Cards/panels: `.card`, `.glass-panel`
- Inputs/selects/textareas: `.input-field`
- Badges: `.badge-green`, `.badge-amber`, `.badge-red`, `.badge-purple`, `.badge-gray`, `.badge-teal`
- Navigation: `.nav-item`

Current component treatment:

- Buttons are square, uppercase, high-contrast, and may use an inset light-blue rule on hover.
- Cards are square, bordered, restrained, and use subtle navy shadows.
- Inputs are square, bordered, white/surface-backed, and focus with a navy/blue ring.
- Badges are squared, compact, uppercase, and semantic.
- Navigation uses uppercase text, thin active rules, and tight spacing.

## Layout Patterns

Use app-like, operational layouts:

- Page shell: `p-8 space-y-8` or `p-8 space-y-10`.
- Header row: title/subtitle on left, direct controls on right.
- Data panels: bordered tables/cards with thin separators.
- Hero/summary bands: deep navy blocks with simple light-blue geometric rules.
- Metrics: large bold numerals with small uppercase labels.

Cards should not be nested inside other cards unless the inner card is a repeated item,
modal, or framed tool. Prefer full-width bands and unframed grouping for sections.

## Anti-Patterns

Do not introduce:

- Purple, lavender, violet, or purple-blue gradients.
- Decorative orbs, bokeh, blob backgrounds, or blurred gradient shapes.
- Rounded pill-heavy SaaS UI unless the existing component requires it.
- Large marketing landing-page composition inside the authenticated app.
- Hardcoded theme colors in Angular templates.
- Text buttons where a standard icon button is clearer.
- SVG logo copies or trademarked A&M marks.

The design may be inspired by Alvarez & Marsal’s public visual direction, but do not
copy A&M trademarks, logos, or proprietary assets.

## Angular Rules

- Standalone components only.
- Lazy-loaded routes.
- CSS variable tokens for all theme-sensitive colors.
- Light and dark support through existing `.dark` variables.
- ARIA labels on all interactive elements.
- Use Material Icons already loaded by `styles.css` unless a component has an established alternative.
- Keep business logic out of components; use services for behavior.

## Verification

For meaningful frontend changes, run:

```bash
/Users/vramakrishnaiah/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/typescript/bin/tsc --noEmit -p tsconfig.app.json
/Users/vramakrishnaiah/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/@angular/compiler-cli/bundles/src/bin/ngc.js -p tsconfig.app.json
```

When possible, start the Angular dev server and perform a browser screenshot check at
desktop and mobile widths. Confirm text does not overlap or clip, especially in the top nav.
