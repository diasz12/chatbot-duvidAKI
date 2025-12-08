"""
Slack bot integration using Bolt SDK
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from typing import Dict, Any

from src.config import Config
from src.services.rag_service import RAGService
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SlackBot:
    """Slack bot for DuvidAKI chatbot"""

    def __init__(self, rag_service: RAGService):
        """
        Initialize Slack bot

        Args:
            rag_service: RAG service instance
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

    def _register_handlers(self):
        """Register Slack event handlers"""

        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle @mention events"""
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
                response = self.rag_service.query(question)

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
            """Handle direct messages"""
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
                response = self.rag_service.query(text)

                # Send response
                say(text=response, thread_ts=thread_ts)

            except Exception as e:
                logger.error(f"Error handling DM: {e}")
                say(
                    text="Desculpe, ocorreu um erro ao processar sua pergunta.",
                    thread_ts=thread_ts
                )

        @self.app.command("/duvidaki")
        def handle_slash_command(ack, command, say):
            """Handle /duvidaki slash command"""
            try:
                ack()

                user = command.get("user_id")
                text = command.get("text", "")

                if not text:
                    say(
                        text="Use: `/duvidaki sua pergunta aqui`",
                        response_type="ephemeral"
                    )
                    return

                logger.info(f"Slash command from {user}: {text}")

                # Get response from RAG
                response = self.rag_service.query(text)

                # Send response
                say(text=response)

            except Exception as e:
                logger.error(f"Error handling slash command: {e}")
                say(
                    text="Desculpe, ocorreu um erro ao processar sua pergunta.",
                    response_type="ephemeral"
                )

        @self.app.command("/duvidaki-stats")
        def handle_stats_command(ack, command, say):
            """Handle /duvidaki-stats slash command"""
            try:
                ack()

                stats = self.rag_service.get_stats()

                response = f"""📊 *Estatísticas do DuvidAKI*

• Total de documentos: {stats['total_documents']}
• Confluence: {'✅ Configurado' if stats['confluence_configured'] else '❌ Não configurado'}
• GitHub: {'✅ Configurado' if stats['github_configured'] else '❌ Não configurado'}
"""

                say(text=response, response_type="ephemeral")

            except Exception as e:
                logger.error(f"Error handling stats command: {e}")
                say(
                    text="Erro ao obter estatísticas.",
                    response_type="ephemeral"
                )

        @self.app.event("message")
        def handle_message_events(body, logger):
            """Catch-all for message events"""
            pass

    def _clean_mention(self, text: str) -> str:
        """
        Remove bot mention from text

        Args:
            text: Message text with mention

        Returns:
            Cleaned text
        """
        import re
        cleaned = re.sub(r'<@[A-Z0-9]+>', '', text)
        return cleaned.strip()

    def start(self):
        """Start the Slack bot"""
        try:
            logger.info("Starting Slack bot...")
            handler = SocketModeHandler(self.app, Config.SLACK_APP_TOKEN)
            handler.start()
        except Exception as e:
            logger.error(f"Error starting Slack bot: {e}")
            raise

    def send_message(self, channel: str, text: str):
        """
        Send message to Slack channel

        Args:
            channel: Channel ID
            text: Message text
        """
        try:
            self.app.client.chat_postMessage(
                channel=channel,
                text=text
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
