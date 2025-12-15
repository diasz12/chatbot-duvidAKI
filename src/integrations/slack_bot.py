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
from src.services.rag_service import RAGService
from src.utils.logger import setup_logger

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
        """Register all Slack event handlers."""
        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle app mention events."""
            try:
                user = event.get("user")
                text = event.get("text", "")
                thread_ts = event.get("thread_ts", event.get("ts"))

                # Remove mention from text
                question = self._clean_mention(text)

                if not question:
                    say(
                        text="Olá! Como posso ajudar? Faça uma pergunta sobre nossa documentação.",
                        thread_ts=thread_ts
                    )
                    return

                # Process question
                logger.info(f"Question from {user}: {question}")

                # Show typing indicator
                say(text="Deixe-me procurar isso para você...", thread_ts=thread_ts)

                # Get response from RAG
                response = self.rag_service.query(question=question)

                # Send response
                say(text=response, thread_ts=thread_ts)

            except Exception as e:
                logger.error(f"Error handling mention: {e}")
                say(
                    text="Desculpe, ocorreu um erro ao processar sua pergunta.",
                    thread_ts=thread_ts
                )

        @self.app.message("")
        def handle_direct_message(message, say):
            """Handle direct messages."""
            try:
                # Only respond to DMs (not channel messages)
                if message.get("channel_type") != "im":
                    return

                user = message.get("user")
                text = message.get("text", "")
                thread_ts = message.get("thread_ts", message.get("ts"))

                if not text:
                    return

                logger.info(f"DM from {user}: {text}")

                # Show typing indicator
                say(text="Deixe-me procurar isso para você...", thread_ts=thread_ts)

                # Get response from RAG
                response = self.rag_service.query(question=text)

                # Send response
                say(text=response, thread_ts=thread_ts)

            except Exception as e:
                logger.error(f"Error handling DM: {e}")
                say(
                    text="Desculpe, ocorreu um erro ao processar sua pergunta.",
                    thread_ts=thread_ts
                )

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

                # Get response from RAG
                response = self.rag_service.query(question=text)

                # Send response
                respond(text=response)

            except Exception as e:
                logger.error(f"Error handling slash command: {e}")
                respond(
                    text="Desculpe, ocorreu um erro ao processar sua pergunta.",
                    response_type="ephemeral"
                )

        @self.app.command("/duvidaki-stats")
        def handle_stats_command(ack, _command, respond):
            """Handle /duvidaki-stats slash command."""
            try:
                ack()

                stats = self.rag_service.get_stats()

                response = f"""📊 *Estatísticas do DuvidAKI*

• Total de documentos: {stats['total_documents']}
• Confluence: {'✅ Configurado' if stats['confluence_configured'] else '❌ Não configurado'}
• GitHub: {'✅ Configurado' if stats['github_configured'] else '❌ Não configurado'}
"""

                respond(text=response, response_type="ephemeral")

            except Exception as e:
                logger.error(f"Error handling stats command: {e}")
                respond(
                    text="Erro ao obter estatísticas.",
                    response_type="ephemeral"
                )

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
