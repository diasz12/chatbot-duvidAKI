"""
Devin AI API client service.
Creates sessions, polls for results, and sends messages via the Devin API.
"""

import time

import requests

from src.config import Config
from src.constants import DEVIN_TIMEOUT_MESSAGE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DevinService:
    BASE_URL = "https://api.devin.ai/v1"

    def __init__(self):
        if not Config.is_devin_configured():
            raise ValueError("DEVIN_API_TOKEN is not configured")

        self.headers = {
            "Authorization": f"Bearer {Config.DEVIN_API_TOKEN}",
            "Content-Type": "application/json",
        }
        logger.info("[DevinService] Initialized")

    def create_session(self, prompt: str) -> dict:
        """Create a new Devin session with the given prompt."""
        url = f"{self.BASE_URL}/sessions"
        payload = {"prompt": prompt}

        logger.info(f"[DevinService] Creating session with prompt: {prompt[:100]}...")

        response = requests.post(url, json=payload, headers=self.headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        logger.info(f"[DevinService] Session created: {data.get('session_id')}")
        return data

    def get_session(self, session_id: str) -> dict:
        """Get the current state of a Devin session."""
        url = f"{self.BASE_URL}/sessions/{session_id}"

        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()

        return response.json()

    def send_message(self, session_id: str, message: str) -> dict:
        """Send a follow-up message to an existing Devin session."""
        url = f"{self.BASE_URL}/sessions/{session_id}/message"
        payload = {"message": message}

        logger.info(f"[DevinService] Sending message to session {session_id}")

        response = requests.post(url, json=payload, headers=self.headers, timeout=30)
        response.raise_for_status()

        return response.json()

    def ask(self, prompt: str, poll_interval: int = 5, timeout: int = 300) -> str:
        """
        Convenience method: create a session, poll until completion, return the response.

        Args:
            prompt: The prompt to send to Devin.
            poll_interval: Seconds between polling requests.
            timeout: Maximum seconds to wait for a response.

        Returns:
            The last message from Devin.
        """
        session = self.create_session(prompt)
        session_id = session.get("session_id")

        if not session_id:
            raise ValueError("No session_id returned from Devin API")

        logger.info(f"[DevinService] Polling session {session_id}...")

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning(f"[DevinService] Timeout after {timeout}s for session {session_id}")
                return DEVIN_TIMEOUT_MESSAGE

            try:
                session_data = self.get_session(session_id)
            except requests.exceptions.RequestException as e:
                logger.warning(f"[DevinService] Polling error: {e}, retrying...")
                time.sleep(poll_interval)
                continue

            status = session_data.get("status_enum", "")
            logger.debug(f"[DevinService] Session {session_id} status: {status}")

            if status in ("blocked", "finished"):
                # Extract last message from Devin
                structured_output = session_data.get("structured_output")
                if structured_output:
                    return str(structured_output)

                messages = session_data.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    return last_message.get("message", last_message.get("text", str(last_message)))

                return f"Devin finalizou a sessao (status: {status}), mas sem mensagem de resposta."

            time.sleep(poll_interval)
