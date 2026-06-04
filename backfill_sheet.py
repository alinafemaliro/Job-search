#!/usr/bin/env python3
"""
backfill_sheet.py — Fill the Google Sheet from all existing digest files.
Run once: python3 backfill_sheet.py

No Anthropic credits needed — reads the saved markdown files directly.
Only adds jobs whose deadline hasn't passed yet.
"""

import glob
import os
import re
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE           = Path(__file__).parent
TODAY          = date.today()
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def read(path):
    return Path(path).read_text(encoding="utf-8")


def guess_cv_version(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["data analyst", "research analyst", "data officer",
                              "bi analyst", "reporting analyst", "insights analyst",
                              "data coordinator", "junior data"]):
        return "Emmanuel_Maliro_v3_Data"
    if any(w in t for w in ["m&e", "mel ", "meal", "programme", "program",
                              "grants officer", "impact analyst", "monitoring",
                              "evaluation", "learning officer"]):
        return "Emmanuel_Maliro_v2_Programmes"
    return "Emmanuel_Maliro_v1_Finance"


def parse_deadline(text: str) -> date | None:
    """Parse a deadline string into a date. Returns None if unparseable."""
    if not text:
        return None
    # Remove time portion and extra words
    text = re.sub(r'\s+at\s+\d+:\d+.*', '', text).strip()
    text = text.replace("**", "").strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:20].strip(), fmt).date()
        except ValueError:
            continue
    return None


def is_open(deadline_str: str) -> bool:
    """Return True if the deadline is today or in the future, or if unknown."""
    dl = parse_deadline(deadline_str)
    if dl is None:
        return True   # can't tell — include it
    return dl >= TODAY


def load_cover_letter(digest_date: str, slug: str) -> str:
    """Load cover letter markdown if the file exists."""
    path = BASE / "cv-variants" / f"{digest_date}_{slug}_cover.md"
    if path.exists():
        return read(path)
    return ""


# ─── Digest parser ───────────────────────────────────────────────────────────

def _get(section: str, field: str) -> str:
    m = re.search(rf'\*\*{re.escape(field)}[:\*]+\s*(.+)', section)
    return m.group(1).strip() if m else ""


def extract_top5(digest_text: str, digest_date: str) -> list[dict]:
    """Extract Top 5 job entries from a digest (structured sections)."""
    jobs = []

    # Each top-5 entry starts with  ### N.  and ends at the next ---  or ###
    sections = re.split(r'\n(?=### \d+\.)', digest_text)

    for section in sections:
        if not re.match(r'### \d+\.', section.lstrip()):
            continue

        # First line: "### 1. Job Title — Employer"
        first_line = section.strip().split("\n")[0]
        header     = re.sub(r'^#{2,3}\s*\d+\.\s*', '', first_line).strip()
        parts      = header.split(" — ", 1)
        title      = parts[0].strip()
        employer   = parts[1].strip() if len(parts) > 1 else ""

        location = _get(section, "Location")
        salary   = _get(section, "Salary")
        deadline = _get(section, "Closing date") or _get(section, "Deadline")

        # URL from Source line: [Text](URL)
        src_m = re.search(r'\*\*Source:\*\*.*?\[.*?\]\((https?://[^\)]+)\)', section)
        link  = src_m.group(1).strip() if src_m else ""

        # Cover letter slug from the file path
        cl_m = re.search(
            r'cv-variants/\d{4}-\d{2}-\d{2}_(.+?)_cover\.md', section
        )
        slug = cl_m.group(1) if cl_m else ""

        if not title or not link:
            continue

        cover = load_cover_letter(digest_date, slug)

        jobs.append({
            "title":         title,
            "employer":      employer,
            "location":      location,
            "salary":        salary,
            "deadline":      deadline,
            "link":          link,
            "cv_version":    guess_cv_version(title),
            "key_points":    "",          # will be empty for backfill
            "cover_letter":  cover,
        })

    return jobs


def extract_also_worth(digest_text: str) -> list[dict]:
    """Extract 'Also worth a look' bullet jobs (less structured)."""
    jobs = []

    # Find the "Also worth a look" section
    m = re.search(
        r'## Also worth a look(.*?)(?=\n##|\Z)', digest_text, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return []

    section = m.group(1)

    for bullet in re.finditer(r'- \*\*(.+?)\*\*.*?\((https?://[^\)]+)\)', section):
        raw_title = bullet.group(1)
        link      = bullet.group(2)

        # "Title — Employer" format
        parts    = raw_title.split(" — ", 1)
        title    = parts[0].strip()
        employer = parts[1].strip() if len(parts) > 1 else ""

        # Salary from context
        salary_m = re.search(r'£[\d,]+(?:–£[\d,]+)?', bullet.group(0))
        salary   = salary_m.group(0) if salary_m else ""

        # Deadline
        dl_m   = re.search(r'Closes?\s+(.+?)(?:\.|\s*\[|\s*$)', bullet.group(0))
        deadline = dl_m.group(1).strip() if dl_m else ""

        if title and link:
            jobs.append({
                "title":        title,
                "employer":     employer,
                "location":     "",
                "salary":       salary,
                "deadline":     deadline,
                "link":         link,
                "cv_version":   guess_cv_version(title),
                "key_points":   "",
                "cover_letter": "",
            })

    return jobs


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'═'*58}")
    print(f"  BACKFILL SHEET  ·  {TODAY.isoformat()}")
    print(f"{'═'*58}\n")

    if not GOOGLE_SHEET_ID:
        print("❌  GOOGLE_SHEET_ID not set in .env")
        return

    from sheets import setup_headers, get_existing_links, append_jobs, sheet_url

    setup_headers(GOOGLE_SHEET_ID)
    existing = get_existing_links(GOOGLE_SHEET_ID)
    print(f"  {len(existing)} job(s) already in sheet\n")

    digest_files = sorted(glob.glob(str(BASE / "digests" / "*.md")))
    print(f"  Reading {len(digest_files)} digest file(s)…\n")

    all_new: list[dict] = []

    for fpath in digest_files:
        stem        = Path(fpath).stem                  # e.g. "2026-06-02-digest"
        digest_date = stem.replace("-digest", "")       # e.g. "2026-06-02"
        text        = read(Path(fpath))

        top5  = extract_top5(digest_text=text, digest_date=digest_date)
        also  = extract_also_worth(digest_text=text)
        found = top5 + also

        kept = 0
        for job in found:
            if job["link"] in existing:
                continue                               # already in sheet
            if not is_open(job["deadline"]):
                continue                               # deadline passed
            all_new.append(job)
            existing.add(job["link"])
            kept += 1

        print(f"  {digest_date}  →  {len(found)} found  ·  {kept} new & still open")

    print(f"\n  Adding {len(all_new)} row(s) to Google Sheet…")
    if all_new:
        n = append_jobs(GOOGLE_SHEET_ID, all_new)
        print(f"  ✅ {n} rows added")
    else:
        print("  ✅ Sheet is already up to date — nothing new to add")

    print(f"\n  Open sheet: {sheet_url(GOOGLE_SHEET_ID)}")
    print(f"\n{'═'*58}\n")


if __name__ == "__main__":
    main()
