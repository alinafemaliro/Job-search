#!/usr/bin/env python3
"""
catchup.py — Email all recent digests + cover letter list in one go.
Run once: python3 catchup.py
No Anthropic API key or credits needed — reads existing files only.
"""

import glob
import os
import smtplib
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE               = Path(__file__).parent
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS", "alinafemaliro@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_TO           = os.getenv("EMAIL_TO", "alinafemaliro@gmail.com")

# ── How many days back to include ──────────────────────────────────────────
LOOKBACK_DAYS = 14


def recent_digests():
    all_files = sorted(glob.glob(str(BASE / "digests" / "*.md")))
    cutoff    = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    return [f for f in all_files if Path(f).stem >= cutoff]


def cover_letters_for(date_str):
    return sorted(glob.glob(str(BASE / "cv-variants" / f"{date_str}_*.md")))


def send():
    if not GMAIL_APP_PASSWORD:
        print("❌  GMAIL_APP_PASSWORD not set in .env — cannot send email.")
        return

    files = recent_digests()
    if not files:
        print("No recent digests found in digests/ folder.")
        return

    print(f"Found {len(files)} digest(s) to send:")

    sections_plain = []
    sections_html  = []

    for f in reversed(files):           # newest first
        date_str = Path(f).stem.replace("-digest", "")
        covers   = cover_letters_for(date_str)
        content  = Path(f).read_text(encoding="utf-8")

        # plain-text section
        cover_bullets = "\n".join(f"  • {Path(c).name}" for c in covers) or "  (none yet)"
        sections_plain.append(
            f"{'═'*60}\n  DIGEST: {date_str}\n"
            f"  Cover letters ready:\n{cover_bullets}\n{'═'*60}\n\n"
            f"{content}"
        )

        # html section
        cover_html = "".join(f"<li><code>{Path(c).name}</code></li>" for c in covers) or "<li><em>none</em></li>"
        sections_html.append(f"""
<div style="border:2px solid #1a56a0;border-radius:6px;padding:16px;margin:24px 0">
  <h3 style="color:#1a56a0;margin:0 0 8px 0">Digest — {date_str}</h3>
  <p><strong>Cover letters ready:</strong></p>
  <ul style="margin:4px 0 12px 0">{cover_html}</ul>
  <pre style="background:#f5f7fa;padding:12px;border-radius:4px;
              font-size:12px;line-height:1.6;white-space:pre-wrap">{content}</pre>
</div>""")

        print(f"  • {date_str}  ({len(covers)} cover letters)")

    plain_body = "\n\n\n".join(sections_plain)
    html_body  = f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;max-width:720px;margin:0 auto;
                   padding:24px;color:#222">
<h2 style="color:#1a56a0;border-bottom:2px solid #1a56a0;padding-bottom:8px">
  Job Catch-up — {len(files)} digest(s)</h2>
<p>All recent digests are below, newest first.
   Cover letters are saved in <code>cv-variants/</code> on your Mac.</p>
{"".join(sections_html)}
<p style="font-size:12px;color:#888;margin-top:32px">
  Sent by catchup.py — your job agent.</p>
</body></html>"""

    first_date = Path(files[0]).stem.replace("-digest", "")
    last_date  = Path(files[-1]).stem.replace("-digest", "")

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"Job Catch-up: {first_date} → {last_date}  ({len(files)} digests)"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = EMAIL_TO

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    print(f"\nSending to {EMAIL_TO} …")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_ADDRESS, EMAIL_TO, msg.as_string())

    print(f"✅  Catch-up email sent  →  {EMAIL_TO}")
    print(f"   Check your inbox — you'll have all job listings + cover letter names.")
    print(f"   Cover letters are in:  ~/Desktop/job-agent/cv-variants/")


if __name__ == "__main__":
    send()
