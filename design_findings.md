# Web Design Review Findings

Review of homepage.html by web design expert agent, 2026-03-13.

---

## Critical Fixes (Accessibility)

- [ ] **Team photos have no alt text** — background-image divs invisible to screen readers. Add `role="img"` + `aria-label` or convert to `<img>` with `object-fit: cover` (preferred)
- [ ] **Featured image div is empty** — needs `role="img"` and `aria-label`
- [ ] **No focus-visible styles** — keyboard users can't see where they are. Add `outline` on `:focus-visible` for buttons, cards, links
- [ ] **No `prefers-reduced-motion`** — animations should be disabled for users who prefer reduced motion
- [ ] **Card headers are `<div>` not headings** — should be `<h3>` for proper heading hierarchy
- [ ] **No semantic landmarks** — use `<section>` instead of `<div>` for hero, services, team, info sections
- [ ] **WCAG contrast failure: #666 text at 0.95rem** — team titles fail AA. Darken to #555 or #4a4a4a
- [ ] **Body text #555 in cards** — borderline. Consider darkening to #444

## Responsive Design

- [ ] **Only one breakpoint (768px)** — need at minimum 480px for small phones
- [ ] **480px breakpoint needed:** hero h1 to 1.5rem, buttons full-width stacked, stat numbers smaller, grid to single column
- [ ] **Team photos too large on mobile** — use `clamp(100px, 30vw, 150px)` for width/height
- [ ] **Featured image `min-width: 300px` can overflow** between 300-768px

## Typography

- [ ] **No consistent type scale** — sizes are ad hoc. Adopt 1.0/1.125/1.25/1.5/2.0/2.5/3.0rem scale
- [ ] **Hero h1 too small** — 2.5rem should be 3.2-3.5rem for stronger hierarchy (3:1 ratio with body text)
- [ ] **h2 sizes too close** — featured (2.2rem) vs section titles (2rem) creates ambiguity
- [ ] **Card headers need `line-height: 1.3`** for multi-line titles
- [ ] **"High-Depth" and "Open" in stat bar** — styled as numbers but they're text. Replace with real numbers or create a `.pcf-stat-text` variant

## Interactive Elements

- [ ] **Cards not fully clickable** — only footer link is clickable. Make entire card an `<a>` or use stretched-link pattern
- [ ] **`transition: all` is too broad** — specify `color, background-color` explicitly for performance
- [ ] **Add arrow hover animation** — translate-x on `.pcf-link-arrow::after` for interactivity signal
- [ ] **Merge two `.pcf-home-wrapper` rule blocks** into one

## Modern Patterns (2026)

- [ ] **Add hero entrance animation** — fade-in sequence for h1, subtitle, buttons (staggered)
- [ ] **Add scroll-based animations** — cards and stats fade up on scroll using `animation-timeline: view()` or IntersectionObserver
- [ ] **Convert team photos to `<img>` tags** — enables alt text, lazy loading, better semantics
- [ ] **Add iconography to service cards** — SVG or Unicode symbols in card headers for visual interest
- [ ] **Featured image should use `aspect-ratio: 16/9`** instead of fixed 280px height

## Missing vs. Top-Tier Sites

- [ ] **No instrument showcase** — top facilities all list their instruments prominently
- [ ] **No testimonials or publication metrics** — "cited in X+ publications" or journal logos
- [ ] **No news/updates feed** — signals the facility is active
- [ ] **No icons anywhere** — every major facility uses icons in service cards and info sections

## Spacing & Code Quality

- [ ] **Mixed spacing units** — standardize on `rem` (currently mixes px and rem)
- [ ] **`<br>` tag between paragraph and list** — use `margin-top` instead
- [ ] **Inline styles** scattered throughout — move to stylesheet
- [ ] **`margin-top: -5px` hack on impact bar** — fragile, find better approach
- [ ] **`box-shadow` transitions are expensive** — use pseudo-element with opacity instead
