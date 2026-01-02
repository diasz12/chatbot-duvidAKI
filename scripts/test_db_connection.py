#!/usr/bin/env python3
"""
Test database connection to Supabase/PostgreSQL

Usage:
    python scripts/test_db_connection.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def test_connection():
    """Test database connection and pgvector extension"""

    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    print()

    # 1. Check if DATABASE_URL is configured
    print("1️⃣  Checking configuration...")
    try:
        database_url = Config.get_database_url()
        # Mask password in output
        masked_url = database_url.split('@')[0].split(':')[0] + ":****@" + database_url.split('@')[1]
        print(f"   ✅ DATABASE_URL configured: {masked_url}")
    except Exception as e:
        print(f"   ❌ DATABASE_URL not configured: {e}")
        print()
        print("   Please set DATABASE_URL in your .env file:")
        print("   DATABASE_URL=postgresql://postgres.xxx:[PASSWORD]@...supabase.com:6543/postgres")
        return False

    print()

    # 2. Test basic connection
    print("2️⃣  Testing connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        print("   ✅ Successfully connected to PostgreSQL!")

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   📊 PostgreSQL version: {version[:50]}...")
        cursor.close()

    except ImportError:
        print("   ❌ psycopg2 not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print()
        print("   Common issues:")
        print("   - Wrong password in DATABASE_URL")
        print("   - Firewall blocking connection")
        print("   - Wrong host/port in connection string")
        return False

    print()

    # 3. Check pgvector extension
    print("3️⃣  Checking pgvector extension...")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()

        if result:
            print("   ✅ pgvector extension is installed!")
        else:
            print("   ❌ pgvector extension NOT installed")
            print()
            print("   To fix:")
            print("   1. Go to Supabase Dashboard → Database → Extensions")
            print("   2. Search for 'vector'")
            print("   3. Enable the extension")
            cursor.close()
            conn.close()
            return False

        cursor.close()

    except Exception as e:
        print(f"   ❌ Error checking extension: {e}")
        conn.close()
        return False

    print()

    # 4. Test pgvector functionality
    print("4️⃣  Testing pgvector functionality...")
    try:
        from pgvector.psycopg2 import register_vector
        register_vector(conn)

        cursor = conn.cursor()

        # Create test table
        cursor.execute("""
            CREATE TEMP TABLE vector_test (
                id SERIAL PRIMARY KEY,
                embedding vector(3)
            );
        """)

        # Insert test vector
        cursor.execute(
            "INSERT INTO vector_test (embedding) VALUES (%s)",
            ([1, 2, 3],)
        )

        # Query test vector
        cursor.execute("SELECT embedding FROM vector_test")
        result = cursor.fetchone()

        print(f"   ✅ pgvector working! Test vector: {result[0]}")
        cursor.close()

    except Exception as e:
        print(f"   ❌ pgvector test failed: {e}")
        conn.close()
        return False

    print()

    # 5. Check embeddings table
    print("5️⃣  Checking embeddings table...")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'embeddings'
            );
        """)
        table_exists = cursor.fetchone()[0]

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            count = cursor.fetchone()[0]
            print(f"   ✅ Embeddings table exists with {count} documents")
        else:
            print("   ⚠️  Embeddings table doesn't exist yet (will be created on first use)")

        cursor.close()

    except Exception as e:
        print(f"   ⚠️  Could not check embeddings table: {e}")

    print()

    # 6. Test VectorStore initialization
    print("6️⃣  Testing VectorStore initialization...")
    try:
        from src.services.vector_store import VectorStore

        vector_store = VectorStore()
        count = vector_store.count_documents()

        print(f"   ✅ VectorStore initialized successfully!")
        print(f"   📊 Current document count: {count}")

    except Exception as e:
        print(f"   ❌ VectorStore initialization failed: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

    # Close connection
    conn.close()

    print()
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Index your documents: python main.py index --confluence")
    print("2. Test a query: python main.py query 'test question'")
    print()

    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
