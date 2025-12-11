import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from .wipo_crawler import WIPOCrawler

class CrawlerPool:
    def __init__(self, size: int = 2):
        self.size = size
        self.crawlers = []
        logger.info(f"📝 CrawlerPool created (target size: {size})")
        
    async def initialize(self):
        logger.info(f"🔧 Starting initialization of {self.size} crawlers...")
        
        for i in range(self.size):
            try:
                logger.info(f"  📝 Initializing crawler {i+1}/{self.size}...")
                crawler = WIPOCrawler(headless=True)
                
                logger.info(f"  📝 Calling crawler.initialize()...")
                await crawler.initialize()
                
                self.crawlers.append(crawler)
                logger.info(f"  ✅ Crawler {i+1}/{self.size} ready")
            except Exception as e:
                logger.error(f"  ❌ Crawler {i+1}/{self.size} FAILED: {e}")
                logger.exception("Full traceback:")
                raise
        
        logger.info(f"✅ Crawler pool initialized with {len(self.crawlers)} crawlers")
    
    def get_crawler(self) -> WIPOCrawler:
        if not self.crawlers:
            logger.warning("⚠️ No crawlers available!")
            return None
        return self.crawlers[0]
    
    async def close(self):
        logger.info("🛑 Closing crawler pool...")
        for i, crawler in enumerate(self.crawlers):
            try:
                await crawler.close()
                logger.info(f"  ✅ Crawler {i+1} closed")
            except Exception as e:
                logger.error(f"  ⚠️ Error closing crawler {i+1}: {e}")
        logger.info("✅ Crawler pool closed")

crawler_pool = CrawlerPool(size=2)
logger.info("📦 CrawlerPool module loaded")
