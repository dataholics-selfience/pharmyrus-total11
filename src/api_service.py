"""
API Service v3.1 HOTFIX - FastAPI Patent Intelligence Service
CORREÇÕES:
- Endpoint /api/v1/wipo/{wo_number} agora usa crawler local com dados completos
- Endpoint /api/v1/search/{molecule} com WO discovery corrigido
- Todos endpoints retornam worldwide_applications completo
- Sistema de debug em todas as respostas
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging
import asyncio
import time
from datetime import datetime

from .wipo_crawler import WIPOCrawler
from .crawler_pool import CrawlerPool
from .pipeline_service import PipelineService
from .batch_service import BatchService

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Pharmyrus v3.1 HOTFIX - Patent Intelligence API",
    version="3.1.0-HOTFIX",
    description="Complete patent intelligence platform with worldwide data extraction"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
crawler_pool = CrawlerPool(pool_size=3)
pipeline = PipelineService()
batch = BatchService()

@app.on_event("startup")
async def startup():
    """Initialize services"""
    logger.info("🚀 Pharmyrus WIPO API iniciando...")
    await crawler_pool.initialize()
    logger.info("✅ API pronta!")
    logger.info(f"📦 Cache TTL: {3600}s")
    logger.info(f"🔄 Batch processing enabled with max {3} concurrent searches")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    logger.info("🛑 Encerrando API...")
    await crawler_pool.close()

@app.get("/")
async def root():
    """API Info"""
    return {
        "service": "Pharmyrus v3.1 HOTFIX",
        "version": "3.1.0-HOTFIX",
        "status": "operational",
        "fixes": [
            "WIPO crawler extrai worldwide_applications completo",
            "WO discovery com múltiplas fontes paralelas",
            "Extração de titular, datas, inventores do HTML",
            "Sistema de debug em camadas",
            "Integração local do crawler (não mais chamada externa)"
        ],
        "endpoints": {
            "wipo": "/api/v1/wipo/{wo_number}",
            "search": "/api/v1/search/{molecule}",
            "batch": "/api/v1/batch/search",
            "test": "/test/{wo_number}",
            "health": "/health"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "pool_size": crawler_pool.pool_size,
        "active_crawlers": len(crawler_pool.pool)
    }

@app.get("/api/v1/wipo/{wo_number}")
async def get_wipo_patent(
    wo_number: str,
    country: Optional[str] = Query(None, description="Filter by country (ex: BR, US)")
):
    """
    Get complete WIPO patent data with worldwide applications
    
    CORRIGIDO v3.1 HOTFIX:
    - Extrai worldwide_applications completo (igual ao /test/)
    - Extrai titular, datas, inventores
    - Debug detalhado
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Buscando patente WO: {wo_number} | Country filter: {country}")
        
        # Usa crawler do pool
        data = await crawler_pool.fetch_patent(wo_number)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Patent {wo_number} not found")
        
        # Filtra por país se solicitado
        if country:
            worldwide = data.get('worldwide_applications', {})
            filtered_apps = {}
            
            for year, apps in worldwide.items():
                filtered = [app for app in apps if app.get('country_code') == country]
                if filtered:
                    filtered_apps[year] = filtered
            
            data['worldwide_applications'] = filtered_apps
            data['country_filter_applied'] = country
        
        duration = time.time() - start_time
        
        return {
            **data,
            "api_metadata": {
                "endpoint": "/api/v1/wipo",
                "version": "3.1-HOTFIX",
                "duration_seconds": round(duration, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "country_filter": country
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/search/{molecule}")
async def search_molecule(
    molecule: str,
    country: Optional[str] = Query(None, description="Filter by country"),
    limit: int = Query(20, ge=1, le=50, description="Max WO patents to process")
):
    """
    Complete patent intelligence search
    
    CORRIGIDO v3.1 HOTFIX:
    - WO discovery com múltiplas fontes
    - Processamento paralelo de todas camadas
    - Worldwide applications completo
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔎 Buscando molécula: {molecule} | Country: {country} | Limit: {limit}")
        
        # Execute pipeline completo
        result = await pipeline.execute_full_pipeline(
            molecule=molecule,
            country_filter=country,
            limit=limit
        )
        
        duration = time.time() - start_time
        result['api_metadata'] = {
            "endpoint": "/api/v1/search",
            "version": "3.1-HOTFIX",
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na busca: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/batch/search")
async def batch_search(request: dict):
    """
    Batch processing for multiple molecules
    
    Body: {
        "molecules": ["darolutamide", "apalutamide"],
        "country": "BR",
        "limit": 10
    }
    """
    try:
        molecules = request.get("molecules", [])
        country = request.get("country")
        limit = request.get("limit", 10)
        
        if not molecules:
            raise HTTPException(status_code=400, detail="molecules list required")
        
        logger.info(f"📦 Batch search: {len(molecules)} molecules")
        
        result = await batch.process_batch(
            molecules=molecules,
            country_filter=country,
            limit=limit
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test/{wo_number}")
async def test_endpoint(wo_number: str):
    """
    Test endpoint - extrai dados completos de uma patente WO
    """
    try:
        logger.info(f"🧪 TEST: {wo_number}")
        
        async with WIPOCrawler(max_retries=3, timeout=60000, headless=True) as crawler:
            data = await crawler.fetch_patent(wo_number)
        
        # Extrai apenas BRs do worldwide
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
            "abstract": data.get('resumo'),
            "filing_date": data.get('datas', {}).get('deposito'),
            "inventors": data.get('inventores'),
            "ipc_cpc": data.get('cpc_ipc'),
            "countries": data.get('paises_familia'),
            "worldwide_applications": data.get('worldwide_applications'),
            "br_patents": br_patents,
            "debug": data.get('debug'),
            "test_metadata": {
                "endpoint": "/test/",
                "version": "3.1-HOTFIX",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
