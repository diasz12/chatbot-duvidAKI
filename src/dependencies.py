"""
Shared service instances (singletons) managed by FastAPI lifespan.
"""

from src.services.rag_service import RAGService
from src.services.devin_service import DevinService
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_rag_service: RAGService | None = None
_devin_service: DevinService | None = None


def init_services():
    """Initialize singleton services. Called once during app startup."""
    global _rag_service, _devin_service

    _rag_service = RAGService()
    logger.info("RAGService singleton initialized")

    if Config.is_devin_configured():
        _devin_service = DevinService()
        logger.info("DevinService singleton initialized")
    else:
        logger.info("DevinService skipped (DEVIN_API_TOKEN not set)")


def get_rag_service() -> RAGService:
    """FastAPI dependency that returns the RAGService singleton."""
    return _rag_service


def get_devin_service() -> DevinService | None:
    """FastAPI dependency that returns the DevinService singleton (or None)."""
    return _devin_service
