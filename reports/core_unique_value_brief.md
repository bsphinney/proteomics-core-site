# UC Davis Proteomics Core Facility — Publication & Citation Data for Grant Application

## Context for the AI agent

You are helping Brett Phinney (Director, UC Davis Proteomics Core Facility) populate publication/citation fields in a grant application. The existing pipeline at `/Users/brettphinney/Documents/proteomics_web_site/` already has most of this data. Key files:

- **`reports/impact_data.json`** — structured metrics (already populated as of 2026-04-12)
- **`reports/executive_summary.md`** — formatted narrative (generated 2026-03-13, needs refresh)
- **`reports/personnel_publications.md`** — full publication + citation breakdown by person (generated 2026-04-12)
- **`reports/audit/personnel_publications.csv`** — raw data
- **`reports/publications_2026-04-12.csv`** — consolidated publication list

---

## Already-populated data (from existing pipeline)

### Personnel Google Scholar metrics

| Person | Total Citations | h-index | i10-index | 5-yr Citations |
|--------|---------------:|--------:|---------:|---------------:|
| **Brett S Phinney** | **10,994** | **53** | **122** | 5,318 |
| **Michelle R Salemi** | **3,934** | **34** | **62** | 3,118 |
| Dietmar Kültz | 12,259 | 52 | 108 | 3,801 |

### Personnel PubMed + iCite metrics

| Person | PubMed Papers | PubMed Citations (iCite) | Mean RCR |
|--------|-------------:|------------------------:|--------:|
| Brett Phinney | 110 | 4,194 | 1.65 |
| Michelle Salemi | 28 | 683 | 1.50 |
| Gabriela Grigorean | 29 | 648 | 1.77 |
| John Schulze | 12 | 725 | 4.19 |
| Lauren Dixon | 7 | 251 | 2.71 |
| Dietmar Kültz | 113 | 6,401 | 1.90 |

*RCR = Relative Citation Ratio (NIH iCite; 1.0 = field-average). All core staff are above field average.*

### Papers acknowledging the Proteomics Core
- **80 verified papers** (PubMed search: "Proteomics Core Facility" AND Davis)
- **3,036 total citations** for the verified set
- Top paper: 400 citations — Gram-negative bacteria + Alzheimer (Neurology, 2016)

### Instrument grant publications
- **70 papers** linked to S10 instrument grants
- **2,098 total citations**

### Funding held by Core users
- **$1.65 billion** in active federal funding held by 149 PIs who use the Core
- UC Davis PIs: 64, holding $605M
- External PIs: 85, holding $1.04B

### Core operations
- 4,311 submissions, 8,866 samples, 1,514 unique PIs, 643 institutions
- $5.48M revenue (Jul 2020 – Mar 2026)

---

## For the grant question: "Describe the unique value of the core"

### What critical capabilities are offered that are not otherwise available?

**1. Instrumentation**
- **Bruker timsTOF HT** — only trapped ion mobility MS on the UC Davis campus. 4D proteomics (RT × m/z × 1/K₀ × intensity) enables 30-50% deeper DIA coverage than Orbitrap-only workflows.
- **Thermo Orbitrap Exploris 480** — high-resolution targeted and discovery proteomics.
- **Thermo Fusion Lumos** — tribrid architecture supporting HCD, CID, ETD, EThcD for glycoproteomics, cross-linking MS, and top-down proteomics unavailable on any other campus instrument.

**2. Open-source QC infrastructure (STAN)**
- STAN (Standardized proteomic Throughput ANalyzer): automated real-time instrument QC monitoring.
- 1,166+ longitudinal QC submissions tracked across 3 instruments.
- Community benchmark with cross-institutional comparison (2 labs, growing).
- Automated gating prevents sample runs on degraded instruments.
- No commercial equivalent combines automated gating + community benchmarking + longitudinal trending.
- GitHub: https://github.com/bsphinney/stan | Dashboard: https://brettsp-stan.hf.space

**3. Staff expertise spanning 14+ research domains**
- 130 unique publications across infectious disease, cardiovascular, neuroscience, cancer, ophthalmology, food science, agriculture, nutrition, microbiology, environmental health, reproductive biology, vascular biology, veterinary medicine, public health.
- Combined h-index: Phinney 53, Salemi 34, Grigorean (29 papers, 648 citations, RCR 1.77).
- Method development for non-standard samples (bats, thermophilic bacteria, plant proteins, extracellular vesicles, nasal swabs, infant formula) that CROs cannot replicate.

**4. Alternatives comparison**

| Alternative | Limitation |
|---|---|
| Campus shared instruments (no staff) | No QC monitoring, no method development, requires PI-side MS expertise |
| Peer institution cores (UCSF, Stanford) | Sample shipping risk, no timsTOF, longer turnaround, no integrated QC benchmark |
| Commercial CROs (Biognosys, Evotec) | $500-2000/sample, 4-8 week turnaround, no customization, no raw data access |
| Individual PI instruments | No cross-campus QC standards, dedicated FTE required, single-point-of-failure |

---

## What the agent still needs to do

1. The `impact_data.json` already has `publications.total: 165` and `instrument_grant_publications: {total: 70, total_citations: 2098}` — these ARE populated (the user's earlier message about zeros may have been from an older version).
2. The `executive_summary.md` shows "Publications from instrument grants: 69" and "Total citations: 2,048" — slightly older numbers than impact_data.json. Regenerate from the pipeline if needed: `cd /Users/brettphinney/Documents/proteomics_web_site && python scripts/consolidate_publications.py`
3. For the grant narrative, combine the personnel metrics table + the 14 research domains + the STAN infrastructure + the alternatives table into a concise paragraph matching the grant's word limit.
4. **Emphasize**: $1.65B in active federal funding held by Core users — this is the single most compelling ROI metric for reviewers.
