# Phase 3 Test Checklist (Extensive Validation)

Use this checklist after any Phase 3 change. Mark each item as Pass/Fail and capture notes.

---

## 0) Test Environment Setup

- [ ] Start app with `streamlit run app.py`
- [ ] Confirm app opens at `http://127.0.0.1:8501`
- [ ] Ensure OpenAI key is configured in `.streamlit/secrets.toml` (optional for AI tests)
- [ ] Confirm demo data exists (jobs visible on Dashboard)

---

## 1) Dashboard Core Behavior

### 1.1 Load & Rendering
- [ ] Dashboard loads without traceback
- [ ] Total jobs, saved jobs, high-match, avg score cards render
- [ ] Job cards show title/company/location/salary/date/source

### 1.2 Filters
- [ ] Min salary filter reduces jobs as expected
- [ ] Max salary filter reduces jobs as expected
- [ ] Remote-only filter shows only remote jobs
- [ ] Company multiselect filters correctly
- [ ] Freshness filter removes older jobs
- [ ] Combined filters produce consistent results

### 1.3 Sorting
- [ ] Best Match sorts by descending match score
- [ ] Newest sorts by posted date descending
- [ ] Highest Salary sorts by top salary descending

### 1.4 Presets
- [ ] Save preset stores current filter/sort state
- [ ] Load preset restores all filter values
- [ ] Delete preset removes it from list
- [ ] Invalid load/delete states show warnings and do not crash

---

## 2) Export Validation (New)

### 2.1 CSV Export
- [ ] Export CSV button enabled when filtered jobs > 0
- [ ] Downloaded CSV opens successfully
- [ ] CSV columns include title/company/location/salary/match/link/source
- [ ] CSV row count matches current filtered jobs count

### 2.2 PDF Export
- [ ] Export PDF button enabled when filtered jobs > 0
- [ ] Downloaded PDF opens successfully
- [ ] PDF includes generated timestamp and total jobs
- [ ] PDF lists each job with match score and salary summary

### 2.3 Edge Cases
- [ ] When no filtered jobs, export buttons are disabled (or safe no-op)
- [ ] Very long links do not break PDF generation

---

## 3) Preferred Companies Scanning

### 3.1 Company Management
- [ ] Add company with valid URL succeeds
- [ ] Add duplicate company warns and blocks
- [ ] Delete company removes it from list
- [ ] Validate URL button reports reachable/unreachable accurately

### 3.2 Scan Single Company
- [ ] Scan single in mock mode completes and persists jobs
- [ ] Scan single in real mode attempts Playwright and falls back if needed
- [ ] Success message reports processed/new/updated counts

### 3.3 Scan All Companies (Parallel, New)
- [ ] Parallel scans slider visible and adjustable
- [ ] Scan all works with parallel=1 (serial-equivalent)
- [ ] Scan all works with parallel=4 or higher
- [ ] Real mode scan all runs without blocking UI permanently
- [ ] If real scraper fails, fallback to mock mode works
- [ ] Persisted jobs appear on Dashboard after completion

### 3.4 California Filter
- [ ] California-only company filter narrows scan targets
- [ ] California-only scan results contain CA locations

---

## 4) Job Alerts (New)

### 4.1 Local Alert Detection
- [ ] Enable Job Alerts in Settings and save
- [ ] Set alert min score and max items
- [ ] Click Check Alerts Now and verify pending jobs found (if available)
- [ ] Alert preview lines show title/company/match

### 4.2 Seen-State Behavior
- [ ] After Check Alerts Now, same jobs are not repeatedly returned
- [ ] New jobs added later can appear in a subsequent alert run
- [ ] Alert state file persists across app restart

### 4.3 Email Delivery (Optional SMTP)
- [ ] With SMTP values configured, Check Alerts Now sends email successfully
- [ ] Email subject/body include expected job summary
- [ ] Missing SMTP settings produce safe message without crash
- [ ] Invalid SMTP credentials produce safe error without crash

---

## 5) Settings + OpenAI

### 5.1 OpenAI Key
- [ ] OpenAI key entry saves for session
- [ ] Key validation passes for valid key
- [ ] Invalid key shows warning but app stays usable

### 5.2 OpenAI Features
- [ ] Dashboard Analyze Match returns score/reasoning
- [ ] Interview Prep generates response text
- [ ] Re-score All Jobs updates metrics and progress UI

### 5.3 Preferences
- [ ] Location/min salary/experience values save for session
- [ ] Blacklist input saves and reloads in session

---

## 6) Profile + Resume

- [ ] PDF resume upload parses without crash
- [ ] DOCX resume upload parses without crash
- [ ] Parsed skills/summary can be edited and saved
- [ ] Skills chips render correctly
- [ ] Reloading app keeps profile persisted from DB

---

## 7) Add Job Page

### 7.1 URL Mode
- [ ] Mock URL scrape creates job and persists
- [ ] Real URL scrape attempts Playwright and fallback works
- [ ] Added job appears on Dashboard

### 7.2 Text Mode
- [ ] Paste JD + optional company creates job
- [ ] Salary parsing works when salary text provided
- [ ] Job persists and appears on Dashboard

---

## 8) Data Integrity / Persistence

- [ ] Restart app; jobs remain persisted
- [ ] Restart app; profile remains persisted
- [ ] Restart app; preset file remains correct JSON
- [ ] Restart app; alerts state remains consistent

---

## 9) Performance / Stress Pass

- [ ] Run Scan All 3 times back-to-back without crash
- [ ] Test with max companies and max jobs per company
- [ ] Test parallel scans at highest setting (8)
- [ ] Dashboard remains responsive with larger job count
- [ ] Export CSV/PDF works with 100+ jobs

---

## 10) Regression Safety

- [ ] No Streamlit secrets missing crash
- [ ] No uncaught traceback on main pages
- [ ] All navigation buttons work
- [ ] No syntax/runtime errors in terminal logs during normal flow

---

## Defect Log Template

For each failure, capture:

- Test ID / Section:
- Steps performed:
- Expected result:
- Actual result:
- Screenshot/log:
- Severity: Critical / High / Medium / Low
- Proposed fix:

---

## Release Gate (Phase 3 Complete)

Ship-ready only when all are true:

- [ ] All critical tests pass
- [ ] No unresolved high-severity defects
- [ ] Scan All (parallel) stable in both real and fallback paths
- [ ] Alerts and exports validated end-to-end
- [ ] OpenAI optional path validated with valid key
