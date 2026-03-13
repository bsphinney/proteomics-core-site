# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository serves two purposes:

1. **Website Rewrite** — Full rewrite of the UC Davis Proteomics Core Facility website (proteomics.ucdavis.edu). Pages are authored as self-contained HTML/CSS files for the UC Davis SiteFarm (Drupal) CMS.

2. **Impact Report Automation** — Automated script that queries NIH, NSF, PubMed, and internal data to generate comprehensive impact reports for administration and granting agencies.

## Directory Structure

```
scripts/
  impact_report.py        — Main impact report generator (6 data sources, 3 report types)
  nih_impact_report.py    — Original NIH-only script (superseded by impact_report.py)

reports/                  — Auto-generated output (committed to git)
  impact_report_latest.md          — Comprehensive report (all services)
  impact_report_ms_only_latest.md  — Mass spec only (for S10 grants)
  impact_report_aaa_only_latest.md — Amino acid analysis only
  executive_summary.pdf            — One-page visual dashboard
  impact_data.json                 — Machine-readable for website JS
  figures/*.png                    — Charts (9 total)

private_data/             — NOT in git (see .gitignore)
  submissions_export_full.csv      — Stratocore submission records
  orders.csv                       — Stratocore order/invoicing data

pages/                    — New HTML files for SiteFarm (self-contained <style> + <div>)
current_site_content/     — Markdown snapshots of current live site (reference material)

.github/workflows/
  impact-report.yml       — Monthly auto-generation via GitHub Actions
```

## Impact Report Script

### Quick Start
```bash
pip install requests matplotlib
python scripts/impact_report.py                    # Full run (~5 min)
python scripts/impact_report.py --skip-pubmed --skip-pi-lookup  # Fast (~30 sec)
python scripts/impact_report.py --nih-only         # NIH only (~10 sec)
```

### Data Sources (6)
1. **NIH Reporter API** — Grants referencing the proteomics core + Kültz/Phinney grants
2. **NIH Publications + iCite** — Papers linked to S10 instrument grants + citation metrics
3. **NSF Award API** — NSF awards at UC Davis related to proteomics/mass spec
4. **PubMed E-utilities** — Publications by core personnel + grant acknowledgments
5. **Stratocore Submissions + Orders** — Usage stats, revenue, department breakdown (private)
6. **PI Grant Discovery** — Looks up each submission PI in NIH/NSF by name

### Key People
- **Brett Phinney** — Core Director, PI on S10 instrument grants
- **Dietmar Kültz** — Faculty Advisor (NSF-funded, name has umlaut: Kültz)
- **Core Staff**: Gabriela Grigorean, Michelle Salemi, John Schulze, Lauren Dixon

### Private Data
Files in `private_data/` are exported from Stratocore and must NOT be committed to git. The grant information extracted from them CAN be public (in reports/).

## Website Pages

### Architecture & Conventions
- No build system — static HTML/CSS only
- Styles scoped under wrapper classes (e.g., `.pcf-home-wrapper`)
- CSS variables for UC Davis brand: `--ucd-blue: #022851`, `--ucd-gold: #FFBF00`, `--ucd-gold-dark: #DAAA00`
- Class names use `pcf-` prefix to namespace within the CMS
- Images reference `proteomics.ucdavis.edu` hosted assets

### Workflow
1. Edit `.html` files in `pages/`
2. Preview locally in browser
3. Run mandatory 5-agent review (see below)
4. Paste into SiteFarm's body field using "Full HTML" text format

## Agent Usage — ALWAYS PARALLELIZE

Always spawn multiple agents in parallel whenever possible.

## Review Process — MANDATORY

After any page content revision, spawn five review agents in parallel:
1. **Proteomics Expert** — Verify MS terminology, instruments, workflows
2. **Biological Researcher** — Clarity for potential users (PIs, students)
3. **Industry Expert** — Positioning, pricing, competitive claims
4. **Statistician** — Quantitative claims, numbers in context
5. **Web Design Expert** — Layout, accessibility, WCAG, responsive design
