from fastapi import FastAPI
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("🚀 Pharmyrus v3.3 DEBUG-SIMPLE")
logger.info("=" * 60)

app = FastAPI(title="Pharmyrus DEBUG-SIMPLE")

@app.on_event("startup")
async def startup():
    logger.info("✅ API started successfully!")
    logger.info("=" * 60)

@app.get("/")
async def root():
    return {
        "service": "Pharmyrus DEBUG-SIMPLE",
        "version": "3.3.0-SIMPLE",
        "status": "✅ Running",
        "note": "This is a minimal version WITHOUT Playwright/Crawlers for testing Railway deployment"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.3.0-SIMPLE"}

@app.get("/test")
async def test():
    return {
        "test": "SUCCESS",
        "message": "If you see this, FastAPI + Railway are working!",
        "next_step": "Deploy the full version with Playwright"
    }

logger.info("📦 API module loaded")
