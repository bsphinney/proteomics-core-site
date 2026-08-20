#!/usr/bin/env python3
"""
Consolidate the core-acknowledgment paper sets into one canonical web feed.

Three audit files disagreed on how many papers acknowledge the facility, which
is exactly the discrepancy a grant reviewer or competitor would find first:

  core_acknowledgments_pmc.csv    394 rows — PMC full-text search (open access only)
  core_acknowledgment_papers.csv   80 rows — PubMed-indexed set, UCD affiliation checked
  core_ack_papers_unverified.csv   14 rows — explicitly rejected during audit

This script unions the first two, subtracts the rejects, and tiers each paper by
how it was matched, so the public number is defensible:

  high   — an explicit facility-name variant, an S10 grant number, or the Core
           Director named in the full text. Publishable without caveat.
  review — matched ONLY by the broad ("Proteomics Core" AND "UC Davis") query.
           Both phrases appear somewhere in the full text, which is weak: the
           core could belong to another institution and "UC Davis" could be an
           author affiliation. Not counted in the headline.

Outputs:
  reports/acknowledgments.json        — canonical feed (high tier only, plus counts)
  reports/acknowledgments_review.md   — the 'review' tier, for manual triage
  pages/publications.html             — offline fallback snapshot re-injected
"""
import csv
import datetime
import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
REPORTS = BASE / "reports"
AUDIT = REPORTS / "audit"

PMC_CSV = AUDIT / "core_acknowledgments_pmc.csv"
PAPERS_CSV = AUDIT / "core_acknowledgment_papers.csv"
REJECT_CSV = AUDIT / "core_ack_papers_unverified.csv"

# The one query that is not, on its own, evidence of anything.
GENERIC_TERM = '("Proteomics Core" AND "UC Davis")'


def norm_doi(d):
    d = (d or "").strip().lower()
    return re.sub(r"^(https?://(dx\.)?doi\.org/)", "", d)


def key_of(row):
    return ("pmid", row["pmid"]) if row.get("pmid") else ("doi", norm_doi(row.get("doi")))


def load_rejects():
    if not REJECT_CSV.exists():
        return set()
    out = set()
    for r in csv.DictReader(open(REJECT_CSV)):
        if r.get("pmid"):
            out.add(("pmid", r["pmid"]))
        if r.get("doi"):
            out.add(("doi", norm_doi(r["doi"])))
    return out


def tier_from_terms(terms):
    """high unless the ONLY thing that matched was the broad generic query."""
    matched = [t.strip() for t in (terms or "").split(";") if t.strip()]
    if not matched:
        return "high"
    return "review" if matched == [GENERIC_TERM] else "high"


FALLBACK_RE = re.compile(
    r'(<script type="application/json" id="pcf-ack-fallback">)(.*?)(</script>)',
    re.DOTALL)


def inject_page_fallback(papers):
    """Refresh the embedded no-fetch snapshot in pages/publications.html."""
    page = BASE / "pages" / "publications.html"
    if not page.exists():
        print("[ack] pages/publications.html not found — skipping fallback injection")
        return
    trimmed = [[p["title"], p["journal"], p["year"], p["doi"]] for p in papers]
    blob = json.dumps(trimmed, separators=(",", ":"))
    text = page.read_text()
    new_text, n = FALLBACK_RE.subn(lambda m: m.group(1) + blob + m.group(3), text)
    if not n:
        print("[ack] fallback <script> block not found — skipping injection")
        return
    page.write_text(new_text)
    print(f"[ack] injected {len(trimmed)} papers ({len(blob)//1024} KB) "
          f"into pages/publications.html")


def main():
    rejects = load_rejects()
    merged = {}

    for r in csv.DictReader(open(PMC_CSV)):
        k = key_of(r)
        if k in rejects or k == ("doi", ""):
            continue
        merged[k] = {
            "pmid": r.get("pmid", ""),
            "doi": norm_doi(r.get("doi")),
            "year": r.get("year", ""),
            "journal": r.get("journal", ""),
            "title": (r.get("title") or "").strip().rstrip("."),
            "citations": int(r["citation_count"]) if (r.get("citation_count") or "").isdigit() else 0,
            "tier": tier_from_terms(r.get("terms_matched")),
            "matched_by": r.get("terms_matched", ""),
            "source": "pmc-fulltext",
        }

    added = 0
    for r in csv.DictReader(open(PAPERS_CSV)):
        k = key_of(r)
        if k in rejects or k == ("doi", ""):
            continue
        if k in merged:
            # Present in both sets: independent corroboration, always high.
            merged[k]["tier"] = "high"
            merged[k]["source"] = "both"
            continue
        # PubMed-indexed but not open access, so the PMC full-text search could
        # not see it. The audit checked UC Davis affiliation instead.
        merged[k] = {
            "pmid": r.get("pmid", ""),
            "doi": norm_doi(r.get("doi")),
            "year": r.get("year", ""),
            "journal": r.get("journal", ""),
            "title": (r.get("title") or "").strip().rstrip("."),
            "citations": int(r["citation_count"]) if (r.get("citation_count") or "").isdigit() else 0,
            "tier": "high" if (r.get("ucd_affiliation_detected") or "").lower() == "true" else "review",
            "matched_by": "PubMed-indexed; UC Davis affiliation verified",
            "source": "pubmed-affiliation",
        }
        added += 1

    papers = sorted(merged.values(),
                    key=lambda p: (str(p["year"]), p["title"]), reverse=True)
    high = [p for p in papers if p["tier"] == "high"]
    review = [p for p in papers if p["tier"] == "review"]

    years = sorted(int(p["year"]) for p in high if str(p["year"]).isdigit())
    journals = {p["journal"].lower() for p in high if p["journal"]}
    citations = sum(p["citations"] for p in high)
    last5 = sum(1 for y in years if y >= years[-1] - 4) if years else 0

    payload = {
        "generated": datetime.date.today().isoformat(),
        "method": ("PMC full-text search across facility-name variants, S10 instrument "
                   "grant numbers (S10OD021801, S10OD026918, S10RR023642), and the Core "
                   "Director's name; merged with the PubMed-indexed set and deduplicated. "
                   "Papers matched only by a broad two-phrase query are excluded."),
        "count": len(high),
        "counts": {
            "high_confidence": len(high),
            "needs_review": len(review),
            "rejected_in_audit": len(rejects),
            "added_from_pubmed_set": added,
        },
        "first_year": years[0] if years else "",
        "last_year": years[-1] if years else "",
        "distinct_journals": len(journals),
        "total_citations": citations,
        "last_5_years": last5,
        "papers": high,
    }
    (REPORTS / "acknowledgments.json").write_text(json.dumps(payload, indent=1))

    lines = [
        "# Acknowledgment papers needing manual review",
        "",
        f"**{len(review)}** papers matched only the broad "
        f"`{GENERIC_TERM}` query — both phrases appear somewhere in the full text, "
        "which is not on its own evidence that this facility was used.",
        "",
        "Confirm or reject each, then move confirmed rows into "
        "`core_acknowledgment_papers.csv` so they count.",
        "",
        "| Year | Title | Journal | PMID |",
        "|------|-------|---------|------|",
    ]
    for p in review:
        lines.append(f"| {p['year']} | {p['title'].replace('|', chr(92)+'|')} | "
                     f"{p['journal']} | {p['pmid']} |")
    (REPORTS / "acknowledgments_review.md").write_text("\n".join(lines) + "\n")

    print(f"[ack] {len(high)} high-confidence acknowledgment papers "
          f"({years[0] if years else '?'}–{years[-1] if years else '?'})")
    print(f"[ack] {len(review)} need review, {len(rejects)} rejected in audit, "
          f"{added} added from the PubMed-indexed set")
    print(f"[ack] {len(journals)} distinct journals, {citations:,} citations, "
          f"{last5} in the last 5 years")
    inject_page_fallback(high)
    print("[ack] -> reports/acknowledgments.json, reports/acknowledgments_review.md")


if __name__ == "__main__":
    main()
