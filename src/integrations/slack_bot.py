import time
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
    def __init__(self, rag_service: RAGService):
        if not Config.is_slack_configured():
            logger.error("[SLACK BOT] Slack not properly configured")
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
        # Dict to track active threads with their last activity timestamp
        # Format: {thread_ts: last_activity_timestamp}
        active_threads = {}
        THREAD_TIMEOUT = 300  # 5 minutes in seconds

        def is_thread_active(thread_ts: str) -> bool:
            if thread_ts not in active_threads:
                return False

            last_activity = active_threads[thread_ts]
            elapsed = time.time() - last_activity

            if elapsed > THREAD_TIMEOUT:
                logger.info(f"[SLACK BOT] Thread {thread_ts} timed out after {elapsed:.0f}s (limit: {THREAD_TIMEOUT}s)")
                del active_threads[thread_ts]
                return False

            return True

        def update_thread_activity(thread_ts: str):
            active_threads[thread_ts] = time.time()
            logger.debug(f"[Slack Bot] Updated activity for thread {thread_ts}")

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
                    # Add thread to active threads for future replies
                    if thread_ts:
                        update_thread_activity(thread_ts)
                        logger.info(f"[Slack Bot] Added thread {thread_ts} to active_threads (from help). Active threads: {len(active_threads)}")
                    return

                logger.info(f"[Slack Bot] Question from {user}: {question[:100]}...")

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
                            logger.info("[SLACK BOT] Retrying due to connection error...")
                            continue
                        raise

                say(text=response, thread_ts=thread_ts)
                logger.info(f"[Slack Bot] Successfully responded to {user}")

                # Add thread to active threads for future replies
                if thread_ts:
                    update_thread_activity(thread_ts)
                    logger.info(f"[Slack Bot] Added thread {thread_ts} to active_threads (from mention)")

            except Exception as e:
                logger.error(f"[Slack Bot] Error handling mention: {e}", exc_info=True)
                try:
                    say(text=SLACK_ERROR_MESSAGE, thread_ts=thread_ts)
                except Exception as say_error:
                    logger.error(f"[Slack Bot] Failed to send error message: {say_error}")

        @self.app.message("")
        def handle_direct_message(message, say):
            """Handle direct messages and thread replies."""
            try:
                channel_type = message.get("channel_type")
                thread_ts = message.get("thread_ts")
                user = message.get("user")
                text = message.get("text", "")
                bot_id = message.get("bot_id")

                logger.info(f"[Slack Bot] Message event received - channel_type={channel_type}, thread_ts={thread_ts}, user={user}, bot_id={bot_id}, text={text[:50] if text else '(empty)'}...")

                # Skip bot's own messages
                if bot_id:
                    logger.debug(f"[Slack Bot] Skipping bot message (bot_id={bot_id})")
                    return

                # Handle DMs
                if channel_type == "im":
                    logger.info(f"[Slack Bot] Handling DM from {user}")
                    if not text:
                        return

                    question = InputValidator.sanitize_slack_message(text)
                    if not question:
                        return

                    logger.info(f"[Slack Bot] DM from {user}: {question[:100]}...")

                    say(text=SLACK_PROCESSING_MESSAGE)

                    response = self.rag_service.query(question=question)

                    say(text=response)
                    return

                # Handle thread replies (messages in active threads without @mention)
                if thread_ts:
                    logger.info(f"[Slack Bot] Message in thread {thread_ts}. Active threads: {list(active_threads.keys())}")
                    if is_thread_active(thread_ts):
                        logger.info(f"[Slack Bot] Thread {thread_ts} IS in active_threads - processing reply")

                        # Deduplicate events
                        event_id = message.get("client_msg_id") or message.get("ts")
                        if event_id in processed_events:
                            logger.debug(f"[Slack Bot] Skipping duplicate thread message: {event_id}")
                            return
                        processed_events.add(event_id)

                        if not text:
                            logger.debug("[Slack Bot] Empty text in thread reply")
                            return

                        question = InputValidator.sanitize_slack_message(text)
                        if not question:
                            logger.debug("[Slack Bot] Empty question after sanitization in thread reply")
                            return

                        logger.info(f"🧵 Thread reply from {user}: {question[:100]}...")

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
                                if "connection" in str(query_error).lower():
                                    logger.info("Retrying due to connection error...")
                                    continue
                                raise

                        say(text=response, thread_ts=thread_ts)
                        logger.info(f"[Slack Bot] Successfully responded to thread reply from {user}")

                        # Update thread activity timestamp
                        update_thread_activity(thread_ts)
                    else:
                        logger.info(f"[Slack Bot] Thread {thread_ts} NOT in active_threads or timed out - ignoring message")
                else:
                    logger.debug(f"[Slack Bot] Message not in thread (thread_ts is None) - ignoring")

            except Exception as e:
                logger.error(f"[Slack Bot] Error handling message: {e}", exc_info=True)
                try:
                    if thread_ts:
                        say(text=SLACK_ERROR_MESSAGE, thread_ts=thread_ts)
                    else:
                        say(text=SLACK_ERROR_MESSAGE)
                except Exception as say_error:
                    logger.error(f"[Slack Bot] Failed to send error message: {say_error}")

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

                logger.info(f"[Slack Bot] Slash command from {user}: {text}")

                response = self.rag_service.query(question=text)

                respond(text=response)

            except Exception as e:
                logger.error(f"[Slack Bot] Error handling slash command: {e}", exc_info=True)
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
                logger.error(f"[Slack Bot] Error handling stats command: {e}", exc_info=True)
                respond(text=SLACK_ERROR_MESSAGE, response_type="ephemeral")

        @self.app.event("message")
        def handle_message_events(_body, _logger):
            """Catch-all for message events."""
            pass

    def start(self) -> None:
        """
        Start the Slack bot in Socket Mode.

        Raises:
            Exception: If bot fails to start
        """
        try:
            logger.info("[Slack Bot] Starting Slack bot...")
            handler = SocketModeHandler(self.app, Config.SLACK_APP_TOKEN)
            handler.start()
        except Exception as e:
            logger.error(f"[Slack Bot] Error starting Slack bot: {e}", exc_info=True)
            raise

    def send_message(self, channel: str, text: str) -> None:
        try:
            self.app.client.chat_postMessage(
                channel=channel,
                text=text
            )
        except Exception as e:
            logger.error(f"[Slack Bot] Error sending message: {e}", exc_info=True)
            raise
