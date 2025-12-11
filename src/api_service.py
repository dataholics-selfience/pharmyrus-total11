from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
import logging
from .wipo_crawler import WIPOCrawler
from .crawler_pool import crawler_pool
from .pipeline_service import pipeline_search

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Pharmyrus v3.3 MINIMAL-DEBUG iniciando...")
    await crawler_pool.initialize()
    logger.info("✅ API pronta!")
    yield
    await crawler_pool.close()

app = FastAPI(title="Pharmyrus v3.3 MINIMAL-DEBUG", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.3.0-MINIMAL-DEBUG", "crawlers": len(crawler_pool.crawlers)}

@app.get("/test/{wo_number}")
async def test_wo(wo_number: str):
    crawler = crawler_pool.get_crawler()
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

@app.get("/api/v1/wipo/{wo_number}")
async def get_wipo(wo_number: str, country: str = Query(None)):
    crawler = crawler_pool.get_crawler()
    result = await crawler.fetch_patent(wo_number)
    
    if country:
        result['filtered_country'] = country
    
    return result

@app.get("/api/v1/search/{molecule}")
async def search_molecule(molecule: str, country: str = Query(None), limit: int = Query(5)):
    result = await pipeline_search(molecule, max_wos=limit)
    
    if country and country == 'BR':
        result['br_patents'] = [p for p in result.get('br_patents', []) if 'BR' in str(p)]
    
    return result
