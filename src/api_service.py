from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
import logging
import sys

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import after logging setup
from .wipo_crawler import WIPOCrawler
from .crawler_pool import crawler_pool
from .pipeline_service import pipeline_search

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("🚀 Pharmyrus v3.3 MINIMAL-DEBUG STARTING")
    logger.info("=" * 60)
    
    try:
        logger.info("📝 Step 1: Initializing crawler pool...")
        await crawler_pool.initialize()
        logger.info("✅ Step 1 COMPLETE: Crawler pool initialized")
        
        logger.info("=" * 60)
        logger.info("✅ API READY!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"❌ STARTUP FAILED: {e}")
        logger.exception("Full traceback:")
        raise
    
    yield
    
    logger.info("🛑 Shutting down...")
    try:
        await crawler_pool.close()
        logger.info("✅ Shutdown complete")
    except Exception as e:
        logger.error(f"⚠️ Shutdown error: {e}")

app = FastAPI(title="Pharmyrus v3.3 MINIMAL-DEBUG", lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "service": "Pharmyrus WIPO Crawler",
        "version": "3.3.0-MINIMAL-DEBUG",
        "status": "running",
        "endpoints": ["/health", "/test/{wo_number}", "/api/v1/wipo/{wo_number}"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.3.0-MINIMAL-DEBUG",
        "crawlers": len(crawler_pool.crawlers)
    }

@app.get("/test/{wo_number}")
async def test_wo(wo_number: str):
    logger.info(f"🧪 Testing WO: {wo_number}")
    
    try:
        crawler = crawler_pool.get_crawler()
        if not crawler:
            return {"test": "FAILED", "error": "No crawler available"}
        
        result = await crawler.fetch_patent(wo_number)
        
        return {
            "test": "SUCCESS" if not result.get('erro') else "FAILED",
            "wo_number": wo_number,
            "has_title": bool(result.get('titulo')),
            "has_applicant": bool(result.get('titular')),
            "worldwide_apps": result.get('debug', {}).get('total_worldwide_apps', 0),
            "countries": result.get('debug', {}).get('countries_found', 0),
            "debug": result.get('debug', {}),
            "full_data": result
        }
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return {"test": "FAILED", "error": str(e)}

@app.get("/api/v1/wipo/{wo_number}")
async def get_wipo(wo_number: str, country: str = Query(None)):
    try:
        crawler = crawler_pool.get_crawler()
        if not crawler:
            return {"erro": "No crawler available"}
        
        result = await crawler.fetch_patent(wo_number)
        
        if country:
            result['filtered_country'] = country
        
        return result
    except Exception as e:
        logger.error(f"❌ WIPO fetch failed: {e}")
        return {"erro": str(e)}

@app.get("/api/v1/search/{molecule}")
async def search_molecule(molecule: str, country: str = Query(None), limit: int = Query(5)):
    try:
        result = await pipeline_search(molecule, max_wos=limit)
        
        if country and country == 'BR':
            result['br_patents'] = [p for p in result.get('br_patents', []) if 'BR' in str(p)]
        
        return result
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return {"erro": str(e)}

logger.info("📦 API module loaded successfully")
