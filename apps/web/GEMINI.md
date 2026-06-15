# Transmuter Web — Frontend Coding Rules

## Stack
Angular standalone components · Tailwind CSS · CSS variables · Libre Franklin typography.

Check `package.json` for the exact installed Angular version before using framework-specific APIs.

## Required Context
- Root rules: `../../AGENTS.md`
- Durable context: `../../docs/team/CODEX_CONTEXT.md` for launch, hostnames, release state, and known follow-ups.
- Design system: `../../team/DESIGN_SYSTEM.md`
- Rupa skills: `../../agents/skills/rupa_skills.md`
- Chitra skills: `../../agents/skills/chitra_skills.md`

## Design System
Use the A&M-inspired Transmuter direction from `../../team/DESIGN_SYSTEM.md`.

- Deep navy, steel blue, light blue accents, white/grey surfaces.
- Libre Franklin typography.
- Square structural geometry, thin dividers, restrained shadows.
- Dense executive layouts built for scanning and repeated operational use.
- CSS variables from `src/styles.css` are the source of truth for theme-sensitive colors.
- Shared component classes include `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.card`, `.glass-panel`, `.input-field`, `.nav-item`, and `.badge-*`.

Do not introduce purple/lavender/violet palettes, purple gradients, decorative blobs/orbs, or rounded pill-heavy SaaS styling unless an existing component contract explicitly requires it.

## Non-Negotiable Rules
- Standalone components only; no NgModules.
- All routes lazy-loaded via `loadComponent`.
- Use `var(--t-*)` tokens for theme-sensitive colors; never hardcode hex colors in components.
- Every component must work in both light and dark mode.
- ARIA labels on all interactive elements.
- No business logic in components; use services for behavior and API access.
- All user-facing workflows need loading, error, empty, and success states where applicable.
- Monetary API values are strings; never use floating-point arithmetic for financial calculations.
- Keep API contracts typed and coordinate backend contract changes with Karya/Vishwa.

## UI Patterns
- Page shell: dense operational layouts, usually `p-8` with clear header rows and direct controls.
- Tables and panels: square borders, thin separators, compact labels, scannable hierarchy.
- Buttons: square, uppercase, high-contrast, with visible hover/focus/active states.
- Forms: `input-field` styling, explicit labels, validation copy, and keyboard-friendly flow.
- Empty states: concise title, useful next action, and no decorative filler.

## Verification
Run relevant checks from `apps/web`:

```bash
npm run build
npm run e2e:real
```

For meaningful UI changes, start the Angular app on port `4300` and verify the real DOM in a browser at desktop and mobile widths. Text must not overlap, clip, or rely on manually created browser state.

## Dev Commands
```bash
npm start -- --port 4300
npm run build
npm run e2e:real
```
