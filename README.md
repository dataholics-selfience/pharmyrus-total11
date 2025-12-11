# Pharmyrus v3.3 MINIMAL-DEBUG 🔬

## 🎯 What Changed from v3.1 → v3.3

**v3.1 HOTFIX** (baseline that WORKED):
- ✅ Extracted title correctly
- ✅ Extracted abstract correctly  
- ✅ Extracted applicant correctly
- ❌ Worldwide applications: 0 (tab click worked, table extraction failed)

**v3.3 MINIMAL-DEBUG** (this version):
- ✅ **EXACT SAME extraction logic as v3.1** (baseline that worked!)
- ✅ **ONLY ADDED**: Enhanced step-by-step logging
- ✅ **ONLY ADDED**: HTML content logging at critical points
- ✅ **NO CHANGES** to selectors, validation, or core logic

## 🚨 Critical Fix Applied

**Problem in v3.2**: Changed validation logic → broke title/abstract extraction

**Solution in v3.3**: ROLLBACK to v3.1 baseline + add logging ONLY

## 📊 Expected Results

### Test 1: WO2016168716
```bash
curl https://APP.railway.app/test/WO2016168716
```

**Expected** (based on v3.1 + target data):
```json
{
  "test": "SUCCESS",
  "has_title": true,        ← v3.1 had this ✅
  "has_applicant": true,    ← v3.1 had this ✅
  "worldwide_apps": 70,     ← v3.1 had 0 ❌ (debugging this)
  "countries": 30           ← v3.1 had 0 ❌ (debugging this)
}
```

### Railway Logs - What to Look For

**✅ GOOD Pattern** (title/abstract working):
```
✅ WO2016168716: SUCCESS
   Title: YES (h3.tab_title)
   Resumo: YES (div.abstract)
   Applicant: YES (table_row)
   Dates: 2/3
   Worldwide: ? apps, ? countries  ← Focus here
```

**🔍 DEBUG Pattern** (worldwide extraction):
```
📝 STEP 1: Looking for National Phase tab...
  🎯 Found tab element: a:has-text("National Phase")
  ✅ Clicked: a:has-text("National Phase")
📝 STEP 2: Waiting 4 seconds for AJAX load...
📝 STEP 3: Searching for table...
  ✅ Table found: table tr (71 rows)  ← Should see this!
  OR
  ❌ NO table data found after trying all selectors  ← Current problem
📝 STEP 4: Parsing 70 rows...
📊 Worldwide: 70 apps from 3 years  ← Goal!
```

**If you see**:
- `❌ NO table data found` → Table selectors don't match WIPO structure
- `📄 Page HTML length: X chars` → HTML was captured
- `✅ Word 'national' found in HTML` → Content exists, selector issue
- `⚠️ Word 'national' NOT found in HTML` → Tab click didn't load content

## 🚀 Deployment

### Quick Deploy to Railway

```bash
# Option 1: Direct upload
# Upload pharmyrus-v3.3-MINIMAL-DEBUG.zip to Railway

# Option 2: Git
git init
git add .
git commit -m "v3.3 MINIMAL-DEBUG"
railway up
```

Build time: ~3-4 minutes

### Test Endpoints

```bash
export APP_URL="https://your-app.up.railway.app"

# Health check
curl $APP_URL/health

# Test WO extraction (KEY TEST!)
curl $APP_URL/test/WO2016168716 | jq

# Full WIPO endpoint
curl "$APP_URL/api/v1/wipo/WO2016168716?country=BR" | jq

# Pipeline search
curl "$APP_URL/api/v1/search/darolutamide?country=BR&limit=5" | jq
```

## 🔍 Debug Strategy

### Step 1: Verify Title/Abstract Work
```bash
curl $APP_URL/test/WO2016168716 | jq '.has_title, .has_applicant'
```
**Expected**: `true, true` (v3.1 baseline worked)

### Step 2: Check Worldwide Extraction
```bash
curl $APP_URL/test/WO2016168716 | jq '.worldwide_apps, .debug.worldwide'
```
**Expected**: `70, ["clicked:...", "table:...", "extracted:70"]`

### Step 3: Analyze Logs

**If worldwide = 0**, check Railway logs for:
1. Did tab click succeed? Look for `✅ Clicked:`
2. Did table search run? Look for `📝 STEP 3:`
3. What happened? Look for `✅ Table found:` or `❌ NO table data`
4. Was HTML checked? Look for `📄 Page HTML length:`

### Step 4: Next Actions Based on Logs

**Scenario A**: Tab clicks but table not found
→ WIPO changed HTML structure
→ Need to inspect actual page HTML
→ Update table selectors

**Scenario B**: Tab doesn't click
→ Tab selector changed
→ Add new tab selectors

**Scenario C**: Table found but 0 rows parsed
→ Column mapping issue
→ Log first 3 rows to see format

## 📝 Changelog

### v3.3.0-MINIMAL-DEBUG (2025-12-11)

**ROLLBACK to v3.1 baseline**:
- Restored v3.1 extraction methods (title, abstract, applicant, dates)
- Restored v3.1 validation logic (flexible, accepts ANY data)
- Kept v3.1 selector strategies (40+ selectors)

**Enhanced logging ONLY**:
- Added step-by-step logging in `_extract_worldwide_applications`
- Added HTML content length logging when table not found
- Added word 'national' presence check in HTML
- Added detailed selector success/failure logging

**NO changes to**:
- Selectors
- Wait times
- Click strategies
- Validation logic
- Data parsing

## 🎓 Lessons Learned

**v3.2 mistake**: Changed too much at once
- Modified selectors
- Changed validation
- Added screenshots
- Result: Broke what was working

**v3.3 approach**: Minimal changes
- Keep baseline that worked (v3.1)
- Add ONLY logging
- Debug one issue at a time

## 📞 Support

Provide:
1. Response from `/test/WO2016168716`
2. Railway logs (last 100 lines)
3. Specific error messages

Expected fix: 1-2 iterations based on logs
