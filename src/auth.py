"""
API Key authentication dependency for FastAPI.
"""

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from src.config import Config

api_key_header = APIKeyHeader(name="X-API-Key")


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not Config.API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not configured on server")
    if api_key != Config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
