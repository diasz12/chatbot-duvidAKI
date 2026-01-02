"""
Vector Store service using PostgreSQL + pgvector
Handles document storage and similarity search
"""

import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from typing import List, Dict, Any
import json
from openai import OpenAI

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VectorStore:
    """Vector database for storing and searching document embeddings using PostgreSQL + pgvector"""

    def __init__(self):
        """Initialize PostgreSQL connection and create schema"""
        try:
            self.database_url = Config.get_database_url()
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.conn = None

            # Establish initial connection
            self._connect()

            # Initialize schema
            self._init_schema()

            logger.info("VectorStore initialized with PostgreSQL + pgvector")

        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {e}")
            raise

    def _connect(self):
        """Establish database connection with pgvector support"""
        try:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass

            self.conn = psycopg2.connect(self.database_url)
            register_vector(self.conn)
            logger.debug("Database connection established")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _ensure_connection(self):
        """Ensure database connection is alive, reconnect if needed"""
        try:
            if self.conn is None or self.conn.closed:
                logger.warning("Connection closed, reconnecting...")
                self._connect()
                return

            # Test connection with a simple query
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            logger.warning(f"Connection lost ({e}), reconnecting...")
            self._connect()

    def _init_schema(self):
        """Create embeddings table and indexes if they don't exist"""
        try:
            cursor = self.conn.cursor()

            # Enable pgvector extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Create embeddings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id VARCHAR(255) PRIMARY KEY,
                    document TEXT NOT NULL,
                    embedding vector(1536),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create HNSW index for fast similarity search
            # Note: This will fail if table is empty, we'll create it on first insert
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
                    ON embeddings USING hnsw (embedding vector_cosine_ops);
                """)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Could not create HNSW index (will retry after first insert): {e}")

            # Create GIN index for metadata filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS embeddings_metadata_idx
                ON embeddings USING gin (metadata);
            """)

            # Create index for metadata->>'source' queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS embeddings_metadata_source_idx
                ON embeddings ((metadata->>'source'));
            """)

            self.conn.commit()
            cursor.close()
            logger.info("Database schema initialized")

        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            self.conn.rollback()
            raise

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

    def _create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings in batches using OpenAI API (much faster!)

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        batch_size = Config.OPENAI_BATCH_SIZE

        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(f"Creating embeddings for batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")

                response = self.openai_client.embeddings.create(
                    model=Config.EMBEDDING_MODEL,
                    input=batch
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            return all_embeddings

        except Exception as e:
            logger.error(f"Error creating batch embeddings: {e}")
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
            # Ensure connection is alive
            self._ensure_connection()

            # Create embeddings in batches (MUCH faster than one-by-one!)
            logger.info(f"Creating embeddings for {len(documents)} documents...")
            embeddings = self._create_embeddings_batch(documents)

            # Insert into PostgreSQL
            cursor = self.conn.cursor()

            # Prepare data for batch insert
            data = [
                (doc_id, doc, emb, json.dumps(meta))
                for doc_id, doc, emb, meta in zip(ids, documents, embeddings, metadatas)
            ]

            # Use execute_values for efficient batch insert with UPSERT
            execute_values(
                cursor,
                """
                INSERT INTO embeddings (id, document, embedding, metadata)
                VALUES %s
                ON CONFLICT (id) DO UPDATE
                SET document = EXCLUDED.document,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    created_at = CURRENT_TIMESTAMP
                """,
                data,
                template="(%s, %s, %s::vector, %s::jsonb)"
            )

            self.conn.commit()
            cursor.close()

            # Try to create HNSW index if it doesn't exist (now that we have data)
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
                    ON embeddings USING hnsw (embedding vector_cosine_ops);
                """)
                self.conn.commit()
                cursor.close()
            except Exception:
                pass  # Index already exists or will be created later

            logger.info(f"✅ Added {len(documents)} documents to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            self.conn.rollback()
            return False

    def search(
        self,
        query: str,
        n_results: int = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents using cosine similarity

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            Search results with documents and metadata (ChromaDB-compatible format)
        """
        if n_results is None:
            n_results = Config.MAX_RESULTS

        try:
            # Ensure connection is alive
            self._ensure_connection()

            # Create query embedding
            query_embedding = self._create_embedding(query)

            # Search using cosine distance operator (<=>)
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, document, metadata, embedding <=> %s::vector AS distance
                FROM embeddings
                ORDER BY distance
                LIMIT %s
                """,
                (query_embedding, n_results)
            )

            results = cursor.fetchall()
            cursor.close()

            # Format results to match ChromaDB format for compatibility
            documents = [[row[1] for row in results]]
            # PostgreSQL JSONB already returns dict, no need for json.loads()
            metadatas = [[row[2] for row in results]]
            distances = [[row[3] for row in results]]

            logger.info(f"Search returned {len(results)} results")

            return {
                "documents": documents,
                "metadatas": metadatas,
                "distances": distances
            }

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
            # Ensure connection is alive
            self._ensure_connection()

            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM embeddings WHERE metadata->>'source' = %s",
                (source,)
            )
            deleted_count = cursor.rowcount
            self.conn.commit()
            cursor.close()

            logger.info(f"Deleted {deleted_count} documents from {source}")
            return True

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            self.conn.rollback()
            return False

    def count_documents(self) -> int:
        """Get total document count"""
        try:
            # Ensure connection is alive
            self._ensure_connection()

            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0

    def reset(self) -> bool:
        """Delete all documents from vector store"""
        try:
            # Ensure connection is alive
            self._ensure_connection()

            cursor = self.conn.cursor()
            cursor.execute("TRUNCATE TABLE embeddings")
            self.conn.commit()
            cursor.close()

            logger.info("Vector store reset - all documents deleted")
            return True

        except Exception as e:
            logger.error(f"Error resetting vector store: {e}")
            self.conn.rollback()
            return False

    def __del__(self):
        """Close database connection on cleanup"""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
