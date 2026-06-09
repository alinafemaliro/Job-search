#!/usr/bin/env python3
"""
biz_agent.py — UK Business Opportunities Finder
─────────────────────────────────────────────────────────────────────────────
Finds UK businesses for sale under £25,000, analyses them with Claude,
and emails a ranked digest with investment insights.

Run:  python3 biz_agent.py

No extra setup needed — uses the same .env as the job agent.
Saves digests to:  business-opps/<date>-biz-digest.md
─────────────────────────────────────────────────────────────────────────────
"""

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
# SECTION 1 — SECRETS  (same .env as agent.py)
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS", "alinafemaliro@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_TO           = os.getenv("EMAIL_TO", "alinafemaliro@gmail.com")

BASE       = Path(__file__).parent
TODAY      = date.today().isoformat()
MAX_PRICE  = 25_000
TOP_N      = 8       # top picks to analyse in depth
CLAUDE_MODEL = "claude-opus-4-8"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — CLAUDE PROMPT
# ─────────────────────────────────────────────────────────────────────────────

BIZ_SYSTEM = """\
You are an investment analyst helping Emmanuel Alinafe Maliro find profitable
UK businesses to buy with a budget of max £25,000.

BUYER PROFILE
- Based in London, full-time job in finance/data/programmes
- Wants extra income — ideally passive or low-hours manageable alongside his job
- First-time business buyer — needs realistic, honest advice
- Open to: online/digital businesses, service businesses, agencies, e-commerce,
  franchises, vending, cleaning, care/support work contracts, trade businesses
  he can manage with a part-time manager, B2B service contracts
- Wants to eventually exit full-time employment or build a property portfolio

SCORING FACTORS (rank top {n} picks)
1. Turnover-to-price ratio — high turnover for low price = strong signal
2. Passive / low-hours — can he keep his job while running this?
3. Low overheads / no heavy stock
4. Growth potential in the UK market
5. Risk level for a first-time buyer
6. Digital or location-independent (ideal for mobile management)

HARD EXCLUDE (flag but do not recommend)
- Restaurants, cafes, pubs above £5,000 asking price
- Businesses needing specialist licences he likely lacks (SIA, HGV, solicitor)
- Manufacturing with heavy machinery
- Loss-making businesses with no clear turnaround story

OUTPUT — produce ALL sections in this exact order:

=== BIZ DIGEST START ===
# UK Business Opportunities — {date}
## Top {n} Picks Under £25,000

### 1. [Type / Name] — [Location]
**Asking price:** £X,XXX
**Annual turnover:** £XX,XXX (or: not stated)
**Type:** service / digital / retail / franchise / etc
**Why it's interesting:** [2-3 sentences on the opportunity and numbers]
**Risks to check:** [1-2 sentences — honest about what could go wrong]
**Passive potential:** [Can he run it alongside a job? What would day-to-day look like?]
**Link:** [full URL]

---
[repeat for each of the top {n} picks]

## Also Worth a Glance
[3-5 bullet points of honourable mentions with one-line reason]

## First-Time Buyer Tips
[4-5 practical due diligence bullets — what to ask the seller before paying]
=== BIZ DIGEST END ===

=== BIZ JSON START ===
[
  {{
    "name": "short business name or type",
    "price": 12500,
    "price_str": "£12,500",
    "location": "London",
    "turnover": "£45,000",
    "type": "cleaning franchise",
    "passive_score": 7,
    "value_score": 8,
    "overall_score": 8,
    "link": "https://..."
  }}
]
=== BIZ JSON END ===
"""


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — ANALYSE WITH CLAUDE
# ─────────────────────────────────────────────────────────────────────────────

def analyse(listings_text: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set.\n"
            "  → Add your key to .env (get it from console.anthropic.com)"
        )

    system   = BIZ_SYSTEM.format(n=TOP_N, date=TODAY)
    user_msg = (
        f"Today is {TODAY}. Analyse these UK business listings and produce "
        f"the digest + JSON for the top {TOP_N} picks.\n\n"
        f"{listings_text}"
    )

    client   = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model      = CLAUDE_MODEL,
        max_tokens = 6000,
        system     = system,
        messages   = [{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — PARSE OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def parse_output(output: str) -> tuple[str, list[dict]]:
    digest = ""
    m = re.search(r"=== BIZ DIGEST START ===(.*?)=== BIZ DIGEST END ===", output, re.DOTALL)
    if m:
        digest = m.group(1).strip()

    picks: list[dict] = []
    m = re.search(r"=== BIZ JSON START ===(.*?)=== BIZ JSON END ===", output, re.DOTALL)
    if m:
        try:
            picks = json.loads(m.group(1).strip())
        except json.JSONDecodeError as e:
            print(f"  ⚠  Could not parse BIZ JSON: {e}")

    return digest, picks


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — EMAIL
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_HTML = """\
<!doctype html>
<html>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;
             padding:24px;color:#222">

<h2 style="color:#1a7f3c;border-bottom:2px solid #1a7f3c;padding-bottom:8px">
  UK Business Opportunities — {date}
</h2>

<table style="width:100%;border-collapse:collapse;margin-bottom:20px">
  <tr>
    <td style="padding:8px 12px;background:#f0faf4;border-radius:6px;font-size:14px">
      💼 <strong>{n_scraped} listings</strong> scraped &amp; filtered (under £{max_price:,})<br>
      🏆 <strong>Top {n_top} picks</strong> ranked by investment potential<br>
      📂 Saved to <code>business-opps/{date}-biz-digest.md</code>
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
  <em>Sent by your Business Opportunity Finder. Run again anytime: python3 biz_agent.py</em>
</p>
</body>
</html>
"""


def send_email(digest: str, n_scraped: int, n_top: int) -> None:
    if not GMAIL_APP_PASSWORD:
        print("  ⚠  GMAIL_APP_PASSWORD not set — skipping email.")
        print("     Add GMAIL_APP_PASSWORD to .env to enable emails.")
        return

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"Business Opps {TODAY} — {n_top} picks under £{MAX_PRICE:,}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = EMAIL_TO

    html = EMAIL_HTML.format(
        date=TODAY, digest=digest,
        n_scraped=n_scraped, n_top=n_top,
        max_price=MAX_PRICE,
    )
    msg.attach(MIMEText(digest, "plain"))
    msg.attach(MIMEText(html,   "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_ADDRESS, EMAIL_TO, msg.as_string())

    print(f"  ✅ email sent  →  {EMAIL_TO}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — FILE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ saved  →  {path.relative_to(BASE)}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'═'*60}")
    print(f"  BUSINESS OPP FINDER  ·  {TODAY}  ·  {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Budget: under £{MAX_PRICE:,}  ·  Top {TOP_N} picks")
    print(f"{'═'*60}\n")

    # Step 1 — Scrape business listings
    print("Step 1 / 4  →  scraping UK business-for-sale sites …")
    from biz_scraper import scrape_all, format_for_claude
    listings = scrape_all(max_price=MAX_PRICE)

    if not listings:
        print("  ⚠  No listings found. Sites may have changed — check biz_scraper.py")
        return

    listings_text = format_for_claude(listings, limit=60)

    # Step 2 — Analyse with Claude
    print(f"\nStep 2 / 4  →  analysing {len(listings)} listings with Claude (~45 sec) …")
    raw = analyse(listings_text)

    # Step 3 — Parse + save
    print("\nStep 3 / 4  →  parsing + saving …")
    digest, picks = parse_output(raw)

    if not digest:
        print("  ⚠  Digest delimiters not found — saving raw output")
        digest = raw

    save(BASE / "business-opps" / f"{TODAY}-biz-digest.md", digest)

    if picks:
        save(
            BASE / "business-opps" / f"{TODAY}-biz-picks.json",
            json.dumps(picks, indent=2),
        )

    print(f"  → {len(picks)} top picks identified")

    # Step 4 — Email
    print("\nStep 4 / 4  →  sending email …")
    send_email(digest, len(listings), len(picks))

    print(f"\n{'═'*60}")
    print(f"  DONE")
    print(f"  • {len(listings)} listings scraped from 3 UK sites")
    print(f"  • {len(picks)} top picks ranked by investment potential")
    print(f"  • digest → business-opps/{TODAY}-biz-digest.md")
    print(f"  • {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
