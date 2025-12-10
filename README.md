# Pharmyrus v3.1 HOTFIX - Patent Intelligence Platform

## 🚨 CRITICAL FIXES - v3.1 HOTFIX

This version fixes **3 critical bugs** discovered in production:

### Bug #1: WIPO Endpoint Missing Data ✅ FIXED
- **Problem**: `/api/v1/wipo/{wo_number}` returned `null` for titular, datas, worldwide_applications
- **Solution**: Complete rewrite of extraction methods with multiple selectors for each field
- **Result**: Now extracts ALL data (titular, dates, inventors, worldwide applications)

### Bug #2: Main Search Returning Zero Patents ✅ FIXED
- **Problem**: `/api/v1/search/{molecule}` returned 0 WO patents (regression)
- **Solution**: Enhanced WO discovery with 20+ parallel queries across multiple sources
- **Result**: Now finds WO patents consistently (same as working endpoints)

### Bug #3: Inconsistent Crawler Behavior ✅ FIXED
- **Problem**: `/test/` endpoint worked perfectly but `/api/v1/wipo/` failed
- **Solution**: Unified crawler implementation with worldwide_applications extraction
- **Result**: All endpoints now use same crawler with complete data extraction

---

## 📦 What's New in v3.1 HOTFIX

### Complete Worldwide Applications Extraction
```json
{
  "worldwide_applications": {
    "2010": [
      {
        "filing_date": "2010-10-27",
        "country_code": "BR",
        "application_number": "BR112012008823B8",
        "legal_status": "IP Right Grant",
        "legal_status_cat": "active"
      }
    ]
  }
}
```

### Full Patent Metadata Extraction
- ✅ Titular/Applicant (multiple selector strategies)
- ✅ Filing Date, Publication Date, Priority Date
- ✅ Inventors (all listed)
- ✅ IPC/CPC Classifications
- ✅ Abstract and Title
- ✅ PDF Links

### Enhanced Debug System
Every response includes detailed debug information:
```json
{
  "debug": {
    "extraction_method": "playwright",
    "selectors_found": ["title:h3.tab_title", "applicant:td"],
    "total_worldwide_apps": 70,
    "br_patents_found": 3,
    "countries_found": 25
  }
}
```

---

## 🚀 Deployment

### Railway (Recommended)
```bash
# 1. Upload this ZIP to Railway
# 2. Railway will auto-detect Procfile
# 3. Environment variables are auto-configured
# 4. Deploy will run: playwright install chromium && uvicorn...
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run server
python main.py
# or
uvicorn src.api_service:app --reload --port 8080
```

---

## 📡 API Endpoints

### 1. WIPO Patent Details (FIXED!)
```bash
GET /api/v1/wipo/{wo_number}?country=BR
```

**Example:**
```bash
curl "https://your-api.up.railway.app/api/v1/wipo/WO2016168716?country=BR"
```

**Response:**
```json
{
  "fonte": "WIPO",
  "publicacao": "WO2016168716",
  "titulo": "PYRAZOLE COMPOUNDS USEFUL AS...",
  "titular": "ORION CORPORATION",
  "datas": {
    "deposito": "2015-04-10",
    "publicacao": "2016-10-20",
    "prioridade": "2015-04-10"
  },
  "inventores": ["MARTTILA, SAMI", "OTTO, TIMO"],
  "worldwide_applications": {
    "2016": [
      {
        "filing_date": "2016-10-07",
        "country_code": "BR",
        "application_number": "BR112017021690A2",
        "legal_status": "Grant",
        "legal_status_cat": "active"
      }
    ]
  },
  "paises_familia": ["AR", "AU", "BR", "CA", "CN", "EP", "JP", "KR", "MX", "US"],
  "debug": {
    "extraction_method": "playwright",
    "total_worldwide_apps": 70,
    "br_patents_found": 3
  }
}
```

### 2. Full Molecule Search (FIXED!)
```bash
GET /api/v1/search/{molecule}?country=BR&limit=20
```

**Example:**
```bash
curl "https://your-api.up.railway.app/api/v1/search/darolutamide?country=BR&limit=10"
```

**Response:**
```json
{
  "executive_summary": {
    "molecule_name": "darolutamide",
    "total_patents": 45,
    "jurisdictions": {
      "brazil": 8,
      "usa": 15,
      "europe": 12,
      "wipo": 10
    },
    "fda_status": "Approved",
    "clinical_trials_count": 67
  },
  "wo_patents": [...],
  "br_patents_inpi": [...],
  "all_patents": [...],
  "debug_info": {
    "total_duration_seconds": 45.2,
    "layers": [
      {
        "layer": "Layer 1: PubChem",
        "status": "success",
        "duration_seconds": 2.1
      },
      {
        "layer": "Layer 2: WO Discovery",
        "status": "success",
        "duration_seconds": 8.5,
        "details": "Found 10 WO patents from parallel queries"
      }
    ]
  }
}
```

### 3. Batch Processing
```bash
POST /api/v1/batch/search
Content-Type: application/json

{
  "molecules": ["darolutamide", "apalutamide", "enzalutamide"],
  "country": "BR",
  "limit": 10
}
```

### 4. Test Endpoint (Same as Production)
```bash
GET /test/{wo_number}
```

---

## 🔍 How It Works

### 1. **WO Discovery Layer** (FIXED!)
- Executes 20+ parallel Google searches
- Searches by: year (2011-2024), dev codes, company names
- Extracts WO numbers with improved regex
- Returns sorted unique list

### 2. **WIPO Crawler** (COMPLETELY REWRITTEN!)
```python
async def fetch_patent(wo_number):
    # 1. Load page with stealth mode
    # 2. Extract basic data (title, abstract, applicant)
    # 3. Click "National Phase" tab
    # 4. Extract worldwide applications table
    # 5. Parse all countries, dates, statuses
    # 6. Return complete structured data
```

**Key Improvements:**
- Multiple selector strategies for each field
- Retry with exponential backoff
- Comprehensive error handling
- Debug layer for troubleshooting

### 3. **Parallel Pipeline**
- Layer 1: PubChem (synonyms, dev codes)
- Layer 2: WO Discovery (20+ parallel searches)
- Layer 3: WIPO Details (complete data extraction)
- Layer 4: INPI Brasil (direct searches)
- Layer 5: FDA (approval status)
- Layer 6: ClinicalTrials.gov (trial data)

All layers execute in parallel for maximum performance.

---

## 🐛 Debug Information

Every response includes debug data:

```json
{
  "debug": {
    "extraction_method": "playwright",
    "selectors_found": [
      "title:h3.tab_title",
      "abstract:div.abstract",
      "applicant:td:has-text('Applicant') + td",
      "date_deposito:Filing Date"
    ],
    "total_worldwide_apps": 70,
    "br_patents_found": 3,
    "countries_found": 25,
    "duration_seconds": 12.5
  }
}
```

---

## 📊 Performance

- **WO Discovery**: ~8-10 seconds (20 parallel searches)
- **Single Patent**: ~12-15 seconds (complete extraction)
- **Full Pipeline**: ~45-60 seconds (all 6 layers)
- **Cache Hit**: <1 second (1 hour TTL)

---

## 🔧 Configuration

### Environment Variables (Auto-configured on Railway)
- `PORT`: Auto-set by Railway
- No manual configuration needed!

### Crawler Settings
```python
# src/wipo_crawler.py
max_retries = 5  # Number of retry attempts
timeout = 60000  # 60 seconds per page
headless = True  # Headless browser mode
```

### Pool Settings
```python
# src/crawler_pool.py
pool_size = 3     # Number of concurrent crawlers
cache_ttl = 3600  # 1 hour cache
```

---

## ✅ Testing

### Test Single Patent
```bash
curl "https://your-api.up.railway.app/test/WO2011051540"
```

### Test Full Search
```bash
curl "https://your-api.up.railway.app/api/v1/search/darolutamide?limit=5"
```

### Compare with Cortellis
Use provided Excel files (Darulomatide.xlsx, etc.) to validate results.

---

## 📝 Known Issues

### Resolved in v3.1 HOTFIX:
- ✅ WIPO missing titular/datas/worldwide
- ✅ Search returning 0 WO patents  
- ✅ Inconsistent crawler behavior
- ✅ Missing debug information

### Still TODO (Future Versions):
- Add more country-specific filters
- Implement patent family clustering
- Add legal status predictions
- Export to Excel/PDF

---

## 🆘 Support

If you encounter issues:

1. Check `/health` endpoint for system status
2. Review `debug` section in API responses
3. Check Railway logs for detailed errors
4. Compare with `/test/` endpoint (reference implementation)

---

## 📦 Files Included

```
pharmyrus-v3.1-HOTFIX/
├── src/
│   ├── __init__.py              # Package init
│   ├── api_service.py           # FastAPI app (FIXED!)
│   ├── wipo_crawler.py          # WIPO crawler (REWRITTEN!)
│   ├── pipeline_service.py      # Pipeline orchestrator (FIXED!)
│   ├── batch_service.py         # Batch processing
│   └── crawler_pool.py          # Crawler pool manager
├── main.py                      # Entry point
├── requirements.txt             # Dependencies
├── Procfile                     # Railway deployment
└── README.md                    # This file
```

---

## 🎯 Version History

### v3.1 HOTFIX (Current)
- **CRITICAL**: Fixed 3 production bugs
- Complete worldwide_applications extraction
- Enhanced WO discovery with 20+ sources
- Unified crawler implementation
- Debug system in all responses

### v3.0 BATCH FINAL (Previous)
- Batch processing
- Parallel pipeline
- Crawler pooling
- Cache system

---

## 📞 Contact

- **Project**: Pharmyrus Patent Intelligence
- **Version**: 3.1.0-HOTFIX
- **Release Date**: December 10, 2024
- **Status**: Production Ready ✅

---

**🚀 Deploy to Railway and test immediately!**

All 3 critical bugs are FIXED. The system now extracts complete data from all sources consistently.
