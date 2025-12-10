"""
Devin AI API Client
Handles interactions with Devin AI API for repository information retrieval
"""

import requests
from typing import Dict, Any, Optional, List
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DevinClient:
    """Client for interacting with Devin AI API"""

    BASE_URL = "https://api.devin.ai"
    API_VERSION = "v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.DEVIN_API_KEY
        if not self.api_key:
            raise ValueError("Devin API key not configured")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

        logger.info("DevinClient initialized")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Devin API

        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            Response data

        Raises:
            Exception: If request fails
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=60
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise

    def create_session(
        self,
        prompt: str,
        knowledge_ids: Optional[List[str]] = None,
        snapshot_id: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_acu_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new Devin session

        Args:
            prompt: Initial instruction or query
            knowledge_ids: Specific knowledge bases to include (None = all, [] = none)
            snapshot_id: Codebase snapshot reference
            title: Custom session name
            tags: Session categorization labels
            max_acu_limit: Maximum ACU limit

        Returns:
            Session data with session_id, url, and is_new_session
        """
        payload = {"prompt": prompt}

        if knowledge_ids is not None:
            payload["knowledge_ids"] = knowledge_ids
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        if title:
            payload["title"] = title
        if tags:
            payload["tags"] = tags
        if max_acu_limit:
            payload["max_acu_limit"] = max_acu_limit

        logger.info(f"Creating Devin session: {title or 'Untitled'}")
        return self._make_request("POST", "sessions", data=payload)

    def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message to an existing Devin session

        Args:
            session_id: Session identifier
            message: Message text

        Returns:
            Response with detail field
        """
        logger.info(f"Sending message to session {session_id}")
        return self._make_request(
            "POST",
            f"sessions/{session_id}/message",
            data={"message": message}
        )

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve session details

        Args:
            session_id: Session identifier

        Returns:
            Session data
        """
        logger.info(f"Retrieving session {session_id}")
        return self._make_request("GET", f"sessions/{session_id}")

    def list_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        List all Devin sessions

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            tags: Filter by tags

        Returns:
            List of sessions
        """
        params = {"limit": limit, "offset": offset}
        if tags:
            params["tags"] = ",".join(tags)

        logger.info("Listing Devin sessions")
        return self._make_request("GET", "sessions", params=params)

    def terminate_session(self, session_id: str) -> Dict[str, Any]:
        """
        Terminate a Devin session

        Args:
            session_id: Session identifier

        Returns:
            Termination response
        """
        logger.info(f"Terminating session {session_id}")
        return self._make_request("DELETE", f"sessions/{session_id}")

    def query_repository(
        self,
        question: str,
        repository_context: Optional[str] = None,
        title: Optional[str] = None
    ) -> str:
        """
        Query repository information through Devin

        Args:
            question: Question about the repository
            repository_context: Additional context about repository
            title: Session title

        Returns:
            Response from Devin
        """
        # Build prompt with repository context
        prompt = f"Question about repository: {question}"
        if repository_context:
            prompt = f"{repository_context}\n\n{prompt}"

        # Create session
        session_data = self.create_session(
            prompt=prompt,
            title=title or f"Repository Query: {question[:50]}",
            tags=["repository", "query"]
        )

        session_id = session_data.get("session_id")
        logger.info(f"Created session {session_id} for repository query")

        return f"Session created: {session_data.get('url')}"
