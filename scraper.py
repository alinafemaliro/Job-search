"""
scraper.py — Direct CharityJob scraper.
Fetches actual job listings from charityjob.co.uk search pages.
"""

import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

SEARCHES = [
    "finance officer",
    "finance assistant",
    "operations coordinator",
    "grants officer",
    "programmes officer",
    "M&E officer",
    "monitoring evaluation officer",
    "data analyst charity",
    "data officer charity",
    "research officer charity",
]


def fetch_charityjob(keyword: str, pages: int = 2) -> list[dict]:
    """Scrape CharityJob for a keyword. Returns list of job dicts."""
    jobs  = []
    seen  = set()

    for page in range(1, pages + 1):
        url = f"https://www.charityjob.co.uk/jobs?keywords={requests.utils.quote(keyword)}&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")

            for card in soup.select("article.job-card-wrapper"):
                job = _parse_card(card)
                if job and job["link"] not in seen:
                    jobs.append(job)
                    seen.add(job["link"])

            if page < pages:
                time.sleep(1)

        except Exception as e:
            print(f"     ⚠  '{keyword}' page {page}: {e}")

    return jobs


def _parse_card(card) -> dict | None:
    # Title + link
    title_el = card.select_one(".job-title a") or card.select_one("a")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    href  = title_el.get("href", "")
    if href and not href.startswith("http"):
        href = "https://www.charityjob.co.uk" + href

    # Clean URL (remove tracking params)
    href = href.split("?")[0]

    # Get full card text for details
    text = card.get_text(" ", strip=True)

    # Employer — usually the first line after the title inside job-summary
    summary_el = card.select_one(".job-summary")
    summary_text = summary_el.get_text(" ", strip=True) if summary_el else text

    # Extract salary (£ pattern)
    salary_m = re.search(r'£[\d,]+(?:\s*[-–]\s*£?[\d,]+)?(?:\s*(?:per|p\.a\.|k)[\w\s]*)?', text)
    salary   = salary_m.group(0).strip() if salary_m else ""

    # Extract closing date
    deadline_m = re.search(
        r'(?:Clos(?:ing|es?)|Deadline)[:\s]+([^\n|]+?)(?:\s*\||$)',
        text, re.IGNORECASE
    )
    deadline = deadline_m.group(1).strip() if deadline_m else ""

    # Employer: text between title and location clues
    employer = ""
    lines = [l.strip() for l in summary_text.split("  ") if l.strip()]
    for line in lines:
        if line == title:
            continue
        if any(x in line.lower() for x in ["£", "closing", "london", "remote",
                                             "hybrid", "full-time", "part-time"]):
            break
        if len(line) > 3 and not line.startswith("Top job"):
            employer = line
            break

    # Location
    location_m = re.search(
        r'\b(London|Manchester|Birmingham|Bristol|Edinburgh|Glasgow|Leeds|'
        r'Oxford|Cambridge|Cardiff|Belfast|Sheffield|Remote|Hybrid|UK-wide'
        r'|[\w\s]+(?:shire|ford|ham|ton|wick))[,\s]',
        text
    )
    location = location_m.group(1).strip() if location_m else ""

    if not title or not href or "charityjob.co.uk/jobs/" not in href:
        return None

    return {
        "title":    title,
        "employer": employer,
        "location": location,
        "salary":   salary,
        "deadline": deadline,
        "link":     href,
    }


def format_results(jobs: list[dict]) -> str:
    if not jobs:
        return "No listings found."
    lines = [f"SCRAPED {len(jobs)} LIVE LISTINGS FROM CHARITYJOB.CO.UK\n"]
    for j in jobs:
        lines.append(
            f"TITLE: {j['title']}\n"
            f"EMPLOYER: {j['employer']}\n"
            f"LOCATION: {j['location']}\n"
            f"SALARY: {j['salary']}\n"
            f"DEADLINE: {j['deadline']}\n"
            f"LINK: {j['link']}\n---"
        )
    return "\n".join(lines)


def scrape_all() -> str:
    all_jobs: list[dict] = []
    seen: set[str] = set()

    for keyword in SEARCHES:
        print(f"     🔍 '{keyword}'")
        jobs = fetch_charityjob(keyword, pages=2)
        for j in jobs:
            if j["link"] not in seen:
                all_jobs.append(j)
                seen.add(j["link"])
        time.sleep(1.5)

    print(f"     → {len(all_jobs)} unique listings scraped")
    return format_results(all_jobs)
