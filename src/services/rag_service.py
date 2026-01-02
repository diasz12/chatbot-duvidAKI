"""
RAG (Retrieval Augmented Generation) service
Combines vector search with LLM generation
"""

from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import Config
from src.constants import (
    DUVIDAKI_SYSTEM_PROMPT,
    QUERY_TEMPLATE,
    NO_RESULTS_MESSAGE,
    ERROR_MESSAGE
)
from src.crawlers.confluence_crawler import ConfluenceCrawler
from src.services.document_processor import DocumentProcessor
from src.services.vector_store import VectorStore
from src.utils.logger import setup_logger
from src.utils.validators import InputValidator

logger = setup_logger(__name__)


class RAGService:
    """Retrieval Augmented Generation service"""

    def __init__(self):
        """Initialize RAG service."""
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor()
        self.confluence_crawler = ConfluenceCrawler()
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("RAGService initialized")

    def index_confluence(self, space_key: Optional[str] = None) -> bool:
        """
        Index Confluence space into vector store

        Args:
            space_key: Confluence space key to index

        Returns:
            True if successful
        """
        try:
            logger.info(f"Indexing Confluence space: {space_key}")

            # Crawl Confluence
            documents = self.confluence_crawler.crawl_space(space_key)

            if not documents:
                logger.warning("No documents found in Confluence")
                return False

            # Process and index
            return self._index_documents(documents)

        except Exception as e:
            logger.error(f"Error indexing Confluence: {e}")
            return False

    def _index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Process and index documents

        Args:
            documents: List of documents

        Returns:
            True if successful
        """
        try:
            # Process documents
            texts, metadatas, ids = self.document_processor.process_documents(documents)

            if not texts:
                logger.warning("No texts to index after processing")
                return False

            # Add to vector store
            success = self.vector_store.add_documents(texts, metadatas, ids)

            if success:
                logger.info(f"Successfully indexed {len(texts)} document chunks")

            return success

        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            return False

    def query(self, question: str, n_results: Optional[int] = None) -> str:
        """
        Query the knowledge base and generate response.

        Args:
            question: User question
            n_results: Number of context documents to retrieve

        Returns:
            Generated response
        """
        try:
            # Validate and sanitize input
            try:
                sanitized_question = InputValidator.sanitize_query(question)
                if not sanitized_question:
                    return ERROR_MESSAGE
            except ValueError as e:
                logger.warning(f"Invalid query blocked: {e}")
                return str(e)

            # Retrieve relevant context from vector store
            results = self.vector_store.search(sanitized_question, n_results)

            # Extract documents
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]

            if not documents:
                return NO_RESULTS_MESSAGE

            # Build context
            context = self._build_context(documents, metadatas)

            # Generate response
            response = self._generate_response(sanitized_question, context)

            return response

        except Exception as e:
            logger.error(f"Error querying RAG: {e}", exc_info=True)
            return ERROR_MESSAGE

    def _build_context(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> str:
        """
        Build context from retrieved documents

        Args:
            documents: Retrieved documents
            metadatas: Document metadata

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, (doc, metadata) in enumerate(zip(documents, metadatas), 1):
            source = metadata.get('source', 'unknown')
            title = metadata.get('title', metadata.get('file_path', 'Documento'))
            url = metadata.get('url', '')

            context_part = f"[Fonte {i} - {source.upper()}]\n"
            context_part += f"Título: {title}\n"
            if url:
                context_part += f"URL: {url}\n"
            context_part += f"\n{doc}\n"

            context_parts.append(context_part)

        return "\n\n---\n\n".join(context_parts)

    def _generate_response(self, question: str, context: str) -> str:
        """
        Generate response using LLM

        Args:
            question: User question
            context: Retrieved context

        Returns:
            Generated response
        """
        try:
            user_prompt = QUERY_TEMPLATE.format(context=context, question=question)

            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": DUVIDAKI_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=Config.OPENAI_TEMPERATURE,
                max_tokens=Config.OPENAI_MAX_TOKENS
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return ERROR_MESSAGE

    def get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_documents": self.vector_store.count_documents(),
            "confluence_configured": Config.is_confluence_configured()
        }

    def reset_knowledge_base(self) -> bool:
        """
        Reset entire knowledge base

        Returns:
            True if successful
        """
        return self.vector_store.reset()
