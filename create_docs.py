#!/usr/bin/env python3
"""
create_docs.py — Add CV and Cover Letter tabs to the Job Agent Google Sheet.
Run once: python3 create_docs.py

Adds these tabs to your existing Job Agent sheet:
  📋 CV v1 - Finance       ← copy from here for finance roles
  📋 CV v2 - Programmes    ← copy from here for M&E/programmes roles
  📋 CV v3 - Data          ← copy from here for data/research roles
  📝 Cover Letters         ← all cover letters indexed and searchable

On your phone: open the sheet → tap the tab at the bottom → tap a cell → copy.
"""

import glob
import json
import os
import re
from datetime import date
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

BASE                        = Path(__file__).parent
GOOGLE_SHEET_ID             = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")


def _ws_client():
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(GOOGLE_SHEET_ID)


def get_or_create_tab(spreadsheet, title: str, index: int = None):
    """Return existing worksheet or create a new one."""
    try:
        ws = spreadsheet.worksheet(title)
        ws.clear()
        return ws
    except gspread.WorksheetNotFound:
        if index is not None:
            return spreadsheet.add_worksheet(title=title, rows=500, cols=3, index=index)
        return spreadsheet.add_worksheet(title=title, rows=500, cols=3)


def format_header(ws, title: str, subtitle: str, color: dict):
    """Write a big header cell at the top of a tab."""
    ws.update("A1", [[title]])
    ws.update("A2", [[subtitle]])
    ws.format("A1", {
        "backgroundColor": color,
        "textFormat": {"bold": True, "fontSize": 14,
                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    })
    ws.format("A2", {
        "textFormat": {"italic": True, "fontSize": 10,
                       "foregroundColor": {"red": 0.4, "green": 0.4, "blue": 0.4}},
    })


# ─── CV content ───────────────────────────────────────────────────────────────

CV_VERSIONS = {
    "📋 CV v1 - Finance": {
        "subtitle": "Use for: Finance Officer, Finance Assistant, Accounts, Operations Coordinator, ACCA Trainee, Grants Finance",
        "color":    {"red": 0.07, "green": 0.34, "blue": 0.68},
        "sections": [
            ("PERSONAL DETAILS", (
                "Emmanuel Alinafe Maliro\n"
                "London, UK\n"
                "Phone: +44 7470 636663\n"
                "Email: emmanuelmaliro2@gmail.com\n"
                "LinkedIn: linkedin.com/in/emmanuel-alinafe-maliro\n"
                "Right to work: UK dependants visa — no sponsorship needed\n"
                "Available: Immediately"
            )),
            ("PROFILE", (
                "Finance and operations professional with 5 years of NGO delivery experience. "
                "Skilled in financial data management, grant tracking, donor reporting, and "
                "operational coordination. Preparing to register for ACCA (2026). "
                "Proven ability to build financial dashboards, manage budgets, and maintain "
                "data accuracy at scale across GiveDirectly, Ladder to Learning, and "
                "Aquaponics for Life."
            )),
            ("KEY SKILLS", (
                "• Financial data management: Excel (advanced), CODA, Salesforce\n"
                "• Grant tracking, donor reporting, budget reconciliation, KPI dashboards\n"
                "• Operations coordination, workflow design, team leadership (15 staff)\n"
                "• Data tools: Python, SQL, Power BI, Tableau\n"
                "• Preparing for ACCA (2026 registration)"
            )),
            ("EXPERIENCE", (
                "Programmes Consultant — Ladder to Learning, Lilongwe | Jan 2025–Present\n"
                "• Migrated all programme financial and operational data to CODA\n"
                "• Built live donor dashboards tracking KPIs across 1,098 learners\n"
                "• Managed grant reporting and compliance for programme funders\n\n"
                "M&E, Accountability & Learning Manager — Aquaponics for Life | 2024\n"
                "• Managed grant compliance and donor financial reporting\n"
                "• Built real-time financial and operational dashboards for 120 farmers\n"
                "• Coordinated budget tracking across two districts\n\n"
                "Research Associate / Field Manager — GiveDirectly Malawi | 2023–2024\n"
                "• Managed field operations budget and financial reconciliation\n"
                "• Supervised payroll and expense tracking for 15 field officers\n"
                "• Oxford-led study: 10,000 interviews, complex multi-site logistics\n\n"
                "Field Officer (M&E, Ops, Call Centre) — GiveDirectly Malawi | 2020–2023\n"
                "• Maintained financial data records and operational logs\n"
                "• Processed data for donor reporting and compliance audits"
            )),
            ("EDUCATION & CERTIFICATIONS", (
                "• BSc Technical Education (Technology), University of Malawi — Dec 2017\n"
                "• Google Advanced Data Analytics Professional Certificate — Sept 2025\n"
                "• ACCA — preparing to register (2026)\n"
                "• Advanced Certificate in Data Science (Python) — Mar 2021\n"
                "• PMD Pro (Project Management for Development Professionals)\n"
                "• Monitoring and Evaluation in Practice"
            )),
            ("KEY ACHIEVEMENTS", (
                "• Ladder to Learning: +19.2 pp gain in English attainment across 1,098 learners; "
                "built live donor dashboards in CODA.\n"
                "• GiveDirectly: Managed 10,000 interviews (Oxford study); supervised team of 15.\n"
                "• Aquaponics for Life: Built M&E system + real-time dashboards for 120 farmers."
            )),
        ],
    },

    "📋 CV v2 - Programmes": {
        "subtitle": "Use for: M&E Officer, MEAL Officer, Programmes Officer, Grants Officer, Impact Analyst, Research Associate",
        "color":    {"red": 0.13, "green": 0.55, "blue": 0.13},
        "sections": [
            ("PERSONAL DETAILS", (
                "Emmanuel Alinafe Maliro\n"
                "London, UK\n"
                "Phone: +44 7470 636663\n"
                "Email: emmanuelmaliro2@gmail.com\n"
                "LinkedIn: linkedin.com/in/emmanuel-alinafe-maliro\n"
                "Right to work: UK dependants visa — no sponsorship needed\n"
                "Available: Immediately"
            )),
            ("PROFILE", (
                "Programmes and M&E professional with 5 years of NGO delivery experience. "
                "Expertise in M&E framework design, programme evaluation, donor reporting, and "
                "grant management. Proven track record across education, food security, and "
                "humanitarian research sectors. Google Advanced Data Analytics certified."
            )),
            ("KEY SKILLS", (
                "• M&E framework design, logframe development, theory of change\n"
                "• Programme evaluation, impact assessment, MEAL systems\n"
                "• Donor reporting, grant tracking, stakeholder engagement\n"
                "• Survey design: SurveyCTO, Taroworks; tools: Stata, Python, SQL\n"
                "• Dashboards: Power BI, Tableau, CODA\n"
                "• Team leadership: managed 15 field officers"
            )),
            ("EXPERIENCE", (
                "Programmes Consultant — Ladder to Learning, Lilongwe | Jan 2025–Present\n"
                "• Delivered +19.2 pp improvement in English attainment (1,098 learners)\n"
                "• Designed M&E framework; built live donor KPI dashboards in CODA\n"
                "• Led stakeholder reporting to donors and government partners\n\n"
                "M&E, Accountability & Learning Manager — Aquaponics for Life | 2024\n"
                "• Built end-to-end M&E system for 120 smallholder farmers\n"
                "• Developed real-time dashboards on water quality, production, outcomes\n"
                "• Led accountability and learning processes across the programme\n\n"
                "Programmes and Research Manager — Phukila Malawi | 2023–2024\n"
                "• Managed programme delivery, M&E, and stakeholder coordination\n"
                "• Designed research frameworks and managed data collection\n\n"
                "Research Associate / Field Manager — GiveDirectly Malawi | 2023–2024\n"
                "• Managed Oxford-led consumption survey (10,000 interviews)\n"
                "• Supervised 15 field officers across phone and face-to-face data collection\n\n"
                "Field Officer (M&E, Ops, Call Centre) — GiveDirectly Malawi | 2020–2023\n"
                "• Collected, cleaned, and validated programme data at scale\n"
                "• Contributed to M&E reporting and donor compliance"
            )),
            ("EDUCATION & CERTIFICATIONS", (
                "• BSc Technical Education (Technology), University of Malawi — Dec 2017\n"
                "• Google Advanced Data Analytics Professional Certificate — Sept 2025\n"
                "• ACCA — preparing to register (2026)\n"
                "• Advanced Certificate in Data Science (Python) — Mar 2021\n"
                "• PMD Pro (Project Management for Development Professionals)\n"
                "• Monitoring and Evaluation in Practice"
            )),
        ],
    },

    "📋 CV v3 - Data": {
        "subtitle": "Use for: Data Analyst, Research Analyst, Data Officer, BI Analyst, Reporting Analyst, Data Coordinator",
        "color":    {"red": 0.60, "green": 0.20, "blue": 0.60},
        "sections": [
            ("PERSONAL DETAILS", (
                "Emmanuel Alinafe Maliro\n"
                "London, UK\n"
                "Phone: +44 7470 636663\n"
                "Email: emmanuelmaliro2@gmail.com\n"
                "LinkedIn: linkedin.com/in/emmanuel-alinafe-maliro\n"
                "Right to work: UK dependants visa — no sponsorship needed\n"
                "Available: Immediately"
            )),
            ("PROFILE", (
                "Data and research professional with 5 years of real-world analytics experience. "
                "Google Advanced Data Analytics certified. Skilled in Python, SQL, Power BI, "
                "Tableau, and dashboard development. Proven ability to turn complex field data "
                "into clear insights for decision-makers across GiveDirectly, Aquaponics for Life, "
                "and Ladder to Learning."
            )),
            ("KEY SKILLS", (
                "• Languages: Python (pandas, numpy, matplotlib, scikit-learn), SQL, Stata\n"
                "• Visualisation: Power BI, Tableau, CODA, Excel (advanced)\n"
                "• Data collection: SurveyCTO, Taroworks, Salesforce\n"
                "• Statistical analysis, data cleaning, data pipeline design\n"
                "• Research methods: survey design, sampling, field data management\n"
                "• Google Advanced Data Analytics Professional Certificate (2025)"
            )),
            ("EXPERIENCE", (
                "Programmes Consultant — Ladder to Learning, Lilongwe | Jan 2025–Present\n"
                "• Built live donor dashboards in CODA (KPIs across 1,098 learners)\n"
                "• Migrated all programme data systems; designed data collection workflows\n"
                "• Analysed attainment data: +19.2 pp improvement attributed to programme\n\n"
                "M&E, Accountability & Learning Manager — Aquaponics for Life | 2024\n"
                "• Built real-time dashboards for 120 farmers (water quality, production)\n"
                "• Managed end-to-end data pipeline from SurveyCTO collection to reporting\n"
                "• Statistical analysis of smallholder outcomes across two districts\n\n"
                "Research Associate / Field Manager — GiveDirectly Malawi | 2023–2024\n"
                "• Managed data collection for Oxford consumption survey (10,000 interviews)\n"
                "• Supervised quality control, cleaning, and validation for academic outputs\n\n"
                "Field Officer (M&E, Ops, Call Centre) — GiveDirectly Malawi | 2020–2023\n"
                "• Collected and cleaned large-scale survey datasets\n"
                "• Maintained database accuracy across phone and field data systems"
            )),
            ("EDUCATION & CERTIFICATIONS", (
                "• BSc Technical Education (Technology), University of Malawi — Dec 2017\n"
                "• Google Advanced Data Analytics Professional Certificate — Sept 2025\n"
                "• ACCA — preparing to register (2026)\n"
                "• Advanced Certificate in Data Science (Python) — Mar 2021\n"
                "• PMD Pro (Project Management for Development Professionals)\n"
                "• Monitoring and Evaluation in Practice"
            )),
        ],
    },
}


# ─── Build tabs ───────────────────────────────────────────────────────────────

def build_cv_tab(spreadsheet, tab_name: str, config: dict):
    ws = get_or_create_tab(spreadsheet, tab_name)
    format_header(ws, tab_name, config["subtitle"], config["color"])

    rows = [[""], [""]]   # blank rows after header
    for section_title, content in config["sections"]:
        rows.append([f"── {section_title} ──"])
        rows.append([content])
        rows.append([""])

    ws.update(f"A3:A{len(rows)+3}", [[r[0]] for r in rows],
              value_input_option="RAW")

    # Wide column A so text wraps nicely
    ws.spreadsheet.batch_update({"requests": [{
        "updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 700},
            "fields": "pixelSize",
        }
    }]})
    # Wrap text in all cells
    ws.format("A1:A500", {"wrapStrategy": "WRAP"})
    return ws


def build_cover_letters_tab(spreadsheet):
    ws = get_or_create_tab(spreadsheet, "📝 Cover Letters")

    # Header
    ws.update("A1:D1", [["Date", "Role", "Employer", "Cover Letter Text"]])
    ws.format("A1:D1", {
        "backgroundColor": {"red": 0.95, "green": 0.60, "blue": 0.07},
        "textFormat": {"bold": True,
                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
    })

    # Load all cover letter files
    cl_files = sorted(glob.glob(str(BASE / "cv-variants" / "*.md")), reverse=True)
    rows = []
    for fpath in cl_files:
        stem  = Path(fpath).stem          # 2026-06-02_rsbc-finance-officer_cover
        parts = stem.split("_", 2)        # ['2026-06-02', 'rsbc-finance-officer', 'cover']
        date_str = parts[0] if parts else ""
        slug     = parts[1].replace("-", " ").title() if len(parts) > 1 else stem
        text     = Path(fpath).read_text(encoding="utf-8")

        # Try to extract employer from the cover letter text
        employer_match = re.search(r'(?:Dear|To)\s+(?:the\s+)?(.+?)\s+(?:Team|Hiring|Recruitment)',
                                   text, re.IGNORECASE)
        employer = employer_match.group(1) if employer_match else ""

        rows.append([date_str, slug, employer, text])

    if rows:
        ws.update(f"A2:D{len(rows)+1}", rows, value_input_option="RAW")

    # Column widths: Date=90, Role=200, Employer=150, Text=550
    ws.spreadsheet.batch_update({"requests": [
        {"updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS",
                      "startIndex": i, "endIndex": i+1},
            "properties": {"pixelSize": w},
            "fields": "pixelSize",
        }}
        for i, w in enumerate([90, 200, 150, 550])
    ]})
    ws.format("A1:D500", {"wrapStrategy": "WRAP"})

    # Freeze header
    ws.spreadsheet.batch_update({"requests": [{
        "updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }
    }]})

    return ws, len(rows)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("❌  GOOGLE_SERVICE_ACCOUNT_JSON not set in .env"); return
    if not GOOGLE_SHEET_ID:
        print("❌  GOOGLE_SHEET_ID not set in .env"); return

    print("\n" + "═"*58)
    print("  BUILDING SHEET TABS")
    print("═"*58 + "\n")

    spreadsheet = _ws_client()

    # ── CV tabs ────────────────────────────────────────────────────────────────
    print("📋 Creating CV tabs…")
    for i, (tab_name, config) in enumerate(CV_VERSIONS.items(), start=1):
        build_cv_tab(spreadsheet, tab_name, config)
        print(f"   ✅ {tab_name}")

    # ── Cover Letters tab ─────────────────────────────────────────────────────
    print("\n📝 Creating Cover Letters tab…")
    _, n_covers = build_cover_letters_tab(spreadsheet)
    print(f"   ✅ {n_covers} cover letters loaded")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"\n{'═'*58}")
    print("  DONE — open your sheet to see the new tabs")
    print(f"{'═'*58}")
    print()
    print(f"  🔗 https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}")
    print()
    print("  📱 On your phone:")
    print("  1. Open the Job Agent sheet")
    print("  2. Scroll right along the bottom tab bar to find:")
    print("     • 📋 CV v1 - Finance")
    print("     • 📋 CV v2 - Programmes")
    print("     • 📋 CV v3 - Data")
    print("     • 📝 Cover Letters")
    print("  3. Tap a cell → long-press → Copy")
    print()
    print("  ⚠  These CVs are based on your profile.md.")
    print("     Update them with your full CV details when you have a moment.")
    print()


if __name__ == "__main__":
    main()
