"""
Input validation and sanitization utilities
"""

import re
from typing import Optional
from src.constants import DANGEROUS_PATTERNS, MAX_QUERY_LENGTH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class InputValidator:
    """Validates and sanitizes user inputs"""

    @staticmethod
    def sanitize_query(query: str) -> Optional[str]:
        """
        Sanitize and validate user query.

        Args:
            query: Raw user query

        Returns:
            Sanitized query or None if invalid

        Raises:
            ValueError: If query contains dangerous patterns
        """
        if not query or not query.strip():
            return None

        # Remove extra whitespace
        query = " ".join(query.split())

        # Check length
        if len(query) > MAX_QUERY_LENGTH:
            logger.warning(f"Query too long: {len(query)} chars")
            raise ValueError(
                f"Query too long. Maximum {MAX_QUERY_LENGTH} characters allowed."
            )

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                raise ValueError(
                    "Query contains potentially dangerous content and was blocked."
                )

        return query.strip()

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid
        """
        if not url:
            return False

        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )

        return bool(url_pattern.match(url))

    @staticmethod
    def sanitize_slack_message(text: str) -> str:
        """
        Sanitize Slack message text.

        Args:
            text: Raw Slack message

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove Slack formatting
        text = re.sub(r'<@[A-Z0-9]+>', '', text)  # Remove mentions
        text = re.sub(r'<#[A-Z0-9]+\|[^>]+>', '', text)  # Remove channel links
        text = re.sub(r'<http[^>]+>', '', text)  # Remove URLs

        return text.strip()

    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix
