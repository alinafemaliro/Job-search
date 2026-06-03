"""
sheets.py — Google Sheets integration for Job Agent
─────────────────────────────────────────────────────────────────────────────
Writes each job to a Google Sheet so you can apply from your phone.

Sheet columns:
  A Date       B Title      C Employer    D Location   E Salary
  F Deadline   G Status     H Apply Link  I CV to Use
  J Key Points K Cover Letter            L Notes (yours)

CV versions:
  Emmanuel_Maliro_v1_Finance     → finance, accounts, operations, grants finance
  Emmanuel_Maliro_v2_Programmes  → M&E, MEAL, programmes, grants management
  Emmanuel_Maliro_v3_Data        → data analyst, research, BI, reporting
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
from datetime import date

HEADERS = [
    "Date Added",           # A
    "Job Title",            # B
    "Employer",             # C
    "Location",             # D
    "Salary",               # E
    "Deadline",             # F
    "Status",               # G  ← YOU change this: Pending → Applied → Interview → Rejected
    "Apply Link",           # H  ← tap on phone to open the job
    "CV to Use",            # I  ← which PDF file to attach
    "Key Points",           # J  ← 3 quick notes to tailor your answers
    "Full Cover Letter",    # K  ← copy-paste this into the application
    "Notes",                # L  ← your own notes (e.g. "salary too low", "applied via email")
]

# Column widths in pixels (matches column order above)
COL_WIDTHS = [85, 210, 160, 130, 90, 90, 90, 230, 210, 300, 400, 150]


def _connect(sheet_id: str):
    """Return (gspread_client, worksheet). Reads creds from GOOGLE_SERVICE_ACCOUNT_JSON env var."""
    import gspread
    from google.oauth2.service_account import Credentials

    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set.\n"
            "  See .env.example — Step 3 for setup instructions."
        )

    creds = Credentials.from_service_account_info(
        json.loads(raw),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).sheet1
    return gc, ws


def setup_headers(sheet_id: str) -> None:
    """
    Create column headers with blue formatting and freeze the top row.
    Safe to call every run — skips if the sheet is already set up.
    """
    gc, ws = _connect(sheet_id)

    if ws.row_values(1) == HEADERS:
        return  # already formatted, skip

    ws.update("A1:L1", [HEADERS])

    # Blue header background, white bold text
    ws.format("A1:L1", {
        "backgroundColor": {"red": 0.07, "green": 0.34, "blue": 0.68},
        "textFormat": {
            "bold": True,
            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
        },
        "horizontalAlignment": "CENTER",
    })

    # Freeze top row + set column widths
    sheet_id_int = ws.id
    gc.open_by_key(sheet_id).batch_update({"requests": [
        # Freeze header
        {"updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id_int,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }},
        # Column widths
        *[
            {"updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id_int,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": w},
                "fields": "pixelSize",
            }}
            for i, w in enumerate(COL_WIDTHS)
        ],
    ]})

    print("  ✅ Google Sheet headers created and formatted")


def get_existing_links(sheet_id: str) -> set[str]:
    """Return all Apply Links already in column H (to avoid adding duplicates)."""
    try:
        _, ws = _connect(sheet_id)
        all_rows = ws.get_all_values()
        return {
            row[7] for row in all_rows[1:]
            if len(row) > 7 and row[7].startswith("http")
        }
    except Exception as e:
        print(f"  ⚠  Could not read existing sheet rows: {e}")
        return set()


def append_jobs(sheet_id: str, jobs: list[dict]) -> int:
    """
    Append job rows to the sheet.
    Each job dict needs: title, employer, location, salary, deadline,
                         link, cv_version, key_points, cover_letter
    Returns number of rows added.
    """
    if not jobs:
        return 0

    _, ws = _connect(sheet_id)
    today = date.today().isoformat()

    rows = [
        [
            today,
            j.get("title",         ""),
            j.get("employer",      ""),
            j.get("location",      ""),
            j.get("salary",        ""),
            j.get("deadline",      ""),
            "Pending",              # default status — user updates this
            j.get("link",          ""),
            j.get("cv_version",    ""),
            j.get("key_points",    ""),
            j.get("cover_letter",  ""),
            "",                     # Notes — empty, user fills in
        ]
        for j in jobs
    ]

    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


def sheet_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
