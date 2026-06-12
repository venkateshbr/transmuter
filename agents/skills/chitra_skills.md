# Chitra — Design System Skills

## Skill: Component Design Spec Template

```markdown
## Component: [Name]

### Purpose
[One sentence: what does this component do?]

### Variants
- Default, Hover, Focused, Active, Disabled, Loading, Error

### Design Tokens
| Token | Light Mode | Dark Mode |
|-------|-----------|-----------|
| Background | `var(--t-bg)` | `var(--t-bg)` |
| Surface | `var(--t-surface)` | `var(--t-surface)` |
| Text | `var(--t-text-primary)` | `var(--t-text-primary)` |
| Border | `var(--t-border)` | `var(--t-border)` |
| Accent | `var(--t-accent)` | `var(--t-accent)` |

### Spacing
- Padding: `p-4` (16px)
- Gap: `gap-3` (12px)
- Border radius: 8px or less unless an existing component contract differs

### Typography
- Heading: `text-lg font-semibold`
- Body: `text-sm font-normal`
- Caption: `text-xs` with `var(--t-text-tertiary)`

### Accessibility
- Role: `[button|dialog|alert|etc.]`
- ARIA: `aria-label="[description]"`
- Keyboard: `Enter` to activate, `Escape` to dismiss
- Focus visible: high-contrast outline or ring using `var(--t-accent)`

### Interaction States
| State | Background | Border | Text |
|-------|-----------|--------|------|
| Default | `var(--t-surface)` | `var(--t-border)` | `var(--t-text-primary)` |
| Hover | `var(--t-surface-raised)` | `var(--t-accent)` | `var(--t-text-primary)` |
| Focus | `var(--t-surface)` | `var(--t-accent)` | `var(--t-text-primary)` |
| Active | `var(--t-bg)` | `var(--t-accent)` | `var(--t-text-primary)` |
| Disabled | muted surface | `var(--t-border)` | `var(--t-text-tertiary)` |

### Hand-off to Rupa
- [ ] Tokens defined in DESIGN_SYSTEM.md
- [ ] All states specified
- [ ] Responsive breakpoints noted
- [ ] Accessibility requirements clear
```

## Skill: WCAG 2.1 AA Quick Reference

### Color Contrast
- Normal text (< 18px): minimum 4.5:1 ratio
- Large text (≥ 18px or bold ≥ 14px): minimum 3:1 ratio
- UI components: minimum 3:1 ratio

### Token Contrast Review

Use actual rendered token values from `apps/web/src/styles.css` for final contrast checks.

### Current Token Contrast Checks
| Pair | Minimum |
|------|---------|
| `var(--t-text)` on `var(--t-bg)` | WCAG AA normal text |
| `var(--t-muted)` on `var(--t-surface)` | WCAG AA normal text |
| `var(--t-accent)` on `var(--t-bg)` | WCAG AA UI component |
| `var(--t-danger)` on `var(--t-surface)` | WCAG AA UI component |

### Focus Indicators
- All interactive elements MUST have visible focus ring
- Use a visible focus style aligned to `var(--t-accent)`
- Never use `outline-none` without a visible alternative

## Skill: Component Library Governance

Promote a component or pattern to shared usage when:
- At least two feature areas need the same behavior.
- The pattern has stable inputs/outputs and clear empty/loading/error states.
- The design tokens and accessibility states are documented.
- Rupa can test it without feature-specific setup.

Do not create nested card systems or decorative abstractions that hide simple page layout.

## Skill: Automated Accessibility Audit Protocol

For release candidates and major UI changes:
- Run axe-core or pa11y against key authenticated routes.
- Treat keyboard traps, missing accessible names, color contrast failures, and dialog focus issues as release blockers unless Vishwa explicitly defers them.
- File violations as Rupa bugs with route, selector, screenshot, and recommended fix.
- Keep ARIA labels exact and user-facing; avoid generic labels like "button" or "open".

## Skill: Agent UI Patterns

### Confidence Meter
- 90-100%: `emerald-400` — "High confidence"
- 70-89%: `amber-400` — "Medium confidence — review recommended"
- 0-69%: `red-400` — "Low confidence — manual review required"

### HITL Dialog
- Always show: What the agent wants to do, confidence level, and reasoning
- Always offer: Approve, Reject, or Edit before approve
- Never auto-dismiss — require explicit user action
