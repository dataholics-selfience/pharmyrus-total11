"""
Pharmyrus v3.1 HOTFIX - Entry Point
"""
from src.api_service import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
