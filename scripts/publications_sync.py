#!/usr/bin/env python3
"""
Publication list sync: ORCID (canonical) -> LinkedIn paste-ready diff.

ORCID is the source of truth for "which papers are mine". PubMed is used as a
gap check, because ORCID's Web of Science / Scopus feeds lag by months on very
recent papers. Crossref supplies clean metadata (ORCID stores journal names in
ALL CAPS from the WoS feed and carries no author lists).

LinkedIn has no write API for profile sections, so the final step is manual:
this emits entries pre-formatted for LinkedIn's "Add publication" form fields.

Inputs:
  private_data/linkedin_publications.txt  — baseline: what's already on LinkedIn.
                                            Free text; DOIs and/or titles, one per
                                            line. Missing file => everything is "new".

Outputs:
  reports/linkedin_publications_to_add.md — paste-ready entries not yet on LinkedIn
  reports/orcid_gaps.md                   — in PubMed but missing from ORCID
  reports/orcid_misattributions.md        — records that appear to be a different Phinney
  reports/publications.json               — clean feed for the website page
  pages/publications.html                 — offline fallback snapshot re-injected
  reports/audit/raw/publications_master.json — merged list with full metadata
  reports/audit/raw/crossref_cache.json   — per-DOI metadata cache
"""
import argparse
import datetime
import difflib
import html
import json
import re
import sys
import time
from pathlib import Path
import requests

BASE = Path(__file__).parent.parent
REPORTS = BASE / "reports"
RAW = REPORTS / "audit" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
PRIVATE = BASE / "private_data"

ORCID_ID = "0000-0003-3870-3302"          # Brett S. Phinney
PUBMED_AUTHOR = "Phinney BS[Author]"

ORCID_PUB = "https://pub.orcid.org/v3.0"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CROSSREF = "https://api.crossref.org/works"
UA = "ucdavis-proteomics-pubsync/1.0 (mailto:bsphinney@ucdavis.edu)"
EUTILS_PARAMS = {"tool": "ucdavis_proteomics_pubsync", "email": "bsphinney@ucdavis.edu"}

CACHE_PATH = RAW / "crossref_cache.json"


def norm_doi(d):
    if not d:
        return ""
    d = d.strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/)", "", d)
    # eLife and others mint versioned DOIs (…100928, …100928.1, …100928.3) for the
    # same paper. Collapse to the base DOI so versions dedupe against each other.
    d = re.sub(r"^(10\.7554/elife\.\d+)\.\d+$", r"\1", d)
    # ACS mints separate DOIs for Supporting Information files; they resolve to a
    # supplementary PDF, not the article.
    d = re.sub(r"^(10\.1021/[^/]+?)\.s\d{3}$", r"\1", d)
    # Research Square / F1000 style versioned DOIs.
    d = re.sub(r"^(10\.21203/rs\.\d+\.rs-\d+)/v\d+$", r"\1", d)
    return d


# Venues that are data repositories, not journals. ORCID's Scopus/WoS feeds file
# ProteomeXchange/PRIDE/Figshare/ArrayExpress deposits as "works".
DATA_REPOS = {"pride", "figshare", "arrayexpress archive", "proteomexchange",
              "zenodo", "dryad", "massive"}
PREPRINT_VENUES = {"biorxiv", "medrxiv", "research square", "arxiv", "chemrxiv",
                   "ssrn", "preprints.org", "authorea"}
ERRATUM_RE = re.compile(
    r"^\s*(correction|corrigend|erratum|errata|retraction|withdrawn|"
    r"the last sentence in the legend|author correction|publisher correction)",
    re.I)
DEPOSIT_TITLE_RE = re.compile(
    r"(\.(raw|zip|txt|sdrf|adf|idf|mzml|mzid)(\.\d+)?$)|^[AE]-[A-Z]{3,}-\d+|"
    r"^MOESM\d+ of |^ProteomeXchange dataset", re.I)


ABSTRACT_VENUES = {
    "investigative ophthalmology & visual science",
    "investigative opthalmology & visual science",
    "molecular biology of the cell",
    "annals of neurology",
    "hepatology",
    "faseb journal",
    "the faseb journal",
    "cell death discovery",
    "cancer research",
    "alzheimer's & dementia",
}


def looks_like_meeting_abstract(w):
    """WoS meeting-abstract signature: society journal, no DOI, no author list.

    ARVO, ASCB, AASLD and ANA abstracts are deposited by Web of Science as
    journal records. They carry no DOI and no contributors, and the journal name
    arrives in the feed's ALL-CAPS form. Abstracts are not peer-reviewed papers.
    """
    if w.get("doi") or w.get("authors"):
        return False
    journal = (w.get("journal") or "").strip().lower()
    if journal in ABSTRACT_VENUES:
        return True
    # Title beginning "Abstract A14: ..." is unambiguous whatever the venue.
    return bool(re.match(r"^abstract\s+[A-Za-z]*\d", w.get("title") or "", re.I))


def classify(w):
    """Bucket a record: article | preprint | dataset | erratum | conference.

    Only 'article' counts as a peer-reviewed publication. The others are real
    outputs but must not be silently folded into a headline publication count.
    """
    journal = (w.get("journal") or "").strip().lower()
    title = w.get("title") or ""
    wtype = (w.get("type") or "").lower()

    if journal in DATA_REPOS or DEPOSIT_TITLE_RE.search(title):
        return "dataset"
    if ERRATUM_RE.match(title):
        return "erratum"
    if journal in PREPRINT_VENUES or wtype == "posted-content":
        return "preprint"
    if looks_like_meeting_abstract(w):
        return "abstract"
    if wtype in ("conference-paper", "proceedings-article") or "conference on mass spectrometry" in journal:
        return "conference"
    return "article"


def clean_text(t):
    """Crossref returns JATS markup and HTML entities in titles/journal names."""
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


GREEK = {
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta",
    "\u03b5": "epsilon", "\u03b6": "zeta", "\u03b7": "eta", "\u03b8": "theta",
    "\u03ba": "kappa", "\u03bb": "lambda", "\u03bc": "mu", "\u00b5": "mu",
    "\u03bd": "nu", "\u03c0": "pi", "\u03c1": "rho", "\u03c3": "sigma",
    "\u03c4": "tau", "\u03c6": "phi", "\u03c7": "chi", "\u03c8": "psi",
    "\u03c9": "omega",
}


def norm_title(t):
    """Aggressive title normalization for matching across sources.

    Publishers disagree on Greek letters: Crossref returns "\u03b1-Ketoglutarate"
    where PubMed and LinkedIn both write "alpha-ketoglutarate". Stripping the
    Greek character instead of transliterating it silently breaks the match.
    """
    t = clean_text(t).lower()
    for ch, word in GREEK.items():
        t = t.replace(ch, word)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# -------------------- ORCID --------------------

def fetch_orcid(orcid_id):
    """Return {doi: {...}} plus entries with no DOI, from the ORCID works summary."""
    print(f"[orcid] fetching works for {orcid_id}", flush=True)
    r = requests.get(f"{ORCID_PUB}/{orcid_id}/works",
                     headers={"Accept": "application/json", "User-Agent": UA}, timeout=30)
    r.raise_for_status()
    out = []
    for group in r.json().get("group", []):
        summary = group["work-summary"][0]
        doi = ""
        for eid in (group.get("external-ids") or {}).get("external-id", []):
            if eid.get("external-id-type") == "doi":
                doi = norm_doi(eid.get("external-id-value"))
                break
        pub_date = summary.get("publication-date") or {}
        year = (pub_date.get("year") or {}).get("value", "") if pub_date else ""
        out.append({
            "doi": doi,
            "title": clean_text(summary["title"]["title"]["value"]),
            "year": year,
            "journal": clean_text((summary.get("journal-title") or {}).get("value", "")),
            "type": summary.get("type", ""),
            "sources": sorted({
                ws["source"]["source-name"]["value"]
                for ws in group["work-summary"]
                if ws.get("source", {}).get("source-name")
            }),
            "in_orcid": True,
        })
    print(f"[orcid] {len(out)} works ({sum(1 for w in out if w['doi'])} with DOIs)", flush=True)
    return out


# -------------------- PubMed gap check --------------------

def fetch_pubmed(author_term):
    print(f"[pubmed] searching {author_term}", flush=True)
    r = requests.get(f"{EUTILS}/esearch.fcgi",
                     params={**EUTILS_PARAMS, "db": "pubmed", "term": author_term,
                             "retmax": 1000, "retmode": "json"}, timeout=30)
    r.raise_for_status()
    ids = r.json()["esearchresult"]["idlist"]
    if not ids:
        return []
    out = []
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        r = requests.get(f"{EUTILS}/esummary.fcgi",
                         params={**EUTILS_PARAMS, "db": "pubmed",
                                 "id": ",".join(chunk), "retmode": "json"}, timeout=60)
        r.raise_for_status()
        result = r.json().get("result", {})
        for pmid in result.get("uids", []):
            a = result[pmid]
            doi = ""
            for aid in a.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = norm_doi(aid.get("value"))
            out.append({
                "doi": doi,
                "pmid": pmid,
                "title": clean_text(a.get("title", "")).rstrip("."),
                "year": (a.get("pubdate") or "")[:4],
                "journal": a.get("source", ""),
                "type": "journal-article",
                "sources": ["PubMed"],
                "in_orcid": False,
            })
        time.sleep(0.4)
    print(f"[pubmed] {len(out)} records", flush=True)
    return out


# -------------------- Crossref enrichment --------------------

def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def enrich_crossref(works, cache, limit=None):
    """Fill in clean journal name, full author list, and date from Crossref."""
    todo = [w for w in works if w["doi"] and w["doi"] not in cache]
    if limit:
        todo = todo[:limit]
    print(f"[crossref] {len(todo)} DOIs to fetch ({len(cache)} cached)", flush=True)
    for n, w in enumerate(todo, 1):
        try:
            r = requests.get(f"{CROSSREF}/{w['doi']}",
                             headers={"User-Agent": UA}, timeout=30)
            if r.status_code != 200:
                cache[w["doi"]] = {"error": r.status_code}
            else:
                m = r.json()["message"]
                parts = ((m.get("published") or {}).get("date-parts") or [[]])[0]
                cache[w["doi"]] = {
                    "title": clean_text((m.get("title") or [""])[0]),
                    "journal": clean_text((m.get("container-title") or [""])[0]),
                    "year": str(parts[0]) if parts else "",
                    "month": str(parts[1]) if len(parts) > 1 else "",
                    "authors": [
                        " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
                        for a in (m.get("author") or [])
                    ],
                    "url": m.get("URL", ""),
                    "type": m.get("type", ""),
                    "institution": [
                        i.get("name", "") for i in (m.get("institution") or [])
                        if i.get("name")
                    ],
                    "has_preprint": [
                        i.get("id", "").lower()
                        for i in (m.get("relation") or {}).get("has-preprint", [])
                        if i.get("id")
                    ],
                }
        except requests.RequestException as e:
            cache[w["doi"]] = {"error": str(e)}
        if n % 25 == 0:
            print(f"[crossref]   {n}/{len(todo)}", flush=True)
            CACHE_PATH.write_text(json.dumps(cache, indent=1))
        time.sleep(0.15)
    CACHE_PATH.write_text(json.dumps(cache, indent=1))

    for w in works:
        c = cache.get(w["doi"]) or {}
        if c and "error" not in c:
            w["title"] = c.get("title") or w["title"]
            # ORCID's feed can attach a journal name to a preprint record (one
            # medRxiv deposit arrives labelled "PLOS ONE"). Crossref knows it is
            # posted-content and names the actual server, so that wins.
            if c.get("type") == "posted-content" and c.get("institution"):
                w["journal"] = c["institution"][0]
            else:
                w["journal"] = c.get("journal") or w["journal"]
            w["year"] = c.get("year") or w["year"]
            w["month"] = c.get("month", "")
            w["authors"] = c.get("authors", [])
            w["url"] = c.get("url", "")
            w["type"] = c.get("type") or w["type"]
            w["has_preprint"] = c.get("has_preprint", [])
        else:
            w.setdefault("authors", [])
            w.setdefault("url", f"https://doi.org/{w['doi']}" if w["doi"] else "")
            w.setdefault("month", "")
    return works


# -------------------- Merge + diff --------------------

def merge(orcid_works, pubmed_works):
    """Union by DOI, falling back to normalized title. Records ORCID gaps."""
    by_doi, by_title, master = {}, {}, []

    def add(w):
        master.append(w)
        if w["doi"]:
            by_doi[w["doi"]] = w
        by_title[norm_title(w["title"])] = w

    for w in orcid_works:
        add(w)

    gaps = []
    for w in pubmed_works:
        existing = by_doi.get(w["doi"]) if w["doi"] else None
        if existing is None:
            existing = by_title.get(norm_title(w["title"]))
        if existing is not None:
            existing["pmid"] = w.get("pmid", existing.get("pmid", ""))
            continue
        gaps.append(w)
        add(w)
    return master, gaps


def load_baseline():
    """Parse the LinkedIn baseline into DOI and title match sets."""
    path = PRIVATE / "linkedin_publications.txt"
    if not path.exists():
        return None, set(), set()
    text = path.read_text()
    dois = {norm_doi(d) for d in re.findall(r"10\.\d{4,9}/[^\s\"'<>,;)\]]+", text)}
    titles = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        line = re.sub(r"10\.\d{4,9}/[^\s\"'<>,;)\]]+", "", line).strip(" -–—•\t")
        if len(line) > 25:
            titles.add(norm_title(line))
    return path, dois, titles


def already_on_linkedin(w, dois, titles):
    if w["doi"] and w["doi"] in dois:
        return True
    nt = norm_title(w["title"])
    if nt in titles:
        return True
    # Substring match catches LinkedIn's truncated / reformatted titles
    if len(nt) <= 25:
        return False   # too short to substring-match safely in either direction
    return any(nt in t or t in nt for t in titles if len(t) > 25)


# -------------------- Output --------------------

def author_line(w, highlight="Phinney"):
    au = w.get("authors") or []
    if not au:
        return ""
    marked = [f"**{a}**" if highlight.lower() in a.lower() else a for a in au]
    if len(marked) > 12:
        marked = marked[:10] + [f"... (+{len(au) - 10} more)"]
    return ", ".join(marked)


def write_linkedin_report(to_add, baseline_path, total):
    lines = [
        "# Publications to add to LinkedIn",
        "",
        f"**{len(to_add)} of {total}** peer-reviewed publications are not yet on "
        f"your LinkedIn profile.",
        "",
        "Data deposits, errata, and duplicate preprint/published pairs are already "
        "filtered out. Preprints are excluded too — pass `--include-preprints` to add them.",
        "",
    ]
    if baseline_path is None:
        lines += [
            "> ⚠️  No baseline found at `private_data/linkedin_publications.txt`, so every",
            "> publication is listed as new. Paste your current LinkedIn publications into",
            "> that file and re-run to get a real diff.",
            "",
        ]
    lines += [
        "Add each at "
        "<https://www.linkedin.com/in/brett-phinney-4776257/details/publications/> → **+**",
        "The headings below map 1:1 onto LinkedIn's form fields.",
        "",
        "---",
        "",
    ]
    for i, w in enumerate(to_add, 1):
        date = f"{w.get('year','')}"
        if w.get("month"):
            date += f"-{int(w['month']):02d}"
        url = w.get("url") or (f"https://doi.org/{w['doi']}" if w.get("doi") else "—")
        lines += [
            f"## {i}. {w['title']}",
            "",
            f"- **Publication/Publisher:** {w.get('journal') or '—'}",
            f"- **Publication date:** {date or '—'}",
            f"- **Publication URL:** {url}",
        ]
        au = author_line(w)
        if au:
            lines.append(f"- **Authors:** {au}")
        if w.get("pmid"):
            lines.append(f"- PMID: {w['pmid']}")
        lines += ["", "---", ""]
    (REPORTS / "linkedin_publications_to_add.md").write_text("\n".join(lines))


ME_RE = re.compile(r"\bbrett\b|\bb\.?\s*s\.?\s*phinney\b|\bbretts\.?\s*phinney\b", re.I)


def find_misattributions(pubs):
    """Records whose author list names a Phinney who is not Brett.

    ORCID's Scopus and Web of Science feeds match on surname and initial, so
    other Phinneys (Brandon B., Brigitte, Bernard O.) drift into the record.
    Only flag when a Phinney is present but is clearly someone else — a record
    with no Phinney at all is usually just incomplete Crossref metadata.
    """
    flagged = []
    for pub in pubs:
        phinneys = [a for a in (pub.get("authors") or []) if "phinney" in a.lower()]
        if not phinneys:
            continue
        if any(ME_RE.search(a) for a in phinneys):
            continue
        flagged.append({**pub, "wrong_author": "; ".join(phinneys)})
    return flagged


def write_misattribution_report(flagged):
    lines = [
        "# Suspected misattributions in the ORCID record",
        "",
        f"**{len(flagged)}** record(s) name a Phinney who does not appear to be Brett.",
        "",
        "ORCID's Scopus and Web of Science feeds match on surname plus initial, so",
        "papers by other Phinneys drift in. Remove these at <https://orcid.org/my-orcid>",
        "-> Works -> select -> Delete. Verify each one first; this is a heuristic.",
        "",
        "| Year | Author found | Title | Journal | DOI |",
        "|------|--------------|-------|---------|-----|",
    ]
    for w in sorted(flagged, key=lambda x: str(x.get("year", "")), reverse=True):
        lines.append(
            f"| {w.get('year','')} | {w['wrong_author']} | "
            f"{w['title'].replace('|', chr(92) + '|')} | {w.get('journal','')} | "
            f"{w.get('doi') or '—'} |")
    lines.append("")
    (REPORTS / "orcid_misattributions.md").write_text("\n".join(lines))


def write_abstracts_report(abstracts):
    lines = [
        "# Records excluded as meeting abstracts",
        "",
        f"**{len(abstracts)}** record(s) match the Web of Science meeting-abstract",
        "signature: a society journal, no DOI, and no author list. ARVO, ASCB,",
        "AASLD and ANA abstracts arrive this way. They are excluded from the",
        "peer-reviewed count.",
        "",
        "**This is a heuristic — please confirm.** If any of these is a real paper,",
        "add its DOI to the ORCID record and it will be reclassified automatically.",
        "",
        "| Year | Title | Journal |",
        "|------|-------|---------|",
    ]
    for w in sorted(abstracts, key=lambda x: str(x.get("year", "")), reverse=True):
        lines.append(f"| {w.get('year','')} | "
                     f"{w['title'].replace('|', chr(92) + '|')} | {w.get('journal','')} |")
    (REPORTS / "excluded_abstracts.md").write_text("\n".join(lines) + "\n")


def write_gaps_report(gaps):
    lines = [
        "# In PubMed but missing from ORCID",
        "",
        f"**{len(gaps)}** publications indexed in PubMed are not in ORCID record "
        f"`{ORCID_ID}`.",
        "",
        "Most gaps are sync lag — ORCID's Web of Science and Scopus feeds trail",
        "PubMed by months on new papers. Add these at",
        "<https://orcid.org/my-orcid> → Works → **+ Add** → *Search & link* (Crossref",
        "Metadata Search), or paste the DOI directly.",
        "",
        "| Year | Title | Journal | DOI | PMID |",
        "|------|-------|---------|-----|------|",
    ]
    for w in sorted(gaps, key=lambda x: str(x.get("year", "")), reverse=True):
        title = w["title"].replace("|", "\\|")
        lines.append(
            f"| {w.get('year','')} | {title} | {w.get('journal','')} | "
            f"{w.get('doi') or '—'} | {w.get('pmid','')} |"
        )
    lines.append("")
    (REPORTS / "orcid_gaps.md").write_text("\n".join(lines))


def collapse_versions(pubs):
    """Merge records that describe the same paper.

    Two things create duplicates: (a) a preprint and its published version carry
    different DOIs, and (b) ORCID's WoS feed contributes a bare ALL-CAPS record
    alongside the properly-cited Scopus one. Both collapse on normalized title;
    the richer record wins (published > preprint, has-DOI > none, more authors).
    """
    def rank(p):
        return (
            0 if p["kind"] == "preprint" else 1,   # published beats preprint
            1 if p["doi"] else 0,
            len(p.get("authors") or []),
            len(p.get("journal") or ""),
        )

    # Crossref sometimes declares the link explicitly. Where it does, it beats
    # any title heuristic — retitled preprints are otherwise undetectable.
    declared = set()
    for pub in pubs:
        for pre in pub.get("has_preprint") or []:
            declared.add(norm_doi(pre))
    if declared:
        pubs = [p for p in pubs
                if not (p["kind"] == "preprint" and p["doi"] in declared)]

    # Bare Web-of-Science stubs (no DOI, no authors) duplicate a properly-cited
    # record under a variant title. Prefix keys cannot catch these: the 2016
    # Plant Physiology pair diverges at character 76, so any key long enough to
    # avoid false merges elsewhere is also long enough to split this pair.
    # Fuzzy-match the stubs against the DOI-bearing records instead.
    solid = [p for p in pubs if p["doi"] and p.get("authors")]
    stubs = [p for p in pubs if not p["doi"] and not p.get("authors")]
    absorbed = set()
    for stub in stubs:
        st = norm_title(stub["title"])
        best, best_ratio = None, 0.0
        for cand in solid:
            if str(cand["year"]) != str(stub["year"]):
                continue
            ratio = difflib.SequenceMatcher(None, st, norm_title(cand["title"])).ratio()
            if ratio > best_ratio:
                best, best_ratio = cand, ratio
        if best is not None and best_ratio >= 0.80:
            absorbed.add(id(stub))
    if absorbed:
        pubs = [p for p in pubs if id(p) not in absorbed]

    groups = {}
    for pub in pubs:
        key = norm_title(pub["title"])[:80]
        groups.setdefault(key, []).append(pub)

    merged, collapsed = [], len(absorbed) + len(declared)
    for key, items in groups.items():
        if len(items) == 1:
            merged.append(items[0])
            continue
        items.sort(key=rank, reverse=True)
        winner = items[0]
        # Keep a pointer to the preprint if the published version won.
        for other in items[1:]:
            if other["kind"] == "preprint" and other["doi"]:
                winner["preprint_doi"] = other["doi"]
        collapsed += len(items) - 1
        merged.append(winner)
    return merged, collapsed


def write_web_feed(master, orcid_id):
    """Clean public feed consumed by pages/publications.html over raw.githubusercontent."""
    pubs = []
    for w in master:
        if not w.get("title"):
            continue
        rec = {
            "title": w["title"],
            "journal": w.get("journal", ""),
            "year": w.get("year", ""),
            "month": w.get("month", ""),
            "doi": w.get("doi", ""),
            "url": w.get("url") or (f"https://doi.org/{w['doi']}" if w.get("doi") else ""),
            "authors": w.get("authors", []),
            "pmid": w.get("pmid", ""),
            "type": w.get("type", ""),
            "has_preprint": w.get("has_preprint", []),
        }
        rec["kind"] = classify(rec)
        pubs.append(rec)

    pubs, collapsed = collapse_versions(pubs)
    pubs.sort(key=lambda x: (str(x["year"]), str(x["month"]).zfill(2), x["title"]),
              reverse=True)

    counts = {}
    for pub in pubs:
        counts[pub["kind"]] = counts.get(pub["kind"], 0) + 1

    # Datasets and errata are real outputs but are not publications; they are
    # excluded from the feed entirely rather than shown and caveated.
    flagged = find_misattributions(pubs)
    write_misattribution_report(flagged)
    flagged_dois = {f["doi"] for f in flagged if f["doi"]}

    abstracts = [p for p in pubs if p["kind"] == "abstract"]
    write_abstracts_report(abstracts)

    listed = [p for p in pubs
              if p["kind"] in ("article", "preprint", "conference")
              and not (p["doi"] and p["doi"] in flagged_dois)]

    articles = [p for p in listed if p["kind"] == "article"]
    years = sorted({int(p["year"]) for p in articles
                    if str(p.get("year", "")).isdigit()})

    payload = {
        "generated": datetime.date.today().isoformat(),
        "orcid": orcid_id,
        "orcid_url": f"https://orcid.org/{orcid_id}",
        "count": len(listed),
        "counts": {
            "peer_reviewed": len(articles),
            "preprints": counts.get("preprint", 0),
            "conference": counts.get("conference", 0),
            "excluded_datasets": counts.get("dataset", 0),
            "excluded_errata": counts.get("erratum", 0),
            "excluded_abstracts": counts.get("abstract", 0),
            "duplicates_collapsed": collapsed,
            "excluded_misattributed": len(flagged),
        },
        "first_year": years[0] if years else "",
        "last_year": years[-1] if years else "",
        "active_years": len(years),
        "publications": listed,
    }
    (REPORTS / "publications.json").write_text(json.dumps(payload, indent=1))

    c = payload["counts"]
    print(f"[feed] {c['peer_reviewed']} peer-reviewed articles, "
          f"{c['preprints']} preprints, {c['conference']} conference")
    print(f"[feed] excluded {c['excluded_datasets']} data deposits, "
          f"{c['excluded_errata']} errata, {c['excluded_abstracts']} meeting abstracts, "
          f"{c['excluded_misattributed']} misattributed; "
          f"collapsed {c['duplicates_collapsed']} duplicates")
    return payload


FALLBACK_RE = re.compile(
    r'(<script type="application/json" id="pcf-pubs-fallback">)(.*?)(</script>)',
    re.DOTALL)


def inject_page_fallback(payload):
    """Refresh the embedded no-fetch snapshot in pages/publications.html."""
    page = BASE / "pages" / "publications.html"
    if not page.exists():
        print("[page] pages/publications.html not found — skipping fallback injection")
        return
    trimmed = [[p["title"], p["journal"], p["year"], p["doi"], p["kind"]]
               for p in payload["publications"]]
    blob = json.dumps(trimmed, separators=(",", ":"))
    text = page.read_text()
    new_text, n = FALLBACK_RE.subn(
        lambda m: m.group(1) + blob + m.group(3), text)
    if not n:
        print("[page] fallback <script> block not found — skipping injection")
        return
    page.write_text(new_text)
    print(f"[page] injected {len(trimmed)} publications "
          f"({len(blob)//1024} KB) into pages/publications.html")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orcid", default=ORCID_ID)
    ap.add_argument("--skip-pubmed", action="store_true",
                    help="skip the PubMed gap check")
    ap.add_argument("--skip-crossref", action="store_true",
                    help="use cached Crossref metadata only")
    ap.add_argument("--include-preprints", action="store_true",
                    help="include preprints in the LinkedIn to-add list")
    ap.add_argument("--since", type=int, default=0,
                    help="only report publications from this year onward")
    args = ap.parse_args()

    orcid_works = fetch_orcid(args.orcid)
    pubmed_works = [] if args.skip_pubmed else fetch_pubmed(PUBMED_AUTHOR)
    master, gaps = merge(orcid_works, pubmed_works)

    cache = load_cache()
    master = enrich_crossref(master, cache, limit=0 if args.skip_crossref else None)

    (RAW / "publications_master.json").write_text(json.dumps(master, indent=1))
    feed = write_web_feed(master, args.orcid)
    inject_page_fallback(feed)

    baseline_path, base_dois, base_titles = load_baseline()
    # Diff against the cleaned feed, not the raw master: no point telling Brett to
    # add ArrayExpress deposits, errata, or both halves of a preprint/published pair.
    candidates = [w for w in feed["publications"] if w["kind"] != "preprint"] \
        if not args.include_preprints else feed["publications"]
    to_add = [w for w in candidates
              if not already_on_linkedin(w, base_dois, base_titles)]
    if args.since:
        to_add = [w for w in to_add if str(w.get("year", "0")).isdigit()
                  and int(w["year"]) >= args.since]
    to_add.sort(key=lambda w: (str(w.get("year", "")), w["title"]), reverse=True)

    write_linkedin_report(to_add, baseline_path, len(candidates))
    write_gaps_report(gaps)

    print()
    print(f"[done] {len(master)} total publications "
          f"({len(orcid_works)} ORCID + {len(gaps)} PubMed-only)")
    print(f"[done] {len(to_add)} of {len(candidates)} not yet on LinkedIn "
          f"-> reports/linkedin_publications_to_add.md")
    print(f"[done] {len(gaps)} ORCID gaps -> reports/orcid_gaps.md")
    print(f"[done] {feed['count']} publications -> reports/publications.json (website feed)")
    print(f"[done] {feed['counts']['excluded_misattributed']} suspected misattributions "
          f"-> reports/orcid_misattributions.md")
    if baseline_path is None:
        print("[warn] no private_data/linkedin_publications.txt — "
              "paste your LinkedIn list there for a real diff")


if __name__ == "__main__":
    main()
