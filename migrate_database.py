#!/usr/bin/env python3
"""
Database Migration Script
Migrates existing database schema to new structure with enrichment_status
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import psycopg2
from src.config import settings
from src.utils import get_logger

logger = get_logger(__name__)


def migrate_database():
    """Migrate database to new schema"""
    logger.info("=" * 70)
    logger.info("🔄 Database Migration")
    logger.info("=" * 70)
    
    config = settings.database.config_dict
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        logger.info("Connected to database")
        
        # Step 1: Create enrichment_status enum if not exists (with PROCESSING status)
        logger.info("\n1️⃣  Creating enrichment_status enum...")
        cursor.execute("""
            DO $$ BEGIN
                CREATE TYPE enrichment_status AS ENUM ('INITIAL', 'PROCESSING', 'PROFILED', 'ENHANCED', 'FAILED');
            EXCEPTION
                WHEN duplicate_object THEN 
                    RAISE NOTICE 'enrichment_status type already exists, skipping...';
            END $$;
        """)
        conn.commit()
        logger.info("✅ Enum created/verified")
        
        # Step 2: Add new columns to developers table if they don't exist
        logger.info("\n2️⃣  Adding new columns to developers table (including parallel execution support)...")
        
        columns_to_add = [
            ("enrichment_status", "enrichment_status DEFAULT 'INITIAL'"),
            ("retry_count", "INTEGER DEFAULT 0"),
            ("last_error", "TEXT"),
            ("processing_started_at", "TIMESTAMP WITH TIME ZONE"),
            ("claimed_by", "VARCHAR(255)"),
            ("profiled_at", "TIMESTAMP WITH TIME ZONE"),
            ("enhanced_at", "TIMESTAMP WITH TIME ZONE")
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                cursor.execute(f"""
                    ALTER TABLE developers 
                    ADD COLUMN IF NOT EXISTS {column_name} {column_def}
                """)
                conn.commit()
                logger.info(f"  ✅ Added column: {column_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  Column {column_name} might already exist: {e}")
                conn.rollback()
        
        # Step 3: Migrate existing data - set status based on existing data
        logger.info("\n3️⃣  Migrating existing data...")
        
        # Check if we have old usernames table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'usernames'
            )
        """)
        has_usernames_table = cursor.fetchone()[0]
        
        if has_usernames_table:
            logger.info("  Found old 'usernames' table")
            
            # Migrate usernames to developers with INITIAL status
            cursor.execute("""
                INSERT INTO developers (username, enrichment_status)
                SELECT username, 'INITIAL'
                FROM usernames
                ON CONFLICT (username) DO NOTHING
            """)
            migrated = cursor.rowcount
            conn.commit()
            logger.info(f"  ✅ Migrated {migrated} usernames to developers table")
        
        # Update status for developers with profile data
        cursor.execute("""
            UPDATE developers
            SET enrichment_status = 'PROFILED',
                profiled_at = scraped_at
            WHERE enrichment_status = 'INITIAL'
                AND (name IS NOT NULL OR email IS NOT NULL OR bio IS NOT NULL)
        """)
        updated = cursor.rowcount
        conn.commit()
        logger.info(f"  ✅ Updated {updated} developers to PROFILED status")
        
        # Step 4: Create indexes
        logger.info("\n4️⃣  Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_developers_status ON developers(enrichment_status)",
            "CREATE INDEX IF NOT EXISTS idx_developers_username ON developers(username)",
            "CREATE INDEX IF NOT EXISTS idx_social_links_developer ON social_links(developer_id)",
            "CREATE INDEX IF NOT EXISTS idx_repositories_developer ON repositories(developer_id)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                conn.commit()
                logger.info(f"  ✅ Created index")
            except Exception as e:
                logger.warning(f"  ⚠️  Index might already exist: {e}")
                conn.rollback()
        
        # Step 5: Show statistics
        logger.info("\n5️⃣  Migration Statistics:")
        
        cursor.execute("""
            SELECT enrichment_status, COUNT(*) 
            FROM developers 
            GROUP BY enrichment_status
        """)
        
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[1]}")
        
        cursor.execute("SELECT COUNT(*) FROM developers")
        total = cursor.fetchone()[0]
        logger.info(f"  TOTAL: {total}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 70)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        migrate_database()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
