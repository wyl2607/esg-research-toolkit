# ESG Research Toolkit — Design Baseline

This document defines our own product-facing UI language for ESG analysis work.
Goal: make complex evidence readable, comparable, and trustworthy.

## 0) Design Intent

The interface should feel like an analyst workspace, not a landing page.
Users should quickly answer:

1. Who/what is being analyzed?
2. What is the current signal?
3. How complete/credible is the data?
4. What action or interpretation follows?

Primary direction: **Editorial Warm** (high readability + professional calm).

---

## 1) Visual Character

- Tone: calm, rigorous, evidence-first.
- Interaction style: quiet and predictable; highlights only where action matters.
- Surface feel: “document + tool” hybrid (not glossy SaaS chrome).
- Motion: subtle and functional (state feedback > decoration).

Avoid:
- marketing-style gradients as default background language,
- overly playful iconography,
- decorative effects that compete with data.

---

## 2) Color System (Semantic Roles)

Use color by meaning, not decoration:

- **Canvas**: warm near-white for long reading comfort.
- **Panel**: soft elevated surfaces for controls/cards.
- **Primary accent**: amber/bronze family for key actions and active navigation.
- **Success**: restrained green.
- **Warning**: muted amber/orange.
- **Risk/Error**: softened rose/red.
- **Body text**: dark ink tone (not pure black).
- **Secondary text**: warm gray with WCAG-compliant contrast.

Accessibility rule:
- all body-size text must meet at least WCAG AA contrast,
- low-contrast styling is allowed only for non-essential decorative elements.

---

## 3) Typography Rules

Recommended stack:
- Display/headline: serif style for editorial confidence,
- UI/body: neutral sans for speed and clarity,
- Numeric/unit content: monospaced style where comparison precision matters.

Principles:
- headings should communicate structure, not brand spectacle,
- long company names and evidence snippets must wrap gracefully,
- unit labels should be visually attached to values (never implied).

---

## 4) Layout Architecture

Each page should follow a stable reading flow:

1. Page intent (kicker + title + short context)
2. Controls/filter surface
3. Key signal area (metrics/charts/list)
4. Detail + interpretation blocks

Guidelines:
- prefer modular cards and grouped sections over one giant dashboard slab,
- keep first screen useful without forcing scroll fatigue,
- dense tables are allowed when comparison is primary, but mobile should degrade to cards.

---

## 5) Component Behavior Standards

- **Cards**: mild radius, soft border/shadow, clean hierarchy.
- **Metric blocks**: label + value + unit + optional quality hint.
- **Badges**: only for status/type/readiness; keep vocabulary consistent.
- **Forms**: explicit labels, helper text for units/ranges, clear validation states.
- **Empty/loading/error states**: always intentional and actionable (not raw or silent).
- **Icon-only controls**: must include accessible name (aria-label/title).

---

## 6) Data Presentation Contract

For every critical metric:
- show what it is,
- show unit/context,
- make missing data explicit (e.g., em dash + interpretation hint).

Default analytic page narrative order:

1. Identity (entity + period + source context)
2. Current signal (headline metrics)
3. Data quality/readiness
4. Comparative quantitative detail
5. Interpretation/recommendation

---

## 7) Mobile + Accessibility Baseline

Minimum baseline for “done”:

- responsive navigation (drawer or equivalent),
- no horizontal overflow on primary routes,
- keyboard reachable controls with visible focus state,
- semantic landmarks + ARIA where needed,
- screen-reader-friendly names for controls and chart regions,
- skip-to-content support for keyboard users.

---

## 8) What We Deliberately Do Not Optimize For

- Trendy visual novelty over auditability,
- maximal minimalism that removes context,
- visual density that hides source/evidence provenance.

If tradeoff is needed, prefer **clarity + trust + comparability** over visual flash.
