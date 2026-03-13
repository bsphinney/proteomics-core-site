# Website Recommendations — Comprehensive

Compiled from competitor analysis, education content research, modern web features research, and all reviewer feedback. 2026-03-13.

---

## Priority 1: High-Impact Content Additions

### "Which Service Is Right for You?" Decision Tool
An interactive flowchart or wizard: "What's your sample type?" -> "What's your biological question?" -> recommended service + estimated cost. This is the #1 feature gap vs. competitors (Broad, UCSF, Fred Hutch all have versions). Can be built as inline HTML/JS within SiteFarm.

### Publications & Impact Page
- List every paper citing the facility, organized by research area and year
- Add a counter to homepage stats bar (e.g., "57+ NIH Grants Supported")
- Quarterly: pick one paper and write a 300-word case study with PI permission
- Collect one-sentence testimonials from PIs when they publish

### "For Grant Writers" Page
- Downloadable facility description (PDF)
- Boilerplate methods text for NIH/NSF grants
- Equipment list formatted for grant applications
- Letters of support process
- Experimental design consultation offer

### Sample Requirements Tables (per service page)
- Minimum protein amount, acceptable buffers, incompatible detergents, sample volume, format
- Pre-submission checklist per service (Harvard Taplin model)
- Reduces failed submissions and saves staff time

### Expected Output Metrics (per service page)
- "From 50ug cell lysate, expect 6,000-8,000 protein IDs"
- Turnaround time per service (not just in FAQ)
- Data deliverables: what formats, what analysis is included

---

## Priority 2: New Pages to Create

### Persona-Based Landing Pages
- "Proteomics for Cancer Researchers"
- "Proteomics for Plant Biologists"
- "Proteomics for Neuroscience"
- "Proteomics for Clinical/Translational Research"
Each speaks directly to that community's sample types and questions. Great for SEO.

### Comparison Content (SEO magnets)
- "DDA vs DIA: Which Approach Is Right for Your Experiment?"
- "Proteomics vs Transcriptomics: Why Protein-Level Data Matters"
- "TMT vs Label-Free Quantification: A Practical Guide"
These rank well in Google and attract researchers at the decision point.

### "Getting Started" / Onboarding Page
- Step-by-step visual guide for first-time users
- What to expect timeline (sample to publication)
- "Before You Submit" checklist
- Link to schedule consultation

### Cross-Linking and TMT Pages (currently placeholders)
- Need to be written from scratch with full service descriptions

---

## Priority 3: Homepage Improvements

### Content Changes (from 5-reviewer feedback)
- Fix "Protein Protein Interactions" -> "Protein-Protein Interactions"
- Add DIA mention explicitly
- List instruments (timsTOF HT, Fusion Lumos, Exploris 480)
- Add "Schedule a Consultation" CTA button
- Replace "High-Depth" stat with concrete number (e.g., "57+" grants or "3,000+" proteins)
- Qualify "$210/sample" with what's included and tier
- Soften "Species Agnostic" to "Multi-Species Compatible"
- Add Lauren Dixon to team section
- Expand acronyms at first use
- Add link to pricing page
- Mention turnaround times
- Mention sample types beyond biofluids

### Design Changes (from web design expert)
- Add focus-visible styles (accessibility critical)
- Convert team photos to `<img>` tags with alt text
- Make service cards fully clickable
- Add 480px mobile breakpoint
- Add hero entrance animation (fade-in sequence)
- Add scroll-based card animations
- Use `<section>` semantic elements
- Card headers should be `<h3>` tags
- Darken #666 text to #555 for WCAG compliance
- Add `prefers-reduced-motion` media query
- Add iconography to service cards

---

## Priority 4: Social Media & Ongoing Content

### YouTube (highest long-term ROI)
- 5-10 short videos (3-5 min each): sample prep, data analysis basics, "what is TMT labeling"
- You already have a channel (@UCDavisProteomics) — expand it

### Cross-Platform Posting
- 1 post/week on Twitter/X + BlueSky + LinkedIn
- Alternate: publication highlights, tips, facility news
- Tag PIs when their papers come out (best organic reach)

### Blog/News Section
- Monthly posts about new methods, instrument updates, user success stories
- Keeps site fresh and signals active facility

---

## Priority 5: Interactive Features (all feasible in SiteFarm inline HTML/CSS/JS)

### Service Recommendation Quiz (~150 lines HTML/CSS/JS)
4-5 step wizard: sample type -> goal -> organism -> sample count -> recommended service. Uses hidden div panels toggled by JS. No server needed.

### Cost Estimator Calculator (~100 lines JS)
User selects: sample type (protein/peptide), tier (UC Davis/Non-Profit/Industry), count, add-ons (enrichment $50). Displays estimated total. Reduces staff email burden.

### Animated Stats Counter (~30 lines JS)
Numbers count up from 0 when scrolled into view using IntersectionObserver + requestAnimationFrame. Add to Impact Bar.

### Accordion FAQ (zero JS!)
Use native HTML `<details>/<summary>` elements. Add JSON-LD `FAQPage` structured data for Google rich snippets — immediate SEO boost.

### Tabbed Service Comparison
CSS-only tabs using hidden radio inputs + sibling selectors. Side-by-side comparison without navigating multiple pages.

### Protein Count Comparison Bar Chart
Animated horizontal bars: "Standard Plasma: ~300" vs "Nanotrap: 3,000+". CSS bars with IntersectionObserver trigger. Visualizes the value proposition.

### Instrument Comparison Chart
Side-by-side feature matrix of 3 instruments with "Best For" badges. Static HTML table with optional toggle view.

### Before/After Data Comparison
Split-screen or slider showing standard vs Nanotrap protein coverage. ~20 lines JS for draggable divider.

### Testimonial Carousel
3-5 rotating PI quotes. CSS scroll-snap + JS auto-advance. No external library needed.

### Collaborator Logo Grid
Grayscale logos that colorize on hover. CSS grid + filter transitions.

### Facility Timeline
Vertical timeline of milestones (2005 established, instruments acquired, etc.). Pure CSS with ::before pseudo-elements.

### Pricing Table with Tier Highlighting
Three-column table (UC Davis/Non-Profit/Industry). User clicks their tier to highlight. localStorage persists selection.

---

## SEO Quick Wins

### JSON-LD Structured Data (inline `<script>` blocks, zero visual impact)
- `FAQPage` schema — enables Google FAQ rich snippets
- `ResearchOrganization` for the facility
- `Service` for each service offering
- `Course` for the Short Course
- `ContactPoint` for contact info

### Semantic HTML
- Use `<section>`, `<article>`, `<nav>` instead of `<div>`
- Add `aria-label` to sections
- Convert background-image divs to `<img>` with alt text

### Things to Avoid in SiteFarm
- External JS libraries via CDN (CSP may block)
- `position: fixed` elements (conflicts with SiteFarm header/footer)
- Auto-playing video
- localStorage for anything critical

---

## Competitor Differentiators UC Davis Already Has (Preserve These)

1. Transparent public pricing (many facilities hide prices)
2. Annual hands-on short course (rare — major differentiator)
3. YouTube channel and virtual course
4. Open protocols library
5. Named team with photos on homepage
6. Deep biofluid featured service with specific metrics
7. NIH grant abstract describes facility as "the sole resource in the area"
