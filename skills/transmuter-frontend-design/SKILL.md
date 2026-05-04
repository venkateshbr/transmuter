---
name: transmuter-frontend-design
description: Use when creating or modifying Transmuter Angular pages, components, app shell UI, dashboards, modals, forms, cards, tables, or any frontend styling. Enforces the A&M-inspired Transmuter design system, CSS variable tokens, accessibility, light/dark support, and repo-specific Angular conventions.
---

# Transmuter Frontend Design

Use this skill for every Transmuter frontend change.

## Required Reference

Read `team/DESIGN_SYSTEM.md` before designing or editing UI. It is the source of truth.

Core files:

- `apps/web/src/styles.css` for tokens and shared classes.
- `apps/web/tailwind.config.js` for font/color mappings.
- `apps/web/src/app/app.ts` for app shell patterns.

## Visual Direction

Default every new component to the A&M-inspired Transmuter system:

- Deep navy, steel blue, light blue accents, white/grey surfaces.
- Libre Franklin / Franklin-style sans-serif typography.
- Square structural geometry, thin dividers, left rules, and restrained shadows.
- Dense, executive, fact-driven layouts.
- Uppercase micro-labels and direct CTA language.

## Must Do

- Use `var(--t-*)` CSS variables for backgrounds, text, borders, focus, and accents.
- Use shared classes: `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.card`, `.glass-panel`, `.input-field`, `.badge-*`, `.nav-item`.
- Preserve light and dark theme support.
- Add ARIA labels to interactive controls.
- Use standalone Angular components and existing lazy route patterns.
- Verify with `tsc --noEmit` and `ngc` after changes.

## Avoid

- Purple/lavender/violet palettes or gradients.
- Decorative blobs, blurred orbs, bokeh, or playful SaaS ornament.
- Large rounded pill-heavy UI unless already established by the component.
- Hardcoded hex colors for theme-sensitive styles.
- A&M logo/trademark copies or proprietary assets.

## Verification Commands

From `apps/web`:

```bash
/Users/vramakrishnaiah/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/typescript/bin/tsc --noEmit -p tsconfig.app.json
/Users/vramakrishnaiah/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/@angular/compiler-cli/bundles/src/bin/ngc.js -p tsconfig.app.json
```
