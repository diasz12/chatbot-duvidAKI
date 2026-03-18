"""
Confluence RAG webhook — tentacle for knowledge base queries.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth import verify_api_key
from src.dependencies import get_rag_service
from src.services.rag_service import RAGService
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(tags=["webhooks"])


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    status: str


@router.post("/webhook/confluence", response_model=AnswerResponse)
async def confluence_webhook(
    body: QuestionRequest,
    _api_key: str = Depends(verify_api_key),
    rag_service: RAGService = Depends(get_rag_service),
):
    logger.info(f"[Confluence Webhook] Question: {body.question[:100]}...")
    try:
        answer = rag_service.query(body.question)
        return AnswerResponse(answer=answer, status="success")
    except Exception as e:
        logger.error(f"[Confluence Webhook] Error: {e}", exc_info=True)
        return AnswerResponse(answer=str(e), status="error")
