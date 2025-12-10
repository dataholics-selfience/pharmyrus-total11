"""Crawler Pool v3.1"""
import asyncio
from typing import Dict, Any, List
from .wipo_crawler import WIPOCrawler
import logging

logger = logging.getLogger(__name__)

class CrawlerPool:
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.pool: List[WIPOCrawler] = []
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        for i in range(self.pool_size):
            crawler = WIPOCrawler(max_retries=3, timeout=60000, headless=True)
            await crawler.initialize()
            self.pool.append(crawler)
            logger.info(f"✅ Crawler {i+1}/{self.pool_size} initialized")
    
    async def close(self):
        for crawler in self.pool:
            await crawler.close()
        self.pool.clear()
    
    async def fetch_patent(self, wo_number: str) -> Dict[str, Any]:
        if wo_number in self.cache:
            return self.cache[wo_number]
        
        if not self.pool:
            async with WIPOCrawler(max_retries=3, timeout=60000, headless=True) as crawler:
                data = await crawler.fetch_patent(wo_number)
        else:
            crawler = self.pool[0]
            data = await crawler.fetch_patent(wo_number)
        
        if not data.get('erro'):
            self.cache[wo_number] = data
        
        return data
