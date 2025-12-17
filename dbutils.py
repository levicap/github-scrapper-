#!/usr/bin/env python3
"""
Database utility module for PostgreSQL connections
"""

import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import os

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'github_developers'),
    'user': os.getenv('DB_USER', 'ahmed'),
    'password': os.getenv('DB_PASSWORD', 'ahmed123')
}


class DatabaseManager:
    """Manage PostgreSQL database operations"""
    
    def __init__(self, config=None):
        self.config = config or DB_CONFIG
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor()
            print("✅ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        try:
            # Create developers table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS developers (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
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
                    CONSTRAINT unique_username UNIQUE (username)
                )
            """)
            
            # Create social_links table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_links (
                    id SERIAL PRIMARY KEY,
                    developer_id INTEGER NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE,
                    CONSTRAINT unique_developer_platform UNIQUE (developer_id, platform)
                )
            """)
            
            # Create repositories table
            self.cursor.execute("""
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
            
            # Create usernames table (for phase 1)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usernames (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_username ON developers(username)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_location ON developers(location)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_email ON developers(email)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_links_developer ON social_links(developer_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_developer ON repositories(developer_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_usernames_username ON usernames(username)")
            
            self.conn.commit()
            print("✅ Database tables created/verified")
        
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed to create tables: {e}")
            raise
    
    def parse_datetime(self, dt_string):
        """Parse ISO datetime string"""
        if not dt_string:
            return None
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None
    
    def insert_username(self, username):
        """Insert a username into the database"""
        try:
            self.cursor.execute(
                "INSERT INTO usernames (username) VALUES (%s) ON CONFLICT (username) DO NOTHING",
                (username,)
            )
        except Exception as e:
            print(f"❌ Error inserting username {username}: {e}")
    
    def insert_usernames_batch(self, usernames):
        """Insert multiple usernames in batch"""
        try:
            data = [(username,) for username in usernames]
            execute_batch(
                self.cursor,
                "INSERT INTO usernames (username) VALUES (%s) ON CONFLICT (username) DO NOTHING",
                data,
                page_size=100
            )
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting usernames batch: {e}")
            raise
    
    def get_usernames(self):
        """Get all usernames from database"""
        try:
            self.cursor.execute("SELECT username FROM usernames ORDER BY id")
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error fetching usernames: {e}")
            return []
    
    def get_username_count(self):
        """Get total count of usernames"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM usernames")
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def insert_developer(self, profile):
        """Insert a developer profile into the database"""
        try:
            insert_query = """
            INSERT INTO developers (
                username, name, email, bio, location, company, blog, 
                twitter_username, hireable, followers, following, 
                public_repos, public_gists, profile_url, avatar_url,
                created_at, updated_at, scraped_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                bio = EXCLUDED.bio,
                location = EXCLUDED.location,
                company = EXCLUDED.company,
                blog = EXCLUDED.blog,
                twitter_username = EXCLUDED.twitter_username,
                hireable = EXCLUDED.hireable,
                followers = EXCLUDED.followers,
                following = EXCLUDED.following,
                public_repos = EXCLUDED.public_repos,
                public_gists = EXCLUDED.public_gists,
                profile_url = EXCLUDED.profile_url,
                avatar_url = EXCLUDED.avatar_url,
                updated_at = EXCLUDED.updated_at,
                scraped_at = EXCLUDED.scraped_at
            RETURNING id
            """
            
            self.cursor.execute(insert_query, (
                profile.get('username'),
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
                self.parse_datetime(profile.get('created_at')),
                self.parse_datetime(profile.get('updated_at')),
                self.parse_datetime(profile.get('scraped_at'))
            ))
            
            developer_id = self.cursor.fetchone()[0]
            self.conn.commit()
            
            # Insert social links
            social_links = profile.get('social_links', {})
            self.insert_social_links(developer_id, social_links)
            
            # Insert repositories
            repositories = profile.get('top_repos', [])
            self.insert_repositories(developer_id, repositories)
            
            return developer_id
        
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting developer {profile.get('username')}: {e}")
            return None
    
    def insert_social_links(self, developer_id, social_links):
        """Insert social links for a developer"""
        try:
            social_data = []
            
            # Add all social links
            for platform, url in social_links.items():
                if url and platform != 'other_links':
                    social_data.append((developer_id, platform, url))
            
            # Add other links
            other_links = social_links.get('other_links', [])
            for idx, url in enumerate(other_links):
                social_data.append((developer_id, f'other_{idx+1}', url))
            
            if social_data:
                execute_batch(
                    self.cursor,
                    """
                    INSERT INTO social_links (developer_id, platform, url)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (developer_id, platform) DO UPDATE SET url = EXCLUDED.url
                    """,
                    social_data,
                    page_size=50
                )
                self.conn.commit()
        
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting social links: {e}")
    
    def insert_repositories(self, developer_id, repositories):
        """Insert repositories for a developer"""
        try:
            repo_data = []
            
            for idx, repo in enumerate(repositories):
                repo_data.append((
                    developer_id,
                    repo.get('name'),
                    repo.get('stars', 0),
                    repo.get('language'),
                    repo.get('url'),
                    repo.get('description'),
                    idx
                ))
            
            if repo_data:
                execute_batch(
                    self.cursor,
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
                self.conn.commit()
        
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting repositories: {e}")
    
    def get_scraped_usernames(self):
        """Get usernames that have already been scraped"""
        try:
            self.cursor.execute("SELECT username FROM developers")
            return {row[0] for row in self.cursor.fetchall()}
        except:
            return set()
    
    def get_developer_count(self):
        """Get total count of developers"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM developers")
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def get_stats(self):
        """Get database statistics"""
        try:
            stats = {}
            
            self.cursor.execute("SELECT COUNT(*) FROM usernames")
            stats['total_usernames'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM developers")
            stats['total_developers'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM developers WHERE email IS NOT NULL")
            stats['developers_with_email'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(DISTINCT developer_id) FROM social_links")
            stats['developers_with_social'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT AVG(followers)::INTEGER FROM developers")
            stats['avg_followers'] = self.cursor.fetchone()[0] or 0
            
            self.cursor.execute("SELECT AVG(public_repos)::INTEGER FROM developers")
            stats['avg_repos'] = self.cursor.fetchone()[0] or 0
            
            return stats
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {}