from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pharmyrus v3.3 DEBUG")

@app.get("/")
async def root():
    return {"status": "API is running!", "version": "3.3.0-DEBUG"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.3.0-DEBUG"}

logger.info("🚀 API initialized (no crawlers yet)")
