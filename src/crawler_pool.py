import asyncio
import logging
from .wipo_crawler import WIPOCrawler

logger = logging.getLogger(__name__)

class CrawlerPool:
    def __init__(self, size: int = 2):
        self.size = size
        self.crawlers = []
        
    async def initialize(self):
        logger.info(f"🔧 Initializing {self.size} crawlers...")
        for i in range(self.size):
            crawler = WIPOCrawler(headless=True)
            await crawler.initialize()
            self.crawlers.append(crawler)
            logger.info(f"  ✅ Crawler {i+1}/{self.size} ready")
        logger.info("✅ Crawler pool initialized")
    
    def get_crawler(self) -> WIPOCrawler:
        return self.crawlers[0] if self.crawlers else None
    
    async def close(self):
        for crawler in self.crawlers:
            await crawler.close()

crawler_pool = CrawlerPool(size=2)
