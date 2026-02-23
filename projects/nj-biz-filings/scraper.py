#!/usr/bin/env python3
"""
NJ Business Filings Monitor — Scraper
Scrapes recently-formed NJ LLCs/Corps from the NJ Division of Revenue
Business Name Search portal. Outputs leads for Matt Gibson (financial advisor).

Usage:
    python3 scraper.py                # scrape LLCs (default)
    python3 scraper.py --type CORP    # scrape corporations
    python3 scraper.py --type ALL     # both LLC and CORP
    python3 scraper.py --days 60      # look back 60 days (default: 30)
    python3 scraper.py --max 100      # max entities to detail-scrape (default: 50)
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / "clawd" / "data" / "biz-filings"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DATA_DIR / "scraper.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("nj-biz-scraper")

SEARCH_URL = "https://www.njportal.com/DOR/BusinessNameSearch/"

ENTITY_TYPE_MAP = {
    "LLC": "Domestic Limited Liability Company",
    "CORP": "Domestic Business Corporation",
}


def parse_date(date_str: str) -> datetime | None:
    """Try multiple date formats."""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def scrape_entities(entity_type: str, days_back: int, max_detail: int) -> list[dict]:
    """Scrape entities of given type from NJ portal. Returns list of entity dicts."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    cutoff = datetime.now() - timedelta(days=days_back)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        log.info(f"Navigating to {SEARCH_URL}")
        try:
            page.goto(SEARCH_URL, wait_until="networkidle")
        except PWTimeout:
            log.error("Timeout loading search page")
            browser.close()
            return []

        # Check for SSO redirect
        if "sso" in page.url.lower() or "login" in page.url.lower():
            log.error(f"Redirected to SSO/login: {page.url} — portal requires auth")
            browser.close()
            return []

        log.info(f"Page loaded: {page.url}")

        # Select entity type
        try:
            type_label = ENTITY_TYPE_MAP.get(entity_type, "Domestic Limited Liability Company")
            # Try to find and select the entity type dropdown
            page.wait_for_selector("select", timeout=10_000)
            selects = page.query_selector_all("select")
            for sel in selects:
                opts = sel.query_selector_all("option")
                opt_texts = [o.inner_text() for o in opts]
                if any("LLC" in t or "Corporation" in t or "Limited" in t for t in opt_texts):
                    # This is likely the entity type select
                    # Try to select our type
                    matched = next(
                        (t for t in opt_texts if type_label.lower() in t.lower() or entity_type in t.upper()),
                        None,
                    )
                    if matched:
                        sel.select_option(label=matched)
                        log.info(f"Selected entity type: {matched}")
                    break
        except Exception as e:
            log.warning(f"Could not set entity type filter: {e}")

        # Leave search box blank or minimal, submit
        try:
            # Try to find and click the search button
            search_btn = page.query_selector("input[type='submit'], button[type='submit'], #btnSearch, .btn-search")
            if search_btn:
                search_btn.click()
                page.wait_for_load_state("networkidle")
                log.info("Search submitted")
            else:
                # Try pressing Enter on any visible input
                inputs = page.query_selector_all("input[type='text']")
                if inputs:
                    inputs[0].press("Enter")
                    page.wait_for_load_state("networkidle")
        except Exception as e:
            log.warning(f"Search submission issue: {e}")

        # Scrape results table
        page_num = 0
        seen_ids: set[str] = set()
        detail_count = 0

        while True:
            page_num += 1
            log.info(f"Scraping results page {page_num}")

            # Find results table rows
            rows = page.query_selector_all("table tbody tr, #searchResults tr, .result-row")
            if not rows:
                log.info("No result rows found on this page")
                break

            page_results = []
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) < 3:
                    continue

                texts = [c.inner_text().strip() for c in cells]
                # Typical columns: Entity Name | Entity ID | Entity Type | Status | Date Formed
                if len(texts) < 4:
                    continue

                # Try to extract entity ID (usually numeric, 10 chars)
                entity_id = None
                name = None
                formed_date_str = None
                status = None
                etype = None

                # Heuristic: find a cell that looks like an entity ID
                for i, t in enumerate(texts):
                    if re.match(r"^\d{6,12}$", t):
                        entity_id = t
                        if i > 0:
                            name = texts[i - 1]
                        if i + 1 < len(texts):
                            etype = texts[i + 1]
                        if i + 2 < len(texts):
                            status = texts[i + 2]
                        if i + 3 < len(texts):
                            formed_date_str = texts[i + 3]
                        break

                if not entity_id:
                    # Fallback: first cell is name, second is ID
                    name = texts[0]
                    entity_id = texts[1] if len(texts) > 1 else None
                    etype = texts[2] if len(texts) > 2 else entity_type
                    status = texts[3] if len(texts) > 3 else "Unknown"
                    formed_date_str = texts[4] if len(texts) > 4 else None

                if not entity_id or entity_id in seen_ids:
                    continue

                # Parse formation date
                formed_date = parse_date(formed_date_str) if formed_date_str else None
                if formed_date and formed_date < cutoff:
                    log.debug(f"Skipping {name} — formed {formed_date_str} (before cutoff)")
                    continue

                seen_ids.add(entity_id)

                # Find the entity name link
                link_el = row.query_selector("a")
                detail_url = None
                if link_el:
                    detail_url = link_el.get_attribute("href")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = SEARCH_URL.rstrip("/") + "/" + detail_url.lstrip("/")

                entry = {
                    "entity_id": entity_id,
                    "name": name or "Unknown",
                    "type": etype or entity_type,
                    "status": status or "Active",
                    "formed_date": formed_date.strftime("%Y-%m-%d") if formed_date else formed_date_str,
                    "agent_name": None,
                    "agent_address": None,
                    "agent_city": None,
                    "agent_state": "NJ",
                    "agent_zip": None,
                    "officers": [],
                    "detail_url": detail_url,
                    "scraped_at": datetime.now().isoformat(),
                }
                page_results.append(entry)

            log.info(f"Found {len(page_results)} recent entities on page {page_num}")

            # Fetch detail pages for each entity
            for entry in page_results:
                if detail_count >= max_detail:
                    log.info(f"Reached max detail limit ({max_detail}), stopping")
                    results.extend(page_results)
                    browser.close()
                    return results

                if entry.get("detail_url"):
                    try:
                        log.info(f"Fetching detail: {entry['name']} ({entry['entity_id']})")
                        detail_page = context.new_page()
                        detail_page.goto(entry["detail_url"], wait_until="domcontentloaded")
                        detail_html = detail_page.content()
                        _parse_detail(entry, detail_page)
                        detail_page.close()
                        detail_count += 1
                    except Exception as e:
                        log.warning(f"Detail fetch failed for {entry['entity_id']}: {e}")

                results.append(entry)

            # Try to go to next page
            next_btn = page.query_selector("a[rel='next'], .pagination .next, #btnNext, a:has-text('Next')")
            if next_btn:
                try:
                    next_btn.click()
                    page.wait_for_load_state("networkidle")
                except Exception:
                    break
            else:
                break

        browser.close()

    log.info(f"Total entities scraped: {len(results)}")
    return results


def _parse_detail(entry: dict, page) -> None:
    """Parse detail page for agent and officer info."""
    try:
        text = page.inner_text("body")
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Look for registered agent section
        agent_section = False
        for i, line in enumerate(lines):
            if "registered agent" in line.lower():
                agent_section = True
                # Next few lines should have name and address
                for j in range(i + 1, min(i + 8, len(lines))):
                    l = lines[j]
                    if not entry.get("agent_name") and l and not any(
                        kw in l.lower() for kw in ["address", "city", "state", "zip", "agent"]
                    ):
                        entry["agent_name"] = l
                    elif re.search(r"\d{5}", l):
                        # Looks like it has a ZIP
                        zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", l)
                        if zip_match:
                            entry["agent_zip"] = zip_match.group(1)
                        # Try to extract city from "City, ST 07701" pattern
                        city_match = re.search(r"([A-Za-z\s]+),\s*([A-Z]{2})\s*\d{5}", l)
                        if city_match:
                            entry["agent_city"] = city_match.group(1).strip()
                            entry["agent_state"] = city_match.group(2)
                    elif entry.get("agent_name") and not entry.get("agent_address") and l:
                        entry["agent_address"] = l
                break

        # Look for officers/members
        officers = []
        officer_section = False
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in ["officer", "director", "member", "manager", "principal"]):
                officer_section = True
                continue
            if officer_section:
                if line and not any(kw in line.lower() for kw in ["registered", "address", "status", "entity"]):
                    officers.append(line)
                if len(officers) >= 5:
                    break
                if not line:
                    officer_section = False

        entry["officers"] = officers[:5]

    except Exception as e:
        log.warning(f"Error parsing detail page: {e}")


def save_results(results: list[dict]) -> None:
    """Save results to dated JSON and merge into master.json."""
    today = datetime.now().strftime("%Y-%m-%d")
    dated_file = DATA_DIR / f"{today}.json"

    # Save today's results
    with open(dated_file, "w") as f:
        json.dump({"scraped_at": datetime.now().isoformat(), "count": len(results), "entities": results}, f, indent=2)
    log.info(f"Saved {len(results)} entities to {dated_file}")

    # Merge into master.json
    master_file = DATA_DIR / "master.json"
    if master_file.exists():
        with open(master_file) as f:
            master = json.load(f)
    else:
        master = {"entities": []}

    existing_ids = {e["entity_id"] for e in master["entities"]}
    new_count = 0
    for entity in results:
        if entity["entity_id"] not in existing_ids:
            master["entities"].append(entity)
            existing_ids.add(entity["entity_id"])
            new_count += 1

    master["last_updated"] = datetime.now().isoformat()
    master["total_count"] = len(master["entities"])

    with open(master_file, "w") as f:
        json.dump(master, f, indent=2)

    log.info(f"Master.json updated: {new_count} new, {len(master['entities'])} total")


def main():
    parser = argparse.ArgumentParser(description="NJ Business Filings Scraper")
    parser.add_argument("--type", choices=["LLC", "CORP", "ALL"], default="LLC", help="Entity type to scrape")
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    parser.add_argument("--max", type=int, default=50, help="Max entities to detail-scrape (default: 50)")
    args = parser.parse_args()

    log.info(f"=== NJ Biz Filings Scraper starting | type={args.type} days={args.days} max={args.max} ===")

    types = ["LLC", "CORP"] if args.type == "ALL" else [args.type]
    all_results = []

    for etype in types:
        log.info(f"--- Scraping {etype} entities ---")
        try:
            results = scrape_entities(etype, args.days, args.max)
            all_results.extend(results)
        except Exception as e:
            log.error(f"Scrape failed for {etype}: {e}")
            error_file = DATA_DIR / f"error-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.json"
            with open(error_file, "w") as f:
                json.dump({"error": str(e), "type": etype, "timestamp": datetime.now().isoformat()}, f)

    if all_results:
        save_results(all_results)
        print(f"\n✅ Scraped {len(all_results)} entities. Data at: {DATA_DIR}")
    else:
        log.warning("No results scraped — portal may be blocking or no recent filings found")
        # Write empty result so dashboard doesn't break
        save_results([])
        sys.exit(1)


if __name__ == "__main__":
    main()
