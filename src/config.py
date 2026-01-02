"""
Configuration module for DuvidAKI Chatbot
Loads and validates environment variables
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
    OPENAI_BATCH_SIZE: int = int(os.getenv("OPENAI_BATCH_SIZE", "100"))

    SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN: Optional[str] = os.getenv("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET: Optional[str] = os.getenv("SLACK_SIGNING_SECRET")

    CONFLUENCE_URL: Optional[str] = os.getenv("CONFLUENCE_URL")
    CONFLUENCE_EMAIL: Optional[str] = os.getenv("CONFLUENCE_EMAIL")
    CONFLUENCE_API_TOKEN: Optional[str] = os.getenv("CONFLUENCE_API_TOKEN")
    CONFLUENCE_SPACE_KEY: Optional[str] = os.getenv("CONFLUENCE_SPACE_KEY")
    CONFLUENCE_PAGE_LIMIT: int = int(os.getenv("CONFLUENCE_PAGE_LIMIT", "50"))

    # Database Configuration (PostgreSQL + pgvector via Supabase)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "5"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "false").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))

    @classmethod
    def validate(cls):
        required = {
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return True

    @classmethod
    def is_slack_configured(cls):
        return all([
            cls.SLACK_BOT_TOKEN,
            cls.SLACK_APP_TOKEN,
            cls.SLACK_SIGNING_SECRET
        ])

    @classmethod
    def is_confluence_configured(cls):
        return all([
            cls.CONFLUENCE_URL,
            cls.CONFLUENCE_EMAIL,
            cls.CONFLUENCE_API_TOKEN
        ])

    @classmethod
    def get_database_url(cls) -> str:
        if cls.DATABASE_URL:
            return cls.DATABASE_URL

        if not cls.DB_PASSWORD:
            raise ValueError("DB_PASSWORD or DATABASE_URL must be set")

        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
