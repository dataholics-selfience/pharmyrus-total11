# Pharmyrus v3.1 HOTFIX - Complete Patent Intelligence API

## 🔧 CRITICAL FIXES

### Bug #1: WIPO worldwide_applications null
**FIXED**: Added complete National Phase tab extraction
- Clicks "National Phase" tab with 5 selector strategies
- Parses worldwide applications table (filing_date, country_code, application_number, legal_status)
- Groups by year with 70+ applications per patent

### Bug #2: WO discovery returning empty []
**FIXED**: Implemented 20+ parallel queries
- Year-based searches (2011-2024)
- Dev code searches
- Company-specific searches
- Improved regex extraction: `WO[\s-]?(\d{4})[\s/]?(\d{6})`

### Bug #3: Local crawler not being used
**FIXED**: Pipeline now uses local WIPOCrawler
- No external API calls
- Complete data extraction
- Exponential backoff retry system

## 🚀 DEPLOYMENT

### Railway Deployment
1. Upload `pharmyrus-v3.1-HOTFIX.zip` to Railway
2. Railway auto-detects `runtime.txt` → Python 3.11.9
3. Installs dependencies from `requirements.txt`
4. Executes `Procfile` → Installs Chromium + starts API

### API Endpoints

**WIPO Patent Details**
```bash
GET /api/v1/wipo/{wo_number}?country=BR
```

**Molecule Search**
```bash
GET /api/v1/search/{molecule}?country=BR&limit=20
```

**Batch Search**
```bash
POST /api/v1/batch/search
{"molecules": ["darolutamide", "olaparib"], "country": "BR", "limit": 10}
```

**Test Endpoint**
```bash
GET /test/{wo_number}
```

## 📋 FILES

- `runtime.txt` → Forces Python 3.11.9 (Railway requirement)
- `requirements.txt` → Updated dependencies (Python 3.11 compatible)
- `Procfile` → Deployment command
- `src/wipo_crawler.py` → Complete WIPO extraction with worldwide_applications
- `src/pipeline_service.py` → Full pipeline with 20+ WO queries
- `src/api_service.py` → FastAPI endpoints
- `src/batch_service.py` → Batch processing
- `src/crawler_pool.py` → Crawler pool manager

## 🧪 TESTING

```bash
# Test 1: WIPO endpoint with BR filter
curl "https://YOUR-APP.up.railway.app/api/v1/wipo/WO2016168716?country=BR"

# Test 2: Molecule search
curl "https://YOUR-APP.up.railway.app/api/v1/search/darolutamide?limit=5"

# Test 3: Reference implementation
curl "https://YOUR-APP.up.railway.app/test/WO2011051540"
```

## 📊 EXPECTED RESULTS

### Before (v3.0)
```json
{
  "titular": null,
  "datas": null,
  "worldwide_applications": {},
  "wo_patents": []
}
```

### After (v3.1 HOTFIX)
```json
{
  "titular": "Orion Corporation",
  "datas": {
    "deposito": "2016-04-20",
    "publicacao": "2016-10-27"
  },
  "worldwide_applications": {
    "2016": [{"country_code": "BR", "filing_date": "2017-10-19", ...}],
    "2017": [...]
  },
  "wo_patents": [
    {"publication_number": "WO2016168716", ...}
  ]
}
```

## ⚙️ CONFIGURATION

### Python Version
- **Enforced**: Python 3.11.9 via `runtime.txt`
- Railway default is 3.13 which is incompatible

### Dependencies
All dependencies updated to Python 3.11+ compatible versions:
- fastapi==0.115.5
- uvicorn[standard]==0.32.1
- playwright==1.49.0
- aiohttp==3.11.11
- pydantic==2.10.5

## 📝 VERSION HISTORY

- **v3.1 HOTFIX** (2024-12-10): Fixed 3 critical bugs
- **v3.0 BATCH FINAL**: Initial batch processing
- **v2.x**: Development versions

## 🆘 TROUBLESHOOTING

**Build fails with greenlet/pydantic errors**
→ Ensure `runtime.txt` exists with `python-3.11.9`

**Empty worldwide_applications**
→ Check WIPO Patentscope site is accessible
→ Review debug.selectors_found in response

**No WO patents found**
→ Increase limit parameter
→ Check molecule name spelling

## 📞 SUPPORT

Check logs in Railway dashboard for detailed debug information.
All responses include `debug` metadata for troubleshooting.
