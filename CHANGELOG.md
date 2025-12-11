# Changelog - Pharmyrus WIPO Crawler

## v3.3.0-MINIMAL-DEBUG (2025-12-11) 🔬

### 🎯 Critical Fix: ROLLBACK to v3.1 Baseline

**Problem Identified:**
- v3.2 ULTRADEBUG made extraction WORSE than v3.1
- v3.1: title ✅, abstract ✅, worldwide ❌
- v3.2: title ❌, abstract ❌, worldwide ❌ (REGRESSION!)

**Root Cause:**
- v3.2 changed validation logic and selectors
- Broke what was already working in v3.1

**Solution:**
- ROLLBACK to v3.1 extraction code (baseline that worked)
- ADD ONLY enhanced logging to diagnose worldwide issue
- NO changes to selectors, validation, or core logic

### ✨ Changes from v3.1

**Added:**
- Step-by-step logging in `_extract_worldwide_applications`:
  - "📝 STEP 1: Looking for National Phase tab..."
  - "📝 STEP 2: Waiting 4 seconds for AJAX load..."
  - "📝 STEP 3: Searching for table..."
  - "📝 STEP 4: Parsing N rows..."
- HTML content length logging when table not found
- Word 'national' presence check in HTML
- Detailed selector success/failure logging

**Unchanged (preserved from v3.1):**
- All extraction methods
- All selectors (40+ strategies)
- Validation logic (flexible, accepts ANY field)
- Wait times (4s after tab click)
- Click strategies
- Data parsing logic

### 📊 Expected Results

**Baseline (v3.1 HOTFIX):**
- Title extraction: ✅ SUCCESS
- Abstract extraction: ✅ SUCCESS
- Applicant extraction: ✅ SUCCESS
- Worldwide applications: ❌ 0 apps (needs debugging)

**v3.3 MINIMAL-DEBUG:**
- Title extraction: ✅ SUCCESS (same as v3.1)
- Abstract extraction: ✅ SUCCESS (same as v3.1)
- Applicant extraction: ✅ SUCCESS (same as v3.1)
- Worldwide applications: 🔍 DEBUGGING with enhanced logs

### 🐛 Known Issues

**Issue #1: Worldwide Applications = 0**
- Tab click succeeds
- 4 second wait occurs
- Table extraction returns 0 rows
- **Root cause**: Unknown (need logs from v3.3 to diagnose)
- **Status**: Under investigation with enhanced logging

**Possible causes:**
1. Table selector doesn't match WIPO HTML structure
2. AJAX content not fully loaded after 4s wait
3. Table structure changed on WIPO side
4. Row parsing logic mismatch

---

## v3.2.0-ULTRADEBUG (2025-12-11) ❌ ABANDONED

### ⚠️ Regression - Made Extraction WORSE

**Problems:**
- Title extraction: ❌ FAILED (was working in v3.1!)
- Abstract extraction: ❌ FAILED (was working in v3.1!)
- Worldwide applications: ❌ Still 0

**Changes (caused regression):**
- Modified validation logic → too strict
- Changed selector strategies → broke existing selectors
- Added 8s waits → didn't help
- Added screenshots → performance impact
- Added 10+ new table selectors → overcomplicated

**Conclusion:**
- Changes were too aggressive
- Broke baseline functionality
- Abandoned in favor of v3.3 rollback approach

---

## v3.1.0-HOTFIX (2025-12-10) ✅ Baseline

### ✨ What Worked

**Successful extraction:**
- Title: ✅ YES (h3.tab_title selector)
- Abstract: ✅ YES (div.abstract selector)
- Applicant: ✅ YES (table row parsing)
- Dates: ✅ 2/3 extracted (priority, filing)

**Partial success:**
- Worldwide applications: ❌ 0 apps (tab clicks, but table extraction fails)

### 🎯 Strategy

**Flexible validation:**
```python
has_data = any([titulo, resumo, titular, any(datas.values()), worldwide])
```
- Accepts result if ANY field has data
- Prevents false negatives
- **This approach is CORRECT** → preserved in v3.3

### 🐛 Known Issues

**Issue #1: Worldwide Applications = 0**
- Status: Partial - tab click works, table extraction fails
- Impact: Medium - other fields extract successfully
- Priority: High - needed for complete patent data

---

## v3.0.0 (2025-12-09)

### 🎉 Initial Production Release

**Features:**
- Multi-selector strategy (40+ selectors)
- Stealth mode (playwright-stealth)
- Smart waits (network idle, AJAX)
- Crawler pool (2 instances)
- FastAPI service
- Railway deployment ready

**Extraction capabilities:**
- Title
- Abstract
- Applicant/Assignee
- Dates (priority, filing, publication)
- Worldwide applications (National Phase)

**Known limitations:**
- Worldwide extraction inconsistent
- Some WO patents timeout
- No retry logic for failed extractions

---

## Version Comparison Table

| Version | Title | Abstract | Applicant | Worldwide | Status |
|---------|-------|----------|-----------|-----------|--------|
| v3.0    | ✅    | ✅       | ✅        | ⚠️ 0-10%  | Initial |
| v3.1    | ✅    | ✅       | ✅        | ❌ 0      | Stable |
| v3.2    | ❌    | ❌       | ❌        | ❌ 0      | ABANDONED |
| v3.3    | ✅    | ✅       | ✅        | 🔍 Debug  | CURRENT |

**Legend:**
- ✅ Working
- ⚠️ Partial
- ❌ Broken
- 🔍 Under investigation

---

## Next Steps (Post v3.3)

### After Enhanced Logs Analysis

**Scenario A: Table not found**
→ v3.4: Add fallback selectors based on actual HTML
→ v3.4: Add page screenshot before table search
→ v3.4: Inspect network traffic for AJAX calls

**Scenario B: Table found, 0 rows parsed**
→ v3.4: Log first 3 raw rows HTML
→ v3.4: Update column mapping based on actual structure
→ v3.4: Add row-by-row parsing debug

**Scenario C: Tab click fails**
→ v3.4: Add alternative tab selectors
→ v3.4: Try JavaScript click instead of Playwright click
→ v3.4: Add tab click verification

### Long-term Roadmap

**v3.5: Enhanced Extraction**
- Claims extraction
- Legal status extraction  
- Patent family extraction
- Inventor details

**v3.6: Performance**
- Parallel WO processing
- Redis caching
- Connection pooling

**v4.0: Alternative Sources**
- EPO API integration
- Google Patents fallback
- WIPO API (if available)
