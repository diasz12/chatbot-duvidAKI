"""
Devin webhook — tentacle for Devin AI queries.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth import verify_api_key
from src.dependencies import get_devin_service
from src.services.devin_service import DevinService
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(tags=["webhooks"])


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    status: str


@router.post("/webhook/devin", response_model=AnswerResponse)
async def devin_webhook(
    body: QuestionRequest,
    _api_key: str = Depends(verify_api_key),
    devin_service: DevinService | None = Depends(get_devin_service),
):
    logger.info(f"[Devin Webhook] Question: {body.question[:100]}...")
    try:
        if devin_service is None:
            return AnswerResponse(
                answer="Devin service is not configured", status="error"
            )
        answer = devin_service.ask(body.question)
        return AnswerResponse(answer=answer, status="success")
    except Exception as e:
        logger.error(f"[Devin Webhook] Error: {e}", exc_info=True)
        return AnswerResponse(answer=str(e), status="error")
