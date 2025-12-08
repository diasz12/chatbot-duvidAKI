"""
Document processor for chunking and preparing documents for vector storage
"""

from typing import List, Dict, Any
import hashlib
from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentProcessor:
    """Process documents for vector storage"""

    def __init__(self):
        """Initialize document processor"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        logger.info("DocumentProcessor initialized")

    def process_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Process documents into chunks with metadata

        Args:
            documents: List of documents with 'content', 'source', and 'metadata'

        Returns:
            Tuple of (texts, metadatas, ids)
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
                # Create unique ID
                chunk_id = self._generate_id(content, source, i)

                # Create metadata
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
        Generate unique ID for document chunk

        Args:
            content: Original content
            source: Source identifier
            index: Chunk index

        Returns:
            Unique ID string
        """
        # Create hash of content for uniqueness
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{source}_{content_hash}_{index}"

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        text = " ".join(text.split())
        return text.strip()

    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from markdown text

        Args:
            text: Markdown text

        Returns:
            List of code blocks with language and content
        """
        import re

        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        code_blocks = []
        for language, code in matches:
            code_blocks.append({
                "language": language or "unknown",
                "code": code.strip()
            })

        return code_blocks
