#!/usr/bin/env python3
"""
UC Davis Proteomics Core Facility — Comprehensive Impact Report Generator

Author: Brett Phinney / UC Davis Proteomics Core
Repository: https://github.com/bsphinney/proteomics-core-site

This script queries 6 data sources to build a comprehensive impact picture
of the UC Davis Proteomics Core Facility, generating reports suitable for
administration, granting agencies, and internal planning.

DATA SOURCES:
  1. NIH Reporter API      — Federal grants referencing the proteomics core
  2. NIH Publications API   — Publications linked to instrument grants + iCite citations
  3. NSF Award API          — NSF grants at UC Davis related to proteomics/mass spec
  4. PubMed E-utilities     — Publications by core personnel + grant acknowledgments
  5. Stratocore/PPMS        — Submission system usage data (private, not in repo)
                              + Order/invoicing data with revenue
  6. PI Grant Discovery     — Looks up each submission PI in NIH/NSF to find ALL
                              their active grants (proves core supports funded research)

OUTPUTS (all saved to reports/):
  - impact_report_latest.md           Comprehensive report (all services)
  - impact_report_ms_only_latest.md   Mass spectrometry only (for S10 grant renewals)
  - impact_report_aaa_only_latest.md  Amino acid analysis only
  - executive_summary.pdf             One-page visual dashboard for leadership
  - impact_data.json                  Machine-readable data for website integration
  - nih_grants_YYYY-MM-DD.csv         NIH grant spreadsheet
  - nsf_awards_YYYY-MM-DD.csv         NSF award spreadsheet
  - publications_YYYY-MM-DD.csv       Publication spreadsheet (when PubMed enabled)
  - figures/*.png                     9 charts (funding, submissions, organisms, etc.)

USAGE:
    # Full run (all sources — takes ~5 min due to PI lookups):
    python scripts/impact_report.py

    # Skip slow steps for quick iteration:
    python scripts/impact_report.py --skip-pubmed --skip-pi-lookup

    # NIH grants only (fastest, ~10 sec):
    python scripts/impact_report.py --nih-only

    # GitHub Actions runs monthly (see .github/workflows/impact-report.yml)
    # Note: Actions skips submissions since private_data/ is not in the repo.

OPTIONS:
    --skip-pubmed      Skip PubMed queries (slow, rate-limited)
    --skip-nsf         Skip NSF queries
    --skip-submissions Skip submission/order analytics (if no private data)
    --skip-citations   Skip NIH publications + iCite citation metrics
    --skip-pi-lookup   Skip PI-based grant discovery (queries each PI individually)
    --nih-only         Only run NIH grant queries (skips everything else)

PRIVATE DATA:
    The following files in private_data/ are NOT committed to git:
    - submissions_export_full.csv  — Stratocore submission records (4,300+ rows)
    - orders.csv                   — Stratocore order/invoicing data with pricing
    These must be exported from Stratocore and placed in private_data/ manually.

DEPENDENCIES:
    pip install requests matplotlib
"""

import json
import requests
import csv
import os
import sys
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime, date
from collections import defaultdict, Counter
from pathlib import Path

# --- Configuration ---

BASE_DIR = Path(__file__).parent.parent
REPORT_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORT_DIR / "figures"
PRIVATE_DIR = BASE_DIR / "private_data"
SUBMISSIONS_FILE = PRIVATE_DIR / "submissions_export_full.csv"  # Full CSV from Stratocore
SUBMISSIONS_FILE_TSV = PRIVATE_DIR / "submissions_export.tsv"  # Legacy TSV (fallback)
ORDERS_FILE = PRIVATE_DIR / "orders.csv"  # Stratocore orders with pricing

NIH_API = "https://api.reporter.nih.gov/v2/projects/search"
NSF_API = "https://api.nsf.gov/services/v1/awards.json"
PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

ORGANIZATION = "UNIVERSITY OF CALIFORNIA DAVIS"
NSF_ORG = "university of california davis"

# Core facility personnel
PERSONNEL = {
    "Phinney": {"full": "Brett S. Phinney", "pubmed": "Phinney BS"},
    "Grigorean": {"full": "Gabriela Grigorean", "pubmed": "Grigorean G"},
    "Salemi": {"full": "Michelle Salemi", "pubmed": "Salemi MR"},
    "Schulze": {"full": "John Schulze", "pubmed": "Schulze J"},
    "Dixon": {"full": "Lauren Dixon", "pubmed": "Dixon L"},
}

# Affiliated faculty (not core staff, but formally associated with the core)
AFFILIATED_FACULTY = [
    {"first": "Dietmar", "last": "Kültz", "full": "Dietmar Kültz",
     "alt_last": "Kueltz",  # Alternative spelling without umlaut
     "role": "Faculty Advisor", "org": ORGANIZATION,
     "pubmed": "Kultz D"},
]

# PubMed courtesy params
PUBMED_TOOL = "ucdavis_proteomics_impact"
PUBMED_EMAIL = "bsphinney@ucdavis.edu"

# Normalize institution names for submission data
INSTITUTE_NORMALIZATIONS = {
    "UC Davis": "UC Davis",
    "UCDavis": "UC Davis",
    "University of California, Davis": "UC Davis",
    "University of California Davis": "UC Davis",
    "UC Davis Plant Pathology": "UC Davis",
    "Department of Biochemistry and Molecular Medicine, UC Davis": "UC Davis",
    "Department of Molecular Biosciences UC Davis SVM": "UC Davis",
    "UC Davis Genome Center": "UC Davis",
    "UCDavis Medical Center": "UC Davis",
    "UC Davis Health- Surgery": "UC Davis",
    "UCDavis of biochemistry and molecular medicine": "UC Davis",
    "UCSF": "UCSF",
    "University of California San Francisco": "UCSF",
    "UC Berkeley": "UC Berkeley",
    "University of California, Berkeley": "UC Berkeley",
    "Gladstone": "Gladstone Institutes",
    "Gladstone Institute": "Gladstone Institutes",
    "UCSB": "UC Santa Barbara",
}

# Normalize organism names (free-text field has many variants)
ORGANISM_NORMALIZATIONS = {
    "human": "Human",
    "Human": "Human",
    "Homo sapiens": "Human",
    "Homo sapience": "Human",
    "Homo sapience ": "Human",
    "Human CSF and Plasma": "Human",
    "Human Lung tissue": "Human",
    "mouse": "Mouse",
    "Mouse": "Mouse",
    "Mus Musculus": "Mouse",
    "Mus musculus": "Mouse",
    "E. coli MG1655": "E. coli",
    "E. coli": "E. coli",
    "Yeast (S. cerevisiae)": "S. cerevisiae",
    "canine (MDCK cells)": "Canine",
    "canine": "Canine",
    "Nicotiana tabacum": "Nicotiana tabacum",
    "Bats": "Bats",
}


# ==============================================================================
# NIH Reporter
# ==============================================================================

NIH_SEARCH_STRATEGIES = [
    {
        "name": "proteomics_core_text",
        "criteria": {
            "advanced_text_search": {
                "operator": "and",
                "search_field": "projecttitle,terms,abstracttext",
                "search_text": "proteomics core",
            },
            "org_names": [ORGANIZATION],
        },
    },
    {
        "name": "genome_center_proteomics",
        "criteria": {
            "advanced_text_search": {
                "operator": "and",
                "search_field": "projecttitle,terms,abstracttext",
                "search_text": "genome center proteomics",
            },
            "org_names": [ORGANIZATION],
        },
    },
    {
        "name": "mass_spec_core",
        "criteria": {
            "advanced_text_search": {
                "operator": "and",
                "search_field": "projecttitle,terms,abstracttext",
                "search_text": "mass spectrometry core",
            },
            "org_names": [ORGANIZATION],
        },
    },
    {
        "name": "pi_phinney",
        "criteria": {
            "pi_names": [{"last_name": "Phinney", "first_name": "Brett"}],
            "org_names": [ORGANIZATION],
        },
    },
    # Affiliated faculty (try both umlaut and anglicized spelling)
    {
        "name": "pi_kueltz",
        "criteria": {
            "pi_names": [{"last_name": "Kueltz", "first_name": "Dietmar"}],
            "org_names": [ORGANIZATION],
        },
    },
    {
        "name": "pi_kultz_umlaut",
        "criteria": {
            "pi_names": [{"last_name": "Kültz", "first_name": "Dietmar"}],
            "org_names": [ORGANIZATION],
        },
    },
]


def search_nih_reporter(criteria, limit=500):
    """Query NIH Reporter API and return all matching projects."""
    payload = {
        "criteria": criteria,
        "offset": 0,
        "limit": limit,
        "sort_field": "project_start_date",
        "sort_order": "desc",
    }
    try:
        resp = requests.post(NIH_API, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        print(f"  NIH API error: {e}")
        return []


def extract_core_project_number(project_number):
    """Strip year/suffix to get the core project number for deduplication."""
    if not project_number:
        return None
    parts = project_number.split("-")[0]
    stripped = parts.lstrip("0123456789")
    return stripped


def run_nih_searches():
    """Run all NIH search strategies and deduplicate results."""
    all_projects = {}
    raw_count = 0

    for strategy in NIH_SEARCH_STRATEGIES:
        print(f"  NIH: {strategy['name']}...")
        results = search_nih_reporter(strategy["criteria"])
        print(f"    Found {len(results)} results")
        raw_count += len(results)

        for project in results:
            core_num = extract_core_project_number(project.get("project_num", ""))
            if not core_num:
                continue
            if core_num not in all_projects:
                all_projects[core_num] = project
            else:
                existing_award = all_projects[core_num].get("award_amount", 0) or 0
                new_award = project.get("award_amount", 0) or 0
                if new_award > existing_award:
                    all_projects[core_num] = project

    print(f"  NIH total raw: {raw_count}, deduplicated: {len(all_projects)}")
    return all_projects


def compute_nih_statistics(projects):
    """Compute aggregate statistics from NIH project data."""
    stats = {
        "total_grants": len(projects),
        "total_funding": 0,
        "unique_pis": set(),
        "institutes": defaultdict(lambda: {"count": 0, "funding": 0}),
        "active_grants": [],
        "closed_grants": [],
        "by_decade": defaultdict(lambda: {"count": 0, "funding": 0}),
        "phinney_grants": [],
        "all_grants": [],
    }

    today = date.today()

    for core_num, project in projects.items():
        award = project.get("award_amount", 0) or 0
        stats["total_funding"] += award

        pi_name = ""
        pis = project.get("principal_investigators", [])
        if pis:
            pi = pis[0]
            pi_name = f"{pi.get('first_name', '')} {pi.get('last_name', '')}".strip()
            stats["unique_pis"].add(pi_name)

        ic = project.get("agency_ic_admin", {})
        ic_abbr = ic.get("abbreviation", "Unknown") if ic else "Unknown"
        stats["institutes"][ic_abbr]["count"] += 1
        stats["institutes"][ic_abbr]["funding"] += award

        end_date_str = project.get("project_end_date", "")
        is_active = False
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(
                    end_date_str.replace("Z", "+00:00")
                ).date()
                is_active = end_date >= today
            except (ValueError, TypeError):
                pass

        grant_info = {
            "core_number": core_num,
            "project_number": project.get("project_num", ""),
            "title": project.get("project_title", ""),
            "pi": pi_name,
            "award_amount": award,
            "institute": ic_abbr,
            "fiscal_year": project.get("fiscal_year", ""),
            "start_date": project.get("project_start_date", ""),
            "end_date": end_date_str,
            "active": is_active,
        }

        if is_active:
            stats["active_grants"].append(grant_info)
        else:
            stats["closed_grants"].append(grant_info)
        stats["all_grants"].append(grant_info)

        fy = project.get("fiscal_year")
        if fy:
            decade = f"{(fy // 10) * 10}s"
            stats["by_decade"][decade]["count"] += 1
            stats["by_decade"][decade]["funding"] += award

        if pi_name and "Phinney" in pi_name:
            stats["phinney_grants"].append(grant_info)

    stats["unique_pis_count"] = len(stats["unique_pis"])
    stats["unique_pis_list"] = sorted(stats["unique_pis"])
    stats["unique_pis"] = len(stats["unique_pis"])
    return stats


# ==============================================================================
# NSF Awards
# ==============================================================================

NSF_KEYWORDS = ["proteomics", "mass spectrometry", "proteomic"]


def search_nsf_awards(keyword, org=NSF_ORG):
    """Query NSF Award API for a keyword + organization."""
    all_awards = []
    offset = 0
    while True:
        params = {
            "keyword": keyword,
            "awardeeName": f'"{org}"',
            "printFields": "id,title,piFirstName,piLastName,piEmail,fundsObligatedAmt,"
                           "estimatedTotalAmt,startDate,expDate,fundProgramName,"
                           "abstractText,activeAwd",
            "rpp": 25,
            "offset": offset,
        }
        try:
            resp = requests.get(NSF_API, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            awards = data.get("response", {}).get("award", [])
            if not awards:
                break
            all_awards.extend(awards)
            if len(awards) < 25:
                break
            offset += 25
            time.sleep(0.5)
        except requests.RequestException as e:
            print(f"  NSF API error: {e}")
            break
    return all_awards


def run_nsf_searches():
    """Search NSF for all relevant keywords, deduplicate by award ID."""
    all_awards = {}
    for kw in NSF_KEYWORDS:
        print(f"  NSF: keyword='{kw}'...")
        awards = search_nsf_awards(kw)
        print(f"    Found {len(awards)} results")
        for award in awards:
            aid = award.get("id", "")
            if aid and aid not in all_awards:
                # Filter: only keep awards that mention proteomics/mass spec
                # in title or abstract (NSF keyword search can be broad)
                title = (award.get("title") or "").lower()
                abstract = (award.get("abstractText") or "").lower()
                text = title + " " + abstract
                if any(term in text for term in [
                    "proteom", "mass spectrom", "lc-ms", "tandem mass",
                    "protein identification", "peptide", "proteomic"
                ]):
                    all_awards[aid] = award

    # Also search for affiliated faculty by PI name
    for faculty in AFFILIATED_FACULTY:
        print(f"  NSF: PI='{faculty['full']}'...")
        params = {
            "piFirstName": faculty["first"],
            "piLastName": faculty["last"],
            "awardeeName": f'"{NSF_ORG}"',
            "printFields": "id,title,piFirstName,piLastName,piEmail,fundsObligatedAmt,"
                           "estimatedTotalAmt,startDate,expDate,fundProgramName,"
                           "abstractText,activeAwd",
            "rpp": 25,
            "offset": 0,
        }
        try:
            resp = requests.get(NSF_API, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            awards = data.get("response", {}).get("award", [])
            print(f"    Found {len(awards)} results")
            for award in awards:
                aid = award.get("id", "")
                if aid and aid not in all_awards:
                    all_awards[aid] = award
        except requests.RequestException as e:
            print(f"    NSF error: {e}")

    print(f"  NSF deduplicated total: {len(all_awards)}")
    return all_awards


def compute_nsf_statistics(awards):
    """Compute stats from NSF award data."""
    stats = {
        "total_awards": len(awards),
        "total_funding": 0,
        "unique_pis": set(),
        "active_awards": [],
        "all_awards": [],
    }

    for aid, award in awards.items():
        amount = int(award.get("fundsObligatedAmt", 0) or 0)
        stats["total_funding"] += amount

        pi_name = f"{award.get('piFirstName', '')} {award.get('piLastName', '')}".strip()
        if pi_name:
            stats["unique_pis"].add(pi_name)

        is_active = str(award.get("activeAwd", "")).lower() == "true"

        info = {
            "award_id": aid,
            "title": award.get("title", ""),
            "pi": pi_name,
            "amount": amount,
            "start_date": award.get("startDate", ""),
            "end_date": award.get("expDate", ""),
            "program": award.get("fundProgramName", ""),
            "active": is_active,
        }
        stats["all_awards"].append(info)
        if is_active:
            stats["active_awards"].append(info)

    stats["unique_pis_count"] = len(stats["unique_pis"])
    stats["unique_pis"] = len(stats["unique_pis"])
    return stats


# ==============================================================================
# PubMed Publications
# ==============================================================================

def search_pubmed(query, retmax=500):
    """Search PubMed and return list of PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "usehistory": "y",
        "tool": PUBMED_TOOL,
        "email": PUBMED_EMAIL,
    }
    try:
        resp = requests.get(PUBMED_SEARCH, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("esearchresult", {})
        return {
            "count": int(result.get("count", 0)),
            "ids": result.get("idlist", []),
            "webenv": result.get("webenv", ""),
            "query_key": result.get("querykey", ""),
        }
    except requests.RequestException as e:
        print(f"  PubMed search error: {e}")
        return {"count": 0, "ids": [], "webenv": "", "query_key": ""}


def fetch_pubmed_details(pmids, batch_size=100):
    """Fetch publication details including grant info from PubMed XML."""
    publications = []

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "xml",
            "retmode": "xml",
            "tool": PUBMED_TOOL,
            "email": PUBMED_EMAIL,
        }
        try:
            resp = requests.get(PUBMED_FETCH, params=params, timeout=60)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)

            for article in root.findall(".//PubmedArticle"):
                pub = parse_pubmed_article(article)
                if pub:
                    publications.append(pub)

        except (requests.RequestException, ET.ParseError) as e:
            print(f"  PubMed fetch error (batch {i}): {e}")

        if i + batch_size < len(pmids):
            time.sleep(0.4)  # Rate limit courtesy

    return publications


def parse_pubmed_article(article):
    """Parse a single PubmedArticle XML element."""
    try:
        citation = article.find(".//MedlineCitation")
        pmid_el = citation.find("PMID")
        pmid = pmid_el.text if pmid_el is not None else ""

        art = citation.find("Article")
        title_el = art.find("ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""

        # Year
        year = ""
        pub_date = art.find(".//PubDate")
        if pub_date is not None:
            year_el = pub_date.find("Year")
            if year_el is not None:
                year = year_el.text

        # Journal
        journal = ""
        journal_el = art.find(".//Journal/Title")
        if journal_el is not None:
            journal = journal_el.text or ""

        # Authors
        authors = []
        for author in art.findall(".//Author"):
            last = author.find("LastName")
            initials = author.find("Initials")
            if last is not None and initials is not None:
                authors.append(f"{last.text} {initials.text}")

        # Grants
        grants = []
        for grant in art.findall(".//Grant"):
            grant_id_el = grant.find("GrantID")
            agency_el = grant.find("Agency")
            if grant_id_el is not None:
                grants.append({
                    "grant_id": grant_id_el.text or "",
                    "agency": agency_el.text if agency_el is not None else "",
                })

        return {
            "pmid": pmid,
            "title": title,
            "year": year,
            "journal": journal,
            "authors": authors,
            "grants": grants,
        }
    except Exception:
        return None


def run_pubmed_searches():
    """Search PubMed for all core personnel publications."""
    # Build combined search: any core person + UC Davis affiliation
    author_terms = " OR ".join(
        f"{p['pubmed']}[Author]" for p in PERSONNEL.values()
    )
    # Add affiliation filter for specificity
    query = f"({author_terms}) AND (proteomics OR mass spectrometry OR proteomic)"

    print(f"  PubMed: searching for core personnel publications...")
    result = search_pubmed(query, retmax=1000)
    print(f"    Found {result['count']} publications")

    if not result["ids"]:
        return {"count": 0, "publications": [], "grants_from_pubs": {}}

    print(f"    Fetching details for {len(result['ids'])} publications...")
    publications = fetch_pubmed_details(result["ids"])
    print(f"    Parsed {len(publications)} publications with details")

    # Extract unique grant numbers
    grants_from_pubs = {}
    for pub in publications:
        for grant in pub.get("grants", []):
            gid = grant["grant_id"].strip()
            if gid:
                # Normalize: remove spaces in grant IDs
                gid_norm = re.sub(r'\s+', '', gid)
                if gid_norm not in grants_from_pubs:
                    grants_from_pubs[gid_norm] = {
                        "grant_id": gid,
                        "agency": grant["agency"],
                        "citing_pmids": [],
                    }
                grants_from_pubs[gid_norm]["citing_pmids"].append(pub["pmid"])

    print(f"    Extracted {len(grants_from_pubs)} unique grant numbers from publications")

    return {
        "count": len(publications),
        "publications": publications,
        "grants_from_pubs": grants_from_pubs,
    }


# ==============================================================================
# NIH Reporter Publications + iCite Citation Metrics
# ==============================================================================

NIH_PUBS_API = "https://api.reporter.nih.gov/v2/publications/search"
ICITE_API = "https://icite.od.nih.gov/api/pubs"


def get_nih_grant_publications(core_project_nums):
    """Get all PMIDs linked to grants via NIH Reporter publications endpoint."""
    all_pubs = {}
    for grant_num in core_project_nums:
        payload = {
            "criteria": {"core_project_nums": [grant_num]},
            "offset": 0,
            "limit": 500,
        }
        try:
            resp = requests.post(NIH_PUBS_API, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            for pub in results:
                pmid = str(pub.get("pmid", ""))
                if pmid and pmid not in all_pubs:
                    all_pubs[pmid] = {
                        "pmid": pmid,
                        "title": pub.get("title", ""),
                        "journal": pub.get("journal", ""),
                        "year": str(pub.get("pub_year", "")),
                        "authors": pub.get("author_list", []),
                        "grants": [grant_num],
                    }
                elif pmid and pmid in all_pubs:
                    if grant_num not in all_pubs[pmid]["grants"]:
                        all_pubs[pmid]["grants"].append(grant_num)
        except requests.RequestException as e:
            print(f"    NIH pubs API error for {grant_num}: {e}")
        time.sleep(0.3)

    return all_pubs


def get_icite_metrics(pmids, batch_size=200):
    """Get citation counts and bibliometrics from NIH iCite API."""
    metrics = {}
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        pmid_str = ",".join(batch)
        try:
            resp = requests.get(f"{ICITE_API}?pmids={pmid_str}", timeout=60)
            resp.raise_for_status()
            data = resp.json()
            for pub in data.get("data", []):
                pmid = str(pub.get("pmid", ""))
                metrics[pmid] = {
                    "citation_count": pub.get("citation_count", 0),
                    "relative_citation_ratio": pub.get("relative_citation_ratio"),
                    "nih_percentile": pub.get("nih_percentile"),
                    "expected_citations": pub.get("expected_citations_per_year"),
                    "year": pub.get("year"),
                    "title": pub.get("title", ""),
                    "journal": pub.get("journal", ""),
                    "is_clinical": pub.get("is_clinical"),
                }
        except requests.RequestException as e:
            print(f"    iCite API error (batch {i}): {e}")
        if i + batch_size < len(pmids):
            time.sleep(0.3)

    return metrics


def run_nih_publications_search(nih_stats):
    """Find all publications linked to NIH grants via Reporter + get citation metrics."""
    if not nih_stats:
        return None

    # Get Phinney instrument grant numbers for publication lookup
    grant_nums = [g["core_number"] for g in nih_stats.get("phinney_grants", [])]
    if not grant_nums:
        return None

    print(f"  NIH Publications: searching for papers linked to {len(grant_nums)} instrument grants...")
    pubs = get_nih_grant_publications(grant_nums)
    print(f"    Found {len(pubs)} unique publications across instrument grants")

    if not pubs:
        return None

    # Get citation metrics from iCite
    pmids = list(pubs.keys())
    print(f"    Fetching citation metrics from iCite for {len(pmids)} publications...")
    metrics = get_icite_metrics(pmids)
    print(f"    Got metrics for {len(metrics)} publications")

    # Merge metrics into publications
    total_citations = 0
    for pmid, pub in pubs.items():
        if pmid in metrics:
            pub["citation_count"] = metrics[pmid]["citation_count"]
            pub["rcr"] = metrics[pmid]["relative_citation_ratio"]
            total_citations += metrics[pmid]["citation_count"] or 0

    # Sort by citations
    sorted_pubs = sorted(pubs.values(), key=lambda x: x.get("citation_count", 0), reverse=True)

    return {
        "total_publications": len(pubs),
        "total_citations": total_citations,
        "publications": sorted_pubs,
        "by_grant": {g: sum(1 for p in pubs.values() if g in p["grants"]) for g in grant_nums},
    }


# ==============================================================================
# Submission System Analytics
# ==============================================================================

def load_submissions(filepath=None):
    """Load and parse submission data (CSV or TSV).

    Tries the full CSV export first, falls back to legacy TSV.
    """
    import re
    from io import StringIO

    # Try CSV first, then TSV fallback
    if filepath is None:
        if SUBMISSIONS_FILE.exists():
            filepath = SUBMISSIONS_FILE
        elif SUBMISSIONS_FILE_TSV.exists():
            filepath = SUBMISSIONS_FILE_TSV
        else:
            print("  No submissions file found")
            return []

    if not filepath.exists():
        print(f"  Submissions file not found: {filepath}")
        return []

    suffix = filepath.suffix.lower()
    delimiter = "," if suffix == ".csv" else "\t"

    if suffix == ".csv":
        # Standard CSV handles quoting properly
        submissions = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                submissions.append(row)
        print(f"  Loaded {len(submissions)} submissions from {filepath.name}")
        return submissions
    else:
        # TSV: handle multiline fields by re-joining broken lines
        raw_lines = filepath.read_text(encoding="utf-8").split("\n")
        header = raw_lines[0]
        fixed_lines = [header]
        for line in raw_lines[1:]:
            if not line.strip():
                continue
            if re.match(r'^[0-9a-f]{12}\t', line):
                fixed_lines.append(line)
            else:
                if len(fixed_lines) > 1:
                    fixed_lines[-1] += " " + line.strip()

        submissions = []
        reader = csv.DictReader(StringIO("\n".join(fixed_lines)), delimiter="\t")
        for row in reader:
            submissions.append(row)
        print(f"  Loaded {len(submissions)} submissions from {filepath.name}")
        return submissions


def normalize_institute(name):
    """Normalize institution names to canonical forms."""
    if not name or not name.strip():
        return "Unknown"
    name = name.strip()
    # Exact match first
    if name in INSTITUTE_NORMALIZATIONS:
        return INSTITUTE_NORMALIZATIONS[name]
    # Fuzzy matching
    lower = name.lower()
    if "uc davis" in lower or "ucdavis" in lower or lower == "ucd":
        return "UC Davis"
    if "ucsf" in lower or "university of california san francisco" in lower:
        return "UCSF"
    if "uc berkeley" in lower or "berkeley" in lower:
        return "UC Berkeley"
    if "gladstone" in lower:
        return "Gladstone Institutes"
    if "active motif" in lower:
        return "Active Motif"
    if "uc santa barbara" in lower or lower == "ucsb":
        return "UC Santa Barbara"
    if "uc santa cruz" in lower or lower == "ucsc":
        return "UC Santa Cruz"
    if "uc san diego" in lower or lower == "ucsd":
        return "UC San Diego"
    if "uc irvine" in lower or lower == "uci":
        return "UC Irvine"
    if "uc los angeles" in lower or lower == "ucla":
        return "UCLA"
    if "uc riverside" in lower or lower == "ucr":
        return "UC Riverside"
    return name


def compute_submission_statistics(submissions):
    """Compute comprehensive usage statistics from submission data."""
    if not submissions:
        return None

    stats = {
        "total_submissions": len(submissions),
        "date_range": {"earliest": None, "latest": None},
        "by_institute": Counter(),
        "by_institute_normalized": Counter(),
        "by_pi": Counter(),
        "by_organism": Counter(),
        "by_proteomics_type": Counter(),
        "by_month": Counter(),
        "by_quarter": Counter(),
        "sample_counts": [],
        "total_samples": 0,
        "uc_davis_vs_external": {"uc_davis": 0, "external": 0},
        "by_ucd_department": Counter(),
        "unique_pis": set(),
        "unique_submitters": set(),
        "unique_institutes": set(),
        "repeat_pi_rate": 0,
        "data_analysis_requested": 0,
    }

    for sub in submissions:
        # Date tracking
        submitted = sub.get("Submitted", "")
        if submitted:
            try:
                dt = datetime.fromisoformat(submitted.split(".")[0])
                if stats["date_range"]["earliest"] is None or dt < stats["date_range"]["earliest"]:
                    stats["date_range"]["earliest"] = dt
                if stats["date_range"]["latest"] is None or dt > stats["date_range"]["latest"]:
                    stats["date_range"]["latest"] = dt

                month_key = dt.strftime("%Y-%m")
                stats["by_month"][month_key] += 1

                q = (dt.month - 1) // 3 + 1
                quarter_key = f"{dt.year}-Q{q}"
                stats["by_quarter"][quarter_key] += 1
            except (ValueError, TypeError):
                pass

        # Institute
        institute = sub.get("Institute", "").strip()
        if institute and len(institute) < 100:  # Skip data-leak rows
            stats["by_institute"][institute] += 1
            norm = normalize_institute(institute)
            stats["by_institute_normalized"][norm] += 1
            stats["unique_institutes"].add(norm)

            if norm == "UC Davis":
                stats["uc_davis_vs_external"]["uc_davis"] += 1

                # UC Davis department breakdown
                pi_email = sub.get("PI Email", "").strip().lower()
                dept_label = None

                # Try to determine department from PI email domain
                if pi_email.endswith("@health.ucdavis.edu") or pi_email.endswith("@ucdmc.ucdavis.edu"):
                    dept_label = "UC Davis Health"
                elif pi_email.endswith("@vetmed.ucdavis.edu"):
                    dept_label = "School of Veterinary Medicine"
                elif pi_email.endswith("@ucdavis.edu"):
                    dept_label = "UC Davis (General)"

                # Try to extract department from Institute field
                dept_match = re.search(r"Department of ([\w\s&]+)", institute, re.IGNORECASE)
                if dept_match:
                    dept_label = f"Dept. of {dept_match.group(1).strip()}"

                if dept_label:
                    stats["by_ucd_department"][dept_label] += 1

            elif norm != "Unknown":
                stats["uc_davis_vs_external"]["external"] += 1

        # PI
        pi_first = sub.get("PI First Name", "").strip()
        pi_last = sub.get("PI Last Name", "").strip()
        if pi_last:
            pi_key = f"{pi_first} {pi_last}"
            stats["by_pi"][pi_key] += 1
            stats["unique_pis"].add(pi_key)

        # Submitter
        submitter = f"{sub.get('First Name', '')} {sub.get('Last Name', '')}".strip()
        if submitter:
            stats["unique_submitters"].add(submitter)

        # Organism (normalize variants)
        organism = sub.get("organism", "").strip()
        if organism and len(organism) < 80:
            organism = ORGANISM_NORMALIZATIONS.get(organism, organism)
            stats["by_organism"][organism] += 1

        # Proteomics type
        ptype = sub.get("proteomics_type", "").strip()
        if ptype and len(ptype) < 50:
            stats["by_proteomics_type"][ptype] += 1

        # Sample count
        try:
            n_samples = int(sub.get("samples", 0))
            stats["sample_counts"].append(n_samples)
            stats["total_samples"] += n_samples
        except (ValueError, TypeError):
            pass

        # Data analysis
        da = sub.get("data_analysis", "").lower()
        if "core" in da or "do the data" in da:
            stats["data_analysis_requested"] += 1

    # Compute repeat PI rate
    pi_counts = stats["by_pi"]
    repeat_pis = sum(1 for c in pi_counts.values() if c > 1)
    total_pis = len(pi_counts)
    stats["repeat_pi_rate"] = (repeat_pis / total_pis * 100) if total_pis > 0 else 0

    # Convert sets to counts for JSON serialization
    stats["unique_pis_count"] = len(stats["unique_pis"])
    stats["unique_submitters_count"] = len(stats["unique_submitters"])
    stats["unique_institutes_count"] = len(stats["unique_institutes"])

    # Date range strings
    if stats["date_range"]["earliest"]:
        stats["date_range"]["earliest_str"] = stats["date_range"]["earliest"].strftime("%Y-%m-%d")
    if stats["date_range"]["latest"]:
        stats["date_range"]["latest_str"] = stats["date_range"]["latest"].strftime("%Y-%m-%d")

    return stats


def load_orders(filepath=ORDERS_FILE):
    """Load and parse Stratocore orders CSV with pricing data."""
    if not filepath.exists():
        print(f"  Orders file not found: {filepath}")
        return []

    orders = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            orders.append(row)
    print(f"  Loaded {len(orders)} orders from {filepath.name}")
    return orders


def compute_order_statistics(orders):
    """Compute revenue and service analytics from orders data."""
    if not orders:
        return None

    stats = {
        "total_orders": len(orders),
        "total_revenue": 0,
        "revenue_by_year": defaultdict(float),
        "orders_by_year": Counter(),
        "revenue_by_service_type": defaultdict(float),
        "orders_by_service_type": Counter(),
        # Split: mass spec vs amino acid analysis
        "ms_orders": 0,
        "ms_revenue": 0,
        "aaa_orders": 0,
        "aaa_revenue": 0,
        "other_orders": 0,
        "other_revenue": 0,
        "date_range": {"earliest": None, "latest": None},
    }

    for order in orders:
        price = 0
        try:
            price = float(order.get("Price", "0").replace(",", ""))
        except (ValueError, TypeError):
            pass

        stats["total_revenue"] += price

        # Date
        ordered = order.get("Ordered date", "").strip()
        if ordered:
            year = ordered[:4]
            stats["revenue_by_year"][year] += price
            stats["orders_by_year"][year] += 1

        # Service classification
        services = order.get("Services List", "").strip().lower()

        is_aaa = "aaa" in services
        is_ms = any(term in services for term in [
            "bruker", "lc-ms", "tmt", "dia", "dda", "digestion",
            "fusion", "exploris", "timstof", "orbitrap", "q exactive",
            "gel band", "gel spot", "insolution", "data analysis",
        ])

        if is_aaa and not is_ms:
            stats["aaa_orders"] += 1
            stats["aaa_revenue"] += price
            service_type = "Amino Acid Analysis"
        elif is_ms:
            stats["ms_orders"] += 1
            stats["ms_revenue"] += price
            service_type = "Mass Spectrometry"
        else:
            stats["other_orders"] += 1
            stats["other_revenue"] += price
            service_type = "Other"

        stats["revenue_by_service_type"][service_type] += price
        stats["orders_by_service_type"][service_type] += 1

    return stats


def cross_reference_submissions_with_grants(sub_stats, nih_stats, nsf_stats):
    """Find PIs in submission data that also have NIH/NSF grants."""
    if not sub_stats:
        return {}

    submission_pis = {name.lower(): name for name in sub_stats["unique_pis"]}
    matches = {}

    # Check NIH grants
    if nih_stats:
        for g in nih_stats["all_grants"]:
            pi_lower = g["pi"].lower()
            # Check last name match (most reliable)
            pi_last = pi_lower.split()[-1] if pi_lower else ""
            for sub_pi_lower, sub_pi_orig in submission_pis.items():
                sub_last = sub_pi_lower.split()[-1] if sub_pi_lower else ""
                if pi_last and sub_last and pi_last == sub_last:
                    key = sub_pi_orig
                    if key not in matches:
                        matches[key] = {"submissions": sub_stats["by_pi"].get(sub_pi_orig, 0),
                                        "nih_grants": [], "nsf_grants": []}
                    matches[key]["nih_grants"].append(g["core_number"])

    # Check NSF grants
    if nsf_stats:
        for a in nsf_stats["all_awards"]:
            pi_lower = a["pi"].lower()
            pi_last = pi_lower.split()[-1] if pi_lower else ""
            for sub_pi_lower, sub_pi_orig in submission_pis.items():
                sub_last = sub_pi_lower.split()[-1] if sub_pi_lower else ""
                if pi_last and sub_last and pi_last == sub_last:
                    key = sub_pi_orig
                    if key not in matches:
                        matches[key] = {"submissions": sub_stats["by_pi"].get(sub_pi_orig, 0),
                                        "nih_grants": [], "nsf_grants": []}
                    matches[key]["nsf_grants"].append(a["award_id"])

    return matches


# ==============================================================================
# PI-Based Grant Discovery (lookup each submission PI in NIH/NSF)
# ==============================================================================

def lookup_pi_grants_nih(first_name, last_name):
    """Search NIH Reporter for all active grants by a specific PI."""
    payload = {
        "criteria": {
            "pi_names": [{"first_name": first_name, "last_name": last_name}],
            # Don't filter by org — PI may have moved or have multi-site grants
            "is_active": True,
        },
        "offset": 0,
        "limit": 50,
        "sort_field": "award_amount",
        "sort_order": "desc",
    }
    try:
        resp = requests.post(NIH_API, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException:
        return []


def lookup_pi_grants_nsf(first_name, last_name):
    """Search NSF Award API for active awards by a specific PI."""
    params = {
        "piFirstName": first_name,
        "piLastName": last_name,
        "printFields": "id,title,piFirstName,piLastName,awardeeName,"
                       "fundsObligatedAmt,estimatedTotalAmt,startDate,expDate,"
                       "fundProgramName,activeAwd",
        "rpp": 25,
        "offset": 0,
    }
    try:
        resp = requests.get(NSF_API, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", {}).get("award", [])
    except requests.RequestException:
        return []


def discover_grants_by_submission_pis(submissions, max_pis=200):
    """For each PI in the submission system, look up their federal grants.

    This captures grants where the PI used the core but didn't explicitly
    mention it in the grant text — a much larger net than text search alone.

    Prioritizes PIs with multiple submissions or recent activity to keep
    runtime manageable. Set max_pis=0 for unlimited (slow).
    """
    if not submissions:
        return None

    # Extract unique PIs with both first and last names
    pi_set = {}
    for sub in submissions:
        first = sub.get("PI First Name", "").strip()
        last = sub.get("PI Last Name", "").strip()
        if first and last and len(last) > 1:
            key = f"{first} {last}"
            if key not in pi_set:
                pi_set[key] = {"first": first, "last": last,
                               "submissions": 0, "institute": "",
                               "latest_date": ""}
            pi_set[key]["submissions"] += 1
            inst = sub.get("Institute", "").strip()
            if inst and len(inst) < 100:
                pi_set[key]["institute"] = inst
            # Track most recent submission date
            sub_date = sub.get("Submitted", "")
            if sub_date > pi_set[key]["latest_date"]:
                pi_set[key]["latest_date"] = sub_date

    # Prioritize: sort by submissions (repeat users first), then recency
    sorted_pis = sorted(pi_set.items(),
                        key=lambda x: (x[1]["submissions"], x[1]["latest_date"]),
                        reverse=True)

    if max_pis > 0 and len(sorted_pis) > max_pis:
        print(f"  {len(sorted_pis)} unique PIs found, searching top {max_pis} "
              f"(by frequency + recency)...")
        sorted_pis = sorted_pis[:max_pis]
    else:
        print(f"  Looking up grants for {len(sorted_pis)} unique PIs...")

    results = {
        "pis_searched": len(pi_set),
        "pis_with_nih": 0,
        "pis_with_nsf": 0,
        "total_active_nih_grants": 0,
        "total_active_nih_funding": 0,
        "total_nsf_awards": 0,
        "total_nsf_funding": 0,
        "pi_details": [],
    }

    for i, (name, info) in enumerate(sorted_pis):
        if i > 0 and i % 10 == 0:
            print(f"    Searched {i}/{len(pi_set)} PIs...")

        pi_result = {
            "name": name,
            "submissions": info["submissions"],
            "institute": info["institute"],
            "nih_grants": [],
            "nsf_awards": [],
        }

        # NIH lookup
        nih_results = lookup_pi_grants_nih(info["first"], info["last"])
        for proj in nih_results:
            award = proj.get("award_amount", 0) or 0
            core_num = extract_core_project_number(proj.get("project_num", ""))
            pi_result["nih_grants"].append({
                "grant": core_num or proj.get("project_num", ""),
                "title": proj.get("project_title", ""),
                "amount": award,
                "org": proj.get("organization", {}).get("org_name", "") if proj.get("organization") else "",
            })
        time.sleep(0.2)

        # NSF lookup
        nsf_results = lookup_pi_grants_nsf(info["first"], info["last"])
        for award_data in nsf_results:
            if str(award_data.get("activeAwd", "")).lower() == "true":
                amt = int(award_data.get("fundsObligatedAmt", 0) or 0)
                pi_result["nsf_awards"].append({
                    "award_id": award_data.get("id", ""),
                    "title": award_data.get("title", ""),
                    "amount": amt,
                    "org": award_data.get("awardeeName", ""),
                })
        time.sleep(0.2)

        if pi_result["nih_grants"] or pi_result["nsf_awards"]:
            results["pi_details"].append(pi_result)

        if pi_result["nih_grants"]:
            results["pis_with_nih"] += 1
            results["total_active_nih_grants"] += len(pi_result["nih_grants"])
            results["total_active_nih_funding"] += sum(
                g["amount"] for g in pi_result["nih_grants"]
            )

        if pi_result["nsf_awards"]:
            results["pis_with_nsf"] += 1
            results["total_nsf_awards"] += len(pi_result["nsf_awards"])
            results["total_nsf_funding"] += sum(
                a["amount"] for a in pi_result["nsf_awards"]
            )

    # Sort by total funding
    results["pi_details"].sort(
        key=lambda x: sum(g["amount"] for g in x["nih_grants"]) +
                       sum(a["amount"] for a in x["nsf_awards"]),
        reverse=True,
    )

    # Compute UC Davis vs External funding split
    ucd_funding = 0
    ucd_pis = 0
    ext_funding = 0
    ext_pis = 0
    for pi in results["pi_details"]:
        pi_total = (sum(g["amount"] for g in pi["nih_grants"]) +
                    sum(a["amount"] for a in pi["nsf_awards"]))
        inst = normalize_institute(pi.get("institute", ""))
        if inst == "UC Davis":
            ucd_funding += pi_total
            ucd_pis += 1
        else:
            ext_funding += pi_total
            ext_pis += 1

    results["ucd_pis"] = ucd_pis
    results["ucd_funding"] = ucd_funding
    results["ext_pis"] = ext_pis
    results["ext_funding"] = ext_funding

    print(f"    Done. {results['pis_with_nih']} PIs with active NIH grants, "
          f"{results['pis_with_nsf']} with active NSF awards")
    print(f"    Total active NIH: {results['total_active_nih_grants']} grants, "
          f"${results['total_active_nih_funding']:,.0f}")
    print(f"    Total active NSF: {results['total_nsf_awards']} awards, "
          f"${results['total_nsf_funding']:,.0f}")
    print(f"    UC Davis: {ucd_pis} PIs, ${ucd_funding:,.0f} | "
          f"External: {ext_pis} PIs, ${ext_funding:,.0f}")

    return results


# ==============================================================================
# Figure Generation (matplotlib)
# ==============================================================================

def generate_figures(nih_stats, nsf_stats, pubmed_data, sub_stats, order_stats=None):
    """Generate PNG charts for the report."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("  matplotlib not installed — skipping figure generation")
        print("  Install with: pip install matplotlib")
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

    # Color palette (UC Davis brand)
    UCD_BLUE = "#022851"
    UCD_GOLD = "#FFBF00"
    UCD_GOLD_DARK = "#DAAA00"
    COLORS = ["#022851", "#DAAA00", "#4B7A2D", "#C6922D", "#5B7FA5",
              "#8B4513", "#6B4C9A", "#2E8B57", "#B8860B", "#4682B4",
              "#CD853F", "#708090", "#D2691E", "#3CB371"]

    # --- Figure 1: NIH Funding by Institute (horizontal bar) ---
    if nih_stats and nih_stats["institutes"]:
        fig, ax = plt.subplots(figsize=(10, 6))
        sorted_inst = sorted(nih_stats["institutes"].items(),
                             key=lambda x: x[1]["funding"], reverse=True)
        names = [x[0] for x in sorted_inst]
        funding = [x[1]["funding"] / 1_000_000 for x in sorted_inst]

        bars = ax.barh(names[::-1], funding[::-1], color=UCD_BLUE, edgecolor="white")
        ax.set_xlabel("Funding ($ millions)")
        ax.set_title("NIH Funding by Institute", fontweight="bold", color=UCD_BLUE)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("$%.1fM"))
        for bar, val in zip(bars, funding[::-1]):
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                    f"${val:.1f}M", va="center", fontsize=9)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "nih_funding_by_institute.png")
        plt.close(fig)
        print("    Saved: nih_funding_by_institute.png")

    # --- Figure 2: NIH Funding by Decade (bar chart) ---
    if nih_stats and nih_stats["by_decade"]:
        fig, ax = plt.subplots(figsize=(8, 5))
        decades = sorted(nih_stats["by_decade"].keys())
        funding = [nih_stats["by_decade"][d]["funding"] / 1_000_000 for d in decades]
        counts = [nih_stats["by_decade"][d]["count"] for d in decades]

        bars = ax.bar(decades, funding, color=[UCD_BLUE, UCD_GOLD_DARK, UCD_GOLD][:len(decades)],
                      edgecolor="white", width=0.6)
        ax.set_ylabel("Funding ($ millions)")
        ax.set_title("NIH Funding by Decade", fontweight="bold", color=UCD_BLUE)

        for bar, val, cnt in zip(bars, funding, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"${val:.1f}M\n({cnt} grants)", ha="center", fontsize=10)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "nih_funding_by_decade.png")
        plt.close(fig)
        print("    Saved: nih_funding_by_decade.png")

    # --- Figure 3: Submission Volume Over Time ---
    if sub_stats and sub_stats["by_month"]:
        fig, ax = plt.subplots(figsize=(12, 5))
        months = sorted(sub_stats["by_month"].keys())
        counts = [sub_stats["by_month"][m] for m in months]

        ax.bar(range(len(months)), counts, color=UCD_BLUE, edgecolor="white")
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels(months, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Submissions")
        ax.set_title("Proteomics Core Submissions by Month", fontweight="bold", color=UCD_BLUE)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "submissions_by_month.png")
        plt.close(fig)
        print("    Saved: submissions_by_month.png")

    # --- Figure 4: UC Davis vs External Institutions (pie) ---
    if sub_stats and sub_stats["uc_davis_vs_external"]:
        fig, ax = plt.subplots(figsize=(7, 7))
        ucd = sub_stats["uc_davis_vs_external"]["uc_davis"]
        ext = sub_stats["uc_davis_vs_external"]["external"]
        if ucd + ext > 0:
            ax.pie([ucd, ext], labels=["UC Davis", "External"],
                   autopct="%1.0f%%", colors=[UCD_BLUE, UCD_GOLD_DARK],
                   textprops={"fontsize": 13}, startangle=90)
            ax.set_title("Submissions: UC Davis vs External", fontweight="bold", color=UCD_BLUE)
            plt.tight_layout()
            fig.savefig(FIGURES_DIR / "ucd_vs_external.png")
            plt.close(fig)
            print("    Saved: ucd_vs_external.png")

    # --- Figure 5: Top Organisms ---
    if sub_stats and sub_stats["by_organism"]:
        fig, ax = plt.subplots(figsize=(10, 6))
        top_orgs = sub_stats["by_organism"].most_common(10)
        names = [o[0][:30] for o in top_orgs]
        counts = [o[1] for o in top_orgs]

        bars = ax.barh(names[::-1], counts[::-1], color=COLORS[:len(names)])
        ax.set_xlabel("Number of Submissions")
        ax.set_title("Top Organisms Analyzed", fontweight="bold", color=UCD_BLUE)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "top_organisms.png")
        plt.close(fig)
        print("    Saved: top_organisms.png")

    # --- Figure 6: Top PIs by Submissions ---
    if sub_stats and sub_stats["by_pi"]:
        fig, ax = plt.subplots(figsize=(10, 6))
        top_pis = sub_stats["by_pi"].most_common(15)
        names = [p[0] for p in top_pis]
        counts = [p[1] for p in top_pis]

        bars = ax.barh(names[::-1], counts[::-1], color=UCD_BLUE, edgecolor="white")
        ax.set_xlabel("Number of Submissions")
        ax.set_title("Top Principal Investigators by Usage", fontweight="bold", color=UCD_BLUE)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "top_pis_by_submissions.png")
        plt.close(fig)
        print("    Saved: top_pis_by_submissions.png")

    # --- Figure 7: Institutions served (bar) ---
    if sub_stats and sub_stats["by_institute_normalized"]:
        fig, ax = plt.subplots(figsize=(10, 6))
        top_inst = sub_stats["by_institute_normalized"].most_common(15)
        names = [i[0] for i in top_inst if i[0] != "Unknown"]
        counts = [i[1] for i in top_inst if i[0] != "Unknown"]

        bars = ax.barh(names[::-1], counts[::-1], color=COLORS[:len(names)])
        ax.set_xlabel("Number of Submissions")
        ax.set_title("Institutions Served", fontweight="bold", color=UCD_BLUE)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "institutions_served.png")
        plt.close(fig)
        print("    Saved: institutions_served.png")

    # --- Figure 8: Combined Grant + Submissions Overview ---
    if nih_stats or nsf_stats:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Left: Grant counts
        labels = []
        values = []
        colors = []
        if nih_stats:
            labels.append(f"NIH ({nih_stats['total_grants']})")
            values.append(nih_stats["total_grants"])
            colors.append(UCD_BLUE)
        if nsf_stats and nsf_stats["total_awards"] > 0:
            labels.append(f"NSF ({nsf_stats['total_awards']})")
            values.append(nsf_stats["total_awards"])
            colors.append(UCD_GOLD_DARK)

        if values:
            axes[0].bar(labels, values, color=colors, edgecolor="white", width=0.5)
            axes[0].set_title("Grants by Agency", fontweight="bold", color=UCD_BLUE)
            axes[0].set_ylabel("Number of Grants")

        # Right: Funding
        fund_labels = []
        fund_values = []
        fund_colors = []
        if nih_stats:
            fund_labels.append("NIH")
            fund_values.append(nih_stats["total_funding"] / 1_000_000)
            fund_colors.append(UCD_BLUE)
        if nsf_stats and nsf_stats["total_funding"] > 0:
            fund_labels.append("NSF")
            fund_values.append(nsf_stats["total_funding"] / 1_000_000)
            fund_colors.append(UCD_GOLD_DARK)

        if fund_values:
            bars = axes[1].bar(fund_labels, fund_values, color=fund_colors,
                               edgecolor="white", width=0.5)
            axes[1].set_title("Total Funding by Agency", fontweight="bold", color=UCD_BLUE)
            axes[1].set_ylabel("Funding ($ millions)")
            axes[1].yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.1fM"))

        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "grants_overview.png")
        plt.close(fig)
        print("    Saved: grants_overview.png")

    # --- Revenue by Year (dual-axis: bars + line) ---
    if order_stats and order_stats.get("revenue_by_year") and order_stats.get("orders_by_year"):
        years = sorted(order_stats["revenue_by_year"].keys())
        revenue = [order_stats["revenue_by_year"][y] / 1_000_000 for y in years]
        orders = [order_stats["orders_by_year"][y] for y in years]

        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Bars for revenue (left axis)
        bar_width = 0.6
        x_pos = range(len(years))
        bars = ax1.bar(x_pos, revenue, width=bar_width, color=UCD_BLUE,
                       edgecolor="white", label="Revenue", zorder=2)
        ax1.set_xlabel("Year")
        ax1.set_ylabel("Revenue ($ millions)", color=UCD_BLUE)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels([str(y) for y in years], rotation=45, ha="right")
        ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.1fM"))
        ax1.tick_params(axis="y", labelcolor=UCD_BLUE)

        # Add value labels on bars
        for bar, val in zip(bars, revenue):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                     f"${val:.1f}M", ha="center", va="bottom", fontsize=8,
                     color=UCD_BLUE)

        # Line for order count (right axis)
        ax2 = ax1.twinx()
        ax2.plot(x_pos, orders, color=UCD_GOLD_DARK, marker="o", linewidth=2,
                 markersize=6, label="Orders", zorder=3)
        ax2.set_ylabel("Number of Orders", color=UCD_GOLD_DARK)
        ax2.tick_params(axis="y", labelcolor=UCD_GOLD_DARK)

        # Add value labels on line points
        for x, val in zip(x_pos, orders):
            ax2.annotate(str(val), (x, val), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8,
                         color=UCD_GOLD_DARK)

        ax1.set_title("Revenue & Orders by Year", fontweight="bold", color=UCD_BLUE)

        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "revenue_by_year.png")
        plt.close(fig)
        print("    Saved: revenue_by_year.png")


# ==============================================================================
# Report Generation
# ==============================================================================

def filter_orders_by_service(order_stats, service_type):
    """Return a filtered copy of order_stats with only MS or AAA orders/revenue.

    Args:
        order_stats: dict from compute_order_statistics()
        service_type: "ms" or "aaa"

    Returns:
        A new dict with the same structure, but totals reflect only the
        selected service type.  Returns None if order_stats is None.
    """
    if not order_stats:
        return None

    filtered = {
        "total_orders": 0,
        "total_revenue": 0,
        "revenue_by_year": defaultdict(float),
        "orders_by_year": Counter(),
        "revenue_by_service_type": defaultdict(float),
        "orders_by_service_type": Counter(),
        "ms_orders": 0,
        "ms_revenue": 0,
        "aaa_orders": 0,
        "aaa_revenue": 0,
        "other_orders": 0,
        "other_revenue": 0,
        "date_range": order_stats.get("date_range", {"earliest": None, "latest": None}),
    }

    if service_type == "ms":
        filtered["total_orders"] = order_stats["ms_orders"]
        filtered["total_revenue"] = order_stats["ms_revenue"]
        filtered["ms_orders"] = order_stats["ms_orders"]
        filtered["ms_revenue"] = order_stats["ms_revenue"]
        svc_key = "Mass Spectrometry"
        if svc_key in order_stats["revenue_by_service_type"]:
            filtered["revenue_by_service_type"][svc_key] = order_stats["revenue_by_service_type"][svc_key]
            filtered["orders_by_service_type"][svc_key] = order_stats["orders_by_service_type"][svc_key]
    elif service_type == "aaa":
        filtered["total_orders"] = order_stats["aaa_orders"]
        filtered["total_revenue"] = order_stats["aaa_revenue"]
        filtered["aaa_orders"] = order_stats["aaa_orders"]
        filtered["aaa_revenue"] = order_stats["aaa_revenue"]
        svc_key = "Amino Acid Analysis"
        if svc_key in order_stats["revenue_by_service_type"]:
            filtered["revenue_by_service_type"][svc_key] = order_stats["revenue_by_service_type"][svc_key]
            filtered["orders_by_service_type"][svc_key] = order_stats["orders_by_service_type"][svc_key]

    return filtered


def generate_comprehensive_report(nih_stats, nsf_stats, pubmed_data, sub_stats, cross_refs,
                                   nih_pubs_data=None, pi_grants_data=None,
                                   order_stats=None, report_title=None,
                                   report_note=None):
    """Generate the full markdown impact report.

    Args:
        report_title: Optional custom title (overrides the default).
        report_note: Optional note inserted below the date line (e.g. scope
                     disclaimer for service-filtered reports).
    """
    today = date.today().isoformat()
    title = report_title or "UC Davis Proteomics Core Facility — Comprehensive Impact Report"
    lines = [
        f"# {title}",
        "",
        f"*Auto-generated on {today}*",
        "",
    ]
    if report_note:
        lines.extend([f"*{report_note}*", ""])
    lines.extend([
        "---",
        "",
    ])

    # === Executive Summary ===
    lines.extend(["## Executive Summary", ""])
    lines.extend(["### Grant Funding", ""])
    lines.extend([
        "| Source | Grants | Total Funding | Active | Active Funding |",
        "|--------|--------|---------------|--------|----------------|",
    ])
    if nih_stats:
        active_funding = sum(g["award_amount"] for g in nih_stats["active_grants"])
        lines.append(
            f"| NIH | {nih_stats['total_grants']} | "
            f"${nih_stats['total_funding']:,.0f} | "
            f"{len(nih_stats['active_grants'])} | ${active_funding:,.0f} |"
        )
    if nsf_stats and nsf_stats["total_awards"] > 0:
        active_nsf_funding = sum(a["amount"] for a in nsf_stats["active_awards"])
        lines.append(
            f"| NSF | {nsf_stats['total_awards']} | "
            f"${nsf_stats['total_funding']:,.0f} | "
            f"{len(nsf_stats['active_awards'])} | ${active_nsf_funding:,.0f} |"
        )
    lines.append("")

    # Instrument grant publications
    if nih_pubs_data:
        lines.extend([
            "### Instrument Grant Scholarly Impact", "",
            f"- **{nih_pubs_data['total_publications']}** publications linked to core instrument grants",
            f"- **{nih_pubs_data['total_citations']:,}** total citations (via NIH iCite)",
            "",
        ])

    # Publications summary
    if pubmed_data and pubmed_data["count"] > 0:
        lines.extend([
            "### Publications", "",
            f"- **{pubmed_data['count']}** publications by core personnel found in PubMed",
            f"- **{len(pubmed_data['grants_from_pubs'])}** unique grant numbers extracted from publication acknowledgments",
            "",
        ])

    # Submission summary
    if sub_stats:
        lines.extend([
            "### Core Usage (Submission System)", "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Date range | {sub_stats['date_range'].get('earliest_str', 'N/A')} to "
            f"{sub_stats['date_range'].get('latest_str', 'N/A')} |",
            f"| Total submissions | **{sub_stats['total_submissions']}** |",
            f"| Total samples processed | **{sub_stats['total_samples']:,}** |",
            f"| Unique principal investigators | **{sub_stats['unique_pis_count']}** |",
            f"| Unique submitters | **{sub_stats['unique_submitters_count']}** |",
            f"| Institutions served | **{sub_stats['unique_institutes_count']}** |",
            f"| Repeat PI rate | **{sub_stats['repeat_pi_rate']:.0f}%** |",
            f"| Data analysis requested | **{sub_stats['data_analysis_requested']}** "
            f"({sub_stats['data_analysis_requested'] / sub_stats['total_submissions'] * 100:.0f}%) |",
            "",
        ])

    # Revenue summary
    if order_stats:
        lines.extend([
            "### Revenue & Services", "",
            "| Metric | All Services | Mass Spec Only | AAA Only |",
            "|--------|-------------|----------------|----------|",
            f"| Orders | {order_stats['total_orders']:,} | "
            f"{order_stats['ms_orders']:,} | {order_stats['aaa_orders']:,} |",
            f"| Revenue | ${order_stats['total_revenue']:,.0f} | "
            f"${order_stats['ms_revenue']:,.0f} | ${order_stats['aaa_revenue']:,.0f} |",
            "",
            "### Revenue by Year", "",
            "| Year | Orders | Revenue |",
            "|------|--------|---------|",
        ])
        for year in sorted(order_stats["revenue_by_year"].keys()):
            lines.append(
                f"| {year} | {order_stats['orders_by_year'][year]} | "
                f"${order_stats['revenue_by_year'][year]:,.0f} |"
            )
        lines.append("")

    # === NIH Details ===
    if nih_stats:
        lines.extend(["---", "", "## NIH Grants", ""])

        # Phinney direct grants
        if nih_stats["phinney_grants"]:
            lines.extend([
                "### Direct Instrument Grants (PI: Brett Phinney)", "",
                "| Grant | Title | Year | Amount |",
                "|-------|-------|------|--------|",
            ])
            total_phinney = 0
            for g in sorted(nih_stats["phinney_grants"], key=lambda x: x.get("fiscal_year", 0)):
                lines.append(
                    f"| {g['core_number']} | {g['title'][:60]} | {g['fiscal_year']} | ${g['award_amount']:,.0f} |"
                )
                total_phinney += g["award_amount"]
            lines.extend([
                f"| **Total** | | | **${total_phinney:,.0f}** |", "",
            ])

        # By decade
        lines.extend([
            "### Funding by Decade", "",
            "| Decade | Grants | Funding |",
            "|--------|--------|---------|",
        ])
        for decade in sorted(nih_stats["by_decade"].keys()):
            d = nih_stats["by_decade"][decade]
            lines.append(f"| {decade} | {d['count']} | ${d['funding']:,.0f} |")
        lines.append("")

        # By institute
        lines.extend([
            "### NIH Institutes Represented", "",
            "| Institute | Grants | Funding |",
            "|-----------|--------|---------|",
        ])
        sorted_inst = sorted(nih_stats["institutes"].items(),
                             key=lambda x: x[1]["funding"], reverse=True)
        for abbr, data in sorted_inst:
            lines.append(f"| {abbr} | {data['count']} | ${data['funding']:,.0f} |")
        lines.append("")

        # Active grants
        if nih_stats["active_grants"]:
            lines.extend([
                "### Currently Active NIH Grants", "",
                "| Grant | PI | Title | Funding |",
                "|-------|----|-------|---------|",
            ])
            for g in sorted(nih_stats["active_grants"], key=lambda x: x["award_amount"], reverse=True):
                lines.append(
                    f"| {g['core_number']} | {g['pi']} | {g['title'][:50]} | ${g['award_amount']:,.0f} |"
                )
            lines.append("")

        # All NIH grants
        lines.extend([
            "### All NIH Grants", "",
            "| Grant | PI | Title | Institute | Funding | Active |",
            "|-------|----|-------|-----------|---------|--------|",
        ])
        for g in sorted(nih_stats["all_grants"], key=lambda x: x["award_amount"], reverse=True):
            active_str = "Yes" if g["active"] else "No"
            lines.append(
                f"| {g['core_number']} | {g['pi'][:20]} | {g['title'][:40]} | "
                f"{g['institute']} | ${g['award_amount']:,.0f} | {active_str} |"
            )
        lines.append("")

    # === Instrument Grant Publications + Citations ===
    if nih_pubs_data:
        lines.extend(["---", "", "## Instrument Grant Publications & Citation Impact", ""])
        lines.extend([
            f"Publications linked to core instrument grants (S10 awards) via NIH Reporter,",
            f"with citation metrics from NIH iCite:",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total publications | **{nih_pubs_data['total_publications']}** |",
            f"| Total citations | **{nih_pubs_data['total_citations']:,}** |",
            "",
        ])

        # By grant
        if nih_pubs_data.get("by_grant"):
            lines.extend([
                "### Publications per Instrument Grant", "",
                "| Grant | Publications |",
                "|-------|-------------|",
            ])
            for grant, count in sorted(nih_pubs_data["by_grant"].items(),
                                       key=lambda x: x[1], reverse=True):
                lines.append(f"| {grant} | {count} |")
            lines.append("")

        # Top cited publications
        top_pubs = [p for p in nih_pubs_data["publications"] if p.get("citation_count", 0) > 0][:20]
        if top_pubs:
            lines.extend([
                "### Most-Cited Publications", "",
                "| Citations | Title | Year | Grants |",
                "|-----------|-------|------|--------|",
            ])
            for pub in top_pubs:
                grants_str = ", ".join(pub.get("grants", [])[:3])
                lines.append(
                    f"| {pub.get('citation_count', 0)} | {pub['title'][:60]} | "
                    f"{pub.get('year', '')} | {grants_str} |"
                )
            lines.append("")

    # === NSF Details ===
    if nsf_stats and nsf_stats["total_awards"] > 0:
        lines.extend(["---", "", "## NSF Awards", ""])
        lines.extend([
            "| Award ID | PI | Title | Amount | Program | Active |",
            "|----------|----|-------|--------|---------|--------|",
        ])
        for a in sorted(nsf_stats["all_awards"], key=lambda x: x["amount"], reverse=True):
            active_str = "Yes" if a["active"] else "No"
            lines.append(
                f"| {a['award_id']} | {a['pi'][:20]} | {a['title'][:40]} | "
                f"${a['amount']:,.0f} | {a['program'][:20]} | {active_str} |"
            )
        lines.append("")

    # === Publications ===
    if pubmed_data and pubmed_data["publications"]:
        lines.extend(["---", "", "## Publications", ""])

        # By year
        pub_by_year = Counter()
        for pub in pubmed_data["publications"]:
            year = pub.get("year", "Unknown")
            pub_by_year[year] += 1

        lines.extend(["### Publications by Year", ""])
        lines.extend(["| Year | Count |", "|------|-------|"])
        for year in sorted(pub_by_year.keys(), reverse=True):
            lines.append(f"| {year} | {pub_by_year[year]} |")
        lines.append("")

        # Grants cited in publications
        if pubmed_data["grants_from_pubs"]:
            lines.extend([
                "### Grant Numbers Cited in Publications", "",
                "| Grant ID | Agency | # Papers |",
                "|----------|--------|----------|",
            ])
            sorted_grants = sorted(pubmed_data["grants_from_pubs"].items(),
                                   key=lambda x: len(x[1]["citing_pmids"]), reverse=True)
            for gid, info in sorted_grants[:50]:  # Top 50
                lines.append(
                    f"| {info['grant_id']} | {info['agency'][:30]} | {len(info['citing_pmids'])} |"
                )
            lines.append("")

    # === Submission Analytics ===
    if sub_stats:
        lines.extend(["---", "", "## Core Usage Analytics", ""])

        # Institutions
        lines.extend([
            "### Institutions Served", "",
            "| Institution | Submissions |",
            "|-------------|-------------|",
        ])
        for inst, count in sub_stats["by_institute_normalized"].most_common(20):
            if inst != "Unknown":
                lines.append(f"| {inst} | {count} |")
        lines.append("")

        # UC Davis Departments
        if sub_stats.get("by_ucd_department"):
            lines.extend([
                "### UC Davis Departments", "",
                "| Department / School | Submissions |",
                "|---------------------|-------------|",
            ])
            for dept, count in sub_stats["by_ucd_department"].most_common(20):
                lines.append(f"| {dept} | {count} |")
            lines.append("")

        # Top PIs
        lines.extend([
            "### Top Principal Investigators", "",
            "| PI | Submissions |",
            "|----|-------------|",
        ])
        for pi, count in sub_stats["by_pi"].most_common(20):
            lines.append(f"| {pi} | {count} |")
        lines.append("")

        # Organisms
        lines.extend([
            "### Organisms Analyzed", "",
            "| Organism | Submissions |",
            "|----------|-------------|",
        ])
        for org, count in sub_stats["by_organism"].most_common(15):
            lines.append(f"| {org} | {count} |")
        lines.append("")

        # Quarterly trends
        lines.extend([
            "### Quarterly Submission Trends", "",
            "| Quarter | Submissions |",
            "|---------|-------------|",
        ])
        for q in sorted(sub_stats["by_quarter"].keys()):
            lines.append(f"| {q} | {sub_stats['by_quarter'][q]} |")
        lines.append("")

    # === Cross-References ===
    if cross_refs:
        lines.extend(["---", "", "## Cross-Reference: Submission PIs with Grants", ""])
        lines.extend([
            "PIs who have both submitted samples AND have NIH/NSF grants:",
            "",
            "| PI | Submissions | NIH Grants | NSF Awards |",
            "|----|-------------|------------|------------|",
        ])
        for pi, data in sorted(cross_refs.items(), key=lambda x: x[1]["submissions"], reverse=True):
            nih_list = ", ".join(data["nih_grants"][:3])
            if len(data["nih_grants"]) > 3:
                nih_list += f" (+{len(data['nih_grants']) - 3})"
            nsf_list = ", ".join(data["nsf_grants"][:3])
            if len(data["nsf_grants"]) > 3:
                nsf_list += f" (+{len(data['nsf_grants']) - 3})"
            lines.append(
                f"| {pi} | {data['submissions']} | {nih_list or '—'} | {nsf_list or '—'} |"
            )
        lines.append("")

    # === PI Grant Discovery ===
    if pi_grants_data:
        lines.extend(["---", "",
            "## Federal Grants Held by Core Users", "",
            "Researchers who submitted samples to the proteomics core and their active",
            "federal grants (discovered via NIH Reporter and NSF Award APIs).", "",
            "**This demonstrates the research infrastructure the core supports,**",
            "**even when grants don't explicitly name the core in their text.**", "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| PIs searched | {pi_grants_data['pis_searched']} |",
            f"| PIs with active NIH grants | **{pi_grants_data['pis_with_nih']}** |",
            f"| PIs with active NSF awards | **{pi_grants_data['pis_with_nsf']}** |",
            f"| Total active NIH grants | **{pi_grants_data['total_active_nih_grants']}** |",
            f"| Total active NIH funding | **${pi_grants_data['total_active_nih_funding']:,.0f}** |",
            f"| Total active NSF awards | **{pi_grants_data['total_nsf_awards']}** |",
            f"| Total active NSF funding | **${pi_grants_data['total_nsf_funding']:,.0f}** |",
            "",
            "### UC Davis vs External Funding", "",
            "| Category | PIs | Active Federal Funding |",
            "|----------|-----|------------------------|",
            f"| UC Davis researchers | {pi_grants_data.get('ucd_pis', 0)} | "
            f"**${pi_grants_data.get('ucd_funding', 0):,.0f}** |",
            f"| External researchers | {pi_grants_data.get('ext_pis', 0)} | "
            f"**${pi_grants_data.get('ext_funding', 0):,.0f}** |",
            f"| **Total** | **{pi_grants_data.get('ucd_pis', 0) + pi_grants_data.get('ext_pis', 0)}** | "
            f"**${pi_grants_data.get('ucd_funding', 0) + pi_grants_data.get('ext_funding', 0):,.0f}** |",
            "",
        ])

        # Top PIs by funding
        if pi_grants_data["pi_details"]:
            lines.extend([
                "### Core Users by Federal Funding (Top 25)", "",
                "| PI | Submissions | NIH Grants | NIH Funding | NSF Awards | NSF Funding |",
                "|----|-------------|------------|-------------|------------|-------------|",
            ])
            for pi in pi_grants_data["pi_details"][:25]:
                nih_total = sum(g["amount"] for g in pi["nih_grants"])
                nsf_total = sum(a["amount"] for a in pi["nsf_awards"])
                lines.append(
                    f"| {pi['name']} | {pi['submissions']} | "
                    f"{len(pi['nih_grants'])} | ${nih_total:,.0f} | "
                    f"{len(pi['nsf_awards'])} | ${nsf_total:,.0f} |"
                )
            lines.append("")

    # === Figures ===
    if FIGURES_DIR.exists() and any(FIGURES_DIR.glob("*.png")):
        lines.extend(["---", "", "## Figures", ""])
        for fig_path in sorted(FIGURES_DIR.glob("*.png")):
            name = fig_path.stem.replace("_", " ").title()
            lines.append(f"### {name}")
            lines.append(f"![{name}](figures/{fig_path.name})")
            lines.append("")

    return "\n".join(lines)


# ==============================================================================
# Executive Summary PDF
# ==============================================================================

GITHUB_REPO_URL = "https://github.com/bsphinney/proteomics-core-site"


def generate_data_index_pdf():
    """Generate a one-page PDF with links to all data files on GitHub."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError:
        print("  matplotlib not installed — skipping data index PDF")
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = REPORT_DIR / "data_index.pdf"

    UCD_BLUE = "#022851"
    UCD_GOLD_DARK = "#DAAA00"

    base = f"{GITHUB_REPO_URL}/blob/main"

    with PdfPages(str(pdf_path)) as pdf:
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Title
        ax.text(0.5, 0.94, "UC Davis Proteomics Core Facility",
                ha="center", fontsize=20, fontweight="bold", color=UCD_BLUE)
        ax.text(0.5, 0.905, "Impact Report — Data Index & Downloads",
                ha="center", fontsize=14, color=UCD_GOLD_DARK)
        ax.text(0.5, 0.875, f"Generated: {date.today().isoformat()}",
                ha="center", fontsize=10, color="#666666")

        # Gold line
        ax.plot([0.1, 0.9], [0.86, 0.86], color=UCD_GOLD_DARK, linewidth=2)

        # Repository link
        ax.text(0.5, 0.83, f"Repository: {GITHUB_REPO_URL}",
                ha="center", fontsize=11, color=UCD_BLUE, fontstyle="italic")

        # Data sections
        y = 0.78
        sections = [
            ("Reports", [
                ("Comprehensive Impact Report (all services)", f"{base}/reports/impact_report_latest.md"),
                ("Mass Spectrometry Only Report", f"{base}/reports/impact_report_ms_only_latest.md"),
                ("Amino Acid Analysis Only Report", f"{base}/reports/impact_report_aaa_only_latest.md"),
                ("Executive Summary (PDF)", f"{base}/reports/executive_summary.pdf"),
            ]),
            ("Spreadsheets (CSV)", [
                ("NIH Grants — 45 grants, $26.2M", f"{base}/reports/nih_grants_2026-03-13.csv"),
                ("NSF Awards — 73 awards, $34.1M", f"{base}/reports/nsf_awards_2026-03-13.csv"),
                ("Core User PI Grants — backs the $1.6B claim", f"{base}/reports/core_user_grants_2026-03-13.csv"),
            ]),
            ("Charts (PNG)", [
                ("NIH Funding by Institute", f"{base}/reports/figures/nih_funding_by_institute.png"),
                ("NIH Funding by Decade", f"{base}/reports/figures/nih_funding_by_decade.png"),
                ("Revenue & Orders by Year", f"{base}/reports/figures/revenue_by_year.png"),
                ("Submissions by Month (11 years)", f"{base}/reports/figures/submissions_by_month.png"),
                ("UC Davis vs External Submissions", f"{base}/reports/figures/ucd_vs_external.png"),
                ("Top Organisms Analyzed", f"{base}/reports/figures/top_organisms.png"),
                ("Top PIs by Submissions", f"{base}/reports/figures/top_pis_by_submissions.png"),
                ("Institutions Served", f"{base}/reports/figures/institutions_served.png"),
                ("Grants Overview (NIH + NSF)", f"{base}/reports/figures/grants_overview.png"),
            ]),
            ("Machine-Readable Data", [
                ("JSON data (for website integration)", f"{base}/reports/impact_data.json"),
            ]),
            ("Source Code", [
                ("Impact report generator script", f"{base}/scripts/impact_report.py"),
                ("GitHub Actions workflow (monthly)", f"{base}/.github/workflows/impact-report.yml"),
            ]),
        ]

        for section_title, items in sections:
            ax.text(0.08, y, section_title, fontsize=13, fontweight="bold", color=UCD_BLUE)
            y -= 0.03
            for label, url in items:
                ax.text(0.10, y, f"• {label}", fontsize=9, color="#333333")
                ax.text(0.10, y - 0.018, url, fontsize=7, color="#0066cc", fontstyle="italic")
                y -= 0.04
            y -= 0.01

        # Footer
        ax.text(0.5, 0.02, "UC Davis Proteomics Core Facility  •  proteomics.ucdavis.edu",
                ha="center", fontsize=8, color="#999999")

        pdf.savefig(fig)
        plt.close(fig)

    print(f"  Data Index PDF: {pdf_path}")


def generate_executive_summary_pdf(nih_stats, nsf_stats, nih_pubs_data,
                                   sub_stats, order_stats, pi_grants_data):
    """Generate a one-page executive summary PDF using matplotlib's PDF backend.

    Produces a clean, infographic-style page (US Letter, 8.5x11") with key
    impact metrics displayed in large bold numbers arranged in a grid.
    Saved to ``reports/executive_summary.pdf``.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError:
        print("  matplotlib not installed — skipping executive summary PDF")
        return

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = REPORT_DIR / "executive_summary.pdf"

    # UC Davis brand colours
    UCD_BLUE = "#022851"
    UCD_GOLD = "#FFBF00"
    UCD_GOLD_DARK = "#DAAA00"
    LIGHT_BG = "#F7F7F7"

    # ---- Gather metrics (handle None gracefully) ----
    def _safe(val, fmt=",.0f", prefix="$", fallback="N/A"):
        """Format a numeric value safely, returning *fallback* on None."""
        if val is None:
            return fallback
        try:
            return f"{prefix}{val:{fmt}}" if prefix else f"{val:{fmt}}"
        except (ValueError, TypeError):
            return fallback

    # Total grant funding (NIH + NSF)
    nih_funding = nih_stats["total_funding"] if nih_stats else None
    nsf_funding = nsf_stats["total_funding"] if nsf_stats else None
    if nih_funding is not None or nsf_funding is not None:
        total_grant_funding = (nih_funding or 0) + (nsf_funding or 0)
    else:
        total_grant_funding = None

    # Publications & citations (from nih_pubs_data / iCite)
    total_pubs = nih_pubs_data["total_publications"] if nih_pubs_data else None
    total_citations = nih_pubs_data["total_citations"] if nih_pubs_data else None

    # Submissions
    total_submissions = sub_stats["total_submissions"] if sub_stats else None
    sub_date_range = ""
    if sub_stats and sub_stats.get("date_range"):
        dr = sub_stats["date_range"]
        earliest = dr.get("earliest_str", "")
        latest = dr.get("latest_str", "")
        if earliest and latest:
            sub_date_range = f"{earliest} \u2013 {latest}"

    # Revenue
    total_revenue = order_stats["total_revenue"] if order_stats else None

    # Unique PIs & institutions
    unique_pis = sub_stats["unique_pis_count"] if sub_stats else None
    unique_inst = sub_stats["unique_institutes_count"] if sub_stats else None

    # Active federal funding held by core users
    if pi_grants_data:
        active_fed_funding = (pi_grants_data.get("total_active_nih_funding", 0) +
                              pi_grants_data.get("total_nsf_funding", 0))
    else:
        active_fed_funding = None

    # ---- Build the metric cards ----
    # Each card: (label, value_string, sub_label_or_empty)
    cards = [
        ("Total Grant Funding",
         _safe(total_grant_funding, ",.0f", "$"),
         "(NIH + NSF combined)"),
        ("Publications / Citations",
         f"{_safe(total_pubs, ',', '')} / {_safe(total_citations, ',', '')}",
         "from instrument grants"),
        ("Sample Submissions",
         _safe(total_submissions, ",", ""),
         sub_date_range if sub_date_range else ""),
        ("Core Revenue",
         _safe(total_revenue, ",.0f", "$"),
         ""),
        ("Unique PIs Served",
         _safe(unique_pis, ",", ""),
         ""),
        ("Institutions Served",
         _safe(unique_inst, ",", ""),
         ""),
        ("Active Federal Funding",
         _safe(active_fed_funding, ",.0f", "$"),
         "held by core users"),
    ]

    # ---- Layout on a letter-size page (8.5 x 11 inches) ----
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor("white")

    # Title
    fig.text(0.50, 0.94,
             "UC Davis Proteomics Core Facility",
             fontsize=22, fontweight="bold", color=UCD_BLUE,
             ha="center", va="center", family="sans-serif")
    fig.text(0.50, 0.91,
             "Impact Summary",
             fontsize=18, fontweight="bold", color=UCD_GOLD_DARK,
             ha="center", va="center", family="sans-serif")

    # Date line
    fig.text(0.50, 0.885,
             f"Generated {date.today().strftime('%B %d, %Y')}",
             fontsize=10, color="#666666",
             ha="center", va="center", family="sans-serif")

    # Horizontal gold rule under the header
    line_ax = fig.add_axes([0.10, 0.875, 0.80, 0.003])
    line_ax.set_facecolor(UCD_GOLD)
    line_ax.set_xticks([])
    line_ax.set_yticks([])
    for spine in line_ax.spines.values():
        spine.set_visible(False)

    # Metric cards in a grid — 2 columns (last card centred if odd)
    n_cols = 2
    n_rows = (len(cards) + 1) // n_cols

    card_w = 0.38       # width of each card
    card_h = 0.095      # height of each card
    x_margin = 0.06
    x_gap = 0.06
    y_top = 0.83
    y_gap = 0.015

    for idx, (label, value, sub) in enumerate(cards):
        row = idx // n_cols
        col = idx % n_cols

        # Centre the last card if it's alone in its row
        if idx == len(cards) - 1 and len(cards) % 2 == 1:
            x = 0.50 - card_w / 2
        else:
            x = x_margin + col * (card_w + x_gap)

        y = y_top - row * (card_h + y_gap)

        # Card background
        card_ax = fig.add_axes([x, y - card_h, card_w, card_h])
        card_ax.set_facecolor(LIGHT_BG)
        card_ax.set_xticks([])
        card_ax.set_yticks([])
        for spine in card_ax.spines.values():
            spine.set_edgecolor("#DDDDDD")
            spine.set_linewidth(0.8)

        # Top accent line on the card
        accent_ax = fig.add_axes([x, y - 0.003, card_w, 0.003])
        accent_ax.set_facecolor(UCD_BLUE if col == 0 else UCD_GOLD_DARK)
        accent_ax.set_xticks([])
        accent_ax.set_yticks([])
        for spine in accent_ax.spines.values():
            spine.set_visible(False)

        # Value (big, bold)
        fig.text(x + card_w / 2, y - card_h * 0.35,
                 value,
                 fontsize=20, fontweight="bold", color=UCD_BLUE,
                 ha="center", va="center", family="sans-serif")

        # Label
        fig.text(x + card_w / 2, y - card_h * 0.70,
                 label,
                 fontsize=10, color="#333333",
                 ha="center", va="center", family="sans-serif")

        # Sub-label (smaller, grey)
        if sub:
            fig.text(x + card_w / 2, y - card_h * 0.92,
                     sub,
                     fontsize=7.5, color="#888888",
                     ha="center", va="center", family="sans-serif",
                     style="italic")

    # ---- Breakdown sidebar: NIH vs NSF ----
    breakdown_y = y_top - n_rows * (card_h + y_gap) - 0.04
    fig.text(0.50, breakdown_y,
             "Funding Breakdown",
             fontsize=13, fontweight="bold", color=UCD_BLUE,
             ha="center", va="center", family="sans-serif")

    breakdown_y -= 0.025
    line2 = fig.add_axes([0.25, breakdown_y, 0.50, 0.002])
    line2.set_facecolor(UCD_GOLD)
    line2.set_xticks([])
    line2.set_yticks([])
    for spine in line2.spines.values():
        spine.set_visible(False)

    col_items = []
    if nih_stats:
        col_items.append(("NIH Grants",
                          f"{nih_stats['total_grants']}",
                          f"${nih_stats['total_funding']:,.0f}"))
    if nsf_stats:
        col_items.append(("NSF Awards",
                          f"{nsf_stats['total_awards']}",
                          f"${nsf_stats['total_funding']:,.0f}"))
    if pi_grants_data:
        pis_total = (pi_grants_data.get("pis_with_nih", 0) +
                     pi_grants_data.get("pis_with_nsf", 0))
        col_items.append(("Core-User PIs with Federal Grants",
                          f"{pis_total}",
                          ""))

    for i, (c_label, c_count, c_funding) in enumerate(col_items):
        cy = breakdown_y - 0.03 - i * 0.025
        fig.text(0.15, cy, c_label, fontsize=9, color="#333333",
                 ha="left", va="center", family="sans-serif")
        fig.text(0.62, cy, c_count, fontsize=9, fontweight="bold",
                 color=UCD_BLUE, ha="center", va="center", family="sans-serif")
        if c_funding:
            fig.text(0.82, cy, c_funding, fontsize=9, color=UCD_GOLD_DARK,
                     ha="center", va="center", family="sans-serif",
                     fontweight="bold")

    # ---- Footer ----
    fig.text(0.50, 0.03,
             "UC Davis Proteomics Core Facility  |  proteomics.ucdavis.edu",
             fontsize=8, color="#999999", ha="center", va="center",
             family="sans-serif")

    # ---- Save ----
    with PdfPages(str(pdf_path)) as pdf:
        pdf.savefig(fig)
    plt.close(fig)

    print(f"  Executive Summary PDF: {pdf_path}")


# ==============================================================================
# Main
# ==============================================================================

def main():
    args = set(sys.argv[1:])

    print("=" * 70)
    print("UC Davis Proteomics Core — Comprehensive Impact Report Generator")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 70)

    skip_pubmed = "--skip-pubmed" in args
    skip_nsf = "--skip-nsf" in args
    skip_submissions = "--skip-submissions" in args
    skip_citations = "--skip-citations" in args
    skip_pi_lookup = "--skip-pi-lookup" in args
    nih_only = "--nih-only" in args

    if nih_only:
        skip_pubmed = skip_nsf = skip_submissions = skip_citations = skip_pi_lookup = True

    nih_stats = None
    nsf_stats = None
    pubmed_data = None
    nih_pubs_data = None
    pi_grants_data = None
    sub_stats = None
    order_stats = None
    cross_refs = {}

    # --- NIH ---
    print("\n[1/6] NIH Reporter API...")
    nih_projects = run_nih_searches()
    if nih_projects:
        nih_stats = compute_nih_statistics(nih_projects)

    # --- NIH Publications + Citation Metrics ---
    if not skip_citations and nih_stats:
        print("\n[2/6] NIH Reporter Publications + iCite Citations...")
        nih_pubs_data = run_nih_publications_search(nih_stats)
    else:
        print("\n[2/6] NIH Publications — skipped")

    # --- NSF ---
    if not skip_nsf:
        print("\n[3/6] NSF Award API...")
        nsf_awards = run_nsf_searches()
        if nsf_awards:
            nsf_stats = compute_nsf_statistics(nsf_awards)
    else:
        print("\n[3/6] NSF — skipped")

    # --- PubMed ---
    if not skip_pubmed:
        print("\n[4/6] PubMed E-utilities...")
        pubmed_data = run_pubmed_searches()
    else:
        print("\n[4/6] PubMed — skipped")

    # --- Submissions + Orders ---
    submissions = []
    if not skip_submissions:
        print("\n[5/6] Submission & Order Analytics...")
        submissions = load_submissions()
        if submissions:
            sub_stats = compute_submission_statistics(submissions)
            cross_refs = cross_reference_submissions_with_grants(
                sub_stats, nih_stats, nsf_stats
            )
        orders = load_orders()
        if orders:
            order_stats = compute_order_statistics(orders)
    else:
        print("\n[5/6] Submissions — skipped")

    # --- PI Grant Discovery ---
    if not skip_pi_lookup and not skip_submissions and submissions:
        print("\n[6/6] PI Grant Discovery (searching NIH/NSF for each submission PI)...")
        pi_grants_data = discover_grants_by_submission_pis(submissions)
    else:
        print("\n[6/6] PI Grant Discovery — skipped")

    # --- Generate Outputs ---
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()

    # Figures
    print("\nGenerating figures...")
    generate_figures(nih_stats, nsf_stats, pubmed_data, sub_stats, order_stats)

    # Markdown report
    print("\nGenerating reports...")
    md_report = generate_comprehensive_report(
        nih_stats, nsf_stats, pubmed_data, sub_stats, cross_refs, nih_pubs_data,
        pi_grants_data, order_stats
    )
    md_path = REPORT_DIR / f"impact_report_{today_str}.md"
    md_path.write_text(md_report)
    print(f"  Markdown: {md_path}")

    latest_md = REPORT_DIR / "impact_report_latest.md"
    latest_md.write_text(md_report)
    print(f"  Latest: {latest_md}")

    # --- Mass Spec Only report ---
    ms_order_stats = filter_orders_by_service(order_stats, "ms")
    ms_report = generate_comprehensive_report(
        nih_stats, nsf_stats, pubmed_data, sub_stats, cross_refs, nih_pubs_data,
        pi_grants_data, ms_order_stats,
        report_title="UC Davis Proteomics Core Facility — Mass Spectrometry Impact Report",
        report_note="This report covers mass spectrometry services only (excludes Amino Acid Analysis).",
    )
    ms_path = REPORT_DIR / f"impact_report_ms_only_{today_str}.md"
    ms_path.write_text(ms_report)
    print(f"  MS-only Markdown: {ms_path}")
    ms_latest = REPORT_DIR / "impact_report_ms_only_latest.md"
    ms_latest.write_text(ms_report)
    print(f"  MS-only Latest: {ms_latest}")

    # --- AAA Only report ---
    aaa_order_stats = filter_orders_by_service(order_stats, "aaa")
    aaa_report = generate_comprehensive_report(
        nih_stats, nsf_stats, pubmed_data, sub_stats, cross_refs, nih_pubs_data,
        pi_grants_data, aaa_order_stats,
        report_title="UC Davis Proteomics Core Facility — Amino Acid Analysis Impact Report",
        report_note="This report covers Amino Acid Analysis services only (excludes mass spectrometry).",
    )
    aaa_path = REPORT_DIR / f"impact_report_aaa_only_{today_str}.md"
    aaa_path.write_text(aaa_report)
    print(f"  AAA-only Markdown: {aaa_path}")
    aaa_latest = REPORT_DIR / "impact_report_aaa_only_latest.md"
    aaa_latest.write_text(aaa_report)
    print(f"  AAA-only Latest: {aaa_latest}")

    # CSV exports
    if nih_stats:
        csv_path = REPORT_DIR / f"nih_grants_{today_str}.csv"
        with open(csv_path, "w", newline="") as f:
            if nih_stats["all_grants"]:
                writer = csv.DictWriter(f, fieldnames=nih_stats["all_grants"][0].keys())
                writer.writeheader()
                writer.writerows(nih_stats["all_grants"])
        print(f"  NIH CSV: {csv_path}")

    if nsf_stats and nsf_stats["all_awards"]:
        csv_path = REPORT_DIR / f"nsf_awards_{today_str}.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=nsf_stats["all_awards"][0].keys())
            writer.writeheader()
            writer.writerows(nsf_stats["all_awards"])
        print(f"  NSF CSV: {csv_path}")

    if pubmed_data and pubmed_data["publications"]:
        csv_path = REPORT_DIR / f"publications_{today_str}.csv"
        with open(csv_path, "w", newline="") as f:
            fields = ["pmid", "title", "year", "journal", "authors", "grants"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for pub in pubmed_data["publications"]:
                writer.writerow({
                    "pmid": pub["pmid"],
                    "title": pub["title"],
                    "year": pub["year"],
                    "journal": pub["journal"],
                    "authors": "; ".join(pub["authors"][:5]),
                    "grants": "; ".join(g["grant_id"] for g in pub["grants"]),
                })
        print(f"  Publications CSV: {csv_path}")

    # PI Grant Discovery CSV (backing data for the "$X billion" claim)
    if pi_grants_data and pi_grants_data["pi_details"]:
        csv_path = REPORT_DIR / f"core_user_grants_{today_str}.csv"
        with open(csv_path, "w", newline="") as f:
            fields = ["pi_name", "submissions", "institute",
                       "nih_grant_count", "nih_total_funding",
                       "nsf_award_count", "nsf_total_funding",
                       "nih_grant_numbers", "nsf_award_ids"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for pi in pi_grants_data["pi_details"]:
                writer.writerow({
                    "pi_name": pi["name"],
                    "submissions": pi["submissions"],
                    "institute": pi["institute"],
                    "nih_grant_count": len(pi["nih_grants"]),
                    "nih_total_funding": sum(g["amount"] for g in pi["nih_grants"]),
                    "nsf_award_count": len(pi["nsf_awards"]),
                    "nsf_total_funding": sum(a["amount"] for a in pi["nsf_awards"]),
                    "nih_grant_numbers": "; ".join(g["grant"] for g in pi["nih_grants"]),
                    "nsf_award_ids": "; ".join(a["award_id"] for a in pi["nsf_awards"]),
                })
        print(f"  Core User Grants CSV: {csv_path}")

    # JSON data (for website)
    json_data = {
        "generated": today_str,
        "nih": {
            "total_grants": nih_stats["total_grants"] if nih_stats else 0,
            "total_funding": nih_stats["total_funding"] if nih_stats else 0,
            "unique_pis": nih_stats["unique_pis"] if nih_stats else 0,
            "institutes_count": len(nih_stats["institutes"]) if nih_stats else 0,
            "active_grants_count": len(nih_stats["active_grants"]) if nih_stats else 0,
            "active_funding": sum(g["award_amount"] for g in nih_stats["active_grants"]) if nih_stats else 0,
        },
        "nsf": {
            "total_awards": nsf_stats["total_awards"] if nsf_stats else 0,
            "total_funding": nsf_stats["total_funding"] if nsf_stats else 0,
        },
        "publications": {
            "total": pubmed_data["count"] if pubmed_data else 0,
            "grants_extracted": len(pubmed_data["grants_from_pubs"]) if pubmed_data else 0,
        },
        "instrument_grant_publications": {
            "total": nih_pubs_data["total_publications"] if nih_pubs_data else 0,
            "total_citations": nih_pubs_data["total_citations"] if nih_pubs_data else 0,
        },
        "revenue": {
            "total": order_stats["total_revenue"] if order_stats else 0,
            "ms_revenue": order_stats["ms_revenue"] if order_stats else 0,
            "aaa_revenue": order_stats["aaa_revenue"] if order_stats else 0,
            "total_orders": order_stats["total_orders"] if order_stats else 0,
        },
        "core_user_grants": {
            "pis_with_nih": pi_grants_data["pis_with_nih"] if pi_grants_data else 0,
            "pis_with_nsf": pi_grants_data["pis_with_nsf"] if pi_grants_data else 0,
            "total_nih_grants": pi_grants_data["total_active_nih_grants"] if pi_grants_data else 0,
            "total_nih_funding": pi_grants_data["total_active_nih_funding"] if pi_grants_data else 0,
            "total_nsf_awards": pi_grants_data["total_nsf_awards"] if pi_grants_data else 0,
            "total_nsf_funding": pi_grants_data["total_nsf_funding"] if pi_grants_data else 0,
            "ucd_pis": pi_grants_data.get("ucd_pis", 0) if pi_grants_data else 0,
            "ucd_funding": pi_grants_data.get("ucd_funding", 0) if pi_grants_data else 0,
            "ext_pis": pi_grants_data.get("ext_pis", 0) if pi_grants_data else 0,
            "ext_funding": pi_grants_data.get("ext_funding", 0) if pi_grants_data else 0,
        },
        "submissions": {
            "total": sub_stats["total_submissions"] if sub_stats else 0,
            "total_samples": sub_stats["total_samples"] if sub_stats else 0,
            "unique_pis": sub_stats["unique_pis_count"] if sub_stats else 0,
            "unique_institutions": sub_stats["unique_institutes_count"] if sub_stats else 0,
            "repeat_pi_rate": round(sub_stats["repeat_pi_rate"], 1) if sub_stats else 0,
        },
    }
    json_path = REPORT_DIR / "impact_data.json"
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"  JSON: {json_path}")

    # Executive Summary PDF
    print("\nGenerating PDFs...")
    generate_executive_summary_pdf(
        nih_stats, nsf_stats, nih_pubs_data, sub_stats, order_stats,
        pi_grants_data
    )
    generate_data_index_pdf()

    # --- Print Summary ---
    print("\n" + "=" * 70)
    print("COMPREHENSIVE IMPACT SUMMARY")
    print("=" * 70)
    if nih_stats:
        print(f"  NIH:  {nih_stats['total_grants']} grants, "
              f"${nih_stats['total_funding']:,.0f} funding, "
              f"{len(nih_stats['active_grants'])} active")
    if nsf_stats:
        print(f"  NSF:  {nsf_stats['total_awards']} awards, "
              f"${nsf_stats['total_funding']:,.0f} funding")
    if pubmed_data:
        print(f"  Pubs: {pubmed_data['count']} publications, "
              f"{len(pubmed_data['grants_from_pubs'])} grant numbers extracted")
    if sub_stats:
        print(f"  Usage: {sub_stats['total_submissions']} submissions, "
              f"{sub_stats['total_samples']:,} samples, "
              f"{sub_stats['unique_pis_count']} PIs, "
              f"{sub_stats['unique_institutes_count']} institutions")
    if nih_pubs_data:
        print(f"  Instrument grant pubs: {nih_pubs_data['total_publications']} publications, "
              f"{nih_pubs_data['total_citations']:,} total citations")
    if order_stats:
        print(f"  Revenue: ${order_stats['total_revenue']:,.0f} total "
              f"(MS: ${order_stats['ms_revenue']:,.0f}, "
              f"AAA: ${order_stats['aaa_revenue']:,.0f})")
    if pi_grants_data:
        total_pi_funding = (pi_grants_data['total_active_nih_funding'] +
                            pi_grants_data['total_nsf_funding'])
        print(f"  PI Grants: {pi_grants_data['pis_with_nih']} PIs with NIH, "
              f"{pi_grants_data['pis_with_nsf']} with NSF, "
              f"${total_pi_funding:,.0f} total active funding held by core users")
    if cross_refs:
        print(f"  Cross-refs: {len(cross_refs)} PIs matched between submissions and grants")
    print()


if __name__ == "__main__":
    main()
