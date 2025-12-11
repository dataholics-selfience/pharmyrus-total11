"""Crawler Pool v3.1 HOTFIX"""
import logging
from typing import List
from .wipo_crawler import WIPOCrawler

logger = logging.getLogger(__name__)

class CrawlerPool:
    def __init__(self, size: int = 3):
        self.size = size
        self.crawlers: List[WIPOCrawler] = []
        self.current = 0
    
    async def initialize(self):
        logger.info(f"🔧 Initializing {self.size} crawlers...")
        for i in range(self.size):
            crawler = WIPOCrawler(max_retries=3, timeout=60000, headless=True)
            await crawler.initialize()
            self.crawlers.append(crawler)
            logger.info(f"  ✅ Crawler {i+1}/{self.size} ready")
        logger.info("✅ Crawler pool initialized")
    
    async def close(self):
        for crawler in self.crawlers:
            await crawler.close()
        self.crawlers = []
    
    def get_crawler(self) -> WIPOCrawler:
        crawler = self.crawlers[self.current]
        self.current = (self.current + 1) % len(self.crawlers)
        return crawler

crawler_pool = CrawlerPool(size=2)
