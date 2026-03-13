# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a **full rewrite** of the UC Davis Proteomics Core Facility website (proteomics.ucdavis.edu). The site runs on UC Davis SiteFarm (Drupal-based CMS). Pages are authored as self-contained HTML/CSS files, then the content is copy/pasted into SiteFarm's "Full HTML" text format body field.

## Directory Structure

```
pages/                    — New HTML files (the deliverables). One file per page.
                            Each file is self-contained <style> + <div> ready to paste into SiteFarm.
current_site_content/     — Markdown snapshots of the current live site (01–25).
                            Used as reference/source material for rewrites.
Frot Page.rtf             — Original homepage (legacy RTF format, being replaced).
```

## Workflow: Editing & Publishing

1. Edit or create `.html` files in `pages/`
2. Preview locally by opening the `.html` file in a browser
3. Run the mandatory 4-agent review (see below)
4. Address review feedback
5. Copy the full file contents and paste into SiteFarm's body field using "Full HTML" text format

## Architecture & Conventions

- **No build system, package manager, or tests** — static HTML/CSS only
- All styles scoped under a wrapper class (e.g., `.pcf-home-wrapper`) to avoid CMS theme conflicts
- CSS custom properties for UC Davis brand colors: `--ucd-blue: #022851`, `--ucd-gold: #FFBF00`, `--ucd-gold-dark: #DAAA00`
- All class names use the `pcf-` prefix to namespace within the CMS
- Images reference `proteomics.ucdavis.edu` hosted assets (uploaded via SiteFarm media)
- Use proper HTML entities (`&reg;`, `&mdash;`, `&amp;`) — no RTF escape sequences
- Each page HTML file starts with a comment block identifying the page and paste instructions

## Site Pages (25 total)

| Page | Source File | Status |
|------|------------|--------|
| Homepage | `pages/homepage.html` | In progress |
| Submissions | — | Not started |
| Biofluid Proteomics (Ceres Nanotrap) | — | Not started |
| Quantitative Discovery | — | Not started |
| Protein Interactions / BioID | — | Not started |
| PTM Discovery | — | Not started |
| Personnel 2026 | — | Not started |
| Short Course | — | Not started |
| FAQ | — | Not started |
| Protocols | — | Not started |
| Prices | — | Not started |
| Proteomics Overview | — | Not started |
| Equipment 2026 | — | Not started |
| Mission and Vision | — | Not started |
| Posters | — | Not started |
| Service Agreements | — | Not started |
| Grant Acknowledgments | — | Not started |
| Cross-Linking | — | Placeholder (needs writing from scratch) |
| TMT Profiling | — | Placeholder (needs writing from scratch) |
| Data Analysis Videos | — | Not started |
| Example Data & Presentations | — | Not started |
| Resources & Background | — | Not started |
| Submissions 2026 | — | Not started |
| Photo Galleries | — | Not started |
| Facility Information | — | Not started |

## Content Source Files

Downloaded page content lives in `current_site_content/` as markdown files (01–25), used as source material for rewriting the site.

## Agent Usage — ALWAYS PARALLELIZE

Always spawn multiple agents in parallel whenever possible. This applies to:
- The 4 mandatory review agents (always run simultaneously)
- Fetching content from multiple URLs
- Writing multiple independent files
- Any independent tasks that don't depend on each other

## Review Process — MANDATORY

After any revision to page content, **always spawn five review agents in parallel** before presenting the final version. Each agent reviews the revised content from a different perspective:

1. **Proteomics Expert** — Verify all mass spectrometry terminology, instrument names, workflows (DIA, DDA, BioID, etc.), and technical claims are accurate and current. Flag any outdated methods or missing best practices.

2. **Biological Researcher** — Review from the perspective of a potential facility user (PI or grad student). Is the content clear and accessible? Are sample requirements, turnaround times, and submission steps easy to understand? Would a non-specialist know what service to choose?

3. **Industry Expert** — Evaluate positioning, pricing language, and competitive claims (e.g., cost-per-protein comparisons). Ensure the facility's value proposition is compelling and that service descriptions align with current industry standards and vendor terminology.

4. **Statistician** — Check any quantitative claims (protein counts, phospho-site numbers, sensitivity comparisons, cost figures). Verify that numbers are presented with appropriate context and that any comparative statements are fair and defensible.

5. **Web Design Expert** — Evaluate layout, visual hierarchy, typography, color/contrast (WCAG compliance), responsive design, whitespace, interactive elements, modern design patterns, accessibility (semantic HTML, ARIA, focus states), and CSS efficiency. Compare against best-in-class institutional sites.
