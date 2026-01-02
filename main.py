"""
DuvidAKI - AI Chatbot with Knowledge Base
Main entry point
"""

import argparse
import sys
import io

# Configure UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.config import Config
from src.services.rag_service import RAGService
from src.integrations.slack_bot import SlackBot
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def index_knowledge_base(rag_service: RAGService, args):
    """Index knowledge base from Confluence"""
    try:
        logger.info("Starting knowledge base indexing...")

        # Index Confluence
        if args.confluence or args.all:
            if Config.is_confluence_configured():
                logger.info("Indexing Confluence...")
                success = rag_service.index_confluence()
                if success:
                    logger.info("✅ Confluence indexed successfully")
                else:
                    logger.error("❌ Failed to index Confluence")
            else:
                logger.warning("⚠️  Confluence not configured")

        # Show stats
        stats = rag_service.get_stats()
        logger.info(f"\n📊 Knowledge Base Stats:")
        logger.info(f"   Total documents: {stats['total_documents']}")

    except Exception as e:
        logger.error(f"Error indexing knowledge base: {e}")
        sys.exit(1)


def start_slack_bot(rag_service: RAGService):
    """Start Slack bot"""
    try:
        if not Config.is_slack_configured():
            logger.error("❌ Slack not configured. Please set SLACK_* environment variables.")
            sys.exit(1)

        logger.info("Starting Slack bot...")
        slack_bot = SlackBot(rag_service)
        slack_bot.start()

    except Exception as e:
        logger.error(f"Error starting Slack bot: {e}")
        sys.exit(1)


def test_query(rag_service: RAGService, question: str):
    """Test a query"""
    try:
        logger.info(f"Question: {question}")
        response = rag_service.query(question)
        logger.info(f"\nResponse:\n{response}")

    except Exception as e:
        logger.error(f"Error testing query: {e}")


def show_stats(rag_service: RAGService):
    """Show knowledge base statistics"""
    try:
        stats = rag_service.get_stats()
        print("\n📊 DuvidAKI Statistics")
        print("=" * 50)
        print(f"Total documents: {stats['total_documents']}")
        print(f"Confluence: {'✅ Configured' if stats['confluence_configured'] else '❌ Not configured'}")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Error showing stats: {e}")


def reset_knowledge_base(rag_service: RAGService):
    """Reset knowledge base"""
    try:
        confirm = input("⚠️  Are you sure you want to reset the knowledge base? (yes/no): ")
        if confirm.lower() == "yes":
            logger.info("Resetting knowledge base...")
            success = rag_service.reset_knowledge_base()
            if success:
                logger.info("✅ Knowledge base reset successfully")
            else:
                logger.error("❌ Failed to reset knowledge base")
        else:
            logger.info("Reset cancelled")

    except Exception as e:
        logger.error(f"Error resetting knowledge base: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DuvidAKI - AI Chatbot with Knowledge Base"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index knowledge base")
    index_parser.add_argument("--confluence", action="store_true", help="Index Confluence only")
    index_parser.add_argument("--all", action="store_true", help="Index all sources")

    # Start command
    subparsers.add_parser("start", help="Start Slack bot")

    # Query command
    query_parser = subparsers.add_parser("query", help="Test a query")
    query_parser.add_argument("question", help="Question to ask")

    # Stats command
    subparsers.add_parser("stats", help="Show statistics")

    # Reset command
    subparsers.add_parser("reset", help="Reset knowledge base")

    args = parser.parse_args()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize RAG service
    rag_service = RAGService()

    # Execute command
    if args.command == "index":
        if not (args.confluence or args.all):
            args.all = True  # Default to all
        index_knowledge_base(rag_service, args)

    elif args.command == "start":
        start_slack_bot(rag_service)

    elif args.command == "query":
        test_query(rag_service, args.question)

    elif args.command == "stats":
        show_stats(rag_service)

    elif args.command == "reset":
        reset_knowledge_base(rag_service)

    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
