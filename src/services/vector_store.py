"""
Vector Store service using ChromaDB
Handles document storage and similarity search
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from openai import OpenAI

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VectorStore:
    """Vector database for storing and searching document embeddings"""

    def __init__(self):
        """Initialize ChromaDB client and collection"""
        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.collection_name = "knowledge_base"
        self.collection = self._get_or_create_collection()
        logger.info("VectorStore initialized")

    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "DuvidAKI knowledge base"}
            )

    def _create_embedding(self, text: str) -> List[float]:
        """
        Create embedding using OpenAI API

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = self.openai_client.embeddings.create(
                model=Config.EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """
        Add documents to vector store

        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs

        Returns:
            True if successful
        """
        try:
            # Create embeddings
            embeddings = [self._create_embedding(doc) for doc in documents]

            # Add to collection
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(documents)} documents to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False

    def search(
        self,
        query: str,
        n_results: int = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            Search results with documents and metadata
        """
        if n_results is None:
            n_results = Config.MAX_RESULTS

        try:
            # Create query embedding
            query_embedding = self._create_embedding(query)

            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            logger.info(f"Search returned {len(results['documents'][0])} results")
            return results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def delete_by_source(self, source: str) -> bool:
        """
        Delete documents by source

        Args:
            source: Source identifier (confluence, github, etc.)

        Returns:
            True if successful
        """
        try:
            results = self.collection.get(
                where={"source": source}
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} documents from {source}")

            return True

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    def count_documents(self) -> int:
        """Get total document count"""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def reset(self) -> bool:
        """Delete all documents from collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Vector store reset")
            return True
        except Exception as e:
            logger.error(f"Error resetting vector store: {e}")
            return False
