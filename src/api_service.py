"""FastAPI Service v3.1 HOTFIX"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from .crawler_pool import crawler_pool
from .pipeline_service import pipeline_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Pharmyrus WIPO API iniciando...")
    await crawler_pool.initialize()
    logger.info("✅ API pronta!")
    yield
    logger.info("🛑 Encerrando...")
    await crawler_pool.close()

app = FastAPI(
    title="Pharmyrus WIPO API v3.1 HOTFIX",
    version="3.1.0-HOTFIX",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "service": "Pharmyrus WIPO API",
        "version": "3.1.0-HOTFIX",
        "status": "operational",
        "endpoints": {
            "wipo": "/api/v1/wipo/{wo_number}",
            "search": "/api/v1/search/{molecule}",
            "test": "/test/{wo_number}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "crawlers": len(crawler_pool.crawlers),
        "version": "3.1.0-HOTFIX"
    }

@app.get("/api/v1/wipo/{wo_number}")
async def get_wipo_patent(wo_number: str, country: str = None):
    """Fetch single WIPO patent"""
    try:
        crawler = crawler_pool.get_crawler()
        result = await crawler.fetch_patent(wo_number)
        
        if country:
            # Filter worldwide apps by country
            filtered = {}
            for year, apps in result.get('worldwide_applications', {}).items():
                country_apps = [a for a in apps if a.get('country_code') == country.upper()]
                if country_apps:
                    filtered[year] = country_apps
            result['worldwide_applications'] = filtered
            result['filtered_country'] = country.upper()
        
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/search/{molecule}")
async def search_molecule(molecule: str, limit: int = 5):
    """Full pipeline search"""
    try:
        result = await pipeline_search(molecule, max_wos=limit)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test/{wo_number}")
async def test_endpoint(wo_number: str):
    """Quick test endpoint"""
    try:
        crawler = crawler_pool.get_crawler()
        result = await crawler.fetch_patent(wo_number)
        
        return {
            "test": "SUCCESS",
            "wo_number": wo_number,
            "has_title": bool(result.get('titulo')),
            "has_applicant": bool(result.get('titular')),
            "worldwide_apps": sum(len(apps) for apps in result.get('worldwide_applications', {}).values()),
            "countries": len(result.get('paises_familia', [])),
            "debug": result.get('debug', {}),
            "full_data": result
        }
    except Exception as e:
        return {
            "test": "FAILED",
            "error": str(e)
        }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )
