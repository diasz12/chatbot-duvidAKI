"""
DuvidAKI - AI Chatbot with Knowledge Base
FastAPI webhook server (Octo tentacle architecture)
"""

import sys
import io
from contextlib import asynccontextmanager

# Configure UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI, Depends

from src.auth import verify_api_key
from src.config import Config
from src.dependencies import init_services, get_rag_service
from src.services.rag_service import RAGService
from src.utils.logger import setup_logger
from src.webhooks.confluence_webhook import router as confluence_router
from src.webhooks.devin_webhook import router as devin_router

logger = setup_logger(__name__)

# Validate configuration at startup
Config.validate()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize singleton services
    init_services()
    logger.info("DuvidAKI server ready")
    yield
    # Shutdown: cleanup if needed
    logger.info("DuvidAKI server shutting down")


app = FastAPI(
    title="DuvidAKI",
    description="AI Chatbot webhook server",
    lifespan=lifespan,
)

# Mount webhook routers
app.include_router(confluence_router)
app.include_router(devin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/index/confluence")
async def index_confluence(
    _api_key: str = Depends(verify_api_key),
    rag_service: RAGService = Depends(get_rag_service),
):
    try:
        if not Config.is_confluence_configured():
            return {"status": "error", "message": "Confluence not configured"}
        success = rag_service.index_confluence()
        if success:
            stats = rag_service.get_stats()
            return {"status": "success", "total_documents": stats["total_documents"]}
        return {"status": "error", "message": "Failed to index Confluence"}
    except Exception as e:
        logger.error(f"Error indexing Confluence: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/stats")
async def stats(
    _api_key: str = Depends(verify_api_key),
    rag_service: RAGService = Depends(get_rag_service),
):
    try:
        return {"status": "success", **rag_service.get_stats()}
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/reset")
async def reset(
    _api_key: str = Depends(verify_api_key),
    rag_service: RAGService = Depends(get_rag_service),
):
    try:
        success = rag_service.reset_knowledge_base()
        if success:
            return {"status": "success", "message": "Knowledge base reset"}
        return {"status": "error", "message": "Failed to reset knowledge base"}
    except Exception as e:
        logger.error(f"Error resetting knowledge base: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
