"""
API Service v3.1 HOTFIX - FastAPI Patent Intelligence Service
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
from datetime import datetime

from .wipo_crawler import WIPOCrawler
from .crawler_pool import CrawlerPool
from .pipeline_service import PipelineService
from .batch_service import BatchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pharmyrus v3.1 HOTFIX",
    version="3.1.0-HOTFIX",
    description="Patent Intelligence API with complete worldwide data extraction"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

crawler_pool = CrawlerPool(pool_size=3)
pipeline = PipelineService()
batch = BatchService()

@app.on_event("startup")
async def startup():
    logger.info("🚀 Pharmyrus WIPO API iniciando...")
    await crawler_pool.initialize()
    logger.info("✅ API pronta!")

@app.on_event("shutdown")
async def shutdown():
    await crawler_pool.close()

@app.get("/")
async def root():
    return {
        "service": "Pharmyrus v3.1 HOTFIX",
        "version": "3.1.0-HOTFIX",
        "status": "operational",
        "fixes": [
            "WIPO worldwide_applications extraction",
            "WO discovery with 20+ parallel sources",
            "Local crawler integration",
            "Complete debug system"
        ],
        "endpoints": {
            "wipo": "/api/v1/wipo/{wo_number}",
            "search": "/api/v1/search/{molecule}",
            "batch": "/api/v1/batch/search",
            "test": "/test/{wo_number}"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/wipo/{wo_number}")
async def get_wipo_patent(wo_number: str, country: Optional[str] = Query(None)):
    try:
        data = await crawler_pool.fetch_patent(wo_number)
        
        if not data or data.get('erro'):
            raise HTTPException(status_code=404, detail=f"Patent {wo_number} not found")
        
        if country:
            worldwide = data.get('worldwide_applications', {})
            filtered = {}
            for year, apps in worldwide.items():
                filtered_apps = [app for app in apps if app.get('country_code') == country]
                if filtered_apps:
                    filtered[year] = filtered_apps
            data['worldwide_applications'] = filtered
            data['country_filter_applied'] = country
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/search/{molecule}")
async def search_molecule(
    molecule: str,
    country: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50)
):
    try:
        result = await pipeline.execute_full_pipeline(
            molecule=molecule,
            country_filter=country,
            limit=limit
        )
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/batch/search")
async def batch_search(request: dict):
    try:
        molecules = request.get("molecules", [])
        if not molecules:
            raise HTTPException(status_code=400, detail="molecules list required")
        
        result = await batch.process_batch(
            molecules=molecules,
            country_filter=request.get("country"),
            limit=request.get("limit", 10)
        )
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test/{wo_number}")
async def test_endpoint(wo_number: str):
    try:
        async with WIPOCrawler(max_retries=3, timeout=60000, headless=True) as crawler:
            data = await crawler.fetch_patent(wo_number)
        
        br_patents = []
        for year, apps in data.get('worldwide_applications', {}).items():
            for app in apps:
                if app.get('country_code') == 'BR':
                    br_patents.append({
                        "number": app.get('application_number', ''),
                        "filing_date": app.get('filing_date', ''),
                        "legal_status": app.get('legal_status', ''),
                        "year": year
                    })
        
        return {
            "wo_number": wo_number,
            "title": data.get('titulo'),
            "applicant": data.get('titular'),
            "worldwide_applications": data.get('worldwide_applications'),
            "br_patents": br_patents,
            "debug": data.get('debug')
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
