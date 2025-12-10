"""
Devin Repository Service
Handles repository information retrieval through Devin AI
"""

from typing import List, Dict, Any, Optional
from src.integrations.devin_client import DevinClient
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DevinRepositoryService:
    """Service for querying repository information via Devin AI"""

    def __init__(self, devin_client: Optional[DevinClient] = None):
        """
        Initialize repository service

        Args:
            devin_client: Devin client instance (creates new if not provided)
        """
        if not Config.is_devin_configured():
            logger.warning("Devin AI not configured")
            self.enabled = False
            return

        self.devin_client = devin_client or DevinClient()
        self.enabled = True
        logger.info("DevinRepositoryService initialized")

    def query_code(self, question: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Query code repositories through Devin

        Args:
            question: Question about the codebase
            context: Additional context for the query

        Returns:
            Dict with session_id, url, and status
        """
        if not self.enabled:
            return {
                "error": "Devin AI not configured",
                "session_id": None,
                "url": None
            }

        try:
            logger.info(f"Querying code: {question[:100]}")

            # Build comprehensive prompt
            prompt = self._build_query_prompt(question, context)

            # Create Devin session
            session = self.devin_client.create_session(
                prompt=prompt,
                title=f"Code Query: {question[:50]}",
                tags=["repository", "code-query", "chatbot"]
            )

            return {
                "session_id": session.get("session_id"),
                "url": session.get("url"),
                "status": "created",
                "is_new": session.get("is_new_session")
            }

        except Exception as e:
            logger.error(f"Error querying code: {e}")
            return {
                "error": str(e),
                "session_id": None,
                "url": None
            }

    def search_documentation(self, query: str) -> Dict[str, Any]:
        """
        Search for documentation in repositories

        Args:
            query: Search query

        Returns:
            Dict with session_id, url, and status
        """
        if not self.enabled:
            return {
                "error": "Devin AI not configured",
                "session_id": None,
                "url": None
            }

        try:
            prompt = f"""Search the repository documentation for: {query}

Please find and summarize relevant documentation including:
- README files
- Documentation pages
- Code comments
- API documentation
- Usage examples

Provide a comprehensive answer with references to specific files and line numbers."""

            session = self.devin_client.create_session(
                prompt=prompt,
                title=f"Doc Search: {query[:50]}",
                tags=["documentation", "search", "chatbot"]
            )

            return {
                "session_id": session.get("session_id"),
                "url": session.get("url"),
                "status": "created",
                "is_new": session.get("is_new_session")
            }

        except Exception as e:
            logger.error(f"Error searching documentation: {e}")
            return {
                "error": str(e),
                "session_id": None,
                "url": None
            }

    def explain_code(self, file_path: str, function_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Request code explanation from Devin

        Args:
            file_path: Path to file in repository
            function_name: Optional specific function to explain

        Returns:
            Dict with session_id, url, and status
        """
        if not self.enabled:
            return {
                "error": "Devin AI not configured",
                "session_id": None,
                "url": None
            }

        try:
            if function_name:
                prompt = f"""Explain the function '{function_name}' in file '{file_path}'.

Please provide:
1. What the function does
2. Parameters and return values
3. Key logic and algorithms used
4. Dependencies and related functions
5. Usage examples if available"""
            else:
                prompt = f"""Explain the code in file '{file_path}'.

Please provide:
1. Overall purpose of the file
2. Key functions and classes
3. Main logic flow
4. Dependencies
5. Usage examples"""

            session = self.devin_client.create_session(
                prompt=prompt,
                title=f"Explain: {file_path}",
                tags=["code-explanation", "chatbot"]
            )

            return {
                "session_id": session.get("session_id"),
                "url": session.get("url"),
                "status": "created",
                "is_new": session.get("is_new_session")
            }

        except Exception as e:
            logger.error(f"Error explaining code: {e}")
            return {
                "error": str(e),
                "session_id": None,
                "url": None
            }

    def find_examples(self, topic: str) -> Dict[str, Any]:
        """
        Find code examples for a specific topic

        Args:
            topic: Topic to find examples for

        Returns:
            Dict with session_id, url, and status
        """
        if not self.enabled:
            return {
                "error": "Devin AI not configured",
                "session_id": None,
                "url": None
            }

        try:
            prompt = f"""Find code examples related to: {topic}

Please search the repository and provide:
1. Relevant code snippets
2. File locations (with line numbers)
3. Explanation of how each example works
4. Best practices demonstrated
5. Related documentation"""

            session = self.devin_client.create_session(
                prompt=prompt,
                title=f"Examples: {topic[:50]}",
                tags=["examples", "search", "chatbot"]
            )

            return {
                "session_id": session.get("session_id"),
                "url": session.get("url"),
                "status": "created",
                "is_new": session.get("is_new_session")
            }

        except Exception as e:
            logger.error(f"Error finding examples: {e}")
            return {
                "error": str(e),
                "session_id": None,
                "url": None
            }

    def _build_query_prompt(self, question: str, context: Optional[str] = None) -> str:
        """
        Build comprehensive prompt for code query

        Args:
            question: User's question
            context: Additional context

        Returns:
            Formatted prompt
        """
        prompt = f"""Answer the following question about the codebase:

Question: {question}"""

        if context:
            prompt += f"\n\nAdditional Context:\n{context}"

        prompt += """

Please provide a detailed answer including:
1. Direct answer to the question
2. Relevant code references (file paths and line numbers)
3. Code snippets if applicable
4. Related documentation or comments
5. Any important context or caveats

Format your response in a clear, structured way."""

        return prompt

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get status of a Devin session

        Args:
            session_id: Session identifier

        Returns:
            Session status information
        """
        if not self.enabled:
            return {"error": "Devin AI not configured"}

        try:
            return self.devin_client.get_session(session_id)
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return {"error": str(e)}

    def send_followup(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Send follow-up message to existing session

        Args:
            session_id: Session identifier
            message: Follow-up message

        Returns:
            Response from Devin
        """
        if not self.enabled:
            return {"error": "Devin AI not configured"}

        try:
            return self.devin_client.send_message(session_id, message)
        except Exception as e:
            logger.error(f"Error sending follow-up: {e}")
            return {"error": str(e)}
