# Frontend design system

React 18 + TypeScript (strict) + Vite 5. Plain CSS with tokens (`src/styles/tokens.css`), Inter via `@fontsource-variable/inter` (bundled; no CDN), icons from `lucide-react`. shadcn/ui, Radix and MagicMouse.js are **not used/implemented** (see architecture-decisions).

## Palette and measured contrast (WCAG ratio, computed)
| Pair | Ratio |
|---|---|
| Navy ink `#0B1B3A` on `#FAF8F4` | 16.07 |
| Muted `#3D4B66` on `#FAF8F4` | 8.26 |
| Accent `#1642B8` on `#FAF8F4` / white on accent | 7.90 / 8.38 |
| Status text on tint: supported 9.00, needs-evidence 7.88, related 9.02, none 7.54, uncertain 8.79, error 7.71 | all ≥ 7 |
Placeholder text and native control chrome use browser defaults and were not measured. Form borders use `#8A93A6` (not measured against 3:1 UI-contrast in a tool; visually distinct).

## Layout
Sticky glass navbar (Product, How it works, Privacy, Get started) → hero → workspace (form → progress → results) → How it works → Privacy → footer. Glass effect only on navbar, hero card and form. Breakpoints 860 px and 520 px; touch targets ≥ 44 px (buttons) / 36 px (small).

## Accessibility implemented
Skip link; visible 3 px focus ring; labelled inputs; errors linked with `aria-describedby` + `aria-invalid`; ARIA tabs with arrow-key support; `role=status` live region announcing stage and percent; native `<progress>`; native `<dialog>` for delete confirmation; `<details>` for evidence; statuses use icon + text (not colour alone); `prefers-reduced-motion` and `prefers-contrast` handled. **Not tested** with a screen reader, axe, or in a real browser during development; only type-check, unit tests and a production build were run.

## Behaviour
Form stays mounted (hidden) during a run so "Back to the form" is a retry with inputs intact. Evidence links are rendered only for `https://github.com` URLs. Polling every 1.5 s; 4 consecutive failures end polling with an error. Active analysis id is kept in `sessionStorage`.
