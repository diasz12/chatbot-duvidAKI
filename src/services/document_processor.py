"""
Document processor for chunking and preparing documents for vector storage.

This module provides the DocumentProcessor class for handling document chunking,
text cleaning, and code block extraction. It prepares documents for embedding
and storage in the vector database.
"""

import hashlib
import re
from typing import Any, Dict, List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import Config
from src.constants import MIN_CHUNK_SIZE, MAX_CHUNK_SIZE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentProcessor:
    """
    Process documents for vector storage.

    Handles document chunking, metadata enrichment, and text preparation
    for embedding generation and vector storage.

    Attributes:
        text_splitter: LangChain text splitter for chunking documents
    """

    def __init__(self):
        """Initialize document processor with configured chunk size and overlap."""
        chunk_size = max(MIN_CHUNK_SIZE, min(Config.CHUNK_SIZE, MAX_CHUNK_SIZE))
        if chunk_size != Config.CHUNK_SIZE:
            logger.warning(
                f"Chunk size {Config.CHUNK_SIZE} outside valid range. "
                f"Using {chunk_size} instead."
            )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=Config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        logger.info(f"DocumentProcessor initialized (chunk_size={chunk_size})")

    def process_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Process documents into chunks with metadata.

        Args:
            documents: List of documents with 'content', 'source', and 'metadata'

        Returns:
            Tuple[List[str], List[Dict[str, Any]], List[str]]:
                - texts: List of chunked text strings
                - metadatas: List of metadata dictionaries for each chunk
                - ids: List of unique IDs for each chunk

        Examples:
            >>> processor = DocumentProcessor()
            >>> docs = [{"content": "text", "source": "github", "metadata": {}}]
            >>> texts, metas, ids = processor.process_documents(docs)
        """
        all_texts = []
        all_metadatas = []
        all_ids = []

        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})

            # Skip empty documents
            if not content or not content.strip():
                continue

            # Split into chunks
            chunks = self.text_splitter.split_text(content)

            for i, chunk in enumerate(chunks):
                chunk_id = self._generate_id(content, source, i)

                chunk_metadata = {
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **metadata
                }

                all_texts.append(chunk)
                all_metadatas.append(chunk_metadata)
                all_ids.append(chunk_id)

        logger.info(f"Processed {len(documents)} documents into {len(all_texts)} chunks")
        return all_texts, all_metadatas, all_ids

    def _generate_id(self, content: str, source: str, index: int) -> str:
        """
        Generate unique ID for document chunk.

        Creates a deterministic ID based on content hash, source, and chunk index.

        Args:
            content: Original document content
            source: Source identifier (e.g., 'github', 'confluence')
            index: Chunk index within the document

        Returns:
            str: Unique ID in format '{source}_{hash}_{index}'

        Examples:
            >>> processor = DocumentProcessor()
            >>> processor._generate_id("Hello World", "github", 0)
            'github_b10a8db1_0'
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"{source}_{content_hash}_{index}"

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Removes extra whitespace and normalizes spacing.

        Args:
            text: Input text to clean

        Returns:
            str: Cleaned and normalized text

        Examples:
            >>> processor = DocumentProcessor()
            >>> processor.clean_text("Hello   World\\n\\n  ")
            'Hello World'
        """
        if not text:
            return ""

        text = " ".join(text.split())
        return text.strip()

    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from markdown text.

        Parses markdown code blocks with optional language specification.

        Args:
            text: Markdown text containing code blocks

        Returns:
            List[Dict[str, str]]: List of code blocks with 'language' and 'code' keys

        Examples:
            >>> processor = DocumentProcessor()
            >>> text = "```python\\nprint('hello')\\n```"
            >>> blocks = processor.extract_code_blocks(text)
            >>> blocks[0]['language']
            'python'
        """
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        code_blocks = []
        for language, code in matches:
            code_blocks.append({
                "language": language or "unknown",
                "code": code.strip()
            })

        return code_blocks
