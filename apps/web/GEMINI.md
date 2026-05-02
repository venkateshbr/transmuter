# Transmuter Web — Antigravity Frontend Coding Rules

## Stack
Angular 18 standalone · Tailwind CSS · CSS variables · Inter font

## Design System (Purple Theme)
- **Full spec**: `../../team/DESIGN_SYSTEM.md`
- **Tokens**: `src/styles.css` — all `--t-*` CSS custom properties
- **Tailwind colors**: `tailwind.config.js` — `brand-*` palette

### Color Tokens (Light / Dark)
| Role | Light | Dark |
|------|-------|------|
| Accent | `#7c3aed` (Violet-600) | `#a78bfa` (Violet-400) |
| Background | `#f8f7fc` (lavender) | `#0c0a14` (purple-black) |
| Surface | `#ffffff` | `#16132a` |
| Border | `#e4e0ee` | `#2a2545` |

### Component Classes
| Class | Purpose |
|-------|---------|
| `.btn-primary` | Purple gradient CTA |
| `.btn-secondary` | Outlined button |
| `.btn-ghost` | Transparent tertiary |
| `.card` | Container with hover glow |
| `.glass-panel` | Frosted glass container |
| `.input-field` | Text input with purple focus |
| `.nav-item` | Navigation link |
| `.badge-green/amber/red/purple/teal/gray` | Status badges |

## Non-Negotiable Rules
- Standalone components only (no NgModules)
- All routes lazy-loaded via `loadComponent`
- Use `var(--t-*)` tokens — **NEVER** hardcode hex for theme colors
- Every component must work in both light and dark mode
- ARIA labels on all interactive elements
- No business logic in components — use services
- Template-driven or reactive forms — both acceptable

## Patterns
- Skeleton loading: shimmer animation with `var(--t-surface-raised)` / `var(--t-border)`
- Empty states: centered icon + title + description + CTA
- Row hover: `var(--t-surface-raised)` background
- Brand dot: `color: var(--t-accent)` after headings
- Filter bar: search input + select dropdowns with `input-field` class

## Dev Commands
```bash
npx ng serve --port 4300    # dev server
npx ng build                # production build
npx ng test                 # unit tests
```
