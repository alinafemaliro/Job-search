#!/usr/bin/env python3
"""
Job Agent — Run: python3 agent.py
─────────────────────────────────────────────────────────────────────────────
Searches UK charity job boards, generates a daily digest + cover letters,
and emails everything to your inbox.

Quick setup:
  1. Copy .env.example → .env and fill in your two keys
  2. Run:  python3 agent.py
  3. Check your email  alinafemaliro@gmail.com

For hands-free daily runs (no PC needed):
  Push this folder to GitHub — see .github/workflows/daily.yml
─────────────────────────────────────────────────────────────────────────────
"""

import glob
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
# SECTION 1 — SECRETS & PATHS
# Edit the .env file, not this section.
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS", "alinafemaliro@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_TO           = os.getenv("EMAIL_TO", "alinafemaliro@gmail.com")

BASE  = Path(__file__).parent
TODAY = date.today().isoformat()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — SETTINGS
# Edit these values to change how the agent behaves.
# ─────────────────────────────────────────────────────────────────────────────

# Claude model — opus is most capable; sonnet is faster and cheaper
CLAUDE_MODEL = "claude-opus-4-8"

# How many cover letters to write per run (top N roles)
TOP_N = 5

# Job boards to include in each search
JOB_BOARDS = [
    "charityjob.co.uk",
    "reed.co.uk",
    "linkedin.com/jobs",
    "indeed.co.uk",
    "jobs.theguardian.com",
]

# Search terms — add or remove lines to change what gets searched
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
# Internal functions — you don't need to edit this section.
# ─────────────────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def save(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ saved  →  {path.relative_to(BASE)}")


def prior_digests() -> str:
    """Return last 14 digests joined — used to avoid repeating roles."""
    files = sorted(glob.glob(str(BASE / "digests" / "*.md")))
    return "\n\n---\n\n".join(read(Path(f)) for f in files[-14:])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — JOB SEARCH
# Uses DuckDuckGo to pull live job listings from UK job boards.
# No API key needed. Results are passed to Claude in Section 5.
# ─────────────────────────────────────────────────────────────────────────────

def search_jobs() -> str:
    """Search UK job boards via DuckDuckGo. Returns combined snippet text."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "[duckduckgo-search not installed — run: pip3 install duckduckgo-search]"

    all_results: list[str] = []
    with DDGS() as ddgs:
        for query in SEARCH_QUERIES:
            print(f"     🔍 {query[:70]}")
            try:
                hits = list(ddgs.text(query, max_results=12, region="uk-en"))
                block = f"\n### Search: {query}\n" + "\n".join(
                    f"- [{h['title']}]({h['href']})\n  {h['body']}" for h in hits
                )
                all_results.append(block)
            except Exception as e:
                all_results.append(f"\n### Search: {query}\n[Error: {e}]")

    return "\n\n".join(all_results)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — CLAUDE GENERATION
# Passes the search results + your profile to Claude.
# Claude produces the digest and cover letters.
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_SYSTEM = """\
You are Emmanuel Alinafe Maliro's automated job-hunting assistant.
Today is {today}. You have been given real web search results from UK job boards.

YOUR TASK
1. From the search results, identify the best matching UK roles that fit the
   candidate's profile and targets (Finance/Operations, M&E/Grants, Data/Research).
2. Write a morning digest in exactly the same format as the previous digests.
3. Write a tailored 250-350 word cover letter for each of the top {n} roles.

RULES
- Only include roles found in the search results. Never invent listings.
- Skip any role already in the previous digests (shown in the user message).
- Follow the profile.md cover letter tone and targets.md rules exactly.
- Salary floor: £25,000. Skip roles below this unless they are ACCA trainee schemes.

OUTPUT — use these exact delimiters, no exceptions:

=== DIGEST START ===
[full digest in markdown, same format as previous digests]
=== DIGEST END ===

=== COVER: <role-slug> START ===
[cover letter 250-350 words]
=== COVER: <role-slug> END ===
"""


def generate(search_results: str) -> str:
    """Call Claude API with search results + profile, return raw output."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set.\n"
            "  → Copy .env.example to .env and add your key from console.anthropic.com"
        )

    profile  = read(BASE / "profile.md")
    targets  = read(BASE / "targets.md")
    prev     = prior_digests()
    system   = CLAUDE_SYSTEM.format(today=TODAY, n=TOP_N)

    user_msg = f"""Today is {TODAY}. Generate the digest and {TOP_N} cover letters.

=== CANDIDATE PROFILE ===
{profile}

=== TARGETS & SEARCH STRATEGY ===
{targets}

=== TODAY'S JOB BOARD SEARCH RESULTS ===
{search_results}

=== PREVIOUS DIGESTS — skip these roles, do NOT repeat them ===
{prev[-5000:] if prev else "None yet — this is the first run."}
"""

    client   = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model    = CLAUDE_MODEL,
        max_tokens = 8192,
        system   = system,
        messages = [{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — PARSE OUTPUT
# Splits Claude's output into the digest and individual cover letters.
# ─────────────────────────────────────────────────────────────────────────────

def parse(output: str) -> tuple[str, dict[str, str]]:
    """Extract digest and cover letters from Claude's delimited output."""
    digest = ""
    covers: dict[str, str] = {}

    m = re.search(r"=== DIGEST START ===(.*?)=== DIGEST END ===", output, re.DOTALL)
    if m:
        digest = m.group(1).strip()

    for m in re.finditer(
        r"=== COVER: (.+?) START ===(.*?)=== COVER: \1 END ===", output, re.DOTALL
    ):
        covers[m.group(1).strip()] = m.group(2).strip()

    return digest, covers


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — EMAIL
# Sends the digest to your Gmail inbox.
# Requires GMAIL_APP_PASSWORD in your .env file (see .env.example).
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_HTML = """\
<!doctype html>
<html>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;
             padding:24px;color:#222">

<h2 style="color:#1a56a0;border-bottom:2px solid #1a56a0;padding-bottom:8px">
  Daily Job Digest — {date}
</h2>

<p>
  Your job agent has finished today's search.<br>
  <strong>{n_covers} cover letter(s)</strong> are ready in
  <code>cv-variants/</code>.
</p>

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


def send_email(digest: str, n_covers: int) -> None:
    """Send the digest to EMAIL_TO via Gmail SMTP."""
    if not GMAIL_APP_PASSWORD:
        print("  ⚠  GMAIL_APP_PASSWORD not set — skipping email.")
        print("     Add it to .env (see .env.example for instructions).")
        return

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"Job Digest — {TODAY}  ({n_covers} cover letters ready)"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = EMAIL_TO

    html = EMAIL_HTML.format(date=TODAY, digest=digest, n_covers=n_covers)
    msg.attach(MIMEText(digest, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_ADDRESS, EMAIL_TO, msg.as_string())

    print(f"  ✅ email sent  →  {EMAIL_TO}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — MAIN
# This is the entry point. Run:  python3 agent.py
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'═' * 58}")
    print(f"  JOB AGENT  ·  {TODAY}  ·  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═' * 58}\n")

    # ── Step 1 — Search job boards ────────────────────────────────────────────
    print("Step 1 / 4  →  searching job boards …")
    search_results = search_jobs()

    # ── Step 2 — Generate digest + cover letters ──────────────────────────────
    print("\nStep 2 / 4  →  generating digest + cover letters (takes ~60 sec) …")
    raw = generate(search_results)

    # ── Step 3 — Parse and save ───────────────────────────────────────────────
    print("\nStep 3 / 4  →  saving files …")
    digest, covers = parse(raw)

    if not digest:
        print("  ⚠  digest delimiters not found — saving raw output as digest")
        digest = raw

    save(BASE / "digests"     / f"{TODAY}-digest.md", digest)
    for slug, text in covers.items():
        save(BASE / "cv-variants" / f"{TODAY}_{slug}_cover.md", text)

    # ── Step 4 — Email ────────────────────────────────────────────────────────
    print("\nStep 4 / 4  →  sending email …")
    send_email(digest, len(covers))

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 58}")
    print(f"  DONE  ·  {len(covers)} cover letters written")
    print(f"        ·  digest emailed to {EMAIL_TO}")
    print(f"        ·  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═' * 58}\n")


if __name__ == "__main__":
    main()
