"""
Crawler Pool v3.1 - Manages multiple WIPO crawlers
"""
import asyncio
from typing import Dict, Any, List
import logging
from .wipo_crawler import WIPOCrawler

logger = logging.getLogger(__name__)

class CrawlerPool:
    """Pool de crawlers WIPO com cache"""
    
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.pool: List[WIPOCrawler] = []
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def initialize(self):
        """Initialize crawler pool"""
        logger.info(f"🔄 Inicializando pool de {self.pool_size} crawlers...")
        
        for i in range(self.pool_size):
            crawler = WIPOCrawler(max_retries=3, timeout=60000, headless=True)
            await crawler.initialize()
            self.pool.append(crawler)
            logger.info(f"✅ Crawler {i+1}/{self.pool_size} inicializado")
    
    async def close(self):
        """Close all crawlers"""
        logger.info("🛑 Fechando pool de crawlers...")
        for crawler in self.pool:
            await crawler.close()
        self.pool.clear()
    
    async def fetch_patent(self, wo_number: str) -> Dict[str, Any]:
        """
        Fetch patent with cache
        """
        # Check cache
        if wo_number in self.cache:
            logger.info(f"📦 Cache hit: {wo_number}")
            return self.cache[wo_number]
        
        # Get crawler from pool
        if not self.pool:
            logger.warning("⚠️ Pool vazio, criando crawler temporário...")
            async with WIPOCrawler(max_retries=3, timeout=60000, headless=True) as crawler:
                data = await crawler.fetch_patent(wo_number)
        else:
            crawler = self.pool[0]  # Use first available
            data = await crawler.fetch_patent(wo_number)
        
        # Cache result
        if not data.get('erro'):
            self.cache[wo_number] = data
            logger.info(f"💾 Cached: {wo_number}")
        
        return data
    
    async def fetch_multiple(self, wo_numbers: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple patents using pool"""
        
        results = []
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.pool_size)
        
        async def fetch_one(wo: str):
            async with semaphore:
                return await self.fetch_patent(wo)
        
        tasks = [fetch_one(wo) for wo in wo_numbers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Erro em {wo_numbers[i]}: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
