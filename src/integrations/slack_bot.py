"""
Slack bot integration using Bolt SDK.

This module provides the SlackBot class for integrating the DuvidAKI chatbot
with Slack using the Bolt SDK. It handles app mentions, direct messages,
and slash commands.
"""

import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.config import Config
from src.constants import (
    SLACK_HELP_MESSAGE,
    SLACK_PROCESSING_MESSAGE,
    SLACK_ERROR_MESSAGE,
    SLACK_STATS_TEMPLATE
)
from src.services.rag_service import RAGService
from src.utils.logger import setup_logger
from src.utils.validators import InputValidator

logger = setup_logger(__name__)


class SlackBot:
    """
    Slack bot integration for DuvidAKI chatbot.

    Handles Slack events including app mentions, direct messages,
    and slash commands. Uses Socket Mode for real-time communication.

    Attributes:
        rag_service: RAG service for answering questions
        app: Slack Bolt application instance

    Raises:
        ValueError: If Slack is not properly configured
    """

    def __init__(self, rag_service: RAGService):
        """
        Initialize Slack bot.

        Args:
            rag_service: RAG service instance for processing queries

        Raises:
            ValueError: If Slack configuration is missing
        """
        if not Config.is_slack_configured():
            logger.error("Slack not properly configured")
            raise ValueError("Slack configuration missing")

        self.rag_service = rag_service

        # Initialize Bolt app
        self.app = App(
            token=Config.SLACK_BOT_TOKEN,
            signing_secret=Config.SLACK_SIGNING_SECRET
        )

        # Register event handlers
        self._register_handlers()

        logger.info("SlackBot initialized")

    def _register_handlers(self) -> None:
        # Set to track processed event IDs (prevent duplicates)
        processed_events = set()

        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle app mention events."""
            event_id = event.get("client_msg_id") or event.get("ts")

            # Prevent duplicate processing
            if event_id in processed_events:
                logger.debug(f"Skipping duplicate event: {event_id}")
                return
            processed_events.add(event_id)

            # Clean old events (keep last 100)
            if len(processed_events) > 100:
                processed_events.pop()

            try:
                user = event.get("user")
                text = event.get("text", "")
                thread_ts = event.get("thread_ts", event.get("ts"))

                question = InputValidator.sanitize_slack_message(text)

                if not question:
                    logger.info(f"Empty question from {user}, sending help message")
                    say(text=SLACK_HELP_MESSAGE, thread_ts=thread_ts)
                    return

                logger.info(f"Question from {user}: {question[:100]}...")

                say(text=SLACK_PROCESSING_MESSAGE, thread_ts=thread_ts)

                # Try query with retry on connection error
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        response = self.rag_service.query(question=question)
                        break
                    except Exception as query_error:
                        logger.warning(f"Query attempt {attempt + 1} failed: {query_error}")
                        if attempt == max_retries - 1:
                            raise
                        # Retry on connection errors
                        if "connection" in str(query_error).lower():
                            logger.info("Retrying due to connection error...")
                            continue
                        raise

                say(text=response, thread_ts=thread_ts)
                logger.info(f"Successfully responded to {user}")

            except Exception as e:
                logger.error(f"Error handling mention: {e}", exc_info=True)
                try:
                    say(text=SLACK_ERROR_MESSAGE, thread_ts=thread_ts)
                except Exception as say_error:
                    logger.error(f"Failed to send error message: {say_error}")

        @self.app.message("")
        def handle_direct_message(message, say):
            """Handle direct messages."""
            try:
                if message.get("channel_type") != "im":
                    return

                user = message.get("user")
                text = message.get("text", "")
                thread_ts = message.get("thread_ts", message.get("ts"))

                if not text:
                    return

                question = InputValidator.sanitize_slack_message(text)
                if not question:
                    return

                logger.info(f"DM from {user}: {question[:100]}...")

                say(text=SLACK_PROCESSING_MESSAGE, thread_ts=thread_ts)

                response = self.rag_service.query(question=question)

                say(text=response, thread_ts=thread_ts)

            except Exception as e:
                logger.error(f"Error handling DM: {e}", exc_info=True)
                say(text=SLACK_ERROR_MESSAGE, thread_ts=thread_ts)

        @self.app.command("/duvidaki")
        def handle_slash_command(ack, command, respond):
            """Handle /duvidaki slash command."""
            try:
                ack()

                user = command.get("user_id")
                text = command.get("text", "")

                if not text:
                    respond(
                        text="Use: `/duvidaki sua pergunta aqui`",
                        response_type="ephemeral"
                    )
                    return

                logger.info(f"Slash command from {user}: {text}")

                response = self.rag_service.query(question=text)

                respond(text=response)

            except Exception as e:
                logger.error(f"Error handling slash command: {e}", exc_info=True)
                respond(text=SLACK_ERROR_MESSAGE, response_type="ephemeral")

        @self.app.command("/duvidaki-stats")
        def handle_stats_command(ack, _command, respond):
            """Handle /duvidaki-stats slash command."""
            try:
                ack()

                stats = self.rag_service.get_stats()

                response = SLACK_STATS_TEMPLATE.format(
                    total_documents=stats['total_documents'],
                    confluence_status='✅ Configurado' if stats['confluence_configured'] else '❌ Não configurado',
                    github_status='✅ Configurado' if stats['github_configured'] else '❌ Não configurado'
                )

                respond(text=response, response_type="ephemeral")

            except Exception as e:
                logger.error(f"Error handling stats command: {e}", exc_info=True)
                respond(text=SLACK_ERROR_MESSAGE, response_type="ephemeral")

        @self.app.event("message")
        def handle_message_events(_body, _logger):
            """Catch-all for message events."""
            pass

    def _clean_mention(self, text: str) -> str:
        """
        Remove bot mention from text.

        Args:
            text: Message text with mention (e.g., "<@U12345> How to deploy?")

        Returns:
            str: Cleaned text without mention (e.g., "How to deploy?")

        Examples:
            >>> bot = SlackBot(rag_service)
            >>> bot._clean_mention("<@U12345> Hello")
            'Hello'
        """
        cleaned = re.sub(r'<@[A-Z0-9]+>', '', text)
        return cleaned.strip()

    def start(self) -> None:
        """
        Start the Slack bot in Socket Mode.

        Raises:
            Exception: If bot fails to start
        """
        try:
            logger.info("Starting Slack bot...")
            handler = SocketModeHandler(self.app, Config.SLACK_APP_TOKEN)
            handler.start()
        except Exception as e:
            logger.error(f"Error starting Slack bot: {e}", exc_info=True)
            raise

    def send_message(self, channel: str, text: str) -> None:
        """
        Send message to Slack channel.

        Args:
            channel: Channel ID (e.g., "C1234567890")
            text: Message text to send

        Raises:
            Exception: If message sending fails

        Examples:
            >>> bot = SlackBot(rag_service)
            >>> bot.send_message("C1234567890", "Hello team!")
        """
        try:
            self.app.client.chat_postMessage(
                channel=channel,
                text=text
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            raise
