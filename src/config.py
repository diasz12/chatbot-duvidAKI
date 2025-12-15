"""
Configuration module for DuvidAKI Chatbot
Loads and validates environment variables
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables"""

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

    # Confluence
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
    CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
    CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")

    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPOS = os.getenv("GITHUB_REPOS", "").split(",") if os.getenv("GITHUB_REPOS") else []

    # Vector Database
    CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")

    # Application
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = {
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return True

    @classmethod
    def is_slack_configured(cls):
        """Check if Slack is properly configured"""
        return all([
            cls.SLACK_BOT_TOKEN,
            cls.SLACK_APP_TOKEN,
            cls.SLACK_SIGNING_SECRET
        ])

    @classmethod
    def is_confluence_configured(cls):
        """Check if Confluence is properly configured"""
        return all([
            cls.CONFLUENCE_URL,
            cls.CONFLUENCE_EMAIL,
            cls.CONFLUENCE_API_TOKEN
        ])

    @classmethod
    def is_github_configured(cls):
        """Check if GitHub is properly configured"""
        return bool(cls.GITHUB_TOKEN and cls.GITHUB_REPOS)
