#!/usr/bin/env python3
"""
Job Agent — Run: python3 agent.py
─────────────────────────────────────────────────────────────────────────────
Searches UK charity job boards, generates a daily digest + cover letters,
writes every job to your Google Sheet, and emails the digest to your inbox.

Quick setup:
  1. Copy .env.example → .env and fill in your keys
  2. Run:  python3 agent.py

Google Sheet:  see .env.example Step 3 for setup (5 minutes)
Auto daily:    push to GitHub — see .github/workflows/daily.yml
─────────────────────────────────────────────────────────────────────────────
"""

import glob
import json
import os
import re
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — SECRETS  (edit .env, not this file)
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()

ANTHROPIC_API_KEY           = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_ADDRESS               = os.getenv("GMAIL_ADDRESS", "alinafemaliro@gmail.com")
GMAIL_APP_PASSWORD          = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_TO                    = os.getenv("EMAIL_TO", "alinafemaliro@gmail.com")
GOOGLE_SHEET_ID             = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

BASE  = Path(__file__).parent
TODAY = date.today().isoformat()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — SETTINGS  (edit freely)
# ─────────────────────────────────────────────────────────────────────────────

# Claude model to use
CLAUDE_MODEL = "claude-opus-4-8"

# Number of cover letters per run
TOP_N = 5

# Job search queries — add or remove lines to change what gets searched
SEARCH_QUERIES = [
    "charityjob.co.uk finance officer UK charity 2026",
    "charityjob.co.uk finance assistant operations coordinator charity UK",
    "charityjob.co.uk grants officer programmes officer UK charity 2026",
    "charityjob.co.uk M&E officer monitoring evaluation UK charity",
    "charityjob.co.uk data analyst data officer UK charity 2026",
    "reed.co.uk finance assistant charity nonprofit London UK",
    "linkedin.com/jobs finance officer grants officer charity UK 2026",
]

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — FILE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def save(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ saved  →  {path.relative_to(BASE)}")


def prior_digests() -> str:
    """Last 14 digests — used to avoid repeating roles."""
    files = sorted(glob.glob(str(BASE / "digests" / "*.md")))
    return "\n\n---\n\n".join(read(Path(f)) for f in files[-14:])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — JOB SEARCH  (scrapes CharityJob directly — no API key needed)
# ─────────────────────────────────────────────────────────────────────────────

def search_jobs() -> str:
    from scraper import scrape_all
    return scrape_all()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — CLAUDE GENERATION
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_SYSTEM = """\
You are Emmanuel Alinafe Maliro's automated job-hunting assistant.
Today is {today}. You have been given real web search results from UK job boards.

YOUR TASK
1. Identify the best matching UK roles from the search results.
2. Write a morning digest in markdown (same format as previous digests).
3. Output a JSON array with one object per top role (for the Google Sheet).
4. Write a 250-350 word cover letter for each of the top {n} roles.

CV VERSIONS — use these exact IDs in the cv_version field of the JSON:
  Emmanuel_Maliro_v1_Finance     → finance officer, finance assistant, accounts assistant,
                                    operations coordinator, grants finance, ACCA trainee,
                                    finance administrator, bookkeeper, finance manager
  Emmanuel_Maliro_v2_Programmes  → M&E officer, MEAL officer, programmes officer,
                                    programme coordinator, grants officer, impact analyst,
                                    research associate, learning officer, programme manager
  Emmanuel_Maliro_v3_Data        → data analyst, research analyst, data officer,
                                    BI analyst, reporting analyst, data coordinator,
                                    insights analyst, junior data analyst

RULES
- Only include roles found in the search results. Never invent listings.
- Skip roles already listed in previous digests.
- Salary floor: £25,000. Skip roles below this unless ACCA trainee scheme.

OUTPUT — output ALL four sections below, in this exact order:

=== DIGEST START ===
[full digest in markdown, same format as previous digests]
=== DIGEST END ===

=== JOBS JSON START ===
[
  {{
    "title": "Exact Job Title",
    "employer": "Organisation Name",
    "location": "City (Remote/Hybrid/On-site)",
    "salary": "£XX,XXX",
    "deadline": "YYYY-MM-DD or 'verify on listing'",
    "link": "https://full-url-to-apply",
    "cv_version": "Emmanuel_Maliro_v1_Finance",
    "key_points": "1. [Specific JD requirement matched to your experience]\\n2. [Second tailoring point]\\n3. [Third tailoring point]",
    "cover_letter_slug": "slug-matching-the-cover-letter-below"
  }}
]
=== JOBS JSON END ===

=== COVER: cover-letter-slug START ===
[cover letter 250-350 words]
=== COVER: cover-letter-slug END ===
"""


def generate(search_results: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set.\n"
            "  → Add your key to .env (get it from console.anthropic.com)"
        )

    profile  = read(BASE / "profile.md")
    targets  = read(BASE / "targets.md")
    prev     = prior_digests()
    system   = CLAUDE_SYSTEM.format(today=TODAY, n=TOP_N)

    user_msg = f"""Today is {TODAY}. Generate the digest, JSON, and {TOP_N} cover letters.

=== CANDIDATE PROFILE ===
{profile}

=== TARGETS & SEARCH STRATEGY ===
{targets}

=== TODAY'S JOB BOARD SEARCH RESULTS ===
{search_results}

=== PREVIOUS DIGESTS — skip these roles ===
{prev[-5000:] if prev else "None yet — first run."}
"""

    client   = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model      = CLAUDE_MODEL,
        max_tokens = 8192,
        system     = system,
        messages   = [{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — PARSE OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def parse(output: str) -> tuple[str, list[dict], dict[str, str]]:
    """
    Returns:
      digest      — markdown string
      jobs        — list of job dicts (from JSON block)
      covers      — {slug: cover_letter_text}
    """
    # ── Digest ────────────────────────────────────────────────────────────────
    digest = ""
    m = re.search(r"=== DIGEST START ===(.*?)=== DIGEST END ===", output, re.DOTALL)
    if m:
        digest = m.group(1).strip()

    # ── Jobs JSON ─────────────────────────────────────────────────────────────
    jobs: list[dict] = []
    m = re.search(r"=== JOBS JSON START ===(.*?)=== JOBS JSON END ===", output, re.DOTALL)
    if m:
        try:
            jobs = json.loads(m.group(1).strip())
        except json.JSONDecodeError as e:
            print(f"  ⚠  Could not parse jobs JSON: {e}")

    # ── Cover letters ─────────────────────────────────────────────────────────
    covers: dict[str, str] = {}
    for m in re.finditer(
        r"=== COVER: (.+?) START ===(.*?)=== COVER: \1 END ===", output, re.DOTALL
    ):
        covers[m.group(1).strip()] = m.group(2).strip()

    # Attach full cover letter text to each job dict
    for job in jobs:
        slug = job.get("cover_letter_slug", "")
        if slug in covers:
            job["cover_letter"] = covers[slug]

    return digest, jobs, covers


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────────────────────

def write_to_sheet(jobs: list[dict]) -> str:
    """Write jobs to Google Sheet. Returns sheet URL or empty string if not configured."""
    if not GOOGLE_SHEET_ID:
        print("  ℹ  GOOGLE_SHEET_ID not set — skipping Google Sheet.")
        print("     See .env.example Step 3 to enable this feature.")
        return ""

    try:
        from sheets import setup_headers, get_existing_links, append_jobs, sheet_url

        setup_headers(GOOGLE_SHEET_ID)
        existing = get_existing_links(GOOGLE_SHEET_ID)
        new_jobs = [j for j in jobs if j.get("link", "") not in existing]

        if not new_jobs:
            print("  ℹ  All jobs already in Google Sheet — nothing to add.")
            return sheet_url(GOOGLE_SHEET_ID)

        n = append_jobs(GOOGLE_SHEET_ID, new_jobs)
        print(f"  ✅ {n} new row(s) added to Google Sheet")
        return sheet_url(GOOGLE_SHEET_ID)

    except Exception as e:
        print(f"  ⚠  Google Sheets error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — EMAIL
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_HTML = """\
<!doctype html>
<html>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;
             padding:24px;color:#222">

<h2 style="color:#1a56a0;border-bottom:2px solid #1a56a0;padding-bottom:8px">
  Daily Job Digest — {date}
</h2>

<table style="width:100%;border-collapse:collapse;margin-bottom:20px">
  <tr>
    <td style="padding:8px 12px;background:#f0f4fa;border-radius:6px;font-size:14px">
      📋 <strong>{n_jobs} jobs</strong> added to your Google Sheet today<br>
      📝 <strong>{n_covers} cover letters</strong> saved to <code>cv-variants/</code><br>
      {sheet_link}
    </td>
  </tr>
</table>

<div style="background:#f5f7fa;border:1px solid #dde3ec;border-radius:6px;
            padding:20px;margin:20px 0;overflow-x:auto">
  <pre style="margin:0;font-size:13px;line-height:1.7;white-space:pre-wrap">\
{digest}\
</pre>
</div>

<p style="font-size:12px;color:#888;margin-top:24px">
  Full digest: <code>digests/{date}-digest.md</code><br>
  Cover letters: <code>cv-variants/{date}_*.md</code><br>
  <em>Sent automatically by your Job Agent.</em>
</p>
</body>
</html>
"""


def send_email(digest: str, n_jobs: int, n_covers: int, sheet_url: str) -> None:
    if not GMAIL_APP_PASSWORD:
        print("  ⚠  GMAIL_APP_PASSWORD not set — skipping email.")
        return

    sheet_link = (
        f'🔗 <a href="{sheet_url}" style="color:#1a56a0">Open Google Sheet</a>'
        if sheet_url else
        "💡 Add GOOGLE_SHEET_ID to .env to enable the Google Sheet."
    )

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"Job Digest — {TODAY}  ({n_jobs} new jobs · {n_covers} cover letters)"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = EMAIL_TO

    html = EMAIL_HTML.format(
        date=TODAY, digest=digest,
        n_jobs=n_jobs, n_covers=n_covers,
        sheet_link=sheet_link,
    )
    msg.attach(MIMEText(digest, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_ADDRESS, EMAIL_TO, msg.as_string())

    print(f"  ✅ email sent  →  {EMAIL_TO}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'═' * 60}")
    print(f"  JOB AGENT  ·  {TODAY}  ·  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═' * 60}\n")

    # Step 1 — Search job boards
    print("Step 1 / 5  →  searching job boards …")
    search_results = search_jobs()

    # Step 2 — Generate digest, JSON, and cover letters via Claude
    print("\nStep 2 / 5  →  generating digest + cover letters (~60 sec) …")
    raw = generate(search_results)

    # Step 3 — Parse output
    print("\nStep 3 / 5  →  parsing output …")
    digest, jobs, covers = parse(raw)

    if not digest:
        print("  ⚠  digest delimiters not found — saving raw output")
        digest = raw

    print(f"  → {len(jobs)} jobs in JSON  ·  {len(covers)} cover letters")

    # Step 4 — Save files
    print("\nStep 4 / 5  →  saving files …")
    save(BASE / "digests"     / f"{TODAY}-digest.md", digest)
    for slug, text in covers.items():
        save(BASE / "cv-variants" / f"{TODAY}_{slug}_cover.md", text)

    # Step 5 — Google Sheet + email
    print("\nStep 5 / 5  →  Google Sheet + email …")
    url = write_to_sheet(jobs)
    send_email(digest, len(jobs), len(covers), url)

    print(f"\n{'═' * 60}")
    print(f"  DONE")
    print(f"  • {len(jobs)} jobs written to Google Sheet")
    print(f"  • {len(covers)} cover letters saved")
    print(f"  • digest emailed to {EMAIL_TO}")
    if url:
        print(f"  • sheet: {url}")
    print(f"  • {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
