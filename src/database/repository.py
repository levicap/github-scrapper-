"""
Database repository pattern with retry logic
Handles all database operations with proper error handling
"""
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from datetime import datetime
import time
from typing import List, Dict, Optional, Set
from contextlib import contextmanager

from src.config import settings
from src.database.models import EnrichmentStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseRepository:
    """Repository pattern for database operations with retry logic"""
    
    def __init__(self):
        self.config = settings.database.config_dict
        self.conn = None
        self.max_retries = settings.scraper.MAX_RETRIES
        self.retry_delay = settings.scraper.RETRY_DELAY
    
    def connect(self):
        """Connect to PostgreSQL database with retry"""
        for attempt in range(self.max_retries):
            try:
                self.conn = psycopg2.connect(**self.config)
                logger.info(f"✅ Connected to PostgreSQL: {self.config['host']}/{self.config['database']}")
                return
            except Exception as e:
                logger.error(f"❌ Connection attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt if settings.scraper.EXPONENTIAL_BACKOFF else 1))
                else:
                    raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")
    
    @contextmanager
    def get_cursor(self, dict_cursor=False):
        """Context manager for database cursor"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor if dict_cursor else None)
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_with_retry(self, query: str, params: tuple = None, fetch: bool = False):
        """Execute query with retry logic"""
        for attempt in range(self.max_retries):
            try:
                with self.get_cursor() as cursor:
                    cursor.execute(query, params)
                    if fetch:
                        return cursor.fetchall()
                    return cursor.rowcount
            except Exception as e:
                logger.error(f"Query attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt if settings.scraper.EXPONENTIAL_BACKOFF else 1))
                    # Reconnect if connection was lost
                    if self.conn.closed:
                        self.connect()
                else:
                    raise
    
    def create_tables(self):
        """Create database tables with status enum"""
        logger.info("Creating/verifying database tables...")
        
        with self.get_cursor() as cursor:
            # Create enum type for enrichment status (with PROCESSING state for parallel execution)
            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE enrichment_status AS ENUM ('INITIAL', 'PROCESSING', 'PROFILED', 'ENHANCED', 'FAILED');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
            
            # Create developers table with status (includes parallel execution fields)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS developers (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    enrichment_status enrichment_status DEFAULT 'INITIAL',
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    processing_started_at TIMESTAMP WITH TIME ZONE,
                    claimed_by VARCHAR(255),
                    name VARCHAR(255),
                    email VARCHAR(255),
                    bio TEXT,
                    location VARCHAR(255),
                    company VARCHAR(255),
                    blog VARCHAR(500),
                    twitter_username VARCHAR(255),
                    hireable BOOLEAN,
                    followers INTEGER DEFAULT 0,
                    following INTEGER DEFAULT 0,
                    public_repos INTEGER DEFAULT 0,
                    public_gists INTEGER DEFAULT 0,
                    profile_url VARCHAR(500),
                    avatar_url VARCHAR(500),
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE,
                    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    profiled_at TIMESTAMP WITH TIME ZONE,
                    enhanced_at TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT unique_username UNIQUE (username)
                )
            """)
            
            # Create social_links table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_links (
                    id SERIAL PRIMARY KEY,
                    developer_id INTEGER NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE,
                    CONSTRAINT unique_developer_platform UNIQUE (developer_id, platform)
                )
            """)
            
            # Create repositories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id SERIAL PRIMARY KEY,
                    developer_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    stars INTEGER DEFAULT 0,
                    language VARCHAR(100),
                    url VARCHAR(500),
                    description TEXT,
                    repo_order INTEGER DEFAULT 0,
                    FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE,
                    CONSTRAINT unique_developer_repo UNIQUE (developer_id, name)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_username ON developers(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_status ON developers(enrichment_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_location ON developers(location)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_email ON developers(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_links_developer ON social_links(developer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_developer ON repositories(developer_id)")
            
        logger.info("✅ Database tables created/verified")
    
    # ============= Username Operations =============
    
    def insert_usernames_batch(self, usernames: List[str]) -> int:
        """Insert multiple usernames in batch with INITIAL status"""
        try:
            data = [(username,) for username in usernames]
            with self.get_cursor() as cursor:
                execute_batch(
                    cursor,
                    """
                    INSERT INTO developers (username, enrichment_status) 
                    VALUES (%s, 'INITIAL') 
                    ON CONFLICT (username) DO NOTHING
                    """,
                    data,
                    page_size=100
                )
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to insert username batch: {e}")
            raise
    
    def get_usernames_by_status(self, status: EnrichmentStatus, limit: Optional[int] = None) -> List[str]:
        """Get usernames by enrichment status"""
        query = "SELECT username FROM developers WHERE enrichment_status = %s"
        if limit:
            query += f" LIMIT {limit}"
        
        with self.get_cursor() as cursor:
            cursor.execute(query, (status.value,))
            return [row[0] for row in cursor.fetchall()]
    
    def get_username_count_by_status(self, status: EnrichmentStatus) -> int:
        """Get count of usernames by status"""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM developers WHERE enrichment_status = %s",
                (status.value,)
            )
            return cursor.fetchone()[0]
    
    def claim_batch_for_processing(self, from_status: EnrichmentStatus, limit: int, 
                                   instance_id: str, timeout_minutes: int = 30) -> List[str]:
        """
        Claim a batch of usernames for processing (parallel-safe with row-level locking)
        
        This method enables running multiple scraper instances concurrently by:
        1. Releasing stale claims from crashed/hung instances
        2. Using FOR UPDATE SKIP LOCKED to prevent race conditions
        3. Marking claimed records as PROCESSING with instance_id
        
        Args:
            from_status: Status to claim from (e.g., INITIAL for profile scraper)
            limit: Number of records to claim
            instance_id: Unique identifier for this scraper instance (e.g., hostname-pid)
            timeout_minutes: Consider records stale after this many minutes
            
        Returns:
            List of claimed usernames for this instance to process
        """
        with self.get_cursor() as cursor:
            # Step 1: Release stale claims (instances that crashed or hung)
            cursor.execute("""
                UPDATE developers
                SET enrichment_status = %s,
                    claimed_by = NULL,
                    processing_started_at = NULL
                WHERE enrichment_status = 'PROCESSING'
                    AND processing_started_at < NOW() - INTERVAL '%s minutes'
            """, (from_status.value, timeout_minutes))
            
            stale_released = cursor.rowcount
            if stale_released > 0:
                logger.info(f"Released {stale_released} stale claims (timeout: {timeout_minutes}min)")
            
            # Step 2: Claim new batch with row-level locking
            # FOR UPDATE SKIP LOCKED ensures no two instances claim the same records
            cursor.execute("""
                UPDATE developers
                SET enrichment_status = 'PROCESSING',
                    claimed_by = %s,
                    processing_started_at = NOW()
                WHERE id IN (
                    SELECT id FROM developers
                    WHERE enrichment_status = %s
                    ORDER BY id
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING username
            """, (instance_id, from_status.value, limit))
            
            claimed = [row[0] for row in cursor.fetchall()]
            
            if claimed:
                logger.info(f"Instance {instance_id} claimed {len(claimed)} records")
            
            return claimed
    
    # ============= Profile Operations =============
    
    def update_profile(self, profile: Dict) -> Optional[int]:
        """Update developer profile and set status to PROFILED"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE developers SET
                        name = %s,
                        email = %s,
                        bio = %s,
                        location = %s,
                        company = %s,
                        blog = %s,
                        twitter_username = %s,
                        hireable = %s,
                        followers = %s,
                        following = %s,
                        public_repos = %s,
                        public_gists = %s,
                        profile_url = %s,
                        avatar_url = %s,
                        created_at = %s,
                        updated_at = %s,
                        enrichment_status = 'PROFILED',
                        profiled_at = CURRENT_TIMESTAMP,
                        retry_count = 0,
                        last_error = NULL,
                        claimed_by = NULL,
                        processing_started_at = NULL
                    WHERE username = %s
                    RETURNING id
                """, (
                    profile.get('name'),
                    profile.get('email'),
                    profile.get('bio'),
                    profile.get('location'),
                    profile.get('company'),
                    profile.get('blog'),
                    profile.get('twitter_username'),
                    profile.get('hireable'),
                    profile.get('followers', 0),
                    profile.get('following', 0),
                    profile.get('public_repos', 0),
                    profile.get('public_gists', 0),
                    profile.get('profile_url'),
                    profile.get('avatar_url'),
                    self._parse_datetime(profile.get('created_at')),
                    self._parse_datetime(profile.get('updated_at')),
                    profile.get('username')
                ))
                
                result = cursor.fetchone()
                if result:
                    developer_id = result[0]
                    
                    # Insert social links and repositories
                    self._insert_social_links(cursor, developer_id, profile.get('social_links', {}))
                    self._insert_repositories(cursor, developer_id, profile.get('top_repos', []))
                    
                    return developer_id
                
                return None
        except Exception as e:
            logger.error(f"Failed to update profile for {profile.get('username')}: {e}")
            raise
    
    def _insert_social_links(self, cursor, developer_id: int, social_links: Dict):
        """Insert social links for a developer"""
        social_data = []
        
        for platform, url in social_links.items():
            if url and platform != 'other_links':
                social_data.append((developer_id, platform, url))
        
        # Add other links
        other_links = social_links.get('other_links', [])
        for idx, url in enumerate(other_links):
            social_data.append((developer_id, f'other_{idx+1}', url))
        
        if social_data:
            execute_batch(
                cursor,
                """
                INSERT INTO social_links (developer_id, platform, url)
                VALUES (%s, %s, %s)
                ON CONFLICT (developer_id, platform) DO UPDATE SET url = EXCLUDED.url
                """,
                social_data,
                page_size=50
            )
    
    def _insert_repositories(self, cursor, developer_id: int, repositories: List[Dict]):
        """Insert repositories for a developer"""
        repo_data = [
            (
                developer_id,
                repo.get('name'),
                repo.get('stars', 0),
                repo.get('language'),
                repo.get('url'),
                repo.get('description'),
                idx
            )
            for idx, repo in enumerate(repositories)
        ]
        
        if repo_data:
            execute_batch(
                cursor,
                """
                INSERT INTO repositories (developer_id, name, stars, language, url, description, repo_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (developer_id, name) DO UPDATE SET
                    stars = EXCLUDED.stars,
                    language = EXCLUDED.language,
                    url = EXCLUDED.url,
                    description = EXCLUDED.description,
                    repo_order = EXCLUDED.repo_order
                """,
                repo_data,
                page_size=50
            )
    
    # ============= Error Handling =============
    
    def mark_as_failed(self, username: str, error_message: str):
        """Mark developer as FAILED after max retries and release claim"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE developers 
                SET enrichment_status = 'FAILED',
                    last_error = %s,
                    retry_count = retry_count + 1,
                    claimed_by = NULL,
                    processing_started_at = NULL
                WHERE username = %s
            """, (error_message, username))
        
        logger.warning(f"Marked {username} as FAILED: {error_message}")
    
    def increment_retry_count(self, username: str, error_message: str, back_to_status: EnrichmentStatus) -> int:
        """Increment retry count, release claim, return to original status, and return current count"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE developers 
                SET retry_count = retry_count + 1,
                    last_error = %s,
                    enrichment_status = %s,
                    claimed_by = NULL,
                    processing_started_at = NULL
                WHERE username = %s
                RETURNING retry_count
            """, (error_message, back_to_status.value, username))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    # ============= Statistics =============
    
    def get_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        stats = {}
        
        with self.get_cursor() as cursor:
            # Total counts by status
            cursor.execute("""
                SELECT enrichment_status, COUNT(*) 
                FROM developers 
                GROUP BY enrichment_status
            """)
            for row in cursor.fetchall():
                stats[f'status_{row[0].lower()}'] = row[1]
            
            # Total developers
            cursor.execute("SELECT COUNT(*) FROM developers")
            stats['total_developers'] = cursor.fetchone()[0]
            
            # Developers with email
            cursor.execute("SELECT COUNT(*) FROM developers WHERE email IS NOT NULL")
            stats['developers_with_email'] = cursor.fetchone()[0]
            
            # Developers with social links
            cursor.execute("SELECT COUNT(DISTINCT developer_id) FROM social_links")
            stats['developers_with_social'] = cursor.fetchone()[0]
            
            # Average metrics
            cursor.execute("SELECT AVG(followers)::INTEGER FROM developers WHERE enrichment_status IN ('PROFILED', 'ENHANCED')")
            stats['avg_followers'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT AVG(public_repos)::INTEGER FROM developers WHERE enrichment_status IN ('PROFILED', 'ENHANCED')")
            stats['avg_repos'] = cursor.fetchone()[0] or 0
            
            # Failed count
            cursor.execute("SELECT COUNT(*) FROM developers WHERE enrichment_status = 'FAILED'")
            stats['failed_count'] = cursor.fetchone()[0]
        
        return stats
    
    @staticmethod
    def _parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string"""
        if not dt_string:
            return None
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None
