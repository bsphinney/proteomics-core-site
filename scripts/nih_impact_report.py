#!/usr/bin/env python3
"""
UC Davis Proteomics Core Facility — NIH Impact Report Generator

Queries the NIH Reporter API to find all grants referencing the proteomics core,
cross-references personnel, and generates a summary report.

Run manually:
    python scripts/nih_impact_report.py

Or via GitHub Actions on a schedule (see .github/workflows/impact-report.yml)
"""

import json
import requests
import csv
import os
from datetime import datetime, date
from collections import defaultdict
from pathlib import Path

# --- Configuration ---

REPORT_DIR = Path(__file__).parent.parent / "reports"
API_BASE = "https://api.reporter.nih.gov/v2/projects/search"
ORGANIZATION = "UNIVERSITY OF CALIFORNIA DAVIS"

# Core facility personnel (for cross-referencing)
PERSONNEL = {
    "Phinney": "Brett S. Phinney",
    "Grigorean": "Gabriela Grigorean",
    "Salemi": "Michelle Salemi",
    "Schulze": "John Schulze",
    "Dixon": "Lauren Dixon",
}

# Search strategies to find grants referencing the core
SEARCH_STRATEGIES = [
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
        resp = requests.post(API_BASE, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.RequestException as e:
        print(f"  API error: {e}")
        return []


def extract_core_project_number(project_number):
    """Strip year/suffix to get the core project number for deduplication."""
    if not project_number:
        return None
    # Remove common prefixes like activity code modifiers
    # Core number pattern: e.g., R01CA251253 from 5R01CA251253-04
    parts = project_number.split("-")[0]
    # Strip leading digits (application type indicator)
    stripped = parts.lstrip("0123456789")
    return stripped


def run_searches():
    """Run all search strategies and deduplicate results."""
    all_projects = {}
    raw_count = 0

    for strategy in SEARCH_STRATEGIES:
        print(f"Searching: {strategy['name']}...")
        results = search_nih_reporter(strategy["criteria"])
        print(f"  Found {len(results)} results")
        raw_count += len(results)

        for project in results:
            core_num = extract_core_project_number(
                project.get("project_num", "")
            )
            if core_num and core_num not in all_projects:
                all_projects[core_num] = project
            elif core_num and core_num in all_projects:
                # Keep the one with more data (higher award amount)
                existing_award = all_projects[core_num].get("award_amount", 0) or 0
                new_award = project.get("award_amount", 0) or 0
                if new_award > existing_award:
                    all_projects[core_num] = project

    print(f"\nTotal raw results: {raw_count}")
    print(f"Unique grants (deduplicated): {len(all_projects)}")
    return all_projects


def compute_statistics(projects):
    """Compute aggregate statistics from the project data."""
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

        # PI info
        pi_name = ""
        pis = project.get("principal_investigators", [])
        if pis:
            pi = pis[0]
            pi_name = f"{pi.get('first_name', '')} {pi.get('last_name', '')}".strip()
            stats["unique_pis"].add(pi_name)

        # Institute
        ic = project.get("agency_ic_admin", {})
        ic_abbr = ic.get("abbreviation", "Unknown") if ic else "Unknown"
        ic_name = ic.get("name", "Unknown") if ic else "Unknown"
        stats["institutes"][ic_abbr]["count"] += 1
        stats["institutes"][ic_abbr]["funding"] += award
        stats["institutes"][ic_abbr]["name"] = ic_name

        # Active vs closed
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

        # Decade breakdown
        fy = project.get("fiscal_year")
        if fy:
            decade = f"{(fy // 10) * 10}s"
            stats["by_decade"][decade]["count"] += 1
            stats["by_decade"][decade]["funding"] += award

        # Phinney direct grants
        if pi_name and "Phinney" in pi_name:
            stats["phinney_grants"].append(grant_info)

    stats["unique_pis"] = len(stats["unique_pis"])
    return stats


def generate_markdown_report(stats):
    """Generate a markdown report from the statistics."""
    today = date.today().isoformat()
    lines = [
        f"# UC Davis Proteomics Core — NIH Impact Report",
        f"",
        f"*Auto-generated on {today} from NIH Reporter API*",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total NIH grants supported | **{stats['total_grants']}** |",
        f"| Total funding across all grants | **${stats['total_funding']:,.0f}** |",
        f"| Unique principal investigators | **{stats['unique_pis']}** |",
        f"| NIH institutes represented | **{len(stats['institutes'])}** |",
        f"| Currently active grants | **{len(stats['active_grants'])}** |",
        f"| Active grant funding | **${sum(g['award_amount'] for g in stats['active_grants']):,.0f}** |",
        f"",
    ]

    # Phinney direct grants
    if stats["phinney_grants"]:
        lines.extend([
            f"## Direct Instrument Grants (PI: Brett Phinney)",
            f"",
            f"| Grant | Title | Year | Amount |",
            f"|-------|-------|------|--------|",
        ])
        total_phinney = 0
        for g in sorted(stats["phinney_grants"], key=lambda x: x.get("fiscal_year", 0)):
            lines.append(
                f"| {g['core_number']} | {g['title'][:60]} | {g['fiscal_year']} | ${g['award_amount']:,.0f} |"
            )
            total_phinney += g["award_amount"]
        lines.extend([
            f"| **Total** | | | **${total_phinney:,.0f}** |",
            f"",
        ])

    # By decade
    lines.extend([
        f"## Funding by Decade",
        f"",
        f"| Decade | Grants | Funding |",
        f"|--------|--------|---------|",
    ])
    for decade in sorted(stats["by_decade"].keys()):
        d = stats["by_decade"][decade]
        lines.append(f"| {decade} | {d['count']} | ${d['funding']:,.0f} |")
    lines.append("")

    # By institute
    lines.extend([
        f"## NIH Institutes Represented",
        f"",
        f"| Institute | Grants | Funding |",
        f"|-----------|--------|---------|",
    ])
    sorted_institutes = sorted(
        stats["institutes"].items(), key=lambda x: x[1]["funding"], reverse=True
    )
    for abbr, data in sorted_institutes:
        lines.append(f"| {abbr} | {data['count']} | ${data['funding']:,.0f} |")
    lines.append("")

    # Active grants
    if stats["active_grants"]:
        lines.extend([
            f"## Currently Active Grants",
            f"",
            f"| Grant | PI | Title | Funding |",
            f"|-------|----|-------|---------|",
        ])
        for g in sorted(stats["active_grants"], key=lambda x: x["award_amount"], reverse=True):
            lines.append(
                f"| {g['core_number']} | {g['pi']} | {g['title'][:50]} | ${g['award_amount']:,.0f} |"
            )
        lines.append("")

    # All grants list
    lines.extend([
        f"## All Grants",
        f"",
        f"| Grant | PI | Title | Institute | Funding | Active |",
        f"|-------|----|-------|-----------|---------|--------|",
    ])
    for g in sorted(stats["all_grants"], key=lambda x: x["award_amount"], reverse=True):
        active_str = "Yes" if g["active"] else "No"
        lines.append(
            f"| {g['core_number']} | {g['pi'][:20]} | {g['title'][:40]} | {g['institute']} | ${g['award_amount']:,.0f} | {active_str} |"
        )
    lines.append("")

    return "\n".join(lines)


def generate_csv(stats):
    """Generate a CSV of all grants for spreadsheet use."""
    rows = []
    for g in stats["all_grants"]:
        rows.append({
            "core_number": g["core_number"],
            "project_number": g["project_number"],
            "pi": g["pi"],
            "title": g["title"],
            "institute": g["institute"],
            "fiscal_year": g["fiscal_year"],
            "award_amount": g["award_amount"],
            "start_date": g["start_date"],
            "end_date": g["end_date"],
            "active": g["active"],
        })
    return rows


def main():
    print("=" * 60)
    print("UC Davis Proteomics Core — NIH Impact Report Generator")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)
    print()

    # Run searches
    projects = run_searches()
    if not projects:
        print("No projects found. Check API connectivity.")
        return

    # Compute statistics
    print("\nComputing statistics...")
    stats = compute_statistics(projects)

    # Generate reports
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()

    # Markdown report
    md_report = generate_markdown_report(stats)
    md_path = REPORT_DIR / f"nih_impact_report_{today_str}.md"
    md_path.write_text(md_report)
    print(f"\nMarkdown report saved: {md_path}")

    # Also save as the "latest" report
    latest_md = REPORT_DIR / "nih_impact_report_latest.md"
    latest_md.write_text(md_report)
    print(f"Latest report saved: {latest_md}")

    # CSV export
    csv_path = REPORT_DIR / f"nih_grants_{today_str}.csv"
    rows = generate_csv(stats)
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV export saved: {csv_path}")

    # JSON data (for website integration)
    json_path = REPORT_DIR / "impact_data.json"
    json_data = {
        "generated": today_str,
        "total_grants": stats["total_grants"],
        "total_funding": stats["total_funding"],
        "unique_pis": stats["unique_pis"],
        "institutes_count": len(stats["institutes"]),
        "active_grants_count": len(stats["active_grants"]),
        "active_funding": sum(g["award_amount"] for g in stats["active_grants"]),
    }
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"JSON data saved: {json_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total grants:       {stats['total_grants']}")
    print(f"Total funding:      ${stats['total_funding']:,.0f}")
    print(f"Unique PIs:         {stats['unique_pis']}")
    print(f"NIH institutes:     {len(stats['institutes'])}")
    print(f"Active grants:      {len(stats['active_grants'])}")
    print(f"Active funding:     ${sum(g['award_amount'] for g in stats['active_grants']):,.0f}")


if __name__ == "__main__":
    main()
