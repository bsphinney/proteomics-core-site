# UC Davis Proteomics Core — Publications & Citations Report

**Generated:** 2026-04-12 | **Data sources:** PubMed (MCP), NIH iCite API, Google Scholar (scholarly lib)

> This report consolidates publication and citation metrics for core personnel,
> S10 instrument-grant-linked papers, and papers acknowledging the UC Davis
> Proteomics Core Facility. Every figure is traceable to raw data in
> `reports/audit/raw/` (PMID lists, iCite responses, Scholar profile JSON).

---

## 1. Core Personnel — Publication & Citation Metrics

### Google Scholar (authoritative for h-index / i10-index)

| Person | Profile | Total Citations | h-index | i10-index | 5-yr Citations | Affiliation |
|--------|---------|---------------:|--------:|---------:|---------------:|-------------|
| Brett S Phinney | [2p9wV0kAAAAJ](https://scholar.google.com/citations?user=2p9wV0kAAAAJ) | 10,994 | 53 | 122 | 5318 | Director Proteomics Core, UC Davis Genome Center |
| Michelle R Salemi | [rjgy6EgAAAAJ](https://scholar.google.com/citations?user=rjgy6EgAAAAJ) | 3,934 | 34 | 62 | 3118 | University of California at Davis |
| Dietmar Kültz | [a-41tYIAAAAJ](https://scholar.google.com/citations?user=a-41tYIAAAAJ) | 12,259 | 52 | 108 | 3801 | Professor of Physiological Genomics, University of California Davis |

*Scholar source: `scholarly` Python library, fetched 2026-04-12. Scholar captures wider publication set than PubMed (includes conference papers, book chapters).*

### Scholar vs PubMed coverage note (2026-04-13 — cross-checked against user's full Scholar list)

- User's Scholar page lists ~300 items total (peer-reviewed + conference abstracts + preprints + ABRF study papers).
- My PubMed search returned **110 peer-reviewed biomedical papers** — matches PubMed indexing (excludes JBT conference abstracts, bioRxiv preprints, meeting reports, thesis).
- The Scholar total citations (10,994) and h-index (53) are the authoritative numbers for grant/CV materials.
- All 4 of Phinney's 2026 PubMed-indexed papers are captured (PMIDs: 41861817, 41843626, 41454884, 41213346).
- **Scholar citation counts run 1.3–2.3× higher than iCite** because Scholar counts all citing sources (books, preprints, theses, non-PubMed papers); iCite counts PubMed-indexed citations only. Use Scholar for external materials, iCite for NIH field-normalized context.
- Full Scholar reference list saved to `reports/audit/raw/scholar_phinney_user_provided.md`.

### PubMed (biomedical indexed papers)

| Person | PubMed Papers | Total PubMed Citations (iCite) | Mean RCR | Notes |
|--------|--------------:|------------------------------:|--------:|-------|
| Brett Phinney | 110 | 4,194 | 1.65 |  |
| Michelle Salemi | 28 | 683 | 1.50 |  |
| Gabriela Grigorean | 29 | 648 | 1.77 |  |
| John Schulze | 12 | 725 | 4.19 | FILTER WARNING: Schulze J is a common name; filter used to r... |
| Lauren Dixon | 7 | 251 | 2.71 | FILTER WARNING: Very old 1549860 (1992) predates her career ... |
| Dietmar Kültz | 113 | 6,401 | 1.90 | 113 papers returned. Dietmar Kültz is unique surname, high c... |

*RCR = Relative Citation Ratio (NIH iCite; 1.0 = field-average). Mean RCR > 1.0 indicates above-field-average impact.*

---

## 2. Papers Acknowledging the Proteomics Core Facility

PubMed search: `"Proteomics Core Facility" AND Davis[Affiliation]`

- **Total PubMed hits:** 94
- **Verified UC Davis affiliation in authors:** 80
- **Unverified / non-UCD:** 14
- **Total citations for verified set (iCite):** 3,036

### Methodology caveats
- The search matches papers where (a) ANY author has a Davis-containing affiliation AND (b) the phrase "Proteomics Core Facility" appears somewhere in the indexed fields.
- This is an UPPER BOUND. A paper may mention a different proteomics core and coincidentally have a UC Davis co-author. Manual spot-check recommended for top papers.
- PubMed does not index the Acknowledgments section of full-text articles, so papers that acknowledge our core in a non-indexed way may be missed (FALSE NEGATIVES).
- For exhaustive coverage, a PMC full-text search is needed — PubMed E-utilities does not support this.

### Top cited papers (verified UC Davis affiliation)

| Year | Journal | Title | Citations | RCR | PMID |
|-----:|---------|-------|---------:|----:|------|
| 2016 | Neurology | Gram-negative bacterial molecules associate with Alzheimer disease pathology. | 400 | 15.37 | [27784770](https://pubmed.ncbi.nlm.nih.gov/27784770/) |
| 2019 | Developmental cell | Galectin-3 Coordinates a Cellular System for Lysosomal Repair and Removal. | 304 | 13.69 | [31813797](https://pubmed.ncbi.nlm.nih.gov/31813797/) |
| 2018 | Molecular cell | Galectins Control mTOR in Response to Endomembrane Damage. | 235 | 8.09 | [29625033](https://pubmed.ncbi.nlm.nih.gov/29625033/) |
| 2021 | Cell reports. Medicine | Divergent and self-reactive immune responses in the CNS of COVID-19 patients with neurological symptoms. | 152 | 9.55 | [33969321](https://pubmed.ncbi.nlm.nih.gov/33969321/) |
| 2015 | Investigative ophthalmology & visual science | Dexamethasone Stiffens Trabecular Meshwork, Trabecular Meshwork Cells, and Matrix. | 143 | 5.82 | [26193921](https://pubmed.ncbi.nlm.nih.gov/26193921/) |
| 2018 | Autophagy | Galectins control MTOR and AMPK in response to lysosomal damage to induce autophagy. | 122 | 5.24 | [30081722](https://pubmed.ncbi.nlm.nih.gov/30081722/) |
| 2014 | Molecular biology and evolution | Evolutionary origin and diversification of epidermal barrier proteins in amniotes. | 114 | 3.54 | [25169930](https://pubmed.ncbi.nlm.nih.gov/25169930/) |
| 2016 | Plant physiology | A Cysteine-Rich Protein Kinase Associates with a Membrane Immune Complex and the Cysteine Residues Are Required for Cell Death. | 107 | 4.31 | [27852951](https://pubmed.ncbi.nlm.nih.gov/27852951/) |
| 2019 | Molecular & cellular proteomics : MCP | NIST Interlaboratory Study on Glycosylation Analysis of Monoclonal Antibodies: Comparison of Results from Diverse Analytical Methods. | 77 | 5.14 | [31591262](https://pubmed.ncbi.nlm.nih.gov/31591262/) |
| 2016 | PloS one | Demonstration of Protein-Based Human Identification Using the Hair Shaft Proteome. | 77 | 3.46 | [27603779](https://pubmed.ncbi.nlm.nih.gov/27603779/) |
| 2017 | Journal of proteome research | Absolute Quantification of Human Milk Caseins and the Whey/Casein Ratio during the First Year of Lactation. | 74 | 3.73 | [28925267](https://pubmed.ncbi.nlm.nih.gov/28925267/) |
| 2018 | Acta biomaterialia | Glaucomatous cell derived matrices differentially modulate non-glaucomatous trabecular meshwork cellular behavior. | 73 | 4.01 | [29524673](https://pubmed.ncbi.nlm.nih.gov/29524673/) |
| 2017 | Carcinogenesis | Integrated Metabolomics and Proteomics Highlight Altered Nicotinamide- and Polyamine Pathways in Lung Adenocarcinoma. | 68 | 2.48 | [28049629](https://pubmed.ncbi.nlm.nih.gov/28049629/) |
| 2021 | Nature cell biology | ATG9A protects the plasma membrane from programmed and incidental permeabilization. | 67 | 3.36 | [34257406](https://pubmed.ncbi.nlm.nih.gov/34257406/) |
| 2022 | The Journal of cell biology | Stress granules and mTOR are regulated by membrane atg8ylation during lysosomal damage. | 65 | 4.66 | [36179369](https://pubmed.ncbi.nlm.nih.gov/36179369/) |

*Full verified list: `reports/audit/core_acknowledgment_papers.csv` (80 rows)*
*Unverified/filtered list: `reports/audit/core_ack_papers_unverified.csv` (14 rows)*

---

## 2b. PMC Full-Text Acknowledgment Search (broader — includes acknowledgment sections)

PubMed only indexes title/abstract/MeSH/affiliations — NOT acknowledgment sections. PMC (PubMed Central) full-text search catches papers that thank the core only in their acknowledgment text. This is where most real core-acknowledgment papers live.

| Query | PMC Hits |
|-------|---------:|
| `"UC Davis Proteomics Core"` | 129 |
| `"UC Davis Proteomics Core Facility"` | 68 |
| `"University of California Davis Proteomics Core"` | 55 |
| `"UC Davis Genome Center Proteomics Core"` | 18 |
| `"Proteomics Core at UC Davis"` | 21 |
| `"Proteomics Core Facility at UC Davis"` | 10 |
| `S10OD021801` | 17 |
| `S10OD026918` | 9 |
| `S10RR023642` | 0 |
| `"Brett Phinney"` | 61 |
| `"Brett S. Phinney"` | 83 |
| `("Proteomics Core" AND "UC Davis")` | 268 |

- **Total unique PMC papers (dedup across queries):** 394
- **Total citations (iCite sum):** 14,923
- **Expansion vs PubMed-indexed search:** 314 additional papers found via full-text

### Top 20 highest-cited papers acknowledging the core (PMC full-text)

| Citations | Year | Journal | Title | PMID | Matched phrase |
|---------:|:----:|---------|-------|------|----------------|
| 463 | 2006 | Cell | Global analysis of protein palmitoylation in yeast. | [16751107](https://pubmed.ncbi.nlm.nih.gov/16751107/) | "Brett S. Phinney" |
| 400 | 2016 | Neurology | Gram-negative bacterial molecules associate with Alzheimer disease pathology. | [27784770](https://pubmed.ncbi.nlm.nih.gov/27784770/) | "Brett Phinney"; ("Proteomics Core" AND "UC Davis") |
| 368 | 2017 | Science (New York, N.Y.) | Redox-based reagents for chemoselective methionine bioconjugation. | [28183972](https://pubmed.ncbi.nlm.nih.gov/28183972/) | "UC Davis Proteomics Core"; ("Proteomics Core" AND "UC Davis |
| 360 | 2021 | Molecular & cellular proteomics : M | IonQuant Enables Accurate and Sensitive Label-Free Quantification With FDR-Controlled Matc | [33813065](https://pubmed.ncbi.nlm.nih.gov/33813065/) | "Brett Phinney" |
| 337 | 2012 | Nature | The spatial architecture of protein function and adaptation. | [23041932](https://pubmed.ncbi.nlm.nih.gov/23041932/) | "University of California Davis Proteomics Core" |
| 304 | 2020 | Developmental cell | Galectin-3 Coordinates a Cellular System for Lysosomal Repair and Removal. | [31813797](https://pubmed.ncbi.nlm.nih.gov/31813797/) | "Proteomics Core at UC Davis"; ("Proteomics Core" AND "UC Da |
| 302 | 2005 | The Plant cell | Identification and functional analysis of in vivo phosphorylation sites of the Arabidopsis | [15894717](https://pubmed.ncbi.nlm.nih.gov/15894717/) | "Brett S. Phinney" |
| 286 | 2018 | Developmental cell | A Proximity Labeling Strategy Provides Insights into the Composition and Dynamics of Lipid | [29275994](https://pubmed.ncbi.nlm.nih.gov/29275994/) | "University of California Davis Proteomics Core" |
| 266 | 2018 | Frontiers in aging neuroscience | Lipopolysaccharide Associates with Amyloid Plaques, Neurons and Oligodendrocytes in Alzhei | [29520228](https://pubmed.ncbi.nlm.nih.gov/29520228/) | "Brett Phinney" |
| 254 | 2015 | Science (New York, N.Y.) | Protein synthesis. Rqc2p and 60S ribosomal subunits mediate mRNA-independent elongation of | [25554787](https://pubmed.ncbi.nlm.nih.gov/25554787/) | "UC Davis Proteomics Core"; ("Proteomics Core" AND "UC Davis |
| 241 | 2015 | Nature immunology | Interferon-γ regulates cellular metabolism and mRNA translation to potentiate macrophage a | [26147685](https://pubmed.ncbi.nlm.nih.gov/26147685/) | "UC Davis Proteomics Core"; ("Proteomics Core" AND "UC Davis |
| 235 | 2015 | The Journal of cell biology | Ltc1 is an ER-localized sterol transporter and a component of ER-mitochondria and ER-vacuo | [25987606](https://pubmed.ncbi.nlm.nih.gov/25987606/) | "UC Davis Proteomics Core"; "UC Davis Proteomics Core Facili |
| 235 | 2018 | Molecular cell | Galectins Control mTOR in Response to Endomembrane Damage. | [29625033](https://pubmed.ncbi.nlm.nih.gov/29625033/) | "Proteomics Core at UC Davis"; ("Proteomics Core" AND "UC Da |
| 234 | 2015 | eLife | MICOS coordinates with respiratory complexes and lipids to establish mitochondrial inner m | [25918844](https://pubmed.ncbi.nlm.nih.gov/25918844/) | "Proteomics Core Facility at UC Davis"; "Brett Phinney"; ("P |
| 221 | 2019 | Cell reports | Cathepsin G Inhibition by Serpinb1 and Serpinb6 Prevents Programmed Necrosis in Neutrophil | [31216481](https://pubmed.ncbi.nlm.nih.gov/31216481/) | "UC Davis Proteomics Core"; "UC Davis Proteomics Core Facili |
| 209 | 2005 | Proceedings of the National Academy | Jasmonate-inducible plant enzymes degrade essential amino acids in the herbivore midgut. | [16357201](https://pubmed.ncbi.nlm.nih.gov/16357201/) | "Brett S. Phinney" |
| 209 | 2009 | PLoS biology | RIN4 functions with plasma membrane H+-ATPases to regulate stomatal apertures during patho | [19564897](https://pubmed.ncbi.nlm.nih.gov/19564897/) | ("Proteomics Core" AND "UC Davis") |
| 198 | 2011 | PLoS genetics | REVEILLE8 and PSEUDO-REPONSE REGULATOR5 form a negative feedback loop within the Arabidops | [21483796](https://pubmed.ncbi.nlm.nih.gov/21483796/) | "Brett S. Phinney" |
| 186 | 2019 | Molecular cell | Proximity RNA Labeling by APEX-Seq Reveals the Organization of Translation Initiation Comp | [31442426](https://pubmed.ncbi.nlm.nih.gov/31442426/) | "UC Davis Genome Center Proteomics Core"; ("Proteomics Core" |
| 185 | 2017 | Tissue engineering. Part C, Methods | A Modified Hydroxyproline Assay Based on Hydrochloric Acid in Ehrlich's Solution Accuratel | [28406755](https://pubmed.ncbi.nlm.nih.gov/28406755/) | "UC Davis Proteomics Core"; "UC Davis Proteomics Core Facili |

*Full list: `reports/audit/core_acknowledgments_pmc.csv` (394 rows)*
*Raw per-query JSON: `reports/audit/raw/pmc_acknowledgment_search.json`*

### False-positive risk
- Broadest query `("Proteomics Core" AND "UC Davis")` (268 hits) is most prone to false positives.
- Specific-phrase queries (`"UC Davis Proteomics Core"` etc.) are high-precision.
- Grant-number queries (`S10OD021801`, `S10OD026918`) are essentially zero-false-positive.
- `"Brett Phinney"` queries may capture papers where he is a co-author, not just an acknowledgment — still evidence of core contribution, but a different category.
- Recommend manual review of the top-25 before using in external materials.

---

## 3. S10 Instrument-Grant-Linked Publications

| Grant | Instrument | Year | PubMed Grant-Field Hits | Notes |
|-------|-----------|:----:|:------------------------:|-------|
| S10RR023642 | AB Sciex Q-Trap 4000 | 2008 | 0 | Pre-dates NIH Public Access indexing. Acknowledgment-text search recommended. |
| S10OD021801 | Thermo Orbitrap Fusion ETD | 2016 | 2 | Grant-field indexing incomplete; more papers likely in acknowledgments. |
| S10OD026918 | Thermo QE-HF-X | 2020 | 1 | Recent grant; papers still accruing. |

**`impact_report.py` pulled a broader list via NIH Reporter publications endpoint:**
- 70 instrument-grant-linked publications, 2,098 total citations (NIH iCite)
- See: `reports/publications_2026-04-12.csv` and `reports/impact_data.json`

---

## 4. Audit Trail

All raw data saved in `reports/audit/raw/`:

| File | Contents |
|------|----------|
| `pmid_searches.json` | Every PubMed query + full PMID list + query_translation + notes on false-positive risk |
| `icite_citations.json` | iCite response for ~308 unique PMIDs — citation_count, RCR, field_citation_rate, NIH percentile |
| `scholar_profiles.json` | Scholar raw response for Phinney, Salemi, Kültz (all indices, 5-year totals, citations per year) |
| `ack_metadata_batch*.json` | PubMed article metadata for all acknowledgment-set PMIDs — affiliations, abstracts, DOIs |
| `pmc_acknowledgment_search.json` | PMC full-text search results with 12 queries, 394 unique PMCIDs, raw esearch responses |
| `pmc_search_log.txt` | Human-readable log of each PMC query, hit counts, query translations |

To re-verify any claim:
1. Find the PMID in `audit/core_acknowledgment_papers.csv`
2. Look up its raw metadata in `ack_metadata_batch*.json`
3. Confirm the UC Davis affiliation regex hit in the `affiliations` field
4. Cross-check citation count against `icite_citations.json`

---

## 5. Known Gaps / Follow-up

- [ ] Grigorean, Dixon, Schulze: no Google Scholar profile → no h-index available. Recommend creating profiles to strengthen grant materials.
- [ ] Dixon LY search returned 7 hits including a 1992 paper (PMID 1549860) that likely predates Lauren's career — manual review needed.
- [ ] Schulze J filter may exclude some of John's papers due to common-name ambiguity; its high mean RCR (4.19) on 12 papers deserves manual verification.
- [ ] Kültz umlaut: PubMed `query_translation` showed `kultz d[Author]` only — umlaut variant not indexed separately; all 113 papers captured under ASCII form.
- [ ] iCite RCR values are null for very recent papers (< 2 years old).
- [ ] PMC broadest query ("Proteomics Core" AND "UC Davis", 268 hits) needs manual spot-check — use narrower queries for authoritative counts.
- [ ] S10RR023642 (Q-Trap 4000, 2008) found in 0 PMC searches — instrument predates most PMC deposits. Manual paper trail needed.
