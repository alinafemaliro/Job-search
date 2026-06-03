# Target Roles & Search Strategy

This file drives the daily vacancy search. Update keywords and sources as patterns emerge.

## Search categories (all three in scope daily)

### 1. Finance & Operations
**Keywords:** finance assistant, finance officer, operations coordinator, operations officer, operations manager, grants officer, programme finance, finance analyst, ACCA trainee, accounts assistant, bookkeeper, finance administrator, business support officer.

**Must-have match signals:** Excel, financial data, budgeting, grant tracking, reporting, reconciliation, KPI.

### 2. M&E, Grants & Programmes
**Keywords:** monitoring and evaluation, M&E officer, M&E manager, impact analyst, programmes officer, programme coordinator, programme manager, research associate, research officer, learning officer, MEAL officer, grants officer, donor reporting.

**Must-have match signals:** programme evaluation, logframe, theory of change, donor reports, Salesforce, SurveyCTO, Power BI, Tableau, dashboards.

### 3. Data & Research
**Keywords:** data analyst, research analyst, data coordinator, reporting analyst, insights analyst, BI analyst, junior data analyst, data officer.

**Must-have match signals:** Python, SQL, Power BI, Tableau, Excel, dashboards, data cleaning, data visualisation.

## Filters
- **Location:** UK-wide (London, Manchester, Birmingham, Edinburgh, Glasgow, Bristol, Leeds, Cardiff, Belfast, Cambridge, Oxford, fully remote — all eligible).
- **Salary floor:** £25,000+ per year (or pro-rata for part-time). Skip anything below unless it's an ACCA trainee programme.
- **Sponsorship:** skip any listing that requires sponsorship from the employer. Emmanuel has his own right to work.
- **Posted within:** last 3 days preferred, last 7 days acceptable.
- **Contract:** permanent or 6+ month FTC preferred. Skip zero-hours, unpaid, commission-only, MLM.

## Source sites to scan
- **Charity-specific:** charityjob.co.uk, escapethecity.org, jobs.theguardian.com (Charities), cafonline.org/jobs
- **General:** indeed.co.uk, reed.co.uk, totaljobs.com, cv-library.co.uk, linkedin.com/jobs
- **Civil service / research:** civilservicejobs.service.gov.uk, jobs.ac.uk (research roles)
- **Finance-specific:** accaglobal.com/jobs, efinancialcareers.co.uk
- **Impact / development:** devnetjobs.org UK filter, bond.org.uk jobs

## Daily digest format
The agent should produce a morning digest with:
1. **Top 5 matches** — strongest fit, apply today. For each: title, employer, location, salary, deadline, 1-sentence why-it-fits, link, and a draft cover letter attached as a file.
2. **Also worth a look** — up to 10 more roles worth 5-minute consideration. Short bullet per role.
3. **Requires org-website application** — roles where the posting only lives on the employer's careers page. Agent should flag these so Emmanuel can self-apply end of day.
4. **Dedup log** — role IDs already shown in previous digests, to avoid repeats.

## Cover letter tailoring rules
- Length: 250–350 words.
- Paragraph 1: which role + one-sentence pitch matching the JD's headline requirement.
- Paragraph 2: two specific achievements from profile.md quantified with numbers, matched to JD keywords.
- Paragraph 3: reference charity/impact/finance context + ACCA trajectory where relevant.
- Close: immediate availability, right-to-work UK confirmed (dependants visa, no sponsorship needed).
- Sign-off: "Kind regards, Emmanuel Alinafe Maliro" + phone + email.

## Files the agent writes each run
- `digests/YYYY-MM-DD-digest.md` — the daily digest.
- `cv-variants/YYYY-MM-DD_<role-slug>_cover.md` — one cover letter per top-5 role.
- `applied-log/applied.csv` — append a row each time Emmanuel confirms he applied (columns: date, role, employer, source, status).

## What the agent should NOT do
- Do not auto-submit applications anywhere.
- Do not invent job listings — if no matches in category, say so.
- Do not include roles already present in `applied-log/applied.csv` or in a previous digest from the last 14 days.
